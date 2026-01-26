"""Models for the DTCs (Diagnostic Trouble Codes) section.

DTCs are fault codes stored by the ECU when errors are detected.
They are accessed via ReadDTCInformation (0x19) and ClearDiagnosticInformation (0x14) services.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from yaml_to_mdd.models.common import HexInt8, HexInt16, HexInt24
from yaml_to_mdd.models.types import TypeDefinition

if TYPE_CHECKING:
    from pydantic_core import core_schema as cs


# Forward reference for AudienceSet to avoid circular imports
AudienceSetType = dict[str, Any] | None

# SAE format regex: [PBCU][0-3][0-9A-F]{3}
_SAE_PATTERN = re.compile(r"^[PBCU][0-3][0-9A-Fa-f]{3}$")


# DTC severity levels per schema (1-4)
# Maps to UDS severity: 1=no_class, 2=maintenance_only, 3=check_at_next_halt, 4=check_immediately
DTCSeverity = Annotated[int, Field(ge=1, le=4)]


class DTCSnapshotDataRecord(BaseModel):
    """A single data item in a DTC snapshot.

    References a DID to capture when the DTC is stored.

    Example:
    -------
        ```yaml
        - did: 0xF190
          name: "VIN"
          description: "Vehicle ID at fault time"
        ```

    """

    model_config = ConfigDict(extra="forbid")

    did: Annotated[
        HexInt16,
        Field(description="DID to capture (references DIDs section)"),
    ]

    name: Annotated[
        str | None,
        Field(default=None, description="Optional name override (defaults to DID name)"),
    ]

    description: Annotated[
        str | None,
        Field(default=None, description="Description of why this data is captured"),
    ]


class DTCSnapshotDefinition(BaseModel):
    """Definition of a DTC snapshot (freeze frame) record.

    Snapshots capture DID values when a DTC is stored.

    Example:
    -------
        ```yaml
        standard_snapshot:
          record_number: 0x01
          description: "Freeze frame at fault detection"
          data:
            - did: 0xF190
            - did: 0x1234
              name: "Engine RPM"
          trigger: firstFault
        ```

    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    record_number: Annotated[
        HexInt8,
        Field(
            description="Snapshot record number (0x00-0xFF)",
        ),
    ]

    description: Annotated[
        str | None,
        Field(default=None, description="Description of when this snapshot is captured"),
    ]

    dids: Annotated[
        list[HexInt16] | None,
        Field(
            default=None,
            description="List of DID identifiers to capture (simple format)",
        ),
    ]

    data: Annotated[
        list[DTCSnapshotDataRecord] | None,
        Field(
            default=None,
            description="Data items to capture in this snapshot (detailed format)",
        ),
    ]

    trigger: Annotated[
        str | None,
        Field(
            default=None,
            description="When to capture: 'firstFault', 'mostRecent', 'custom'",
        ),
    ]

    update: Annotated[
        bool | None,
        Field(
            default=None,
            description="Whether to update on subsequent faults",
        ),
    ]

    x_oem: Annotated[
        dict[str, Any] | None,
        Field(
            default=None,
            alias="x-oem",
            description="OEM-specific extensions",
        ),
    ]


