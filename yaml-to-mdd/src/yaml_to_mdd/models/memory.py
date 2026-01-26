"""Memory region and data block models for UDS memory operations."""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, model_validator

from yaml_to_mdd.models.common import HexInt32


class MemoryAccess(str, Enum):
    """Memory access permissions."""

    READ = "read"
    WRITE = "write"
    READ_WRITE = "read_write"
    EXECUTE = "execute"


class AddressFormat(BaseModel):
    """Address and length format for memory operations.

    Per ISO 14229, the addressAndLengthFormatIdentifier specifies
    the number of bytes used for address and length parameters.
    """

    address_bytes: Annotated[
        int, Field(ge=1, le=5, description="Bytes for memory address (1-5)")
    ] = 4
    length_bytes: Annotated[int, Field(ge=1, le=5, description="Bytes for memory length (1-5)")] = 4

    @property
    def format_identifier(self) -> int:
        """Calculate addressAndLengthFormatIdentifier byte.

        High nibble = length bytes, low nibble = address bytes.
        """
        return (self.length_bytes << 4) | self.address_bytes


class MemoryRegion(BaseModel):
    """Definition of a memory region in the ECU."""

    name: Annotated[str, Field(description="Human-readable name for the region")]
    description: Annotated[
        str | None, Field(default=None, description="Region purpose description")
    ]
    start_address: Annotated[HexInt32, Field(description="Starting address of the region")]
    size: Annotated[HexInt32, Field(description="Size of the region in bytes")]
    access: Annotated[
        MemoryAccess, Field(default=MemoryAccess.READ, description="Access permissions")
    ]
    address_format: Annotated[
        AddressFormat | None,
        Field(default=None, description="Custom address/length format"),
    ]
    security_level: Annotated[
        str | None, Field(default=None, description="Required security level")
    ]
    session: Annotated[
        str | list[str] | None,
        Field(default=None, description="Required diagnostic session(s)"),
    ]

    @property
    def end_address(self) -> int:
        """Calculate end address (exclusive)."""
        return self.start_address + self.size

    @model_validator(mode="after")
    def validate_region(self) -> MemoryRegion:
        """Validate region doesn't overflow address space."""
        if self.end_address > 0xFFFFFFFF:
            msg = f"Region end address {self.end_address:#x} exceeds 32-bit address space"
            raise ValueError(msg)
        return self


class DataBlockType(str, Enum):
    """Type of data block transfer."""

    DOWNLOAD = "download"  # ECU receives data
    UPLOAD = "upload"  # ECU sends data


class DataBlockFormat(str, Enum):
    """Data format/compression for block transfers."""

    RAW = "raw"
    ENCRYPTED = "encrypted"
    COMPRESSED = "compressed"
    ENCRYPTED_COMPRESSED = "encrypted_compressed"


class DataBlock(BaseModel):
    """Definition of a data block for transfer operations.

    Used with RequestDownload (0x34) and RequestUpload (0x35) services.
    """

    name: Annotated[str, Field(description="Human-readable name for the data block")]
    description: Annotated[str | None, Field(default=None, description="Block purpose description")]
    type: Annotated[
        DataBlockType,
        Field(default=DataBlockType.DOWNLOAD, description="Transfer direction"),
    ]
    memory_address: Annotated[HexInt32, Field(description="Target memory address")]
    memory_size: Annotated[HexInt32, Field(description="Size of the data block in bytes")]
    format: Annotated[
        DataBlockFormat, Field(default=DataBlockFormat.RAW, description="Data format")
    ]
    max_block_length: Annotated[
        HexInt32 | None,
        Field(default=None, description="Max bytes per TransferData call"),
    ]
    security_level: Annotated[
        str | None, Field(default=None, description="Required security level")
    ]
    session: Annotated[str | None, Field(default=None, description="Required diagnostic session")]
    checksum_type: Annotated[str | None, Field(default=None, description="Checksum algorithm")]

    @property
    def data_format_identifier(self) -> int:
        """Calculate dataFormatIdentifier byte.

        High nibble = compression method
        Low nibble = encryption method
        """
        format_map = {
            DataBlockFormat.RAW: 0x00,
            DataBlockFormat.ENCRYPTED: 0x01,
            DataBlockFormat.COMPRESSED: 0x10,
            DataBlockFormat.ENCRYPTED_COMPRESSED: 0x11,
        }
        return format_map.get(self.format, 0x00)


class MemoryConfig(BaseModel):
    """Memory configuration for the ECU."""

    default_address_format: Annotated[
        AddressFormat,
        Field(default_factory=AddressFormat, description="Default address/length format"),
    ]
    regions: Annotated[
        dict[str, MemoryRegion],
        Field(default_factory=dict, description="Named memory regions"),
    ]
    data_blocks: Annotated[
        dict[str, DataBlock],
        Field(default_factory=dict, description="Named data blocks"),
    ]

    @model_validator(mode="after")
    def validate_no_overlaps(self) -> MemoryConfig:
        """Validate regions don't overlap."""
        regions = list(self.regions.values())

        for i, r1 in enumerate(regions):
            for r2 in regions[i + 1 :]:
                if _regions_overlap(r1, r2):
                    msg = f"Memory regions '{r1.name}' and '{r2.name}' overlap"
                    raise ValueError(msg)

        return self


def _regions_overlap(r1: MemoryRegion, r2: MemoryRegion) -> bool:
    """Check if two regions overlap."""
    return r1.start_address < r2.end_address and r2.start_address < r1.end_address


# Type aliases
MemoryDict = dict[str, MemoryRegion]
DataBlockDict = dict[str, DataBlock]
