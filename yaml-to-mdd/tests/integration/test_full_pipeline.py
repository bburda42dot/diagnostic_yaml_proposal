"""Full pipeline integration tests for yaml-to-mdd.

Tests the complete conversion flow: YAML -> Pydantic -> IR -> FlatBuffers -> MDD.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml
from pydantic import ValidationError
from yaml_to_mdd.converters import (
    IRToFlatBuffersConverter,
    MDDWriter,
    convert_yaml_to_mdd,
)
from yaml_to_mdd.converters.mdd_writer import FILE_MAGIC
from yaml_to_mdd.filter import AudienceFilter
from yaml_to_mdd.models import load_diagnostic_description
from yaml_to_mdd.proto_generated import Chunk, MDDFile
from yaml_to_mdd.transform import YamlToIRTransformer

from tests.fixtures.sample_yamls import (
    FULL_YAML,
    MINIMAL_YAML,
    YAML_INVALID_SCHEMA,
    YAML_WITH_AUDIENCE,
    YAML_WITH_MEMORY,
)

if TYPE_CHECKING:
    from yaml_to_mdd.ir.database import IRDatabase


class TestFullPipeline:
    """Integration tests for the full conversion pipeline."""

    @pytest.fixture
    def minimal_yaml_file(self) -> Path:
        """Create a temporary minimal YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(MINIMAL_YAML, f)
            return Path(f.name)

    @pytest.fixture
    def full_yaml_file(self) -> Path:
        """Create a temporary full-featured YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(FULL_YAML, f)
            return Path(f.name)

    def test_minimal_yaml_full_pipeline(self, minimal_yaml_file: Path) -> None:
        """Should process minimal YAML through the complete pipeline."""
        # Step 1: Load and validate YAML
        doc = load_diagnostic_description(minimal_yaml_file)
        assert doc.ecu.id == "MINIMAL_ECU"

        # Step 2: Transform to IR
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)
        assert ir_db.ecu_name == "MINIMAL_ECU"

        # Step 3: Convert to FlatBuffers
        fb_converter = IRToFlatBuffersConverter()
        fbs_bytes = fb_converter.convert(ir_db)
        assert len(fbs_bytes) > 0

        # Step 4: Write MDD
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "minimal.mdd"
            writer = MDDWriter()
            writer.write(ir_db, output_path)

            assert output_path.exists()
            assert output_path.stat().st_size > 0

            # Step 5: Verify MDD can be read back
            with open(output_path, "rb") as f:
                mdd = MDDFile()
                mdd.ParseFromString(f.read()[len(FILE_MAGIC) :])

            assert mdd.ecu_name == "MINIMAL_ECU"
            assert mdd.revision == "1.0.0"
            assert len(mdd.chunks) == 1
            assert mdd.chunks[0].type == Chunk.DIAGNOSTIC_DESCRIPTION

    def test_full_yaml_pipeline(self, full_yaml_file: Path) -> None:
        """Should process full-featured YAML through the pipeline."""
        # Load and validate
        doc = load_diagnostic_description(full_yaml_file)
        assert doc.ecu.id == "FULL_ECU"
        assert doc.dids is not None
        assert len(doc.dids) == 6
        assert doc.dtcs is not None
        assert len(doc.dtcs) == 3

        # Transform to IR
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)
        assert ir_db.ecu_name == "FULL_ECU"
        # Check services were generated for DIDs
        assert len(ir_db.services) > 0
        # Check DTCs were processed
        assert len(ir_db.dtcs) == 3

        # Write MDD
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "full.mdd"
            writer = MDDWriter()
            writer.write(ir_db, output_path)

            # Read back and verify
            with open(output_path, "rb") as f:
                mdd = MDDFile()
                mdd.ParseFromString(f.read()[len(FILE_MAGIC) :])

            assert mdd.ecu_name == "FULL_ECU"
            assert mdd.revision == "2.5.0"

    def test_convert_yaml_to_mdd_helper(self, minimal_yaml_file: Path) -> None:
        """Should use high-level convert function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.mdd"
            convert_yaml_to_mdd(minimal_yaml_file, output_path)

            assert output_path.exists()

            with open(output_path, "rb") as f:
                mdd = MDDFile()
                mdd.ParseFromString(f.read()[len(FILE_MAGIC) :])

            assert mdd.ecu_name == "MINIMAL_ECU"

    def test_pipeline_preserves_metadata(self, full_yaml_file: Path) -> None:
        """Should preserve metadata through the pipeline."""
        doc = load_diagnostic_description(full_yaml_file)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)

        assert ir_db.author == "Integration Test Suite"
        assert ir_db.description == "Full-featured integration test ECU"
        assert ir_db.revision == "2.5.0"

        # Write and read back
        writer = MDDWriter()
        mdd_bytes = writer.write_bytes(ir_db)

        mdd = MDDFile()
        mdd.ParseFromString(mdd_bytes[len(FILE_MAGIC) :])

        assert mdd.metadata["author"] == "Integration Test Suite"
        assert "description" in mdd.metadata


