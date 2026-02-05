"""Convert IR models to FlatBuffers binary format.

This module provides the IRToFlatBuffersConverter class that takes an
IRDatabase and produces a FlatBuffers binary representation suitable
for embedding in an MDD file.

The converter generates protocol structures required by CDA (Classic Diagnostic
Adapter). CDA looks up protocols via:
    DiagLayer.comParamRefs[*].protocol.diagLayer.shortName

Supported protocol names (mapped from YAML protocol_short_name):
    - UDSonDoIP -> UDS_Ethernet_DoIP_DOBT (default for DoIP)
    - UDSonCAN -> UDS_CAN
    - ISO_14229_3_DoIP -> UDS_Ethernet_DoIP

Note on ComplexValue and Union Vectors:
    CDA expects ComplexValue.entries to be a union vector [SimpleOrComplexValueEntry]
    but Python FlatBuffers doesn't support union vectors natively. This module
    patches ComplexValueT.Pack at runtime to produce the correct union vector format.

    The FlatBuffers union vector format requires two separate fields:
    - entries_type: vector of u8 tags (SimpleOrComplexValueEntry enum values)
    - entries: vector of offsets to the actual tables (SimpleValue or ComplexValue)

Note on String Interning:
    This module uses StringInterningBuilder to cache string offsets, reducing
    FlatBuffers size by ~60% through string deduplication. Without interning,
    repeated strings like "SERVICE_ID" (100+ copies) would each allocate new
    storage. The builder caches offsets by string value, reusing them on
    subsequent CreateString calls.
"""

# mypy: disable-error-code="no-untyped-call"

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import flatbuffers

from yaml_to_mdd.fbs_generated.dataformat.CodedConst import CodedConstT
from yaml_to_mdd.fbs_generated.dataformat.ComParam import ComParamT
from yaml_to_mdd.fbs_generated.dataformat.ComParamRef import ComParamRefT
from yaml_to_mdd.fbs_generated.dataformat.ComParamSpecificData import (
    ComParamSpecificData,
)
from yaml_to_mdd.fbs_generated.dataformat.ComParamType import ComParamType
from yaml_to_mdd.fbs_generated.dataformat.ComplexComParam import ComplexComParamT
from yaml_to_mdd.fbs_generated.dataformat.CompuInternalToPhys import (
    CompuInternalToPhysT,
)
from yaml_to_mdd.fbs_generated.dataformat.CompuMethod import CompuMethodT
from yaml_to_mdd.fbs_generated.dataformat.CompuScale import CompuScaleT
from yaml_to_mdd.fbs_generated.dataformat.CompuValues import CompuValuesT
from yaml_to_mdd.fbs_generated.dataformat.DataType import DataType
from yaml_to_mdd.fbs_generated.dataformat.DiagCodedType import DiagCodedTypeT
from yaml_to_mdd.fbs_generated.dataformat.DiagComm import DiagCommT
from yaml_to_mdd.fbs_generated.dataformat.DiagLayer import DiagLayerT
from yaml_to_mdd.fbs_generated.dataformat.DiagService import DiagServiceT
from yaml_to_mdd.fbs_generated.dataformat.DOP import DOPT
from yaml_to_mdd.fbs_generated.dataformat.DOPType import DOPType
from yaml_to_mdd.fbs_generated.dataformat.EcuData import EcuDataT
from yaml_to_mdd.fbs_generated.dataformat.NormalDOP import NormalDOPT
from yaml_to_mdd.fbs_generated.dataformat.Param import ParamT
from yaml_to_mdd.fbs_generated.dataformat.ParamSpecificData import ParamSpecificData
from yaml_to_mdd.fbs_generated.dataformat.Protocol import ProtocolT
from yaml_to_mdd.fbs_generated.dataformat.RegularComParam import RegularComParamT
from yaml_to_mdd.fbs_generated.dataformat.Request import RequestT
from yaml_to_mdd.fbs_generated.dataformat.Response import ResponseT
from yaml_to_mdd.fbs_generated.dataformat.SimpleValue import SimpleValueT
from yaml_to_mdd.fbs_generated.dataformat.SpecificDataType import SpecificDataType
from yaml_to_mdd.fbs_generated.dataformat.SpecificDOPData import SpecificDOPData
from yaml_to_mdd.fbs_generated.dataformat.StandardLengthType import StandardLengthTypeT
from yaml_to_mdd.fbs_generated.dataformat.Value import ValueT
from yaml_to_mdd.fbs_generated.dataformat.ValueEntry import ValueEntryT
from yaml_to_mdd.fbs_generated.dataformat.Variant import VariantT
from yaml_to_mdd.fbs_generated.dataformat.VariantPattern import VariantPatternT
from yaml_to_mdd.fbs_generated.dataformat.MatchingParameter import MatchingParameterT
from yaml_to_mdd.fbs_generated.dataformat.ParentRef import ParentRefT
from yaml_to_mdd.fbs_generated.dataformat.ParentRefType import ParentRefType
from yaml_to_mdd.fbs_generated.dataformat.ComplexValue import ComplexValueT
from yaml_to_mdd.fbs_generated.dataformat.State import StateT
from yaml_to_mdd.fbs_generated.dataformat.StateChart import StateChartT
from yaml_to_mdd.fbs_generated.dataformat.StateTransition import StateTransitionT

if TYPE_CHECKING:
    from yaml_to_mdd.ir.database import IRDatabase, IRVariant
    from yaml_to_mdd.ir.services import IRDiagService, IRParam, IRRequest, IRResponse
    from yaml_to_mdd.ir.types import IRDOP, IRCompuMethod, IRCompuScale, IRDiagCodedType

# Mapping from YAML protocol_short_name to CDA protocol names
PROTOCOL_NAME_MAP: dict[str, str] = {
    "UDSonDoIP": "UDS_Ethernet_DoIP_DOBT",
    "UDSonCAN": "UDS_CAN",
    "UDSonLIN": "UDS_LIN",
    "UDSonFR": "UDS_FlexRay",
    "UDSonIP": "UDS_Ethernet_DoIP",
    "ISO_14229_3_DoIP": "UDS_Ethernet_DoIP",
    "ISO_15765_3_CAN": "UDS_CAN",
    "ISO_14229_3_CAN": "UDS_CAN",
}


