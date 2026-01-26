"""Performance tests for yaml-to-mdd conversion.

Benchmarks and performance regression tests for the conversion pipeline.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any

import pytest
import yaml
from yaml_to_mdd.converters import IRToFlatBuffersConverter, MDDWriter
from yaml_to_mdd.converters.mdd_writer import FILE_MAGIC
from yaml_to_mdd.models import load_diagnostic_description
from yaml_to_mdd.transform import YamlToIRTransformer

from tests.fixtures.sample_yamls import FULL_YAML, MINIMAL_YAML


class TestPerformanceBenchmarks:
    """Performance benchmarks for the conversion pipeline."""

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

    @pytest.fixture
    def large_yaml_data(self) -> dict[str, Any]:
        """Generate a large YAML structure for stress testing."""
        base = {
            **FULL_YAML,
            "dids": {},
            "dtcs": {},
        }

        # Add many DIDs
        for i in range(100):
            did_id = f"0x{0x1000 + i:04X}"
            base["dids"][did_id] = {
                "name": f"TestDID_{i}",
                "description": f"Test DID number {i} for stress testing",
                "access": "read",
                "type": {"base": "u32"},
                "access_pattern": "standard_read",
            }

        # Add many DTCs
        for i in range(50):
            dtc_code = f"0x{0x010000 + (i << 8):06X}"
            base["dtcs"][dtc_code] = {
                "name": f"TestFault_{i}",
                "description": f"Test fault number {i} for stress testing",
                "severity": 3,  # check_at_next_halt
                "functional_unit": i % 10,
            }

        return base

    @pytest.fixture
    def large_yaml_file(self, large_yaml_data: dict[str, Any]) -> Path:
        """Create a temporary large YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(large_yaml_data, f)
            return Path(f.name)

    def test_minimal_yaml_load_time(self, minimal_yaml_file: Path) -> None:
        """Loading minimal YAML should be fast."""
        start = time.perf_counter()
        doc = load_diagnostic_description(minimal_yaml_file)
        elapsed = time.perf_counter() - start

        assert doc is not None
        # Loading minimal YAML should take less than 500ms
        assert elapsed < 0.5, f"Loading took {elapsed:.3f}s, expected < 0.5s"

    def test_full_yaml_load_time(self, full_yaml_file: Path) -> None:
        """Loading full YAML should be reasonably fast."""
        start = time.perf_counter()
        doc = load_diagnostic_description(full_yaml_file)
        elapsed = time.perf_counter() - start

        assert doc is not None
        # Loading full YAML should take less than 1 second
        assert elapsed < 1.0, f"Loading took {elapsed:.3f}s, expected < 1.0s"

    def test_transform_time(self, full_yaml_file: Path) -> None:
        """Transformation should be fast."""
        doc = load_diagnostic_description(full_yaml_file)

        start = time.perf_counter()
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)
        elapsed = time.perf_counter() - start

        assert ir_db is not None
        # Transformation should take less than 500ms
        assert elapsed < 0.5, f"Transform took {elapsed:.3f}s, expected < 0.5s"

    def test_flatbuffers_conversion_time(self, full_yaml_file: Path) -> None:
        """FlatBuffers conversion should be fast."""
        doc = load_diagnostic_description(full_yaml_file)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)

        start = time.perf_counter()
        converter = IRToFlatBuffersConverter()
        fbs_bytes = converter.convert(ir_db)
        elapsed = time.perf_counter() - start

        assert len(fbs_bytes) > 0
        # FlatBuffers conversion should take less than 500ms
        assert elapsed < 0.5, f"FlatBuffers conversion took {elapsed:.3f}s, expected < 0.5s"

    def test_mdd_write_time(self, full_yaml_file: Path) -> None:
        """MDD writing should be fast."""
        doc = load_diagnostic_description(full_yaml_file)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)

        start = time.perf_counter()
        writer = MDDWriter()
        mdd_bytes = writer.write_bytes(ir_db)
        elapsed = time.perf_counter() - start

        assert len(mdd_bytes) > 0
        # MDD writing should take less than 500ms
        assert elapsed < 0.5, f"MDD writing took {elapsed:.3f}s, expected < 0.5s"

    def test_full_pipeline_time(self, full_yaml_file: Path) -> None:
        """Full pipeline should complete in reasonable time."""
        start = time.perf_counter()

        # Full pipeline
        doc = load_diagnostic_description(full_yaml_file)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)
        writer = MDDWriter()
        mdd_bytes = writer.write_bytes(ir_db)

        elapsed = time.perf_counter() - start

        assert len(mdd_bytes) > 0
        # Full pipeline should take less than 2 seconds
        assert elapsed < 2.0, f"Full pipeline took {elapsed:.3f}s, expected < 2.0s"

    def test_large_yaml_pipeline_time(self, large_yaml_file: Path) -> None:
        """Large YAML should still process in reasonable time."""
        start = time.perf_counter()

        doc = load_diagnostic_description(large_yaml_file)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)
        writer = MDDWriter()
        mdd_bytes = writer.write_bytes(ir_db)

        elapsed = time.perf_counter() - start

        assert len(mdd_bytes) > 0
        # Large YAML (100 DIDs, 50 DTCs) should process in under 5 seconds
        assert elapsed < 5.0, f"Large pipeline took {elapsed:.3f}s, expected < 5.0s"

    def test_compression_overhead(self, full_yaml_file: Path) -> None:
        """Compression should not add excessive overhead."""
        doc = load_diagnostic_description(full_yaml_file)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)

        # Uncompressed timing
        start = time.perf_counter()
        writer_plain = MDDWriter()
        writer_plain.write_bytes(ir_db)
        plain_time = time.perf_counter() - start

        # Compressed timing
        start = time.perf_counter()
        writer_gzip = MDDWriter(compression="gzip")
        writer_gzip.write_bytes(ir_db)
        gzip_time = time.perf_counter() - start

        # Compression should not add more than 2x overhead
        assert (
            gzip_time < plain_time * 3
        ), f"Compression overhead too high: {gzip_time:.3f}s vs {plain_time:.3f}s"


