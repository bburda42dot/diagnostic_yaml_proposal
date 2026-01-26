"""Tests for IR type models."""

from yaml_to_mdd.ir.types import (
    IRDOP,
    IRCompuCategory,
    IRCompuMethod,
    IRCompuScale,
    IRDataType,
    IRDiagCodedType,
    IRDiagCodedTypeName,
    IRLimit,
)


class TestIRDataType:
    """Tests for IRDataType enum."""

    def test_data_type_values(self) -> None:
        """Should have correct data type values."""
        assert IRDataType.A_INT_32.value == 0
        assert IRDataType.A_UINT_32.value == 1
        assert IRDataType.A_FLOAT_32.value == 2
        assert IRDataType.A_ASCIISTRING.value == 3

    def test_all_data_types(self) -> None:
        """Should have 8 data types."""
        assert len(IRDataType) == 8


class TestIRCompuCategory:
    """Tests for IRCompuCategory enum."""

    def test_category_values(self) -> None:
        """Should have correct category values."""
        assert IRCompuCategory.IDENTICAL.value == 0
        assert IRCompuCategory.LINEAR.value == 1
        assert IRCompuCategory.TEXT_TABLE.value == 3

    def test_all_categories(self) -> None:
        """Should have 8 categories."""
        assert len(IRCompuCategory) == 8


class TestIRDiagCodedTypeName:
    """Tests for IRDiagCodedTypeName enum."""

    def test_type_name_values(self) -> None:
        """Should have correct type name values."""
        assert IRDiagCodedTypeName.LEADING_LENGTH_INFO_TYPE.value == 0
        assert IRDiagCodedTypeName.STANDARD_LENGTH_TYPE.value == 3


class TestIRLimit:
    """Tests for IRLimit dataclass."""

    def test_numeric_limit(self) -> None:
        """Should create numeric limit."""
        limit = IRLimit(value=100)
        assert limit.value == 100
        assert limit.interval_type == "CLOSED"

    def test_limit_with_interval_type(self) -> None:
        """Should create limit with custom interval type."""
        limit = IRLimit(value=0, interval_type="OPEN")
        assert limit.interval_type == "OPEN"

    def test_limit_is_frozen(self) -> None:
        """Limit should be immutable."""
        limit = IRLimit(value=100)
        try:
            limit.value = 200  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass  # Expected


class TestIRCompuScale:
    """Tests for IRCompuScale dataclass."""

    def test_linear_scale(self) -> None:
        """Should create linear scale with offset and factor."""
        scale = IRCompuScale(
            offset=0.0,
            factor=0.1,
            short_label="rpm",
        )
        assert scale.factor == 0.1
        assert scale.offset == 0.0
        assert scale.short_label == "rpm"

    def test_text_scale(self) -> None:
        """Should create text table scale."""
        scale = IRCompuScale(
            internal_value=0,
            text_value="OFF",
        )
        assert scale.internal_value == 0
        assert scale.text_value == "OFF"

    def test_scale_with_limits(self) -> None:
        """Should create scale with limits."""
        scale = IRCompuScale(
            lower_limit=IRLimit(value=0),
            upper_limit=IRLimit(value=255),
            factor=1.0,
        )
        assert scale.lower_limit is not None
        assert scale.lower_limit.value == 0

    def test_scale_is_frozen(self) -> None:
        """Scale should be immutable."""
        scale = IRCompuScale(factor=1.0)
        try:
            scale.factor = 2.0  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass  # Expected


class TestIRCompuMethod:
    """Tests for IRCompuMethod dataclass."""

    def test_identical_method(self) -> None:
        """Should create identical (no conversion) method."""
        method = IRCompuMethod(
            category=IRCompuCategory.IDENTICAL,
        )
        assert method.category == IRCompuCategory.IDENTICAL
        assert method.scales == ()
        assert method.unit is None

    def test_linear_method(self) -> None:
        """Should create linear conversion method."""
        scale = IRCompuScale(offset=0.0, factor=0.1)
        method = IRCompuMethod(
            category=IRCompuCategory.LINEAR,
            scales=(scale,),
            unit="rpm",
        )
        assert method.category == IRCompuCategory.LINEAR
        assert len(method.scales) == 1
        assert method.unit == "rpm"

    def test_text_table_method(self) -> None:
        """Should create text table method with multiple scales."""
        scales = (
            IRCompuScale(internal_value=0, text_value="OFF"),
            IRCompuScale(internal_value=1, text_value="ON"),
        )
        method = IRCompuMethod(
            category=IRCompuCategory.TEXT_TABLE,
            scales=scales,
        )
        assert len(method.scales) == 2

    def test_method_is_frozen(self) -> None:
        """Method should be immutable."""
        method = IRCompuMethod(category=IRCompuCategory.IDENTICAL)
        try:
            method.unit = "test"  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass  # Expected


