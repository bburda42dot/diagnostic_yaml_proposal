"""Tests for YamlToIRTransformer."""

from typing import Any

from yaml_to_mdd.ir.database import IRDatabase
from yaml_to_mdd.ir.types import IRCompuCategory, IRDataType
from yaml_to_mdd.models.root import DiagnosticDescription
from yaml_to_mdd.transform import YamlToIRTransformer


class TestYamlToIRTransformerBasics:
    """Basic transformer tests."""

    def test_create_transformer(self) -> None:
        """Should create transformer instance."""
        transformer = YamlToIRTransformer()
        assert transformer is not None

    def test_transform_minimal_document(self, valid_base_data: dict[str, Any]) -> None:
        """Should transform minimal document."""
        doc = DiagnosticDescription.model_validate(valid_base_data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        assert isinstance(result, IRDatabase)
        assert result.ecu_name == "ECM_V1"

    def test_transform_creates_standard_dops(self, valid_base_data: dict[str, Any]) -> None:
        """Should create standard DOPs for minimal document."""
        doc = DiagnosticDescription.model_validate(valid_base_data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        # Standard DOPs should exist
        did_dop = result.get_dop("DOP_DID")
        rid_dop = result.get_dop("DOP_RID")

        assert did_dop is not None
        assert rid_dop is not None
        assert did_dop.diag_coded_type.base_data_type == IRDataType.A_UINT_32


class TestYamlToIRTransformerTypes:
    """Tests for type processing."""

    def test_transform_with_types(self, valid_base_data: dict[str, Any]) -> None:
        """Should convert types to DOPs."""
        data = {
            **valid_base_data,
            "types": {
                "temperature": {
                    "base": "u16",
                },
            },
        }
        doc = DiagnosticDescription.model_validate(data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        dop = result.get_dop("temperature")
        assert dop is not None
        assert dop.short_name == "temperature"
        assert dop.diag_coded_type.base_data_type == IRDataType.A_UINT_32

    def test_transform_with_scaled_type(self, valid_base_data: dict[str, Any]) -> None:
        """Should convert scaled types correctly."""
        data = {
            **valid_base_data,
            "types": {
                "temperature_celsius": {
                    "base": "u8",
                    "offset": -40.0,
                    "scale": 1.0,
                },
            },
        }
        doc = DiagnosticDescription.model_validate(data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        dop = result.get_dop("temperature_celsius")
        assert dop is not None
        assert dop.compu_method is not None
        assert dop.compu_method.category == IRCompuCategory.LINEAR

    def test_transform_with_enum_type(self, valid_base_data: dict[str, Any]) -> None:
        """Should convert enum types correctly."""
        data = {
            **valid_base_data,
            "types": {
                "status": {
                    "base": "u8",
                    "enum": {0: "OFF", 1: "ON", 2: "ERROR"},
                },
            },
        }
        doc = DiagnosticDescription.model_validate(data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        dop = result.get_dop("status")
        assert dop is not None
        assert dop.compu_method is not None
        assert dop.compu_method.category == IRCompuCategory.TEXT_TABLE

    def test_transform_preserves_multiple_types(self, valid_base_data: dict[str, Any]) -> None:
        """Should preserve all types in conversion."""
        data = {
            **valid_base_data,
            "types": {
                "type_a": {"base": "u8"},
                "type_b": {"base": "u16"},
                "type_c": {"base": "u32"},
            },
        }
        doc = DiagnosticDescription.model_validate(data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        assert result.get_dop("type_a") is not None
        assert result.get_dop("type_b") is not None
        assert result.get_dop("type_c") is not None


class TestYamlToIRTransformerDIDs:
    """Tests for DID processing."""

    def test_transform_with_read_did(self, valid_base_data: dict[str, Any]) -> None:
        """Should generate read service for read DID."""
        data = {
            **valid_base_data,
            "dids": {
                "0xF190": {
                    "name": "VIN",
                    "type": {"base": "ascii", "length": 17},
                    "access": "read",
                },
            },
        }
        doc = DiagnosticDescription.model_validate(data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        service = result.get_service("Read_VIN")
        assert service is not None
        assert service.service_id == 0x22

    def test_transform_with_write_did(self, valid_base_data: dict[str, Any]) -> None:
        """Should generate write service for write DID."""
        data = {
            **valid_base_data,
            "dids": {
                "0xF199": {
                    "name": "Config",
                    "type": {"base": "u8"},
                    "access": "write",
                },
            },
        }
        doc = DiagnosticDescription.model_validate(data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        service = result.get_service("Write_Config")
        assert service is not None
        assert service.service_id == 0x2E

    def test_transform_with_readwrite_did(self, valid_base_data: dict[str, Any]) -> None:
        """Should generate both services for read-write DID."""
        data = {
            **valid_base_data,
            "dids": {
                "0xF100": {
                    "name": "Setting",
                    "type": {"base": "u8"},
                    "access": "read_write",
                },
            },
        }
        doc = DiagnosticDescription.model_validate(data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        read_service = result.get_service("Read_Setting")
        write_service = result.get_service("Write_Setting")

        assert read_service is not None
        assert write_service is not None

    def test_transform_did_uses_type_reference(self, valid_base_data: dict[str, Any]) -> None:
        """Should use type reference when DID references defined type."""
        data = {
            **valid_base_data,
            "types": {
                "vin_type": {"base": "ascii", "length": 17},
            },
            "dids": {
                "0xF190": {
                    "name": "VIN",
                    "type": "vin_type",
                    "access": "read",
                },
            },
        }
        doc = DiagnosticDescription.model_validate(data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        # Type should exist
        assert result.get_dop("vin_type") is not None
        # Service should be generated
        assert result.get_service("Read_VIN") is not None


class TestYamlToIRTransformerRoutines:
    """Tests for routine processing."""

    def test_transform_with_start_routine(self, valid_base_data: dict[str, Any]) -> None:
        """Should generate start service for routine."""
        data = {
            **valid_base_data,
            "routines": {
                "0xFF00": {
                    "name": "SelfTest",
                    "access": "standard_read",
                    "operations": ["start"],
                },
            },
        }
        doc = DiagnosticDescription.model_validate(data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        service = result.get_service("Start_SelfTest")
        assert service is not None
        assert service.service_id == 0x31
        assert service.subfunction == 0x01

    def test_transform_with_all_operations(self, valid_base_data: dict[str, Any]) -> None:
        """Should generate all services for full routine."""
        data = {
            **valid_base_data,
            "routines": {
                "0xFF01": {
                    "name": "DiagRoutine",
                    "access": "standard_read",
                    "operations": ["start", "stop", "result"],
                },
            },
        }
        doc = DiagnosticDescription.model_validate(data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        assert result.get_service("Start_DiagRoutine") is not None
        assert result.get_service("Stop_DiagRoutine") is not None
        assert result.get_service("Result_DiagRoutine") is not None


class TestYamlToIRTransformerComplex:
    """Complex integration tests."""

    def test_transform_complete_document(self, valid_base_data: dict[str, Any]) -> None:
        """Should transform document with types, DIDs, and routines."""
        data = {
            **valid_base_data,
            "types": {
                "temperature": {
                    "base": "u8",
                    "offset": -40.0,
                    "scale": 1.0,
                },
                "status_enum": {
                    "base": "u8",
                    "enum": {0: "OFF", 1: "ON"},
                },
            },
            "dids": {
                "0xF100": {
                    "name": "Temperature",
                    "type": "temperature",
                    "access": "read",
                },
                "0xF101": {
                    "name": "Status",
                    "type": "status_enum",
                    "access": "read_write",
                },
            },
            "routines": {
                "0xFF00": {
                    "name": "Calibration",
                    "access": "standard_read",
                    "operations": ["start", "stop"],
                },
            },
        }
        doc = DiagnosticDescription.model_validate(data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        # Check database properties
        assert result.ecu_name == "ECM_V1"

        # Check types converted
        assert result.get_dop("temperature") is not None
        assert result.get_dop("status_enum") is not None

        # Check DID services
        assert result.get_service("Read_Temperature") is not None
        assert result.get_service("Read_Status") is not None
        assert result.get_service("Write_Status") is not None

        # Check routine services
        assert result.get_service("Start_Calibration") is not None
        assert result.get_service("Stop_Calibration") is not None

        # Check standard DOPs always exist
        assert result.get_dop("DOP_DID") is not None
        assert result.get_dop("DOP_RID") is not None

    def test_transform_idempotent(self, valid_base_data: dict[str, Any]) -> None:
        """Transforming same document should produce equivalent results."""
        data = {
            **valid_base_data,
            "dids": {
                "0xF100": {
                    "name": "Test",
                    "type": {"base": "u8"},
                    "access": "read",
                },
            },
        }
        doc = DiagnosticDescription.model_validate(data)
        transformer = YamlToIRTransformer()

        result1 = transformer.transform(doc)
        result2 = transformer.transform(doc)

        assert result1.ecu_name == result2.ecu_name
        assert len(result1.dops) == len(result2.dops)
        assert len(result1.services) == len(result2.services)

    def test_transform_with_sessions(self, valid_base_data: dict[str, Any]) -> None:
        """Should capture session mappings."""
        doc = DiagnosticDescription.model_validate(valid_base_data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        assert "default" in result.sessions
        assert "programming" in result.sessions
        assert "extended" in result.sessions
        assert result.sessions["default"] == 1
        assert result.sessions["programming"] == 2
        assert result.sessions["extended"] == 3

    def test_transform_with_security(self, valid_base_data_with_security: dict[str, Any]) -> None:
        """Should capture security level mappings."""
        doc = DiagnosticDescription.model_validate(valid_base_data_with_security)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        assert "level1" in result.security_levels
        assert result.security_levels["level1"] == 1


class TestYamlToIRTransformerMemory:
    """Tests for memory configuration processing."""

    def test_transform_without_memory(self, valid_base_data: dict[str, Any]) -> None:
        """Should handle document without memory config."""
        doc = DiagnosticDescription.model_validate(valid_base_data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        assert result.memory_regions == []
        assert result.data_blocks == []

    def test_transform_with_memory_region(self, valid_base_data: dict[str, Any]) -> None:
        """Should convert memory regions to IR."""
        data = {
            **valid_base_data,
            "memory": {
                "regions": {
                    "flash": {
                        "name": "flash",
                        "start_address": "0x00100000",
                        "size": "0x00100000",
                        "access": "read_write",
                    },
                },
            },
        }
        doc = DiagnosticDescription.model_validate(data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        assert len(result.memory_regions) == 1
        region = result.memory_regions[0]
        assert region.name == "flash"
        assert region.start_address == 0x00100000
        assert region.size == 0x00100000
        assert region.access == "read_write"
        assert region.address_bytes == 4  # default
        assert region.length_bytes == 4  # default

    def test_transform_with_memory_region_custom_format(
        self, valid_base_data: dict[str, Any]
    ) -> None:
        """Should use custom address format for memory region."""
        data = {
            **valid_base_data,
            "memory": {
                "regions": {
                    "flash": {
                        "name": "flash",
                        "start_address": "0x00100000",
                        "size": "0x00100000",
                        "address_format": {
                            "address_bytes": 3,
                            "length_bytes": 2,
                        },
                    },
                },
            },
        }
        doc = DiagnosticDescription.model_validate(data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        region = result.memory_regions[0]
        assert region.address_bytes == 3
        assert region.length_bytes == 2

    def test_transform_with_memory_region_default_format(
        self, valid_base_data: dict[str, Any]
    ) -> None:
        """Should use config default format when region has no format."""
        data = {
            **valid_base_data,
            "memory": {
                "default_address_format": {
                    "address_bytes": 2,
                    "length_bytes": 3,
                },
                "regions": {
                    "flash": {
                        "name": "flash",
                        "start_address": "0x00100000",
                        "size": "0x00100000",
                    },
                },
            },
        }
        doc = DiagnosticDescription.model_validate(data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        region = result.memory_regions[0]
        assert region.address_bytes == 2
        assert region.length_bytes == 3

    def test_transform_with_memory_region_sessions(self, valid_base_data: dict[str, Any]) -> None:
        """Should convert session list to tuple."""
        data = {
            **valid_base_data,
            "memory": {
                "regions": {
                    "flash": {
                        "name": "flash",
                        "start_address": "0x00100000",
                        "size": "0x00100000",
                        "session": ["extended", "programming"],
                    },
                },
            },
        }
        doc = DiagnosticDescription.model_validate(data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        region = result.memory_regions[0]
        assert region.sessions == ("extended", "programming")

    def test_transform_with_memory_region_single_session(
        self, valid_base_data: dict[str, Any]
    ) -> None:
        """Should convert single session string to tuple."""
        data = {
            **valid_base_data,
            "memory": {
                "regions": {
                    "flash": {
                        "name": "flash",
                        "start_address": "0x00100000",
                        "size": "0x00100000",
                        "session": "extended",
                    },
                },
            },
        }
        doc = DiagnosticDescription.model_validate(data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        region = result.memory_regions[0]
        assert region.sessions == ("extended",)

    def test_transform_with_data_block(self, valid_base_data: dict[str, Any]) -> None:
        """Should convert data blocks to IR."""
        data = {
            **valid_base_data,
            "memory": {
                "data_blocks": {
                    "firmware": {
                        "name": "firmware",
                        "memory_address": "0x00100000",
                        "memory_size": "0x00080000",
                        "type": "download",
                        "format": "compressed",
                    },
                },
            },
        }
        doc = DiagnosticDescription.model_validate(data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        assert len(result.data_blocks) == 1
        block = result.data_blocks[0]
        assert block.name == "firmware"
        assert block.memory_address == 0x00100000
        assert block.memory_size == 0x00080000
        assert block.block_type == "download"
        assert block.data_format == 0x10  # compressed

    def test_transform_with_data_block_all_formats(self, valid_base_data: dict[str, Any]) -> None:
        """Should convert all data format types correctly."""
        data = {
            **valid_base_data,
            "memory": {
                "data_blocks": {
                    "raw_block": {
                        "name": "raw_block",
                        "memory_address": "0x00100000",
                        "memory_size": "0x1000",
                        "format": "raw",
                    },
                    "encrypted_block": {
                        "name": "encrypted_block",
                        "memory_address": "0x00200000",
                        "memory_size": "0x1000",
                        "format": "encrypted",
                    },
                    "compressed_block": {
                        "name": "compressed_block",
                        "memory_address": "0x00300000",
                        "memory_size": "0x1000",
                        "format": "compressed",
                    },
                    "enc_comp_block": {
                        "name": "enc_comp_block",
                        "memory_address": "0x00400000",
                        "memory_size": "0x1000",
                        "format": "encrypted_compressed",
                    },
                },
            },
        }
        doc = DiagnosticDescription.model_validate(data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        formats = {b.name: b.data_format for b in result.data_blocks}
        assert formats["raw_block"] == 0x00
        assert formats["encrypted_block"] == 0x01
        assert formats["compressed_block"] == 0x10
        assert formats["enc_comp_block"] == 0x11

    def test_transform_with_full_memory_config(self, valid_base_data: dict[str, Any]) -> None:
        """Should convert complete memory configuration."""
        data = {
            **valid_base_data,
            "memory": {
                "default_address_format": {
                    "address_bytes": 4,
                    "length_bytes": 4,
                },
                "regions": {
                    "flash": {
                        "name": "flash",
                        "start_address": "0x00100000",
                        "size": "0x00100000",
                        "access": "read_write",
                        "security_level": "level1",
                    },
                    "ram": {
                        "name": "ram",
                        "start_address": "0x20000000",
                        "size": "0x00040000",
                        "access": "read",
                    },
                },
                "data_blocks": {
                    "firmware": {
                        "name": "firmware",
                        "memory_address": "0x00100000",
                        "memory_size": "0x00080000",
                        "max_block_length": "0x0FFA",
                        "security_level": "level1",
                        "session": "programming",
                    },
                },
            },
        }
        doc = DiagnosticDescription.model_validate(data)
        transformer = YamlToIRTransformer()

        result = transformer.transform(doc)

        # Check regions
        assert len(result.memory_regions) == 2
        flash = next(r for r in result.memory_regions if r.name == "flash")
        assert flash.security_level == "level1"

        # Check data blocks
        assert len(result.data_blocks) == 1
        firmware = result.data_blocks[0]
        assert firmware.max_block_length == 0x0FFA
        assert firmware.security_level == "level1"
        assert firmware.session == "programming"
