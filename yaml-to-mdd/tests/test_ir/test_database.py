"""Tests for IR database model."""

from yaml_to_mdd.ir.database import IRDatabase, IRMatchingParameter, IRVariant
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


class TestIRMatchingParameter:
    """Tests for IRMatchingParameter dataclass."""

    def test_create_matching_parameter(self) -> None:
        """Should create matching parameter with required fields."""
        param = IRMatchingParameter(
            expected_value="0xFF0000",
            diag_service_ref="Identification_Read",
            out_param_ref="Identification",
        )
        assert param.expected_value == "0xFF0000"
        assert param.diag_service_ref == "Identification_Read"
        assert param.out_param_ref == "Identification"
        assert param.use_physical_addressing is True  # default

    def test_matching_parameter_with_physical_addressing(self) -> None:
        """Should create matching parameter with physical addressing disabled."""
        param = IRMatchingParameter(
            expected_value="0x01",
            diag_service_ref="ReadDID_F1A0",
            out_param_ref="HardwareVersion",
            use_physical_addressing=False,
        )
        assert param.use_physical_addressing is False

    def test_matching_parameter_is_immutable(self) -> None:
        """Should be immutable (frozen dataclass)."""
        param = IRMatchingParameter(
            expected_value="0xFF",
            diag_service_ref="Service1",
            out_param_ref="Param1",
        )
        # frozen dataclass should raise FrozenInstanceError
        import pytest

        with pytest.raises(AttributeError):
            param.expected_value = "0x00"  # type: ignore


class TestIRVariant:
    """Tests for IRVariant dataclass."""

    def test_create_variant(self) -> None:
        """Should create variant with name."""
        variant = IRVariant(short_name="Boot_Variant")
        assert variant.short_name == "Boot_Variant"
        assert variant.is_base_variant is False  # default
        assert variant.matching_parameters == ()  # default

    def test_create_base_variant(self) -> None:
        """Should create base variant."""
        variant = IRVariant(
            short_name="FLXC1000",
            is_base_variant=True,
        )
        assert variant.is_base_variant is True

    def test_variant_with_matching_parameters(self) -> None:
        """Should create variant with matching parameters."""
        params = (
            IRMatchingParameter(
                expected_value="0xFF0000",
                diag_service_ref="Identification_Read",
                out_param_ref="Identification",
            ),
        )
        variant = IRVariant(
            short_name="Boot_Variant",
            matching_parameters=params,
        )
        assert len(variant.matching_parameters) == 1
        assert variant.matching_parameters[0].expected_value == "0xFF0000"

    def test_variant_with_multiple_matching_parameters(self) -> None:
        """Should support multiple matching parameters."""
        params = (
            IRMatchingParameter("0xFF0000", "Service1", "Param1"),
            IRMatchingParameter(
                "0x01", "Service2", "Param2", use_physical_addressing=False
            ),
        )
        variant = IRVariant(
            short_name="Complex_Variant",
            matching_parameters=params,
        )
        assert len(variant.matching_parameters) == 2

    def test_variant_is_immutable(self) -> None:
        """Should be immutable (frozen dataclass)."""
        variant = IRVariant(short_name="Test")
        import pytest

        with pytest.raises(AttributeError):
            variant.short_name = "Modified"  # type: ignore


class TestIRDatabaseVariants:
    """Tests for IRDatabase variant management."""

    def test_add_variant(self) -> None:
        """Should add variant to database."""
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")
        variant = IRVariant(short_name="Boot_Variant")

        db.add_variant(variant)

        assert len(db.variants) == 1
        assert db.variants[0].short_name == "Boot_Variant"

    def test_add_multiple_variants(self) -> None:
        """Should add multiple variants."""
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")

        db.add_variant(IRVariant(short_name="Base", is_base_variant=True))
        db.add_variant(IRVariant(short_name="Boot_Variant"))
        db.add_variant(IRVariant(short_name="App_Variant"))

        assert len(db.variants) == 3

    def test_variants_preserved_order(self) -> None:
        """Should preserve insertion order of variants."""
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")

        db.add_variant(IRVariant(short_name="First"))
        db.add_variant(IRVariant(short_name="Second"))
        db.add_variant(IRVariant(short_name="Third"))

        assert db.variants[0].short_name == "First"
        assert db.variants[1].short_name == "Second"
        assert db.variants[2].short_name == "Third"

    def test_variant_with_detection_pattern(self) -> None:
        """Should add variant with full detection pattern."""
        db = IRDatabase(ecu_name="FLXC1000", revision="1.0.0")

        # Add service that variant detection references
        db.add_service(
            IRDiagService(
                short_name="Identification_Read",
                service_id=0x22,
            )
        )

        # Add variant with detection pattern
        variant = IRVariant(
            short_name="FLXC1000_Boot_Variant",
            matching_parameters=(
                IRMatchingParameter(
                    expected_value="0xFF0000",
                    diag_service_ref="Identification_Read",
                    out_param_ref="Identification",
                ),
            ),
        )
        db.add_variant(variant)

        assert len(db.variants) == 1
        assert (
            db.variants[0].matching_parameters[0].diag_service_ref
            == "Identification_Read"
        )
