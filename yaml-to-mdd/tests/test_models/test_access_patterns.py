"""Tests for access_patterns section models."""

import pytest
from pydantic import TypeAdapter, ValidationError
from yaml_to_mdd.models.access_patterns import AccessPattern, AccessPatterns


class TestAccessPattern:
    """Tests for AccessPattern model."""

    def test_minimal_pattern(self) -> None:
        """Should accept minimal access pattern with required fields."""
        pattern = AccessPattern(
            sessions="any",
            security="none",
            authentication="none",
        )
        assert pattern.sessions == "any"
        assert pattern.security == "none"
        assert pattern.authentication == "none"
        assert pattern.nrc_on_fail is None

    def test_sessions_any(self) -> None:
        """Should accept 'any' for sessions."""
        pattern = AccessPattern(
            sessions="any",
            security="none",
            authentication="none",
        )
        assert pattern.sessions == "any"
        assert pattern.requires_session("default") is True
        assert pattern.requires_session("extended") is True

    def test_sessions_list(self) -> None:
        """Should accept list of session names."""
        pattern = AccessPattern(
            sessions=["extended", "programming"],
            security="none",
            authentication="none",
        )
        assert pattern.sessions == ["extended", "programming"]
        assert pattern.requires_session("extended") is True
        assert pattern.requires_session("default") is False

    def test_single_session_string_converted_to_list(self) -> None:
        """Should convert single session string to list."""
        pattern = AccessPattern(
            sessions="extended",  # type: ignore[arg-type]
            security="none",
            authentication="none",
        )
        assert pattern.sessions == ["extended"]

    def test_security_none(self) -> None:
        """Should accept 'none' for security."""
        pattern = AccessPattern(
            sessions="any",
            security="none",
            authentication="none",
        )
        assert pattern.security == "none"
        assert pattern.requires_security() is False

    def test_security_list(self) -> None:
        """Should accept list of security levels."""
        pattern = AccessPattern(
            sessions="any",
            security=["level_1", "level_2"],
            authentication="none",
        )
        assert pattern.security == ["level_1", "level_2"]
        assert pattern.requires_security() is True

    def test_single_security_string_converted_to_list(self) -> None:
        """Should convert single security level string to list."""
        pattern = AccessPattern(
            sessions="any",
            security="level_1",  # type: ignore[arg-type]
            authentication="none",
        )
        assert pattern.security == ["level_1"]

    def test_authentication_none(self) -> None:
        """Should accept 'none' for authentication."""
        pattern = AccessPattern(
            sessions="any",
            security="none",
            authentication="none",
        )
        assert pattern.authentication == "none"
        assert pattern.requires_authentication() is False

    def test_authentication_list(self) -> None:
        """Should accept list of authentication roles."""
        pattern = AccessPattern(
            sessions="any",
            security="none",
            authentication=["role_engineer", "role_admin"],
        )
        assert pattern.authentication == ["role_engineer", "role_admin"]
        assert pattern.requires_authentication() is True

    def test_single_authentication_string_converted_to_list(self) -> None:
        """Should convert single authentication role string to list."""
        pattern = AccessPattern(
            sessions="any",
            security="none",
            authentication="role_engineer",  # type: ignore[arg-type]
        )
        assert pattern.authentication == ["role_engineer"]

    def test_nrc_on_fail_hex_string(self) -> None:
        """Should accept nrc_on_fail as hex string."""
        pattern = AccessPattern(
            sessions="any",
            security=["level_1"],
            authentication="none",
            nrc_on_fail="0x22",  # type: ignore[arg-type]
        )
        assert pattern.nrc_on_fail == 0x22

    def test_nrc_on_fail_int(self) -> None:
        """Should accept nrc_on_fail as int."""
        pattern = AccessPattern(
            sessions="any",
            security=["level_1"],
            authentication="none",
            nrc_on_fail=0x33,
        )
        assert pattern.nrc_on_fail == 0x33

    def test_full_pattern(self) -> None:
        """Should accept full pattern with all fields."""
        pattern = AccessPattern(
            sessions=["extended", "programming"],
            security=["level_2"],
            authentication=["role_engineer"],
            nrc_on_fail=0x33,
        )
        assert pattern.sessions == ["extended", "programming"]
        assert pattern.security == ["level_2"]
        assert pattern.authentication == ["role_engineer"]
        assert pattern.nrc_on_fail == 0x33

    def test_reject_missing_sessions(self) -> None:
        """Should reject pattern missing sessions field."""
        with pytest.raises(ValidationError) as exc_info:
            AccessPattern(
                security="none",  # type: ignore[call-arg]
                authentication="none",
            )
        assert "sessions" in str(exc_info.value)

    def test_reject_missing_security(self) -> None:
        """Should reject pattern missing security field."""
        with pytest.raises(ValidationError) as exc_info:
            AccessPattern(
                sessions="any",  # type: ignore[call-arg]
                authentication="none",
            )
        assert "security" in str(exc_info.value)

    def test_reject_missing_authentication(self) -> None:
        """Should reject pattern missing authentication field."""
        with pytest.raises(ValidationError) as exc_info:
            AccessPattern(
                sessions="any",  # type: ignore[call-arg]
                security="none",
            )
        assert "authentication" in str(exc_info.value)

    def test_reject_invalid_sessions_type(self) -> None:
        """Should reject invalid sessions type."""
        with pytest.raises(ValidationError):
            AccessPattern(
                sessions=123,  # type: ignore[arg-type]
                security="none",
                authentication="none",
            )

    def test_reject_invalid_security_type(self) -> None:
        """Should reject invalid security type."""
        with pytest.raises(ValidationError):
            AccessPattern(
                sessions="any",
                security=123,  # type: ignore[arg-type]
                authentication="none",
            )

    def test_reject_invalid_authentication_type(self) -> None:
        """Should reject invalid authentication type."""
        with pytest.raises(ValidationError):
            AccessPattern(
                sessions="any",
                security="none",
                authentication=123,  # type: ignore[arg-type]
            )

    def test_reject_sessions_list_with_non_strings(self) -> None:
        """Should reject sessions list with non-string items."""
        with pytest.raises(ValidationError):
            AccessPattern(
                sessions=[1, 2, 3],  # type: ignore[arg-type]
                security="none",
                authentication="none",
            )

    def test_reject_extra_fields(self) -> None:
        """Should reject extra fields due to extra='forbid'."""
        with pytest.raises(ValidationError):
            AccessPattern(
                sessions="any",
                security="none",
                authentication="none",
                unknown_field="value",  # type: ignore[call-arg]
            )


