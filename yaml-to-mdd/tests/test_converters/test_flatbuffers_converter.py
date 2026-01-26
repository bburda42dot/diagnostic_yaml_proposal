"""Tests for FlatBuffers converter."""

import pytest
from yaml_to_mdd.converters.flatbuffers_converter import IRToFlatBuffersConverter
from yaml_to_mdd.ir.database import IRDatabase
from yaml_to_mdd.ir.services import IRDiagService, IRParam, IRRequest, IRResponse
from yaml_to_mdd.ir.types import (
    IRDOP,
    IRCompuCategory,
    IRCompuMethod,
    IRCompuScale,
    IRDataType,
    IRDiagCodedType,
    IRDiagCodedTypeName,
)


class TestIRToFlatBuffersConverterBasics:
    """Basic tests for FlatBuffers converter."""

    @pytest.fixture
    def minimal_db(self) -> IRDatabase:
        """Create minimal IR database."""
        return IRDatabase(
            ecu_name="TestECU",
            revision="1.0.0",
        )

    def test_create_converter(self) -> None:
        """Should create converter instance."""
        converter = IRToFlatBuffersConverter()
        assert converter is not None

    def test_convert_empty_db(self, minimal_db: IRDatabase) -> None:
        """Should convert empty database."""
        converter = IRToFlatBuffersConverter()
        result = converter.convert(minimal_db)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_convert_returns_bytes(self, minimal_db: IRDatabase) -> None:
        """Should return bytes object."""
        converter = IRToFlatBuffersConverter()
        result = converter.convert(minimal_db)

        assert isinstance(result, bytes)


class TestIRToFlatBuffersConverterDOPs:
    """Tests for DOP conversion."""

    @pytest.fixture
    def db_with_dop(self) -> IRDatabase:
        """Create database with a DOP."""
        db = IRDatabase(
            ecu_name="TestECU",
            revision="1.0.0",
        )
        dop = IRDOP(
            short_name="EngineSpeed",
            diag_coded_type=IRDiagCodedType(
                type_name=IRDiagCodedTypeName.STANDARD_LENGTH_TYPE,
                base_data_type=IRDataType.A_UINT_32,
                bit_length=16,
            ),
        )
        db.add_dop(dop)
        return db

    def test_convert_with_simple_dop(self, db_with_dop: IRDatabase) -> None:
        """Should convert database with simple DOP."""
        converter = IRToFlatBuffersConverter()
        result = converter.convert(db_with_dop)

        assert len(result) > 0

    def test_convert_with_compu_method_linear(self) -> None:
        """Should convert DOP with linear computation method."""
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")

        dop = IRDOP(
            short_name="Temperature",
            diag_coded_type=IRDiagCodedType(
                type_name=IRDiagCodedTypeName.STANDARD_LENGTH_TYPE,
                base_data_type=IRDataType.A_UINT_32,
                bit_length=8,
            ),
            compu_method=IRCompuMethod(
                category=IRCompuCategory.LINEAR,
                scales=(
                    IRCompuScale(
                        offset=-40.0,
                        factor=1.0,
                    ),
                ),
            ),
        )
        db.add_dop(dop)

        converter = IRToFlatBuffersConverter()
        result = converter.convert(db)

        assert len(result) > 0

    def test_convert_with_compu_method_text_table(self) -> None:
        """Should convert DOP with text table computation method."""
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")

        dop = IRDOP(
            short_name="Status",
            diag_coded_type=IRDiagCodedType(
                type_name=IRDiagCodedTypeName.STANDARD_LENGTH_TYPE,
                base_data_type=IRDataType.A_UINT_32,
                bit_length=8,
            ),
            compu_method=IRCompuMethod(
                category=IRCompuCategory.TEXT_TABLE,
                scales=(
                    IRCompuScale(internal_value=0, text_value="OFF"),
                    IRCompuScale(internal_value=1, text_value="ON"),
                ),
            ),
        )
        db.add_dop(dop)

        converter = IRToFlatBuffersConverter()
        result = converter.convert(db)

        assert len(result) > 0


