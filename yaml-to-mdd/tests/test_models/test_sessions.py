"""Tests for Sessions section models."""

import pytest
from pydantic import ValidationError
from yaml_to_mdd.models.sessions import Session, SessionTiming


class TestSessionTiming:
    """Tests for SessionTiming model."""

    def test_valid_timing(self) -> None:
        """Should accept valid timing values."""
        timing = SessionTiming(p2_ms=50, p2_star_ms=5000)
        assert timing.p2_ms == 50
        assert timing.p2_star_ms == 5000

    def test_timing_defaults_to_none(self) -> None:
        """Should default all fields to None."""
        timing = SessionTiming()
        assert timing.p2_ms is None
        assert timing.p2_star_ms is None

    def test_rejects_negative_timing(self) -> None:
        """Should reject negative timing values."""
        with pytest.raises(ValidationError):
            SessionTiming(p2_ms=-1)

    def test_rejects_timing_out_of_range(self) -> None:
        """Should reject timing > 65535."""
        with pytest.raises(ValidationError):
            SessionTiming(p2_ms=70000)

    def test_rejects_extra_fields(self) -> None:
        """Should reject extra fields."""
        with pytest.raises(ValidationError):
            SessionTiming(p2_ms=50, unknown_field=100)  # type: ignore


class TestSession:
    """Tests for Session model."""

    def test_minimal_session(self) -> None:
        """Should accept session with only ID."""
        session = Session(id=0x01)
        assert session.id == 0x01
        assert session.alias is None
        assert session.requires_unlock is None
        assert session.timing is None

    def test_full_session(self) -> None:
        """Should accept full session config."""
        session = Session(
            id="0x03",  # type: ignore
            alias="ExtendedSession",
            requires_unlock=False,
            timing=SessionTiming(p2_ms=100),
        )
        assert session.id == 0x03
        assert session.alias == "ExtendedSession"
        assert session.requires_unlock is False
        assert session.timing is not None
        assert session.timing.p2_ms == 100

    def test_hex_id_parsing(self) -> None:
        """Should parse hex string IDs."""
        session = Session(id="0x02")  # type: ignore
        assert session.id == 0x02

    def test_decimal_id(self) -> None:
        """Should accept decimal integer IDs."""
        session = Session(id=3)
        assert session.id == 3

    def test_rejects_id_out_of_range(self) -> None:
        """Should reject session ID > 0xFF."""
        with pytest.raises(ValidationError):
            Session(id=0x100)

    def test_rejects_negative_id(self) -> None:
        """Should reject negative session ID."""
        with pytest.raises(ValidationError):
            Session(id=-1)

    def test_rejects_empty_alias(self) -> None:
        """Should reject empty alias."""
        with pytest.raises(ValidationError):
            Session(id=0x01, alias="")

    def test_rejects_extra_fields(self) -> None:
        """Should reject extra fields."""
        with pytest.raises(ValidationError):
            Session(id=0x01, unknown_field="value")  # type: ignore

    def test_nested_timing_from_dict(self) -> None:
        """Should parse nested timing from dict."""
        session = Session.model_validate(
            {
                "id": "0x03",
                "timing": {
                    "p2_ms": 100,
                    "p2_star_ms": 10000,
                },
            }
        )
        assert session.timing is not None
        assert session.timing.p2_ms == 100
        assert session.timing.p2_star_ms == 10000


class TestSessionsInRoot:
    """Tests for sessions in DiagnosticDescription."""

    @pytest.fixture
    def valid_base_data(self) -> dict:
        """Return valid base document data."""
        return {
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
            "services": {},
            "access_patterns": {},
        }

    def test_sessions_dictionary(self, valid_base_data: dict) -> None:
        """Should parse sessions as dictionary."""
        from yaml_to_mdd.models.root import DiagnosticDescription

        valid_base_data["sessions"] = {
            "default": {"id": "0x01"},
            "extended": {
                "id": "0x03",
                "alias": "Extended",
                "requires_unlock": False,
            },
            "programming": {
                "id": "0x02",
                "requires_unlock": True,
                "timing": {"p2_ms": 100, "p2_star_ms": 10000},
            },
        }

        doc = DiagnosticDescription.model_validate(valid_base_data)
        assert len(doc.sessions) == 3
        assert doc.sessions["default"].id == 0x01
        assert doc.sessions["extended"].alias == "Extended"
        assert doc.sessions["programming"].timing is not None
        assert doc.sessions["programming"].timing.p2_ms == 100

    def test_empty_sessions(self, valid_base_data: dict) -> None:
        """Should accept empty sessions dict."""
        from yaml_to_mdd.models.root import DiagnosticDescription

        valid_base_data["sessions"] = {}
        doc = DiagnosticDescription.model_validate(valid_base_data)
        assert doc.sessions == {}

    def test_single_session(self, valid_base_data: dict) -> None:
        """Should accept single session."""
        from yaml_to_mdd.models.root import DiagnosticDescription

        valid_base_data["sessions"] = {
            "default": {"id": "0x01", "alias": "Default"},
        }
        doc = DiagnosticDescription.model_validate(valid_base_data)
        assert len(doc.sessions) == 1
        assert doc.sessions["default"].alias == "Default"

    def test_custom_session_keys(self, valid_base_data: dict) -> None:
        """Should accept custom session key names."""
        from yaml_to_mdd.models.root import DiagnosticDescription

        valid_base_data["sessions"] = {
            "my_custom_session": {"id": "0x40"},
            "vendor_specific": {"id": "0x60"},
        }
        doc = DiagnosticDescription.model_validate(valid_base_data)
        assert "my_custom_session" in doc.sessions
        assert doc.sessions["vendor_specific"].id == 0x60
