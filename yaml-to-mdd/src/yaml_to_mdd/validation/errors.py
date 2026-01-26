"""Validation error types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ValidationSeverity(Enum):
    """Severity level for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class ValidationLocation:
    """Location in the YAML where an issue was found."""

    path: str
    """JSONPath-like path to the issue (e.g., 'dids.0xF190.type')."""

    line: int | None = None
    """Line number in the source file (if available)."""

    column: int | None = None
    """Column number in the source file (if available)."""

    def __str__(self) -> str:
        """Format location as string."""
        if self.line is not None:
            if self.column is not None:
                return f"{self.path} (line {self.line}, col {self.column})"
            return f"{self.path} (line {self.line})"
        return self.path


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation issue."""

    code: str
    """Unique error code (e.g., 'E001', 'W001')."""

    message: str
    """Human-readable error message."""

    severity: ValidationSeverity
    """Severity level."""

    location: ValidationLocation | None = None
    """Location in the YAML file."""

    suggestion: str | None = None
    """Suggested fix."""

    context: dict[str, Any] = field(default_factory=dict)
    """Additional context for debugging."""

    def __str__(self) -> str:
        """Format issue as string."""
        parts = [f"[{self.code}]", self.severity.value.upper(), self.message]
        if self.location:
            parts.append(f"at {self.location}")
        if self.suggestion:
            parts.append(f"(hint: {self.suggestion})")
        return " ".join(parts)


@dataclass
class ValidationResult:
    """Result of validation containing all issues."""

    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        """Get only error-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Get only warning-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    @property
    def is_valid(self) -> bool:
        """Check if there are no errors (warnings are OK)."""
        return len(self.errors) == 0

    def add(self, issue: ValidationIssue) -> None:
        """Add an issue to the result."""
        self.issues.append(issue)

    def add_error(
        self,
        code: str,
        message: str,
        path: str,
        suggestion: str | None = None,
        **context: Any,
    ) -> None:
        """Add an error issue."""
        self.add(
            ValidationIssue(
                code=code,
                message=message,
                severity=ValidationSeverity.ERROR,
                location=ValidationLocation(path=path),
                suggestion=suggestion,
                context=context,
            )
        )

    def add_warning(
        self,
        code: str,
        message: str,
        path: str,
        suggestion: str | None = None,
        **context: Any,
    ) -> None:
        """Add a warning issue."""
        self.add(
            ValidationIssue(
                code=code,
                message=message,
                severity=ValidationSeverity.WARNING,
                location=ValidationLocation(path=path),
                suggestion=suggestion,
                context=context,
            )
        )

    def merge(self, other: ValidationResult) -> None:
        """Merge another result into this one."""
        self.issues.extend(other.issues)


class ErrorCodes:
    """Standard validation error codes."""

    # E0xx - Reference errors
    E001_UNDEFINED_TYPE = "E001"
    E002_UNDEFINED_SESSION = "E002"
    E003_UNDEFINED_SECURITY = "E003"
    E004_UNDEFINED_ACCESS_PATTERN = "E004"
    E005_UNDEFINED_DID = "E005"

    # E1xx - Duplicate errors
    E100_DUPLICATE_ID = "E100"
    E101_DUPLICATE_NAME = "E101"
    E102_DUPLICATE_DID_ADDRESS = "E102"

    # E2xx - Range errors
    E200_VALUE_OUT_OF_RANGE = "E200"
    E201_INVALID_DID_ADDRESS = "E201"
    E202_INVALID_SESSION_ID = "E202"

    # E3xx - Format errors
    E300_INVALID_FORMAT = "E300"
    E301_INVALID_HEX_VALUE = "E301"
    E302_INVALID_DTC_FORMAT = "E302"

    # W0xx - Warnings
    W001_UNUSED_TYPE = "W001"
    W002_UNUSED_SESSION = "W002"
    W003_MISSING_DESCRIPTION = "W003"
    W004_DEPRECATED_FEATURE = "W004"
    W010_MISMATCHED_SECURITY_PAIR = "W010"