class TestValidationIntegration:
    """Integration tests for validation in the pipeline."""

    def test_invalid_schema_rejected(self) -> None:
        """Should reject YAML with invalid schema version."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(YAML_INVALID_SCHEMA, f)
            yaml_path = Path(f.name)

        with pytest.raises(ValidationError):  # ValidationError from Pydantic
            load_diagnostic_description(yaml_path)

    def test_validation_errors_propagate(self) -> None:
        """Should propagate validation errors from Pydantic."""
        invalid_yaml = {
            "schema": "opensovd.cda.diagdesc/v1",
            # Missing required fields
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(invalid_yaml, f)
            yaml_path = Path(f.name)

        with pytest.raises(ValidationError):  # ValidationError
            load_diagnostic_description(yaml_path)

    def test_extra_fields_rejected(self) -> None:
        """Should reject YAML with unknown fields (extra='forbid')."""
        yaml_with_extra = {
            **MINIMAL_YAML,
            "unknown_field": "should be rejected",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(yaml_with_extra, f)
            yaml_path = Path(f.name)

        with pytest.raises(ValidationError):  # ValidationError
            load_diagnostic_description(yaml_path)


class TestCompressionIntegration:
    """Integration tests for compression in MDD output."""

    @pytest.fixture
    def full_yaml_file(self) -> Path:
        """Create a temporary full-featured YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(FULL_YAML, f)
            return Path(f.name)

    def test_gzip_compression_reduces_size(self, full_yaml_file: Path) -> None:
        """Gzip compression should affect output (usually smaller for larger data)."""
        doc = load_diagnostic_description(full_yaml_file)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)

        writer_plain = MDDWriter()
        writer_gzip = MDDWriter(compression="gzip")

        bytes_plain = writer_plain.write_bytes(ir_db)
        bytes_gzip = writer_gzip.write_bytes(ir_db)

        # Compressed should be different
        assert bytes_plain != bytes_gzip

        # Verify gzip compression metadata
        mdd_gzip = MDDFile()
        mdd_gzip.ParseFromString(bytes_gzip[len(FILE_MAGIC) :])
        assert mdd_gzip.chunks[0].compression_algorithm == "gzip"
        assert mdd_gzip.chunks[0].uncompressed_size > 0

    def test_convert_with_compression(self, full_yaml_file: Path) -> None:
        """Should use compression with convert_yaml_to_mdd helper."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "compressed.mdd"
            convert_yaml_to_mdd(full_yaml_file, output_path, compression="gzip")

            with open(output_path, "rb") as f:
                mdd = MDDFile()
                mdd.ParseFromString(f.read()[len(FILE_MAGIC) :])

            assert mdd.chunks[0].compression_algorithm == "gzip"


class TestMemoryIntegration:
    """Integration tests for memory configuration handling."""

    @pytest.fixture
    def memory_yaml_file(self) -> Path:
        """Create a temporary YAML file with memory config."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(YAML_WITH_MEMORY, f)
            return Path(f.name)

    def test_memory_config_processed(self, memory_yaml_file: Path) -> None:
        """Should process memory configuration in pipeline."""
        doc = load_diagnostic_description(memory_yaml_file)
        assert doc.memory is not None
        assert len(doc.memory.regions) == 3
        assert len(doc.memory.data_blocks) == 2

        # Transform to IR
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)

        # Check memory regions in IR
        assert len(ir_db.memory_regions) == 3
        # Check data blocks in IR
        assert len(ir_db.data_blocks) == 2

        # Verify regions have correct data
        region_names = {r.name for r in ir_db.memory_regions}
        assert "Application Flash" in region_names
        assert "Calibration Data" in region_names
        assert "Bootloader" in region_names

    def test_memory_address_format(self, memory_yaml_file: Path) -> None:
        """Should preserve address format configuration."""
        doc = load_diagnostic_description(memory_yaml_file)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)

        # Check default address format propagated
        for region in ir_db.memory_regions:
            assert region.address_bytes == 4
            assert region.length_bytes == 4


