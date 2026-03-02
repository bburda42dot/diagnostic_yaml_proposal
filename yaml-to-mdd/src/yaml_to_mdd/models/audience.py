"""Audience filtering models.

Audience-based filtering allows generating different MDD files for different
target audiences (development, production, aftermarket, etc.). Some data
should only be visible to certain audiences.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field


class StandardAudience(str, Enum):
    """Standard audience identifiers."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    AFTERMARKET = "aftermarket"
    OEM = "oem"
    INTERNAL = "internal"
    SUPPLIER = "supplier"


# Type for audience field - can be standard enum or custom string
AudienceValue = StandardAudience | str


class AudienceSet(BaseModel):
    """Set of audiences that can access an item.

    If no audiences are specified, the item is available to all.

    Example:
    -------
        ```yaml
        audience:
          include: [development, oem]
          exclude: [aftermarket]
        ```

    """

    model_config = ConfigDict(extra="forbid")

    include: Annotated[
        list[AudienceValue],
        Field(
            default_factory=list,
            description="Audiences that can access this item",
        ),
    ]

    exclude: Annotated[
        list[AudienceValue],
        Field(
            default_factory=list,
            description="Audiences explicitly denied access",
        ),
    ]

    def is_accessible(self, target_audience: AudienceValue | None) -> bool:
        """Check if item is accessible to target audience.

        Args:
        ----
            target_audience: The audience to check, or None for no filtering.

        Returns:
        -------
            True if accessible, False otherwise.

        """
        if target_audience is None:
            return True

        # Normalize to string for comparison
        target = str(
            target_audience.value if isinstance(target_audience, Enum) else target_audience
        )

        # Check exclusions first
        exclude_strs = [str(a.value if isinstance(a, Enum) else a) for a in self.exclude]
        if target in exclude_strs:
            return False

        # If no inclusions, allow all (except excluded)
        if not self.include:
            return True

        # Check inclusions
        include_strs = [str(a.value if isinstance(a, Enum) else a) for a in self.include]
        return target in include_strs

    def is_accessible_with_hierarchy(
        self,
        target_audience: AudienceValue | None,
        effective_audiences: set[str],
    ) -> bool:
        """Check if item is accessible considering audience hierarchy.

        Args:
        ----
            target_audience: The primary audience to check.
            effective_audiences: Set of all effective audience values (including inherited).

        Returns:
        -------
            True if accessible, False otherwise.

        """
        if target_audience is None:
            return True

        # Check exclusions first against primary audience only
        target = str(
            target_audience.value if isinstance(target_audience, Enum) else target_audience
        )
        exclude_strs = [str(a.value if isinstance(a, Enum) else a) for a in self.exclude]
        if target in exclude_strs:
            return False

        # If no inclusions, allow all (except excluded)
        if not self.include:
            return True

        # Check inclusions against all effective audiences
        include_strs = {str(a.value if isinstance(a, Enum) else a) for a in self.include}
        return bool(effective_audiences & include_strs)


class AudienceConfig(BaseModel):
    """Global audience configuration.

    Defines default audience, available audiences, and audience hierarchy
    for the diagnostic description.

    Example:
    -------
        ```yaml
        audience_config:
          default: production
          available:
            - development
            - production
            - aftermarket
            - oem
          hierarchy:
            development:
              - production
              - aftermarket
            production:
              - aftermarket
        ```

    """

    model_config = ConfigDict(extra="forbid")

    default: Annotated[
        AudienceValue,
        Field(
            default=StandardAudience.PRODUCTION,
            description="Default audience when not specified",
        ),
    ]

    available: Annotated[
        list[AudienceValue],
        Field(
            default_factory=lambda: list(StandardAudience),
            description="Available audience values",
        ),
    ]

    hierarchy: Annotated[
        dict[str, list[str]],
        Field(
            default_factory=dict,
            description="Audience hierarchy (e.g., development includes production)",
        ),
    ]

    def get_effective_audiences(self, audience: AudienceValue) -> set[str]:
        """Get all audiences included by the given audience.

        For example, 'development' might include 'production' and 'aftermarket'.

        Args:
        ----
            audience: The target audience.

        Returns:
        -------
            Set of all effective audience values.

        """
        aud_str = str(audience.value if isinstance(audience, Enum) else audience)
        visited: set[str] = set()
        return self._collect_audiences(aud_str, visited)

    def _collect_audiences(self, audience: str, visited: set[str]) -> set[str]:
        """Recursively collect all effective audiences.

        Args:
        ----
            audience: Current audience to expand.
            visited: Set of already visited audiences (to prevent cycles).

        Returns:
        -------
            Set of all effective audience values.

        """
        if audience in visited:
            return visited

        visited.add(audience)

        # Add inherited audiences
        if audience in self.hierarchy:
            for inherited in self.hierarchy[audience]:
                if inherited not in visited:
                    self._collect_audiences(inherited, visited)

        return visited


