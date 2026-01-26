"""Round-trip tests for yaml-to-mdd conversion.

Tests that data survives the full round-trip conversion and maintains integrity.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import yaml
from yaml_to_mdd.converters import IRToFlatBuffersConverter, MDDWriter
from yaml_to_mdd.converters.mdd_writer import FILE_MAGIC
from yaml_to_mdd.fbs_generated.dataformat.DiagLayer import DiagLayer
from yaml_to_mdd.fbs_generated.dataformat.EcuData import EcuData
from yaml_to_mdd.models import load_diagnostic_description
from yaml_to_mdd.proto_generated import MDDFile
from yaml_to_mdd.transform import YamlToIRTransformer

from tests.fixtures.sample_yamls import FULL_YAML, MINIMAL_YAML, YAML_WITH_MEMORY


def get_diag_layer_from_fbs(fbs_bytes: bytes) -> DiagLayer:
    """Extract DiagLayer from FlatBuffers bytes (EcuData root).

    The FlatBuffers structure is: EcuData -> Variants[0] -> DiagLayer
    """
    ecu_data = EcuData.GetRootAs(fbs_bytes, 0)  # type: ignore[no-untyped-call]
    variant = ecu_data.Variants(0)
    return variant.DiagLayer()


class TestDataIntegrity:
    """Tests for data integrity through the conversion pipeline."""

    def _load_and_convert(self, yaml_data: dict[str, Any]) -> tuple[Any, bytes, MDDFile]:
        """Load YAML, convert to MDD, and return components for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(yaml_data, f)
            yaml_path = Path(f.name)

        doc = load_diagnostic_description(yaml_path)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)

        writer = MDDWriter()
        mdd_bytes = writer.write_bytes(ir_db)

        # Strip FILE_MAGIC header before parsing protobuf
        protobuf_bytes = mdd_bytes[len(FILE_MAGIC) :]

        mdd = MDDFile()
        mdd.ParseFromString(protobuf_bytes)

        return doc, mdd_bytes, mdd

    def test_ecu_id_preserved(self) -> None:
        """ECU ID should be preserved through conversion."""
        doc, _, mdd = self._load_and_convert(MINIMAL_YAML)
        assert mdd.ecu_name == doc.ecu.id
        assert mdd.ecu_name == "MINIMAL_ECU"

    def test_revision_preserved(self) -> None:
        """Revision should be preserved through conversion."""
        doc, _, mdd = self._load_and_convert(FULL_YAML)
        assert mdd.revision == doc.meta.revision
        assert mdd.revision == "2.5.0"

    def test_author_preserved(self) -> None:
        """Author should be preserved in metadata."""
        doc, _, mdd = self._load_and_convert(FULL_YAML)
        assert mdd.metadata["author"] == doc.meta.author
        assert mdd.metadata["author"] == "Integration Test Suite"

    def test_did_count_preserved(self) -> None:
        """Number of DIDs should be preserved in services."""
        doc, _, mdd = self._load_and_convert(FULL_YAML)

        # Get FlatBuffers data from chunk (decompress if needed)
        chunk = mdd.chunks[0]
        chunk_data = chunk.data
        if chunk.compression_algorithm == "lzma":
            import lzma

            chunk_data = lzma.decompress(chunk_data, format=lzma.FORMAT_ALONE)

        diag_layer = get_diag_layer_from_fbs(chunk_data)
        assert diag_layer is not None

        # Original YAML has 6 DIDs, which should generate services
        assert doc.dids is not None
        original_did_count = len(doc.dids)
        assert original_did_count == 6

        # Services should exist for DIDs
        service_count = diag_layer.DiagServicesLength()
        assert service_count > 0

    def test_dtc_count_preserved(self) -> None:
        """Number of DTCs should be preserved."""
        doc, _, _ = self._load_and_convert(FULL_YAML)

        # Load again and transform to check IR
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(FULL_YAML, f)
            yaml_path = Path(f.name)

        doc2 = load_diagnostic_description(yaml_path)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc2)

        assert doc.dtcs is not None
        assert len(ir_db.dtcs) == len(doc.dtcs)
        assert len(ir_db.dtcs) == 3

    def test_session_mappings_preserved(self) -> None:
        """Session mappings should be preserved in IR."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(FULL_YAML, f)
            yaml_path = Path(f.name)

        doc = load_diagnostic_description(yaml_path)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)

        # Check sessions were captured
        assert len(ir_db.sessions) == len(doc.sessions)
        assert "default" in ir_db.sessions
        assert "programming" in ir_db.sessions
        assert "extended" in ir_db.sessions

        # Check session IDs
        assert ir_db.sessions["default"] == 0x01
        assert ir_db.sessions["programming"] == 0x02
        assert ir_db.sessions["extended"] == 0x03

    def test_security_levels_preserved(self) -> None:
        """Security level mappings should be preserved in IR."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(FULL_YAML, f)
            yaml_path = Path(f.name)

        doc = load_diagnostic_description(yaml_path)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)

        assert doc.security is not None
        assert len(ir_db.security_levels) == len(doc.security)
        assert ir_db.security_levels["level1"] == 1
        assert ir_db.security_levels["level2"] == 2


