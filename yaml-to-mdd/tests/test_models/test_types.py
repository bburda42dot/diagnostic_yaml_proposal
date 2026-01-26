"""Tests for Types section models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from yaml_to_mdd.models.types import (
    BaseType,
    Endianness,
    StructField,
    TypeDefinition,
)


class TestBaseType:
    """Tests for BaseType enum."""

    def test_unsigned_integers(self) -> None:
        """Should have unsigned integer types."""
        assert BaseType.U8.value == "u8"
        assert BaseType.U16.value == "u16"
        assert BaseType.U32.value == "u32"
        assert BaseType.U64.value == "u64"

    def test_signed_integers(self) -> None:
        """Should have signed integer types."""
        assert BaseType.I8.value == "i8"
        assert BaseType.I16.value == "i16"
        assert BaseType.I32.value == "i32"
        assert BaseType.I64.value == "i64"

    def test_floating_point(self) -> None:
        """Should have floating point types."""
        assert BaseType.F32.value == "f32"
        assert BaseType.F64.value == "f64"

    def test_string_types(self) -> None:
        """Should have string types."""
        assert BaseType.ASCII.value == "ascii"
        assert BaseType.UTF8.value == "utf8"
        assert BaseType.UTF16.value == "utf16"

    def test_other_types(self) -> None:
        """Should have bytes, struct, and bool types."""
        assert BaseType.BYTES.value == "bytes"
        assert BaseType.STRUCT.value == "struct"
        assert BaseType.BOOL.value == "bool"


class TestEndianness:
    """Tests for Endianness enum."""

    def test_endianness_values(self) -> None:
        """Should have big and little endian."""
        assert Endianness.BIG.value == "big"
        assert Endianness.LITTLE.value == "little"


class TestTypeDefinition:
    """Tests for TypeDefinition model."""

    def test_simple_u8(self) -> None:
        """Should accept simple u8 type."""
        t = TypeDefinition(base=BaseType.U8)
        assert t.base == BaseType.U8
        assert t.endian is None
        assert t.scale is None
        assert t.offset is None

    def test_simple_u8_from_string(self) -> None:
        """Should accept base type as string."""
        t = TypeDefinition(base="u8")  # type: ignore[arg-type]
        assert t.base == BaseType.U8

    def test_scaled_u16(self) -> None:
        """Should accept scaled u16 type."""
        t = TypeDefinition(
            base=BaseType.U16,
            endian=Endianness.BIG,
            scale=0.01,
            offset=0,
            unit="km/h",
            min=0,
            max=655.35,
        )
        assert t.base == BaseType.U16
        assert t.endian == Endianness.BIG
        assert t.scale == 0.01
        assert t.offset == 0
        assert t.unit == "km/h"
        assert t.min == 0
        assert t.max == 655.35

    def test_endian_from_string(self) -> None:
        """Should accept endianness as string."""
        t = TypeDefinition(base=BaseType.U16, endian="big")  # type: ignore[arg-type]
        assert t.endian == Endianness.BIG

        t = TypeDefinition(base=BaseType.U16, endian="little")  # type: ignore[arg-type]
        assert t.endian == Endianness.LITTLE

    def test_enum_type_with_int_keys(self) -> None:
        """Should accept enum type with integer keys."""
        t = TypeDefinition(
            base=BaseType.U8,
            enum={
                0: "Park",
                1: "Reverse",
                2: "Neutral",
                3: "Drive",
            },
        )
        assert t.enum is not None
        assert t.enum[0] == "Park"
        assert t.enum[1] == "Reverse"

    def test_enum_type_with_string_keys(self) -> None:
        """Should accept enum type with string keys."""
        t = TypeDefinition(
            base=BaseType.U8,
            enum={
                "0": "Off",
                "1": "On",
            },
        )
        assert t.enum is not None
        assert t.enum["0"] == "Off"

    def test_ascii_string_fixed_length(self) -> None:
        """Should accept ASCII string with fixed length."""
        t = TypeDefinition(
            base=BaseType.ASCII,
            length=17,
            description="Vehicle Identification Number",
        )
        assert t.base == BaseType.ASCII
        assert t.length == 17
        assert t.description == "Vehicle Identification Number"

    def test_ascii_string_with_encoding(self) -> None:
        """Should accept ASCII string with encoding."""
        t = TypeDefinition(
            base=BaseType.ASCII,
            length=16,
            encoding="US-ASCII",
        )
        assert t.encoding == "US-ASCII"

    def test_utf8_string(self) -> None:
        """Should accept UTF-8 string type."""
        t = TypeDefinition(
            base=BaseType.UTF8,
            max_length=255,
        )
        assert t.base == BaseType.UTF8
        assert t.max_length == 255

    def test_bytes_type_variable_length(self) -> None:
        """Should accept bytes type with variable length."""
        t = TypeDefinition(
            base=BaseType.BYTES,
            min_length=1,
            max_length=255,
        )
        assert t.base == BaseType.BYTES
        assert t.min_length == 1
        assert t.max_length == 255

    def test_bytes_type_fixed_length(self) -> None:
        """Should accept bytes type with fixed length."""
        t = TypeDefinition(
            base=BaseType.BYTES,
            length=32,
        )
        assert t.length == 32

    def test_struct_type(self) -> None:
        """Should accept struct type with fields."""
        t = TypeDefinition(
            base=BaseType.STRUCT,
            fields=[
                StructField(name="speed", type="u16"),
                StructField(name="gear", type="u8"),
            ],
        )
        assert t.base == BaseType.STRUCT
        assert t.fields is not None
        assert len(t.fields) == 2
        assert t.fields[0].name == "speed"
        assert t.fields[1].name == "gear"

    def test_bit_length_override(self) -> None:
        """Should accept bit_length for packed fields."""
        t = TypeDefinition(
            base=BaseType.U8,
            bit_length=4,
        )
        assert t.bit_length == 4

    def test_bool_type(self) -> None:
        """Should accept bool type."""
        t = TypeDefinition(base=BaseType.BOOL)
        assert t.base == BaseType.BOOL


class TestTypeDefinitionValidation:
    """Tests for TypeDefinition validation rules."""

    def test_struct_requires_fields(self) -> None:
        """Struct type must have fields defined."""
        with pytest.raises(ValidationError, match="fields"):
            TypeDefinition(base=BaseType.STRUCT)

    def test_struct_with_empty_fields_fails(self) -> None:
        """Struct with empty fields list should fail."""
        with pytest.raises(ValidationError):
            TypeDefinition(base=BaseType.STRUCT, fields=[])

    def test_struct_rejects_scale(self) -> None:
        """Struct type cannot have scale."""
        with pytest.raises(ValidationError, match="scale"):
            TypeDefinition(
                base=BaseType.STRUCT,
                scale=1.0,
                fields=[StructField(name="f", type="u8")],
            )

    def test_struct_rejects_offset(self) -> None:
        """Struct type cannot have offset."""
        with pytest.raises(ValidationError, match="offset"):
            TypeDefinition(
                base=BaseType.STRUCT,
                offset=10.0,
                fields=[StructField(name="f", type="u8")],
            )

    def test_struct_rejects_enum(self) -> None:
        """Struct type cannot have enum."""
        with pytest.raises(ValidationError, match="enum"):
            TypeDefinition(
                base=BaseType.STRUCT,
                enum={0: "A"},
                fields=[StructField(name="f", type="u8")],
            )

    def test_enum_requires_integer_base(self) -> None:
        """Enum should require integer base type."""
        with pytest.raises(ValidationError, match="integer base"):
            TypeDefinition(
                base=BaseType.ASCII,
                enum={0: "Value"},
            )

    def test_enum_rejects_float_base(self) -> None:
        """Enum should reject float base type."""
        with pytest.raises(ValidationError, match="integer base"):
            TypeDefinition(
                base=BaseType.F32,
                enum={0: "Zero"},
            )

    def test_enum_rejects_bytes_base(self) -> None:
        """Enum should reject bytes base type."""
        with pytest.raises(ValidationError, match="integer base"):
            TypeDefinition(
                base=BaseType.BYTES,
                enum={0: "Empty"},
            )

    def test_enum_accepts_all_integer_types(self) -> None:
        """Enum should accept all integer types."""
        for base in [
            BaseType.U8,
            BaseType.U16,
            BaseType.U32,
            BaseType.U64,
            BaseType.I8,
            BaseType.I16,
            BaseType.I32,
            BaseType.I64,
        ]:
            t = TypeDefinition(base=base, enum={0: "A", 1: "B"})
            assert t.enum is not None

    def test_string_rejects_scale(self) -> None:
        """String type cannot have scale."""
        with pytest.raises(ValidationError, match="scale"):
            TypeDefinition(
                base=BaseType.ASCII,
                scale=1.0,
            )

    def test_string_rejects_offset(self) -> None:
        """String type cannot have offset."""
        with pytest.raises(ValidationError, match="offset"):
            TypeDefinition(
                base=BaseType.UTF8,
                offset=10.0,
            )

    def test_min_length_greater_than_max_length_fails(self) -> None:
        """min_length cannot exceed max_length."""
        with pytest.raises(ValidationError, match="min_length"):
            TypeDefinition(
                base=BaseType.BYTES,
                min_length=100,
                max_length=10,
            )

    def test_rejects_extra_fields(self) -> None:
        """Should reject unknown fields."""
        with pytest.raises(ValidationError):
            TypeDefinition(
                base=BaseType.U8,
                unknown_field="value",  # type: ignore[call-arg]
            )

    def test_rejects_invalid_base_type(self) -> None:
        """Should reject invalid base type."""
        with pytest.raises(ValidationError):
            TypeDefinition(base="invalid_type")  # type: ignore[arg-type]


class TestStructField:
    """Tests for StructField model."""

    def test_minimal_field(self) -> None:
        """Should accept minimal field definition."""
        f = StructField(name="my_field", type="u16")
        assert f.name == "my_field"
        assert f.type == "u16"
        assert f.description is None
        assert f.bit_position is None
        assert f.bit_length is None

    def test_field_with_description(self) -> None:
        """Should accept field with description."""
        f = StructField(
            name="speed",
            type="VehicleSpeed",
            description="Current vehicle speed",
        )
        assert f.description == "Current vehicle speed"

    def test_field_with_custom_type_reference(self) -> None:
        """Should accept custom type reference."""
        f = StructField(name="gear", type="GearPosition")
        assert f.type == "GearPosition"

    def test_bit_field(self) -> None:
        """Should accept bit field specification."""
        f = StructField(
            name="flag",
            type="bool",
            bit_position=0,
            bit_length=1,
        )
        assert f.bit_position == 0
        assert f.bit_length == 1

    def test_bit_field_with_multiple_bits(self) -> None:
        """Should accept multi-bit field."""
        f = StructField(
            name="nibble",
            type="u8",
            bit_position=4,
            bit_length=4,
        )
        assert f.bit_position == 4
        assert f.bit_length == 4

    def test_valid_field_names(self) -> None:
        """Should accept valid identifier names."""
        valid_names = [
            "field",
            "_private",
            "camelCase",
            "PascalCase",
            "snake_case",
            "field1",
            "field_123",
            "__dunder__",
        ]
        for name in valid_names:
            f = StructField(name=name, type="u8")
            assert f.name == name

    def test_invalid_field_name_starts_with_number(self) -> None:
        """Should reject field name starting with number."""
        with pytest.raises(ValidationError, match="pattern"):
            StructField(name="123invalid", type="u8")

    def test_invalid_field_name_with_dash(self) -> None:
        """Should reject field name with dash."""
        with pytest.raises(ValidationError, match="pattern"):
            StructField(name="has-dash", type="u8")

    def test_invalid_field_name_with_space(self) -> None:
        """Should reject field name with space."""
        with pytest.raises(ValidationError, match="pattern"):
            StructField(name="has space", type="u8")

    def test_empty_field_name(self) -> None:
        """Should reject empty field name."""
        with pytest.raises(ValidationError):
            StructField(name="", type="u8")

    def test_empty_type(self) -> None:
        """Should reject empty type."""
        with pytest.raises(ValidationError):
            StructField(name="field", type="")

    def test_rejects_extra_fields(self) -> None:
        """Should reject unknown fields."""
        with pytest.raises(ValidationError):
            StructField(
                name="field",
                type="u8",
                unknown="value",  # type: ignore[call-arg]
            )

    def test_negative_bit_position_fails(self) -> None:
        """Should reject negative bit_position."""
        with pytest.raises(ValidationError):
            StructField(name="f", type="u8", bit_position=-1)

    def test_zero_bit_length_fails(self) -> None:
        """Should reject zero bit_length."""
        with pytest.raises(ValidationError):
            StructField(name="f", type="u8", bit_length=0)


class TestTypesInRoot:
    """Tests for Types integration in root model."""

    def test_types_dictionary(self) -> None:
        """Should parse types as dictionary of TypeDefinition."""
        from yaml_to_mdd.models.root import DiagnosticDescription

        data = {
            "schema": "opensovd.cda.diagdesc/v1",
            "meta": {
                "author": "Test",
                "domain": "Test",
                "created": "2025-01-01",
                "revision": "1.0.0",
                "description": "Test",
            },
            "ecu": {
                "id": "TEST",
                "name": "Test ECU",
                "addressing": {
                    "doip": {
                        "ip": "192.168.1.1",
                        "logical_address": 0x100,
                        "tester_address": 0x200,
                    }
                },
            },
            "sessions": {"default": {"id": 1}},
            "services": {},
            "access_patterns": {},
            "types": {
                "VehicleSpeed": {
                    "base": "u16",
                    "scale": 0.01,
                    "unit": "km/h",
                },
                "GearPosition": {
                    "base": "u8",
                    "enum": {0: "P", 1: "R", 2: "N", 3: "D"},
                },
            },
        }
        doc = DiagnosticDescription.model_validate(data)
        assert doc.types is not None
        assert len(doc.types) == 2
        assert "VehicleSpeed" in doc.types
        assert "GearPosition" in doc.types
        assert doc.types["VehicleSpeed"].scale == 0.01
        assert doc.types["GearPosition"].enum is not None

    def test_empty_types(self) -> None:
        """Should accept empty types dict."""
        from yaml_to_mdd.models.root import DiagnosticDescription

        data = {
            "schema": "opensovd.cda.diagdesc/v1",
            "meta": {
                "author": "Test",
                "domain": "Test",
                "created": "2025-01-01",
                "revision": "1.0.0",
                "description": "Test",
            },
            "ecu": {
                "id": "TEST",
                "name": "Test ECU",
                "addressing": {
                    "doip": {
                        "ip": "192.168.1.1",
                        "logical_address": 0x100,
                        "tester_address": 0x200,
                    }
                },
            },
            "sessions": {"default": {"id": 1}},
            "services": {},
            "access_patterns": {},
            "types": {},
        }
        doc = DiagnosticDescription.model_validate(data)
        assert doc.types == {}

    def test_null_types(self) -> None:
        """Should accept null/missing types."""
        from yaml_to_mdd.models.root import DiagnosticDescription

        data = {
            "schema": "opensovd.cda.diagdesc/v1",
            "meta": {
                "author": "Test",
                "domain": "Test",
                "created": "2025-01-01",
                "revision": "1.0.0",
                "description": "Test",
            },
            "ecu": {
                "id": "TEST",
                "name": "Test ECU",
                "addressing": {
                    "doip": {
                        "ip": "192.168.1.1",
                        "logical_address": 0x100,
                        "tester_address": 0x200,
                    }
                },
            },
            "sessions": {"default": {"id": 1}},
            "services": {},
            "access_patterns": {},
        }
        doc = DiagnosticDescription.model_validate(data)
        assert doc.types is None
