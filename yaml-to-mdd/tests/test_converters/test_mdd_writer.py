"""Tests for MDD writer."""

import tempfile
from pathlib import Path
from typing import Any

import pytest
from yaml_to_mdd.converters.mdd_writer import FILE_MAGIC, MDDWriter, convert_yaml_to_mdd
from yaml_to_mdd.ir.database import IRDatabase
from yaml_to_mdd.ir.services import IRDiagService, IRParam, IRRequest
from yaml_to_mdd.ir.types import (
    IRDOP,
    IRDataType,
    IRDiagCodedType,
    IRDiagCodedTypeName,
)
from yaml_to_mdd.proto_generated import Chunk, MDDFile


class TestMDDWriterBasics:
    """Basic tests for MDD writer."""

    @pytest.fixture
    def minimal_db(self) -> IRDatabase:
        """Create minimal IR database."""
        return IRDatabase(
            ecu_name="TestECU",
            revision="1.0.0",
            author="Test Author",
            description="Test Description",
        )

    def test_create_writer(self) -> None:
        """Should create writer instance."""
        writer = MDDWriter()
        assert writer is not None

    def test_create_writer_with_version(self) -> None:
        """Should create writer with custom version."""
        writer = MDDWriter(version="2.0.0")
        assert writer is not None

    def test_write_bytes(self, minimal_db: IRDatabase) -> None:
        """Should write MDD bytes."""
        writer = MDDWriter()
        result = writer.write_bytes(minimal_db)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_write_file(self, minimal_db: IRDatabase) -> None:
        """Should write MDD file."""
        writer = MDDWriter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.mdd"
            writer.write(minimal_db, output_path)

            assert output_path.exists()
            assert output_path.stat().st_size > 0

    def test_write_creates_parent_dirs(self, minimal_db: IRDatabase) -> None:
        """Should create parent directories if needed."""
        writer = MDDWriter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "dir" / "test.mdd"
            writer.write(minimal_db, output_path)

            assert output_path.exists()


class TestMDDWriterProtobufStructure:
    """Tests for Protobuf container structure."""

    @pytest.fixture
    def minimal_db(self) -> IRDatabase:
        """Create minimal IR database."""
        return IRDatabase(
            ecu_name="TestECU",
            revision="1.0.0",
            author="Test Author",
            description="Test Description",
        )

    def test_read_back_protobuf(self, minimal_db: IRDatabase) -> None:
        """Should be able to read back as Protobuf."""
        writer = MDDWriter()
        mdd_bytes = writer.write_bytes(minimal_db)

        # Read back (strip FILE_MAGIC header)
        mdd = MDDFile()
        mdd.ParseFromString(mdd_bytes[len(FILE_MAGIC) :])

        assert mdd.ecu_name == "TestECU"
        assert mdd.revision == "1.0.0"

    def test_protobuf_version(self, minimal_db: IRDatabase) -> None:
        """Should include version in Protobuf."""
        writer = MDDWriter(version="2.5.0")
        mdd_bytes = writer.write_bytes(minimal_db)

        mdd = MDDFile()
        mdd.ParseFromString(mdd_bytes[len(FILE_MAGIC) :])

        assert mdd.version == "2.5.0"

    def test_protobuf_metadata(self, minimal_db: IRDatabase) -> None:
        """Should include metadata in Protobuf."""
        writer = MDDWriter()
        mdd_bytes = writer.write_bytes(minimal_db)

        mdd = MDDFile()
        mdd.ParseFromString(mdd_bytes[len(FILE_MAGIC) :])

        assert mdd.metadata["author"] == "Test Author"
        assert mdd.metadata["description"] == "Test Description"
        assert "schema_version" in mdd.metadata

    def test_protobuf_chunk_structure(self, minimal_db: IRDatabase) -> None:
        """Should have proper chunk structure."""
        writer = MDDWriter()
        mdd_bytes = writer.write_bytes(minimal_db)

        mdd = MDDFile()
        mdd.ParseFromString(mdd_bytes[len(FILE_MAGIC) :])

        assert len(mdd.chunks) == 1
        chunk = mdd.chunks[0]

        assert chunk.type == Chunk.DataType.DIAGNOSTIC_DESCRIPTION
        assert chunk.name == "diagnostic_description"
        assert chunk.mimeType == "application/x-flatbuffers"
        assert len(chunk.data) > 0

    def test_protobuf_chunk_metadata(self, minimal_db: IRDatabase) -> None:
        """Should include chunk metadata."""
        writer = MDDWriter()
        mdd_bytes = writer.write_bytes(minimal_db)

        mdd = MDDFile()
        mdd.ParseFromString(mdd_bytes[len(FILE_MAGIC) :])

        chunk = mdd.chunks[0]
        assert chunk.metadata["flatbuffers_schema"] == "diagnostic_description.fbs"


