"""Manual Builder API for FlatBuffers - skip default values.

The generated Object API's Pack() method writes all scalar fields, including
those with default values (0, False, None). This causes significant size bloat.

This module provides patched Pack() methods that only call AddX() for fields
with non-default values, matching the behavior of the Kotlin/Java reference
implementation (odx-converter).

Apply patches by calling apply_manual_builder_patches() before serialization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import flatbuffers

if TYPE_CHECKING:
    from yaml_to_mdd.fbs_generated.dataformat.CodedConst import CodedConstT
    from yaml_to_mdd.fbs_generated.dataformat.DiagCodedType import DiagCodedTypeT
    from yaml_to_mdd.fbs_generated.dataformat.DiagService import DiagServiceT
    from yaml_to_mdd.fbs_generated.dataformat.DOP import DOPT
    from yaml_to_mdd.fbs_generated.dataformat.NormalDOP import NormalDOPT
    from yaml_to_mdd.fbs_generated.dataformat.Param import ParamT
    from yaml_to_mdd.fbs_generated.dataformat.Request import RequestT
    from yaml_to_mdd.fbs_generated.dataformat.Response import ResponseT
    from yaml_to_mdd.fbs_generated.dataformat.StandardLengthType import (
        StandardLengthTypeT,
    )


def _param_manual_pack(self: ParamT, builder: flatbuffers.Builder) -> int:
    """Manual Builder API Pack for ParamT - skip default values.

    Only calls AddX() for fields that differ from their default value.
    This matches the Kotlin/Java odx-converter behavior.
    """
    from yaml_to_mdd.fbs_generated.dataformat.Param import (
        ParamAddBitPosition,
        ParamAddBytePosition,
        ParamAddId,
        ParamAddParamType,
        ParamAddPhysicalDefaultValue,
        ParamAddSdgs,
        ParamAddSemantic,
        ParamAddShortName,
        ParamAddSpecificData,
        ParamAddSpecificDataType,
        ParamEnd,
        ParamStart,
    )

    # Pre-create strings and nested objects (must be done before StartObject)
    shortName = None
    if self.shortName is not None:
        shortName = builder.CreateString(self.shortName)

    semantic = None
    if self.semantic is not None:
        semantic = builder.CreateString(self.semantic)

    sdgs = None
    if self.sdgs is not None:
        sdgs = self.sdgs.Pack(builder)

    physicalDefaultValue = None
    if self.physicalDefaultValue is not None:
        physicalDefaultValue = builder.CreateString(self.physicalDefaultValue)

    specificData = None
    if self.specificData is not None:
        specificData = self.specificData.Pack(builder)

    # Start building the table
    ParamStart(builder)

    # Only add fields with non-default values
    if self.id != 0:
        ParamAddId(builder, self.id)

    if self.paramType != 0:
        ParamAddParamType(builder, self.paramType)

    if shortName is not None:
        ParamAddShortName(builder, shortName)

    if semantic is not None:
        ParamAddSemantic(builder, semantic)

    if sdgs is not None:
        ParamAddSdgs(builder, sdgs)

    if physicalDefaultValue is not None:
        ParamAddPhysicalDefaultValue(builder, physicalDefaultValue)

    if self.bytePosition is not None:
        ParamAddBytePosition(builder, self.bytePosition)

    if self.bitPosition is not None:
        ParamAddBitPosition(builder, self.bitPosition)

    if self.specificDataType != 0:
        ParamAddSpecificDataType(builder, self.specificDataType)

    if specificData is not None:
        ParamAddSpecificData(builder, specificData)

    return int(ParamEnd(builder))


def _coded_const_manual_pack(self: CodedConstT, builder: flatbuffers.Builder) -> int:
    """Manual Builder API Pack for CodedConstT - skip default values."""
    from yaml_to_mdd.fbs_generated.dataformat.CodedConst import (
        CodedConstAddCodedValue,
        CodedConstAddDiagCodedType,
        CodedConstEnd,
        CodedConstStart,
    )

    # Pre-create strings and nested objects
    codedValue = None
    if self.codedValue is not None:
        codedValue = builder.CreateString(self.codedValue)

    diagCodedType = None
    if self.diagCodedType is not None:
        # Use pack_cached to share identical DiagCodedType instances
        if hasattr(builder, "pack_cached"):
            diagCodedType = builder.pack_cached(self.diagCodedType)
        else:
            diagCodedType = self.diagCodedType.Pack(builder)

    CodedConstStart(builder)

    if codedValue is not None:
        CodedConstAddCodedValue(builder, codedValue)

    if diagCodedType is not None:
        CodedConstAddDiagCodedType(builder, diagCodedType)

    return int(CodedConstEnd(builder))


def _diag_coded_type_manual_pack(self: DiagCodedTypeT, builder: flatbuffers.Builder) -> int:
    """Manual Builder API Pack for DiagCodedTypeT - skip default values."""
    from yaml_to_mdd.fbs_generated.dataformat.DiagCodedType import (
        DiagCodedTypeAddBaseDataType,
        DiagCodedTypeAddBaseTypeEncoding,
        DiagCodedTypeAddIsHighLowByteOrder,
        DiagCodedTypeAddSpecificData,
        DiagCodedTypeAddSpecificDataType,
        DiagCodedTypeAddType,
        DiagCodedTypeEnd,
        DiagCodedTypeStart,
    )

    # Pre-create strings and nested objects
    baseTypeEncoding = None
    if self.baseTypeEncoding is not None:
        baseTypeEncoding = builder.CreateString(self.baseTypeEncoding)

    specificData = None
    if self.specificData is not None:
        specificData = self.specificData.Pack(builder)

    DiagCodedTypeStart(builder)

    if self.type != 0:
        DiagCodedTypeAddType(builder, self.type)

    if baseTypeEncoding is not None:
        DiagCodedTypeAddBaseTypeEncoding(builder, baseTypeEncoding)

    if self.baseDataType != 0:
        DiagCodedTypeAddBaseDataType(builder, self.baseDataType)

    # Only add isHighLowByteOrder if False (default is True!)
    if not self.isHighLowByteOrder:
        DiagCodedTypeAddIsHighLowByteOrder(builder, self.isHighLowByteOrder)

    if self.specificDataType != 0:
        DiagCodedTypeAddSpecificDataType(builder, self.specificDataType)

    if specificData is not None:
        DiagCodedTypeAddSpecificData(builder, specificData)

    return int(DiagCodedTypeEnd(builder))


def _standard_length_type_manual_pack(
    self: StandardLengthTypeT, builder: flatbuffers.Builder
) -> int:
    """Manual Builder API Pack for StandardLengthTypeT - skip default values."""
    from yaml_to_mdd.fbs_generated.dataformat.StandardLengthType import (
        StandardLengthTypeAddBitLength,
        StandardLengthTypeAddCondensed,
        StandardLengthTypeEnd,
        StandardLengthTypeStart,
    )

    StandardLengthTypeStart(builder)

    if self.bitLength != 0:
        StandardLengthTypeAddBitLength(builder, self.bitLength)

    if self.condensed:  # Only add if True (default is False)
        StandardLengthTypeAddCondensed(builder, self.condensed)

    return int(StandardLengthTypeEnd(builder))


def _diag_service_manual_pack(self: DiagServiceT, builder: flatbuffers.Builder) -> int:
    """Manual Builder API Pack for DiagServiceT - skip default values."""
    from yaml_to_mdd.fbs_generated.dataformat.DiagService import (
        DiagServiceAddDiagComm,
        DiagServiceAddNegResponses,
        DiagServiceAddPosResponses,
        DiagServiceAddRequest,
        DiagServiceEnd,
        DiagServiceStart,
        DiagServiceStartNegResponsesVector,
        DiagServiceStartPosResponsesVector,
    )

    # Pre-create nested objects
    diagComm = None
    if self.diagComm is not None:
        diagComm = self.diagComm.Pack(builder)

    request = None
    if self.request is not None:
        request = self.request.Pack(builder)

    posResponses = None
    if self.posResponses is not None and len(self.posResponses) > 0:
        posResponsesOffsets = [resp.Pack(builder) for resp in self.posResponses]
        DiagServiceStartPosResponsesVector(builder, len(posResponsesOffsets))
        for offset in reversed(posResponsesOffsets):
            builder.PrependUOffsetTRelative(offset)
        posResponses = builder.EndVector()

    negResponses = None
    if self.negResponses is not None and len(self.negResponses) > 0:
        negResponsesOffsets = [resp.Pack(builder) for resp in self.negResponses]
        DiagServiceStartNegResponsesVector(builder, len(negResponsesOffsets))
        for offset in reversed(negResponsesOffsets):
            builder.PrependUOffsetTRelative(offset)
        negResponses = builder.EndVector()

    DiagServiceStart(builder)

    if diagComm is not None:
        DiagServiceAddDiagComm(builder, diagComm)

    if request is not None:
        DiagServiceAddRequest(builder, request)

    if posResponses is not None:
        DiagServiceAddPosResponses(builder, posResponses)

    if negResponses is not None:
        DiagServiceAddNegResponses(builder, negResponses)

    return int(DiagServiceEnd(builder))


def _request_manual_pack(self: RequestT, builder: flatbuffers.Builder) -> int:
    """Manual Builder API Pack for RequestT - skip default values."""
    from yaml_to_mdd.fbs_generated.dataformat.Request import (
        RequestAddParams,
        RequestEnd,
        RequestStart,
        RequestStartParamsVector,
    )

    # Pre-create params vector
    params = None
    if self.params is not None and len(self.params) > 0:
        paramsOffsets = [param.Pack(builder) for param in self.params]
        RequestStartParamsVector(builder, len(paramsOffsets))
        for offset in reversed(paramsOffsets):
            builder.PrependUOffsetTRelative(offset)
        params = builder.EndVector()

    RequestStart(builder)

    if params is not None:
        RequestAddParams(builder, params)

    return int(RequestEnd(builder))


def _response_manual_pack(self: ResponseT, builder: flatbuffers.Builder) -> int:
    """Manual Builder API Pack for ResponseT - skip default values."""
    from yaml_to_mdd.fbs_generated.dataformat.Response import (
        ResponseAddParams,
        ResponseEnd,
        ResponseStart,
        ResponseStartParamsVector,
    )

    # Pre-create params vector
    params = None
    if self.params is not None and len(self.params) > 0:
        paramsOffsets = [param.Pack(builder) for param in self.params]
        ResponseStartParamsVector(builder, len(paramsOffsets))
        for offset in reversed(paramsOffsets):
            builder.PrependUOffsetTRelative(offset)
        params = builder.EndVector()

    ResponseStart(builder)

    if params is not None:
        ResponseAddParams(builder, params)

    return int(ResponseEnd(builder))


def _dop_manual_pack(self: DOPT, builder: flatbuffers.Builder) -> int:
    """Manual Builder API Pack for DOPT - skip default values."""
    from yaml_to_mdd.fbs_generated.dataformat.DOP import (
        DOPAddDopType,
        DOPAddShortName,
        DOPAddSpecificData,
        DOPAddSpecificDataType,
        DOPEnd,
        DOPStart,
    )

    # Pre-create strings and nested objects
    shortName = None
    if self.shortName is not None:
        shortName = builder.CreateString(self.shortName)

    specificData = None
    if self.specificData is not None:
        specificData = self.specificData.Pack(builder)

    DOPStart(builder)

    if shortName is not None:
        DOPAddShortName(builder, shortName)

    if self.dopType != 0:
        DOPAddDopType(builder, self.dopType)

    if self.specificDataType != 0:
        DOPAddSpecificDataType(builder, self.specificDataType)

    if specificData is not None:
        DOPAddSpecificData(builder, specificData)

    return int(DOPEnd(builder))


def _normal_dop_manual_pack(self: NormalDOPT, builder: flatbuffers.Builder) -> int:
    """Manual Builder API Pack for NormalDOPT - skip default values.

    NormalDOP has only optional fields, so the original Pack() is already
    correct. We just delegate to avoid issues.
    """
    from yaml_to_mdd.fbs_generated.dataformat.NormalDOP import (
        NormalDOPAddCompuMethod,
        NormalDOPAddDiagCodedType,
        NormalDOPAddInternalConstr,
        NormalDOPAddPhysConstr,
        NormalDOPAddPhysicalType,
        NormalDOPAddUnitRef,
        NormalDOPEnd,
        NormalDOPStart,
    )

    # Pre-create nested objects
    compuMethod = None
    if self.compuMethod is not None:
        compuMethod = self.compuMethod.Pack(builder)

    diagCodedType = None
    if self.diagCodedType is not None:
        # Use pack_cached to share identical DiagCodedType instances
        if hasattr(builder, "pack_cached"):
            diagCodedType = builder.pack_cached(self.diagCodedType)
        else:
            diagCodedType = self.diagCodedType.Pack(builder)

    physicalType = None
    if self.physicalType is not None:
        physicalType = self.physicalType.Pack(builder)

    internalConstr = None
    if self.internalConstr is not None:
        internalConstr = self.internalConstr.Pack(builder)

    unitRef = None
    if self.unitRef is not None:
        unitRef = self.unitRef.Pack(builder)

    physConstr = None
    if self.physConstr is not None:
        physConstr = self.physConstr.Pack(builder)

    NormalDOPStart(builder)

    if compuMethod is not None:
        NormalDOPAddCompuMethod(builder, compuMethod)

    if diagCodedType is not None:
        NormalDOPAddDiagCodedType(builder, diagCodedType)

    if physicalType is not None:
        NormalDOPAddPhysicalType(builder, physicalType)

    if internalConstr is not None:
        NormalDOPAddInternalConstr(builder, internalConstr)

    if unitRef is not None:
        NormalDOPAddUnitRef(builder, unitRef)

    if physConstr is not None:
        NormalDOPAddPhysConstr(builder, physConstr)

    return int(NormalDOPEnd(builder))


def _diag_comm_manual_pack(self, builder: flatbuffers.Builder) -> int:
    """Manual Builder API Pack for DiagCommT - skip default values."""
    from yaml_to_mdd.fbs_generated.dataformat.DiagComm import (
        DiagCommAddAudience,
        DiagCommAddDiagClassType,
        DiagCommAddFunctClass,
        DiagCommAddIsExecutable,
        DiagCommAddIsFinal,
        DiagCommAddIsMandatory,
        DiagCommAddLongName,
        DiagCommAddPreConditionStateRefs,
        DiagCommAddProtocols,
        DiagCommAddSdgs,
        DiagCommAddSemantic,
        DiagCommAddShortName,
        DiagCommAddStateTransitionRefs,
        DiagCommEnd,
        DiagCommStart,
        DiagCommStartFunctClassVector,
        DiagCommStartPreConditionStateRefsVector,
        DiagCommStartProtocolsVector,
        DiagCommStartStateTransitionRefsVector,
    )

    # Pre-create strings and nested objects
    shortName = None
    if self.shortName is not None:
        shortName = builder.CreateString(self.shortName)

    longName = None
    if self.longName is not None:
        longName = self.longName.Pack(builder)

    semantic = None
    if self.semantic is not None:
        semantic = builder.CreateString(self.semantic)

    functClass = None
    if self.functClass is not None and len(self.functClass) > 0:
        functClassOffsets = [fc.Pack(builder) for fc in self.functClass]
        DiagCommStartFunctClassVector(builder, len(functClassOffsets))
        for offset in reversed(functClassOffsets):
            builder.PrependUOffsetTRelative(offset)
        functClass = builder.EndVector()

    sdgs = None
    if self.sdgs is not None:
        sdgs = self.sdgs.Pack(builder)

    preConditionStateRefs = None
    if self.preConditionStateRefs is not None and len(self.preConditionStateRefs) > 0:
        preConditionStateRefsOffsets = [ref.Pack(builder) for ref in self.preConditionStateRefs]
        DiagCommStartPreConditionStateRefsVector(builder, len(preConditionStateRefsOffsets))
        for offset in reversed(preConditionStateRefsOffsets):
            builder.PrependUOffsetTRelative(offset)
        preConditionStateRefs = builder.EndVector()

    stateTransitionRefs = None
    if self.stateTransitionRefs is not None and len(self.stateTransitionRefs) > 0:
        stateTransitionRefsOffsets = [ref.Pack(builder) for ref in self.stateTransitionRefs]
        DiagCommStartStateTransitionRefsVector(builder, len(stateTransitionRefsOffsets))
        for offset in reversed(stateTransitionRefsOffsets):
            builder.PrependUOffsetTRelative(offset)
        stateTransitionRefs = builder.EndVector()

    protocols = None
    if self.protocols is not None and len(self.protocols) > 0:
        protocolsOffsets = [p.Pack(builder) for p in self.protocols]
        DiagCommStartProtocolsVector(builder, len(protocolsOffsets))
        for offset in reversed(protocolsOffsets):
            builder.PrependUOffsetTRelative(offset)
        protocols = builder.EndVector()

    audience = None
    if self.audience is not None:
        audience = self.audience.Pack(builder)

    DiagCommStart(builder)

    if shortName is not None:
        DiagCommAddShortName(builder, shortName)

    if longName is not None:
        DiagCommAddLongName(builder, longName)

    if semantic is not None:
        DiagCommAddSemantic(builder, semantic)

    if functClass is not None:
        DiagCommAddFunctClass(builder, functClass)

    if sdgs is not None:
        DiagCommAddSdgs(builder, sdgs)

    # Only add diagClassType if non-zero (default is 0)
    if self.diagClassType != 0:
        DiagCommAddDiagClassType(builder, self.diagClassType)

    if preConditionStateRefs is not None:
        DiagCommAddPreConditionStateRefs(builder, preConditionStateRefs)

    if stateTransitionRefs is not None:
        DiagCommAddStateTransitionRefs(builder, stateTransitionRefs)

    if protocols is not None:
        DiagCommAddProtocols(builder, protocols)

    if audience is not None:
        DiagCommAddAudience(builder, audience)

    # Only add isMandatory if True (default is False)
    if self.isMandatory:
        DiagCommAddIsMandatory(builder, self.isMandatory)

    # Only add isExecutable if False (default is True!)
    if not self.isExecutable:
        DiagCommAddIsExecutable(builder, self.isExecutable)

    # Only add isFinal if True (default is False)
    if self.isFinal:
        DiagCommAddIsFinal(builder, self.isFinal)

    return int(DiagCommEnd(builder))


def _matching_request_param_manual_pack(self, builder: flatbuffers.Builder) -> int:
    """Manual Builder API Pack for MatchingRequestParamT - skip default values."""
    from yaml_to_mdd.fbs_generated.dataformat.MatchingRequestParam import (
        MatchingRequestParamAddByteLength,
        MatchingRequestParamAddRequestBytePos,
        MatchingRequestParamEnd,
        MatchingRequestParamStart,
    )

    MatchingRequestParamStart(builder)

    if self.requestBytePos != 0:
        MatchingRequestParamAddRequestBytePos(builder, self.requestBytePos)

    if self.byteLength != 0:
        MatchingRequestParamAddByteLength(builder, self.byteLength)

    return int(MatchingRequestParamEnd(builder))


_patches_applied = False


def _com_param_ref_manual_pack(self, builder: flatbuffers.Builder) -> int:
    """Manual Builder API Pack for ComParamRefT - use pack_cached for Protocol."""
    from yaml_to_mdd.fbs_generated.dataformat.ComParamRef import (
        ComParamRefAddComParam,
        ComParamRefAddComplexValue,
        ComParamRefAddProtocol,
        ComParamRefAddProtStack,
        ComParamRefAddSimpleValue,
        ComParamRefEnd,
        ComParamRefStart,
    )

    # Pre-create nested objects (use pack_cached for shared objects)
    simpleValue = None
    if self.simpleValue is not None:
        simpleValue = self.simpleValue.Pack(builder)

    complexValue = None
    if self.complexValue is not None:
        complexValue = self.complexValue.Pack(builder)

    comParam = None
    if self.comParam is not None:
        comParam = self.comParam.Pack(builder)

    protocol = None
    if self.protocol is not None:
        # Protocol objects are shared across ComParamRefs and parentRefs
        if hasattr(builder, "pack_cached"):
            protocol = builder.pack_cached(self.protocol)
        else:
            protocol = self.protocol.Pack(builder)

    protStack = None
    if self.protStack is not None:
        protStack = self.protStack.Pack(builder)

    ComParamRefStart(builder)

    if simpleValue is not None:
        ComParamRefAddSimpleValue(builder, simpleValue)
    if complexValue is not None:
        ComParamRefAddComplexValue(builder, complexValue)
    if comParam is not None:
        ComParamRefAddComParam(builder, comParam)
    if protocol is not None:
        ComParamRefAddProtocol(builder, protocol)
    if protStack is not None:
        ComParamRefAddProtStack(builder, protStack)

    return int(ComParamRefEnd(builder))


def _parent_ref_manual_pack(self, builder: flatbuffers.Builder) -> int:
    """Manual Builder API Pack for ParentRefT - use pack_cached for ref (Protocol/Variant)."""
    from yaml_to_mdd.fbs_generated.dataformat.ParentRef import (
        ParentRefAddNotInheritedDiagCommShortNames,
        ParentRefAddNotInheritedDopsShortNames,
        ParentRefAddNotInheritedGlobalNegResponsesShortNames,
        ParentRefAddNotInheritedTablesShortNames,
        ParentRefAddNotInheritedVariablesShortNames,
        ParentRefAddRef,
        ParentRefAddRefType,
        ParentRefEnd,
        ParentRefStart,
        ParentRefStartNotInheritedDiagCommShortNamesVector,
        ParentRefStartNotInheritedDopsShortNamesVector,
        ParentRefStartNotInheritedGlobalNegResponsesShortNamesVector,
        ParentRefStartNotInheritedTablesShortNamesVector,
        ParentRefStartNotInheritedVariablesShortNamesVector,
    )

    # Pack the ref object (Protocol or Variant) using pack_cached for sharing
    ref = None
    if self.ref is not None:
        if hasattr(builder, "pack_cached"):
            ref = builder.pack_cached(self.ref)
        else:
            ref = self.ref.Pack(builder)

    # Build string vectors
    notInheritedDiagComm = None
    if (
        self.notInheritedDiagCommShortNames is not None
        and len(self.notInheritedDiagCommShortNames) > 0
    ):
        offsets = [builder.CreateString(s) for s in self.notInheritedDiagCommShortNames]
        ParentRefStartNotInheritedDiagCommShortNamesVector(builder, len(offsets))
        for o in reversed(offsets):
            builder.PrependUOffsetTRelative(o)
        notInheritedDiagComm = builder.EndVector()

    notInheritedVars = None
    if (
        self.notInheritedVariablesShortNames is not None
        and len(self.notInheritedVariablesShortNames) > 0
    ):
        offsets = [builder.CreateString(s) for s in self.notInheritedVariablesShortNames]
        ParentRefStartNotInheritedVariablesShortNamesVector(builder, len(offsets))
        for o in reversed(offsets):
            builder.PrependUOffsetTRelative(o)
        notInheritedVars = builder.EndVector()

    notInheritedDops = None
    if self.notInheritedDopsShortNames is not None and len(self.notInheritedDopsShortNames) > 0:
        offsets = [builder.CreateString(s) for s in self.notInheritedDopsShortNames]
        ParentRefStartNotInheritedDopsShortNamesVector(builder, len(offsets))
        for o in reversed(offsets):
            builder.PrependUOffsetTRelative(o)
        notInheritedDops = builder.EndVector()

    notInheritedTables = None
    if self.notInheritedTablesShortNames is not None and len(self.notInheritedTablesShortNames) > 0:
        offsets = [builder.CreateString(s) for s in self.notInheritedTablesShortNames]
        ParentRefStartNotInheritedTablesShortNamesVector(builder, len(offsets))
        for o in reversed(offsets):
            builder.PrependUOffsetTRelative(o)
        notInheritedTables = builder.EndVector()

    notInheritedNegResp = None
    if (
        self.notInheritedGlobalNegResponsesShortNames is not None
        and len(self.notInheritedGlobalNegResponsesShortNames) > 0
    ):
        offsets = [builder.CreateString(s) for s in self.notInheritedGlobalNegResponsesShortNames]
        ParentRefStartNotInheritedGlobalNegResponsesShortNamesVector(builder, len(offsets))
        for o in reversed(offsets):
            builder.PrependUOffsetTRelative(o)
        notInheritedNegResp = builder.EndVector()

    ParentRefStart(builder)

    if self.refType != 0:
        ParentRefAddRefType(builder, self.refType)

    if ref is not None:
        ParentRefAddRef(builder, ref)

    if notInheritedDiagComm is not None:
        ParentRefAddNotInheritedDiagCommShortNames(builder, notInheritedDiagComm)
    if notInheritedVars is not None:
        ParentRefAddNotInheritedVariablesShortNames(builder, notInheritedVars)
    if notInheritedDops is not None:
        ParentRefAddNotInheritedDopsShortNames(builder, notInheritedDops)
    if notInheritedTables is not None:
        ParentRefAddNotInheritedTablesShortNames(builder, notInheritedTables)
    if notInheritedNegResp is not None:
        ParentRefAddNotInheritedGlobalNegResponsesShortNames(builder, notInheritedNegResp)

    return int(ParentRefEnd(builder))


def apply_manual_builder_patches() -> None:
    """Apply Manual Builder API patches to Object API Pack methods.

    Call this once before any FlatBuffers serialization to enable
    optimized serialization that skips default values.

    This is idempotent - calling it multiple times has no effect.
    """
    global _patches_applied
    if _patches_applied:
        return

    from yaml_to_mdd.fbs_generated.dataformat.CodedConst import CodedConstT
    from yaml_to_mdd.fbs_generated.dataformat.ComParamRef import ComParamRefT
    from yaml_to_mdd.fbs_generated.dataformat.DiagCodedType import DiagCodedTypeT
    from yaml_to_mdd.fbs_generated.dataformat.DiagComm import DiagCommT
    from yaml_to_mdd.fbs_generated.dataformat.DiagService import DiagServiceT
    from yaml_to_mdd.fbs_generated.dataformat.DOP import DOPT
    from yaml_to_mdd.fbs_generated.dataformat.MatchingRequestParam import (
        MatchingRequestParamT,
    )
    from yaml_to_mdd.fbs_generated.dataformat.NormalDOP import NormalDOPT
    from yaml_to_mdd.fbs_generated.dataformat.Param import ParamT
    from yaml_to_mdd.fbs_generated.dataformat.ParentRef import ParentRefT
    from yaml_to_mdd.fbs_generated.dataformat.Request import RequestT
    from yaml_to_mdd.fbs_generated.dataformat.Response import ResponseT
    from yaml_to_mdd.fbs_generated.dataformat.StandardLengthType import (
        StandardLengthTypeT,
    )

    # Patch all the Pack methods
    ParamT.Pack = _param_manual_pack  # type: ignore[method-assign]
    CodedConstT.Pack = _coded_const_manual_pack  # type: ignore[method-assign]
    DiagCodedTypeT.Pack = _diag_coded_type_manual_pack  # type: ignore[method-assign]
    StandardLengthTypeT.Pack = _standard_length_type_manual_pack  # type: ignore[method-assign]
    DiagServiceT.Pack = _diag_service_manual_pack  # type: ignore[method-assign]
    RequestT.Pack = _request_manual_pack  # type: ignore[method-assign]
    ResponseT.Pack = _response_manual_pack  # type: ignore[method-assign]
    DOPT.Pack = _dop_manual_pack  # type: ignore[method-assign]
    NormalDOPT.Pack = _normal_dop_manual_pack  # type: ignore[method-assign]
    DiagCommT.Pack = _diag_comm_manual_pack  # type: ignore[method-assign]
    MatchingRequestParamT.Pack = _matching_request_param_manual_pack  # type: ignore[method-assign]
    ComParamRefT.Pack = _com_param_ref_manual_pack  # type: ignore[method-assign]
    ParentRefT.Pack = _parent_ref_manual_pack  # type: ignore[method-assign]

    _patches_applied = True
