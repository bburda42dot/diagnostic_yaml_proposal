"""Tests for DIDs section models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from yaml_to_mdd.models.dids import (
    DIDDefinition,
    IOControl,
    WriteCondition,
    _validate_dids,
)
from yaml_to_mdd.models.types import BaseType, TypeDefinition


class TestWriteCondition:
    """Tests for WriteCondition model."""

    def test_session_condition(self) -> None:
        """Should accept session condition."""
        cond = WriteCondition(session="extended")
        assert cond.session == "extended"
        assert cond.security is None
        assert cond.authentication is None

    def test_security_condition(self) -> None:
        """Should accept security condition."""
        cond = WriteCondition(security="level_1")
        assert cond.security == "level_1"

    def test_authentication_condition(self) -> None:
        """Should accept authentication condition."""
        cond = WriteCondition(authentication="admin")
        assert cond.authentication == "admin"

    def test_combined_conditions(self) -> None:
        """Should accept multiple conditions."""
        cond = WriteCondition(session="extended", security="level_1")
        assert cond.session == "extended"
        assert cond.security == "level_1"

    def test_empty_condition(self) -> None:
        """Should accept empty condition (all None)."""
        cond = WriteCondition()
        assert cond.session is None
        assert cond.security is None
        assert cond.authentication is None

    def test_rejects_extra_fields(self) -> None:
        """Should reject unknown fields."""
        with pytest.raises(ValidationError):
            WriteCondition(session="ext", unknown="value")  # type: ignore[call-arg]


class TestDIDDefinition:
    """Tests for DIDDefinition model."""

    def test_minimal_did(self) -> None:
        """Should accept minimal DID definition."""
        did = DIDDefinition(
            name="TestDID",
            type="u16",
            access="read",
        )
        assert did.name == "TestDID"
        assert did.type == "u16"
        assert did.access == "read"
        assert did.description is None
        assert did.access_pattern is None

    def test_full_did(self) -> None:
        """Should accept full DID definition."""
        did = DIDDefinition(
            name="VIN",
            description="Vehicle Identification Number",
            type="VINType",
            access="standard_read",
            access_pattern="standard_read",
            readable=True,
            writable=False,
        )
        assert did.name == "VIN"
        assert did.description == "Vehicle Identification Number"
        assert did.access == "standard_read"
        assert did.access_pattern == "standard_read"
        assert did.readable is True
        assert did.writable is False

    def test_access_as_string(self) -> None:
        """Should accept access as string reference to access_patterns."""
        did = DIDDefinition(
            name="Test",
            type="u8",
            access="extended_write",
        )
        assert did.access == "extended_write"

    def test_inline_type_definition(self) -> None:
        """Should accept inline type definition as dict."""
        did = DIDDefinition(
            name="HardwareNumber",
            type={"base": "ascii", "length": 20},  # type: ignore[arg-type]
            access="read",
        )
        assert isinstance(did.type, TypeDefinition)
        assert did.type.base == BaseType.ASCII
        assert did.type.length == 20

    def test_inline_type_definition_u16_scaled(self) -> None:
        """Should accept inline scaled type definition."""
        did = DIDDefinition(
            name="EngineSpeed",
            type={  # type: ignore[arg-type]
                "base": "u16",
                "scale": 0.25,
                "unit": "rpm",
            },
            access="read",
        )
        assert isinstance(did.type, TypeDefinition)
        assert did.type.base == BaseType.U16
        assert did.type.scale == 0.25
        assert did.type.unit == "rpm"

    def test_readable_writable_flags(self) -> None:
        """Should accept readable/writable boolean flags."""
        did = DIDDefinition(
            name="Calibration",
            type="CalibType",
            access="calib",
            readable=True,
            writable=True,
        )
        assert did.readable is True
        assert did.writable is True

    def test_writable_only(self) -> None:
        """Should accept write-only DID."""
        did = DIDDefinition(
            name="Command",
            type="u8",
            access="write",
            readable=False,
            writable=True,
        )
        assert did.readable is False
        assert did.writable is True

    def test_write_conditions(self) -> None:
        """Should accept write conditions."""
        did = DIDDefinition(
            name="ConfigDID",
            type="u8",
            access="config",
            readable=True,
            writable=True,
            write_conditions=[
                WriteCondition(session="extended"),
                WriteCondition(security="level_1"),
            ],
        )
        assert did.write_conditions is not None
        assert len(did.write_conditions) == 2
        assert did.write_conditions[0].session == "extended"
        assert did.write_conditions[1].security == "level_1"

    def test_read_conditions(self) -> None:
        """Should accept read conditions."""
        did = DIDDefinition(
            name="SecureDID",
            type="bytes",
            access="secure",
            read_conditions=[
                WriteCondition(security="level_2"),
            ],
        )
        assert did.read_conditions is not None
        assert len(did.read_conditions) == 1
        assert did.read_conditions[0].security == "level_2"

    def test_scaling_override(self) -> None:
        """Should accept scale/offset override."""
        did = DIDDefinition(
            name="Temperature",
            type="TemperatureType",
            access="read",
            scale=0.1,
            offset=-40.0,
            unit="°C",
        )
        assert did.scale == 0.1
        assert did.offset == -40.0
        assert did.unit == "°C"

    def test_io_control(self) -> None:
        """Should accept io_control for InputOutputControlByIdentifier."""
        did = DIDDefinition(
            name="ActuatorDID",
            type="u8",
            access="ioctl",
            io_control=IOControl(
                return_control_to_ecu=True,
                short_term_adjustment=True,
            ),
        )
        assert did.io_control is not None
        assert did.io_control.return_control_to_ecu is True
        assert did.io_control.short_term_adjustment is True

    def test_snapshot_flag(self) -> None:
        """Should accept snapshot flag for DTC freeze frame."""
        did = DIDDefinition(
            name="SnapshotDID",
            type="u16",
            access="read",
            snapshot=True,
        )
        assert did.snapshot is True

    def test_annotations(self) -> None:
        """Should accept annotations dict."""
        did = DIDDefinition(
            name="AnnotatedDID",
            type="u8",
            access="read",
            annotations={"category": "diagnostics", "priority": 1},
        )
        assert did.annotations is not None
        assert did.annotations["category"] == "diagnostics"

    def test_rejects_empty_name(self) -> None:
        """Should reject empty name."""
        with pytest.raises(ValidationError):
            DIDDefinition(name="", type="u8", access="read")


class TestDIDsDict:
    """Tests for DIDsDict parsing."""

    def test_parse_hex_string_keys(self) -> None:
        """Should parse hex string keys."""
        data = {
            "0xF190": {"name": "VIN", "type": "VINType", "access": "read"},
            "0xF191": {"name": "ECUHardware", "type": "ascii", "access": "read"},
        }
        dids = _validate_dids(data)
        assert 0xF190 in dids
        assert 0xF191 in dids
        assert dids[0xF190].name == "VIN"
        assert dids[0xF191].name == "ECUHardware"

    def test_parse_lowercase_hex_keys(self) -> None:
        """Should parse lowercase hex keys."""
        data = {
            "0xf190": {"name": "VIN", "type": "VINType", "access": "read"},
        }
        dids = _validate_dids(data)
        assert 0xF190 in dids

    def test_parse_integer_keys(self) -> None:
        """Should parse integer keys."""
        data = {
            61840: {"name": "VIN", "type": "VINType", "access": "read"},
        }
        dids = _validate_dids(data)
        assert 0xF190 in dids  # 61840 == 0xF190

    def test_parse_decimal_string_keys(self) -> None:
        """Should parse decimal string keys."""
        data = {
            "61840": {"name": "VIN", "type": "VINType", "access": "read"},
        }
        dids = _validate_dids(data)
        assert 61840 in dids

    def test_parse_mixed_keys(self) -> None:
        """Should parse mixed key formats."""
        data = {
            "0xF190": {"name": "VIN", "type": "VINType", "access": "read"},
            61841: {"name": "ECUHardware", "type": "ascii", "access": "read"},
            "4660": {"name": "EngineSpeed", "type": "u16", "access": "read"},
        }
        dids = _validate_dids(data)
        assert len(dids) == 3
        assert 0xF190 in dids
        assert 0xF191 in dids  # 61841
        assert 0x1234 in dids  # 4660

    def test_parse_zero_did(self) -> None:
        """Should accept DID 0x0000."""
        data = {
            "0x0000": {"name": "ZeroDID", "type": "u8", "access": "read"},
        }
        dids = _validate_dids(data)
        assert 0 in dids

    def test_parse_max_did(self) -> None:
        """Should accept DID 0xFFFF."""
        data = {
            "0xFFFF": {"name": "MaxDID", "type": "u8", "access": "read"},
        }
        dids = _validate_dids(data)
        assert 0xFFFF in dids

    def test_reject_out_of_range_did(self) -> None:
        """Should reject DID > 0xFFFF."""
        data = {
            "0x10000": {"name": "Invalid", "type": "u8", "access": "read"},
        }
        with pytest.raises(ValueError, match="out of range"):
            _validate_dids(data)

    def test_reject_negative_did(self) -> None:
        """Should reject negative DID."""
        data = {
            -1: {"name": "Invalid", "type": "u8", "access": "read"},
        }
        with pytest.raises(ValueError, match="out of range"):
            _validate_dids(data)

    def test_reject_invalid_key_type(self) -> None:
        """Should reject invalid key type."""
        data = {
            3.14: {"name": "Invalid", "type": "u8", "access": "read"},  # type: ignore[dict-item]
        }
        with pytest.raises(ValueError, match="Invalid DID key type"):
            _validate_dids(data)

    def test_reject_non_dict_value(self) -> None:
        """Should reject non-dict input."""
        with pytest.raises(ValueError, match="must be a dictionary"):
            _validate_dids([])  # type: ignore[arg-type]

    def test_empty_dids(self) -> None:
        """Should accept empty DIDs dictionary."""
        dids = _validate_dids({})
        assert len(dids) == 0


class TestDIDsInRoot:
    """Tests for DIDs integrated with root model."""

    def test_dids_in_document(self) -> None:
        """Should parse DIDs in full document."""
        from yaml_to_mdd.models.root import DiagnosticDescription

        data = {
            "schema": "opensovd.cda.diagdesc/v1",
            "meta": {
                "author": "Test",
                "domain": "Test",
                "created": "2025-01-01",
                "revision": "1.0.0",
                "description": "Test",
            },
            "ecu": {
                "id": "TEST",
                "name": "Test ECU",
                "addressing": {
                    "doip": {
                        "ip": "192.168.1.1",
                        "logical_address": 0x100,
                        "tester_address": 0x200,
                    }
                },
            },
            "sessions": {"default": {"id": 1}},
            "services": {},
            "access_patterns": {},
            "dids": {
                "0xF190": {
                    "name": "VIN",
                    "type": {"base": "ascii", "length": 17},
                    "access": "read",
                },
                "0x1234": {
                    "name": "EngineSpeed",
                    "type": "EngineSpeedType",
                    "access": "read_write",
                    "write_conditions": [
                        {"session": "extended"},
                    ],
                },
            },
        }

        doc = DiagnosticDescription.model_validate(data)
        assert doc.dids is not None
        assert 0xF190 in doc.dids
        assert doc.dids[0xF190].name == "VIN"
        assert isinstance(doc.dids[0xF190].type, TypeDefinition)
        assert doc.dids[0x1234].name == "EngineSpeed"
        assert doc.dids[0x1234].access == "read_write"

    def test_dids_with_integer_keys(self) -> None:
        """Should handle integer keys in document."""
        from yaml_to_mdd.models.root import DiagnosticDescription

        data = {
            "schema": "opensovd.cda.diagdesc/v1",
            "meta": {
                "author": "Test",
                "domain": "Test",
                "created": "2025-01-01",
                "revision": "1.0.0",
                "description": "Test",
            },
            "ecu": {
                "id": "TEST",
                "name": "Test ECU",
                "addressing": {
                    "doip": {
                        "ip": "192.168.1.1",
                        "logical_address": 0x100,
                        "tester_address": 0x200,
                    }
                },
            },
            "sessions": {"default": {"id": 1}},
            "services": {},
            "access_patterns": {},
            "dids": {
                61840: {  # 0xF190
                    "name": "VIN",
                    "type": "VINType",
                    "access": "read",
                },
            },
        }

        doc = DiagnosticDescription.model_validate(data)
        assert doc.dids is not None
        assert 0xF190 in doc.dids

    def test_empty_dids_in_document(self) -> None:
        """Should accept empty DIDs."""
        from yaml_to_mdd.models.root import DiagnosticDescription

        data = {
            "schema": "opensovd.cda.diagdesc/v1",
            "meta": {
                "author": "Test",
                "domain": "Test",
                "created": "2025-01-01",
                "revision": "1.0.0",
                "description": "Test",
            },
            "ecu": {
                "id": "TEST",
                "name": "Test ECU",
                "addressing": {
                    "doip": {
                        "ip": "192.168.1.1",
                        "logical_address": 0x100,
                        "tester_address": 0x200,
                    }
                },
            },
            "sessions": {"default": {"id": 1}},
            "services": {},
            "access_patterns": {},
            "dids": {},
        }

        doc = DiagnosticDescription.model_validate(data)
        assert doc.dids == {}

    def test_null_dids_in_document(self) -> None:
        """Should accept null/missing DIDs."""
        from yaml_to_mdd.models.root import DiagnosticDescription

        data = {
            "schema": "opensovd.cda.diagdesc/v1",
            "meta": {
                "author": "Test",
                "domain": "Test",
                "created": "2025-01-01",
                "revision": "1.0.0",
                "description": "Test",
            },
            "ecu": {
                "id": "TEST",
                "name": "Test ECU",
                "addressing": {
                    "doip": {
                        "ip": "192.168.1.1",
                        "logical_address": 0x100,
                        "tester_address": 0x200,
                    }
                },
            },
            "sessions": {"default": {"id": 1}},
            "services": {},
            "access_patterns": {},
        }

        doc = DiagnosticDescription.model_validate(data)
        assert doc.dids is None