class TestMDDWriterCompression:
    """Tests for MDD compression support."""

    @pytest.fixture
    def minimal_db(self) -> IRDatabase:
        """Create minimal IR database."""
        return IRDatabase(
            ecu_name="TestECU",
            revision="1.0.0",
        )

    def test_write_with_gzip_compression(self, minimal_db: IRDatabase) -> None:
        """Should write with gzip compression."""
        writer = MDDWriter(compression="gzip")
        mdd_bytes = writer.write_bytes(minimal_db)

        mdd = MDDFile()
        mdd.ParseFromString(mdd_bytes[len(FILE_MAGIC) :])

        chunk = mdd.chunks[0]
        assert chunk.compression_algorithm == "gzip"
        assert chunk.uncompressed_size > 0

    def test_gzip_compressed_is_smaller(self) -> None:
        """Gzip compressed data should be different (usually smaller for large data)."""
        # Create larger database for better compression test
        db = IRDatabase(ecu_name="TestECU", revision="1.0.0")
        for i in range(100):
            db.add_dop(
                IRDOP(
                    short_name=f"DOP_{i}",
                    diag_coded_type=IRDiagCodedType(
                        type_name=IRDiagCodedTypeName.STANDARD_LENGTH_TYPE,
                        base_data_type=IRDataType.A_UINT_32,
                        bit_length=8,
                    ),
                )
            )

        writer_uncompressed = MDDWriter()
        writer_compressed = MDDWriter(compression="gzip")

        bytes_uncompressed = writer_uncompressed.write_bytes(db)
        bytes_compressed = writer_compressed.write_bytes(db)

        # Compressed should be different
        assert bytes_uncompressed != bytes_compressed

    def test_invalid_compression_raises_error(self, minimal_db: IRDatabase) -> None:
        """Should raise error for unknown compression."""
        writer = MDDWriter(compression="unknown_algo")

        with pytest.raises(ValueError, match="Unknown compression"):
            writer.write_bytes(minimal_db)


class TestMDDWriterIntegration:
    """Integration tests for MDD writer."""

    def test_write_complete_database(self) -> None:
        """Should write complete database with DOPs and services."""
        db = IRDatabase(
            ecu_name="CompleteECU",
            revision="2.0.0",
            author="Integration Test",
            description="Complete integration test",
        )

        # Add DOPs
        db.add_dop(
            IRDOP(
                short_name="DID_Type",
                diag_coded_type=IRDiagCodedType(
                    type_name=IRDiagCodedTypeName.STANDARD_LENGTH_TYPE,
                    base_data_type=IRDataType.A_UINT_32,
                    bit_length=16,
                ),
            )
        )

        # Add service
        db.add_service(
            IRDiagService(
                short_name="ReadDID",
                service_id=0x22,
                request=IRRequest(
                    short_name="ReadDID_Request",
                    params=(
                        IRParam(short_name="SID", byte_position=0),
                        IRParam(short_name="DID", byte_position=1, dop_ref="DID_Type"),
                    ),
                ),
            )
        )

        writer = MDDWriter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "complete.mdd"
            writer.write(db, output_path)

            # Read back and verify
            with open(output_path, "rb") as f:
                mdd = MDDFile()
                mdd.ParseFromString(f.read()[len(FILE_MAGIC) :])

            assert mdd.ecu_name == "CompleteECU"
            assert mdd.revision == "2.0.0"
            assert len(mdd.chunks) == 1


class TestConvertYamlToMddFunction:
    """Tests for high-level convert function."""

    @pytest.fixture
    def yaml_file(self, valid_base_data: dict[str, Any]) -> Path:
        """Create a temporary YAML file."""
        import yaml

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_base_data, f)
            return Path(f.name)

    def test_convert_yaml_to_mdd(self, yaml_file: Path) -> None:
        """Should convert YAML file to MDD."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.mdd"
            convert_yaml_to_mdd(yaml_file, output_path)

            assert output_path.exists()
            assert output_path.stat().st_size > 0

            # Verify it's valid Protobuf
            with open(output_path, "rb") as f:
                mdd = MDDFile()
                mdd.ParseFromString(f.read()[len(FILE_MAGIC) :])

            assert mdd.ecu_name == "ECM_V1"

    def test_convert_yaml_to_mdd_with_compression(self, yaml_file: Path) -> None:
        """Should convert with compression."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output_compressed.mdd"
            convert_yaml_to_mdd(yaml_file, output_path, compression="gzip")

            with open(output_path, "rb") as f:
                mdd = MDDFile()
                mdd.ParseFromString(f.read()[len(FILE_MAGIC) :])

            assert mdd.chunks[0].compression_algorithm == "gzip"

    def test_convert_yaml_file_not_found(self) -> None:
        """Should raise error for missing YAML file."""
        from yaml_to_mdd.models.loader import LoaderError

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.mdd"

            with pytest.raises(LoaderError):
                convert_yaml_to_mdd(Path("/nonexistent/file.yaml"), output_path)
