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

    Maps to FlatBuffers Param table.

    Attributes
    ----------
        short_name: Unique identifier for the parameter.
        long_name: Human-readable description.
        byte_position: Position in the message (0-indexed).
        bit_position: For bit-level params, position within byte.
        dop_ref: Reference to DOP for encoding/decoding.
        semantic: Semantic type hint (SERVICE_ID, SUBFUNCTION, DATA).
        coded_value: Fixed value for CodedConst params (e.g., DID, subfunction).
        bit_length: Bit length for coded values (default 8 for 1-byte values).

    """

    short_name: str
    long_name: str | None = None

    byte_position: int = 0
    bit_position: int | None = None

    # Reference to DOP for encoding/decoding
    dop_ref: str | None = None

    # Semantic type hints
    semantic: str | None = None  # e.g., "SERVICE_ID", "SUBFUNCTION", "DATA"

    # Coded value for CodedConst params (DID, subfunction, etc.)
    coded_value: int | None = None
    bit_length: int = 8  # Default 8 bits (1 byte)


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
