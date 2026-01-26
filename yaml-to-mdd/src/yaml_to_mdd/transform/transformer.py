"""Main YAML to IR transformer."""

from __future__ import annotations

from yaml_to_mdd.ir.database import (
    IRDTC,
    IRDatabase,
    IRDataBlock,
    IRExtendedDataRecord,
    IRMemoryRegion,
    IRSnapshotDataItem,
    IRSnapshotRecord,
)
from yaml_to_mdd.ir.types import (
    IRDOP,
    IRDataType,
    IRDiagCodedType,
    IRDiagCodedTypeName,
)
from yaml_to_mdd.models.dids import DIDDefinition
from yaml_to_mdd.models.dtcs import (
    DTCDefinition,
    DTCExtendedDataDefinition,
    DTCSnapshotDefinition,
)
from yaml_to_mdd.models.memory import AddressFormat, DataBlock, MemoryRegion
from yaml_to_mdd.models.root import DiagnosticDescription
from yaml_to_mdd.models.types import TypeDefinition
from yaml_to_mdd.transform.service_generator import (
    generate_read_did_service,
    generate_routine_services,
    generate_write_did_service,
)
from yaml_to_mdd.transform.type_converter import type_definition_to_dop


class YamlToIRTransformer:
    """Transform validated YAML models to IR format.

    This is the main entry point for converting a validated
    DiagnosticDescription (from YAML/JSON) into an IRDatabase
    ready for FlatBuffers serialization.

    Usage:
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(diagnostic_description)
    """

    def __init__(self) -> None:
        """Initialize the transformer."""
        self._type_cache: dict[str, IRDOP] = {}

    def transform(self, doc: DiagnosticDescription) -> IRDatabase:
        """Transform a DiagnosticDescription to IRDatabase.

        Args:
        ----
            doc: Validated Pydantic model from YAML/JSON.

        Returns:
        -------
            IRDatabase ready for FlatBuffers serialization.

        """
        # Create database with metadata
        db = IRDatabase(
            ecu_name=doc.ecu.id,
            revision=doc.meta.revision,
            author=doc.meta.author,
            description=doc.meta.description,
        )

        # Add session mappings
        if doc.sessions:
            for name, session in doc.sessions.items():
                db.sessions[name] = session.id

        # Add security level mappings
        if doc.security:
            for name, level in doc.security.items():
                db.security_levels[name] = level.level

        # Process types -> DOPs
        self._process_types(doc, db)

        # Add standard DOPs
        self._add_standard_dops(db)

        # Process DIDs -> Services
        self._process_dids(doc, db)

        # Process Routines -> Services
        self._process_routines(doc, db)

        # Process Memory configuration
        self._process_memory(doc, db)

        # Process DTCs
        self._process_dtcs(doc, db)

        return db

    def _process_types(self, doc: DiagnosticDescription, db: IRDatabase) -> None:
        """Process type definitions into DOPs."""
        if not doc.types:
            return

        for type_name, type_def in doc.types.items():
            dop = type_definition_to_dop(type_name, type_def)
            db.add_dop(dop)
            self._type_cache[type_name] = dop

    def _add_standard_dops(self, db: IRDatabase) -> None:
        """Add standard DOPs used by multiple services."""
        # DOP for 16-bit DID identifier
        dop_did = IRDOP(
            short_name="DOP_DID",
            long_name="Data Identifier",
            diag_coded_type=IRDiagCodedType(
                type_name=IRDiagCodedTypeName.STANDARD_LENGTH_TYPE,
                base_data_type=IRDataType.A_UINT_32,
                bit_length=16,
            ),
        )
        db.add_dop(dop_did)

        # DOP for 16-bit Routine ID
        dop_rid = IRDOP(
            short_name="DOP_RID",
            long_name="Routine Identifier",
            diag_coded_type=IRDiagCodedType(
                type_name=IRDiagCodedTypeName.STANDARD_LENGTH_TYPE,
                base_data_type=IRDataType.A_UINT_32,
                bit_length=16,
            ),
        )
        db.add_dop(dop_rid)

    def _process_dids(self, doc: DiagnosticDescription, db: IRDatabase) -> None:
        """Process DIDs into services."""
        if not doc.dids:
            return

        for did_id, did_def in doc.dids.items():
            # Resolve access requirements
            sessions, security = self._resolve_access(doc, did_def.access_pattern)

            # Create DOP for DID data
            dop_name = self._get_or_create_dop_for_did(doc, db, did_def)

            # Determine readability/writability from explicit flags or access pattern string
            # If readable/writable fields are set, use them; otherwise infer from access string
            is_readable = did_def.readable if did_def.readable is not None else True
            is_writable = did_def.writable if did_def.writable is not None else False

            # Legacy: if access is a string like "read", "write", "read_write", parse it
            if did_def.access:
                access_lower = did_def.access.lower()
                if "read" in access_lower and "write" in access_lower:
                    is_readable = True
                    is_writable = True
                elif "write" in access_lower:
                    is_readable = False
                    is_writable = True
                elif "read" in access_lower:
                    is_readable = True
                    is_writable = False

            # Generate read service
            if is_readable:
                service = generate_read_did_service(did_id, did_def, dop_name, sessions, security)
                db.add_service(service)
                db.did_read_services[did_id] = service.short_name

            # Generate write service
            if is_writable:
                # Write may have additional conditions
                write_sessions, write_security = sessions, security
                if did_def.write_conditions:
                    for cond in did_def.write_conditions:
                        if cond.session:
                            write_sessions = (*write_sessions, cond.session)
                        if cond.security:
                            write_security = (*write_security, cond.security)

                service = generate_write_did_service(
                    did_id, did_def, dop_name, write_sessions, write_security
                )
                db.add_service(service)
                db.did_write_services[did_id] = service.short_name

    def _process_routines(self, doc: DiagnosticDescription, db: IRDatabase) -> None:
        """Process routines into services."""
        if not doc.routines:
            return

        for routine_id, routine_def in doc.routines.items():
            # Resolve access requirements
            sessions, security = self._resolve_access(doc, routine_def.access)

            # Generate services for each supported operation
            services = generate_routine_services(routine_id, routine_def, sessions, security)

            db.routine_services[routine_id] = []
            for service in services:
                db.add_service(service)
                db.routine_services[routine_id].append(service.short_name)

    def _resolve_access(
        self,
        doc: DiagnosticDescription,
        pattern_name: str | None,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Resolve access pattern to session and security requirements.

        Args:
        ----
            doc: The diagnostic description document.
            pattern_name: Name of the access pattern to resolve.

        Returns:
        -------
            Tuple of (sessions, security) tuples.

        """
        if not pattern_name or not doc.access_patterns:
            return (), ()

        pattern = doc.access_patterns.get(pattern_name)
        if not pattern:
            return (), ()

        sessions: tuple[str, ...] = ()
        if pattern.sessions != "any":
            sessions = tuple(pattern.sessions)

        security: tuple[str, ...] = ()
        if pattern.security != "none":
            security = tuple(pattern.security)

        return sessions, security

    def _get_or_create_dop_for_did(
        self,
        doc: DiagnosticDescription,
        db: IRDatabase,
        did_def: DIDDefinition,
    ) -> str:
        """Get or create DOP for a DID's data type.

        Args:
        ----
            doc: The diagnostic description document.
            db: The IR database being built.
            did_def: The DID definition.

        Returns:
        -------
            Name of the DOP for this DID's data.

        """
        if isinstance(did_def.type, str):
            # Type reference - should exist in types section
            if did_def.type in self._type_cache:
                return did_def.type

            # Create inline DOP for unresolved reference
            # (This is a fallback - normally types should exist)
            return f"DOP_{did_def.name}"

        # Inline type definition
        dop_name = f"DOP_{did_def.name}"
        if dop_name not in db.dops:
            dop = type_definition_to_dop(dop_name, did_def.type)
            db.add_dop(dop)

        return dop_name

    def _process_memory(self, doc: DiagnosticDescription, db: IRDatabase) -> None:
        """Process memory configuration into IR memory regions and data blocks."""
        if not doc.memory:
            return

        memory_config = doc.memory
        default_format = memory_config.default_address_format

        # Process memory regions
        for _name, region in memory_config.regions.items():
            ir_region = self._transform_memory_region(region, default_format)
            db.memory_regions.append(ir_region)

        # Process data blocks
        for _name, data_block in memory_config.data_blocks.items():
            ir_block = self._transform_data_block(data_block)
            db.data_blocks.append(ir_block)

    def _transform_memory_region(
        self,
        region: MemoryRegion,
        default_format: AddressFormat,
    ) -> IRMemoryRegion:
        """Transform a MemoryRegion model to IRMemoryRegion.

        Args:
        ----
            region: The memory region model.
            default_format: The default address format from config.

        Returns:
        -------
            IR representation of the memory region.

        """
        # Use region-specific format or fall back to default
        addr_format = region.address_format or default_format

        # Normalize sessions to tuple
        sessions: tuple[str, ...] = ()
        if region.session:
            if isinstance(region.session, list):
                sessions = tuple(region.session)
            else:
                sessions = (region.session,)

        return IRMemoryRegion(
            name=region.name,
            start_address=region.start_address,
            size=region.size,
            access=region.access.value,
            address_bytes=addr_format.address_bytes,
            length_bytes=addr_format.length_bytes,
            security_level=region.security_level,
            sessions=sessions,
        )

    def _transform_data_block(self, data_block: DataBlock) -> IRDataBlock:
        """Transform a DataBlock model to IRDataBlock.

        Args:
        ----
            data_block: The data block model.

        Returns:
        -------
            IR representation of the data block.

        """
        return IRDataBlock(
            name=data_block.name,
            block_type=data_block.type.value,
            memory_address=data_block.memory_address,
            memory_size=data_block.memory_size,
            data_format=data_block.data_format_identifier,
            max_block_length=data_block.max_block_length,
            security_level=data_block.security_level,
            session=data_block.session,
        )

    def _process_dtcs(self, doc: DiagnosticDescription, db: IRDatabase) -> None:
        """Process DTCs into IR format."""
        if not doc.dtcs:
            return

        # Get default snapshots and extended data from config
        default_snapshots: dict[str, DTCSnapshotDefinition] = {}
        default_extended: dict[str, DTCExtendedDataDefinition] = {}

        if doc.dtc_config:
            # Support both old and new field names
            if doc.dtc_config.default_snapshots:
                default_snapshots = doc.dtc_config.default_snapshots
            elif doc.dtc_config.snapshots:
                default_snapshots = doc.dtc_config.snapshots

            if doc.dtc_config.default_extended_data:
                default_extended = doc.dtc_config.default_extended_data
            elif doc.dtc_config.extended_data:
                default_extended = doc.dtc_config.extended_data

        # Process each DTC
        for dtc_code, dtc_def in doc.dtcs.items():
            ir_dtc = self._transform_dtc(dtc_code, dtc_def, default_snapshots, default_extended)
            db.dtcs.append(ir_dtc)

    def _transform_dtc(
        self,
        dtc_code: int,
        dtc_def: DTCDefinition,
        default_snapshots: dict[str, DTCSnapshotDefinition],
        default_extended: dict[str, DTCExtendedDataDefinition],
    ) -> IRDTC:
        """Transform a single DTC to IR format.

        Args:
        ----
            dtc_code: The 24-bit DTC code.
            dtc_def: The DTC definition model.
            default_snapshots: Default snapshot definitions from config.
            default_extended: Default extended data definitions from config.

        Returns:
        -------
            IR representation of the DTC.

        """
        # Resolve severity
        severity_value = self._get_severity_value(dtc_def.severity)

        # Collect snapshots - merge defaults with DTC-specific
        snapshots = self._collect_snapshots(dtc_def, default_snapshots)
        ir_snapshots = tuple(self._transform_snapshot(s) for s in snapshots)

        # Collect extended data - merge defaults with DTC-specific
        extended_data = self._collect_extended_data(dtc_def, default_extended)
        ir_extended = tuple(self._transform_extended_data(e) for e in extended_data)

        return IRDTC(
            code=dtc_code,
            name=dtc_def.name,
            description=dtc_def.description or "",
            severity=severity_value,
            functional_unit=dtc_def.functional_unit or 0,
            snapshots=ir_snapshots,
            extended_data=ir_extended,
            aging_threshold=dtc_def.aging_counter_threshold,
            aged_threshold=dtc_def.aged_counter_threshold,
            priority=dtc_def.priority,
        )

    def _get_severity_value(self, severity: int | None) -> int:
        """Convert severity to byte value.

        Args:
        ----
            severity: Severity level (1-4) or None.
                1=no_class (0x00), 2=maintenance_only (0x20),
                3=check_at_next_halt (0x40), 4=check_immediately (0x80)

        Returns:
        -------
            Severity byte value per ISO 14229.

        """
        if severity is None:
            return 0x00

        # Map severity integer (1-4) to UDS severity bytes
        severity_map = {
            1: 0x00,  # no_class
            2: 0x20,  # maintenance_only
            3: 0x40,  # check_at_next_halt
            4: 0x80,  # check_immediately
        }
        return severity_map.get(severity, 0x00)

    def _collect_snapshots(
        self,
        dtc_def: DTCDefinition,
        default_snapshots: dict[str, DTCSnapshotDefinition],
    ) -> list[DTCSnapshotDefinition]:
        """Collect all applicable snapshots for a DTC.

        Args:
        ----
            dtc_def: The DTC definition.
            default_snapshots: Default snapshot definitions.

        Returns:
        -------
            List of snapshot definitions to apply.

        """
        result: list[DTCSnapshotDefinition] = []

        # Add all default snapshots first
        result.extend(default_snapshots.values())

        # Add DTC-specific snapshots
        if dtc_def.snapshots:
            for item in dtc_def.snapshots:
                if isinstance(item, str):
                    # Reference to named snapshot (skip if already included in defaults)
                    if item in default_snapshots:
                        continue
                elif isinstance(item, DTCSnapshotDefinition):
                    result.append(item)

        return result

    def _collect_extended_data(
        self,
        dtc_def: DTCDefinition,
        default_extended: dict[str, DTCExtendedDataDefinition],
    ) -> list[DTCExtendedDataDefinition]:
        """Collect all applicable extended data for a DTC.

        Args:
        ----
            dtc_def: The DTC definition.
            default_extended: Default extended data definitions.

        Returns:
        -------
            List of extended data definitions to apply.

        """
        result: list[DTCExtendedDataDefinition] = []

        # Add all default extended data first
        result.extend(default_extended.values())

        # Add DTC-specific extended data
        if dtc_def.extended_data:
            for item in dtc_def.extended_data:
                if isinstance(item, str):
                    # Reference to named definition (skip if already included)
                    if item in default_extended:
                        continue
                elif isinstance(item, DTCExtendedDataDefinition):
                    result.append(item)

        return result

    def _transform_snapshot(
        self,
        snapshot: DTCSnapshotDefinition,
    ) -> IRSnapshotRecord:
        """Transform a snapshot definition to IR format.

        Args:
        ----
            snapshot: The snapshot definition model.

        Returns:
        -------
            IR representation of the snapshot.

        """
        data_items: list[IRSnapshotDataItem] = []
        byte_position = 0

        # Process either 'data' (detailed) or 'dids' (simple) format
        if snapshot.data:
            for data_record in snapshot.data:
                size = 2  # Default size, could be resolved from DID type
                data_items.append(
                    IRSnapshotDataItem(
                        did=data_record.did,
                        name=data_record.name or f"DID_{data_record.did:#06x}",
                        byte_position=byte_position,
                        byte_size=size,
                    )
                )
                byte_position += size
        elif snapshot.dids:
            for did in snapshot.dids:
                size = 2  # Default size
                data_items.append(
                    IRSnapshotDataItem(
                        did=did,
                        name=f"DID_{did:#06x}",
                        byte_position=byte_position,
                        byte_size=size,
                    )
                )
                byte_position += size

        return IRSnapshotRecord(
            record_number=snapshot.record_number,
            description=snapshot.description or "",
            data_items=tuple(data_items),
            total_size=byte_position,
        )

    def _transform_extended_data(
        self,
        extended: DTCExtendedDataDefinition,
    ) -> IRExtendedDataRecord:
        """Transform extended data definition to IR format.

        Args:
        ----
            extended: The extended data definition model.

        Returns:
        -------
            IR representation of the extended data record.

        """
        # Calculate size from type (simplified - uses defaults)
        size = self._get_type_byte_size(extended.type)

        # Get type reference as string
        type_ref: str
        if extended.type is None:
            type_ref = "u8"
        elif isinstance(extended.type, TypeDefinition):
            type_ref = extended.type.base.value
        else:
            type_ref = extended.type

        return IRExtendedDataRecord(
            record_number=extended.record_number,
            name=extended.name or f"ExtData_{extended.record_number:#04x}",
            type_ref=type_ref,
            byte_size=size,
        )

    def _get_type_byte_size(self, type_name: str | TypeDefinition | None) -> int:
        """Get byte size for a type name.

        Args:
        ----
            type_name: Type name (e.g., "u8", "u16", "u32") or TypeDefinition.

        Returns:
        -------
            Byte size of the type.

        """
        if not type_name:
            return 1

        # Handle TypeDefinition objects
        if isinstance(type_name, TypeDefinition):
            # Use the base type from the TypeDefinition
            type_name = type_name.base.value

        type_sizes = {
            "u8": 1,
            "i8": 1,
            "u16": 2,
            "i16": 2,
            "u24": 3,
            "i24": 3,
            "u32": 4,
            "i32": 4,
            "f32": 4,
            "f64": 8,
        }
        return type_sizes.get(type_name, 2)