class StringInterningBuilder(flatbuffers.Builder):
    """FlatBuffers Builder with string interning for size optimization.

    This builder caches string offsets by value, so repeated strings
    (e.g., "SERVICE_ID" appearing 100+ times) only allocate storage once.
    Reduces FlatBuffers binary size by ~60% for typical diagnostic data.

    Usage:
        builder = StringInterningBuilder(1024)
        # Use like regular flatbuffers.Builder
        offset = ecu_data.Pack(builder)
    """

    def __init__(self, initialSize: int = 1024) -> None:
        """Initialize builder with string cache.

        Args:
        ----
            initialSize: Initial buffer size in bytes.

        """
        super().__init__(initialSize)
        self._string_cache: dict[str, int] = {}

    def CreateString(  # noqa: N802 - Matching FlatBuffers API
        self, s: str | bytes, encoding: str = "utf-8", errors: str = "strict"
    ) -> int:
        """Create a string with interning (caching).

        If the string was already created, returns the cached offset.
        Otherwise creates a new string and caches its offset.

        Args:
        ----
            s: String to create (str or bytes).
            encoding: Encoding for str-to-bytes conversion.
            errors: Error handling for encoding.

        Returns:
        -------
            Offset to the string in the buffer.

        """
        # Normalize to string for cache key
        if isinstance(s, bytes):
            cache_key = s.decode(encoding, errors)
        else:
            cache_key = s

        # Check cache first
        if cache_key in self._string_cache:
            return self._string_cache[cache_key]

        # Create new string and cache it
        offset = super().CreateString(s, encoding, errors)
        self._string_cache[cache_key] = offset
        return offset

    @property
    def strings_cached(self) -> int:
        """Return number of unique strings cached."""
        return len(self._string_cache)


# Union type tags for SimpleOrComplexValueEntry (CDA FlatBuffers schema)
class SimpleOrComplexValueEntry:
    """Union type tags matching CDA's FlatBuffers schema."""

    NONE = 0
    SimpleValue = 1
    ComplexValue = 2


class CDAComplexValueT:
    """CDA-compatible ComplexValue that uses union vector format.

    CDA expects ComplexValue.entries to be [SimpleOrComplexValueEntry] union vector,
    but Python FlatBuffers doesn't support union vectors natively. This class
    manually builds the correct binary format with entries_type and entries vectors.

    The FlatBuffers union vector format requires two separate fields:
    - entries_type: vector of u8 tags (SimpleOrComplexValueEntry enum values)
    - entries: vector of offsets to the actual tables (SimpleValue or ComplexValue)

    Usage:
        cv = CDAComplexValueT()
        cv.add_simple_value("3584")  # Add ECU address
        offset = cv.Pack(builder)
    """

    def __init__(self) -> None:
        """Initialize empty ComplexValue."""
        self._entries: list[tuple[int, SimpleValueT]] = []  # (tag, value)

    def add_simple_value(self, value: str) -> None:
        """Add a SimpleValue entry to the ComplexValue.

        Args:
        ----
            value: The string value to add.

        """
        simple_val = SimpleValueT()
        simple_val.value = value
        self._entries.append((SimpleOrComplexValueEntry.SimpleValue, simple_val))

    def Pack(self, builder: flatbuffers.Builder) -> int:  # noqa: N802
        """Serialize ComplexValue with union vector format.

        This creates the binary format expected by CDA:
        - entries_type vector at vtable slot 0 (VT=4)
        - entries vector at vtable slot 1 (VT=6)

        Args:
        ----
            builder: FlatBuffers builder instance.

        Returns:
        -------
            Offset to the serialized ComplexValue table.

        """
        if not self._entries:
            # Empty ComplexValue - just create table with no entries
            builder.StartObject(2)
            return int(builder.EndObject())

        # Step 1: Serialize all entry tables first (SimpleValue tables)
        entry_offsets: list[int] = []
        for _tag, value in self._entries:
            # SimpleValueT.Pack() returns offset
            offset = value.Pack(builder)
            entry_offsets.append(offset)

        # Step 2: Create entries_type vector (u8 tags)
        builder.StartVector(1, len(self._entries), 1)  # elemSize=1, alignment=1
        for tag, _ in reversed(self._entries):
            builder.PrependByte(tag)
        entries_type_offset = builder.EndVector()

        # Step 3: Create entries vector (offsets to tables)
        builder.StartVector(
            4, len(self._entries), 4
        )  # elemSize=4 (offset), alignment=4
        for offset in reversed(entry_offsets):
            builder.PrependUOffsetTRelative(offset)
        entries_offset = builder.EndVector()

        # Step 4: Create ComplexValue table with both vectors
        builder.StartObject(2)  # 2 fields: entries_type, entries
        builder.PrependUOffsetTRelativeSlot(
            0, entries_type_offset, 0
        )  # slot 0 = entries_type
        builder.PrependUOffsetTRelativeSlot(1, entries_offset, 0)  # slot 1 = entries
        return int(builder.EndObject())


def _complexvalue_cda_pack(self: ComplexValueT, builder: flatbuffers.Builder) -> int:
    """CDA-compatible Pack method for ComplexValueT.

    This replaces the generated ComplexValueT.Pack() to produce union vector
    format instead of wrapper table format.

    The standard generated Pack() creates:
        ComplexValue { entries: [ValueEntry] }

    CDA expects:
        ComplexValue { entries: [SimpleOrComplexValueEntry] }  // union vector

    Union vectors require two parallel arrays:
        entries_type: [u8]  - type tags for each entry
        entries: [offset]   - offsets to the actual tables

    Args:
    ----
        self: The ComplexValueT instance.
        builder: FlatBuffers builder instance.

    Returns:
    -------
        Offset to the serialized ComplexValue table.

    """
    if self.entries is None or len(self.entries) == 0:
        # Empty ComplexValue - create empty table
        builder.StartObject(2)
        return int(builder.EndObject())

    # Extract values from ValueEntry wrappers and pack them
    entry_offsets: list[int] = []
    entry_tags: list[int] = []

    for entry in self.entries:
        if entry.simpleValue is not None:
            # Pack SimpleValue and record tag
            offset = entry.simpleValue.Pack(builder)
            entry_offsets.append(offset)
            entry_tags.append(SimpleOrComplexValueEntry.SimpleValue)
        elif entry.complexValue is not None:
            # Recursively pack nested ComplexValue
            offset = _complexvalue_cda_pack(entry.complexValue, builder)
            entry_offsets.append(offset)
            entry_tags.append(SimpleOrComplexValueEntry.ComplexValue)
        else:
            # Empty entry - skip (CDA doesn't handle NONE in union vectors)
            continue

    if not entry_offsets:
        # All entries were empty
        builder.StartObject(2)
        return int(builder.EndObject())

    # Create type tags vector (u8)
    builder.StartVector(1, len(entry_tags), 1)
    for tag in reversed(entry_tags):
        builder.PrependByte(tag)
    entries_type_offset = builder.EndVector()

    # Create offsets vector
    builder.StartVector(4, len(entry_offsets), 4)
    for offset in reversed(entry_offsets):
        builder.PrependUOffsetTRelative(offset)
    entries_offset = builder.EndVector()

    # Build ComplexValue table with both vectors
    builder.StartObject(2)
    builder.PrependUOffsetTRelativeSlot(0, entries_type_offset, 0)
    builder.PrependUOffsetTRelativeSlot(1, entries_offset, 0)
    return int(builder.EndObject())


