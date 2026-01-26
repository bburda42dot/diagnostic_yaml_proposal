"""Tests for reference validators."""

from yaml_to_mdd.models.root import DiagnosticDescription
from yaml_to_mdd.validation.errors import ErrorCodes
from yaml_to_mdd.validation.validator import DiagnosticValidator


class TestTypeReferenceValidator:
    """Tests for TypeReferenceValidator."""

    def test_valid_type_reference(self, doc_with_valid_dids: DiagnosticDescription) -> None:
        """Should pass when type references are valid."""
        validator = DiagnosticValidator()
        result = validator.validate(doc_with_valid_dids)

        type_errors = [e for e in result.errors if e.code == ErrorCodes.E001_UNDEFINED_TYPE]
        assert len(type_errors) == 0

    def test_undefined_type_reference(self, doc_with_undefined_type: DiagnosticDescription) -> None:
        """Should error when type reference is undefined."""
        validator = DiagnosticValidator()
        result = validator.validate(doc_with_undefined_type)

        type_errors = [e for e in result.errors if e.code == ErrorCodes.E001_UNDEFINED_TYPE]
        assert len(type_errors) == 1
        assert "UndefinedType" in type_errors[0].message

    def test_builtin_types_always_valid(self, minimal_doc: DiagnosticDescription) -> None:
        """Should accept all builtin types without definitions."""
        from yaml_to_mdd.models.dids import DIDDefinition

        # Add DIDs using builtin types
        dids = {
            0x0001: DIDDefinition(name="Test u8", type="u8", access="read"),
            0x0002: DIDDefinition(name="Test u16", type="u16", access="read"),
            0x0003: DIDDefinition(name="Test u32", type="u32", access="read"),
            0x0004: DIDDefinition(name="Test i8", type="i8", access="read"),
            0x0005: DIDDefinition(name="Test string", type="string", access="read"),
            0x0006: DIDDefinition(name="Test bool", type="bool", access="read"),
        }

        doc = DiagnosticDescription(**{**minimal_doc.model_dump(), "dids": dids})

        validator = DiagnosticValidator()
        result = validator.validate(doc)

        type_errors = [e for e in result.errors if e.code == ErrorCodes.E001_UNDEFINED_TYPE]
        assert len(type_errors) == 0


class TestSessionReferenceValidator:
    """Tests for SessionReferenceValidator."""

    def test_valid_session_reference(self, doc_with_valid_sessions: DiagnosticDescription) -> None:
        """Should pass when session reference is valid."""
        validator = DiagnosticValidator()
        result = validator.validate(doc_with_valid_sessions)

        session_errors = [e for e in result.errors if e.code == ErrorCodes.E002_UNDEFINED_SESSION]
        assert len(session_errors) == 0

    def test_undefined_session_reference(
        self, doc_with_undefined_session: DiagnosticDescription
    ) -> None:
        """Should error when session reference is undefined."""
        validator = DiagnosticValidator()
        result = validator.validate(doc_with_undefined_session)

        session_errors = [e for e in result.errors if e.code == ErrorCodes.E002_UNDEFINED_SESSION]
        assert len(session_errors) == 1
        assert "nonexistent_session" in session_errors[0].message

    def test_any_session_always_valid(self, doc_with_any_session: DiagnosticDescription) -> None:
        """Should accept 'any' as valid session value."""
        validator = DiagnosticValidator()
        result = validator.validate(doc_with_any_session)

        session_errors = [e for e in result.errors if e.code == ErrorCodes.E002_UNDEFINED_SESSION]
        assert len(session_errors) == 0


class TestSecurityReferenceValidator:
    """Tests for SecurityReferenceValidator."""

    def test_valid_security_reference(self, doc_with_valid_security: DiagnosticDescription) -> None:
        """Should pass when security reference is valid."""
        validator = DiagnosticValidator()
        result = validator.validate(doc_with_valid_security)

        security_errors = [e for e in result.errors if e.code == ErrorCodes.E003_UNDEFINED_SECURITY]
        assert len(security_errors) == 0

    def test_undefined_security_reference(
        self, doc_with_undefined_security: DiagnosticDescription
    ) -> None:
        """Should error when security reference is undefined."""
        validator = DiagnosticValidator()
        result = validator.validate(doc_with_undefined_security)

        security_errors = [e for e in result.errors if e.code == ErrorCodes.E003_UNDEFINED_SECURITY]
        assert len(security_errors) == 1
        assert "nonexistent_level" in security_errors[0].message

    def test_none_security_always_valid(self, minimal_doc: DiagnosticDescription) -> None:
        """Should accept 'none' as valid security value."""
        validator = DiagnosticValidator()
        result = validator.validate(minimal_doc)

        # minimal_doc has security: none
        security_errors = [e for e in result.errors if e.code == ErrorCodes.E003_UNDEFINED_SECURITY]
        assert len(security_errors) == 0


class TestAccessPatternReferenceValidator:
    """Tests for AccessPatternReferenceValidator."""

    def test_valid_access_pattern_reference(
        self, doc_with_valid_dids: DiagnosticDescription
    ) -> None:
        """Should pass when access pattern reference is valid."""
        validator = DiagnosticValidator()
        result = validator.validate(doc_with_valid_dids)

        ap_errors = [e for e in result.errors if e.code == ErrorCodes.E004_UNDEFINED_ACCESS_PATTERN]
        assert len(ap_errors) == 0

    def test_undefined_access_pattern_reference(
        self, doc_with_undefined_access_pattern: DiagnosticDescription
    ) -> None:
        """Should error when access pattern reference is undefined."""
        validator = DiagnosticValidator()
        result = validator.validate(doc_with_undefined_access_pattern)

        ap_errors = [e for e in result.errors if e.code == ErrorCodes.E004_UNDEFINED_ACCESS_PATTERN]
        assert len(ap_errors) == 1
        assert "nonexistent_pattern" in ap_errors[0].message
