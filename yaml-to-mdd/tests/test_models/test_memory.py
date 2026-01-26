"""Tests for memory models."""

import pytest
from pydantic import ValidationError
from yaml_to_mdd.models.memory import (
    AddressFormat,
    DataBlock,
    DataBlockFormat,
    DataBlockType,
    MemoryAccess,
    MemoryConfig,
    MemoryRegion,
)


class TestMemoryAccess:
    """Tests for MemoryAccess enum."""

    def test_valid_access_values(self) -> None:
        """Should accept valid access values."""
        assert MemoryAccess.READ.value == "read"
        assert MemoryAccess.WRITE.value == "write"
        assert MemoryAccess.READ_WRITE.value == "read_write"
        assert MemoryAccess.EXECUTE.value == "execute"


class TestAddressFormat:
    """Tests for AddressFormat model."""

    def test_default_values(self) -> None:
        """Should have sensible defaults (4 bytes each)."""
        fmt = AddressFormat()
        assert fmt.address_bytes == 4
        assert fmt.length_bytes == 4

    def test_format_identifier_default(self) -> None:
        """Should calculate correct format identifier for defaults."""
        fmt = AddressFormat()
        # High nibble = length_bytes (4), low nibble = address_bytes (4)
        # 0x44 = 68
        assert fmt.format_identifier == 0x44

    def test_format_identifier_custom(self) -> None:
        """Should calculate correct format identifier for custom values."""
        fmt = AddressFormat(address_bytes=2, length_bytes=3)
        # High nibble = 3, low nibble = 2 -> 0x32
        assert fmt.format_identifier == 0x32

    def test_format_identifier_max(self) -> None:
        """Should calculate correct format identifier for max values."""
        fmt = AddressFormat(address_bytes=5, length_bytes=5)
        # 0x55
        assert fmt.format_identifier == 0x55

    def test_format_identifier_min(self) -> None:
        """Should calculate correct format identifier for min values."""
        fmt = AddressFormat(address_bytes=1, length_bytes=1)
        # 0x11
        assert fmt.format_identifier == 0x11

    def test_rejects_invalid_address_bytes(self) -> None:
        """Should reject address_bytes outside 1-5 range."""
        with pytest.raises(ValidationError):
            AddressFormat(address_bytes=0)

        with pytest.raises(ValidationError):
            AddressFormat(address_bytes=6)

    def test_rejects_invalid_length_bytes(self) -> None:
        """Should reject length_bytes outside 1-5 range."""
        with pytest.raises(ValidationError):
            AddressFormat(length_bytes=0)

        with pytest.raises(ValidationError):
            AddressFormat(length_bytes=6)


class TestMemoryRegion:
    """Tests for MemoryRegion model."""

    def test_basic_creation(self) -> None:
        """Should create memory region with minimal fields."""
        region = MemoryRegion(
            name="flash",
            start_address=0x00100000,
            size=0x00100000,
        )
        assert region.name == "flash"
        assert region.start_address == 0x00100000
        assert region.size == 0x00100000
        assert region.access == MemoryAccess.READ

    def test_end_address_property(self) -> None:
        """Should calculate end address correctly."""
        region = MemoryRegion(
            name="flash",
            start_address=0x00100000,
            size=0x00050000,
        )
        assert region.end_address == 0x00150000

    def test_hex_string_addresses(self) -> None:
        """Should parse hex string addresses."""
        region = MemoryRegion(
            name="flash",
            start_address="0x00100000",  # type: ignore[arg-type]
            size="0x00050000",  # type: ignore[arg-type]
        )
        assert region.start_address == 0x00100000
        assert region.size == 0x00050000

    def test_with_all_fields(self) -> None:
        """Should create region with all optional fields."""
        region = MemoryRegion(
            name="calibration",
            description="Calibration data area",
            start_address=0x00200000,
            size=0x00010000,
            access=MemoryAccess.READ_WRITE,
            address_format=AddressFormat(address_bytes=3, length_bytes=2),
            security_level="level_1",
            session=["extended", "programming"],
        )
        assert region.name == "calibration"
        assert region.description == "Calibration data area"
        assert region.access == MemoryAccess.READ_WRITE
        assert region.address_format is not None
        assert region.address_format.address_bytes == 3
        assert region.security_level == "level_1"
        assert region.session == ["extended", "programming"]

    def test_rejects_address_overflow(self) -> None:
        """Should reject regions that overflow 32-bit address space."""
        with pytest.raises(ValidationError, match="exceeds 32-bit"):
            MemoryRegion(
                name="overflow",
                start_address=0xFFFFFFFF,
                size=2,
            )

    def test_allows_max_address_space(self) -> None:
        """Should allow regions that exactly fit 32-bit address space."""
        region = MemoryRegion(
            name="max",
            start_address=0x00000000,
            size=0xFFFFFFFF,
        )
        assert region.end_address == 0xFFFFFFFF

    def test_session_as_string(self) -> None:
        """Should accept session as single string."""
        region = MemoryRegion(
            name="flash",
            start_address=0x00100000,
            size=0x00100000,
            session="extended",
        )
        assert region.session == "extended"


