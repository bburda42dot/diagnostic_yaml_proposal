"""Common types and validators for Pydantic models."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import AfterValidator, BeforeValidator, PlainSerializer


def parse_hex_int(value: Any) -> int:
    """Parse a value that can be either an integer or a hex string.

    Args:
    ----
        value: Input value - can be int, str (hex format like "0xF190"), or None

    Returns:
    -------
        Parsed integer value

    Raises:
    ------
        ValueError: If the value cannot be parsed as an integer

    Examples:
    --------
        >>> parse_hex_int(61840)
        61840
        >>> parse_hex_int("0xF190")
        61840
        >>> parse_hex_int("0XF190")  # Case insensitive
        61840
        >>> parse_hex_int("61840")  # Decimal string
        61840

    """
    if value is None:
        raise ValueError("Value cannot be None")

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        value = value.strip()
        if value.lower().startswith("0x"):
            try:
                return int(value, 16)
            except ValueError as e:
                raise ValueError(f"Invalid hex string: {value}") from e
        else:
            try:
                return int(value)
            except ValueError as e:
                raise ValueError(f"Invalid integer string: {value}") from e

    raise ValueError(f"Cannot parse {type(value).__name__} as integer: {value}")


def serialize_hex_int(value: int) -> str:
    """Serialize an integer to a hex string for YAML output.

    Args:
    ----
        value: Integer value to serialize

    Returns:
    -------
        Hex string representation (e.g., "0xF190")

    """
    return f"0x{value:X}"


# HexInt type that accepts both "0xF190" and 61840
HexInt = Annotated[
    int,
    BeforeValidator(parse_hex_int),
    PlainSerializer(serialize_hex_int, return_type=str),
]


# Variants for different bit widths (for additional validation)
def validate_uint8(value: int) -> int:
    """Validate that value fits in uint8 range."""
    if not 0 <= value <= 0xFF:
        raise ValueError(f"Value {value} out of uint8 range (0-255)")
    return value


def validate_uint16(value: int) -> int:
    """Validate that value fits in uint16 range."""
    if not 0 <= value <= 0xFFFF:
        raise ValueError(f"Value {value} out of uint16 range (0-65535)")
    return value


def validate_uint24(value: int) -> int:
    """Validate that value fits in uint24 range (3 bytes)."""
    if not 0 <= value <= 0xFFFFFF:
        raise ValueError(f"Value {value} out of uint24 range (0-16777215)")
    return value


def validate_uint32(value: int) -> int:
    """Validate that value fits in uint32 range."""
    if not 0 <= value <= 0xFFFFFFFF:
        raise ValueError(f"Value {value} out of uint32 range (0-4294967295)")
    return value


def validate_uint64(value: int) -> int:
    """Validate that value fits in uint64 range."""
    if not 0 <= value <= 0xFFFFFFFFFFFFFFFF:
        raise ValueError(f"Value {value} out of uint64 range")
    return value


# Typed HexInt variants - use AfterValidator so range check happens after hex parsing
HexInt8 = Annotated[
    int,
    BeforeValidator(parse_hex_int),
    AfterValidator(validate_uint8),
    PlainSerializer(serialize_hex_int, return_type=str),
]

HexInt16 = Annotated[
    int,
    BeforeValidator(parse_hex_int),
    AfterValidator(validate_uint16),
    PlainSerializer(serialize_hex_int, return_type=str),
]

HexInt24 = Annotated[
    int,
    BeforeValidator(parse_hex_int),
    AfterValidator(validate_uint24),
    PlainSerializer(serialize_hex_int, return_type=str),
]

HexInt32 = Annotated[
    int,
    BeforeValidator(parse_hex_int),
    AfterValidator(validate_uint32),
    PlainSerializer(serialize_hex_int, return_type=str),
]

HexInt64 = Annotated[
    int,
    BeforeValidator(parse_hex_int),
    AfterValidator(validate_uint64),
    PlainSerializer(serialize_hex_int, return_type=str),
]


# Optional hex variants (for fields that can be None)
HexInt8Optional = HexInt8 | None
HexInt16Optional = HexInt16 | None
HexInt24Optional = HexInt24 | None
HexInt32Optional = HexInt32 | None
HexInt64Optional = HexInt64 | None
