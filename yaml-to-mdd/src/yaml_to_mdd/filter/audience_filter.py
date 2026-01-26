"""Filter diagnostic description by audience.

Provides the AudienceFilter class for filtering diagnostic descriptions
to only include items accessible to a specific target audience.
"""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any, TypeVar

from yaml_to_mdd.models.audience import (
    AudienceConfig,
    AudienceSet,
    AudienceValue,
    StandardAudience,
    parse_audience_set,
)

if TYPE_CHECKING:
    from yaml_to_mdd.models.root import DiagnosticDescription
    from yaml_to_mdd.models.services import Services

T = TypeVar("T")


class AudienceFilter:
    """Filter diagnostic descriptions by target audience.

    This class creates a filtered copy of a DiagnosticDescription that
    only includes items accessible to the specified target audience.

    Example:
    -------
        ```python
        filter_obj = AudienceFilter(StandardAudience.AFTERMARKET)
        filtered_doc = filter_obj.filter(original_doc)
        ```

    """

    def __init__(
        self,
        target_audience: AudienceValue,
        config: AudienceConfig | None = None,
    ) -> None:
        """Initialize filter.

        Args:
        ----
            target_audience: The audience to filter for.
            config: Audience configuration (for hierarchy). If not provided,
                   defaults will be used.

        """
        self.target_audience = target_audience
        self.config = config or AudienceConfig(
            default=StandardAudience.PRODUCTION,
            available=list(StandardAudience),
            hierarchy={},
        )
        self.effective_audiences = self.config.get_effective_audiences(target_audience)

    def filter(
        self,
        doc: DiagnosticDescription,
    ) -> DiagnosticDescription:
        """Filter document for target audience.

        Creates a new document with only items accessible to
        the target audience.

        Args:
        ----
            doc: The document to filter.

        Returns:
        -------
            Filtered document (deep copy).

        """
        # Deep copy to avoid modifying original
        filtered = deepcopy(doc)

        # Filter each section
        if filtered.dids:
            filtered.dids = self._filter_dict(filtered.dids)  # type: ignore[assignment]

        if filtered.routines:
            filtered.routines = self._filter_dict(filtered.routines)  # type: ignore[assignment]

        if filtered.dtcs:
            filtered.dtcs = self._filter_dict(filtered.dtcs)  # type: ignore[assignment]

        if filtered.services:
            filtered.services = self._filter_services(filtered.services)

        if filtered.types:
            # Keep types that are referenced by kept items
            filtered.types = self._filter_referenced_types(filtered)

        return filtered

    def _is_accessible(self, audience_set: AudienceSet | None) -> bool:
        """Check if item is accessible to target audience.

        Uses hierarchy-aware checking when available.

        Args:
        ----
            audience_set: The audience set to check, or None for unrestricted.

        Returns:
        -------
            True if accessible, False otherwise.

        """
        if audience_set is None:
            return True  # No restrictions

        return audience_set.is_accessible_with_hierarchy(
            self.target_audience,
            self.effective_audiences,
        )

    def _get_audience_set(self, item: Any) -> AudienceSet | None:
        """Extract audience set from an item.

        Args:
        ----
            item: The item to extract audience from.

        Returns:
        -------
            Parsed AudienceSet or None.

        """
        audience_data = getattr(item, "audience", None)
        return parse_audience_set(audience_data)

    def _filter_dict(self, items: dict[Any, Any]) -> dict[Any, Any]:
        """Filter a dictionary of items by audience.

        Args:
        ----
            items: Dictionary of keyed items (DIDs, routines, DTCs).

        Returns:
        -------
            Filtered dictionary with only accessible items.

        """
        return {
            key: value
            for key, value in items.items()
            if self._is_accessible(self._get_audience_set(value))
        }

    def _filter_services(self, services: Services) -> Services:
        """Filter services by audience.

        Args:
        ----
            services: The Services model to filter.

        Returns:
        -------
            Filtered Services model.

        """
        from yaml_to_mdd.models.services import Services

        # Get all service attributes that are not None
        service_data: dict[str, Any] = {}

        for field_name in Services.model_fields:
            service_config = getattr(services, field_name)
            if service_config is None:
                continue

            # Check if service has audience restriction
            audience_set = self._get_audience_set(service_config)
            if self._is_accessible(audience_set):
                service_data[field_name] = service_config

        # Create new Services instance with filtered data
        return Services.model_validate(service_data)

    def _filter_referenced_types(
        self,
        doc: DiagnosticDescription,
    ) -> dict[str, Any]:
        """Keep only types that are still referenced after filtering.

        Args:
        ----
            doc: The filtered document to analyze.

        Returns:
        -------
            Dictionary of types that are still referenced.

        """
        if not doc.types:
            return {}

        # Collect all referenced type names
        referenced: set[str] = set()

        # From DIDs
        if doc.dids:
            for did_def in doc.dids.values():
                self._collect_type_refs(did_def.type, referenced)

        # From routines
        if doc.routines:
            for routine_def in doc.routines.values():
                if routine_def.parameters:
                    self._collect_routine_type_refs(routine_def.parameters, referenced)

        # Build result with referenced types and their dependencies
        result: dict[str, Any] = {}
        types_to_process = list(referenced)
        processed: set[str] = set()

        while types_to_process:
            type_name = types_to_process.pop()
            if type_name in processed:
                continue

            processed.add(type_name)

            if type_name in doc.types:
                type_def = doc.types[type_name]
                result[type_name] = type_def

                # Add dependencies from struct fields
                if type_def.fields:
                    for field in type_def.fields:
                        self._collect_type_refs(field.type, referenced)
                        if isinstance(field.type, str) and field.type not in processed:
                            types_to_process.append(field.type)

        return result

    def _collect_type_refs(self, type_value: Any, referenced: set[str]) -> None:
        """Collect type references from a type value.

        Args:
        ----
            type_value: The type value (string reference or inline definition).
            referenced: Set to add referenced type names to.

        """
        if isinstance(type_value, str):
            referenced.add(type_value)
        elif hasattr(type_value, "base") and isinstance(type_value.base, str):
            # Inline type definition with base type - could reference another custom type
            referenced.add(type_value.base)

    def _collect_routine_type_refs(
        self,
        parameters: Any,
        referenced: set[str],
    ) -> None:
        """Collect type references from routine parameters.

        Args:
        ----
            parameters: RoutineParameters object.
            referenced: Set to add referenced type names to.

        """
        param_lists = [
            "start_request",
            "start_response",
            "stop_request",
            "stop_response",
            "result_request",
            "result_response",
        ]

        for param_list_name in param_lists:
            param_list = getattr(parameters, param_list_name, None)
            if param_list:
                for param in param_list:
                    if hasattr(param, "type"):
                        self._collect_type_refs(param.type, referenced)

    def get_filter_summary(
        self,
        original: DiagnosticDescription,
        filtered: DiagnosticDescription,
    ) -> dict[str, Any]:
        """Get summary of what was filtered out.

        Args:
        ----
            original: The original document before filtering.
            filtered: The filtered document.

        Returns:
        -------
            Dictionary with counts of original vs filtered items.

        """

        def count_items(doc: DiagnosticDescription) -> dict[str, int]:
            return {
                "dids": len(doc.dids) if doc.dids else 0,
                "routines": len(doc.routines) if doc.routines else 0,
                "dtcs": len(doc.dtcs) if doc.dtcs else 0,
                "types": len(doc.types) if doc.types else 0,
            }

        original_counts = count_items(original)
        filtered_counts = count_items(filtered)

        return {
            "audience": str(
                self.target_audience.value
                if hasattr(self.target_audience, "value")
                else self.target_audience
            ),
            "effective_audiences": sorted(self.effective_audiences),
            "original": original_counts,
            "filtered": filtered_counts,
            "removed": {
                key: original_counts[key] - filtered_counts[key] for key in original_counts
            },
        }