class TestIRToFlatBuffersConverterServices:
    """Tests for service conversion."""

    @pytest.fixture
    def db_with_service(self) -> IRDatabase:
        """Create database with a service."""
        db = IRDatabase(
            ecu_name="TestECU",
            revision="1.0.0",
        )

        # Add a DOP for the service to reference
        dop = IRDOP(
            short_name="DOP_DID",
            diag_coded_type=IRDiagCodedType(
                type_name=IRDiagCodedTypeName.STANDARD_LENGTH_TYPE,
                base_data_type=IRDataType.A_UINT_32,
                bit_length=16,
            ),
        )
        db.add_dop(dop)

        service = IRDiagService(
            short_name="ReadEngineSpeed",
            service_id=0x22,
            request=IRRequest(
                short_name="ReadEngineSpeed_Request",
                params=(
                    IRParam(short_name="SID", byte_position=0, semantic="SERVICE_ID"),
                    IRParam(short_name="DID", byte_position=1, dop_ref="DOP_DID"),
                ),
            ),
            positive_response=IRResponse(
                short_name="ReadEngineSpeed_Response",
                params=(
                    IRParam(short_name="SID", byte_position=0, semantic="SERVICE_ID"),
                    IRParam(short_name="DID", byte_position=1, dop_ref="DOP_DID"),
                    IRParam(short_name="Data", byte_position=3, semantic="DATA"),
                ),
            ),
        )
        db.add_service(service)
        return db

    def test_convert_with_service(self, db_with_service: IRDatabase) -> None:
        """Should convert database with service."""
        converter = IRToFlatBuffersConverter()
        result = converter.convert(db_with_service)

        assert len(result) > 0

    def test_convert_service_with_request_only(self) -> None:
        """Should convert service with only request."""
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")

        service = IRDiagService(
            short_name="TesterPresent",
            service_id=0x3E,
            request=IRRequest(
                short_name="TesterPresent_Request",
                params=(IRParam(short_name="SID", byte_position=0),),
            ),
        )
        db.add_service(service)

        converter = IRToFlatBuffersConverter()
        result = converter.convert(db)

        assert len(result) > 0

    def test_convert_multiple_services(self) -> None:
        """Should convert multiple services."""
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")

        for i in range(5):
            service = IRDiagService(
                short_name=f"Service_{i}",
                service_id=0x22 + i,
                request=IRRequest(
                    short_name=f"Service_{i}_Request",
                    params=(IRParam(short_name="SID", byte_position=0),),
                ),
            )
            db.add_service(service)

        converter = IRToFlatBuffersConverter()
        result = converter.convert(db)

        assert len(result) > 0


class TestIRToFlatBuffersConverterIntegration:
    """Integration tests for FlatBuffers converter."""

    def test_convert_complete_database(self) -> None:
        """Should convert complete database with DOPs and services."""
        db = IRDatabase(
            ecu_name="CompleteECU",
            revision="2.0.0",
            author="Test Author",
            description="Complete test ECU",
        )

        # Add various DOPs
        dop_u8 = IRDOP(
            short_name="U8_Type",
            diag_coded_type=IRDiagCodedType(
                type_name=IRDiagCodedTypeName.STANDARD_LENGTH_TYPE,
                base_data_type=IRDataType.A_UINT_32,
                bit_length=8,
            ),
        )
        dop_u16 = IRDOP(
            short_name="U16_Type",
            diag_coded_type=IRDiagCodedType(
                type_name=IRDiagCodedTypeName.STANDARD_LENGTH_TYPE,
                base_data_type=IRDataType.A_UINT_32,
                bit_length=16,
            ),
        )
        db.add_dop(dop_u8)
        db.add_dop(dop_u16)

        # Add services
        read_service = IRDiagService(
            short_name="ReadData",
            service_id=0x22,
            request=IRRequest(
                short_name="ReadData_Request",
                params=(
                    IRParam(short_name="SID", byte_position=0),
                    IRParam(short_name="DID", byte_position=1, dop_ref="U16_Type"),
                ),
            ),
            positive_response=IRResponse(
                short_name="ReadData_Response",
                params=(
                    IRParam(short_name="SID", byte_position=0),
                    IRParam(short_name="DID", byte_position=1, dop_ref="U16_Type"),
                    IRParam(short_name="Data", byte_position=3, dop_ref="U8_Type"),
                ),
            ),
        )
        db.add_service(read_service)

        converter = IRToFlatBuffersConverter()
        result = converter.convert(db)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_convert_idempotent(self) -> None:
        """Converting same database twice should produce same result."""
        db = IRDatabase(
            ecu_name="TestECU",
            revision="1.0.0",
        )
        db.add_dop(
            IRDOP(
                short_name="TestDOP",
                diag_coded_type=IRDiagCodedType(
                    type_name=IRDiagCodedTypeName.STANDARD_LENGTH_TYPE,
                    base_data_type=IRDataType.A_UINT_32,
                    bit_length=8,
                ),
            )
        )

        converter = IRToFlatBuffersConverter()

        result1 = converter.convert(db)
        result2 = converter.convert(db)

        assert result1 == result2

    def test_builder_size_parameter(self) -> None:
        """Should respect custom builder size."""
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")

        # Create with small buffer
        converter_small = IRToFlatBuffersConverter(builder_size=1024)
        result_small = converter_small.convert(db)

        # Create with large buffer
        converter_large = IRToFlatBuffersConverter(builder_size=10 * 1024 * 1024)
        result_large = converter_large.convert(db)

        # Results should be the same (builder auto-grows)
        assert result_small == result_large
