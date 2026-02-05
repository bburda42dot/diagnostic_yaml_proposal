"""Intermediate Representation (IR) models for YAML to MDD conversion.

The IR serves as an intermediate format between Pydantic YAML models
and FlatBuffers output:

1. Flattens nested structures where appropriate
2. Resolves type references to concrete types
3. Matches the FlatBuffers schema structure more closely
4. Uses dataclasses for simple, immutable data structures
"""

from yaml_to_mdd.ir.database import (
    IRDTC,
    IRDatabase,
    IRDataBlock,
    IRExtendedDataRecord,
    IRMemoryRegion,
    IRSnapshotDataItem,
    IRSnapshotRecord,
)
from yaml_to_mdd.ir.services import (
    IRDiagService,
    IRParam,
    IRParamType,
    IRRequest,
    IRResponse,
    IRServiceType,
)
from yaml_to_mdd.ir.types import (
    IRDOP,
    IRCompuCategory,
    IRCompuMethod,
    IRCompuScale,
    IRDataType,
    IRDiagCodedType,
    IRDiagCodedTypeName,
    IRLimit,
)

__all__ = [
    # Types
    "IRDataType",
    "IRCompuCategory",
    "IRCompuMethod",
    "IRCompuScale",
    "IRDiagCodedType",
    "IRDiagCodedTypeName",
    "IRDOP",
    "IRLimit",
    # Services
    "IRParam",
    "IRParamType",
    "IRRequest",
    "IRResponse",
    "IRDiagService",
    "IRServiceType",
    # Database
    "IRDatabase",
    # Memory
    "IRMemoryRegion",
    "IRDataBlock",
    # DTCs
    "IRDTC",
    "IRSnapshotRecord",
    "IRSnapshotDataItem",
    "IRExtendedDataRecord",
]
