"""Tests for validation error types."""

import pytest
from yaml_to_mdd.validation.errors import (
    ErrorCodes,
    ValidationIssue,
    ValidationLocation,
    ValidationResult,
    ValidationSeverity,
)


class TestValidationLocation:
    """Tests for ValidationLocation."""

    def test_str_with_all_fields(self) -> None:
        """Should format location with line and column."""
        loc = ValidationLocation(path="dids.0xF190.type", line=10, column=5)
        assert str(loc) == "dids.0xF190.type (line 10, col 5)"

    def test_str_with_line_only(self) -> None:
        """Should format location with line only."""
        loc = ValidationLocation(path="dids.0xF190.type", line=10)
        assert str(loc) == "dids.0xF190.type (line 10)"

    def test_str_path_only(self) -> None:
        """Should format location with path only."""
        loc = ValidationLocation(path="dids.0xF190.type")
        assert str(loc) == "dids.0xF190.type"

    def test_frozen(self) -> None:
        """Should be immutable."""
        loc = ValidationLocation(path="test")
        with pytest.raises(AttributeError):
            loc.path = "new"  # type: ignore[misc]


class TestValidationIssue:
    """Tests for ValidationIssue."""

    def test_str_basic(self) -> None:
        """Should format issue as string."""
        issue = ValidationIssue(
            code="E001",
            message="Test error",
            severity=ValidationSeverity.ERROR,
        )
        result = str(issue)
        assert "[E001]" in result
        assert "ERROR" in result
        assert "Test error" in result

    def test_str_with_location(self) -> None:
        """Should include location in string."""
        issue = ValidationIssue(
            code="E001",
            message="Test error",
            severity=ValidationSeverity.ERROR,
            location=ValidationLocation(path="test.path"),
        )
        result = str(issue)
        assert "at test.path" in result

    def test_str_with_suggestion(self) -> None:
        """Should include suggestion in string."""
        issue = ValidationIssue(
            code="E001",
            message="Test error",
            severity=ValidationSeverity.ERROR,
            suggestion="Try this fix",
        )
        result = str(issue)
        assert "hint: Try this fix" in result

    def test_frozen(self) -> None:
        """Should be immutable."""
        issue = ValidationIssue(
            code="E001",
            message="Test",
            severity=ValidationSeverity.ERROR,
        )
        with pytest.raises(AttributeError):
            issue.code = "E002"  # type: ignore[misc]


class TestValidationResult:
    """Tests for ValidationResult."""

    def test_is_valid_with_no_issues(self) -> None:
        """Should be valid with no issues."""
        result = ValidationResult()
        assert result.is_valid is True

    def test_is_valid_with_warnings_only(self) -> None:
        """Should be valid with only warnings."""
        result = ValidationResult()
        result.add_warning("W001", "Test warning", "path")
        assert result.is_valid is True

    def test_is_valid_with_errors(self) -> None:
        """Should be invalid with errors."""
        result = ValidationResult()
        result.add_error("E001", "Test error", "path")
        assert result.is_valid is False

    def test_errors_property(self) -> None:
        """Should filter only errors."""
        result = ValidationResult()
        result.add_error("E001", "Error", "path")
        result.add_warning("W001", "Warning", "path")

        assert len(result.errors) == 1
        assert result.errors[0].code == "E001"

    def test_warnings_property(self) -> None:
        """Should filter only warnings."""
        result = ValidationResult()
        result.add_error("E001", "Error", "path")
        result.add_warning("W001", "Warning", "path")

        assert len(result.warnings) == 1
        assert result.warnings[0].code == "W001"

    def test_add_error_creates_issue(self) -> None:
        """Should create error issue with correct fields."""
        result = ValidationResult()
        result.add_error(
            code="E001",
            message="Test error",
            path="test.path",
            suggestion="Fix it",
            extra="context",
        )

        assert len(result.issues) == 1
        issue = result.issues[0]
        assert issue.code == "E001"
        assert issue.severity == ValidationSeverity.ERROR
        assert issue.location is not None
        assert issue.location.path == "test.path"
        assert issue.suggestion == "Fix it"
        assert issue.context == {"extra": "context"}

    def test_add_warning_creates_issue(self) -> None:
        """Should create warning issue with correct fields."""
        result = ValidationResult()
        result.add_warning(
            code="W001",
            message="Test warning",
            path="test.path",
        )

        assert len(result.issues) == 1
        assert result.issues[0].severity == ValidationSeverity.WARNING

    def test_merge(self) -> None:
        """Should merge issues from another result."""
        result1 = ValidationResult()
        result1.add_error("E001", "Error 1", "path")

        result2 = ValidationResult()
        result2.add_error("E002", "Error 2", "path")
        result2.add_warning("W001", "Warning", "path")

        result1.merge(result2)

        assert len(result1.issues) == 3
        assert len(result1.errors) == 2
        assert len(result1.warnings) == 1


class TestErrorCodes:
    """Tests for ErrorCodes constants."""

    def test_reference_errors_start_with_e0(self) -> None:
        """Reference errors should be E0xx."""
        assert ErrorCodes.E001_UNDEFINED_TYPE == "E001"
        assert ErrorCodes.E002_UNDEFINED_SESSION == "E002"
        assert ErrorCodes.E003_UNDEFINED_SECURITY == "E003"

    def test_duplicate_errors_start_with_e1(self) -> None:
        """Duplicate errors should be E1xx."""
        assert ErrorCodes.E100_DUPLICATE_ID == "E100"

    def test_range_errors_start_with_e2(self) -> None:
        """Range errors should be E2xx."""
        assert ErrorCodes.E200_VALUE_OUT_OF_RANGE == "E200"
        assert ErrorCodes.E201_INVALID_DID_ADDRESS == "E201"

    def test_format_errors_start_with_e3(self) -> None:
        """Format errors should be E3xx."""
        assert ErrorCodes.E300_INVALID_FORMAT == "E300"
        assert ErrorCodes.E302_INVALID_DTC_FORMAT == "E302"

    def test_warnings_start_with_w(self) -> None:
        """Warnings should be W0xx."""
        assert ErrorCodes.W001_UNUSED_TYPE == "W001"
        assert ErrorCodes.W002_UNUSED_SESSION == "W002"
