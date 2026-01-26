"""IR models for data types and DOPs (Data Object Properties).

This module defines the intermediate representation for data types
used in diagnostic services. These map closely to FlatBuffers schema types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from yaml_to_mdd.ir.services import IRParam


class IRDataType(Enum):
    """FlatBuffers-compatible data types.

    Maps to the DataType enum in the FlatBuffers schema.
    """

    A_INT_32 = 0
    A_UINT_32 = 1
    A_FLOAT_32 = 2
    A_ASCIISTRING = 3
    A_UTF_8_STRING = 4
    A_UNICODE_2_STRING = 5
    A_BYTEFIELD = 6
    A_FLOAT_64 = 7


class IRCompuCategory(Enum):
    """Computation method categories.

    Defines how raw values are converted to physical values.
    Maps to FlatBuffers CompuCategory enum.
    """

    IDENTICAL = 0  # No conversion (raw = physical)
    LINEAR = 1  # y = ax + b
    SCALE_LINEAR = 2  # Multiple linear ranges
    TEXT_TABLE = 3  # Enum mapping
    COMPU_CODE = 4  # Custom code
    TAB_INTP = 5  # Table interpolation
    RAT_FUNC = 6  # Rational function
    SCALE_RAT_FUNC = 7  # Multiple rational ranges


class IRDiagCodedTypeName(Enum):
    """Diagnostic coded type names.

    Defines how data is encoded on the wire.
    Maps to FlatBuffers DiagCodedTypeName enum.
    """

    LEADING_LENGTH_INFO_TYPE = 0
    MIN_MAX_LENGTH_TYPE = 1
    PARAM_LENGTH_INFO_TYPE = 2
    STANDARD_LENGTH_TYPE = 3


@dataclass(frozen=True)
class IRLimit:
    """A limit value for compu scales.

    Attributes
    ----------
        value: The limit value (numeric or string).
        interval_type: OPEN, CLOSED, or INFINITE.

    """

    value: float | int | str
    interval_type: str = "CLOSED"


@dataclass(frozen=True)
class IRCompuScale:
    """A computation scale for data conversion.

    Used for linear conversions (y = ax + b) or enum mappings.

    Attributes
    ----------
        lower_limit: Lower bound of the scale range.
        upper_limit: Upper bound of the scale range.
        offset: The 'b' coefficient in y = ax + b.
        factor: The 'a' coefficient in y = ax + b.
        internal_value: For text tables, the raw enum value.
        text_value: For text tables, the string representation.
        short_label: Optional short description.

    """

    lower_limit: IRLimit | None = None
    upper_limit: IRLimit | None = None

    # For linear: coefficients
    offset: float | None = None  # b in y = ax + b
    factor: float | None = None  # a in y = ax + b

    # For text table: enum value
    internal_value: int | None = None
    text_value: str | None = None

    short_label: str | None = None


@dataclass(frozen=True)
class IRCompuMethod:
    """Computation method for converting between raw and physical values.

    Attributes
    ----------
        category: The type of conversion (IDENTICAL, LINEAR, etc.).
        scales: Tuple of scales defining the conversion.
        unit: Optional physical unit (e.g., "rpm", "km/h").

    """

    category: IRCompuCategory
    scales: tuple[IRCompuScale, ...] = field(default_factory=tuple)
    unit: str | None = None


@dataclass(frozen=True)
class IRDiagCodedType:
    """Diagnostic coded type defining wire format.

    Maps to FlatBuffers DiagCodedType table.

    Attributes
    ----------
        type_name: The coded type category.
        base_data_type: The underlying data type.
        bit_length: Length in bits (default 8).
        is_high_low_byte_order: True for big endian (default).
        min_length: For variable-length types, minimum length.
        max_length: For variable-length types, maximum length.
        termination: For strings: END_OF_PDU, ZERO, HEX_FF.

    """

    type_name: IRDiagCodedTypeName
    base_data_type: IRDataType
    bit_length: int = 8
    is_high_low_byte_order: bool = True  # Big endian

    # For MIN_MAX_LENGTH_TYPE
    min_length: int | None = None
    max_length: int | None = None
    termination: str | None = None  # END_OF_PDU, ZERO, HEX_FF


@dataclass(frozen=True)
class IRDOP:
    """Data Object Property - defines how data is encoded/decoded.

    Maps to FlatBuffers DOP table. A DOP combines the coded type
    (wire format) with the computation method (value conversion).

    Attributes
    ----------
        short_name: Unique identifier for the DOP.
        long_name: Human-readable description.
        diag_coded_type: Wire format definition.
        compu_method: Value conversion definition.
        physical_type: Physical data type after conversion.
        unit: Physical unit.
        structure_params: For struct types, nested parameters.

    """

    short_name: str
    long_name: str | None = None

    diag_coded_type: IRDiagCodedType | None = None
    compu_method: IRCompuMethod | None = None
    physical_type: IRDataType | None = None

    unit: str | None = None

    # For structs: nested parameters
    structure_params: tuple[IRParam, ...] | None = None

    def __hash__(self) -> int:
        """Hash by short_name for use in sets/dicts."""
        return hash(self.short_name)
