"""Sample YAML data for integration testing.

This module provides reusable YAML data structures for testing the
complete conversion pipeline from YAML -> Pydantic -> IR -> FlatBuffers -> MDD.
"""

from typing import Any

# Minimal valid YAML structure - smallest possible valid document
MINIMAL_YAML: dict[str, Any] = {
    "schema": "opensovd.cda.diagdesc/v1",
    "meta": {
        "author": "Test Author",
        "domain": "Powertrain",
        "created": "2024-01-15",
        "revision": "1.0.0",
        "description": "Minimal test ECU",
    },
    "ecu": {
        "id": "MINIMAL_ECU",
        "name": "Minimal Engine Control Module",
        "addressing": {
            "doip": {
                "ip": "192.168.1.1",
                "logical_address": "0x0E80",
                "tester_address": "0x0E00",
            },
        },
    },
    "sessions": {
        "default": {"id": "0x01"},
    },
    "services": {
        "diagnosticSessionControl": {"enabled": True},
    },
    "access_patterns": {
        "default_access": {
            "sessions": ["default"],
            "security": "none",
            "authentication": "none",
        },
    },
}

# Full-featured YAML with all sections populated
FULL_YAML: dict[str, Any] = {
    "schema": "opensovd.cda.diagdesc/v1",
    "meta": {
        "author": "Integration Test Suite",
        "domain": "Powertrain",
        "created": "2024-01-15",
        "revision": "2.5.0",
        "description": "Full-featured integration test ECU",
    },
    "ecu": {
        "id": "FULL_ECU",
        "name": "Full Feature Engine Control Module",
        "addressing": {
            "doip": {
                "ip": "192.168.1.100",
                "logical_address": "0x0E80",
                "tester_address": "0x0E00",
            },
        },
    },
    "sessions": {
        "default": {"id": "0x01"},
        "programming": {"id": "0x02"},
        "extended": {"id": "0x03"},
    },
    "security": {
        "level1": {
            "level": 1,
            "seed_request": "0x01",
            "key_send": "0x02",
            "seed_size": 4,
            "key_size": 4,
            "algorithm": "xor",
            "max_attempts": 3,
            "delay_on_fail_ms": 10000,
            "allowed_sessions": ["extended"],
        },
        "level2": {
            "level": 2,
            "seed_request": "0x03",
            "key_send": "0x04",
            "seed_size": 4,
            "key_size": 4,
            "algorithm": "aes128",
            "max_attempts": 3,
            "delay_on_fail_ms": 10000,
            "allowed_sessions": ["programming"],
        },
    },
    "services": {
        "diagnosticSessionControl": {"enabled": True},
        "readDataByIdentifier": {"enabled": True},
        "writeDataByIdentifier": {"enabled": True},
        "securityAccess": {"enabled": True},
        "routineControl": {"enabled": True},
        "clearDiagnosticInformation": {"enabled": True},
        "readDTCInformation": {"enabled": True},
    },
    "access_patterns": {
        "standard_read": {
            "sessions": ["default", "extended"],
            "security": "none",
            "authentication": "none",
        },
        "standard_write": {
            "sessions": ["extended"],
            "security": ["level1"],
            "authentication": "none",
        },
        "programming_access": {
            "sessions": ["programming"],
            "security": ["level2"],
            "authentication": "none",
        },
    },
    "types": {
        "VehicleSpeed": {
            "base": "u16",
            "unit": "km/h",
            "min": 0,
            "max": 300,
            "scale": 0.01,
            "offset": 0,
        },
        "EngineRPM": {
            "base": "u16",
            "unit": "rpm",
            "min": 0,
            "max": 10000,
        },
        "TemperatureC": {
            "base": "i16",
            "unit": "°C",
            "min": -40,
            "max": 215,
            "offset": -40,
        },
        "SoftwareVersion": {
            "base": "struct",
            "fields": [
                {"name": "major", "type": "u8"},
                {"name": "minor", "type": "u8"},
                {"name": "patch", "type": "u8"},
            ],
        },
    },
    "dids": {
        "0xF190": {
            "name": "VehicleIdentificationNumber",
            "description": "17-character VIN",
            "access": "read",
            "type": {"base": "ascii", "length": 17},
            "access_pattern": "standard_read",
        },
        "0xF191": {
            "name": "HardwareVersion",
            "description": "ECU hardware version",
            "access": "read",
            "type": "SoftwareVersion",
            "access_pattern": "standard_read",
        },
        "0xF192": {
            "name": "SoftwareVersion",
            "description": "ECU software version",
            "access": "read",
            "type": "SoftwareVersion",
            "access_pattern": "standard_read",
        },
        "0x0100": {
            "name": "EngineSpeed",
            "description": "Current engine speed",
            "access": "read",
            "type": "EngineRPM",
            "access_pattern": "standard_read",
        },
        "0x0101": {
            "name": "VehicleSpeed",
            "description": "Current vehicle speed",
            "access": "read",
            "type": "VehicleSpeed",
            "access_pattern": "standard_read",
        },
        "0x0200": {
            "name": "ConfigParam1",
            "description": "Configurable parameter 1",
            "access": "read_write",
            "type": {"base": "u32"},
            "access_pattern": "standard_write",
        },
    },
    "routines": {
        "0xFF00": {
            "name": "SelfTest",
            "description": "Execute ECU self-test",
            "operations": ["start", "stop", "result"],
            "access": "programming_access",
        },
        "0xFF01": {
            "name": "ClearLearning",
            "description": "Clear adaptive learning values",
            "operations": ["start"],
            "access": "programming_access",
        },
    },
    "dtc_config": {
        "default_snapshots": {
            "standard_snapshot": {
                "record_number": 1,
                "description": "Standard failure snapshot",
                "dids": ["0x0100", "0x0101"],
            },
        },
        "default_extended_data": {
            "occurrence_counter": {
                "record_number": 1,
                "name": "OccurrenceCounter",
                "type": "u8",
            },
        },
    },
    "dtcs": {
        "0x010100": {
            "name": "EngineOverheat",
            "description": "Engine coolant temperature too high",
            "severity": 1,
            "functional_unit": 1,
        },
        "0x010200": {
            "name": "LowOilPressure",
            "description": "Engine oil pressure below threshold",
            "severity": 1,
            "functional_unit": 1,
        },
        "0x020100": {
            "name": "TransmissionSlip",
            "description": "Transmission clutch slip detected",
            "severity": 3,
            "functional_unit": 2,
        },
    },
}

