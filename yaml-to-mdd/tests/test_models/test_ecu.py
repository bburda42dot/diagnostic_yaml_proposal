"""Tests for ECU section models."""

import pytest
from pydantic import ValidationError
from yaml_to_mdd.models.ecu import (
    Addressing,
    AddressingMode,
    CANAddressing,
    DoIPAddressing,
    Ecu,
    ProtocolDefinition,
    Timing,
)


class TestProtocolDefinition:
    """Tests for ProtocolDefinition model."""

    def test_minimal_protocol_definition(self) -> None:
        """Should accept minimal protocol definition."""
        protocol = ProtocolDefinition(protocol_short_name="UDSonCAN")
        assert protocol.protocol_short_name == "UDSonCAN"
        assert protocol.description is None
        assert protocol.is_default is False

    def test_full_protocol_definition(self) -> None:
        """Should accept full protocol definition."""
        protocol = ProtocolDefinition(
            protocol_short_name="UDSonDoIP",
            description="UDS over DoIP",
            is_default=True,
        )
        assert protocol.protocol_short_name == "UDSonDoIP"
        assert protocol.description == "UDS over DoIP"
        assert protocol.is_default is True

    def test_valid_short_names(self) -> None:
        """Should accept all valid protocol short names."""
        valid_names = [
            "UDSonCAN",
            "UDSonDoIP",
            "UDSonLIN",
            "UDSonIP",
            "UDSonFR",
            "ISO_14229_3_DoIP",
            "ISO_15765_3_CAN",
            "ISO_14229_3_CAN",
        ]
        for name in valid_names:
            protocol = ProtocolDefinition(protocol_short_name=name)  # type: ignore
            assert protocol.protocol_short_name == name

    def test_rejects_invalid_short_name(self) -> None:
        """Should reject invalid protocol short name."""
        with pytest.raises(ValidationError):
            ProtocolDefinition(protocol_short_name="UNKNOWN_PROTOCOL")  # type: ignore


class TestProtocols:
    """Tests for protocols as dict[str, ProtocolDefinition]."""

    def test_protocols_single(self) -> None:
        """Should accept single protocol definition."""
        protocols: dict[str, ProtocolDefinition] = {
            "UDS_CAN": ProtocolDefinition(protocol_short_name="UDSonCAN"),
        }
        assert len(protocols) == 1
        assert protocols["UDS_CAN"].protocol_short_name == "UDSonCAN"

    def test_protocols_multiple(self) -> None:
        """Should accept multiple protocol definitions."""
        protocols: dict[str, ProtocolDefinition] = {
            "can": ProtocolDefinition(protocol_short_name="UDSonCAN", is_default=True),
            "doip": ProtocolDefinition(protocol_short_name="UDSonDoIP"),
        }
        assert len(protocols) == 2
        assert protocols["can"].is_default is True


class TestDoIPAddressing:
    """Tests for DoIPAddressing model."""

    @pytest.fixture
    def valid_doip_data(self) -> dict:
        """Return valid DoIP data."""
        return {
            "ip": "192.168.1.100",
            "logical_address": "0x0010",
            "tester_address": "0x0F00",
        }

    def test_valid_doip_minimal(self, valid_doip_data: dict) -> None:
        """Should accept minimal valid DoIP config."""
        doip = DoIPAddressing.model_validate(valid_doip_data)
        assert str(doip.ip) == "192.168.1.100"
        assert doip.logical_address == 0x0010
        assert doip.tester_address == 0x0F00
        assert doip.port == 13400  # Default

    def test_valid_doip_full(self) -> None:
        """Should accept full DoIP config."""
        doip = DoIPAddressing(
            ip="192.168.1.100",
            port=13400,
            logical_address=0x0010,
            tester_address=0x0F00,
            functional_address=0x7DF,
            routing_activation=0x00,
        )
        assert doip.functional_address == 0x7DF

    def test_accepts_ipv6(self) -> None:
        """Should accept IPv6 address."""
        doip = DoIPAddressing(
            ip="::1",
            logical_address=0x0010,
            tester_address=0x0F00,
        )
        assert str(doip.ip) == "::1"

    def test_accepts_hex_addresses(self, valid_doip_data: dict) -> None:
        """Should accept hex string addresses."""
        valid_doip_data["logical_address"] = "0xFFFF"
        doip = DoIPAddressing.model_validate(valid_doip_data)
        assert doip.logical_address == 0xFFFF

    def test_rejects_invalid_ip(self, valid_doip_data: dict) -> None:
        """Should reject invalid IP address."""
        valid_doip_data["ip"] = "not-an-ip"
        with pytest.raises(ValidationError):
            DoIPAddressing.model_validate(valid_doip_data)

    def test_rejects_invalid_port(self, valid_doip_data: dict) -> None:
        """Should reject invalid port numbers."""
        valid_doip_data["port"] = 70000  # > 65535
        with pytest.raises(ValidationError):
            DoIPAddressing.model_validate(valid_doip_data)

    def test_rejects_address_out_of_range(self, valid_doip_data: dict) -> None:
        """Should reject address > 16-bit."""
        valid_doip_data["logical_address"] = 0x10000  # > 0xFFFF
        with pytest.raises(ValidationError):
            DoIPAddressing.model_validate(valid_doip_data)


