"""IR models for diagnostic services, requests, and responses.

This module defines the intermediate representation for UDS diagnostic
services. These models map closely to the FlatBuffers schema structure.

Includes:
- IRParamType: Parameter type enum matching FlatBuffers ParamSpecificData union.
- IRParam: Parameter definition with explicit param_type.
- IRRequest/IRResponse: Message containers.
- IRDiagService: Complete UDS service definition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from yaml_to_mdd.ir.types import IRDOP, IRDiagCodedType


class IRParamType(Enum):
    """Parameter types mapping 1:1 to FlatBuffers ParamSpecificData union.

    Values match the FlatBuffers enum values for direct mapping:
    - NONE = 0 (should never be used - indicates missing type)
    - CODED_CONST = 1
    - DYNAMIC = 2
    - MATCHING_REQUEST_PARAM = 3
    - NRC_CONST = 4
    - PHYS_CONST = 5
    - RESERVED = 6
    - VALUE = 7
    - TABLE_ENTRY = 8
    - TABLE_KEY = 9
    - TABLE_STRUCT = 10
    - SYSTEM = 11
    - LENGTH_KEY_REF = 12
    """

    NONE = 0  # Invalid/unset - for error detection
    CODED_CONST = 1
    DYNAMIC = 2
    MATCHING_REQUEST_PARAM = 3
    NRC_CONST = 4
    PHYS_CONST = 5
    RESERVED = 6
    VALUE = 7
    TABLE_ENTRY = 8
    TABLE_KEY = 9
    TABLE_STRUCT = 10
    SYSTEM = 11
    LENGTH_KEY_REF = 12


class IRServiceType(Enum):
    """Types of diagnostic services.

    Defines the expected response behavior for a service.
    """

    REQUEST_ONLY = 0  # No response expected
    POS_RESPONSE = 1  # Single positive response
    POS_RESPONSE_WITH_SUBFUNCTION = 2
    NEG_RESPONSE = 3
    UNKNOWN = 255


@dataclass(frozen=True)
class IRParam:
    """A parameter in a request or response.

    Maps to FlatBuffers Param table. Now with explicit param_type
    for deterministic conversion to FlatBuffers.

    Attributes
    ----------
        short_name: Unique identifier for the parameter.
        byte_position: Position in the message (0-indexed).
        bit_position: For bit-level params, position within byte.
        semantic: Semantic type hint (SERVICE_ID, SUBFUNCTION, DATA, DID).

        param_type: Explicit parameter type (maps to ParamSpecificData union).

        # For CODED_CONST:
        coded_value: Fixed value (e.g., service ID, DID value).
        coded_diag_type: DiagCodedType for wire encoding.
        bit_length: Bit length for coded values (default 8).

        # For MATCHING_REQUEST_PARAM:
        matching_request_byte_pos: Byte position in request to copy from.
        matching_byte_length: Number of bytes to copy from request.

        # For VALUE:
        dop: Full DOP object for encoding/decoding.
        physical_default_value: Default value for the parameter.

        # Deprecated (use dop instead):
        dop_ref: String reference to DOP (kept for backward compat).
        long_name: Human-readable description.

    """

    short_name: str
    byte_position: int = 0
    bit_position: int | None = None
    semantic: str | None = None

    # Explicit param type
    param_type: IRParamType = IRParamType.VALUE

    # For CODED_CONST
    coded_value: int | None = None
    coded_diag_type: IRDiagCodedType | None = None
    bit_length: int = 8

    # For MATCHING_REQUEST_PARAM
    matching_request_byte_pos: int | None = None
    matching_byte_length: int | None = None

    # For VALUE (full DOP object)
    dop: IRDOP | None = None
    physical_default_value: str | None = None

    # Deprecated fields (kept for backward compatibility)
    dop_ref: str | None = None
    long_name: str | None = None


@dataclass(frozen=True)
class IRRequest:
    """A diagnostic service request message.

    Maps to FlatBuffers Request table.

    Attributes
    ----------
        short_name: Unique identifier for the request.
        params: Tuple of parameters in the request.
        constant_prefix: Fixed bytes at start (for validation).

    """

    short_name: str
    params: tuple[IRParam, ...] = field(default_factory=tuple)

    # Request bytes (for validation/documentation)
    constant_prefix: bytes | None = None


@dataclass(frozen=True)
class IRResponse:
    """A diagnostic service response message.

    Maps to FlatBuffers Response table.

    Attributes
    ----------
        short_name: Unique identifier for the response.
        params: Tuple of parameters in the response.
        constant_prefix: Fixed bytes at start (for matching).

    """

    short_name: str
    params: tuple[IRParam, ...] = field(default_factory=tuple)

    # Response prefix for matching
    constant_prefix: bytes | None = None


@dataclass(frozen=True)
class IRDiagService:
    """A diagnostic service definition.

    Maps to FlatBuffers DiagService table. Represents a complete
    UDS diagnostic service with request/response definitions.

    Attributes
    ----------
        short_name: Unique identifier for the service.
        service_id: UDS service ID (0x00-0xFF).
        long_name: Human-readable description.
        subfunction: Optional subfunction ID.
        service_type: Expected response behavior.
        request: Request message definition.
        positive_response: Positive response definition.
        negative_response: Negative response definition.
        required_sessions: Sessions where service is available.
        required_security: Security levels required.
        addressing_mode: physical, functional, or both.
        audience_enabled: Audiences for which enabled.
        audience_disabled: Audiences for which disabled.

    """

    # Required fields first
    short_name: str
    service_id: int  # 0x00-0xFF

    # Optional fields with defaults
    long_name: str | None = None
    subfunction: int | None = None

    # Service type
    service_type: IRServiceType = IRServiceType.POS_RESPONSE

    # Messages
    request: IRRequest | None = None
    positive_response: IRResponse | None = None
    negative_response: IRResponse | None = None

    # Access control
    required_sessions: tuple[str, ...] = field(default_factory=tuple)
    required_security: tuple[str, ...] = field(default_factory=tuple)

    # Addressing
    addressing_mode: str = "physical"  # physical, functional, both

    # Audience (optional)
    audience_enabled: tuple[str, ...] | None = None
    audience_disabled: tuple[str, ...] | None = None

    # Variant ownership - if set, service belongs only to this variant (not base)
    variant_ref: str | None = None

    def __hash__(self) -> int:
        """Hash by service identification for use in sets/dicts."""
        return hash((self.short_name, self.service_id, self.subfunction))