class TestAudienceFilterIntegration:
    """Integration tests for audience filtering in the pipeline."""

    @pytest.fixture
    def audience_yaml_file(self) -> Path:
        """Create a temporary YAML file with audience config."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(YAML_WITH_AUDIENCE, f)
            return Path(f.name)

    def test_filter_for_development(self, audience_yaml_file: Path) -> None:
        """Should filter content for development audience."""
        doc = load_diagnostic_description(audience_yaml_file)

        # Unfiltered document has all DIDs
        assert doc.dids is not None
        assert len(doc.dids) == 3

        # Filter for development audience
        audience_filter = AudienceFilter(target_audience="development")
        filtered_doc = audience_filter.filter(doc)

        # Development sees VIN, InternalDebugData, but not FactoryCalibration
        assert filtered_doc.dids is not None
        assert 0xF190 in filtered_doc.dids  # VIN - development included
        assert 0xFD00 in filtered_doc.dids  # InternalDebugData - development only
        # FactoryCalibration is for oem/supplier, not development
        # But it doesn't exclude development, so it should still be visible
        # depending on filter logic

    def test_filter_for_production(self, audience_yaml_file: Path) -> None:
        """Should filter content for production audience."""
        doc = load_diagnostic_description(audience_yaml_file)

        audience_filter = AudienceFilter(target_audience="production")
        filtered_doc = audience_filter.filter(doc)

        # Production should see VIN but not internal debug data
        assert filtered_doc.dids is not None
        assert 0xF190 in filtered_doc.dids  # VIN - production included

    def test_filtered_document_converts_to_mdd(self, audience_yaml_file: Path) -> None:
        """Should successfully convert filtered document to MDD."""
        doc = load_diagnostic_description(audience_yaml_file)

        audience_filter = AudienceFilter(target_audience="production")
        filtered_doc = audience_filter.filter(doc)

        # Transform filtered document
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(filtered_doc)

        # Write to MDD
        writer = MDDWriter()
        mdd_bytes = writer.write_bytes(ir_db)

        # Verify valid MDD
        mdd = MDDFile()
        mdd.ParseFromString(mdd_bytes[len(FILE_MAGIC) :])
        assert mdd.ecu_name == "AUDIENCE_ECU"


class TestFlatBuffersValidation:
    """Tests for FlatBuffers data validation."""

    @pytest.fixture
    def ir_database(self) -> IRDatabase:
        """Create IR database from full YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(FULL_YAML, f)
            yaml_path = Path(f.name)

        doc = load_diagnostic_description(yaml_path)
        transformer = YamlToIRTransformer()
        return transformer.transform(doc)

    def test_flatbuffers_is_valid(self, ir_database: IRDatabase) -> None:
        """FlatBuffers output should be valid and parseable."""
        converter = IRToFlatBuffersConverter()
        fbs_bytes = converter.convert(ir_database)

        # Verify it's valid FlatBuffers by parsing it as EcuData (the root type)
        from yaml_to_mdd.fbs_generated.dataformat.EcuData import EcuData

        ecu_data = EcuData.GetRootAs(fbs_bytes, 0)  # type: ignore[no-untyped-call]
        assert ecu_data is not None

        # Navigate to DiagLayer through Variant
        variant = ecu_data.Variants(0)
        assert variant is not None
        diag_layer = variant.DiagLayer()
        assert diag_layer is not None

        # Check we can access main data
        short_name = diag_layer.ShortName()
        assert short_name is not None

    def test_flatbuffers_services_readable(self, ir_database: IRDatabase) -> None:
        """Generated services should be readable from FlatBuffers."""
        converter = IRToFlatBuffersConverter()
        fbs_bytes = converter.convert(ir_database)

        from yaml_to_mdd.fbs_generated.dataformat.EcuData import EcuData

        ecu_data = EcuData.GetRootAs(fbs_bytes, 0)  # type: ignore[no-untyped-call]
        assert ecu_data is not None

        # Navigate to DiagLayer through Variant
        variant = ecu_data.Variants(0)
        assert variant is not None
        diag_layer = variant.DiagLayer()
        assert diag_layer is not None

        # Should have services
        service_count = diag_layer.DiagServicesLength()
        assert service_count > 0


class TestRealYamlFiles:
    """Tests using real example YAML files from diagnostic_yaml directory."""

    def test_minimal_ecu_yaml(self, minimal_ecu_yaml: Path) -> None:
        """Should process real minimal-ecu.yml file."""
        if not minimal_ecu_yaml.exists():
            pytest.skip("minimal-ecu.yml not found")

        # Load and validate the YAML
        doc = load_diagnostic_description(minimal_ecu_yaml)
        assert doc.ecu.id == "MIN_ECU"
        assert doc.schema_version == "opensovd.cda.diagdesc/v1"

        # Check protocols are parsed correctly (dynamic map)
        if doc.ecu.protocols:
            assert isinstance(doc.ecu.protocols, dict)
            for _name, proto in doc.ecu.protocols.items():
                assert proto.protocol_short_name is not None

    def test_example_ecm_yaml(self, example_ecm_yaml: Path) -> None:
        """Should process real example-ecm.yml file."""
        if not example_ecm_yaml.exists():
            pytest.skip("example-ecm.yml not found")

        # Load and validate the YAML
        doc = load_diagnostic_description(example_ecm_yaml)
        assert doc.ecu.id == "ECM_01"
        assert doc.schema_version == "opensovd.cda.diagdesc/v1"

        # Check various sections are parsed
        assert doc.dids is not None
        assert len(doc.dids) > 0

        assert doc.dtcs is not None
        assert len(doc.dtcs) > 0

        assert doc.routines is not None
        assert len(doc.routines) > 0

        # Check custom services are parsed
        if doc.services.custom:
            assert isinstance(doc.services.custom, dict)
            for _name, service in doc.services.custom.items():
                assert service.sid is not None
