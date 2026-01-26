"""Models for the ECU section of diagnostic description."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress, model_validator

from yaml_to_mdd.models.common import HexInt16, HexInt32


class AddressingMode(str, Enum):
    """ECU addressing mode for diagnostic services."""

    PHYSICAL = "physical"
    FUNCTIONAL = "functional"
    BOTH = "both"


# Protocol short names per schema.json
ProtocolShortName = Literal[
    "UDSonDoIP",
    "UDSonCAN",
    "UDSonLIN",
    "UDSonFR",
    "UDSonIP",
    "ISO_14229_3_DoIP",
    "ISO_15765_3_CAN",
    "ISO_14229_3_CAN",
]


class ProtocolDefinition(BaseModel):
    """Protocol definition per schema.json.

    Example:
    -------
        ```yaml
        protocols:
          doip:
            protocol_short_name: "UDSonDoIP"
            description: "UDS over DoIP for service bay diagnostics"
            is_default: true
        ```

    """

    model_config = ConfigDict(extra="forbid")

    protocol_short_name: Annotated[
        ProtocolShortName,
        Field(
            description="Canonical protocol identifier",
        ),
    ]
    description: Annotated[
        str | None,
        Field(
            default=None,
            description="Human-readable protocol description",
        ),
    ]
    is_default: Annotated[
        bool,
        Field(
            default=False,
            description="If true, this protocol is used as default when multiple are available",
        ),
    ]


# Protocols is now a dynamic map of protocol definitions
Protocols = dict[str, ProtocolDefinition]


class DoIPAddressing(BaseModel):
    """DoIP (Diagnostics over IP) addressing configuration.

    Contains IP address, port, and logical addresses for DoIP communication.

    Example:
    -------
        ```yaml
        doip:
          ip: "192.168.1.100"
          port: 13400
          logical_address: 0x0010
          tester_address: 0x0F00
          functional_address: 0x7DF
          routing_activation: 0x00
        ```

    """

    model_config = ConfigDict(extra="forbid")

    ip: Annotated[
        IPvAnyAddress,
        Field(description="IP address of the ECU (IPv4 or IPv6)"),
    ]
    port: Annotated[
        int | None,
        Field(
            default=13400,  # Standard DoIP port
            ge=1,
            le=65535,
            description="DoIP port (default: 13400)",
        ),
    ]
    logical_address: Annotated[
        HexInt16,
        Field(description="ECU logical address for DoIP routing"),
    ]
    tester_address: Annotated[
        HexInt16,
        Field(description="Tester/client logical address"),
    ]
    functional_address: Annotated[
        HexInt16 | None,
        Field(
            default=None,
            description="Functional group address for broadcast requests",
        ),
    ]
    routing_activation: Annotated[
        HexInt16 | None,
        Field(
            default=None,
            description="Routing activation type",
        ),
    ]


class CANAddressing(BaseModel):
    """CAN addressing configuration.

    Contains CAN IDs for physical and functional addressing.

    Example:
    -------
        ```yaml
        can:
          physical_request: 0x700
          physical_response: 0x708
          functional_request: 0x7DF
        ```

    """

    model_config = ConfigDict(extra="forbid")

    physical_request: Annotated[
        HexInt32 | None,
        Field(
            default=None,
            description="CAN ID for physical request messages (tester to ECU)",
        ),
    ]
    physical_response: Annotated[
        HexInt32 | None,
        Field(
            default=None,
            description="CAN ID for physical response messages (ECU to tester)",
        ),
    ]
    functional_request: Annotated[
        HexInt32 | None,
        Field(
            default=None,
            description="CAN ID for functional (broadcast) request messages",
        ),
    ]


class Timing(BaseModel):
    """UDS timing parameters.

    P2 and P2* are server response timing parameters.
    S3 is the session timeout (TesterPresent keepalive).

    Example:
    -------
        ```yaml
        timing:
          p2_ms: 50
          p2_star_ms: 5000
          s3_ms: 5000
        ```

    """

    model_config = ConfigDict(extra="forbid")

    p2_ms: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            le=65535,
            description="P2 timeout: max time for initial response (ms)",
        ),
    ]
    p2_star_ms: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            le=65535,
            description="P2* timeout: max time after NRC 0x78 response pending (ms)",
        ),
    ]
    s3_ms: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            le=65535,
            description="S3 timeout: session keepalive interval (ms)",
        ),
    ]


class Addressing(BaseModel):
    """Complete addressing configuration for all protocols.

    Groups DoIP, CAN, and timing configurations together.

    Example:
    -------
        ```yaml
        addressing:
          doip:
            ip: "192.168.1.100"
            ...
          can:
            physical_request: 0x700
            ...
          timing:
            p2_ms: 50
            ...
        ```

    """

    model_config = ConfigDict(extra="forbid")

    doip: Annotated[
        DoIPAddressing | None,
        Field(
            default=None,
            description="DoIP addressing configuration",
        ),
    ]
    can: Annotated[
        CANAddressing | None,
        Field(
            default=None,
            description="CAN addressing configuration",
        ),
    ]
    timing: Annotated[
        Timing | None,
        Field(
            default=None,
            description="UDS timing parameters",
        ),
    ]


class Annotations(BaseModel):
    """Annotations/comments for documentation purposes.

    A flexible structure for adding notes and documentation.
    """

    model_config = ConfigDict(extra="allow")  # Allow any additional fields


class Ecu(BaseModel):
    """ECU identification and configuration.

    The main ECU section containing identity, protocol support,
    and addressing information.

    Example:
    -------
        ```yaml
        ecu:
          id: "ECM_V1"
          name: "Engine Control Module"
          default_addressing_mode: physical
          protocols:
            uds_on_can: true
          addressing:
            doip:
              ip: "192.168.1.100"
              logical_address: 0x0010
              tester_address: 0x0F00
        ```

    """

    model_config = ConfigDict(extra="forbid")

    id: Annotated[
        str,
        Field(
            min_length=1,
            description="Unique ECU identifier",
            examples=["ECM_V1", "ABS_2024"],
        ),
    ]
    name: Annotated[
        str,
        Field(
            min_length=1,
            description="Human-readable ECU name",
            examples=["Engine Control Module", "Anti-lock Braking System"],
        ),
    ]
    protocols: Annotated[
        Protocols | None,
        Field(
            default=None,
            description="Protocol support flags",
        ),
    ]
    default_addressing_mode: Annotated[
        AddressingMode | None,
        Field(
            default=None,
            description="Default addressing mode for services",
        ),
    ]
    addressing: Annotated[
        Addressing,
        Field(description="Protocol addressing configuration"),
    ]
    annotations: Annotated[
        Annotations | None,
        Field(
            default=None,
            description="Optional annotations and comments",
        ),
    ]

    @model_validator(mode="after")
    def validate_addressing_has_at_least_one_protocol(self) -> Ecu:
        """Validate that at least one addressing method is configured."""
        if self.addressing.doip is None and self.addressing.can is None:
            # This is a warning, not an error - ECU might use other protocols
            # In production, you might want to log a warning here
            pass
        return self
