"""Write MDD files (FlatBuffers wrapped in Protobuf container).

The MDD format is a container format that uses Protocol Buffers as an
outer envelope and FlatBuffers for the diagnostic data payload.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from yaml_to_mdd.converters.flatbuffers_converter import (
    DoIPAddressingConfig,
    IRToFlatBuffersConverter,
)
from yaml_to_mdd.proto_generated import MDDFile

if TYPE_CHECKING:
    from yaml_to_mdd.ir.database import IRDatabase

# MDD file magic bytes - must match classic-diagnostic-adapter and odx-converter
# "MDD version 0      \0" - 20 bytes total (ASCII)
FILE_MAGIC = b"MDD version 0      \x00"


class MDDWriter:
    """Write MDD files combining FlatBuffers data with Protobuf container.

    The MDD format wraps diagnostic data (in FlatBuffers format) inside
    a Protobuf container that provides metadata, versioning, and optional
    compression/encryption support.

    Usage:
        writer = MDDWriter()
        writer.write(ir_database, Path("output.mdd"))

    Or for in-memory conversion:
        mdd_bytes = writer.write_bytes(ir_database)
    """

    def __init__(
        self,
        version: str = "1.0.0",
        compression: str | None = "lzma",
    ) -> None:
        """Initialize the MDD writer.

        Args:
        ----
            version: MDD file format version string.
            compression: Compression algorithm ("lzma", "zstd", "gzip", or None).
                Defaults to "lzma" for compatibility with classic-diagnostic-adapter.

        """
        self._version = version
        self._compression = compression

    def write(
        self,
        db: IRDatabase,
        output_path: Path,
        doip_addressing: DoIPAddressingConfig | None = None,
    ) -> None:
        """Write IR database to MDD file.

        Args:
        ----
            db: The IR database to write.
            output_path: Output file path. Parent directories will be created.
            doip_addressing: Optional DoIP addressing configuration.

        """
        mdd_bytes = self.write_bytes(db, doip_addressing)

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "wb") as f:
            f.write(mdd_bytes)

    def write_bytes(
        self,
        db: IRDatabase,
        doip_addressing: DoIPAddressingConfig | None = None,
    ) -> bytes:
        """Convert IR database to MDD bytes without writing to file.

        Args:
        ----
            db: The IR database to convert.
            doip_addressing: Optional DoIP addressing configuration.

        Returns:
        -------
            MDD file as bytes (Protobuf-serialized container with magic header).

        """
        # Convert to FlatBuffers
        converter = IRToFlatBuffersConverter()
        fbs_bytes = converter.convert(db, doip_addressing=doip_addressing)

        # Optionally compress
        data = fbs_bytes
        uncompressed_size: int | None = None
        if self._compression:
            data, uncompressed_size = self._compress(fbs_bytes)

        # Create Protobuf container
        mdd = self._create_mdd_file(db, data, uncompressed_size)

        # Return magic header + protobuf data
        return FILE_MAGIC + bytes(mdd.SerializeToString())

    def _create_mdd_file(
        self,
        db: IRDatabase,
        data: bytes,
        uncompressed_size: int | None,
    ) -> MDDFile:
        """Create MDD Protobuf container.

        Args:
        ----
            db: IR database for metadata.
            data: FlatBuffers data (possibly compressed).
            uncompressed_size: Original size if compressed, None otherwise.

        Returns:
        -------
            MDDFile protobuf message ready for serialization.

        """
        mdd = MDDFile()
        mdd.version = self._version
        mdd.ecu_name = db.ecu_name
        mdd.revision = db.revision

        # Add metadata
        if db.author:
            mdd.metadata["author"] = db.author
        if db.description:
            mdd.metadata["description"] = db.description
        mdd.metadata["schema_version"] = db.schema_version

        # Add main diagnostic chunk
        chunk = mdd.chunks.add()
        chunk.type = 0  # type: ignore[assignment]  # DIAGNOSTIC_DESCRIPTION
        chunk.name = "diagnostic_description"
        chunk.data = data
        chunk.mimeType = "application/x-flatbuffers"
        chunk.metadata["flatbuffers_schema"] = "diagnostic_description.fbs"

        if self._compression and uncompressed_size is not None:
            chunk.compression_algorithm = self._compression
            chunk.uncompressed_size = uncompressed_size

        return mdd

    def _compress(self, data: bytes) -> tuple[bytes, int]:
        """Compress data using configured algorithm.

        Args:
        ----
            data: Uncompressed data bytes.

        Returns:
        -------
            Tuple of (compressed_data, original_size).

        Raises:
        ------
            ValueError: If compression algorithm is unknown.
            RuntimeError: If required compression library is not installed.

        """
        original_size = len(data)

        if self._compression == "lzma":
            import lzma

            # Use LZMA format (not XZ) for compatibility with classic-diagnostic-adapter
            compressed = lzma.compress(data, format=lzma.FORMAT_ALONE)
            return compressed, original_size

        elif self._compression == "zstd":
            try:
                import zstandard as zstd

                compressor = zstd.ZstdCompressor()
                compressed = compressor.compress(data)
                return compressed, original_size
            except ImportError:
                raise RuntimeError(
                    "zstandard package required for zstd compression. "
                    "Install with: pip install zstandard"
                ) from None

        elif self._compression == "gzip":
            import gzip

            compressed = gzip.compress(data)
            return compressed, original_size

        else:
            raise ValueError(f"Unknown compression algorithm: {self._compression}")


def convert_yaml_to_mdd(
    yaml_path: Path,
    output_path: Path,
    compression: str | None = None,
) -> None:
    """High-level function to convert YAML to MDD.

    This is a convenience function that handles the full pipeline:
    1. Load and validate YAML
    2. Transform to IR
    3. Extract DoIP addressing from YAML
    4. Write MDD file

    Args:
    ----
        yaml_path: Input YAML file path.
        output_path: Output MDD file path.
        compression: Optional compression algorithm ("zstd" or "gzip").

    Raises:
    ------
        FileNotFoundError: If YAML file doesn't exist.
        pydantic.ValidationError: If YAML is invalid.

    """
    from yaml_to_mdd.models.loader import load_diagnostic_description
    from yaml_to_mdd.transform.transformer import YamlToIRTransformer

    # Load and validate YAML
    doc = load_diagnostic_description(yaml_path)

    # Transform to IR
    transformer = YamlToIRTransformer()
    ir_db = transformer.transform(doc)

    # Extract DoIP addressing from YAML if available
    doip_addressing: DoIPAddressingConfig | None = None
    if doc.ecu.addressing and doc.ecu.addressing.doip:
        doip = doc.ecu.addressing.doip
        timing = doc.ecu.addressing.timing
        doip_addressing = DoIPAddressingConfig(
            logical_gateway_address=doip.logical_address,
            logical_ecu_address=doip.logical_address,  # Same as gateway for most ECUs
            logical_functional_address=doip.functional_address or 0xE400,
            logical_tester_address=doip.tester_address,
            # UDS timing parameters
            p2_max_ms=timing.p2_ms if timing else None,
            p2_star_ms=timing.p2_star_ms if timing else None,
            p6_max_ms=getattr(timing, "p6_ms", None) if timing else None,
            p6_star_ms=getattr(timing, "p6_star_ms", None) if timing else None,
            s3_ms=timing.s3_ms if timing else None,
            # NRC completion timeouts
            rc78_completion_timeout_ms=(
                getattr(timing, "rc78_completion_timeout_ms", None) if timing else None
            ),
            rc21_completion_timeout_ms=(
                getattr(timing, "rc21_completion_timeout_ms", None) if timing else None
            ),
            # DoIP-specific timeouts
            doip_diagnostic_ack_timeout_ms=getattr(
                doip, "diagnostic_ack_timeout_ms", None
            ),
            doip_routing_activation_timeout_ms=getattr(
                doip, "routing_activation_timeout_ms", None
            ),
            # Retry configuration
            doip_number_of_retries=getattr(doip, "number_of_retries", None),
            doip_retry_period_ms=getattr(doip, "retry_period_ms", None),
        )

    # Write MDD
    writer = MDDWriter(compression=compression)
    writer.write(ir_db, output_path, doip_addressing=doip_addressing)
