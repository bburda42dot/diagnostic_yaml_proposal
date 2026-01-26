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
    but Python FlatBuffers doesn't support union vectors. We use a custom
    CDAComplexValueT class that manually builds the union vector format.
"""

# mypy: disable-error-code="no-untyped-call"

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import flatbuffers

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
from yaml_to_mdd.fbs_generated.dataformat.SpecificDOPData import SpecificDOPData
from yaml_to_mdd.fbs_generated.dataformat.Value import ValueT
from yaml_to_mdd.fbs_generated.dataformat.Variant import VariantT

if TYPE_CHECKING:
    from yaml_to_mdd.ir.database import IRDatabase
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
        builder.StartVector(4, len(self._entries), 4)  # elemSize=4 (offset), alignment=4
        for offset in reversed(entry_offsets):
            builder.PrependUOffsetTRelative(offset)
        entries_offset = builder.EndVector()

        # Step 4: Create ComplexValue table with both vectors
        builder.StartObject(2)  # 2 fields: entries_type, entries
        builder.PrependUOffsetTRelativeSlot(0, entries_type_offset, 0)  # slot 0 = entries_type
        builder.PrependUOffsetTRelativeSlot(1, entries_offset, 0)  # slot 1 = entries
        return int(builder.EndObject())


@dataclass
class DoIPAddressingConfig:
    """DoIP addressing configuration for FlatBuffers conversion.

    These values are required by CDA to establish DoIP communication.
    """

    logical_gateway_address: int = 0x0E00
    logical_ecu_address: int = 0x0E00
    logical_functional_address: int = 0xE400
    logical_tester_address: int = 0x0E80


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

        # Create protocols first (they are referenced by ComParamRefs)
        for proto_name in protocols:
            cda_name = PROTOCOL_NAME_MAP.get(proto_name, proto_name)
            protocol = self._create_protocol(cda_name)
            self._protocol_cache[cda_name] = protocol

        # Create the DiagLayer for the ECU
        diag_layer = DiagLayerT()
        diag_layer.shortName = db.ecu_name

        # Convert DOPs - build cache for reference lookup
        for dop_name, ir_dop in db.dops.items():
            fbs_dop = self._convert_dop(ir_dop)
            self._dop_cache[dop_name] = fbs_dop

        # Convert services
        services: list[DiagServiceT] = []
        for _service_name, ir_service in db.services.items():
            fbs_service = self._convert_service(ir_service)
            services.append(fbs_service)

        diag_layer.diagServices = services if services else None  # type: ignore[assignment]

        # Add ComParamRefs with protocol references and addressing parameters
        # CDA requires these parameters for DoIP communication
        com_param_refs: list[ComParamRefT] = []
        for cda_name, protocol in self._protocol_cache.items():
            # Create ComParamRefs for DoIP addressing parameters
            if "DoIP" in cda_name:
                com_param_refs.extend(self._create_doip_com_param_refs(protocol, doip_addressing))
            else:
                # For non-DoIP protocols, just add protocol reference
                com_param_ref = ComParamRefT()
                com_param_ref.protocol = protocol
                com_param_refs.append(com_param_ref)

        if com_param_refs:
            diag_layer.comParamRefs = com_param_refs  # type: ignore[assignment]

        # Create Variant containing the DiagLayer
        variant = VariantT()
        variant.diagLayer = diag_layer
        variant.isBaseVariant = True

        # Create EcuData as the root type
        ecu_data = EcuDataT()
        ecu_data.ecuName = db.ecu_name
        ecu_data.version = "1.0"
        ecu_data.variants = [variant]

        # Serialize using Object API
        builder = flatbuffers.Builder(self._builder_size)
        offset = ecu_data.Pack(builder)
        builder.Finish(offset)

        return bytes(builder.Output())

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

        # Tester address (simple)
        refs.append(
            self._create_simple_com_param_ref(
                protocol,
                "CP_DoIPLogicalTesterAddress",
                str(addressing.logical_tester_address),
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

        # Create CDA-compatible ComplexValue with union vector format
        # Using CDAComplexValueT instead of ComplexValueT to generate correct binary
        complex_value = CDAComplexValueT()
        for _, value in entries:
            complex_value.add_simple_value(value)

        # Duck typing: ComParamRefT.Pack() calls complexValue.Pack(builder)
        # CDAComplexValueT has compatible Pack() method
        com_param_ref.complexValue = complex_value  # type: ignore[assignment]

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
            normal_dop.diagCodedType = self._convert_diag_coded_type(ir_dop.diag_coded_type)

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
            IRDiagCodedTypeName.MIN_MAX_LENGTH_TYPE: (DiagCodedTypeName.MIN_MAX_LENGTH_TYPE),
            IRDiagCodedTypeName.PARAM_LENGTH_INFO_TYPE: (DiagCodedTypeName.PARAM_LENGTH_INFO_TYPE),
            IRDiagCodedTypeName.STANDARD_LENGTH_TYPE: (DiagCodedTypeName.STANDARD_LENGTH_TYPE),
        }
        dct.type = type_name_map.get(ir_dct.type_name, DiagCodedTypeName.STANDARD_LENGTH_TYPE)

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
        dct.baseDataType = data_type_map.get(ir_dct.base_data_type, DataType.A_BYTEFIELD)

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

        # Convert request
        if ir_service.request:
            service.request = self._convert_request(ir_service.request)

        # Convert positive response(s)
        if ir_service.positive_response:
            service.posResponses = [self._convert_response(ir_service.positive_response)]

        # Convert negative response(s)
        if ir_service.negative_response:
            service.negResponses = [self._convert_response(ir_service.negative_response)]

        return service

    def _convert_request(self, ir_request: IRRequest) -> RequestT:
        """Convert IR Request to FlatBuffers Request.

        Args:
        ----
            ir_request: The IR request.

        Returns:
        -------
            FlatBuffers RequestT instance.

        """
        request = RequestT()

        # Convert parameters
        if ir_request.params:
            request.params = []
            for ir_param in ir_request.params:
                param = self._convert_param(ir_param)
                request.params.append(param)

        return request

    def _convert_response(self, ir_response: IRResponse) -> ResponseT:
        """Convert IR Response to FlatBuffers Response.

        Args:
        ----
            ir_response: The IR response.

        Returns:
        -------
            FlatBuffers ResponseT instance.

        """
        response = ResponseT()

        # Convert parameters
        if ir_response.params:
            response.params = []
            for ir_param in ir_response.params:
                param = self._convert_param(ir_param)
                response.params.append(param)

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

        # Create Value as specific data with DOP reference
        if ir_param.dop_ref and ir_param.dop_ref in self._dop_cache:
            value = ValueT()
            # Embed the DOP directly
            value.dop = self._dop_cache[ir_param.dop_ref]
            param.specificDataType = ParamSpecificData.Value
            param.specificData = value

        return param