class TestCANAddressing:
    """Tests for CANAddressing model."""

    def test_valid_can_full(self) -> None:
        """Should accept full CAN config."""
        can = CANAddressing(
            physical_request=0x700,
            physical_response=0x708,
            functional_request=0x7DF,
        )
        assert can.physical_request == 0x700
        assert can.physical_response == 0x708
        assert can.functional_request == 0x7DF

    def test_can_all_optional(self) -> None:
        """All CAN fields should be optional."""
        can = CANAddressing()
        assert can.physical_request is None
        assert can.physical_response is None
        assert can.functional_request is None

    def test_accepts_hex_strings(self) -> None:
        """Should accept hex string CAN IDs."""
        can = CANAddressing(
            physical_request="0x700",  # type: ignore
            physical_response="0x708",  # type: ignore
        )
        assert can.physical_request == 0x700
        assert can.physical_response == 0x708

    def test_accepts_29bit_can_ids(self) -> None:
        """Should accept 29-bit CAN IDs."""
        can = CANAddressing(
            physical_request=0x18DA00F1,  # 29-bit extended ID
        )
        assert can.physical_request == 0x18DA00F1


class TestTiming:
    """Tests for Timing model."""

    def test_valid_timing_full(self) -> None:
        """Should accept full timing config."""
        timing = Timing(
            p2_ms=50,
            p2_star_ms=5000,
            s3_ms=5000,
        )
        assert timing.p2_ms == 50
        assert timing.p2_star_ms == 5000
        assert timing.s3_ms == 5000

    def test_timing_all_optional(self) -> None:
        """All timing fields should be optional."""
        timing = Timing()
        assert timing.p2_ms is None
        assert timing.p2_star_ms is None
        assert timing.s3_ms is None

    def test_rejects_negative_timing(self) -> None:
        """Should reject negative timing values."""
        with pytest.raises(ValidationError):
            Timing(p2_ms=-1)


class TestAddressing:
    """Tests for Addressing model."""

    def test_valid_addressing_doip_only(self) -> None:
        """Should accept DoIP-only addressing."""
        addressing = Addressing(
            doip=DoIPAddressing(
                ip="192.168.1.100",
                logical_address=0x0010,
                tester_address=0x0F00,
            )
        )
        assert addressing.doip is not None
        assert addressing.can is None

    def test_valid_addressing_can_only(self) -> None:
        """Should accept CAN-only addressing."""
        addressing = Addressing(
            can=CANAddressing(
                physical_request=0x700,
                physical_response=0x708,
            )
        )
        assert addressing.can is not None
        assert addressing.doip is None

    def test_valid_addressing_both(self) -> None:
        """Should accept both DoIP and CAN."""
        addressing = Addressing(
            doip=DoIPAddressing(
                ip="192.168.1.100",
                logical_address=0x0010,
                tester_address=0x0F00,
            ),
            can=CANAddressing(
                physical_request=0x700,
            ),
            timing=Timing(p2_ms=50),
        )
        assert addressing.doip is not None
        assert addressing.can is not None
        assert addressing.timing is not None