def _patch_complexvalue_pack() -> None:
    """Patch ComplexValueT.Pack to produce CDA-compatible union vector format.

    This must be called before any FlatBuffers serialization that includes
    ComplexValue tables.
    """
    # Replace the Pack method on the class
    ComplexValueT.Pack = _complexvalue_cda_pack  # type: ignore[method-assign]


# Apply the patch at module load time
_patch_complexvalue_pack()


@dataclass
class DoIPAddressingConfig:
    """DoIP addressing configuration for FlatBuffers conversion.

    These values are required by CDA to establish DoIP communication.
    Also includes UDS timing parameters and DoIP-specific timeouts.
    """

    # DoIP addressing
    logical_gateway_address: int = 0x0E00
    logical_ecu_address: int = 0x0E00
    logical_functional_address: int = 0xE400
    logical_tester_address: int | None = None

    # UDS Timing parameters (in milliseconds)
    p2_max_ms: int | None = None  # P2 timeout: max time for initial response
    p2_star_ms: int | None = None  # P2* timeout: max time after NRC 0x78
    p6_max_ms: int | None = None  # P6 timeout: extended timing for data transfer
    p6_star_ms: int | None = None  # P6* timeout: extended after NRC 0x78
    s3_ms: int | None = None  # S3 timeout: session keepalive interval

    # NRC completion timeouts
    rc78_completion_timeout_ms: int | None = None  # ResponsePending completion
    rc21_completion_timeout_ms: int | None = None  # BusyRepeatRequest completion

    # DoIP-specific timeouts
    doip_diagnostic_ack_timeout_ms: int | None = None
    doip_routing_activation_timeout_ms: int | None = None

    # Retry configuration
    doip_number_of_retries: int | None = None
    doip_retry_period_ms: int | None = None