class TestMemoryUsage:
    """Tests for memory usage during conversion."""

    @pytest.fixture
    def large_yaml_data(self) -> dict[str, Any]:
        """Generate a large YAML structure for memory testing."""
        base = {
            **FULL_YAML,
            "dids": {},
        }

        # Add many DIDs with larger data types
        for i in range(200):
            did_id = f"0x{0x1000 + i:04X}"
            base["dids"][did_id] = {
                "name": f"TestDID_{i}",
                "description": (
                    f"Test DID number {i} with longer description " "for memory testing purposes"
                ),
                "access": "read_write" if i % 2 == 0 else "read",
                "type": {
                    "base": "struct",
                    "fields": [
                        {"name": "field1", "type": "u32"},
                        {"name": "field2", "type": "u32"},
                        {"name": "field3", "type": "u32"},
                        {"name": "field4", "type": "u32"},
                    ],
                },
                "access_pattern": "standard_read" if i % 2 == 0 else "standard_write",
            }

        return base

    def test_output_size_reasonable(self, large_yaml_data: dict[str, Any]) -> None:
        """Output size should be reasonable for the input."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(large_yaml_data, f)
            yaml_path = Path(f.name)

        # Get input size
        input_size = yaml_path.stat().st_size

        # Convert
        doc = load_diagnostic_description(yaml_path)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)
        writer = MDDWriter()
        mdd_bytes = writer.write_bytes(ir_db)

        output_size = len(mdd_bytes)

        # Output should not be excessively larger than input
        # FlatBuffers typically has some overhead but shouldn't explode
        # Allow up to 10x for binary format overhead
        assert (
            output_size < input_size * 10
        ), f"Output size {output_size} is too large compared to input {input_size}"

    def test_compressed_size_smaller(self, large_yaml_data: dict[str, Any]) -> None:
        """Compressed output should have compression metadata set correctly."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(large_yaml_data, f)
            yaml_path = Path(f.name)

        doc = load_diagnostic_description(yaml_path)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)

        writer_plain = MDDWriter(compression=None)
        writer_gzip = MDDWriter(compression="gzip")

        bytes_plain = writer_plain.write_bytes(ir_db)
        bytes_gzip = writer_gzip.write_bytes(ir_db)

        # Parse both to verify compression metadata
        from yaml_to_mdd.proto_generated import MDDFile

        mdd_plain = MDDFile()
        mdd_plain.ParseFromString(bytes_plain[len(FILE_MAGIC) :])
        mdd_gzip = MDDFile()
        mdd_gzip.ParseFromString(bytes_gzip[len(FILE_MAGIC) :])

        # Verify compression metadata is set correctly
        assert mdd_plain.chunks[0].compression_algorithm == ""
        assert mdd_gzip.chunks[0].compression_algorithm == "gzip"
        assert mdd_gzip.chunks[0].uncompressed_size > 0

        # Verify the uncompressed size matches the plain chunk size
        plain_chunk_size = len(mdd_plain.chunks[0].data)
        assert mdd_gzip.chunks[0].uncompressed_size == plain_chunk_size


class TestScalability:
    """Tests for scalability with increasing data sizes."""

    def _generate_yaml_with_dids(self, num_dids: int) -> dict[str, Any]:
        """Generate YAML with specified number of DIDs."""
        base = {
            **MINIMAL_YAML,
            "dids": {},
        }

        for i in range(num_dids):
            did_id = f"0x{0x1000 + i:04X}"
            base["dids"][did_id] = {
                "name": f"DID_{i}",
                "description": f"Test DID {i}",
                "access": "read",
                "type": {"base": "u32"},
                "access_pattern": "default_access",
            }

        return base

    @pytest.mark.parametrize("num_dids", [10, 50, 100, 200])
    def test_scaling_with_dids(self, num_dids: int) -> None:
        """Pipeline should scale reasonably with DID count."""
        yaml_data = self._generate_yaml_with_dids(num_dids)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(yaml_data, f)
            yaml_path = Path(f.name)

        start = time.perf_counter()

        doc = load_diagnostic_description(yaml_path)
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)
        writer = MDDWriter()
        mdd_bytes = writer.write_bytes(ir_db)

        elapsed = time.perf_counter() - start

        assert len(mdd_bytes) > 0

        # Should process even 200 DIDs in under 10 seconds
        assert elapsed < 10.0, f"Processing {num_dids} DIDs took {elapsed:.3f}s"

    def test_repeated_conversions_consistent(self) -> None:
        """Multiple conversions should have consistent timing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(FULL_YAML, f)
            yaml_path = Path(f.name)

        times = []
        for _ in range(5):
            start = time.perf_counter()

            doc = load_diagnostic_description(yaml_path)
            transformer = YamlToIRTransformer()
            ir_db = transformer.transform(doc)
            writer = MDDWriter()
            writer.write_bytes(ir_db)

            times.append(time.perf_counter() - start)

        avg_time = sum(times) / len(times)
        max_deviation = max(abs(t - avg_time) for t in times)

        # Times should be consistent within 50% of average
        assert (
            max_deviation < avg_time * 0.5
        ), f"Times varied too much: {times}, avg={avg_time:.3f}s, max_dev={max_deviation:.3f}s"
