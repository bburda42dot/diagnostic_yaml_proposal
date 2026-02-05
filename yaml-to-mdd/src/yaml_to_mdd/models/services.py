"""Models for the services section of diagnostic description."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from yaml_to_mdd.models.common import HexInt8, HexInt16, HexInt32, HexInt64

# Forward reference for AudienceSet to avoid circular imports
AudienceSetType = dict[str, Any] | None


class AddressingMode(str, Enum):
    """Addressing mode for UDS services."""

    PHYSICAL = "physical"
    FUNCTIONAL = "functional"
    BOTH = "both"


class StateEffect(BaseModel):
    """State effect definition per schema.json.

    Describes how a service call modifies ECU state.

    Example:
    -------
        state_effects:
          on_success:
            session: from_request
            security: none
            authentication_role: none

    """

    model_config = ConfigDict(extra="forbid")

    session: Annotated[
        str | None,
        Field(
            default=None,
            description="Session transition: 'unchanged', 'from_request', or explicit session name",
        ),
    ]
    security: Annotated[
        str | None,
        Field(
            default=None,
            description="Security transition: 'unchanged'/'from_request'/'none'/level",
        ),
    ]
    authentication_role: Annotated[
        str | None,
        Field(
            default=None,
            description="Auth role transition: 'unchanged'/'from_request'/'none'/role",
        ),
    ]


class StateEffects(BaseModel):
    """Collection of state effects for different outcomes."""

    model_config = ConfigDict(extra="forbid")

    on_success: Annotated[
        StateEffect | None,
        Field(default=None, description="Effect on successful execution"),
    ]
    on_unlock: Annotated[
        StateEffect | None,
        Field(default=None, description="Effect when security is unlocked"),
    ]
    on_authenticate: Annotated[
        StateEffect | None,
        Field(default=None, description="Effect when authenticated"),
    ]
    on_deauthenticate: Annotated[
        StateEffect | None,
        Field(default=None, description="Effect when deauthenticated"),
    ]
    # ecuReset-specific state effects
    hardReset: Annotated[
        StateEffect | None,
        Field(default=None, description="Effect on hard reset"),
    ]
    keyOffOnReset: Annotated[
        StateEffect | None,
        Field(default=None, description="Effect on key off/on reset"),
    ]
    softReset: Annotated[
        StateEffect | None,
        Field(default=None, description="Effect on soft reset"),
    ]


class ServiceRequestLayout(BaseModel):
    """Custom request parameter layout for a service.

    Allows overriding the default UDS request structure.
    """

    model_config = ConfigDict(extra="allow")  # Allow complex schema fields

    use_uds_defaults: Annotated[
        bool | None,
        Field(
            default=None,
            description="If true, use standard UDS parameter layout",
        ),
    ]
    subfunction_position: Annotated[
        int | None,
        Field(
            default=None,
            ge=1,
            description="Byte position of subfunction (1-indexed, after SID)",
        ),
    ]
    subfunction_bit_length: Annotated[
        int | None,
        Field(
            default=None,
            ge=1,
            le=8,
            description="Bit length for subfunction",
        ),
    ]
    parameters: Annotated[
        list[dict[str, Any]] | None,
        Field(
            default=None,
            description="List of parameter definitions",
        ),
    ]


class ResponseOutput(BaseModel):
    """Response output parameter structure for response_param_match.

    Example:
    -------
        response_outputs:
          hwInfo:
            name: "hwInfo"
            param_id: "HW_INFO"
            type: ascii
            children: [...]

    """

    model_config = ConfigDict(extra="forbid")

    name: Annotated[
        str | None,
        Field(default=None, description="Parameter name"),
    ]
    param_id: Annotated[
        str | None,
        Field(default=None, description="Stable identifier for this parameter"),
    ]
    short_name: Annotated[
        str | None,
        Field(default=None, description="Short name override for export formats"),
    ]
    type: Annotated[
        str | dict[str, Any] | None,
        Field(default=None, description="Type reference or inline type definition"),
    ]
    children: Annotated[
        list[ResponseOutput] | None,
        Field(
            default=None, description="Nested parameters (for struct-like responses)"
        ),
    ]


class MemoryRegion(BaseModel):
    """Memory region definition for memory access services."""

    model_config = ConfigDict(extra="forbid")

    name: Annotated[
        str,
        Field(description="Region name"),
    ]
    start: Annotated[
        HexInt32 | HexInt64,
        Field(description="Start address"),
    ]
    end: Annotated[
        HexInt32 | HexInt64,
        Field(description="End address"),
    ]
    access: Annotated[
        str,
        Field(description="Access pattern reference"),
    ]


class BaseServiceConfig(BaseModel):
    """Base configuration shared by all UDS services."""

    model_config = ConfigDict(extra="forbid")

    enabled: Annotated[
        bool,
        Field(description="Whether this service is enabled"),
    ]
    addressing_mode: Annotated[
        AddressingMode | None,
        Field(
            default=None,
            description="Addressing mode (physical, functional, or both)",
        ),
    ]
    request_layout: Annotated[
        ServiceRequestLayout | None,
        Field(
            default=None,
            description="Custom request parameter layout",
        ),
    ]
    audience: Annotated[
        AudienceSetType,
        Field(
            default=None,
            description="Audiences that can use this service",
        ),
    ]


class DiagnosticSessionControlConfig(BaseServiceConfig):
    """Configuration for DiagnosticSessionControl (0x10) service."""

    subfunctions: Annotated[
        dict[str, HexInt8] | list[HexInt8] | None,
        Field(
            default=None,
            description="Session subfunctions (name -> id mapping or list)",
        ),
    ]
    state_effects: Annotated[
        StateEffects | None,
        Field(default=None, description="State machine effects"),
    ]


class EcuResetConfig(BaseServiceConfig):
    """Configuration for ECUReset (0x11) service."""

    subfunctions: Annotated[
        dict[str, HexInt8] | None,
        Field(
            default=None,
            description="Reset type subfunctions",
        ),
    ]
    state_effects: Annotated[
        StateEffects | None,
        Field(default=None, description="State machine effects per reset type"),
    ]


class SecurityAccessConfig(BaseServiceConfig):
    """Configuration for SecurityAccess (0x27) service."""

    subfunctions: Annotated[
        dict[str, HexInt8] | list[HexInt8] | None,
        Field(
            default=None,
            description="Security access subfunctions",
        ),
    ]
    state_effects: Annotated[
        StateEffects | None,
        Field(default=None, description="State machine effects"),
    ]


class CommunicationControlConfig(BaseServiceConfig):
    """Configuration for CommunicationControl (0x28) service."""

    subfunctions: Annotated[
        dict[str, HexInt8] | list[HexInt8] | None,
        Field(default=None, description="Control type subfunctions"),
    ]
    communication_types: Annotated[
        list[HexInt8] | None,
        Field(default=None, description="Communication type values"),
    ]
    nrc_on_fail: Annotated[
        HexInt8 | None,
        Field(default=None, description="NRC on failure"),
    ]


class AuthenticationConfig(BaseServiceConfig):
    """Configuration for Authentication (0x29) service."""

    subfunctions: Annotated[
        dict[str, HexInt8] | list[HexInt8] | None,
        Field(default=None, description="Authentication subfunctions"),
    ]
    state_effects: Annotated[
        StateEffects | None,
        Field(default=None, description="State machine effects"),
    ]


class _TesterPresentConfig(BaseServiceConfig):
    """Configuration for TesterPresent (0x3E) service.

    Note: Named with underscore prefix to avoid pytest collection warning
    (pytest tries to collect classes starting with 'Test').
    """

    pass  # Only needs enabled and addressing_mode from base


# Alias for backwards compatibility and cleaner API
TesterPresentConfig = _TesterPresentConfig


class ControlDTCSettingConfig(BaseServiceConfig):
    """Configuration for ControlDTCSetting (0x85) service."""

    pass  # Only needs enabled and addressing_mode from base


class ResponseOnEventConfig(BaseServiceConfig):
    """Configuration for ResponseOnEvent (0x86) service."""

    subfunctions: Annotated[
        dict[str, HexInt8] | list[HexInt8] | None,
        Field(default=None, description="Event type subfunctions"),
    ]
    max_active_events: Annotated[
        int | None,
        Field(default=None, ge=0, le=255, description="Max concurrent events"),
    ]


class LinkControlConfig(BaseServiceConfig):
    """Configuration for LinkControl (0x87) service."""

    subfunctions: Annotated[
        dict[str, HexInt8] | list[HexInt8] | None,
        Field(default=None, description="Link control subfunctions"),
    ]


class ReadDataByIdentifierConfig(BaseServiceConfig):
    """Configuration for ReadDataByIdentifier (0x22) service."""

    response_outputs: Annotated[
        dict[str, ResponseOutput] | None,
        Field(
            default=None,
            description="Response output parameter structure for response_param_match",
        ),
    ]


class WriteDataByIdentifierConfig(BaseServiceConfig):
    """Configuration for WriteDataByIdentifier (0x2E) service."""

    pass  # DIDs are defined separately in dids section


# ==================== NEW SERVICES per schema.json ====================


class ReadMemoryByAddressConfig(BaseServiceConfig):
    """Configuration for ReadMemoryByAddress (0x23) service."""

    alfid: Annotated[
        HexInt8 | None,
        Field(default=None, description="Address and length format identifier"),
    ]
    max_length: Annotated[
        int | None,
        Field(default=None, ge=0, le=65535, description="Maximum read length"),
    ]
    regions: Annotated[
        list[MemoryRegion] | None,
        Field(default=None, description="Memory regions that can be read"),
    ]


class WriteMemoryByAddressConfig(BaseServiceConfig):
    """Configuration for WriteMemoryByAddress (0x3D) service."""

    alfid: Annotated[
        HexInt8 | None,
        Field(default=None, description="Address and length format identifier"),
    ]
    max_length: Annotated[
        int | None,
        Field(default=None, ge=0, le=65535, description="Maximum write length"),
    ]
    regions: Annotated[
        list[MemoryRegion] | None,
        Field(default=None, description="Memory regions that can be written"),
    ]


class ReadScalingDataByIdentifierConfig(BaseServiceConfig):
    """Configuration for ReadScalingDataByIdentifier (0x24) service."""

    dids: Annotated[
        list[HexInt16] | None,
        Field(default=None, description="DIDs that support scaling data read"),
    ]


class ReadDataByPeriodicIdentifierConfig(BaseServiceConfig):
    """Configuration for ReadDataByPeriodicIdentifier (0x2A) service."""

    subfunctions: Annotated[
        dict[str, HexInt8] | list[HexInt8] | None,
        Field(default=None, description="Periodic read subfunctions"),
    ]
    supported_periods_ms: Annotated[
        list[int] | None,
        Field(default=None, description="Supported periodic intervals in ms"),
    ]
    identifiers: Annotated[
        list[HexInt8] | None,
        Field(default=None, description="Supported periodic identifiers"),
    ]


class DynamicallyDefineDataIdentifierConfig(BaseServiceConfig):
    """Configuration for DynamicallyDefineDataIdentifier (0x2C) service."""

    subfunctions: Annotated[
        dict[str, HexInt8] | list[HexInt8] | None,
        Field(default=None, description="Dynamic DID subfunctions"),
    ]
    max_dynamic_dids: Annotated[
        int | None,
        Field(default=None, ge=0, le=65535, description="Max dynamic DIDs"),
    ]
    allow_by_identifier: Annotated[
        bool | None,
        Field(default=None, description="Allow define by identifier"),
    ]
    allow_by_memory_address: Annotated[
        bool | None,
        Field(default=None, description="Allow define by memory address"),
    ]


class InputOutputControlByIdentifierConfig(BaseServiceConfig):
    """Configuration for InputOutputControlByIdentifier (0x2F) service."""

    control_types: Annotated[
        list[
            Literal[
                "returnControlToECU",
                "resetToDefault",
                "freezeCurrentState",
                "shortTermAdjustment",
            ]
        ]
        | None,
        Field(default=None, description="Supported I/O control types"),
    ]


class RoutineControlConfig(BaseServiceConfig):
    """Configuration for RoutineControl (0x31) service."""

    # Per schema.json: subfunctions is array of strings, not dict
    subfunctions: Annotated[
        list[Literal["startRoutine", "stopRoutine", "requestResults"]] | None,
        Field(
            default=None,
            description="Routine control subfunctions (startRoutine, stopRoutine, requestResults)",
        ),
    ]
    response_outputs: Annotated[
        dict[str, ResponseOutput] | None,
        Field(
            default=None,
            description="Response output parameter structure for response_param_match",
        ),
    ]


class ReadDTCInformationConfig(BaseServiceConfig):
    """Configuration for ReadDTCInformation (0x19) service."""

    subfunctions: Annotated[
        list[HexInt8] | None,
        Field(default=None, description="DTC information subfunctions"),
    ]
    response_outputs: Annotated[
        dict[str, ResponseOutput] | None,
        Field(
            default=None,
            description="Response output parameter structure for response_param_match",
        ),
    ]


class ClearDiagnosticInformationConfig(BaseServiceConfig):
    """Configuration for ClearDiagnosticInformation (0x14) service."""

    pass  # Only needs enabled and addressing_mode from base


class RequestDownloadConfig(BaseServiceConfig):
    """Configuration for RequestDownload (0x34) service."""

    max_number_of_block_length: Annotated[
        int | None,
        Field(default=None, ge=0, description="Max block length"),
    ]
    regions: Annotated[
        list[MemoryRegion] | None,
        Field(default=None, description="Memory regions for download"),
    ]


class RequestUploadConfig(BaseServiceConfig):
    """Configuration for RequestUpload (0x35) service."""

    max_number_of_block_length: Annotated[
        int | None,
        Field(default=None, ge=0, description="Max block length"),
    ]
    regions: Annotated[
        list[MemoryRegion] | None,
        Field(default=None, description="Memory regions for upload"),
    ]


class TransferDataConfig(BaseServiceConfig):
    """Configuration for TransferData (0x36) service."""

    max_block_sequence_counter: Annotated[
        int | None,
        Field(default=None, ge=0, le=255, description="Max block sequence counter"),
    ]


class RequestTransferExitConfig(BaseServiceConfig):
    """Configuration for RequestTransferExit (0x37) service."""

    pass  # Only needs enabled from base


class RequestFileTransferConfig(BaseServiceConfig):
    """Configuration for RequestFileTransfer (0x38) service."""

    subfunctions: Annotated[
        dict[str, HexInt8] | list[HexInt8] | None,
        Field(default=None, description="File transfer subfunctions"),
    ]
    max_file_size: Annotated[
        int | str | None,
        Field(default=None, description="Maximum file size"),
    ]


class SecuredDataTransmissionConfig(BaseServiceConfig):
    """Configuration for SecuredDataTransmission (0x84) service."""

    subfunctions: Annotated[
        dict[str, HexInt8] | list[HexInt8] | None,
        Field(default=None, description="Secured transmission subfunctions"),
    ]


class PositiveResponse(BaseModel):
    """Positive response definition for custom services."""

    model_config = ConfigDict(extra="allow")  # Allow complex schema fields

    sid: Annotated[
        HexInt8 | None,
        Field(default=None, description="Response SID (usually request SID + 0x40)"),
    ]
    parameters: Annotated[
        list[dict[str, Any]] | None,
        Field(default=None, description="Response parameters"),
    ]
    structure: Annotated[
        dict[str, Any] | None,
        Field(
            default=None,
            description="Structured response definition for complex layouts",
        ),
    ]


class NegativeResponse(BaseModel):
    """Negative response definition for custom services."""

    model_config = ConfigDict(extra="allow")  # Allow complex schema fields

    nrc: Annotated[
        HexInt8,
        Field(description="Negative response code"),
    ]
    name: Annotated[
        str | None,
        Field(default=None, description="Human-readable name"),
    ]
    description: Annotated[
        str | None,
        Field(default=None, description="Description of this NRC"),
    ]
    parameters: Annotated[
        list[dict[str, Any]] | None,
        Field(default=None, description="Additional NRC parameters"),
    ]


class CustomServiceDefinition(BaseModel):
    """Definition of a custom/OEM-specific service."""

    model_config = ConfigDict(extra="allow")  # Allow annotations, x-oem, etc.

    # Per schema.json: field is 'sid', not 'service_id'
    sid: Annotated[
        HexInt8,
        Field(description="Service Identifier (SID) for this custom service"),
    ]
    description: Annotated[
        str | None,
        Field(default=None, description="Human-readable description"),
    ]
    addressing_mode: Annotated[
        AddressingMode | None,
        Field(default=None, description="Addressing mode"),
    ]
    request_layout: Annotated[
        ServiceRequestLayout | None,
        Field(default=None, description="Request parameter layout"),
    ]
    positive_response: Annotated[
        PositiveResponse | None,
        Field(default=None, description="Positive response definition"),
    ]
    negative_responses: Annotated[
        list[NegativeResponse] | None,
        Field(default=None, description="Supported negative response codes"),
    ]
    response_outputs: Annotated[
        dict[str, ResponseOutput] | None,
        Field(default=None, description="Response output parameter structure (legacy)"),
    ]
    access: Annotated[
        str | None,
        Field(default=None, description="Access pattern reference"),
    ]
    audience: Annotated[
        AudienceSetType,
        Field(default=None, description="Audience gating"),
    ]
    annotations: Annotated[
        dict[str, Any] | None,
        Field(default=None, description="Custom annotations"),
    ]


class Services(BaseModel):
    """The services section defining UDS service configurations.

    Example:
    -------
        services:
          diagnosticSessionControl:
            enabled: true
            subfunctions:
              default: 0x01
              extended: 0x03
            state_effects:
              on_success:
                session: from_request
          readDataByIdentifier:
            enabled: true

    """

    model_config = ConfigDict(extra="forbid")

    # Session Management (0x10)
    diagnosticSessionControl: Annotated[
        DiagnosticSessionControlConfig | None,
        Field(default=None, alias="diagnosticSessionControl"),
    ]

    # ECU Reset (0x11)
    ecuReset: Annotated[
        EcuResetConfig | None,
        Field(default=None, alias="ecuReset"),
    ]

    # Clear Diagnostic Information (0x14)
    clearDiagnosticInformation: Annotated[
        ClearDiagnosticInformationConfig | None,
        Field(default=None, alias="clearDiagnosticInformation"),
    ]

    # Read DTC Information (0x19)
    readDTCInformation: Annotated[
        ReadDTCInformationConfig | None,
        Field(default=None, alias="readDTCInformation"),
    ]

    # Read Data By Identifier (0x22)
    readDataByIdentifier: Annotated[
        ReadDataByIdentifierConfig | None,
        Field(default=None, alias="readDataByIdentifier"),
    ]

    # Read Memory By Address (0x23) - NEW
    readMemoryByAddress: Annotated[
        ReadMemoryByAddressConfig | None,
        Field(default=None, alias="readMemoryByAddress"),
    ]

    # Read Scaling Data By Identifier (0x24) - NEW
    readScalingDataByIdentifier: Annotated[
        ReadScalingDataByIdentifierConfig | None,
        Field(default=None, alias="readScalingDataByIdentifier"),
    ]

    # Security Access (0x27)
    securityAccess: Annotated[
        SecurityAccessConfig | None,
        Field(default=None, alias="securityAccess"),
    ]

    # Communication Control (0x28)
    communicationControl: Annotated[
        CommunicationControlConfig | None,
        Field(default=None, alias="communicationControl"),
    ]

    # Authentication (0x29)
    authentication: Annotated[
        AuthenticationConfig | None,
        Field(default=None, alias="authentication"),
    ]

    # Read Data By Periodic Identifier (0x2A) - NEW
    readDataByPeriodicIdentifier: Annotated[
        ReadDataByPeriodicIdentifierConfig | None,
        Field(default=None, alias="readDataByPeriodicIdentifier"),
    ]

    # Dynamically Define Data Identifier (0x2C) - NEW
    dynamicallyDefineDataIdentifier: Annotated[
        DynamicallyDefineDataIdentifierConfig | None,
        Field(default=None, alias="dynamicallyDefineDataIdentifier"),
    ]

    # Write Data By Identifier (0x2E)
    writeDataByIdentifier: Annotated[
        WriteDataByIdentifierConfig | None,
        Field(default=None, alias="writeDataByIdentifier"),
    ]

    # Input Output Control By Identifier (0x2F) - NEW
    inputOutputControlByIdentifier: Annotated[
        InputOutputControlByIdentifierConfig | None,
        Field(default=None, alias="inputOutputControlByIdentifier"),
    ]

    # Routine Control (0x31)
    routineControl: Annotated[
        RoutineControlConfig | None,
        Field(default=None, alias="routineControl"),
    ]

    # Request Download (0x34) - NEW
    requestDownload: Annotated[
        RequestDownloadConfig | None,
        Field(default=None, alias="requestDownload"),
    ]

    # Request Upload (0x35) - NEW
    requestUpload: Annotated[
        RequestUploadConfig | None,
        Field(default=None, alias="requestUpload"),
    ]

    # Transfer Data (0x36) - NEW
    transferData: Annotated[
        TransferDataConfig | None,
        Field(default=None, alias="transferData"),
    ]

    # Request Transfer Exit (0x37) - NEW
    requestTransferExit: Annotated[
        RequestTransferExitConfig | None,
        Field(default=None, alias="requestTransferExit"),
    ]

    # Request File Transfer (0x38) - NEW
    requestFileTransfer: Annotated[
        RequestFileTransferConfig | None,
        Field(default=None, alias="requestFileTransfer"),
    ]

    # Write Memory By Address (0x3D) - NEW
    writeMemoryByAddress: Annotated[
        WriteMemoryByAddressConfig | None,
        Field(default=None, alias="writeMemoryByAddress"),
    ]

    # Tester Present (0x3E)
    testerPresent: Annotated[
        TesterPresentConfig | None,
        Field(default=None, alias="testerPresent"),
    ]

    # Secured Data Transmission (0x84) - NEW
    securedDataTransmission: Annotated[
        SecuredDataTransmissionConfig | None,
        Field(default=None, alias="securedDataTransmission"),
    ]

    # Control DTC Setting (0x85)
    controlDTCSetting: Annotated[
        ControlDTCSettingConfig | None,
        Field(default=None, alias="controlDTCSetting"),
    ]

    # Response On Event (0x86)
    responseOnEvent: Annotated[
        ResponseOnEventConfig | None,
        Field(default=None, alias="responseOnEvent"),
    ]

    # Link Control (0x87)
    linkControl: Annotated[
        LinkControlConfig | None,
        Field(default=None, alias="linkControl"),
    ]

    # Custom OEM Services - RENAMED from custom_services to custom
    custom: Annotated[
        dict[str, CustomServiceDefinition] | None,
        Field(default=None, description="Custom/OEM-specific services"),
    ]