def parse_audience_set(value: Any) -> AudienceSet | None:
    """Parse audience set from various formats.

    Supports:
    - None: no restriction
    - dict with include/exclude: AudienceSet
    - list: shorthand for include list

    Args:
    ----
        value: Raw audience value from YAML.

    Returns:
    -------
        Parsed AudienceSet or None.

    """
    if value is None:
        return None

    if isinstance(value, AudienceSet):
        return value

    if isinstance(value, dict):
        return AudienceSet.model_validate(value)

    if isinstance(value, list):
        return AudienceSet(include=value, exclude=[])

    msg = f"Invalid audience format: {type(value)}"
    raise ValueError(msg)


# Mapping from YAML audience names to FBS Audience boolean field names.
# The FBS Audience table has: isDevelopment, isManufacturing, isSupplier,
# isAfterSales, isAfterMarket.  The YAML schema uses slightly different
# names – this mapping bridges the two.
_YAML_TO_FBS_AUDIENCE_FIELD: dict[str, str] = {
    # StandardAudience enum values
    "development": "is_development",
    "production": "is_manufacturing",
    "aftermarket": "is_after_market",
    "supplier": "is_supplier",
    # Extra CDA-native names
    "afterSales": "is_after_sales",
    "after_sales": "is_after_sales",
    "manufacturing": "is_manufacturing",
    "after_market": "is_after_market",
    # Aliases that map to the closest CDA field
    "oem": "is_manufacturing",
    "internal": "is_development",
}


def extract_audience_flags(
    audience_raw: dict[str, Any] | None,
) -> tuple[tuple[str, ...] | None, tuple[str, ...] | None]:
    """Convert a raw YAML audience dict to ``(enabled, disabled)`` tuples.

    The function handles two formats:

    1. **include/exclude** – ``{"include": ["development"], "exclude": []}``
    2. **boolean flags** – ``{"development": false, "afterSales": true}``

    For boolean flags, audiences set to ``True`` are placed in the
    *enabled* tuple and audiences set to ``False`` in the *disabled*
    tuple.  These tuples store the canonical YAML audience names (not
    the FBS field names) so that downstream layers can map them to the
    FBS ``AudienceT`` booleans via :data:`_YAML_TO_FBS_AUDIENCE_FIELD`.

    Returns ``(None, None)`` when *audience_raw* is ``None`` (no
    restriction).
    """
    if audience_raw is None:
        return None, None

    # Format 1: include/exclude dict
    if "include" in audience_raw or "exclude" in audience_raw:
        inc = tuple(str(a) for a in audience_raw.get("include", []))
        exc = tuple(str(a) for a in audience_raw.get("exclude", []))
        return (inc or None), (exc or None)

    # Format 2: boolean flag dict  – e.g. {"development": False, "afterSales": True}
    enabled: list[str] = []
    disabled: list[str] = []
    for name, value in audience_raw.items():
        if isinstance(value, bool):
            if value:
                enabled.append(name)
            else:
                disabled.append(name)
    return (tuple(enabled) or None), (tuple(disabled) or None)


def audience_enabled_to_fbs_flags(
    enabled: tuple[str, ...] | None,
) -> dict[str, bool]:
    """Map IR *audience_enabled* names to FBS ``AudienceT`` boolean kwargs.

    Returns a dict suitable for unpacking into ``AudienceT(**flags)``.
    Only audiences that are in *enabled* will be set to ``True``; the
    rest default to ``False`` (the FlatBuffers default).
    """
    flags: dict[str, bool] = {}
    if enabled is None:
        return flags
    for name in enabled:
        fbs_field = _YAML_TO_FBS_AUDIENCE_FIELD.get(name)
        if fbs_field is not None:
            flags[fbs_field] = True
    return flags
