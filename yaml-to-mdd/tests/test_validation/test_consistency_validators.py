"""Tests for consistency validators."""

from yaml_to_mdd.models.root import DiagnosticDescription
from yaml_to_mdd.validation.errors import ErrorCodes
from yaml_to_mdd.validation.validator import DiagnosticValidator


class TestUniqueSessionIdValidator:
    """Tests for UniqueSessionIdValidator."""

    def test_unique_session_ids_pass(self, minimal_doc: DiagnosticDescription) -> None:
        """Should pass when session IDs are unique."""
        validator = DiagnosticValidator()
        result = validator.validate(minimal_doc)

        dup_errors = [
            e
            for e in result.errors
            if e.code == ErrorCodes.E100_DUPLICATE_ID and "Session" in e.message
        ]
        assert len(dup_errors) == 0

    def test_duplicate_session_ids_fail(
        self, doc_with_duplicate_session_ids: DiagnosticDescription
    ) -> None:
        """Should error when session IDs are duplicated."""
        validator = DiagnosticValidator()
        result = validator.validate(doc_with_duplicate_session_ids)

        dup_errors = [
            e
            for e in result.errors
            if e.code == ErrorCodes.E100_DUPLICATE_ID and "Session" in e.message
        ]
        assert len(dup_errors) == 1
        assert "duplicate ID" in dup_errors[0].message


class TestUniqueSecurityLevelValidator:
    """Tests for UniqueSecurityLevelValidator."""

    def test_valid_security_levels_pass(
        self, doc_with_valid_security: DiagnosticDescription
    ) -> None:
        """Should pass with valid odd/even security levels."""
        validator = DiagnosticValidator()
        result = validator.validate(doc_with_valid_security)

        # No duplicate errors for seed_request/key_send
        dup_errors = [
            e
            for e in result.errors
            if e.code == ErrorCodes.E100_DUPLICATE_ID
            and ("seed_request" in e.message or "key_send" in e.message)
        ]
        assert len(dup_errors) == 0

    def test_mismatched_security_pair_warning(
        self, doc_with_mismatched_security_pair: DiagnosticDescription
    ) -> None:
        """Should warn when seed_request and key_send don't match expected pattern."""
        validator = DiagnosticValidator()
        result = validator.validate(doc_with_mismatched_security_pair)

        mismatch_warnings = [
            w for w in result.warnings if w.code == ErrorCodes.W010_MISMATCHED_SECURITY_PAIR
        ]
        assert len(mismatch_warnings) == 1
        assert "doesn't match expected" in mismatch_warnings[0].message


class TestDIDRangeValidator:
    """Tests for DIDRangeValidator."""

    def test_valid_did_range_pass(self, doc_with_valid_dids: DiagnosticDescription) -> None:
        """Should pass with valid DID addresses."""
        validator = DiagnosticValidator()
        result = validator.validate(doc_with_valid_dids)

        did_errors = [e for e in result.errors if e.code == ErrorCodes.E201_INVALID_DID_ADDRESS]
        assert len(did_errors) == 0


class TestDTCFormatValidator:
    """Tests for DTCFormatValidator."""

    def test_valid_dtc_format_pass(self, doc_with_dtc_valid_prefix: DiagnosticDescription) -> None:
        """Should pass with valid DTC format."""
        validator = DiagnosticValidator()
        result = validator.validate(doc_with_dtc_valid_prefix)

        dtc_errors = [e for e in result.errors if e.code == ErrorCodes.E302_INVALID_DTC_FORMAT]
        assert len(dtc_errors) == 0


class TestUnusedDefinitionsValidator:
    """Tests for UnusedDefinitionsValidator."""

    def test_unused_type_warning(self, doc_with_unused_type: DiagnosticDescription) -> None:
        """Should warn about unused type definitions."""
        validator = DiagnosticValidator()
        result = validator.validate(doc_with_unused_type)

        unused_warnings = [w for w in result.warnings if w.code == ErrorCodes.W001_UNUSED_TYPE]
        assert len(unused_warnings) == 1
        assert "UnusedType" in unused_warnings[0].message

    def test_used_type_no_warning(self, doc_with_valid_dids: DiagnosticDescription) -> None:
        """Should not warn when type is used."""
        validator = DiagnosticValidator()
        result = validator.validate(doc_with_valid_dids)

        # VIN type is used in DIDs
        unused_warnings = [
            w
            for w in result.warnings
            if w.code == ErrorCodes.W001_UNUSED_TYPE and "VIN" in w.message
        ]
        assert len(unused_warnings) == 0
