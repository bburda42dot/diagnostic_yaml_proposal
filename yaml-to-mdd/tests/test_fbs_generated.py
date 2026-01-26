"""Tests to verify FlatBuffers generated code is working."""

from __future__ import annotations

import flatbuffers


class TestFlatBuffersImports:
    """Test that generated FlatBuffers modules can be imported."""

    def test_import_fbs_generated_package(self) -> None:
        """Should be able to import the fbs_generated package."""
        from yaml_to_mdd import fbs_generated

        assert fbs_generated is not None

    def test_import_dataformat_subpackage(self) -> None:
        """Should be able to import the dataformat subpackage."""
        from yaml_to_mdd.fbs_generated import dataformat

        assert dataformat is not None

    def test_import_diag_service(self) -> None:
        """Should be able to import DiagService."""
        from yaml_to_mdd.fbs_generated.dataformat.DiagService import DiagService

        assert DiagService is not None

    def test_import_dop(self) -> None:
        """Should be able to import DOP."""
        from yaml_to_mdd.fbs_generated.dataformat.DOP import DOP

        assert DOP is not None

    def test_import_param(self) -> None:
        """Should be able to import Param."""
        from yaml_to_mdd.fbs_generated.dataformat.Param import Param

        assert Param is not None

    def test_import_request(self) -> None:
        """Should be able to import Request."""
        from yaml_to_mdd.fbs_generated.dataformat.Request import Request

        assert Request is not None

    def test_import_response(self) -> None:
        """Should be able to import Response."""
        from yaml_to_mdd.fbs_generated.dataformat.Response import Response

        assert Response is not None

    def test_import_text(self) -> None:
        """Should be able to import Text."""
        from yaml_to_mdd.fbs_generated.dataformat.Text import Text, TextT

        assert Text is not None
        assert TextT is not None


class TestDataTypeEnum:
    """Test the DataType enum values."""

    def test_data_type_exists(self) -> None:
        """Should be able to import DataType."""
        from yaml_to_mdd.fbs_generated.dataformat.DataType import DataType

        assert DataType is not None

    def test_integer_types(self) -> None:
        """DataType should have integer type constants."""
        from yaml_to_mdd.fbs_generated.dataformat.DataType import DataType

        assert DataType.A_INT_32 == 0
        assert DataType.A_UINT_32 == 1

    def test_float_types(self) -> None:
        """DataType should have float type constants."""
        from yaml_to_mdd.fbs_generated.dataformat.DataType import DataType

        assert DataType.A_FLOAT_32 == 2
        assert DataType.A_FLOAT_64 == 7

    def test_string_types(self) -> None:
        """DataType should have string type constants."""
        from yaml_to_mdd.fbs_generated.dataformat.DataType import DataType

        assert DataType.A_ASCIISTRING == 3
        assert DataType.A_UTF_8_STRING == 4
        assert DataType.A_UNICODE_2_STRING == 5

    def test_bytefield_type(self) -> None:
        """DataType should have bytefield type constant."""
        from yaml_to_mdd.fbs_generated.dataformat.DataType import DataType

        assert DataType.A_BYTEFIELD == 6


class TestDiagCodedTypeName:
    """Test DiagCodedTypeName enum values."""

    def test_diag_coded_type_name_exists(self) -> None:
        """Should be able to import DiagCodedTypeName."""
        from yaml_to_mdd.fbs_generated.dataformat.DiagCodedTypeName import (
            DiagCodedTypeName,
        )

        assert DiagCodedTypeName is not None

    def test_standard_length_type(self) -> None:
        """Should have STANDARD_LENGTH_TYPE constant."""
        from yaml_to_mdd.fbs_generated.dataformat.DiagCodedTypeName import (
            DiagCodedTypeName,
        )

        assert hasattr(DiagCodedTypeName, "STANDARD_LENGTH_TYPE")

    def test_leading_length_info_type(self) -> None:
        """Should have LEADING_LENGTH_INFO_TYPE constant."""
        from yaml_to_mdd.fbs_generated.dataformat.DiagCodedTypeName import (
            DiagCodedTypeName,
        )

        assert hasattr(DiagCodedTypeName, "LEADING_LENGTH_INFO_TYPE")


