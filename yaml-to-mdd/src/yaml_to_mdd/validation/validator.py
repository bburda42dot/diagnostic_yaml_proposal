"""Main validator combining all validation rules."""

from __future__ import annotations

from typing import TYPE_CHECKING

from yaml_to_mdd.validation.base import CompositeValidator
from yaml_to_mdd.validation.consistency_validators import (
    DIDRangeValidator,
    DTCFormatValidator,
    RoutineIdRangeValidator,
    UniqueSecurityLevelValidator,
    UniqueSessionIdValidator,
    UnusedDefinitionsValidator,
)
from yaml_to_mdd.validation.errors import ValidationResult, ValidationSeverity
from yaml_to_mdd.validation.reference_validators import (
    AccessPatternReferenceValidator,
    SecurityReferenceValidator,
    SessionReferenceValidator,
    TypeReferenceValidator,
)

if TYPE_CHECKING:
    from yaml_to_mdd.models.root import DiagnosticDescription


class DiagnosticValidator:
    """Main validator for diagnostic descriptions.

    Combines reference validators (for cross-reference checks) and
    consistency validators (for semantic checks).
    """

    def __init__(self, strict: bool = False) -> None:
        """Initialize validator.

        Args:
        ----
            strict: If True, treat warnings as errors.

        """
        self.strict = strict
        self._validator = CompositeValidator(
            [
                # Reference validators
                TypeReferenceValidator(),
                SessionReferenceValidator(),
                SecurityReferenceValidator(),
                AccessPatternReferenceValidator(),
                # Consistency validators
                UniqueSessionIdValidator(),
                UniqueSecurityLevelValidator(),
                DIDRangeValidator(),
                DTCFormatValidator(),
                RoutineIdRangeValidator(),
                UnusedDefinitionsValidator(),
            ]
        )

    def validate(self, doc: DiagnosticDescription) -> ValidationResult:
        """Validate a diagnostic description.

        Args:
        ----
            doc: The document to validate.

        Returns:
        -------
            ValidationResult with all issues found.

        """
        result = ValidationResult()
        self._validator.validate(doc, result)
        return result

    def validate_and_raise(self, doc: DiagnosticDescription) -> None:
        """Validate and raise exception if invalid.

        Args:
        ----
            doc: The document to validate.

        Raises:
        ------
            ValidationError: If validation fails.

        """
        result = self.validate(doc)

        if not result.is_valid:
            raise ValidationError(result)

        if self.strict and result.warnings:
            raise ValidationError(result)


class ValidationError(Exception):
    """Raised when validation fails."""

    def __init__(self, result: ValidationResult) -> None:
        """Initialize with validation result.

        Args:
        ----
            result: The validation result containing issues.

        """
        self.result = result
        error_count = len(result.errors)
        warning_count = len(result.warnings)

        parts = []
        if error_count:
            parts.append(f"{error_count} error(s)")
        if warning_count:
            parts.append(f"{warning_count} warning(s)")

        message = f"Validation failed: {', '.join(parts)}"
        super().__init__(message)

    def format_issues(self) -> str:
        """Format all issues as a string.

        Returns
        -------
            Formatted string with all issues.

        """
        lines = []

        for issue in self.result.errors:
            lines.append(f"ERROR: {issue}")

        for issue in self.result.warnings:
            lines.append(f"WARNING: {issue}")

        return "\n".join(lines)

    @property
    def errors_only(self) -> list[str]:
        """Get only error messages.

        Returns
        -------
            List of error message strings.

        """
        return [
            str(issue) for issue in self.result.issues if issue.severity == ValidationSeverity.ERROR
        ]
