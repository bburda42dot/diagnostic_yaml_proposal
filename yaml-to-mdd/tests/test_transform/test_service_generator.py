"""Tests for service generator."""

from yaml_to_mdd.ir.services import IRServiceType
from yaml_to_mdd.models.dids import DIDDefinition
from yaml_to_mdd.models.routines import RoutineDefinition
from yaml_to_mdd.models.types import BaseType, TypeDefinition
from yaml_to_mdd.transform.service_generator import (
    generate_read_did_service,
    generate_routine_services,
    generate_write_did_service,
)


class TestGenerateReadDidService:
    """Tests for generate_read_did_service."""

    def test_basic_read_service(self) -> None:
        """Should generate basic read service."""
        did_def = DIDDefinition(
            name="VIN",
            type=TypeDefinition(base=BaseType.ASCII, length=17),
            access="read",
        )

        service = generate_read_did_service(
            did_id=0xF190,
            did_def=did_def,
            dop_name="DOP_VIN",
        )

        assert service.short_name == "Read_VIN"
        assert service.service_id == 0x22
        assert service.service_type == IRServiceType.POS_RESPONSE

    def test_read_service_request(self) -> None:
        """Should generate correct request structure."""
        did_def = DIDDefinition(
            name="TestDID",
            type=TypeDefinition(base=BaseType.U16),
            access="read",
        )

        service = generate_read_did_service(0x1234, did_def, "DOP_Test")

        assert service.request is not None
        assert service.request.short_name == "Read_TestDID_Request"
        assert len(service.request.params) == 2
        # Check constant prefix: 22 12 34
        assert service.request.constant_prefix == bytes([0x22, 0x12, 0x34])

    def test_read_service_response(self) -> None:
        """Should generate correct response structure."""
        did_def = DIDDefinition(
            name="TestDID",
            type=TypeDefinition(base=BaseType.U16),
            access="read",
        )

        service = generate_read_did_service(0x1234, did_def, "DOP_Test")

        assert service.positive_response is not None
        assert len(service.positive_response.params) == 3  # SID, DID, Data
        # Check constant prefix: 62 12 34
        assert service.positive_response.constant_prefix == bytes([0x62, 0x12, 0x34])

    def test_read_service_with_sessions(self) -> None:
        """Should include session requirements."""
        did_def = DIDDefinition(
            name="ProtectedDID",
            type=TypeDefinition(base=BaseType.U8),
            access="read",
        )

        service = generate_read_did_service(
            0xF100,
            did_def,
            "DOP_Protected",
            sessions=("extended", "programming"),
        )

        assert service.required_sessions == ("extended", "programming")

    def test_read_service_with_security(self) -> None:
        """Should include security requirements."""
        did_def = DIDDefinition(
            name="SecureDID",
            type=TypeDefinition(base=BaseType.U8),
            access="read",
        )

        service = generate_read_did_service(
            0xF100,
            did_def,
            "DOP_Secure",
            security=("level1",),
        )

        assert service.required_security == ("level1",)


class TestGenerateWriteDidService:
    """Tests for generate_write_did_service."""

    def test_basic_write_service(self) -> None:
        """Should generate basic write service."""
        did_def = DIDDefinition(
            name="Config",
            type=TypeDefinition(base=BaseType.U8),
            access="write",
        )

        service = generate_write_did_service(
            did_id=0xF199,
            did_def=did_def,
            dop_name="DOP_Config",
        )

        assert service.short_name == "Write_Config"
        assert service.service_id == 0x2E
        assert service.service_type == IRServiceType.POS_RESPONSE

    def test_write_service_request(self) -> None:
        """Should generate correct request structure."""
        did_def = DIDDefinition(
            name="TestDID",
            type=TypeDefinition(base=BaseType.U16),
            access="write",
        )

        service = generate_write_did_service(0x1234, did_def, "DOP_Test")

        assert service.request is not None
        assert len(service.request.params) == 3  # SID, DID, Data
        # Check constant prefix: 2E 12 34
        assert service.request.constant_prefix == bytes([0x2E, 0x12, 0x34])

    def test_write_service_response(self) -> None:
        """Should generate correct response structure."""
        did_def = DIDDefinition(
            name="TestDID",
            type=TypeDefinition(base=BaseType.U16),
            access="write",
        )

        service = generate_write_did_service(0x1234, did_def, "DOP_Test")

        assert service.positive_response is not None
        assert len(service.positive_response.params) == 2  # SID, DID (no data)
        # Check constant prefix: 6E 12 34
        assert service.positive_response.constant_prefix == bytes([0x6E, 0x12, 0x34])