class TestAccessPatterns:
    """Tests for AccessPatterns dict type."""

    def test_parse_access_patterns_dict(self) -> None:
        """Should parse dictionary of access patterns."""
        data = {
            "standard_read": {
                "sessions": "any",
                "security": "none",
                "authentication": "none",
            },
            "extended_rw": {
                "sessions": ["extended", "programming"],
                "security": ["level_1"],
                "authentication": "none",
            },
        }

        adapter = TypeAdapter(AccessPatterns)
        patterns = adapter.validate_python(data)

        assert len(patterns) == 2
        assert "standard_read" in patterns
        assert "extended_rw" in patterns
        assert patterns["standard_read"].sessions == "any"
        assert patterns["extended_rw"].sessions == ["extended", "programming"]

    def test_empty_dict(self) -> None:
        """Should accept empty access patterns dict."""
        adapter = TypeAdapter(AccessPatterns)
        patterns = adapter.validate_python({})
        assert len(patterns) == 0

    def test_pattern_with_all_fields(self) -> None:
        """Should parse pattern with all optional fields."""
        data = {
            "secure_write": {
                "sessions": ["extended"],
                "security": ["level_2"],
                "authentication": ["role_engineer"],
                "nrc_on_fail": "0x33",
            },
        }

        adapter = TypeAdapter(AccessPatterns)
        patterns = adapter.validate_python(data)

        assert patterns["secure_write"].nrc_on_fail == 0x33
        assert patterns["secure_write"].requires_security() is True
        assert patterns["secure_write"].requires_authentication() is True


class TestAccessPatternsInRoot:
    """Tests for access_patterns integrated with root model."""

    def test_access_patterns_in_document(self) -> None:
        """Should parse access_patterns in full document."""
        from yaml_to_mdd.models.root import DiagnosticDescription

        data = {
            "schema": "opensovd.cda.diagdesc/v1",
            "meta": {
                "author": "Test",
                "domain": "Test",
                "created": "2024-01-01",
                "revision": "1.0.0",
                "description": "Test",
            },
            "ecu": {
                "id": "TEST",
                "name": "Test ECU",
                "addressing": {"can": {}},
            },
            "sessions": {"default": {"id": "0x01"}},
            "services": {},
            "access_patterns": {
                "standard_read": {
                    "sessions": "any",
                    "security": "none",
                    "authentication": "none",
                },
                "secure_write": {
                    "sessions": ["extended"],
                    "security": ["level_1", "level_2"],
                    "authentication": "none",
                    "nrc_on_fail": "0x33",
                },
            },
        }

        doc = DiagnosticDescription.model_validate(data)
        assert doc.access_patterns is not None
        assert len(doc.access_patterns) == 2
        assert doc.access_patterns["standard_read"].sessions == "any"
        assert doc.access_patterns["secure_write"].security == ["level_1", "level_2"]
        assert doc.access_patterns["secure_write"].nrc_on_fail == 0x33

    def test_access_patterns_optional(self) -> None:
        """Should accept document without access_patterns."""
        from yaml_to_mdd.models.root import DiagnosticDescription

        data = {
            "schema": "opensovd.cda.diagdesc/v1",
            "meta": {
                "author": "Test",
                "domain": "Test",
                "created": "2024-01-01",
                "revision": "1.0.0",
                "description": "Test",
            },
            "ecu": {
                "id": "TEST",
                "name": "Test ECU",
                "addressing": {"can": {}},
            },
            "sessions": {"default": {"id": "0x01"}},
            "services": {},
        }

        doc = DiagnosticDescription.model_validate(data)
        assert doc.access_patterns is None