class TestDataBlockType:
    """Tests for DataBlockType enum."""

    def test_valid_types(self) -> None:
        """Should have correct values."""
        assert DataBlockType.DOWNLOAD.value == "download"
        assert DataBlockType.UPLOAD.value == "upload"


class TestDataBlockFormat:
    """Tests for DataBlockFormat enum."""

    def test_valid_formats(self) -> None:
        """Should have correct values."""
        assert DataBlockFormat.RAW.value == "raw"
        assert DataBlockFormat.ENCRYPTED.value == "encrypted"
        assert DataBlockFormat.COMPRESSED.value == "compressed"
        assert DataBlockFormat.ENCRYPTED_COMPRESSED.value == "encrypted_compressed"


class TestDataBlock:
    """Tests for DataBlock model."""

    def test_basic_creation(self) -> None:
        """Should create data block with minimal fields."""
        block = DataBlock(
            name="firmware",
            memory_address=0x00100000,
            memory_size=0x00080000,
        )
        assert block.name == "firmware"
        assert block.memory_address == 0x00100000
        assert block.memory_size == 0x00080000
        assert block.type == DataBlockType.DOWNLOAD
        assert block.format == DataBlockFormat.RAW

    def test_data_format_identifier_raw(self) -> None:
        """Should return 0x00 for raw format."""
        block = DataBlock(
            name="test",
            memory_address=0x00100000,
            memory_size=0x1000,
            format=DataBlockFormat.RAW,
        )
        assert block.data_format_identifier == 0x00

    def test_data_format_identifier_encrypted(self) -> None:
        """Should return 0x01 for encrypted format."""
        block = DataBlock(
            name="test",
            memory_address=0x00100000,
            memory_size=0x1000,
            format=DataBlockFormat.ENCRYPTED,
        )
        assert block.data_format_identifier == 0x01

    def test_data_format_identifier_compressed(self) -> None:
        """Should return 0x10 for compressed format."""
        block = DataBlock(
            name="test",
            memory_address=0x00100000,
            memory_size=0x1000,
            format=DataBlockFormat.COMPRESSED,
        )
        assert block.data_format_identifier == 0x10

    def test_data_format_identifier_encrypted_compressed(self) -> None:
        """Should return 0x11 for encrypted+compressed format."""
        block = DataBlock(
            name="test",
            memory_address=0x00100000,
            memory_size=0x1000,
            format=DataBlockFormat.ENCRYPTED_COMPRESSED,
        )
        assert block.data_format_identifier == 0x11

    def test_with_all_fields(self) -> None:
        """Should create block with all optional fields."""
        block = DataBlock(
            name="calibration",
            description="Calibration data block",
            type=DataBlockType.UPLOAD,
            memory_address=0x00200000,
            memory_size=0x00010000,
            format=DataBlockFormat.COMPRESSED,
            max_block_length=0x0FFA,
            security_level="level_2",
            session="programming",
            checksum_type="crc32",
        )
        assert block.name == "calibration"
        assert block.description == "Calibration data block"
        assert block.type == DataBlockType.UPLOAD
        assert block.format == DataBlockFormat.COMPRESSED
        assert block.max_block_length == 0x0FFA
        assert block.security_level == "level_2"
        assert block.session == "programming"
        assert block.checksum_type == "crc32"