class IRToFlatBuffersConverter:
    """Convert IR database to FlatBuffers binary format.

    This converter transforms an IRDatabase into a FlatBuffers binary
    representation. The output is a DiagLayer containing all DOPs and
    diagnostic services, with proper protocol references for CDA compatibility.

    CDA requires protocols to be accessible via:
        DiagLayer.comParamRefs[*].protocol.diagLayer.shortName

    Usage:
        converter = IRToFlatBuffersConverter()
        fbs_bytes = converter.convert(ir_database)

        # Or with explicit protocols:
        fbs_bytes = converter.convert(ir_database, protocols=["UDSonDoIP"])
    """

    def __init__(self, builder_size: int = 1024 * 1024) -> None:
        """Initialize the converter.

        Args:
        ----
            builder_size: Initial FlatBuffers builder size in bytes.
                Defaults to 1MB which should be sufficient for most ECUs.

        """
        self._builder_size = builder_size
        self._dop_cache: dict[str, DOPT] = {}  # DOP name -> converted DOP
        self._protocol_cache: dict[str, ProtocolT] = {}  # Protocol name -> Protocol
        self._all_services_cache: list[DiagServiceT] = (
            []
        )  # All services including variant-specific

    def convert(
        self,
        db: IRDatabase,
        protocols: list[str] | None = None,
        doip_addressing: DoIPAddressingConfig | None = None,
    ) -> bytes:
        """Convert IRDatabase to FlatBuffers bytes.

        Creates an EcuData structure as the root type, which is required by CDA.
        The structure is: EcuData -> Variant -> DiagLayer -> ComParamRef -> Protocol

        Args:
        ----
            db: The IR database to convert.
            protocols: List of protocol short names (from YAML) to include.
                If None, defaults to ["UDSonDoIP"].
            doip_addressing: DoIP addressing configuration. If None, defaults
                are used. Required for CDA to establish DoIP communication.

        Returns:
        -------
            FlatBuffers serialized bytes representing an EcuData root.

        """
        # Reset state for fresh conversion
        self._dop_cache.clear()
        self._protocol_cache.clear()

        # Default to DoIP protocol if none specified
        if protocols is None:
            protocols = ["UDSonDoIP"]

        # Use default DoIP addressing if not provided
        if doip_addressing is None:
            doip_addressing = DoIPAddressingConfig()

        # Create protocols first (they are referenced by ComParamRefs and parentRefs)
        # For DoIP, create both UDS_Ethernet_DoIP and UDS_Ethernet_DoIP_DOBT
        # to match ODX-generated MDDs structure
        for proto_name in protocols:
            cda_name = PROTOCOL_NAME_MAP.get(proto_name, proto_name)
            protocol = self._create_protocol(cda_name)
            self._protocol_cache[cda_name] = protocol
            # For DoIP, also create the companion protocol
            if "DoIP" in cda_name:
                if (
                    cda_name == "UDS_Ethernet_DoIP"
                    and "UDS_Ethernet_DoIP_DOBT" not in self._protocol_cache
                ):
                    dobt_protocol = self._create_protocol("UDS_Ethernet_DoIP_DOBT")
                    self._protocol_cache["UDS_Ethernet_DoIP_DOBT"] = dobt_protocol
                elif (
                    cda_name == "UDS_Ethernet_DoIP_DOBT"
                    and "UDS_Ethernet_DoIP" not in self._protocol_cache
                ):
                    base_protocol = self._create_protocol("UDS_Ethernet_DoIP")
                    self._protocol_cache["UDS_Ethernet_DoIP"] = base_protocol

        # Create the DiagLayer for the ECU
        diag_layer = DiagLayerT()
        diag_layer.shortName = db.ecu_name

        # Convert DOPs - build cache for reference lookup
        for dop_name, ir_dop in db.dops.items():
            fbs_dop = self._convert_dop(ir_dop)
            self._dop_cache[dop_name] = fbs_dop

        # Convert services
        # Base DiagLayer only includes services without variant_ref (not variant-specific)
        services: list[DiagServiceT] = []
        all_services: list[DiagServiceT] = []  # All services for variant lookups
        for _service_name, ir_service in db.services.items():
            fbs_service = self._convert_service(ir_service)
            all_services.append(fbs_service)
            # Only include in base if not variant-specific
            if ir_service.variant_ref is None:
                services.append(fbs_service)

        diag_layer.diagServices = services if services else None  # type: ignore[assignment]

        # Store all services for variant reference (including variant-specific ones)
        self._all_services_cache = all_services

        # Add ComParamRefs with protocol references and addressing parameters
        # CDA requires these parameters for DoIP communication
        com_param_refs: list[ComParamRefT] = []
        for cda_name, protocol in self._protocol_cache.items():
            # Create ComParamRefs for DoIP addressing parameters
            if "DoIP" in cda_name:
                com_param_refs.extend(
                    self._create_doip_com_param_refs(protocol, doip_addressing)
                )
            else:
                # For non-DoIP protocols, just add protocol reference
                com_param_ref = ComParamRefT()
                com_param_ref.protocol = protocol
                com_param_refs.append(com_param_ref)

        if com_param_refs:
            diag_layer.comParamRefs = com_param_refs  # type: ignore[assignment]

        # Add StateCharts for sessions and security access
        # CDA uses these to validate service pre-conditions
        state_charts = self._create_state_charts(db)
        if state_charts:
            diag_layer.stateCharts = state_charts  # type: ignore[assignment]

        # Create Variants from IR database
        variants = self._create_variants(db, diag_layer)

        # Create EcuData as the root type
        ecu_data = EcuDataT()
        ecu_data.ecuName = db.ecu_name
        ecu_data.version = "1.0"
        ecu_data.variants = variants

        # Serialize using Object API with string interning for size optimization
        builder = StringInterningBuilder(self._builder_size)
        offset = ecu_data.Pack(builder)
        builder.Finish(offset)

        return bytes(builder.Output())

    def _create_variants(
        self, db: "IRDatabase", base_diag_layer: DiagLayerT
    ) -> list[VariantT]:
        """Create Variant tables from IR variants.

        Args:
        ----
            db: The IR database containing variant definitions.
            base_diag_layer: The base DiagLayer with all services.

        Returns:
        -------
            List of VariantT for the ECU.

        """
        variants: list[VariantT] = []

        # If no variants defined, create a single base variant
        if not db.variants:
            variant = VariantT()
            variant.diagLayer = base_diag_layer
            variant.isBaseVariant = True
            return [variant]

        # Create a variant for each IR variant
        for ir_variant in db.variants:
            variant = VariantT()

            # Create DiagLayer for this variant
            # Non-base variants get their own DiagLayer with just the short_name
            if ir_variant.is_base_variant:
                variant.diagLayer = base_diag_layer
            else:
                # Create a minimal DiagLayer for non-base variant
                # Non-base variants only include their own services, not inherited ones
                variant_layer = DiagLayerT()
                variant_layer.shortName = ir_variant.short_name

                # Only include services specified in service_refs (variant-specific)
                # If empty, variant inherits from parent via parentRef
                if ir_variant.service_refs:
                    # Look in ALL services (including variant-specific) for matches
                    variant_services = []
                    for svc in self._all_services_cache:
                        svc_name = svc.diagComm.shortName if svc.diagComm else ""
                        if svc_name in ir_variant.service_refs:
                            variant_services.append(svc)
                    variant_layer.diagServices = (
                        variant_services if variant_services else None
                    )
                else:
                    # No variant-specific services - inherit all from parent
                    variant_layer.diagServices = None

                # comParamRefs and stateCharts are typically inherited, not copied
                variant_layer.comParamRefs = None
                variant_layer.stateCharts = None
                variant.diagLayer = variant_layer

            variant.isBaseVariant = ir_variant.is_base_variant

            # Create variant patterns for detection
            if ir_variant.matching_parameters:
                variant_pattern = VariantPatternT()
                matching_params: list[MatchingParameterT] = []

                for ir_mp in ir_variant.matching_parameters:
                    mp = MatchingParameterT()
                    mp.expectedValue = ir_mp.expected_value

                    # Create service reference with proper DiagComm for matching
                    if ir_mp.diag_service_ref:
                        diag_service = DiagServiceT()
                        diag_comm = DiagCommT()
                        diag_comm.shortName = ir_mp.diag_service_ref
                        diag_service.diagComm = diag_comm
                        mp.diagService = diag_service

                    # Create output param reference if specified
                    if ir_mp.out_param_ref:
                        out_param = ParamT()
                        out_param.shortName = ir_mp.out_param_ref
                        mp.outParam = out_param

                    mp.usePhysicalAddressing = ir_mp.use_physical_addressing
                    matching_params.append(mp)

                variant_pattern.matchingParameter = matching_params
                variant.variantPattern = [variant_pattern]

            # Set parent references
            parent_refs: list[ParentRefT] = []

            if ir_variant.is_base_variant:
                # Base variant gets Protocol parentRefs (matches ODX structure)
                # Order: UDS_Ethernet_DoIP first, then UDS_Ethernet_DoIP_DOBT
                for proto_name in ["UDS_Ethernet_DoIP", "UDS_Ethernet_DoIP_DOBT"]:
                    if proto_name in self._protocol_cache:
                        parent_ref = ParentRefT()
                        parent_ref.refType = ParentRefType.Protocol
                        parent_ref.ref = self._protocol_cache[proto_name]
                        parent_refs.append(parent_ref)
            elif ir_variant.parent_ref:
                # Non-base variants reference their parent Variant
                # Find the parent variant (base) that was already created
                parent_variant = next(
                    (
                        v
                        for v in variants
                        if v.diagLayer
                        and v.diagLayer.shortName == ir_variant.parent_ref
                    ),
                    None,
                )
                if parent_variant:
                    parent_ref = ParentRefT()
                    parent_ref.refType = ParentRefType.Variant
                    parent_ref.ref = parent_variant
                    parent_refs.append(parent_ref)

            if parent_refs:
                variant.parentRefs = parent_refs

            variants.append(variant)

        return variants

    def _create_state_charts(self, db: "IRDatabase") -> list[StateChartT]:
        """Create StateChart tables for sessions and security access.

        CDA uses StateCharts to track diagnostic session and security access states.
        These are used to validate service pre-conditions.

        Args:
        ----
            db: The IR database containing session and security definitions.

        Returns:
        -------
            List of StateChartT instances (Session and SecurityAccess).

        """
        state_charts: list[StateChartT] = []

        # Create Session state chart
        if db.sessions:
            session_chart = StateChartT()
            session_chart.shortName = "Session"
            session_chart.semantic = "SESSION"

            # Create states for each session
            states: list[StateT] = []
            for name, _session_id in db.sessions.items():
                state = StateT()
                # Capitalize first letter for CDA compatibility (e.g., "default" -> "Default")
                state.shortName = name.capitalize()
                states.append(state)

            session_chart.states = states

            # Set default as start state
            session_chart.startStateShortNameRef = "Default"

            # Create transitions (from each state to each other state)
            # For simplicity, allow all transitions (CDA validates based on service pre-conditions)
            transitions: list[StateTransitionT] = []
            state_names = [s.shortName for s in states]
            for source in state_names:
                for target in state_names:
                    if source != target:
                        trans = StateTransitionT()
                        trans.shortName = f"{source}_to_{target}"
                        trans.sourceShortNameRef = source
                        trans.targetShortNameRef = target
                        transitions.append(trans)

            session_chart.stateTransitions = transitions

            state_charts.append(session_chart)

        # Create SecurityAccess state chart
        if db.security_levels:
            security_chart = StateChartT()
            security_chart.shortName = "SecurityAccess"
            security_chart.semantic = "SECURITY-ACCESS"

            # Create states for each security level + "Locked" initial state
            states = []
            locked_state = StateT()
            locked_state.shortName = "Locked"
            states.append(locked_state)

            for name, _level in db.security_levels.items():
                state = StateT()
                # Use the security level name (e.g., "level_03" -> "Level_03")
                state.shortName = name.replace("level_", "Level_")
                states.append(state)

            security_chart.states = states
            security_chart.startStateShortNameRef = "Locked"

            # Transitions: Locked -> any level, any level -> Locked
            transitions = []
            for state in states[1:]:  # Skip Locked
                # Locked -> Level_X
                trans = StateTransitionT()
                trans.shortName = f"Locked_to_{state.shortName}"
                trans.sourceShortNameRef = "Locked"
                trans.targetShortNameRef = state.shortName
                transitions.append(trans)

                # Level_X -> Locked
                trans = StateTransitionT()
                trans.shortName = f"{state.shortName}_to_Locked"
                trans.sourceShortNameRef = state.shortName
                trans.targetShortNameRef = "Locked"
                transitions.append(trans)

            security_chart.stateTransitions = transitions

            state_charts.append(security_chart)

        return state_charts

    def _create_doip_com_param_refs(
        self,
        protocol: ProtocolT,
        addressing: DoIPAddressingConfig,
    ) -> list[ComParamRefT]:
        """Create ComParamRefs for DoIP addressing parameters.

        CDA requires these specific parameters to establish DoIP communication:
        - CP_DoIPLogicalGatewayAddress (simple)
        - CP_UniqueRespIdTable -> CP_DoIPLogicalEcuAddress (complex)
        - CP_DoIPLogicalFunctionalAddress (simple)
        - CP_DoIPLogicalTesterAddress (simple)

        Args:
        ----
            protocol: The Protocol to reference.
            addressing: DoIP addressing configuration.

        Returns:
        -------
            List of ComParamRefT instances with addressing parameters.

        """
        refs: list[ComParamRefT] = []

        # Gateway address (simple)
        refs.append(
            self._create_simple_com_param_ref(
                protocol,
                "CP_DoIPLogicalGatewayAddress",
                str(addressing.logical_gateway_address),
            )
        )

        # ECU address via UniqueRespIdTable (complex with union vector)
        # CDA looks up CP_UniqueRespIdTable and inside it CP_DoIPLogicalEcuAddress
        # Uses CDAComplexValueT to generate correct union vector format
        refs.append(
            self._create_complex_com_param_ref(
                protocol,
                "CP_UniqueRespIdTable",
                [("CP_DoIPLogicalEcuAddress", str(addressing.logical_ecu_address))],
            )
        )

        # Functional address (simple)
        refs.append(
            self._create_simple_com_param_ref(
                protocol,
                "CP_DoIPLogicalFunctionalAddress",
                str(addressing.logical_functional_address),
            )
        )

        # Tester address (simple) - only if provided
        if addressing.logical_tester_address is not None:
            refs.append(
                self._create_simple_com_param_ref(
                    protocol,
                    "CP_DoIPLogicalTesterAddress",
                    str(addressing.logical_tester_address),
                )
            )

        # UDS Timing parameters
        # P2 timeout (P2Max in ODX/MDD terminology)
        if addressing.p2_max_ms is not None:
            refs.append(
                self._create_simple_com_param_ref(
                    protocol,
                    "CP_P2Max",
                    str(addressing.p2_max_ms),
                )
            )

        # P2* timeout (P2Star in ODX/MDD terminology)
        if addressing.p2_star_ms is not None:
            refs.append(
                self._create_simple_com_param_ref(
                    protocol,
                    "CP_P2Star",
                    str(addressing.p2_star_ms),
                )
            )

        # P6 timeout (extended timing for data transfer)
        if addressing.p6_max_ms is not None:
            refs.append(
                self._create_simple_com_param_ref(
                    protocol,
                    "CP_P6Max",
                    str(addressing.p6_max_ms),
                )
            )

        # P6* timeout (extended timing after NRC 0x78)
        if addressing.p6_star_ms is not None:
            refs.append(
                self._create_simple_com_param_ref(
                    protocol,
                    "CP_P6Star",
                    str(addressing.p6_star_ms),
                )
            )

        # NRC 0x78 (ResponsePending) completion timeout
        if addressing.rc78_completion_timeout_ms is not None:
            refs.append(
                self._create_simple_com_param_ref(
                    protocol,
                    "CP_RC78CompletionTimeout",
                    str(addressing.rc78_completion_timeout_ms),
                )
            )

        # NRC 0x21 (BusyRepeatRequest) completion timeout
        if addressing.rc21_completion_timeout_ms is not None:
            refs.append(
                self._create_simple_com_param_ref(
                    protocol,
                    "CP_RC21CompletionTimeout",
                    str(addressing.rc21_completion_timeout_ms),
                )
            )

        # DoIP diagnostic acknowledgement timeout
        if addressing.doip_diagnostic_ack_timeout_ms is not None:
            refs.append(
                self._create_simple_com_param_ref(
                    protocol,
                    "CP_DoIPDiagnosticAckTimeout",
                    str(addressing.doip_diagnostic_ack_timeout_ms),
                )
            )

        # DoIP routing activation timeout
        if addressing.doip_routing_activation_timeout_ms is not None:
            refs.append(
                self._create_simple_com_param_ref(
                    protocol,
                    "CP_DoIPRoutingActivationTimeout",
                    str(addressing.doip_routing_activation_timeout_ms),
                )
            )

        # DoIP retry configuration
        if addressing.doip_number_of_retries is not None:
            refs.append(
                self._create_simple_com_param_ref(
                    protocol,
                    "CP_DoIPNumberOfRetries",
                    str(addressing.doip_number_of_retries),
                )
            )

        if addressing.doip_retry_period_ms is not None:
            refs.append(
                self._create_simple_com_param_ref(
                    protocol,
                    "CP_DoIPRetryPeriod",
                    str(addressing.doip_retry_period_ms),
                )
            )

        return refs

    def _create_complex_com_param_ref(
        self,
        protocol: ProtocolT,
        param_name: str,
        entries: list[tuple[str, str]],
    ) -> ComParamRefT:
        """Create a ComParamRef with a complex value using CDA-compatible union vector.

        CDA expects ComplexComParam to have:
        - comParams: list of ComParam definitions (REGULAR with DOP)
        - Corresponding complexValue entries with actual values

        The complexValue uses CDAComplexValueT which generates the correct union
        vector format that CDA expects ([SimpleOrComplexValueEntry]).

        Args:
        ----
            protocol: The Protocol to reference.
            param_name: The ComParam short name (e.g., "CP_UniqueRespIdTable").
            entries: List of (param_name, value) tuples for nested parameters.

        Returns:
        -------
            ComParamRefT instance.

        """
        com_param_ref = ComParamRefT()
        com_param_ref.protocol = protocol

        # Create parent ComParam with COMPLEX type
        com_param = ComParamT()
        com_param.shortName = param_name
        com_param.comParamType = ComParamType.COMPLEX

        # Create ComplexComParam with nested ComParams definitions
        complex_com_param = ComplexComParamT()
        complex_com_param.comParams = []

        for entry_name, _ in entries:
            # Each entry needs a REGULAR ComParam with DOP
            inner_com_param = ComParamT()
            inner_com_param.shortName = entry_name
            inner_com_param.comParamType = ComParamType.REGULAR

            regular_com_param = RegularComParamT()
            dop = DOPT()
            dop.shortName = f"{entry_name}_DOP"
            dop.dopType = DOPType.REGULAR
            normal_dop = NormalDOPT()
            dop.specificDataType = SpecificDOPData.NormalDOP
            dop.specificData = normal_dop
            regular_com_param.dop = dop

            inner_com_param.specificDataType = ComParamSpecificData.RegularComParam
            inner_com_param.specificData = regular_com_param

            complex_com_param.comParams.append(inner_com_param)

        com_param.specificDataType = ComParamSpecificData.ComplexComParam
        com_param.specificData = complex_com_param
        com_param_ref.comParam = com_param

        # Create ComplexValue with ValueEntry wrapper tables
        # The patched ComplexValueT.Pack() will convert this to CDA's union vector format
        complex_value = ComplexValueT()
        complex_value.entries = []
        for _, value in entries:
            # Create SimpleValue
            simple_val = SimpleValueT()
            simple_val.value = value
            # Wrap in ValueEntry (converted to union vector by patched Pack)
            entry = ValueEntryT()
            entry.simpleValue = simple_val
            complex_value.entries.append(entry)

        com_param_ref.complexValue = complex_value

        return com_param_ref

    def _create_simple_com_param_ref(
        self,
        protocol: ProtocolT,
        param_name: str,
        value: str,
    ) -> ComParamRefT:
        """Create a ComParamRef with a simple value.

        CDA expects ComParam to have type REGULAR with a RegularComParam
        containing a DOP (Data Object Property).

        Args:
        ----
            protocol: The Protocol to reference.
            param_name: The ComParam short name.
            value: The simple value as string.

        Returns:
        -------
            ComParamRefT instance.

        """
        com_param_ref = ComParamRefT()
        com_param_ref.protocol = protocol

        # Create ComParam with the parameter name and REGULAR type
        com_param = ComParamT()
        com_param.shortName = param_name
        com_param.comParamType = ComParamType.REGULAR

        # Create RegularComParam with a minimal DOP
        regular_com_param = RegularComParamT()

        # Create a minimal DOP - CDA only extracts unit from it
        dop = DOPT()
        dop.shortName = f"{param_name}_DOP"
        dop.dopType = DOPType.REGULAR

        normal_dop = NormalDOPT()
        dop.specificDataType = SpecificDOPData.NormalDOP
        dop.specificData = normal_dop

        regular_com_param.dop = dop
        com_param.specificDataType = ComParamSpecificData.RegularComParam
        com_param.specificData = regular_com_param

        com_param_ref.comParam = com_param

        # Create SimpleValue with the address
        simple_value = SimpleValueT()
        simple_value.value = value
        com_param_ref.simpleValue = simple_value

        return com_param_ref

    def _create_protocol(self, name: str) -> ProtocolT:
        """Create a Protocol with a DiagLayer.

        CDA looks up protocols by DiagLayer.shortName, so we create
        a Protocol containing a DiagLayer with the protocol name.

        Args:
        ----
            name: The CDA protocol name (e.g., "UDS_Ethernet_DoIP_DOBT").

        Returns:
        -------
            A ProtocolT instance.

        """
        protocol = ProtocolT()

        # Create DiagLayer for the protocol
        proto_diag_layer = DiagLayerT()
        proto_diag_layer.shortName = name

        protocol.diagLayer = proto_diag_layer

        return protocol

    def _convert_dop(self, ir_dop: IRDOP) -> DOPT:
        """Convert IR DOP to FlatBuffers DOP.

        Args:
        ----
            ir_dop: The IR DOP to convert.

        Returns:
        -------
            FlatBuffers DOPT instance.

        """
        dop = DOPT()
        dop.shortName = ir_dop.short_name
        dop.dopType = DOPType.REGULAR

        # Create NormalDOP as the specific data
        normal_dop = NormalDOPT()

        # Convert diagnostic coded type
        if ir_dop.diag_coded_type:
            normal_dop.diagCodedType = self._convert_diag_coded_type(
                ir_dop.diag_coded_type
            )

        # Convert computation method
        if ir_dop.compu_method:
            normal_dop.compuMethod = self._convert_compu_method(ir_dop.compu_method)

        # Set specific data type and data
        dop.specificDataType = SpecificDOPData.NormalDOP
        dop.specificData = normal_dop

        return dop

    def _convert_diag_coded_type(self, ir_dct: IRDiagCodedType) -> DiagCodedTypeT:
        """Convert IR DiagCodedType to FlatBuffers DiagCodedType.

        Args:
        ----
            ir_dct: The IR diagnostic coded type.

        Returns:
        -------
            FlatBuffers DiagCodedTypeT instance.

        """
        from yaml_to_mdd.fbs_generated.dataformat.DataType import DataType
        from yaml_to_mdd.fbs_generated.dataformat.DiagCodedTypeName import (
            DiagCodedTypeName,
        )
        from yaml_to_mdd.fbs_generated.dataformat.StandardLengthType import (
            StandardLengthTypeT,
        )
        from yaml_to_mdd.ir.types import IRDataType, IRDiagCodedTypeName

        dct = DiagCodedTypeT()

        # Map type name
        type_name_map = {
            IRDiagCodedTypeName.LEADING_LENGTH_INFO_TYPE: (
                DiagCodedTypeName.LEADING_LENGTH_INFO_TYPE
            ),
            IRDiagCodedTypeName.MIN_MAX_LENGTH_TYPE: (
                DiagCodedTypeName.MIN_MAX_LENGTH_TYPE
            ),
            IRDiagCodedTypeName.PARAM_LENGTH_INFO_TYPE: (
                DiagCodedTypeName.PARAM_LENGTH_INFO_TYPE
            ),
            IRDiagCodedTypeName.STANDARD_LENGTH_TYPE: (
                DiagCodedTypeName.STANDARD_LENGTH_TYPE
            ),
        }
        dct.type = type_name_map.get(
            ir_dct.type_name, DiagCodedTypeName.STANDARD_LENGTH_TYPE
        )

        # Map base data type
        data_type_map = {
            IRDataType.A_INT_32: DataType.A_INT_32,
            IRDataType.A_UINT_32: DataType.A_UINT_32,
            IRDataType.A_FLOAT_32: DataType.A_FLOAT_32,
            IRDataType.A_ASCIISTRING: DataType.A_ASCIISTRING,
            IRDataType.A_UTF_8_STRING: DataType.A_UTF_8_STRING,
            IRDataType.A_UNICODE_2_STRING: DataType.A_UNICODE_2_STRING,
            IRDataType.A_BYTEFIELD: DataType.A_BYTEFIELD,
            IRDataType.A_FLOAT_64: DataType.A_FLOAT_64,
        }
        dct.baseDataType = data_type_map.get(
            ir_dct.base_data_type, DataType.A_BYTEFIELD
        )

        dct.isHighLowByteOrder = ir_dct.is_high_low_byte_order

        # Create specific data (StandardLengthType for most cases)
        if ir_dct.type_name == IRDiagCodedTypeName.STANDARD_LENGTH_TYPE:
            std_type = StandardLengthTypeT()
            std_type.bitLength = ir_dct.bit_length
            dct.specificData = std_type

        return dct

    def _convert_compu_method(self, ir_cm: IRCompuMethod) -> CompuMethodT:
        """Convert IR CompuMethod to FlatBuffers CompuMethod.

        Args:
        ----
            ir_cm: The IR computation method.

        Returns:
        -------
            FlatBuffers CompuMethodT instance.

        """
        from yaml_to_mdd.fbs_generated.dataformat.CompuCategory import CompuCategory
        from yaml_to_mdd.ir.types import IRCompuCategory

        cm = CompuMethodT()

        # Map category
        category_map = {
            IRCompuCategory.IDENTICAL: CompuCategory.IDENTICAL,
            IRCompuCategory.LINEAR: CompuCategory.LINEAR,
            IRCompuCategory.SCALE_LINEAR: CompuCategory.SCALE_LINEAR,
            IRCompuCategory.TEXT_TABLE: CompuCategory.TEXT_TABLE,
            IRCompuCategory.TAB_INTP: CompuCategory.TAB_INTP,
            IRCompuCategory.RAT_FUNC: CompuCategory.RAT_FUNC,
            IRCompuCategory.SCALE_RAT_FUNC: CompuCategory.SCALE_RAT_FUNC,
        }
        cm.category = category_map.get(ir_cm.category, CompuCategory.IDENTICAL)

        # Convert scales
        if ir_cm.scales:
            internal_to_phys = CompuInternalToPhysT()
            internal_to_phys.compuScales = []

            for ir_scale in ir_cm.scales:
                scale = self._convert_compu_scale(ir_scale)
                internal_to_phys.compuScales.append(scale)

            cm.internalToPhys = internal_to_phys

        return cm

    def _convert_compu_scale(self, ir_scale: IRCompuScale) -> CompuScaleT:
        """Convert IR CompuScale to FlatBuffers CompuScale.

        Args:
        ----
            ir_scale: The IR computation scale.

        Returns:
        -------
            FlatBuffers CompuScaleT instance.

        """
        from yaml_to_mdd.fbs_generated.dataformat.IntervalType import IntervalType
        from yaml_to_mdd.fbs_generated.dataformat.Limit import LimitT
        from yaml_to_mdd.fbs_generated.dataformat.Text import TextT

        scale = CompuScaleT()

        # Text table entry
        if ir_scale.text_value is not None:
            values = CompuValuesT()
            values.vt = ir_scale.text_value
            scale.consts = values

        # Limits
        if ir_scale.lower_limit is not None:
            scale.lowerLimit = LimitT()
            scale.lowerLimit.value = str(ir_scale.lower_limit.value)
            scale.lowerLimit.intervalType = IntervalType.CLOSED

        if ir_scale.upper_limit is not None:
            scale.upperLimit = LimitT()
            scale.upperLimit.value = str(ir_scale.upper_limit.value)
            scale.upperLimit.intervalType = IntervalType.CLOSED

        # Short label
        if ir_scale.short_label is not None:
            scale.shortLabel = TextT()
            scale.shortLabel.value = ir_scale.short_label

        return scale

    def _convert_service(self, ir_service: IRDiagService) -> DiagServiceT:
        """Convert IR DiagService to FlatBuffers DiagService.

        Args:
        ----
            ir_service: The IR diagnostic service.

        Returns:
        -------
            FlatBuffers DiagServiceT instance.

        """
        service = DiagServiceT()

        # Create DiagComm for metadata
        diag_comm = DiagCommT()
        diag_comm.shortName = ir_service.short_name
        service.diagComm = diag_comm

        # Convert request (pass service_id for CodedConst generation)
        if ir_service.request:
            service.request = self._convert_request(
                ir_service.request, ir_service.service_id
            )

        # Convert positive response(s)
        if ir_service.positive_response:
            service.posResponses = [
                self._convert_response(
                    ir_service.positive_response, ir_service.service_id
                )
            ]

        # Convert negative response(s)
        if ir_service.negative_response:
            service.negResponses = [
                self._convert_response(
                    ir_service.negative_response, ir_service.service_id
                )
            ]

        return service

    def _create_service_id_param(self, service_id: int) -> ParamT:
        """Create a CodedConst parameter for the UDS Service ID.

        CDA's request_id() expects a CodedConst param at byte_position=0
        with DiagCodedType.base_data_type = A_UINT_32 and StandardLengthType.

        Args:
        ----
            service_id: The UDS service ID (0x00-0xFF).

        Returns:
        -------
            FlatBuffers ParamT with CodedConst specific data.

        """
        param = ParamT()
        param.shortName = "ServiceID"
        param.bytePosition = 0
        param.bitPosition = 0
        param.semantic = "SERVICE_ID"

        # Create StandardLengthType (8 bits = 1 byte)
        std_len = StandardLengthTypeT()
        std_len.bitLength = 8
        std_len.condensed = False

        # Create DiagCodedType
        diag_coded_type = DiagCodedTypeT()
        diag_coded_type.baseDataType = DataType.A_UINT_32
        diag_coded_type.specificDataType = SpecificDataType.StandardLengthType
        diag_coded_type.specificData = std_len

        # Create CodedConst with the service ID value
        coded_const = CodedConstT()
        coded_const.codedValue = str(service_id)  # CDA parses string to u16
        coded_const.diagCodedType = diag_coded_type

        param.specificDataType = ParamSpecificData.CodedConst
        param.specificData = coded_const

        return param

    def _convert_request(self, ir_request: IRRequest, service_id: int) -> RequestT:
        """Convert IR Request to FlatBuffers Request.

        Args:
        ----
            ir_request: The IR request.
            service_id: The UDS service ID for CodedConst generation.

        Returns:
        -------
            FlatBuffers RequestT instance.

        """
        request = RequestT()
        request.params = []

        # First param MUST be ServiceID CodedConst at byte_position=0
        # CDA's request_id() looks for this to identify the service
        sid_param = self._create_service_id_param(service_id)
        request.params.append(sid_param)

        # Convert remaining parameters (skip any existing SERVICE_ID param)
        if ir_request.params:
            for ir_param in ir_request.params:
                # Skip if already a ServiceID param (we created one above)
                if ir_param.semantic == "SERVICE_ID":
                    continue
                param = self._convert_param(ir_param)
                # Adjust byte position to account for ServiceID at position 0
                if param.bytePosition is not None and param.bytePosition == 0:
                    param.bytePosition = 1
                request.params.append(param)

        return request

    def _convert_response(
        self, ir_response: IRResponse, service_id: int | None = None
    ) -> ResponseT:
        """Convert IR Response to FlatBuffers Response.

        Args:
        ----
            ir_response: The IR response.
            service_id: The UDS service ID for CodedConst generation. If provided,
                        a ServiceID CodedConst with value (service_id + 0x40) will
                        be created as the first parameter (positive response format).

        Returns:
        -------
            FlatBuffers ResponseT instance.

        """
        response = ResponseT()
        response.params = []

        # Create ServiceID CodedConst if service_id provided (response SID = request SID + 0x40)
        if service_id is not None:
            sid_param = self._create_service_id_param(service_id + 0x40)
            response.params.append(sid_param)

        # Convert remaining parameters (skip any existing SERVICE_ID param)
        if ir_response.params:
            for ir_param in ir_response.params:
                # Skip if already a ServiceID param (we created one above)
                if ir_param.semantic == "SERVICE_ID" and service_id is not None:
                    continue
                param = self._convert_param(ir_param)
                response.params.append(param)

        return response

        return response

    def _convert_param(self, ir_param: IRParam) -> ParamT:
        """Convert IR Param to FlatBuffers Param.

        Args:
        ----
            ir_param: The IR parameter.

        Returns:
        -------
            FlatBuffers ParamT instance.

        """
        param = ParamT()
        param.shortName = ir_param.short_name
        param.bytePosition = ir_param.byte_position

        if ir_param.bit_position is not None:
            param.bitPosition = ir_param.bit_position

        if ir_param.semantic:
            param.semantic = ir_param.semantic

        # If coded_value is set, create CodedConst
        if ir_param.coded_value is not None:
            std_len = StandardLengthTypeT()
            std_len.bitLength = ir_param.bit_length

            diag_coded_type = DiagCodedTypeT()
            diag_coded_type.baseDataType = DataType.A_UINT_32
            diag_coded_type.specificDataType = SpecificDataType.StandardLengthType
            diag_coded_type.specificData = std_len

            coded_const = CodedConstT()
            coded_const.codedValue = str(ir_param.coded_value)
            coded_const.diagCodedType = diag_coded_type

            param.specificDataType = ParamSpecificData.CodedConst
            param.specificData = coded_const
        # Otherwise create Value as specific data with DOP reference
        elif ir_param.dop_ref and ir_param.dop_ref in self._dop_cache:
            value = ValueT()
            # Embed the DOP directly
            value.dop = self._dop_cache[ir_param.dop_ref]
            param.specificDataType = ParamSpecificData.Value
            param.specificData = value

        return param