class DTCExtendedDataDefinition(BaseModel):
    """Definition of DTC extended data record.

    Extended data holds additional information about the DTC
    such as occurrence counters, aging counters, etc.

    Example:
    -------
        ```yaml
        occurrence_counter:
          record_number: 0x01
          name: "OccurrenceCounter"
          type: u8
          unit: "count"
        ```

    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    record_number: Annotated[
        HexInt8,
        Field(
            description="Extended data record number (0x01-0xFE, 0x00 and 0xFF reserved)",
        ),
    ]

    name: Annotated[
        str | None,
        Field(default=None, description="Name of the extended data record"),
    ]

    type: Annotated[
        str | TypeDefinition | None,
        Field(
            default=None,
            description="Type reference (built-in or custom type name) or inline type definition",
        ),
    ]

    unit: Annotated[
        str | None,
        Field(default=None, description="Engineering unit for the data"),
    ]

    trigger: Annotated[
        str | None,
        Field(
            default=None,
            description="When to capture this data",
        ),
    ]

    x_oem: Annotated[
        dict[str, Any] | None,
        Field(
            default=None,
            alias="x-oem",
            description="OEM-specific extensions",
        ),
    ]


class DTCGroup(BaseModel):
    """Group of related DTCs.

    Allows organizing DTCs into logical groups for reporting
    and clearing operations.

    Example:
    -------
        ```yaml
        powertrain:
          name: "Powertrain DTCs"
          group_id: 0x000100
          dtcs: ["P0100", "P0101"]
        ```

    """

    model_config = ConfigDict(extra="forbid")

    name: Annotated[
        str,
        Field(description="Group name"),
    ]

    description: Annotated[
        str | None,
        Field(default=None, description="Group description"),
    ]

    group_id: Annotated[
        HexInt24 | None,
        Field(default=None, description="UDS DTC group identifier (3 bytes)"),
    ]

    dtcs: Annotated[
        list[str],
        Field(default_factory=list, description="List of DTC codes in this group"),
    ]


class DTCConfig(BaseModel):
    """Global DTC configuration.

    Defines common settings for all DTCs including status mask
    and snapshot/extended data definitions.

    Example:
    -------
        ```yaml
        dtc_config:
          status_availability_mask: 0xFF
          default_snapshots:
            standard_snapshot:
              record_number: 0x01
              dids: [0xF190, 0x1234]
          groups:
            powertrain:
              name: "Powertrain DTCs"
        ```

    """

    model_config = ConfigDict(extra="forbid")

    status_availability_mask: Annotated[
        HexInt8 | None,
        Field(
            default=None,
            description="DTC status availability mask (ISO 14229)",
        ),
    ]

    # Legacy field names
    snapshots: Annotated[
        dict[str, DTCSnapshotDefinition] | None,
        Field(
            default=None,
            description="Named snapshot definitions",
        ),
    ]

    extended_data: Annotated[
        dict[str, DTCExtendedDataDefinition] | None,
        Field(
            default=None,
            description="Named extended data definitions",
        ),
    ]

    # New field names (preferred)
    default_snapshots: Annotated[
        dict[str, DTCSnapshotDefinition] | None,
        Field(
            default=None,
            description="Default snapshots applied to all DTCs",
        ),
    ]

    default_extended_data: Annotated[
        dict[str, DTCExtendedDataDefinition] | None,
        Field(
            default=None,
            description="Default extended data records for all DTCs",
        ),
    ]

    groups: Annotated[
        dict[str, DTCGroup] | None,
        Field(
            default=None,
            description="Named DTC groups",
        ),
    ]


class DTCDefinition(BaseModel):
    """A Diagnostic Trouble Code (DTC) definition.

    DTCs are 24-bit fault codes following ISO 15031-6 (SAE J2012) format.
    The SAE code format is [PBCU][0-3][0-9A-F]{3} where:
    - P = Powertrain, B = Body, C = Chassis, U = Network
    - Second digit: 0=SAE standard, 1-3=manufacturer specific
    - Last 3 digits: Hexadecimal fault code

    Example:
    -------
        ```yaml
        0x123456:
          name: EngineOvertemperature
          sae: P0217
          description: Engine coolant exceeds safe limit
          severity: check_immediately
          functional_unit: 0x01
          aging_counter_threshold: 40
        ```

    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: Annotated[
        str,
        Field(
            min_length=1,
            description="Human-readable DTC name",
        ),
    ]

    sae: Annotated[
        str | None,
        Field(
            default=None,
            description="SAE J2012 formatted code (e.g., P0123, B1234, C0001, U0100)",
        ),
    ]

    description: Annotated[
        str | None,
        Field(
            default=None,
            description="Detailed description of the fault condition",
        ),
    ]

    severity: Annotated[
        DTCSeverity | None,
        Field(
            default=None,
            description="Severity classification per ISO 14229",
        ),
    ]

    functional_unit: Annotated[
        HexInt8 | None,
        Field(
            default=None,
            description="Functional unit identifier (0x00-0xFF)",
        ),
    ]

    # Snapshot / Freeze Frame data
    snapshots: Annotated[
        list[str] | list[DTCSnapshotDefinition] | None,
        Field(
            default=None,
            description="Snapshot definition names or inline definitions",
        ),
    ]

    # Extended data records
    extended_data: Annotated[
        list[str] | list[DTCExtendedDataDefinition] | None,
        Field(
            default=None,
            description="Extended data definition names or inline definitions",
        ),
    ]

    # DTC behavior
    aging_counter_threshold: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            le=255,
            description="Number of driving cycles before DTC ages out",
        ),
    ]

    aged_counter_threshold: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            le=255,
            description="Number of driving cycles in aged state before clearing",
        ),
    ]

    priority: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            le=255,
            description="DTC priority (lower = higher priority)",
        ),
    ]

    x_oem: Annotated[
        dict[str, Any] | None,
        Field(
            default=None,
            alias="x-oem",
            description="OEM-specific extensions",
        ),
    ]

    audience: Annotated[
        AudienceSetType,
        Field(
            default=None,
            description="Audiences that can see this DTC",
        ),
    ]

    @field_validator("sae")
    @classmethod
    def validate_sae_format(cls, v: str | None) -> str | None:
        """Validate SAE DTC format (e.g., P0123, B1234).

        The SAE J2012 format is: [PBCU][0-3][0-9A-F]{3}
        - P = Powertrain, B = Body, C = Chassis, U = Network
        - Second character: 0-3 (0=SAE, 1-3=manufacturer specific)
        - Last 3 characters: Hexadecimal code
        """
        if v is None:
            return None
        upper_v = v.upper()
        if not _SAE_PATTERN.match(upper_v):
            raise ValueError(
                f"Invalid SAE DTC format: {v}. " "Expected format: P0123, B1234, C0001, or U0100"
            )
        return upper_v