# YAML with intentional validation errors for negative testing
YAML_WITH_ERRORS: dict[str, Any] = {
    "schema": "opensovd.cda.diagdesc/v1",
    "meta": {
        "author": "Error Test",
        "domain": "Powertrain",
        "created": "2024-01-15",
        "revision": "1.0.0",
        # Missing description is OK, but let's put valid meta
    },
    "ecu": {
        "id": "ERROR_ECU",
        "name": "Error Test ECU",
        "addressing": {
            "doip": {
                "ip": "192.168.1.1",
                "logical_address": "0x0E80",
                "tester_address": "0x0E00",
            },
        },
    },
    "sessions": {
        "default": {"id": "0x01"},
    },
    "services": {
        "diagnosticSessionControl": {"enabled": True},
    },
    # Missing access_patterns - this is required now based on schema
    # This should trigger validation warning/error
}

# YAML with invalid schema version for negative testing
YAML_INVALID_SCHEMA: dict[str, Any] = {
    "schema": "invalid/v999",  # Invalid schema version
    "meta": {
        "author": "Invalid Schema Test",
        "domain": "Powertrain",
        "created": "2024-01-15",
        "revision": "1.0.0",
    },
    "ecu": {
        "id": "INVALID_ECU",
        "name": "Invalid Test ECU",
        "addressing": {
            "doip": {
                "ip": "192.168.1.1",
                "logical_address": "0x0E80",
                "tester_address": "0x0E00",
            },
        },
    },
    "sessions": {
        "default": {"id": "0x01"},
    },
    "services": {
        "diagnosticSessionControl": {"enabled": True},
    },
    "access_patterns": {
        "default": {
            "sessions": ["default"],
            "security": "none",
            "authentication": "none",
        },
    },
}

# YAML with memory configuration for upload/download testing
YAML_WITH_MEMORY: dict[str, Any] = {
    "schema": "opensovd.cda.diagdesc/v1",
    "meta": {
        "author": "Memory Test Author",
        "domain": "Powertrain",
        "created": "2024-01-15",
        "revision": "1.0.0",
        "description": "ECU with memory configuration",
    },
    "ecu": {
        "id": "MEMORY_ECU",
        "name": "Memory Test ECU",
        "addressing": {
            "doip": {
                "ip": "192.168.1.1",
                "logical_address": "0x0E80",
                "tester_address": "0x0E00",
            },
        },
    },
    "sessions": {
        "default": {"id": "0x01"},
        "programming": {"id": "0x02"},
    },
    "security": {
        "flash_access": {
            "level": 1,
            "seed_request": "0x01",
            "key_send": "0x02",
            "seed_size": 4,
            "key_size": 4,
            "algorithm": "xor",
            "max_attempts": 3,
            "delay_on_fail_ms": 10000,
            "allowed_sessions": ["programming"],
        },
    },
    "services": {
        "diagnosticSessionControl": {"enabled": True},
    },
    "access_patterns": {
        "default_access": {
            "sessions": ["default"],
            "security": "none",
            "authentication": "none",
        },
        "flash_write": {
            "sessions": ["programming"],
            "security": ["flash_access"],
            "authentication": "none",
        },
    },
    "memory": {
        "default_address_format": {
            "address_bytes": 4,
            "length_bytes": 4,
        },
        "regions": {
            "application_flash": {
                "name": "Application Flash",
                "start_address": "0x00010000",
                "size": "0x000F0000",
                "access": "read_write",
                "security_level": "flash_access",
                "session": "programming",
            },
            "calibration_data": {
                "name": "Calibration Data",
                "start_address": "0x00100000",
                "size": "0x00020000",
                "access": "read_write",
                "security_level": "flash_access",
                "session": "programming",
            },
            "bootloader": {
                "name": "Bootloader",
                "start_address": "0x00000000",
                "size": "0x00010000",
                "access": "read",
            },
        },
        "data_blocks": {
            "app_software": {
                "name": "Application Software",
                "type": "download",
                "memory_address": "0x00010000",
                "memory_size": "0x000F0000",
                "format": "raw",
                "max_block_length": 4096,
                "security_level": "flash_access",
                "session": "programming",
            },
            "calibration": {
                "name": "Calibration Data Block",
                "type": "download",
                "memory_address": "0x00100000",
                "memory_size": "0x00020000",
                "format": "raw",
                "max_block_length": 2048,
            },
        },
    },
}