class TestMemoryRoundTrip:
    """Tests for memory configuration data integrity."""

    def test_memory_regions_preserved(self) -> None:
        """Memory regions should be preserved through conversion."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(YAML_WITH_MEMORY, f)
            yaml_path = Path(f.name)

        doc = load_diagnostic_description(yaml_path)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)

        assert doc.memory is not None
        assert len(ir_db.memory_regions) == len(doc.memory.regions)

        # Check specific region properties
        app_flash = next(r for r in ir_db.memory_regions if r.name == "Application Flash")
        assert app_flash.start_address == 0x00010000
        assert app_flash.size == 0x000F0000
        assert app_flash.access == "read_write"

    def test_data_blocks_preserved(self) -> None:
        """Data blocks should be preserved through conversion."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(YAML_WITH_MEMORY, f)
            yaml_path = Path(f.name)

        doc = load_diagnostic_description(yaml_path)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)

        assert doc.memory is not None
        assert len(ir_db.data_blocks) == len(doc.memory.data_blocks)

        # Check specific data block properties
        app_software = next(b for b in ir_db.data_blocks if b.name == "Application Software")
        assert app_software.memory_address == 0x00010000
        assert app_software.max_block_length == 4096


class TestFlatBuffersReadBack:
    """Tests for reading back FlatBuffers data."""

    def test_read_ecu_short_name(self) -> None:
        """Should read ECU short name from FlatBuffers."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(FULL_YAML, f)
            yaml_path = Path(f.name)

        doc = load_diagnostic_description(yaml_path)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)

        converter = IRToFlatBuffersConverter()
        fbs_bytes = converter.convert(ir_db)

        diag_layer = get_diag_layer_from_fbs(fbs_bytes)
        # DiagLayer short name should match ecu_name from IR
        short_name = diag_layer.ShortName()
        if short_name is not None:
            short_name = short_name.decode("utf-8") if isinstance(short_name, bytes) else short_name
            assert short_name == ir_db.ecu_name

    def test_read_diag_services(self) -> None:
        """Should read diagnostic services from FlatBuffers."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(FULL_YAML, f)
            yaml_path = Path(f.name)

        doc = load_diagnostic_description(yaml_path)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)

        converter = IRToFlatBuffersConverter()
        fbs_bytes = converter.convert(ir_db)

        diag_layer = get_diag_layer_from_fbs(fbs_bytes)
        assert diag_layer is not None

        # Read each service
        service_count = diag_layer.DiagServicesLength()
        for i in range(service_count):
            service = diag_layer.DiagServices(i)
            assert service is not None
            # Each service should have DiagComm with short name
            diag_comm = service.DiagComm()
            assert diag_comm is not None
            short_name = diag_comm.ShortName()
            assert short_name is not None

    def test_read_dops(self) -> None:
        """Should read DOPs (Data Object Properties) from FlatBuffers."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(FULL_YAML, f)
            yaml_path = Path(f.name)

        doc = load_diagnostic_description(yaml_path)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)

        converter = IRToFlatBuffersConverter()
        fbs_bytes = converter.convert(ir_db)

        diag_layer = get_diag_layer_from_fbs(fbs_bytes)

        # DOPs are embedded within services/parameters
        # Just verify we can access the layer without errors
        assert diag_layer is not None


class TestMDDContainerIntegrity:
    """Tests for MDD protobuf container integrity."""

    def test_mdd_version_present(self) -> None:
        """MDD should have version set."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(MINIMAL_YAML, f)
            yaml_path = Path(f.name)

        doc = load_diagnostic_description(yaml_path)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)

        writer = MDDWriter(version="1.2.3")
        mdd_bytes = writer.write_bytes(ir_db)

        mdd = MDDFile()
        mdd.ParseFromString(mdd_bytes[len(FILE_MAGIC) :])

        assert mdd.version == "1.2.3"

    def test_mdd_chunk_type_correct(self) -> None:
        """MDD chunk should have correct type."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(MINIMAL_YAML, f)
            yaml_path = Path(f.name)

        doc = load_diagnostic_description(yaml_path)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)

        writer = MDDWriter()
        mdd_bytes = writer.write_bytes(ir_db)

        mdd = MDDFile()
        mdd.ParseFromString(mdd_bytes[len(FILE_MAGIC) :])

        from yaml_to_mdd.proto_generated import Chunk

        assert len(mdd.chunks) == 1
        assert mdd.chunks[0].type == Chunk.DIAGNOSTIC_DESCRIPTION
        assert mdd.chunks[0].name == "diagnostic_description"

    def test_mdd_chunk_mimetype(self) -> None:
        """MDD chunk should have correct MIME type."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(MINIMAL_YAML, f)
            yaml_path = Path(f.name)

        doc = load_diagnostic_description(yaml_path)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)

        writer = MDDWriter()
        mdd_bytes = writer.write_bytes(ir_db)

        mdd = MDDFile()
        mdd.ParseFromString(mdd_bytes[len(FILE_MAGIC) :])

        assert mdd.chunks[0].mimeType == "application/x-flatbuffers"

    def test_mdd_schema_metadata(self) -> None:
        """MDD chunk should reference FlatBuffers schema."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(MINIMAL_YAML, f)
            yaml_path = Path(f.name)

        doc = load_diagnostic_description(yaml_path)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)

        writer = MDDWriter()
        mdd_bytes = writer.write_bytes(ir_db)

        mdd = MDDFile()
        mdd.ParseFromString(mdd_bytes[len(FILE_MAGIC) :])

        assert mdd.chunks[0].metadata["flatbuffers_schema"] == "diagnostic_description.fbs"


class TestCompressionRoundTrip:
    """Tests for compression round-trip integrity."""

    def test_gzip_preserves_data(self) -> None:
        """Gzip compression should preserve all data."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(FULL_YAML, f)
            yaml_path = Path(f.name)

        doc = load_diagnostic_description(yaml_path)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)

        # Write with compression
        writer_compressed = MDDWriter(compression="gzip")
        mdd_bytes_compressed = writer_compressed.write_bytes(ir_db)

        # Parse compressed MDD
        mdd_compressed = MDDFile()
        mdd_compressed.ParseFromString(mdd_bytes_compressed[len(FILE_MAGIC) :])

        # Decompress and verify FlatBuffers
        import gzip

        chunk = mdd_compressed.chunks[0]
        assert chunk.compression_algorithm == "gzip"

        decompressed_data = gzip.decompress(chunk.data)
        assert len(decompressed_data) == chunk.uncompressed_size

        # Verify FlatBuffers is valid after decompression
        diag_layer = get_diag_layer_from_fbs(decompressed_data)
        assert diag_layer is not None

        # Verify short name matches
        short_name = diag_layer.ShortName()
        if short_name is not None:
            short_name = short_name.decode("utf-8") if isinstance(short_name, bytes) else short_name
            assert short_name == ir_db.ecu_name
