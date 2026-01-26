"""Tests for main DiagnosticValidator."""

import pytest
from yaml_to_mdd.models.root import DiagnosticDescription
from yaml_to_mdd.validation.errors import ValidationResult
from yaml_to_mdd.validation.validator import DiagnosticValidator, ValidationError


class TestDiagnosticValidator:
    """Tests for DiagnosticValidator class."""

    def test_validate_returns_result(self, minimal_doc: DiagnosticDescription) -> None:
        """Should return ValidationResult."""
        validator = DiagnosticValidator()
        result = validator.validate(minimal_doc)

        assert isinstance(result, ValidationResult)

    def test_validate_valid_doc(self, minimal_doc: DiagnosticDescription) -> None:
        """Should have no errors for valid document."""
        validator = DiagnosticValidator()
        result = validator.validate(minimal_doc)

        assert result.is_valid

    def test_validate_invalid_doc(self, doc_with_undefined_type: DiagnosticDescription) -> None:
        """Should have errors for invalid document."""
        validator = DiagnosticValidator()
        result = validator.validate(doc_with_undefined_type)

        assert not result.is_valid
        assert len(result.errors) > 0


class TestValidateAndRaise:
    """Tests for validate_and_raise method."""

    def test_valid_doc_no_exception(self, minimal_doc: DiagnosticDescription) -> None:
        """Should not raise for valid document."""
        validator = DiagnosticValidator()
        # Should not raise
        validator.validate_and_raise(minimal_doc)

    def test_invalid_doc_raises_error(self, doc_with_undefined_type: DiagnosticDescription) -> None:
        """Should raise ValidationError for invalid document."""
        validator = DiagnosticValidator()

        with pytest.raises(ValidationError) as exc_info:
            validator.validate_and_raise(doc_with_undefined_type)

        assert "error" in str(exc_info.value).lower()

    def test_strict_mode_raises_on_warnings(
        self, doc_with_unused_type: DiagnosticDescription
    ) -> None:
        """Should raise in strict mode when there are warnings."""
        validator = DiagnosticValidator(strict=True)

        with pytest.raises(ValidationError):
            validator.validate_and_raise(doc_with_unused_type)

    def test_non_strict_mode_allows_warnings(
        self, doc_with_unused_type: DiagnosticDescription
    ) -> None:
        """Should not raise in non-strict mode when there are only warnings."""
        validator = DiagnosticValidator(strict=False)
        # Should not raise (only warnings)
        validator.validate_and_raise(doc_with_unused_type)


class TestValidationError:
    """Tests for ValidationError class."""

    def test_error_message_contains_counts(
        self, doc_with_undefined_type: DiagnosticDescription
    ) -> None:
        """Error message should contain error/warning counts."""
        validator = DiagnosticValidator()

        with pytest.raises(ValidationError) as exc_info:
            validator.validate_and_raise(doc_with_undefined_type)

        assert "error" in str(exc_info.value)

    def test_format_issues(self, doc_with_undefined_type: DiagnosticDescription) -> None:
        """format_issues should list all issues."""
        validator = DiagnosticValidator()

        with pytest.raises(ValidationError) as exc_info:
            validator.validate_and_raise(doc_with_undefined_type)

        formatted = exc_info.value.format_issues()
        assert "ERROR:" in formatted

    def test_result_property(self, doc_with_undefined_type: DiagnosticDescription) -> None:
        """Should have result property with ValidationResult."""
        validator = DiagnosticValidator()

        with pytest.raises(ValidationError) as exc_info:
            validator.validate_and_raise(doc_with_undefined_type)

        assert isinstance(exc_info.value.result, ValidationResult)
        assert len(exc_info.value.result.errors) > 0

    def test_errors_only_property(self, doc_with_undefined_type: DiagnosticDescription) -> None:
        """errors_only should return list of error messages."""
        validator = DiagnosticValidator()

        with pytest.raises(ValidationError) as exc_info:
            validator.validate_and_raise(doc_with_undefined_type)

        errors = exc_info.value.errors_only
        assert isinstance(errors, list)
        assert len(errors) > 0
        assert all(isinstance(e, str) for e in errors)