def _parse_dtc_key(key: str | int) -> int:
    """Parse a DTC key to an integer.

    Args:
    ----
        key: DTC identifier as hex string (e.g., "0x123456") or integer.

    Returns:
    -------
        Integer representation of the DTC code.

    Raises:
    ------
        ValueError: If key cannot be parsed or is invalid type.

    """
    if isinstance(key, str):
        if key.lower().startswith("0x"):
            return int(key, 16)
        return int(key)
    if isinstance(key, int):
        return key
    raise ValueError(f"Invalid DTC key type: {type(key)}")


def _validate_dtc_id(dtc_id: int) -> None:
    """Validate that DTC ID is within 24-bit range.

    Args:
    ----
        dtc_id: DTC identifier to validate.

    Raises:
    ------
        ValueError: If DTC ID is out of range.

    """
    if not 0 <= dtc_id <= 0xFFFFFF:
        raise ValueError(f"DTC {hex(dtc_id)} out of range (0x000000-0xFFFFFF)")


def _validate_dtcs(value: Any) -> dict[int, DTCDefinition]:
    """Validate and parse a DTCs dictionary.

    Args:
    ----
        value: Raw dictionary with DTC definitions.

    Returns:
    -------
        Parsed dictionary with integer keys and DTCDefinition values.

    Raises:
    ------
        ValueError: If value is not a dict or contains invalid data.

    """
    if not isinstance(value, dict):
        raise ValueError("DTCs must be a dictionary")

    result: dict[int, DTCDefinition] = {}
    for key, val in value.items():
        int_key = _parse_dtc_key(key)
        _validate_dtc_id(int_key)

        if isinstance(val, DTCDefinition):
            result[int_key] = val
        else:
            result[int_key] = DTCDefinition.model_validate(val)

    return result


class _DTCsDictMeta(type):
    """Metaclass for DTCsDict to support Pydantic validation."""

    def __getattr__(cls, name: str) -> Any:
        """Handle Pydantic attribute access."""
        if name == "model_validate":
            return _validate_dtcs
        raise AttributeError(f"type object 'DTCsDict' has no attribute {name!r}")


class DTCsDict(dict[int, DTCDefinition], metaclass=_DTCsDictMeta):
    """Dictionary of DTCs keyed by their 24-bit identifier.

    Supports hex string keys (e.g., "0x123456") and integer keys.
    Validates that all keys are in the range 0x000000-0xFFFFFF.
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: Any,
    ) -> cs.CoreSchema:
        """Get Pydantic core schema for validation."""
        from pydantic_core import core_schema

        return core_schema.no_info_plain_validator_function(_validate_dtcs)


# Type alias for simpler usage
DTCs = DTCsDict