class TestMemoryConfig:
    """Tests for MemoryConfig model."""

    def test_empty_config(self) -> None:
        """Should create empty config with defaults."""
        config = MemoryConfig()
        assert config.default_address_format.address_bytes == 4
        assert config.default_address_format.length_bytes == 4
        assert config.regions == {}
        assert config.data_blocks == {}

    def test_with_regions(self) -> None:
        """Should create config with memory regions."""
        config = MemoryConfig(
            regions={
                "flash": MemoryRegion(
                    name="flash",
                    start_address=0x00100000,
                    size=0x00100000,
                ),
                "ram": MemoryRegion(
                    name="ram",
                    start_address=0x20000000,
                    size=0x00040000,
                ),
            }
        )
        assert len(config.regions) == 2
        assert "flash" in config.regions
        assert "ram" in config.regions

    def test_non_overlapping_regions(self) -> None:
        """Should accept non-overlapping regions."""
        config = MemoryConfig(
            regions={
                "region1": MemoryRegion(
                    name="region1",
                    start_address=0x00100000,
                    size=0x00010000,
                ),
                "region2": MemoryRegion(
                    name="region2",
                    start_address=0x00110000,  # Starts where region1 ends
                    size=0x00010000,
                ),
            }
        )
        assert len(config.regions) == 2

    def test_rejects_overlapping_regions(self) -> None:
        """Should reject overlapping regions."""
        with pytest.raises(ValidationError, match="overlap"):
            MemoryConfig(
                regions={
                    "region1": MemoryRegion(
                        name="region1",
                        start_address=0x00100000,
                        size=0x00020000,  # Ends at 0x00120000
                    ),
                    "region2": MemoryRegion(
                        name="region2",
                        start_address=0x00110000,  # Starts inside region1
                        size=0x00010000,
                    ),
                }
            )

    def test_rejects_fully_contained_region(self) -> None:
        """Should reject region fully contained in another."""
        with pytest.raises(ValidationError, match="overlap"):
            MemoryConfig(
                regions={
                    "outer": MemoryRegion(
                        name="outer",
                        start_address=0x00100000,
                        size=0x00100000,
                    ),
                    "inner": MemoryRegion(
                        name="inner",
                        start_address=0x00110000,
                        size=0x00010000,
                    ),
                }
            )

    def test_with_data_blocks(self) -> None:
        """Should create config with data blocks."""
        config = MemoryConfig(
            data_blocks={
                "firmware": DataBlock(
                    name="firmware",
                    memory_address=0x00100000,
                    memory_size=0x00080000,
                ),
                "calibration": DataBlock(
                    name="calibration",
                    type=DataBlockType.UPLOAD,
                    memory_address=0x00200000,
                    memory_size=0x00010000,
                ),
            }
        )
        assert len(config.data_blocks) == 2
        assert "firmware" in config.data_blocks
        assert "calibration" in config.data_blocks

    def test_with_custom_default_format(self) -> None:
        """Should accept custom default address format."""
        config = MemoryConfig(default_address_format=AddressFormat(address_bytes=3, length_bytes=2))
        assert config.default_address_format.address_bytes == 3
        assert config.default_address_format.length_bytes == 2

    def test_full_config(self) -> None:
        """Should create config with all components."""
        config = MemoryConfig(
            default_address_format=AddressFormat(address_bytes=4, length_bytes=4),
            regions={
                "flash": MemoryRegion(
                    name="flash",
                    start_address=0x00100000,
                    size=0x00100000,
                    access=MemoryAccess.READ_WRITE,
                ),
            },
            data_blocks={
                "firmware": DataBlock(
                    name="firmware",
                    memory_address=0x00100000,
                    memory_size=0x00080000,
                ),
            },
        )
        assert config.default_address_format.format_identifier == 0x44
        assert len(config.regions) == 1
        assert len(config.data_blocks) == 1
