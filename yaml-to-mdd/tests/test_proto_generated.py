"""Tests to verify Protobuf generated code is working."""


class TestProtobufImports:
    """Tests for Protobuf import functionality."""

    def test_import_mdd_file(self) -> None:
        """Should be able to import MDDFile."""
        from yaml_to_mdd.proto_generated import MDDFile

        assert MDDFile is not None

    def test_import_chunk(self) -> None:
        """Should be able to import Chunk."""
        from yaml_to_mdd.proto_generated import Chunk

        assert Chunk is not None

    def test_import_signature(self) -> None:
        """Should be able to import Signature."""
        from yaml_to_mdd.proto_generated import Signature

        assert Signature is not None

    def test_import_encryption(self) -> None:
        """Should be able to import Encryption."""
        from yaml_to_mdd.proto_generated import Encryption

        assert Encryption is not None


class TestMDDFileCreation:
    """Tests for MDDFile message creation."""

    def test_create_mdd_file(self) -> None:
        """Should be able to create an MDDFile instance."""
        from yaml_to_mdd.proto_generated import MDDFile

        mdd = MDDFile()
        mdd.version = "1.0.0"
        mdd.ecu_name = "TestECU"
        mdd.revision = "1.0.0"

        assert mdd.version == "1.0.0"
        assert mdd.ecu_name == "TestECU"
        assert mdd.revision == "1.0.0"

    def test_add_metadata_to_mdd(self) -> None:
        """Should be able to add metadata key-value pairs."""
        from yaml_to_mdd.proto_generated import MDDFile

        mdd = MDDFile()
        mdd.metadata["created"] = "2024-01-01"
        mdd.metadata["author"] = "Test"
        mdd.metadata["description"] = "Test MDD file"

        assert len(mdd.metadata) == 3
        assert mdd.metadata["author"] == "Test"
        assert mdd.metadata["created"] == "2024-01-01"


class TestChunkCreation:
    """Tests for Chunk message creation."""

    def test_create_chunk(self) -> None:
        """Should be able to create a Chunk instance."""
        from yaml_to_mdd.proto_generated import Chunk

        chunk = Chunk()
        chunk.type = Chunk.DataType.DIAGNOSTIC_DESCRIPTION
        chunk.name = "diagnostic_data"
        chunk.data = b"test data bytes"

        assert chunk.type == Chunk.DataType.DIAGNOSTIC_DESCRIPTION
        assert chunk.name == "diagnostic_data"
        assert chunk.data == b"test data bytes"

    def test_chunk_metadata(self) -> None:
        """Should be able to add metadata to Chunk."""
        from yaml_to_mdd.proto_generated import Chunk

        chunk = Chunk()
        chunk.metadata["format"] = "flatbuffers"
        chunk.metadata["version"] = "1.0"

        assert chunk.metadata["format"] == "flatbuffers"
        assert len(chunk.metadata) == 2

    def test_chunk_data_types_enum(self) -> None:
        """Should be able to access Chunk.DataType enum values."""
        from yaml_to_mdd.proto_generated import Chunk

        assert Chunk.DataType.DIAGNOSTIC_DESCRIPTION == 0
        assert Chunk.DataType.JAR_FILE == 1
        assert Chunk.DataType.JAR_FILE_PARTIAL == 2
        assert Chunk.DataType.EMBEDDED_FILE == 3
        assert Chunk.DataType.VENDOR_SPECIFIC == 1024

    def test_compression_fields(self) -> None:
        """Should be able to set compression fields on Chunk."""
        from yaml_to_mdd.proto_generated import Chunk

        chunk = Chunk()
        chunk.compression_algorithm = "zstd"
        chunk.uncompressed_size = 1024 * 1024  # 1 MB
        chunk.data = b"compressed data here"

        assert chunk.compression_algorithm == "zstd"
        assert chunk.uncompressed_size == 1024 * 1024


class TestSignatureCreation:
    """Tests for Signature message creation."""

    def test_create_signature(self) -> None:
        """Should be able to create Signature with metadata."""
        from yaml_to_mdd.proto_generated import Signature

        sig = Signature()
        sig.algorithm = "SHA256withRSA"
        sig.key_identifier = b"\x01\x02\x03\x04"
        sig.signature = b"\x00" * 256

        assert sig.algorithm == "SHA256withRSA"
        assert sig.key_identifier == b"\x01\x02\x03\x04"
        assert len(sig.signature) == 256

    def test_signature_metadata(self) -> None:
        """Should be able to add metadata to Signature."""
        from yaml_to_mdd.proto_generated import Signature

        sig = Signature()
        sig.metadata["signer"] = "test-signer"
        sig.metadata["timestamp"] = "2024-01-01T00:00:00Z"

        assert sig.metadata["signer"] == "test-signer"


class TestEncryptionCreation:
    """Tests for Encryption message creation."""

    def test_create_encryption(self) -> None:
        """Should be able to create Encryption instance."""
        from yaml_to_mdd.proto_generated import Encryption

        enc = Encryption()
        enc.encryption_algorithm = "AES-256-GCM"
        enc.key_identifier = b"\xaa\xbb\xcc\xdd"

        assert enc.encryption_algorithm == "AES-256-GCM"
        assert enc.key_identifier == b"\xaa\xbb\xcc\xdd"