# YAML with audience filtering for multi-target testing
YAML_WITH_AUDIENCE: dict[str, Any] = {
    "schema": "opensovd.cda.diagdesc/v1",
    "meta": {
        "author": "Audience Test Author",
        "domain": "Powertrain",
        "created": "2024-01-15",
        "revision": "1.0.0",
        "description": "ECU with audience-filtered content",
    },
    "ecu": {
        "id": "AUDIENCE_ECU",
        "name": "Audience Test ECU",
        "addressing": {
            "doip": {
                "ip": "192.168.1.1",
                "logical_address": "0x0E80",
                "tester_address": "0x0E00",
            },
        },
    },
    "sessions": {
        "default": {"id": "0x01"},
        "extended": {"id": "0x03"},
    },
    "services": {
        "diagnosticSessionControl": {"enabled": True},
        "readDataByIdentifier": {"enabled": True},
    },
    "access_patterns": {
        "public_read": {
            "sessions": ["default", "extended"],
            "security": "none",
            "authentication": "none",
        },
        "internal_read": {
            "sessions": ["extended"],
            "security": "none",
            "authentication": "none",
        },
    },
    "dids": {
        "0xF190": {
            "name": "VehicleIdentificationNumber",
            "description": "17-character VIN",
            "access": "read",
            "type": {"base": "ascii", "length": 17},
            "access_pattern": "public_read",
            "audience": {"include": ["production", "development", "aftermarket"]},
        },
        "0xFD00": {
            "name": "InternalDebugData",
            "description": "Internal debugging data",
            "access": "read",
            "type": {"base": "u32"},
            "access_pattern": "internal_read",
            "audience": {"include": ["development"]},
        },
        "0xFD01": {
            "name": "FactoryCalibration",
            "description": "Factory calibration values",
            "access": "read",
            "type": {"base": "bytes", "length": 64},
            "access_pattern": "internal_read",
            "audience": {"include": ["oem", "supplier"], "exclude": ["aftermarket"]},
        },
    },
    "dtcs": {
        "0x010100": {
            "name": "PublicFault",
            "description": "Public fault visible to all",
            "audience": {"include": ["production", "aftermarket", "development"]},
        },
        "0xFFFF00": {
            "name": "InternalTestDTC",
            "description": "Internal test DTC for development only",
            "audience": {"include": ["development"], "exclude": ["production"]},
        },
    },
}

# YAML string versions for file-based testing
MINIMAL_YAML_STR = """
schema: opensovd.cda.diagdesc/v1
meta:
  author: Test Author
  domain: Powertrain
  created: "2024-01-15"
  revision: "1.0.0"
  description: Minimal test ECU
ecu:
  id: MINIMAL_ECU
  name: Minimal Engine Control Module
  addressing:
    doip:
      ip: "192.168.1.1"
      logical_address: "0x0E80"
      tester_address: "0x0E00"
sessions:
  default:
    id: "0x01"
services:
  diagnosticSessionControl:
    enabled: true
access_patterns:
  default_access:
    sessions:
      - default
    security: none
    authentication: none
"""

INVALID_YAML_STR = """
schema: invalid/v999
meta:
  author: Invalid Test
  domain: Powertrain
  created: "2024-01-15"
  revision: "1.0.0"
ecu:
  id: INVALID_ECU
  name: Invalid ECU
  addressing:
    doip:
      ip: "192.168.1.1"
      logical_address: "0x0E80"
      tester_address: "0x0E00"
sessions:
  default:
    id: "0x01"
services:
  diagnosticSessionControl:
    enabled: true
"""
