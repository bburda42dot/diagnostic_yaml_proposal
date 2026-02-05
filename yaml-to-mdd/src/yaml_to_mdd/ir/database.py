"""IR model for the complete diagnostic database.

This module defines the top-level container that holds all diagnostic
information ready for conversion to FlatBuffers format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from yaml_to_mdd.ir.services import IRDiagService
    from yaml_to_mdd.ir.types import IRDOP


@dataclass(frozen=True)
class IRMatchingParameter:
    """IR representation of a variant matching parameter.

    Used to identify which variant is running based on a diagnostic response.
    """

    expected_value: str  # Value to match (as string for consistency with FlatBuffers)
    diag_service_ref: str  # Reference to the diagnostic service to call
    out_param_ref: str | None = None  # Reference to the output parameter to match
    use_physical_addressing: bool = True


@dataclass(frozen=True)
class IRVariant:
    """IR representation of an ECU variant.

    Variants allow different configurations of an ECU (e.g., bootloader vs app).
    """

    short_name: str
    is_base_variant: bool = False
    matching_parameters: tuple[IRMatchingParameter, ...] = ()
    # Variant-specific service overrides (services only in this variant)
    service_refs: tuple[str, ...] = ()
    # Parent variant reference (for inheritance)
    parent_ref: str | None = None


@dataclass(frozen=True)
class IRMemoryRegion:
    """IR representation of a memory region."""

    name: str
    start_address: int
    size: int
    access: str
    address_bytes: int
    length_bytes: int
    security_level: str | None = None
    sessions: tuple[str, ...] = ()


@dataclass(frozen=True)
class IRDataBlock:
    """IR representation of a data block."""

    name: str
    block_type: str  # "download" or "upload"
    memory_address: int
    memory_size: int
    data_format: int
    max_block_length: int | None = None
    security_level: str | None = None
    session: str | None = None


@dataclass(frozen=True)
class IRSnapshotDataItem:
    """IR representation of a snapshot data item."""

    did: int
    name: str
    byte_position: int
    byte_size: int


@dataclass(frozen=True)
class IRSnapshotRecord:
    """IR representation of a snapshot record."""

    record_number: int
    description: str
    data_items: tuple[IRSnapshotDataItem, ...]
    total_size: int


@dataclass(frozen=True)
class IRExtendedDataRecord:
    """IR representation of an extended data record."""

    record_number: int
    name: str
    type_ref: str  # Reference to type or DOP
    byte_size: int


@dataclass(frozen=True)
class IRDTC:
    """IR representation of a DTC with snapshot support."""

    code: int  # 3-byte DTC code
    name: str
    description: str
    severity: int  # Severity byte value
    functional_unit: int
    snapshots: tuple[IRSnapshotRecord, ...]
    extended_data: tuple[IRExtendedDataRecord, ...]
    aging_threshold: int | None = None
    aged_threshold: int | None = None
    priority: int | None = None


@dataclass
class IRDatabase:
    """Complete diagnostic database in IR format.

    This is the top-level container that holds all diagnostic
    information ready for conversion to FlatBuffers format.

    The database is mutable (not frozen) to allow building it
    incrementally during transformation.

    Attributes
    ----------
        ecu_name: Name of the ECU.
        revision: Version string (semver).
        author: Author of the diagnostic description.
        description: Human-readable description.
        schema_version: Schema version identifier.
        dops: Dictionary of DOPs by short_name.
        services: Dictionary of services by short_name.
        sessions: Session name to ID mapping.
        security_levels: Security level name to level mapping.
        did_read_services: DID to read service name mapping.
        did_write_services: DID to write service name mapping.
        routine_services: Routine ID to service names mapping.

    """

    # Metadata
    ecu_name: str
    revision: str
    author: str | None = None
    description: str | None = None

    # Schema version
    schema_version: str = "opensovd.cda.diagdesc/v1"

    # Collections (using dict for fast lookup by name)
    dops: dict[str, IRDOP] = field(default_factory=dict)
    services: dict[str, IRDiagService] = field(default_factory=dict)

    # Session definitions
    sessions: dict[str, int] = field(default_factory=dict)  # name -> id

    # Security levels
    security_levels: dict[str, int] = field(default_factory=dict)  # name -> level

    # DID to service mapping (for ReadDataByIdentifier)
    did_read_services: dict[int, str] = field(
        default_factory=dict
    )  # DID -> service_name
    did_write_services: dict[int, str] = field(
        default_factory=dict
    )  # DID -> service_name

    # Routine to service mapping
    routine_services: dict[int, list[str]] = field(
        default_factory=dict
    )  # routine_id -> [service_names]

    # Memory configuration
    memory_regions: list[IRMemoryRegion] = field(default_factory=list)
    data_blocks: list[IRDataBlock] = field(default_factory=list)

    # DTC definitions
    dtcs: list[IRDTC] = field(default_factory=list)

    # Variant definitions
    variants: list[IRVariant] = field(default_factory=list)

    def add_dop(self, dop: IRDOP) -> None:
        """Add a DOP to the database.

        Args:
        ----
            dop: The DOP to add.

        """
        self.dops[dop.short_name] = dop

    def add_service(self, service: IRDiagService) -> None:
        """Add a service to the database.

        Args:
        ----
            service: The service to add.

        """
        self.services[service.short_name] = service

    def add_variant(self, variant: IRVariant) -> None:
        """Add a variant to the database.

        Args:
        ----
            variant: The variant to add.

        """
        self.variants.append(variant)

    def get_dop(self, name: str) -> IRDOP | None:
        """Get a DOP by name.

        Args:
        ----
            name: The short_name of the DOP.

        Returns:
        -------
            The DOP if found, None otherwise.

        """
        return self.dops.get(name)

    def get_service(self, name: str) -> IRDiagService | None:
        """Get a service by name.

        Args:
        ----
            name: The short_name of the service.

        Returns:
        -------
            The service if found, None otherwise.

        """
        return self.services.get(name)

    def get_all_services(self) -> list[IRDiagService]:
        """Get all services as a list.

        Returns
        -------
            List of all services in the database.

        """
        return list(self.services.values())

    def get_all_dops(self) -> list[IRDOP]:
        """Get all DOPs as a list.

        Returns
        -------
            List of all DOPs in the database.

        """
        return list(self.dops.values())
