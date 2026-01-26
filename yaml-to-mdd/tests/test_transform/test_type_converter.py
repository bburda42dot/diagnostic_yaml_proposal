"""Tests for type converter."""


from yaml_to_mdd.ir.types import (
    IRCompuCategory,
    IRDataType,
    IRDiagCodedTypeName,
)
from yaml_to_mdd.models.types import BaseType, Endianness, TypeDefinition
from yaml_to_mdd.transform.type_converter import (
    create_compu_method_for_type,
    create_diag_coded_type,
    determine_physical_type,
    type_definition_to_dop,
)


class TestCreateCompuMethodForType:
    """Tests for create_compu_method_for_type."""

    def test_no_compu_method_for_simple_type(self) -> None:
        """Simple type without scale/enum needs no compu method."""
        type_def = TypeDefinition(base=BaseType.U16)
        result = create_compu_method_for_type(type_def)
        assert result is None

    def test_linear_with_scale(self) -> None:
        """Type with scale should create LINEAR compu method."""
        type_def = TypeDefinition(base=BaseType.U16, scale=0.25)
        result = create_compu_method_for_type(type_def)

        assert result is not None
        assert result.category == IRCompuCategory.LINEAR
        assert len(result.scales) == 1
        assert result.scales[0].factor == 0.25
        assert result.scales[0].offset == 0.0

    def test_linear_with_scale_and_offset(self) -> None:
        """Type with scale and offset should create LINEAR compu method."""
        type_def = TypeDefinition(base=BaseType.U16, scale=0.1, offset=-40.0)
        result = create_compu_method_for_type(type_def)

        assert result is not None
        assert result.category == IRCompuCategory.LINEAR
        assert result.scales[0].factor == 0.1
        assert result.scales[0].offset == -40.0

    def test_linear_with_unit(self) -> None:
        """Linear compu method should include unit."""
        type_def = TypeDefinition(base=BaseType.U16, scale=0.25, unit="rpm")
        result = create_compu_method_for_type(type_def)

        assert result is not None
        assert result.unit == "rpm"

    def test_text_table_for_enum(self) -> None:
        """Type with enum should create TEXT_TABLE compu method."""
        type_def = TypeDefinition(
            base=BaseType.U8,
            enum={0: "OFF", 1: "ON", 2: "AUTO"},
        )
        result = create_compu_method_for_type(type_def)

        assert result is not None
        assert result.category == IRCompuCategory.TEXT_TABLE
        assert len(result.scales) == 3

    def test_text_table_values(self) -> None:
        """TEXT_TABLE should have correct internal/text values."""
        type_def = TypeDefinition(
            base=BaseType.U8,
            enum={0: "INACTIVE", 1: "ACTIVE"},
        )
        result = create_compu_method_for_type(type_def)

        assert result is not None
        # Find the scale for value 1
        scale_1 = next(s for s in result.scales if s.internal_value == 1)
        assert scale_1.text_value == "ACTIVE"


class TestCreateDiagCodedType:
    """Tests for create_diag_coded_type."""

    def test_u8_type(self) -> None:
        """U8 should create 8-bit coded type."""
        type_def = TypeDefinition(base=BaseType.U8)
        result = create_diag_coded_type(type_def)

        assert result.type_name == IRDiagCodedTypeName.STANDARD_LENGTH_TYPE
        assert result.base_data_type == IRDataType.A_UINT_32
        assert result.bit_length == 8

    def test_u16_type(self) -> None:
        """U16 should create 16-bit coded type."""
        type_def = TypeDefinition(base=BaseType.U16)
        result = create_diag_coded_type(type_def)

        assert result.bit_length == 16

    def test_u32_type(self) -> None:
        """U32 should create 32-bit coded type."""
        type_def = TypeDefinition(base=BaseType.U32)
        result = create_diag_coded_type(type_def)

        assert result.bit_length == 32

    def test_signed_type(self) -> None:
        """Signed type should use A_INT_32."""
        type_def = TypeDefinition(base=BaseType.I16)
        result = create_diag_coded_type(type_def)

        assert result.base_data_type == IRDataType.A_INT_32
        assert result.bit_length == 16

    def test_float32_type(self) -> None:
        """F32 should create float32 coded type."""
        type_def = TypeDefinition(base=BaseType.F32)
        result = create_diag_coded_type(type_def)

        assert result.base_data_type == IRDataType.A_FLOAT_32
        assert result.bit_length == 32

    def test_ascii_string_type(self) -> None:
        """ASCII string should use length in bits."""
        type_def = TypeDefinition(base=BaseType.ASCII, length=17)
        result = create_diag_coded_type(type_def)

        assert result.base_data_type == IRDataType.A_ASCIISTRING
        assert result.bit_length == 17 * 8  # 136 bits

    def test_bytes_type(self) -> None:
        """Bytes type should use A_BYTEFIELD."""
        type_def = TypeDefinition(base=BaseType.BYTES, length=10)
        result = create_diag_coded_type(type_def)

        assert result.base_data_type == IRDataType.A_BYTEFIELD
        assert result.bit_length == 10 * 8

    def test_big_endian_default(self) -> None:
        """Default should be big endian (high-low byte order)."""
        type_def = TypeDefinition(base=BaseType.U16)
        result = create_diag_coded_type(type_def)

        assert result.is_high_low_byte_order is True

    def test_little_endian(self) -> None:
        """Little endian should set is_high_low_byte_order to False."""
        type_def = TypeDefinition(base=BaseType.U16, endian=Endianness.LITTLE)
        result = create_diag_coded_type(type_def)

        assert result.is_high_low_byte_order is False

    def test_explicit_bit_length(self) -> None:
        """Explicit bit_length should override default."""
        type_def = TypeDefinition(base=BaseType.U8, bit_length=4)
        result = create_diag_coded_type(type_def)

        assert result.bit_length == 4