class TestTextSerialization:
    """Test serialization/deserialization of Text table."""

    def test_create_text_with_object_api(self) -> None:
        """Should be able to create a Text object using the Object API."""
        from yaml_to_mdd.fbs_generated.dataformat.Text import TextT

        text = TextT()
        text.value = "Test Value"
        text.ti = None

        assert text.value == "Test Value"
        assert text.ti is None

    def test_serialize_text(self) -> None:
        """Should be able to serialize a Text object to bytes."""
        from yaml_to_mdd.fbs_generated.dataformat.Text import TextT

        text = TextT()
        text.value = "Hello World"
        text.ti = None

        builder = flatbuffers.Builder(256)
        offset = text.Pack(builder)
        builder.Finish(offset)
        buf = bytes(builder.Output())

        assert len(buf) > 0
        assert isinstance(buf, bytes)

    def test_deserialize_text(self) -> None:
        """Should be able to deserialize a Text object from bytes."""
        from yaml_to_mdd.fbs_generated.dataformat.Text import Text, TextT

        # Create and serialize
        text = TextT()
        text.value = "Test Deserialization"
        text.ti = "test-ti"

        builder = flatbuffers.Builder(256)
        offset = text.Pack(builder)
        builder.Finish(offset)
        buf = bytes(builder.Output())

        # Deserialize
        text_read = Text.GetRootAs(buf, 0)
        assert text_read.Value().decode("utf-8") == "Test Deserialization"
        assert text_read.Ti().decode("utf-8") == "test-ti"

    def test_roundtrip_text(self) -> None:
        """Text should survive serialization round-trip."""
        from yaml_to_mdd.fbs_generated.dataformat.Text import Text, TextT

        original = TextT()
        original.value = "Round Trip Value"
        original.ti = None

        # Serialize
        builder = flatbuffers.Builder(256)
        offset = original.Pack(builder)
        builder.Finish(offset)
        buf = bytes(builder.Output())

        # Deserialize
        read = Text.GetRootAs(buf, 0)

        assert read.Value().decode("utf-8") == original.value
        assert read.Ti() is None


class TestCompuCategory:
    """Test CompuCategory enum."""

    def test_compu_category_exists(self) -> None:
        """Should be able to import CompuCategory."""
        from yaml_to_mdd.fbs_generated.dataformat.CompuCategory import CompuCategory

        assert CompuCategory is not None

    def test_has_identical_category(self) -> None:
        """Should have IDENTICAL category."""
        from yaml_to_mdd.fbs_generated.dataformat.CompuCategory import CompuCategory

        assert hasattr(CompuCategory, "IDENTICAL")

    def test_has_linear_category(self) -> None:
        """Should have LINEAR category."""
        from yaml_to_mdd.fbs_generated.dataformat.CompuCategory import CompuCategory

        assert hasattr(CompuCategory, "LINEAR")


class TestBuilderBasics:
    """Test basic FlatBuffers builder operations."""

    def test_builder_creation(self) -> None:
        """Should be able to create a FlatBuffers builder."""
        builder = flatbuffers.Builder(256)
        assert builder is not None

    def test_builder_create_string(self) -> None:
        """Should be able to create a string in the builder."""
        builder = flatbuffers.Builder(256)
        string_offset = builder.CreateString("test")
        assert string_offset > 0

    def test_builder_output(self) -> None:
        """Builder output should return bytes-like object."""
        from yaml_to_mdd.fbs_generated.dataformat.Text import TextT

        text = TextT()
        text.value = "test"

        builder = flatbuffers.Builder(256)
        offset = text.Pack(builder)
        builder.Finish(offset)
        output = builder.Output()

        # Output is a bytearray
        assert isinstance(output, bytearray)
        # Can convert to bytes
        assert isinstance(bytes(output), bytes)