class TestEcu:
    """Tests for Ecu model."""

    @pytest.fixture
    def valid_ecu_data(self) -> dict:
        """Return valid ECU data."""
        return {
            "id": "ECM_V1",
            "name": "Engine Control Module",
            "addressing": {
                "doip": {
                    "ip": "192.168.1.100",
                    "logical_address": "0x0010",
                    "tester_address": "0x0F00",
                }
            },
        }

    def test_valid_ecu_minimal(self, valid_ecu_data: dict) -> None:
        """Should accept minimal valid ECU."""
        ecu = Ecu.model_validate(valid_ecu_data)
        assert ecu.id == "ECM_V1"
        assert ecu.name == "Engine Control Module"
        assert ecu.addressing.doip is not None

    def test_valid_ecu_full(self, valid_ecu_data: dict) -> None:
        """Should accept full ECU config."""
        valid_ecu_data["protocols"] = {
            "doip": {"protocol_short_name": "UDSonDoIP"},
        }
        valid_ecu_data["default_addressing_mode"] = "physical"

        ecu = Ecu.model_validate(valid_ecu_data)
        assert ecu.protocols is not None
        assert "doip" in ecu.protocols
        assert ecu.protocols["doip"].protocol_short_name == "UDSonDoIP"
        assert ecu.default_addressing_mode == AddressingMode.PHYSICAL

    def test_addressing_mode_enum_values(self, valid_ecu_data: dict) -> None:
        """Should accept all addressing mode values."""
        for mode in ["physical", "functional", "both"]:
            valid_ecu_data["default_addressing_mode"] = mode
            ecu = Ecu.model_validate(valid_ecu_data)
            assert ecu.default_addressing_mode == AddressingMode(mode)

    def test_rejects_empty_id(self, valid_ecu_data: dict) -> None:
        """Should reject empty ECU ID."""
        valid_ecu_data["id"] = ""
        with pytest.raises(ValidationError):
            Ecu.model_validate(valid_ecu_data)

    def test_rejects_empty_name(self, valid_ecu_data: dict) -> None:
        """Should reject empty ECU name."""
        valid_ecu_data["name"] = ""
        with pytest.raises(ValidationError):
            Ecu.model_validate(valid_ecu_data)

    @pytest.mark.parametrize("field", ["id", "name", "addressing"])
    def test_missing_required_field(self, valid_ecu_data: dict, field: str) -> None:
        """Should reject missing required fields."""
        del valid_ecu_data[field]
        with pytest.raises(ValidationError):
            Ecu.model_validate(valid_ecu_data)


class TestEcuWithRoot:
    """Tests for ECU integrated with DiagnosticDescription."""

    def test_full_document_with_ecu(self) -> None:
        """Should parse full document with proper ECU."""
        from yaml_to_mdd.models.root import DiagnosticDescription

        data = {
            "schema": "opensovd.cda.diagdesc/v1",
            "meta": {
                "author": "John Doe",
                "domain": "Powertrain",
                "created": "2024-01-15",
                "revision": "1.0.0",
                "description": "Engine Control Module",
            },
            "ecu": {
                "id": "ECM_V1",
                "name": "Engine Control Module",
                "protocols": {
                    "doip": {
                        "protocol_short_name": "UDSonDoIP",
                        "is_default": True,
                    },
                    "can": {
                        "protocol_short_name": "UDSonCAN",
                    },
                },
                "default_addressing_mode": "physical",
                "addressing": {
                    "doip": {
                        "ip": "192.168.1.100",
                        "port": 13400,
                        "logical_address": "0x0010",
                        "tester_address": "0x0F00",
                    },
                    "can": {
                        "physical_request": "0x700",
                        "physical_response": "0x708",
                    },
                    "timing": {
                        "p2_ms": 50,
                        "p2_star_ms": 5000,
                    },
                },
            },
            "sessions": {},
            "services": {},
            "access_patterns": {},
        }

        doc = DiagnosticDescription.model_validate(data)
        assert doc.ecu.id == "ECM_V1"
        assert doc.ecu.addressing.doip is not None
        assert doc.ecu.addressing.doip.logical_address == 0x0010
        assert doc.ecu.addressing.can is not None
        assert doc.ecu.addressing.can.physical_request == 0x700
