"""Tests for IR database model."""

from yaml_to_mdd.ir.database import IRDatabase
from yaml_to_mdd.ir.services import IRDiagService, IRServiceType
from yaml_to_mdd.ir.types import IRDOP


class TestIRDatabaseCreation:
    """Tests for IRDatabase creation."""

    def test_create_empty_database(self) -> None:
        """Should create empty database."""
        db = IRDatabase(
            ecu_name="TestECU",
            revision="1.0.0",
        )
        assert db.ecu_name == "TestECU"
        assert db.revision == "1.0.0"
        assert len(db.dops) == 0
        assert len(db.services) == 0

    def test_create_database_with_metadata(self) -> None:
        """Should create database with full metadata."""
        db = IRDatabase(
            ecu_name="EngineECU",
            revision="2.1.0",
            author="Test Author",
            description="Engine Control Unit diagnostics",
        )
        assert db.author == "Test Author"
        assert db.description == "Engine Control Unit diagnostics"

    def test_default_schema_version(self) -> None:
        """Should have correct default schema version."""
        db = IRDatabase(ecu_name="Test", revision="1.0.0")
        assert db.schema_version == "opensovd.cda.diagdesc/v1"

    def test_custom_schema_version(self) -> None:
        """Should allow custom schema version."""
        db = IRDatabase(
            ecu_name="Test",
            revision="1.0.0",
            schema_version="custom/v2",
        )
        assert db.schema_version == "custom/v2"


class TestIRDatabaseDOPs:
    """Tests for IRDatabase DOP management."""

    def test_add_dop(self) -> None:
        """Should add DOP to database."""
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")
        dop = IRDOP(short_name="EngineSpeed")

        db.add_dop(dop)

        assert "EngineSpeed" in db.dops
        assert db.get_dop("EngineSpeed") == dop

    def test_add_multiple_dops(self) -> None:
        """Should add multiple DOPs."""
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")
        db.add_dop(IRDOP(short_name="DOP1"))
        db.add_dop(IRDOP(short_name="DOP2"))
        db.add_dop(IRDOP(short_name="DOP3"))

        assert len(db.dops) == 3

    def test_get_nonexistent_dop(self) -> None:
        """Should return None for nonexistent DOP."""
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")
        assert db.get_dop("NonExistent") is None

    def test_get_all_dops(self) -> None:
        """Should return all DOPs as list."""
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")
        db.add_dop(IRDOP(short_name="DOP1"))
        db.add_dop(IRDOP(short_name="DOP2"))

        dops = db.get_all_dops()

        assert len(dops) == 2
        assert all(isinstance(d, IRDOP) for d in dops)

    def test_overwrite_dop(self) -> None:
        """Adding DOP with same name should overwrite."""
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")
        db.add_dop(IRDOP(short_name="DOP1", long_name="First"))
        db.add_dop(IRDOP(short_name="DOP1", long_name="Second"))

        assert len(db.dops) == 1
        assert db.get_dop("DOP1").long_name == "Second"  # type: ignore[union-attr]


class TestIRDatabaseServices:
    """Tests for IRDatabase service management."""

    def test_add_service(self) -> None:
        """Should add service to database."""
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")
        service = IRDiagService(
            short_name="ReadEngineSpeed",
            service_id=0x22,
        )

        db.add_service(service)

        assert "ReadEngineSpeed" in db.services
        assert db.get_service("ReadEngineSpeed") == service

    def test_add_multiple_services(self) -> None:
        """Should add multiple services."""
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")
        db.add_service(IRDiagService(short_name="Svc1", service_id=0x22))
        db.add_service(IRDiagService(short_name="Svc2", service_id=0x2E))

        assert len(db.services) == 2

    def test_get_nonexistent_service(self) -> None:
        """Should return None for nonexistent service."""
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")
        assert db.get_service("NonExistent") is None

    def test_get_all_services(self) -> None:
        """Should return all services as list."""
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")
        db.add_service(IRDiagService(short_name="Svc1", service_id=0x22))
        db.add_service(IRDiagService(short_name="Svc2", service_id=0x2E))

        services = db.get_all_services()

        assert len(services) == 2
        assert all(isinstance(s, IRDiagService) for s in services)


class TestIRDatabaseSessions:
    """Tests for IRDatabase session management."""

    def test_add_sessions(self) -> None:
        """Should store session mappings."""
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")
        db.sessions["default"] = 0x01
        db.sessions["extended"] = 0x03
        db.sessions["programming"] = 0x02

        assert db.sessions["default"] == 0x01
        assert db.sessions["extended"] == 0x03
        assert len(db.sessions) == 3


class TestIRDatabaseSecurityLevels:
    """Tests for IRDatabase security level management."""

    def test_add_security_levels(self) -> None:
        """Should store security level mappings."""
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")
        db.security_levels["level1"] = 1
        db.security_levels["level3"] = 3

        assert db.security_levels["level1"] == 1
        assert db.security_levels["level3"] == 3


class TestIRDatabaseDIDMappings:
    """Tests for IRDatabase DID to service mappings."""

    def test_did_read_mapping(self) -> None:
        """Should store DID to read service mapping."""
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")
        db.did_read_services[0xF190] = "ReadVIN"
        db.did_read_services[0xF191] = "ReadECUSerialNumber"

        assert db.did_read_services[0xF190] == "ReadVIN"
        assert len(db.did_read_services) == 2

    def test_did_write_mapping(self) -> None:
        """Should store DID to write service mapping."""
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")
        db.did_write_services[0xF199] = "WriteVIN"

        assert db.did_write_services[0xF199] == "WriteVIN"


class TestIRDatabaseRoutineMappings:
    """Tests for IRDatabase routine to service mappings."""

    def test_routine_mapping(self) -> None:
        """Should store routine to service mapping."""
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")
        db.routine_services[0xFF00] = ["StartRoutine_FF00", "StopRoutine_FF00"]

        assert len(db.routine_services[0xFF00]) == 2
        assert "StartRoutine_FF00" in db.routine_services[0xFF00]


class TestIRDatabaseIntegration:
    """Integration tests for IRDatabase."""

    def test_complete_database(self) -> None:
        """Should create complete database with all components."""
        db = IRDatabase(
            ecu_name="EngineECU",
            revision="1.2.3",
            author="Developer",
            description="Complete test database",
        )

        # Add DOPs
        db.add_dop(IRDOP(short_name="UInt8"))
        db.add_dop(IRDOP(short_name="UInt16"))

        # Add services
        db.add_service(
            IRDiagService(
                short_name="ReadDID_F190",
                service_id=0x22,
                service_type=IRServiceType.POS_RESPONSE,
                required_sessions=("default", "extended"),
            )
        )

        # Add sessions
        db.sessions["default"] = 0x01
        db.sessions["extended"] = 0x03

        # Add security levels
        db.security_levels["level1"] = 1

        # Add DID mapping
        db.did_read_services[0xF190] = "ReadDID_F190"

        # Verify
        assert len(db.get_all_dops()) == 2
        assert len(db.get_all_services()) == 1
        assert len(db.sessions) == 2
        assert len(db.security_levels) == 1
        assert db.did_read_services[0xF190] == "ReadDID_F190"

    def test_database_is_mutable(self) -> None:
        """Database should be mutable for incremental building."""
        db = IRDatabase(ecu_name="Test", revision="1.0.0")

        # Should be able to modify attributes
        db.ecu_name = "ModifiedECU"
        db.author = "New Author"

        assert db.ecu_name == "ModifiedECU"
        assert db.author == "New Author"