class TestIRDiagCodedType:
    """Tests for IRDiagCodedType dataclass."""

    def test_standard_length_type(self) -> None:
        """Should create standard length type."""
        coded_type = IRDiagCodedType(
            type_name=IRDiagCodedTypeName.STANDARD_LENGTH_TYPE,
            base_data_type=IRDataType.A_UINT_32,
            bit_length=16,
        )
        assert coded_type.type_name == IRDiagCodedTypeName.STANDARD_LENGTH_TYPE
        assert coded_type.base_data_type == IRDataType.A_UINT_32
        assert coded_type.bit_length == 16

    def test_default_values(self) -> None:
        """Should have correct defaults."""
        coded_type = IRDiagCodedType(
            type_name=IRDiagCodedTypeName.STANDARD_LENGTH_TYPE,
            base_data_type=IRDataType.A_UINT_32,
        )
        assert coded_type.bit_length == 8
        assert coded_type.is_high_low_byte_order is True

    def test_min_max_length_type(self) -> None:
        """Should create variable length type."""
        coded_type = IRDiagCodedType(
            type_name=IRDiagCodedTypeName.MIN_MAX_LENGTH_TYPE,
            base_data_type=IRDataType.A_ASCIISTRING,
            min_length=1,
            max_length=20,
            termination="ZERO",
        )
        assert coded_type.min_length == 1
        assert coded_type.max_length == 20
        assert coded_type.termination == "ZERO"

    def test_coded_type_is_frozen(self) -> None:
        """Coded type should be immutable."""
        coded_type = IRDiagCodedType(
            type_name=IRDiagCodedTypeName.STANDARD_LENGTH_TYPE,
            base_data_type=IRDataType.A_UINT_32,
        )
        try:
            coded_type.bit_length = 32  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass  # Expected


class TestIRDOP:
    """Tests for IRDOP dataclass."""

    def test_simple_dop(self) -> None:
        """Should create simple DOP."""
        dop = IRDOP(
            short_name="EngineSpeed",
            long_name="Engine Speed in RPM",
            unit="rpm",
        )
        assert dop.short_name == "EngineSpeed"
        assert dop.long_name == "Engine Speed in RPM"
        assert dop.unit == "rpm"

    def test_dop_with_coded_type(self) -> None:
        """Should create DOP with coded type."""
        coded_type = IRDiagCodedType(
            type_name=IRDiagCodedTypeName.STANDARD_LENGTH_TYPE,
            base_data_type=IRDataType.A_UINT_32,
            bit_length=16,
        )
        dop = IRDOP(
            short_name="EngineSpeed",
            diag_coded_type=coded_type,
        )
        assert dop.diag_coded_type is not None
        assert dop.diag_coded_type.bit_length == 16

    def test_dop_with_compu_method(self) -> None:
        """Should create DOP with computation method."""
        scale = IRCompuScale(offset=0.0, factor=0.25)
        method = IRCompuMethod(
            category=IRCompuCategory.LINEAR,
            scales=(scale,),
            unit="rpm",
        )
        dop = IRDOP(
            short_name="EngineSpeed",
            compu_method=method,
        )
        assert dop.compu_method is not None
        assert dop.compu_method.unit == "rpm"

    def test_dop_is_hashable(self) -> None:
        """DOP should be hashable for use in sets/dicts."""
        dop1 = IRDOP(short_name="DOP1")
        dop2 = IRDOP(short_name="DOP2")
        dop_set = {dop1, dop2}
        assert len(dop_set) == 2

    def test_dop_hash_by_name(self) -> None:
        """DOPs with same name should have same hash."""
        dop1 = IRDOP(short_name="Same", long_name="First")
        dop2 = IRDOP(short_name="Same", long_name="Second")
        assert hash(dop1) == hash(dop2)

    def test_dop_is_frozen(self) -> None:
        """DOP should be immutable."""
        dop = IRDOP(short_name="Test")
        try:
            dop.short_name = "Changed"  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass  # Expected

    def test_minimal_dop(self) -> None:
        """Should create DOP with only required fields."""
        dop = IRDOP(short_name="MinimalDOP")
        assert dop.short_name == "MinimalDOP"
        assert dop.long_name is None
        assert dop.diag_coded_type is None
        assert dop.compu_method is None
        assert dop.unit is None