class TestGenerateRoutineServices:
    """Tests for generate_routine_services."""

    def test_start_only_routine(self) -> None:
        """Should generate only start service for start-only routine."""
        routine_def = RoutineDefinition(
            name="SelfTest",
            access="standard_read",
            operations=["start"],
        )

        services = generate_routine_services(0xFF00, routine_def)

        assert len(services) == 1
        assert services[0].short_name == "Start_SelfTest"

    def test_start_stop_routine(self) -> None:
        """Should generate start and stop services."""
        routine_def = RoutineDefinition(
            name="Calibration",
            access="standard_read",
            operations=["start", "stop"],
        )

        services = generate_routine_services(0xFF01, routine_def)

        assert len(services) == 2
        names = [s.short_name for s in services]
        assert "Start_Calibration" in names
        assert "Stop_Calibration" in names

    def test_all_operations_routine(self) -> None:
        """Should generate all three services."""
        routine_def = RoutineDefinition(
            name="DiagRoutine",
            access="standard_read",
            operations=["start", "stop", "result"],
        )

        services = generate_routine_services(0xFF02, routine_def)

        assert len(services) == 3
        names = [s.short_name for s in services]
        assert "Start_DiagRoutine" in names
        assert "Stop_DiagRoutine" in names
        assert "Result_DiagRoutine" in names

    def test_start_routine_service(self) -> None:
        """Should generate correct start routine service."""
        routine_def = RoutineDefinition(
            name="Test",
            access="standard_read",
            operations=["start"],
        )

        services = generate_routine_services(0x1234, routine_def)
        service = services[0]

        assert service.service_id == 0x31
        assert service.subfunction == 0x01
        assert service.service_type == IRServiceType.POS_RESPONSE_WITH_SUBFUNCTION
        # Request prefix: 31 01 12 34
        assert service.request.constant_prefix == bytes([0x31, 0x01, 0x12, 0x34])
        # Response prefix: 71 01 12 34
        assert service.positive_response.constant_prefix == bytes([0x71, 0x01, 0x12, 0x34])

    def test_stop_routine_service(self) -> None:
        """Should generate correct stop routine service."""
        routine_def = RoutineDefinition(
            name="Test",
            access="standard_read",
            operations=["stop"],
        )

        services = generate_routine_services(0x1234, routine_def)
        service = services[0]

        assert service.subfunction == 0x02
        assert service.request.constant_prefix == bytes([0x31, 0x02, 0x12, 0x34])
        assert service.positive_response.constant_prefix == bytes([0x71, 0x02, 0x12, 0x34])

    def test_result_routine_service(self) -> None:
        """Should generate correct result routine service."""
        routine_def = RoutineDefinition(
            name="Test",
            access="standard_read",
            operations=["result"],
        )

        services = generate_routine_services(0x1234, routine_def)
        service = services[0]

        assert service.subfunction == 0x03
        assert service.request.constant_prefix == bytes([0x31, 0x03, 0x12, 0x34])
        assert service.positive_response.constant_prefix == bytes([0x71, 0x03, 0x12, 0x34])

    def test_routine_with_sessions(self) -> None:
        """Should include session requirements."""
        routine_def = RoutineDefinition(
            name="Test",
            access="standard_read",
            operations=["start"],
        )

        services = generate_routine_services(
            0xFF00,
            routine_def,
            sessions=("extended",),
        )

        assert services[0].required_sessions == ("extended",)

    def test_routine_with_security(self) -> None:
        """Should include security requirements."""
        routine_def = RoutineDefinition(
            name="Test",
            access="standard_read",
            operations=["start"],
        )

        services = generate_routine_services(
            0xFF00,
            routine_def,
            security=("level1", "level3"),
        )

        assert services[0].required_security == ("level1", "level3")