class TestSerialization:
    """Tests for serialization and deserialization."""

    def test_serialize_deserialize_mdd_file(self) -> None:
        """Should be able to serialize and deserialize MDDFile."""
        from yaml_to_mdd.proto_generated import Chunk, MDDFile

        # Create MDDFile with a chunk
        mdd = MDDFile()
        mdd.version = "1.0.0"
        mdd.ecu_name = "TestECU"
        mdd.revision = "1.0.0"
        mdd.metadata["author"] = "Test Author"

        chunk = mdd.chunks.add()
        chunk.type = Chunk.DataType.DIAGNOSTIC_DESCRIPTION
        chunk.name = "main"
        chunk.data = b"\x00\x01\x02\x03"

        # Serialize to bytes
        serialized = mdd.SerializeToString()
        assert isinstance(serialized, bytes)
        assert len(serialized) > 0

        # Deserialize
        mdd_read = MDDFile()
        mdd_read.ParseFromString(serialized)

        assert mdd_read.version == "1.0.0"
        assert mdd_read.ecu_name == "TestECU"
        assert mdd_read.revision == "1.0.0"
        assert mdd_read.metadata["author"] == "Test Author"
        assert len(mdd_read.chunks) == 1
        assert mdd_read.chunks[0].data == b"\x00\x01\x02\x03"
        assert mdd_read.chunks[0].name == "main"

    def test_serialize_multiple_chunks(self) -> None:
        """Should be able to serialize MDDFile with multiple chunks."""
        from yaml_to_mdd.proto_generated import Chunk, MDDFile

        mdd = MDDFile()
        mdd.version = "1.0.0"
        mdd.ecu_name = "MultiChunkECU"

        # Add diagnostic description chunk
        chunk1 = mdd.chunks.add()
        chunk1.type = Chunk.DataType.DIAGNOSTIC_DESCRIPTION
        chunk1.name = "diagnostic"
        chunk1.data = b"diagnostic data"

        # Add embedded file chunk
        chunk2 = mdd.chunks.add()
        chunk2.type = Chunk.DataType.EMBEDDED_FILE
        chunk2.name = "firmware.bin"
        chunk2.data = b"firmware binary data"
        chunk2.mimeType = "application/octet-stream"

        # Serialize and deserialize
        serialized = mdd.SerializeToString()
        mdd_read = MDDFile()
        mdd_read.ParseFromString(serialized)

        assert len(mdd_read.chunks) == 2
        assert mdd_read.chunks[0].type == Chunk.DataType.DIAGNOSTIC_DESCRIPTION
        assert mdd_read.chunks[1].type == Chunk.DataType.EMBEDDED_FILE
        assert mdd_read.chunks[1].mimeType == "application/octet-stream"

    def test_serialize_with_signature(self) -> None:
        """Should be able to serialize MDDFile with chunksSignature."""
        from yaml_to_mdd.proto_generated import Chunk, MDDFile

        mdd = MDDFile()
        mdd.version = "1.0.0"
        mdd.ecu_name = "SignedECU"

        chunk = mdd.chunks.add()
        chunk.type = Chunk.DataType.DIAGNOSTIC_DESCRIPTION
        chunk.data = b"signed data"

        # Add signature
        sig = mdd.chunksSignature
        sig.algorithm = "SHA256withRSA"
        sig.signature = b"\x00" * 64

        # Serialize and deserialize
        serialized = mdd.SerializeToString()
        mdd_read = MDDFile()
        mdd_read.ParseFromString(serialized)

        assert mdd_read.chunksSignature.algorithm == "SHA256withRSA"
        assert len(mdd_read.chunksSignature.signature) == 64


class TestOptionalFields:
    """Tests for optional field handling."""

    def test_has_field_check(self) -> None:
        """Should be able to check if optional field is set."""
        from yaml_to_mdd.proto_generated import Chunk

        chunk = Chunk()

        # Before setting
        assert not chunk.HasField("compression_algorithm")

        # After setting
        chunk.compression_algorithm = "zstd"
        assert chunk.HasField("compression_algorithm")

    def test_clear_field(self) -> None:
        """Should be able to clear a field."""
        from yaml_to_mdd.proto_generated import Chunk

        chunk = Chunk()
        chunk.compression_algorithm = "zstd"
        assert chunk.HasField("compression_algorithm")

        chunk.ClearField("compression_algorithm")
        assert not chunk.HasField("compression_algorithm")

    def test_optional_name_field(self) -> None:
        """Should be able to use optional name field."""
        from yaml_to_mdd.proto_generated import Chunk

        chunk = Chunk()

        # Name is optional
        assert not chunk.HasField("name")
        assert chunk.name == ""  # Default value

        chunk.name = "my_chunk"
        assert chunk.HasField("name")
        assert chunk.name == "my_chunk"
