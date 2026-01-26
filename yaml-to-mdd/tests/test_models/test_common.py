"""Tests for common types and validators."""

import pytest
from pydantic import BaseModel, ValidationError
from yaml_to_mdd.models.common import (
    HexInt,
    HexInt8,
    HexInt16,
    HexInt24,
    HexInt32,
    parse_hex_int,
    serialize_hex_int,
)


class TestParseHexInt:
    """Tests for parse_hex_int function."""

    def test_parse_integer(self) -> None:
        """Should parse regular integers."""
        assert parse_hex_int(42) == 42
        assert parse_hex_int(0) == 0
        assert parse_hex_int(61840) == 61840

    def test_parse_hex_string_lowercase(self) -> None:
        """Should parse lowercase hex strings."""
        assert parse_hex_int("0xf190") == 61840
        assert parse_hex_int("0xff") == 255
        assert parse_hex_int("0x0") == 0

    def test_parse_hex_string_uppercase(self) -> None:
        """Should parse uppercase hex strings."""
        assert parse_hex_int("0XF190") == 61840
        assert parse_hex_int("0xFF") == 255

    def test_parse_hex_string_mixed_case(self) -> None:
        """Should parse mixed case hex strings."""
        assert parse_hex_int("0xFf") == 255
        assert parse_hex_int("0Xf190") == 61840

    def test_parse_decimal_string(self) -> None:
        """Should parse decimal strings."""
        assert parse_hex_int("42") == 42
        assert parse_hex_int("61840") == 61840

    def test_parse_with_whitespace(self) -> None:
        """Should handle whitespace in strings."""
        assert parse_hex_int("  0xFF  ") == 255
        assert parse_hex_int("  42  ") == 42

    def test_parse_none_raises(self) -> None:
        """Should raise ValueError for None."""
        with pytest.raises(ValueError, match="cannot be None"):
            parse_hex_int(None)

    def test_parse_invalid_hex_raises(self) -> None:
        """Should raise ValueError for invalid hex."""
        with pytest.raises(ValueError, match="Invalid hex string"):
            parse_hex_int("0xGGGG")

    def test_parse_invalid_type_raises(self) -> None:
        """Should raise ValueError for invalid types."""
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_hex_int([1, 2, 3])  # type: ignore[arg-type]


class TestSerializeHexInt:
    """Tests for serialize_hex_int function."""

    def test_serialize_to_uppercase_hex(self) -> None:
        """Should serialize to uppercase hex with 0x prefix."""
        assert serialize_hex_int(255) == "0xFF"
        assert serialize_hex_int(61840) == "0xF190"
        assert serialize_hex_int(0) == "0x0"


class TestHexIntInModel:
    """Tests for HexInt type in Pydantic models."""

    def test_model_accepts_integer(self) -> None:
        """Model should accept integer values."""

        class MyModel(BaseModel):
            value: HexInt

        m = MyModel(value=61840)
        assert m.value == 61840

    def test_model_accepts_hex_string(self) -> None:
        """Model should accept hex string values."""

        class MyModel(BaseModel):
            value: HexInt

        m = MyModel(value="0xF190")  # type: ignore[arg-type]
        assert m.value == 61840

    def test_model_serializes_to_hex(self) -> None:
        """Model should serialize to hex string."""

        class MyModel(BaseModel):
            value: HexInt

        m = MyModel(value=61840)
        data = m.model_dump()
        assert data["value"] == "0xF190"

    def test_model_validation_error(self) -> None:
        """Model should raise ValidationError for invalid values."""

        class MyModel(BaseModel):
            value: HexInt

        with pytest.raises(ValidationError):
            MyModel(value="invalid")  # type: ignore[arg-type]


class TestHexInt8:
    """Tests for HexInt8 (uint8 range validation)."""

    def test_accepts_valid_range(self) -> None:
        """Should accept values in uint8 range."""

        class MyModel(BaseModel):
            value: HexInt8

        assert MyModel(value=0).value == 0
        assert MyModel(value=255).value == 255
        assert MyModel(value="0xFF").value == 255  # type: ignore[arg-type]

    def test_rejects_out_of_range(self) -> None:
        """Should reject values outside uint8 range."""

        class MyModel(BaseModel):
            value: HexInt8

        with pytest.raises(ValidationError):
            MyModel(value=256)

        with pytest.raises(ValidationError):
            MyModel(value=-1)


class TestHexInt16:
    """Tests for HexInt16 (uint16 range validation)."""

    def test_accepts_valid_range(self) -> None:
        """Should accept values in uint16 range."""

        class MyModel(BaseModel):
            value: HexInt16

        assert MyModel(value=0).value == 0
        assert MyModel(value=65535).value == 65535
        assert MyModel(value="0xFFFF").value == 65535  # type: ignore[arg-type]

    def test_rejects_out_of_range(self) -> None:
        """Should reject values outside uint16 range."""

        class MyModel(BaseModel):
            value: HexInt16

        with pytest.raises(ValidationError):
            MyModel(value=65536)


class TestHexInt24:
    """Tests for HexInt24 (uint24 range validation)."""

    def test_accepts_valid_range(self) -> None:
        """Should accept values in uint24 range."""

        class MyModel(BaseModel):
            value: HexInt24

        assert MyModel(value=0).value == 0
        assert MyModel(value=16777215).value == 16777215
        assert MyModel(value="0xFFFFFF").value == 16777215  # type: ignore[arg-type]

    def test_rejects_out_of_range(self) -> None:
        """Should reject values outside uint24 range."""

        class MyModel(BaseModel):
            value: HexInt24

        with pytest.raises(ValidationError):
            MyModel(value=16777216)


class TestHexInt32:
    """Tests for HexInt32 (uint32 range validation)."""

    def test_accepts_valid_range(self) -> None:
        """Should accept values in uint32 range."""

        class MyModel(BaseModel):
            value: HexInt32

        assert MyModel(value=0).value == 0
        assert MyModel(value=4294967295).value == 4294967295
        assert MyModel(value="0xFFFFFFFF").value == 4294967295  # type: ignore[arg-type]

    def test_rejects_out_of_range(self) -> None:
        """Should reject values outside uint32 range."""

        class MyModel(BaseModel):
            value: HexInt32

        with pytest.raises(ValidationError):
            MyModel(value=4294967296)
