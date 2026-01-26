"""Models for the DIDs section of diagnostic description."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import core_schema

from yaml_to_mdd.models.types import TypeDefinition

# Forward reference for AudienceSet to avoid circular imports
AudienceSetType = dict[str, Any] | None


class IOControl(BaseModel):
    """Input/Output control configuration for a DID.

    Example:
    -------
        ```yaml
        io_control:
          enabled: true
          return_control_to_ecu: true
          freeze_current_state: true
        ```

    """

    model_config = ConfigDict(extra="forbid")

    enabled: Annotated[
        bool | None,
        Field(
            default=None,
            description="Whether I/O control is enabled for this DID",
        ),
    ]
    return_control_to_ecu: Annotated[
        bool | None,
        Field(
            default=None,
            description="Support returnControlToECU subfunction",
        ),
    ]
    reset_to_default: Annotated[
        bool | None,
        Field(
            default=None,
            description="Support resetToDefault subfunction",
        ),
    ]
    freeze_current_state: Annotated[
        bool | None,
        Field(
            default=None,
            description="Support freezeCurrentState subfunction",
        ),
    ]
    short_term_adjustment: Annotated[
        bool | None,
        Field(
            default=None,
            description="Support shortTermAdjustment subfunction",
        ),
    ]


class WriteCondition(BaseModel):
    """Condition required for writing a DID.

    Example:
    -------
        ```yaml
        write_conditions:
          - session: extended
          - security: level_1
        ```

    """

    model_config = ConfigDict(extra="forbid")

    session: Annotated[
        str | None,
        Field(
            default=None,
            description="Required session name",
        ),
    ]
    security: Annotated[
        str | None,
        Field(
            default=None,
            description="Required security level name",
        ),
    ]
    authentication: Annotated[
        str | None,
        Field(
            default=None,
            description="Required authentication role",
        ),
    ]


class DIDDefinition(BaseModel):
    """A Data Identifier (DID) definition.

    DIDs are data items accessible via UDS ReadDataByIdentifier (0x22)
    and WriteDataByIdentifier (0x2E) services.

    Example:
    -------
        ```yaml
        0xF190:
          name: VIN
          description: Vehicle Identification Number
          type: VIN
          access: public  # Reference to access_patterns
          readable: true
          writable: false
          snapshot: false
        ```

    """

    model_config = ConfigDict(extra="forbid")

    name: Annotated[
        str,
        Field(
            min_length=1,
            description="Human-readable DID name",
        ),
    ]
    description: Annotated[
        str | None,
        Field(
            default=None,
            description="Detailed description of the DID",
        ),
    ]

    # Type can be a reference (string) or inline definition
    type: Annotated[
        str | TypeDefinition,
        Field(
            description="Type reference or inline type definition",
        ),
    ]

    # Access is now a string reference to access_patterns (per schema.json)
    access: Annotated[
        str,
        Field(
            description="Reference to access_patterns section (e.g., 'public', 'extended_write')",
        ),
    ]

    # NEW FIELDS per schema.json
    readable: Annotated[
        bool | None,
        Field(
            default=None,
            description="Whether this DID is readable via 0x22",
        ),
    ]
    writable: Annotated[
        bool | None,
        Field(
            default=None,
            description="Whether this DID is writable via 0x2E",
        ),
    ]
    snapshot: Annotated[
        bool | None,
        Field(
            default=None,
            description="Whether this DID can be captured in DTC snapshots",
        ),
    ]
    io_control: Annotated[
        IOControl | None,
        Field(
            default=None,
            description="I/O control configuration for InputOutputControlByIdentifier (0x2F)",
        ),
    ]
    annotations: Annotated[
        dict[str, Any] | None,
        Field(
            default=None,
            description="Custom annotations and metadata",
        ),
    ]

    # Legacy/deprecated fields (kept for backward compatibility)
    access_pattern: Annotated[
        str | None,
        Field(
            default=None,
            description="Deprecated: use 'access' instead",
        ),
    ]

    # Conditions for read access
    read_conditions: Annotated[
        list[WriteCondition] | None,
        Field(
            default=None,
            description="Conditions required for reading",
        ),
    ]

    # Conditions for write access
    write_conditions: Annotated[
        list[WriteCondition] | None,
        Field(
            default=None,
            description="Conditions required for writing",
        ),
    ]

    # Scaling override (if not defined in type)
    scale: Annotated[
        float | None,
        Field(
            default=None,
            description="Scale factor override",
        ),
    ]
    offset: Annotated[
        float | None,
        Field(
            default=None,
            description="Offset override",
        ),
    ]
    unit: Annotated[
        str | None,
        Field(
            default=None,
            description="Unit override",
        ),
    ]

    audience: Annotated[
        AudienceSetType,
        Field(
            default=None,
            description="Audiences that can access this DID",
        ),
    ]

    @field_validator("type", mode="before")
    @classmethod
    def parse_type(cls, v: Any) -> str | TypeDefinition | Any:
        """Parse type as either string reference or inline definition."""
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            return TypeDefinition.model_validate(v)
        # Return as-is, Pydantic will handle validation
        return v


def _validate_dids(value: Any) -> dict[int, DIDDefinition]:
    """Validate DIDs dictionary with hex key support."""
    if not isinstance(value, dict):
        msg = "DIDs must be a dictionary"
        raise ValueError(msg)

    result: dict[int, DIDDefinition] = {}
    for key, val in value.items():
        # Parse key as hex or int
        if isinstance(key, str):
            int_key = int(key, 16) if key.lower().startswith("0x") else int(key)
        elif isinstance(key, int):
            int_key = key
        else:
            msg = f"Invalid DID key type: {type(key)}"
            raise ValueError(msg)

        # Validate range (0x0000-0xFFFF)
        if not 0 <= int_key <= 0xFFFF:
            msg = f"DID {hex(int_key)} out of range (0x0000-0xFFFF)"
            raise ValueError(msg)

        # Parse value
        if isinstance(val, DIDDefinition):
            result[int_key] = val
        else:
            result[int_key] = DIDDefinition.model_validate(val)

    return result


class DIDsDict(dict[int, DIDDefinition]):
    """Dictionary of DIDs keyed by their 16-bit identifier.

    Keys can be integers or hex strings (e.g., "0xF190").
    """

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> core_schema.CoreSchema:
        """Get Pydantic schema for DIDsDict."""
        return core_schema.no_info_plain_validator_function(_validate_dids)


# Type alias for simpler usage
DIDs = DIDsDict