class TestDeterminePhysicalType:
    """Tests for determine_physical_type."""

    def test_unsigned_integer(self) -> None:
        """Unsigned integer should return A_UINT_32."""
        type_def = TypeDefinition(base=BaseType.U16)
        result = determine_physical_type(type_def, None)

        assert result == IRDataType.A_UINT_32

    def test_signed_integer(self) -> None:
        """Signed integer should return A_INT_32."""
        type_def = TypeDefinition(base=BaseType.I16)
        result = determine_physical_type(type_def, None)

        assert result == IRDataType.A_INT_32

    def test_float32(self) -> None:
        """F32 should return A_FLOAT_32."""
        type_def = TypeDefinition(base=BaseType.F32)
        result = determine_physical_type(type_def, None)

        assert result == IRDataType.A_FLOAT_32

    def test_float64(self) -> None:
        """F64 should return A_FLOAT_64."""
        type_def = TypeDefinition(base=BaseType.F64)
        result = determine_physical_type(type_def, None)

        assert result == IRDataType.A_FLOAT_64

    def test_ascii(self) -> None:
        """ASCII should return A_ASCIISTRING."""
        type_def = TypeDefinition(base=BaseType.ASCII, length=10)
        result = determine_physical_type(type_def, None)

        assert result == IRDataType.A_ASCIISTRING

    def test_bytes(self) -> None:
        """Bytes should return A_BYTEFIELD."""
        type_def = TypeDefinition(base=BaseType.BYTES, length=10)
        result = determine_physical_type(type_def, None)

        assert result == IRDataType.A_BYTEFIELD

    def test_enum_returns_string(self) -> None:
        """Enum (TEXT_TABLE) should return A_ASCIISTRING."""
        from yaml_to_mdd.ir.types import IRCompuCategory, IRCompuMethod

        type_def = TypeDefinition(base=BaseType.U8, enum={0: "OFF", 1: "ON"})
        compu_method = IRCompuMethod(category=IRCompuCategory.TEXT_TABLE, scales=())
        result = determine_physical_type(type_def, compu_method)

        assert result == IRDataType.A_ASCIISTRING


class TestTypeDefinitionToDop:
    """Tests for type_definition_to_dop."""

    def test_simple_u16(self) -> None:
        """Should create DOP for simple U16 type."""
        type_def = TypeDefinition(base=BaseType.U16)
        dop = type_definition_to_dop("EngineSpeed", type_def)

        assert dop.short_name == "EngineSpeed"
        assert dop.diag_coded_type is not None
        assert dop.diag_coded_type.bit_length == 16

    def test_scaled_type_with_unit(self) -> None:
        """Should create DOP with compu method and unit."""
        type_def = TypeDefinition(base=BaseType.U16, scale=0.25, unit="rpm")
        dop = type_definition_to_dop("EngineSpeed", type_def)

        assert dop.unit == "rpm"
        assert dop.compu_method is not None
        assert dop.compu_method.category == IRCompuCategory.LINEAR

    def test_enum_type(self) -> None:
        """Should create DOP with TEXT_TABLE for enum."""
        type_def = TypeDefinition(
            base=BaseType.U8,
            enum={0: "OFF", 1: "ON"},
        )
        dop = type_definition_to_dop("Status", type_def)

        assert dop.compu_method is not None
        assert dop.compu_method.category == IRCompuCategory.TEXT_TABLE
        assert dop.physical_type == IRDataType.A_ASCIISTRING

    def test_string_type(self) -> None:
        """Should create DOP for ASCII string type."""
        type_def = TypeDefinition(base=BaseType.ASCII, length=17)
        dop = type_definition_to_dop("VIN", type_def)

        assert dop.diag_coded_type is not None
        assert dop.diag_coded_type.base_data_type == IRDataType.A_ASCIISTRING
        assert dop.diag_coded_type.bit_length == 17 * 8
