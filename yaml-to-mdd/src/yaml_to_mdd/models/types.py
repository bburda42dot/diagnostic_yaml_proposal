"""Models for the types section of diagnostic description."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BaseType(str, Enum):
    """Base data types for type definitions.

    These map to UDS/ODX standard data types used in automotive diagnostics.
    """

    # Unsigned integers
    U8 = "u8"
    U16 = "u16"
    U32 = "u32"
    U64 = "u64"

    # Signed integers
    I8 = "i8"
    I16 = "i16"
    I32 = "i32"
    I64 = "i64"

    # Floating point
    F32 = "f32"
    F64 = "f64"

    # String types
    ASCII = "ascii"
    UTF8 = "utf8"
    UTF16 = "utf16"

    # Binary data
    BYTES = "bytes"

    # Composite types
    STRUCT = "struct"

    # Boolean
    BOOL = "bool"


class Endianness(str, Enum):
    """Byte order for multi-byte types."""

    BIG = "big"
    LITTLE = "little"


class StructField(BaseModel):
    """A single field in a struct type definition.

    Example:
    -------
        ```yaml
        - name: speed
          type: VehicleSpeed
          description: Current vehicle speed
        ```

    """

    model_config = ConfigDict(extra="forbid")

    name: Annotated[
        str,
        Field(
            min_length=1,
            pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$",
            description="Field name (must be valid identifier)",
        ),
    ]
    type: Annotated[
        str,
        Field(
            min_length=1,
            description="Type reference (built-in or custom type name)",
        ),
    ]
    description: Annotated[
        str | None,
        Field(
            default=None,
            description="Human-readable description of the field",
        ),
    ]
    bit_position: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            description="Bit position within parent (for bit fields)",
        ),
    ]
    bit_length: Annotated[
        int | None,
        Field(
            default=None,
            ge=1,
            description="Bit length (for bit fields)",
        ),
    ]


# Integer base types for enum validation
_INTEGER_BASE_TYPES = {
    BaseType.U8,
    BaseType.U16,
    BaseType.U32,
    BaseType.U64,
    BaseType.I8,
    BaseType.I16,
    BaseType.I32,
    BaseType.I64,
}

# String base types
_STRING_BASE_TYPES = {
    BaseType.ASCII,
    BaseType.UTF8,
    BaseType.UTF16,
}

# Types that support length constraints
_LENGTH_CONSTRAINED_TYPES = _STRING_BASE_TYPES | {BaseType.BYTES}


# Termination method for variable-length fields (per schema.json)
TerminationType = Literal["zero", "length_field", "end_of_pdu", "none"]


class Constraints(BaseModel):
    """Value constraints for internal (raw) and physical (scaled) values.

    Example:
    -------
        ```yaml
        constraints:
          internal: [0, 255]
          physical: [-40, 215]
        ```

    """

    model_config = ConfigDict(extra="forbid")

    internal: Annotated[
        list[float] | None,
        Field(
            default=None,
            min_length=2,
            max_length=2,
            description="[min, max] range for internal (raw) values",
        ),
    ]
    physical: Annotated[
        list[float] | None,
        Field(
            default=None,
            min_length=2,
            max_length=2,
            description="[min, max] range for physical (scaled) values",
        ),
    ]


class Validation(BaseModel):
    """Validation rules for string/bytes types.

    Example:
    -------
        ```yaml
        validation:
          forbidden_characters: ["<", ">", "&"]
          forbidden_values: [0x00, 0xFF]
        ```

    """

    model_config = ConfigDict(extra="forbid")

    forbidden_characters: Annotated[
        list[str] | None,
        Field(
            default=None,
            description="Characters that are not allowed in the value",
        ),
    ]
    forbidden_values: Annotated[
        list[int | str] | None,
        Field(
            default=None,
            description="Values that are not allowed (hex or int)",
        ),
    ]


class LinearConversion(BaseModel):
    """Full linear conversion specification.

    Formula: physical = (internal - offset) * scale / divisor + shift

    Example:
    -------
        ```yaml
        conversion:
          scale: 0.1
          offset: 0
          divisor: 1
          shift: -40
          unit: "degC"
          internal_constraints: [0, 255]
          physical_constraints: [-40, 215]
        ```

    """

    model_config = ConfigDict(extra="forbid")

    scale: Annotated[
        float,
        Field(
            default=1,
            description="Multiplier (numerator)",
        ),
    ]
    offset: Annotated[
        float,
        Field(
            default=0,
            description="Value subtracted from internal before scaling",
        ),
    ]
    divisor: Annotated[
        float,
        Field(
            default=1,
            description="Divisor (denominator)",
        ),
    ]
    shift: Annotated[
        float,
        Field(
            default=0,
            description="Value added after scaling",
        ),
    ]
    unit: Annotated[
        str | None,
        Field(
            default=None,
            description="Physical unit (e.g., 'degC', 'rpm', 'km/h')",
        ),
    ]
    internal_constraints: Annotated[
        list[float] | None,
        Field(
            default=None,
            min_length=2,
            max_length=2,
            description="[min, max] valid range for internal (raw) values",
        ),
    ]
    physical_constraints: Annotated[
        list[float] | None,
        Field(
            default=None,
            min_length=2,
            max_length=2,
            description="[min, max] valid range for physical (scaled) values",
        ),
    ]


class TextTableEntry(BaseModel):
    """Single text table entry mapping value/range to text.

    Example:
    -------
        ```yaml
        - value: 0
          text: "Park"
        - range: [1, 3]
          text: "Forward Gears"
        ```

    """

    model_config = ConfigDict(extra="forbid")

    value: Annotated[
        int | str | None,
        Field(
            default=None,
            description="Exact value (mutually exclusive with range)",
        ),
    ]
    range: Annotated[
        list[int | str] | None,
        Field(
            default=None,
            min_length=2,
            max_length=2,
            description="[min, max] inclusive range",
        ),
    ]
    text: Annotated[
        str,
        Field(description="Display text for this value/range"),
    ]
    description: Annotated[
        str | None,
        Field(
            default=None,
            description="Additional description",
        ),
    ]


class TypeDefinition(BaseModel):
    """A custom type definition.

    Supports atomic types with scaling, enums, strings, bytes, structs, and text tables.

    Examples
    --------
        ```yaml
        # Scaled numeric type with constraints
        VehicleSpeed:
          base: u16
          endian: big
          scale: 0.01
          unit: "km/h"
          constraints:
            physical: [0, 350]

        # Enum type
        GearPosition:
          base: u8
          enum:
            0: Park
            1: Reverse

        # Text table type
        StatusTable:
          base: u8
          entries:
            - value: 0
              text: "Off"
            - range: [1, 3]
              text: "Active"
          default_text: "Unknown"

        # String type with validation
        VIN:
          base: ascii
          length: 17
          pattern: "^[A-HJ-NPR-Z0-9]{17}$"

        # Struct type
        ComplexData:
          base: struct
          size: 10
          fields:
            - name: speed
              type: VehicleSpeed
        ```

    """

    model_config = ConfigDict(extra="forbid")

    # Base type - required
    base: Annotated[
        BaseType,
        Field(description="Base data type"),
    ]

    # Byte order for multi-byte types
    endian: Annotated[
        Endianness | None,
        Field(
            default=None,
            description="Byte order (default: big for multi-byte types)",
        ),
    ]

    # Simple scaling parameters (for numeric types)
    scale: Annotated[
        float | None,
        Field(
            default=None,
            description="Scale factor: physical = raw * scale + offset",
        ),
    ]
    offset: Annotated[
        float | None,
        Field(
            default=None,
            description="Offset value: physical = raw * scale + offset",
        ),
    ]

    # Range constraints (deprecated - use constraints instead)
    min: Annotated[
        float | None,
        Field(
            default=None,
            description="Minimum physical value (deprecated: use constraints)",
        ),
    ]
    max: Annotated[
        float | None,
        Field(
            default=None,
            description="Maximum physical value (deprecated: use constraints)",
        ),
    ]

    # Unit of measurement
    unit: Annotated[
        str | None,
        Field(
            default=None,
            description="Physical unit (e.g., 'km/h', '°C', 'bar')",
        ),
    ]

    # Enum mapping (for enum types)
    enum: Annotated[
        dict[int | str, str] | None,
        Field(
            default=None,
            description="Enum mapping: raw_value -> display_name",
        ),
    ]

    # String/bytes length constraints
    length: Annotated[
        int | None,
        Field(
            default=None,
            ge=1,
            description="Fixed length for string/bytes types",
        ),
    ]
    min_length: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            description="Minimum length for variable-length types",
        ),
    ]
    max_length: Annotated[
        int | None,
        Field(
            default=None,
            ge=1,
            description="Maximum length for variable-length types",
        ),
    ]

    # Character encoding for string types
    encoding: Annotated[
        str | None,
        Field(
            default=None,
            description="Character encoding (e.g., 'US-ASCII', 'UTF-8')",
        ),
    ]

    # Struct fields
    fields: Annotated[
        list[StructField] | None,
        Field(
            default=None,
            min_length=1,
            description="Fields for struct types",
        ),
    ]

    # Bit length override (for sub-byte fields)
    bit_length: Annotated[
        int | None,
        Field(
            default=None,
            ge=1,
            description="Bit length (for packed/bit field types)",
        ),
    ]

    # Description
    description: Annotated[
        str | None,
        Field(
            default=None,
            description="Human-readable type description",
        ),
    ]

    # ====== NEW FIELDS per schema.json ======

    # Constraints (alternative to min/max, more flexible)
    constraints: Annotated[
        Constraints | None,
        Field(
            default=None,
            description="Value constraints for internal and physical values",
        ),
    ]

    # Pattern for string validation
    pattern: Annotated[
        str | None,
        Field(
            default=None,
            description="Regex pattern for validation (ascii/string types)",
        ),
    ]

    # Validation rules
    validation: Annotated[
        Validation | None,
        Field(
            default=None,
            description="Validation rules for forbidden characters/values",
        ),
    ]

    # Termination method for variable-length fields
    termination: Annotated[
        TerminationType | None,
        Field(
            default=None,
            description="Termination method: zero, length_field, end_of_pdu, none",
        ),
    ]

    # Bitmask for masking before interpretation
    bitmask: Annotated[
        int | str | None,
        Field(
            default=None,
            description="Bitmask to apply before interpretation (value & bitmask)",
        ),
    ]

    # Full linear conversion specification
    conversion: Annotated[
        LinearConversion | None,
        Field(
            default=None,
            description="Full linear conversion specification",
        ),
    ]

    # Struct size in bytes
    size: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            description="Size in bytes for struct types",
        ),
    ]

    # Text table entries
    entries: Annotated[
        list[TextTableEntry] | None,
        Field(
            default=None,
            description="Text table entries for coded-to-text conversion",
        ),
    ]

    # Default text for text tables
    default_text: Annotated[
        str | None,
        Field(
            default=None,
            description="Default text if no text table entry matches",
        ),
    ]

    @model_validator(mode="after")
    def validate_type_consistency(self) -> TypeDefinition:
        """Validate that type definition is internally consistent."""
        base = self.base

        # Struct must have fields
        if base == BaseType.STRUCT:
            if not self.fields:
                msg = "Struct type must have 'fields' defined"
                raise ValueError(msg)
            # Struct shouldn't have numeric properties
            if any([self.scale, self.offset, self.enum]):
                msg = "Struct type cannot have scale, offset, or enum"
                raise ValueError(msg)

        # Enum requires integer base type
        if self.enum is not None and base not in _INTEGER_BASE_TYPES:
            msg = f"Enum can only be used with integer base types, not {base.value}"
            raise ValueError(msg)

        # String types should not have scale/offset
        if base in _STRING_BASE_TYPES and (self.scale is not None or self.offset is not None):
            msg = "String types cannot have scale/offset"
            raise ValueError(msg)

        # Validate min_length <= max_length if both specified
        if (
            self.min_length is not None
            and self.max_length is not None
            and self.min_length > self.max_length
        ):
            msg = f"min_length ({self.min_length}) cannot exceed max_length ({self.max_length})"
            raise ValueError(msg)

        # Text table entries require base type
        if self.entries is not None and base not in _INTEGER_BASE_TYPES:
            msg = f"Text table entries require integer base type, not {base.value}"
            raise ValueError(msg)

        return self


# Type alias for the types dictionary
Types = dict[str, TypeDefinition]
