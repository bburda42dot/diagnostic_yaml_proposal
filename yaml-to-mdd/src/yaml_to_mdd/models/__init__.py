"""Pydantic models for OpenSOVD CDA Diagnostic Description YAML schema validation.

This module provides type-safe Pydantic models that mirror the JSON Schema
structure defined in diagnostic_yaml/schema.json. These models are used for:

- Parsing and validating YAML/JSON diagnostic description files
- Type-safe access to all schema elements
- Serialization back to YAML/JSON

Primary Entry Points:
    load_diagnostic_description(path): Load and validate a YAML/JSON file
    validate_diagnostic_description(path): Validate and return list of errors
    DiagnosticDescription: Root model for the entire document

Example:
-------
    >>> from yaml_to_mdd.models import load_diagnostic_description
    >>> doc = load_diagnostic_description("my-ecu.yaml")
    >>> print(f"ECU: {doc.ecu.name}")
    >>> print(f"DIDs: {len(doc.dids) if doc.dids else 0}")

Model Hierarchy:
    DiagnosticDescription (root)
    ├── Meta - document metadata
    ├── Ecu - ECU identification and addressing
    ├── Sessions - diagnostic session definitions
    ├── Services - UDS service configurations
    ├── Security - security access levels (optional)
    ├── AccessPatterns - reusable access control (optional)
    ├── Types - custom type definitions (optional)
    ├── DIDs - data identifier definitions (optional)
    ├── Routines - control routine definitions (optional)
    ├── DTCConfig - DTC configuration (optional)
    ├── DTCs - diagnostic trouble codes (optional)
    └── Memory - memory configuration (optional)


"""

from yaml_to_mdd.models.audience import (
    AudienceConfig,
    AudienceSet,
    AudienceValue,
    StandardAudience,
    parse_audience_set,
)
from yaml_to_mdd.models.common import (
    HexInt,
    HexInt8,
    HexInt8Optional,
    HexInt16,
    HexInt16Optional,
    HexInt24,
    HexInt24Optional,
    HexInt32,
    HexInt32Optional,
    parse_hex_int,
    serialize_hex_int,
)
from yaml_to_mdd.models.dids import (
    DIDDefinition,
    DIDs,
    DIDsDict,
    IOControl,
    WriteCondition,
)
from yaml_to_mdd.models.ecu import (
    Addressing,
    AddressingMode,
    Annotations,
    CANAddressing,
    DoIPAddressing,
    Ecu,
    ProtocolDefinition,
    Protocols,
    ProtocolShortName,
    Timing,
)
from yaml_to_mdd.models.loader import (
    LoaderError,
    load_diagnostic_description,
    load_yaml_file,
    validate_diagnostic_description,
)
from yaml_to_mdd.models.meta import Meta, RevisionEntry
from yaml_to_mdd.models.root import DiagnosticDescription
from yaml_to_mdd.models.sessions import Session, Sessions, SessionTiming
from yaml_to_mdd.models.types import (
    BaseType,
    Endianness,
    StructField,
    TypeDefinition,
    Types,
)

__all__ = [
    # Audience models
    "AudienceConfig",
    "AudienceSet",
    "AudienceValue",
    "StandardAudience",
    "parse_audience_set",
    # Common types
    "HexInt",
    "HexInt8",
    "HexInt16",
    "HexInt24",
    "HexInt32",
    "HexInt8Optional",
    "HexInt16Optional",
    "HexInt24Optional",
    "HexInt32Optional",
    "parse_hex_int",
    "serialize_hex_int",
    # Models
    "DiagnosticDescription",
    "Meta",
    "RevisionEntry",
    "Ecu",
    "AddressingMode",
    "Addressing",
    "Annotations",
    "DoIPAddressing",
    "CANAddressing",
    "Timing",
    "ProtocolDefinition",
    "ProtocolShortName",
    "Protocols",
    "Session",
    "Sessions",
    "SessionTiming",
    # Types section models
    "BaseType",
    "Endianness",
    "StructField",
    "TypeDefinition",
    "Types",
    # DIDs section models
    "DIDDefinition",
    "DIDs",
    "DIDsDict",
    "IOControl",
    "WriteCondition",
    # Loader utilities
    "LoaderError",
    "load_diagnostic_description",
    "load_yaml_file",
    "validate_diagnostic_description",
]
