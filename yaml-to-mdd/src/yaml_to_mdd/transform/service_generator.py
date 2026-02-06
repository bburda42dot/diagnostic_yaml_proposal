"""Generate diagnostic services from YAML definitions."""

from __future__ import annotations

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
    IRDataType,
    IRDiagCodedType,
    IRDiagCodedTypeName,
)
from yaml_to_mdd.models.dids import DIDDefinition
from yaml_to_mdd.models.routines import RoutineDefinition


def _create_coded_const_param(
    short_name: str,
    coded_value: int,
    byte_position: int | None = None,
    bit_length: int = 8,
    semantic: str | None = None,
) -> IRParam:
    """Create a CodedConst parameter with proper DiagCodedType.

    Args:
    ----
        short_name: Parameter name (e.g., "SID_RQ", "DID_RQ")
        byte_position: Position in message
        coded_value: The constant value
        bit_length: Bit length (default 8 for 1-byte values)
        semantic: Semantic hint (SERVICE_ID, DID, etc.)

    Returns:
    -------
        IRParam with param_type=CODED_CONST

    """
    diag_type = IRDiagCodedType(
        type_name=IRDiagCodedTypeName.STANDARD_LENGTH_TYPE,
        base_data_type=IRDataType.A_UINT_32,
        bit_length=bit_length,
        is_high_low_byte_order=True,
    )
    return IRParam(
        short_name=short_name,
        byte_position=byte_position,
        semantic=semantic,
        param_type=IRParamType.CODED_CONST,
        coded_value=coded_value,
        coded_diag_type=diag_type,
        bit_length=bit_length,
    )


def _create_matching_request_param(
    short_name: str,
    byte_position: int,
    request_byte_pos: int,
    byte_length: int,
    semantic: str | None = None,
) -> IRParam:
    """Create a MatchingRequestParam that references request data.

    Args:
    ----
        short_name: Parameter name (e.g., "DID_PR")
        byte_position: Position in response
        request_byte_pos: Position in request to copy from
        byte_length: Number of bytes to copy
        semantic: Semantic hint

    Returns:
    -------
        IRParam with param_type=MATCHING_REQUEST_PARAM

    """
    return IRParam(
        short_name=short_name,
        byte_position=byte_position,
        semantic=semantic,
        param_type=IRParamType.MATCHING_REQUEST_PARAM,
        matching_request_byte_pos=request_byte_pos,
        matching_byte_length=byte_length,
    )


def _create_value_param(
    short_name: str,
    byte_position: int,
    dop: IRDOP | None = None,
    dop_ref: str | None = None,
    semantic: str = "DATA",
    physical_default_value: str | None = None,
) -> IRParam:
    """Create a Value parameter with DOP reference.

    Args:
    ----
        short_name: Parameter name
        byte_position: Position in message
        dop: Data Object Property for encoding/decoding
        dop_ref: Legacy DOP reference string (deprecated, use dop)
        semantic: Semantic hint (typically "DATA")
        physical_default_value: Optional default value

    Returns:
    -------
        IRParam with param_type=VALUE

    """
    return IRParam(
        short_name=short_name,
        byte_position=byte_position,
        semantic=semantic,
        param_type=IRParamType.VALUE,
        dop=dop,
        dop_ref=dop_ref,
        physical_default_value=physical_default_value,
    )


def generate_read_did_service(
    did_id: int,
    did_def: DIDDefinition,
    dop_name: str,
    response_dop: IRDOP | None = None,
    sessions: tuple[str, ...] = (),
    security: tuple[str, ...] = (),
) -> IRDiagService:
    """Generate ReadDataByIdentifier service for a DID.

    Service naming follows ODX convention: {name}_Read

    Args:
    ----
        did_id: DID identifier (0x0000-0xFFFF).
        did_def: DID definition from YAML.
        dop_name: Name of the DOP for this DID's data (deprecated, use response_dop).
        response_dop: Full IRDOP for response data.
        sessions: Required sessions.
        security: Required security levels.

    Returns:
    -------
        IRDiagService for reading this DID.

    """
    service_name = f"{did_def.name}_Read"

    # Request: [SID=0x22][DID_HI][DID_LO]
    request = IRRequest(
        short_name=f"RQ_{service_name}",
        params=(
            _create_coded_const_param(
                short_name="SID_RQ",
                coded_value=0x22,
                semantic="SERVICE_ID",
            ),
            _create_coded_const_param(
                short_name="DID_RQ",
                byte_position=1,
                coded_value=did_id,
                bit_length=16,
                semantic="DID",
            ),
        ),
        constant_prefix=bytes([0x22, (did_id >> 8) & 0xFF, did_id & 0xFF]),
    )

    # Response: [SID+0x40=0x62][DID_HI][DID_LO][DATA...]
    response_params: list[IRParam] = [
        _create_coded_const_param(
            short_name="SID_PR",
            coded_value=0x62,
            semantic="SERVICE_ID",
        ),
        _create_matching_request_param(
            short_name="DID_PR",
            byte_position=1,
            request_byte_pos=1,
            byte_length=2,
            semantic="DID",
        ),
    ]

    # Add data param
    response_params.append(
        _create_value_param(
            short_name=did_def.name,
            byte_position=3,
            dop=response_dop,
            dop_ref=dop_name if response_dop is None else None,
            semantic="DATA",
        )
    )

    response = IRResponse(
        short_name=f"PR_{service_name}",
        params=tuple(response_params),
        constant_prefix=bytes([0x62, (did_id >> 8) & 0xFF, did_id & 0xFF]),
    )

    return IRDiagService(
        short_name=service_name,
        service_id=0x22,
        long_name=f"Read {did_def.name}",
        service_type=IRServiceType.POS_RESPONSE,
        request=request,
        positive_response=response,
        required_sessions=sessions,
        required_security=security,
    )


def generate_write_did_service(
    did_id: int,
    did_def: DIDDefinition,
    dop_name: str,
    request_dop: IRDOP | None = None,
    sessions: tuple[str, ...] = (),
    security: tuple[str, ...] = (),
) -> IRDiagService:
    """Generate WriteDataByIdentifier service for a DID.

    Service naming follows ODX convention: {name}_Write

    Args:
    ----
        did_id: DID identifier.
        did_def: DID definition.
        dop_name: DOP name for data (deprecated, use request_dop).
        request_dop: Full IRDOP for request data.
        sessions: Required sessions.
        security: Required security levels.

    Returns:
    -------
        IRDiagService for writing this DID.

    """
    service_name = f"{did_def.name}_Write"

    # Request: [SID=0x2E][DID_HI][DID_LO][DATA...]
    request = IRRequest(
        short_name=f"RQ_{service_name}",
        params=(
            _create_coded_const_param(
                short_name="SID_RQ",
                coded_value=0x2E,
                semantic="SERVICE_ID",
            ),
            _create_coded_const_param(
                short_name="DID_RQ",
                byte_position=1,
                coded_value=did_id,
                bit_length=16,
                semantic="DID",
            ),
            _create_value_param(
                short_name=did_def.name,
                byte_position=3,
                dop=request_dop,
                dop_ref=dop_name if request_dop is None else None,
                semantic="DATA",
            ),
        ),
        constant_prefix=bytes([0x2E, (did_id >> 8) & 0xFF, did_id & 0xFF]),
    )

    # Response: [SID+0x40=0x6E][DID_HI][DID_LO]
    response = IRResponse(
        short_name=f"PR_{service_name}",
        params=(
            _create_coded_const_param(
                short_name="SID_PR",
                coded_value=0x6E,
                semantic="SERVICE_ID",
            ),
            _create_matching_request_param(
                short_name="DID_PR",
                byte_position=1,
                request_byte_pos=1,
                byte_length=2,
                semantic="DID",
            ),
        ),
        constant_prefix=bytes([0x6E, (did_id >> 8) & 0xFF, did_id & 0xFF]),
    )

    return IRDiagService(
        short_name=service_name,
        service_id=0x2E,
        long_name=f"Write {did_def.name}",
        service_type=IRServiceType.POS_RESPONSE,
        request=request,
        positive_response=response,
        required_sessions=sessions,
        required_security=security,
    )


def generate_session_control_services(
    sessions: dict[str, int],
) -> list[IRDiagService]:
    """Generate DiagnosticSessionControl services (0x10).

    Service naming follows ODX convention: {Session}_Start

    Args:
    ----
        sessions: Dict of session_name -> session_id (e.g., {"Default": 0x01}).

    Returns:
    -------
        List of IRDiagService for each session.

    """
    services = []

    for session_name, session_id in sessions.items():
        # Capitalize session name for service naming (default -> Default)
        display_name = session_name.capitalize()
        service_name = f"{display_name}_Start"

        request = IRRequest(
            short_name=f"RQ_{service_name}",
            params=(
                _create_coded_const_param(
                    short_name="SID_RQ",
                    coded_value=0x10,
                    semantic="SERVICE_ID",
                ),
                _create_coded_const_param(
                    short_name="SF_RQ",
                    byte_position=1,
                    coded_value=session_id,
                    semantic="SUBFUNCTION",
                ),
            ),
            constant_prefix=bytes([0x10, session_id]),
        )

        response = IRResponse(
            short_name=f"PR_{service_name}",
            params=(
                _create_coded_const_param(
                    short_name="SID_PR",
                    coded_value=0x50,
                    semantic="SERVICE_ID",
                ),
                _create_matching_request_param(
                    short_name="SF_PR",
                    byte_position=1,
                    request_byte_pos=1,
                    byte_length=1,
                    semantic="SUBFUNCTION",
                ),
            ),
            constant_prefix=bytes([0x50, session_id]),
        )

        service = IRDiagService(
            short_name=service_name,
            service_id=0x10,
            subfunction=session_id,
            long_name=f"Start {display_name} Session",
            service_type=IRServiceType.POS_RESPONSE_WITH_SUBFUNCTION,
            request=request,
            positive_response=response,
        )
        services.append(service)

    return services


def generate_security_access_services(
    security_levels: dict[str, int] | list[int],
    variant_ref: str | None = None,
) -> list[IRDiagService]:
    """Generate SecurityAccess services (0x27).

    For each security level, generates:
    - RequestSeed_Level_{n} (odd subfunction)
    - SendKey_Level_{n} (even subfunction = odd + 1)

    Service naming follows ODX convention.

    Args:
    ----
        security_levels: Dict of level_name -> level_number (e.g., {"level_03": 3})
            or list of level numbers (e.g., [3, 5, 7]).
        variant_ref: Optional variant name if services belong to specific variant.

    Returns:
    -------
        List of IRDiagService pairs (RequestSeed + SendKey) for each level.

    """
    services = []

    # Normalize to dict if list is provided
    if isinstance(security_levels, list):
        security_levels = {f"level_{level:02d}": level for level in security_levels}

    for _level_name, level_num in security_levels.items():
        # RequestSeed service (odd subfunction)
        request_seed_name = f"RequestSeed_Level_{level_num}"
        request_seed_sf = level_num  # e.g., 3, 5, 7

        request = IRRequest(
            short_name=f"RQ_{request_seed_name}",
            params=(
                _create_coded_const_param(
                    short_name="SID_RQ",
                    coded_value=0x27,
                    semantic="SERVICE_ID",
                ),
                _create_coded_const_param(
                    short_name="SF_RQ",
                    byte_position=1,
                    coded_value=request_seed_sf,
                    semantic="SUBFUNCTION",
                ),
            ),
            constant_prefix=bytes([0x27, request_seed_sf]),
        )

        response = IRResponse(
            short_name=f"PR_{request_seed_name}",
            params=(
                _create_coded_const_param(
                    short_name="SID_PR",
                    coded_value=0x67,
                    semantic="SERVICE_ID",
                ),
                _create_matching_request_param(
                    short_name="SF_PR",
                    byte_position=1,
                    request_byte_pos=1,
                    byte_length=1,
                    semantic="SUBFUNCTION",
                ),
            ),
            constant_prefix=bytes([0x67, request_seed_sf]),
        )

        services.append(
            IRDiagService(
                short_name=request_seed_name,
                service_id=0x27,
                subfunction=request_seed_sf,
                long_name=f"Request Seed for Security Level {level_num}",
                service_type=IRServiceType.POS_RESPONSE_WITH_SUBFUNCTION,
                request=request,
                positive_response=response,
                variant_ref=variant_ref,
            )
        )

        # SendKey service (even subfunction = odd + 1)
        send_key_name = f"SendKey_Level_{level_num}"
        send_key_sf = level_num + 1  # e.g., 4, 6, 8

        request_key = IRRequest(
            short_name=f"RQ_{send_key_name}",
            params=(
                _create_coded_const_param(
                    short_name="SID_RQ",
                    coded_value=0x27,
                    semantic="SERVICE_ID",
                ),
                _create_coded_const_param(
                    short_name="SF_RQ",
                    byte_position=1,
                    coded_value=send_key_sf,
                    semantic="SUBFUNCTION",
                ),
                _create_value_param(
                    short_name="SecurityKey",
                    byte_position=2,
                    dop_ref="DOP_EndOfPDU_ByteArray",
                    semantic="DATA",
                ),
            ),
            constant_prefix=bytes([0x27, send_key_sf]),
        )

        response_key = IRResponse(
            short_name=f"PR_{send_key_name}",
            params=(
                _create_coded_const_param(
                    short_name="SID_PR",
                    coded_value=0x67,
                    semantic="SERVICE_ID",
                ),
                _create_matching_request_param(
                    short_name="SF_PR",
                    byte_position=1,
                    request_byte_pos=1,
                    byte_length=1,
                    semantic="SUBFUNCTION",
                ),
            ),
            constant_prefix=bytes([0x67, send_key_sf]),
        )

        # Negative response for failed authentication
        neg_response_key = IRResponse(
            short_name=f"NR_{send_key_name}",
            params=(
                _create_coded_const_param(
                    short_name="SID_NR",
                    coded_value=0x7F,
                    semantic="SERVICE_ID",
                ),
                _create_matching_request_param(
                    short_name="SIDRQ_NR",
                    byte_position=1,
                    request_byte_pos=0,
                    byte_length=1,
                    semantic="SERVICEIDRQ",
                ),
                _create_value_param(
                    short_name="NRC",
                    byte_position=2,
                    dop_ref="DOP_UINT8",
                    semantic="DATA",
                ),
            ),
            constant_prefix=bytes([0x7F, 0x27]),
        )

        services.append(
            IRDiagService(
                short_name=send_key_name,
                service_id=0x27,
                subfunction=send_key_sf,
                long_name=f"Send Key for Security Level {level_num}",
                service_type=IRServiceType.POS_RESPONSE_WITH_SUBFUNCTION,
                request=request_key,
                positive_response=response_key,
                negative_response=neg_response_key,
                variant_ref=variant_ref,
            )
        )

    return services


def generate_ecu_reset_services(
    reset_types: dict[str, int] | None = None,
) -> list[IRDiagService]:
    """Generate ECUReset services (0x11).

    Service naming follows ODX convention: HardReset, SoftReset, etc.

    Args:
    ----
        reset_types: Dict of reset_name -> subfunction (e.g., {"HardReset": 0x01}).
            If None, defaults to HardReset (0x01) and SoftReset (0x03).

    Returns:
    -------
        List of IRDiagService for each reset type.

    """
    if reset_types is None:
        reset_types = {"HardReset": 0x01, "SoftReset": 0x03}

    services = []

    for reset_name, subfunction in reset_types.items():
        request = IRRequest(
            short_name=f"RQ_{reset_name}",
            params=(
                _create_coded_const_param(
                    short_name="SID_RQ",
                    coded_value=0x11,
                    semantic="SERVICE_ID",
                ),
                _create_coded_const_param(
                    short_name="SF_RQ",
                    byte_position=1,
                    coded_value=subfunction,
                    semantic="SUBFUNCTION",
                ),
            ),
            constant_prefix=bytes([0x11, subfunction]),
        )

        response = IRResponse(
            short_name=f"PR_{reset_name}",
            params=(
                _create_coded_const_param(
                    short_name="SID_PR",
                    coded_value=0x51,
                    semantic="SERVICE_ID",
                ),
                _create_matching_request_param(
                    short_name="SF_PR",
                    byte_position=1,
                    request_byte_pos=1,
                    byte_length=1,
                    semantic="SUBFUNCTION",
                ),
            ),
            constant_prefix=bytes([0x51, subfunction]),
        )

        service = IRDiagService(
            short_name=reset_name,
            service_id=0x11,
            subfunction=subfunction,
            long_name=f"ECU {reset_name}",
            service_type=IRServiceType.POS_RESPONSE_WITH_SUBFUNCTION,
            request=request,
            positive_response=response,
        )
        services.append(service)

    return services


def generate_authentication_services(
    subfunctions: dict[str, int] | None = None,
) -> list[IRDiagService]:
    """Generate Authentication services (0x29).

    Service naming follows ODX convention: Authentication_{Name}

    Args:
    ----
        subfunctions: Dict of name -> subfunction (e.g., {"Deauthenticate": 0x00}).
            If None, defaults to Deauthenticate (0x00) and Configuration (0x08).

    Returns:
    -------
        List of IRDiagService for each authentication operation.

    """
    if subfunctions is None:
        subfunctions = {"Deauthenticate": 0x00, "Configuration": 0x08}

    services = []

    for name, subfunction in subfunctions.items():
        service_name = f"Authentication_{name}"

        request = IRRequest(
            short_name=f"RQ_{service_name}",
            params=(
                _create_coded_const_param(
                    short_name="SID_RQ",
                    coded_value=0x29,
                    semantic="SERVICE_ID",
                ),
                _create_coded_const_param(
                    short_name="SF_RQ",
                    byte_position=1,
                    coded_value=subfunction,
                    semantic="SUBFUNCTION",
                ),
            ),
            constant_prefix=bytes([0x29, subfunction]),
        )

        # Response params depend on subfunction
        response_params: list[IRParam] = [
            _create_coded_const_param(
                short_name="SID_PR",
                coded_value=0x69,
                semantic="SERVICE_ID",
            ),
            _create_matching_request_param(
                short_name="SF_PR",
                byte_position=1,
                request_byte_pos=1,
                byte_length=1,
                semantic="SUBFUNCTION",
            ),
        ]

        # Configuration response includes AuthenticationReturnParameter
        if name == "Configuration":
            response_params.append(
                _create_value_param(
                    short_name="AuthenticationReturnParameter",
                    byte_position=2,
                    dop_ref="DOP_AuthReturnParam",
                    semantic="DATA",
                )
            )

        response = IRResponse(
            short_name=f"PR_{service_name}",
            params=tuple(response_params),
            constant_prefix=bytes([0x69, subfunction]),
        )

        service = IRDiagService(
            short_name=service_name,
            service_id=0x29,
            subfunction=subfunction,
            long_name=f"Authentication {name}",
            service_type=IRServiceType.POS_RESPONSE_WITH_SUBFUNCTION,
            request=request,
            positive_response=response,
        )
        services.append(service)

    return services


def generate_communication_control_services(
    control_types: dict[str, int] | None = None,
) -> list[IRDiagService]:
    """Generate CommunicationControl services (0x28).

    Service naming follows ODX convention: {Name}_Control

    Args:
    ----
        control_types: Dict of name -> control_type (e.g., {"EnableRxAndEnableTx": 0x00}).
            If None, defaults to standard control types.

    Returns:
    -------
        List of IRDiagService for each control type.

    """
    if control_types is None:
        control_types = {
            "EnableRxAndEnableTx": 0x00,
            "EnableRxAndDisableTx": 0x01,
            "DisableRxAndEnableTx": 0x02,
            "DisableRxAndDisableTx": 0x03,
            "EnableRxAndDisableTxWithEnhancedAddressInformation": 0x04,
            "EnableRxAndTxWithEnhancedAddressInformation": 0x05,
            "TemporalSync": 0x88,
        }

    services = []

    for name, control_type in control_types.items():
        service_name = f"{name}_Control"

        # Request: [SID=0x28][ControlType][CommunicationType]
        request_params: list[IRParam] = [
            _create_coded_const_param(
                short_name="SID_RQ",
                coded_value=0x28,
                semantic="SERVICE_ID",
            ),
            _create_coded_const_param(
                short_name="SF_RQ",
                byte_position=1,
                coded_value=control_type,
                semantic="SUBFUNCTION",
            ),
            _create_coded_const_param(
                short_name="CommunicationType",
                byte_position=2,
                coded_value=1,  # normalComm
                semantic="DATA",
            ),
        ]

        # TemporalSync has additional parameter
        if name == "TemporalSync":
            request_params.append(
                _create_value_param(
                    short_name="temporalEraId",
                    byte_position=3,
                    dop_ref="DOP_INT32",
                    semantic="DATA",
                )
            )

        request = IRRequest(
            short_name=f"RQ_{service_name}",
            params=tuple(request_params),
            constant_prefix=bytes([0x28, control_type, 0x01]),  # 0x01 = normalComm
        )

        response = IRResponse(
            short_name=f"PR_{service_name}",
            params=(
                _create_coded_const_param(
                    short_name="SID_PR",
                    coded_value=0x68,
                    semantic="SERVICE_ID",
                ),
                _create_matching_request_param(
                    short_name="SF_PR",
                    byte_position=1,
                    request_byte_pos=1,
                    byte_length=1,
                    semantic="SUBFUNCTION",
                ),
            ),
            constant_prefix=bytes([0x68, control_type]),
        )

        service = IRDiagService(
            short_name=service_name,
            service_id=0x28,
            subfunction=control_type,
            long_name=f"Communication Control - {name}",
            service_type=IRServiceType.POS_RESPONSE_WITH_SUBFUNCTION,
            request=request,
            positive_response=response,
        )
        services.append(service)

    return services


def generate_transfer_data_services() -> list[IRDiagService]:
    """Generate Transfer Data services (0x34, 0x36, 0x37).

    Generates:
    - RequestDownload (0x34)
    - TransferData (0x36)
    - TransferExit (0x37)

    Returns
    -------
        List of IRDiagService for transfer operations.

    """
    services = []

    # RequestDownload (0x34)
    request_download_request = IRRequest(
        short_name="RQ_RequestDownload",
        params=(
            _create_coded_const_param(
                short_name="SID_RQ",
                coded_value=0x34,
                semantic="SERVICE_ID",
            ),
            _create_value_param(
                short_name="DataFormatIdentifier",
                byte_position=1,
                dop_ref="DOP_UINT8",
                semantic="DATA",
            ),
            _create_value_param(
                short_name="AddressAndLengthFormatIdentifier",
                byte_position=2,
                dop_ref="DOP_UINT8",
                semantic="DATA",
            ),
            _create_value_param(
                short_name="MemoryAddress",
                byte_position=3,
                dop_ref="DOP_ByteArray",
                semantic="DATA",
            ),
            _create_value_param(
                short_name="MemorySize",
                byte_position=7,  # After 4-byte address
                dop_ref="DOP_ByteArray",
                semantic="DATA",
            ),
        ),
        constant_prefix=bytes([0x34]),
    )

    request_download_response = IRResponse(
        short_name="PR_RequestDownload",
        params=(
            _create_coded_const_param(
                short_name="SID_PR",
                coded_value=0x74,
                semantic="SERVICE_ID",
            ),
            _create_value_param(
                short_name="LengthFormatIdentifier",
                byte_position=1,
                dop_ref="DOP_UINT8",
                semantic="DATA",
            ),
            _create_value_param(
                short_name="MaxNumberOfBlockLength",
                byte_position=2,
                dop_ref="DOP_UINT32",
                semantic="DATA",
            ),
        ),
        constant_prefix=bytes([0x74]),
    )

    services.append(
        IRDiagService(
            short_name="RequestDownload",
            service_id=0x34,
            long_name="Request Download",
            service_type=IRServiceType.POS_RESPONSE,
            request=request_download_request,
            positive_response=request_download_response,
        )
    )

    # TransferData (0x36)
    transfer_data_request = IRRequest(
        short_name="RQ_TransferData",
        params=(
            _create_coded_const_param(
                short_name="SID_RQ",
                coded_value=0x36,
                semantic="SERVICE_ID",
            ),
            _create_value_param(
                short_name="BlockSequenceCounter",
                byte_position=1,
                dop_ref="DOP_UINT8",
                semantic="DATA",
            ),
            _create_value_param(
                short_name="TransferRequestParameterRecord",
                byte_position=2,
                dop_ref="DOP_EndOfPDU_ByteArray",
                semantic="DATA",
            ),
        ),
        constant_prefix=bytes([0x36]),
    )

    transfer_data_response = IRResponse(
        short_name="PR_TransferData",
        params=(
            _create_coded_const_param(
                short_name="SID_PR",
                coded_value=0x76,
                semantic="SERVICE_ID",
            ),
            _create_matching_request_param(
                short_name="BlockSequenceCounter_PR",
                byte_position=1,
                request_byte_pos=1,
                byte_length=1,
                semantic="DATA",
            ),
            _create_value_param(
                short_name="TransferRequestParameterRecord",
                byte_position=2,
                dop_ref="DOP_EndOfPDU_ByteArray",
                semantic="DATA",
            ),
        ),
        constant_prefix=bytes([0x76]),
    )

    services.append(
        IRDiagService(
            short_name="TransferData",
            service_id=0x36,
            long_name="Transfer Data",
            service_type=IRServiceType.POS_RESPONSE,
            request=transfer_data_request,
            positive_response=transfer_data_response,
        )
    )

    # TransferExit (0x37)
    transfer_exit_request = IRRequest(
        short_name="RQ_TransferExit",
        params=(
            _create_coded_const_param(
                short_name="SID_RQ",
                coded_value=0x37,
                semantic="SERVICE_ID",
            ),
        ),
        constant_prefix=bytes([0x37]),
    )

    transfer_exit_response = IRResponse(
        short_name="PR_TransferExit",
        params=(
            _create_coded_const_param(
                short_name="SID_PR",
                coded_value=0x77,
                semantic="SERVICE_ID",
            ),
        ),
        constant_prefix=bytes([0x77]),
    )

    services.append(
        IRDiagService(
            short_name="TransferExit",
            service_id=0x37,
            long_name="Request Transfer Exit",
            service_type=IRServiceType.POS_RESPONSE,
            request=transfer_exit_request,
            positive_response=transfer_exit_response,
        )
    )

    return services


def generate_routine_services(
    routine_id: int,
    routine_def: RoutineDefinition,
    sessions: tuple[str, ...] = (),
    security: tuple[str, ...] = (),
) -> list[IRDiagService]:
    """Generate RoutineControl services for a routine.

    Args:
    ----
        routine_id: Routine identifier.
        routine_def: Routine definition.
        sessions: Required sessions.
        security: Required security levels.

    Returns:
    -------
        List of IRDiagService (one per supported operation).

    """
    services = []

    if routine_def.supports_start():
        services.append(_generate_routine_start(routine_id, routine_def, sessions, security))

    if routine_def.supports_stop():
        services.append(_generate_routine_stop(routine_id, routine_def, sessions, security))

    if routine_def.supports_result():
        services.append(_generate_routine_result(routine_id, routine_def, sessions, security))

    return services


def _generate_routine_start(
    routine_id: int,
    routine_def: RoutineDefinition,
    sessions: tuple[str, ...],
    security: tuple[str, ...],
) -> IRDiagService:
    """Generate startRoutine service."""
    service_name = f"Start_{routine_def.name}"

    # Request: [SID=0x31][SF=0x01][RID_HI][RID_LO][params...]
    request_params: list[IRParam] = [
        _create_coded_const_param(
            short_name="SID_RQ",
            coded_value=0x31,
            semantic="SERVICE_ID",
        ),
        _create_coded_const_param(
            short_name="SF_RQ",
            byte_position=1,
            coded_value=0x01,
            semantic="SUBFUNCTION",
        ),
        _create_coded_const_param(
            short_name="RID_RQ",
            byte_position=2,
            coded_value=routine_id,
            bit_length=16,
            semantic="DATA",
        ),
    ]

    request = IRRequest(
        short_name=f"{service_name}_Request",
        params=tuple(request_params),
        constant_prefix=bytes([0x31, 0x01, (routine_id >> 8) & 0xFF, routine_id & 0xFF]),
    )

    response = IRResponse(
        short_name=f"{service_name}_Response",
        params=(
            _create_coded_const_param(
                short_name="SID_PR",
                coded_value=0x71,
                semantic="SERVICE_ID",
            ),
            _create_matching_request_param(
                short_name="SF_PR",
                byte_position=1,
                request_byte_pos=1,
                byte_length=1,
                semantic="SUBFUNCTION",
            ),
            _create_matching_request_param(
                short_name="RID_PR",
                byte_position=2,
                request_byte_pos=2,
                byte_length=2,
                semantic="DATA",
            ),
        ),
        constant_prefix=bytes([0x71, 0x01, (routine_id >> 8) & 0xFF, routine_id & 0xFF]),
    )

    return IRDiagService(
        short_name=service_name,
        service_id=0x31,
        long_name=f"Start Routine: {routine_def.name}",
        subfunction=0x01,
        service_type=IRServiceType.POS_RESPONSE_WITH_SUBFUNCTION,
        request=request,
        positive_response=response,
        required_sessions=sessions,
        required_security=security,
    )


def _generate_routine_stop(
    routine_id: int,
    routine_def: RoutineDefinition,
    sessions: tuple[str, ...],
    security: tuple[str, ...],
) -> IRDiagService:
    """Generate stopRoutine service."""
    service_name = f"Stop_{routine_def.name}"

    request = IRRequest(
        short_name=f"{service_name}_Request",
        params=(
            _create_coded_const_param(
                short_name="SID_RQ",
                coded_value=0x31,
                semantic="SERVICE_ID",
            ),
            _create_coded_const_param(
                short_name="SF_RQ",
                byte_position=1,
                coded_value=0x02,
                semantic="SUBFUNCTION",
            ),
            _create_coded_const_param(
                short_name="RID_RQ",
                byte_position=2,
                coded_value=routine_id,
                bit_length=16,
                semantic="DATA",
            ),
        ),
        constant_prefix=bytes([0x31, 0x02, (routine_id >> 8) & 0xFF, routine_id & 0xFF]),
    )

    response = IRResponse(
        short_name=f"{service_name}_Response",
        params=(
            _create_coded_const_param(
                short_name="SID_PR",
                coded_value=0x71,
                semantic="SERVICE_ID",
            ),
            _create_matching_request_param(
                short_name="SF_PR",
                byte_position=1,
                request_byte_pos=1,
                byte_length=1,
                semantic="SUBFUNCTION",
            ),
            _create_matching_request_param(
                short_name="RID_PR",
                byte_position=2,
                request_byte_pos=2,
                byte_length=2,
                semantic="DATA",
            ),
        ),
        constant_prefix=bytes([0x71, 0x02, (routine_id >> 8) & 0xFF, routine_id & 0xFF]),
    )

    return IRDiagService(
        short_name=service_name,
        service_id=0x31,
        long_name=f"Stop Routine: {routine_def.name}",
        subfunction=0x02,
        service_type=IRServiceType.POS_RESPONSE_WITH_SUBFUNCTION,
        request=request,
        positive_response=response,
        required_sessions=sessions,
        required_security=security,
    )


def _generate_routine_result(
    routine_id: int,
    routine_def: RoutineDefinition,
    sessions: tuple[str, ...],
    security: tuple[str, ...],
) -> IRDiagService:
    """Generate requestRoutineResults service."""
    service_name = f"Result_{routine_def.name}"

    request = IRRequest(
        short_name=f"{service_name}_Request",
        params=(
            _create_coded_const_param(
                short_name="SID_RQ",
                coded_value=0x31,
                semantic="SERVICE_ID",
            ),
            _create_coded_const_param(
                short_name="SF_RQ",
                byte_position=1,
                coded_value=0x03,
                semantic="SUBFUNCTION",
            ),
            _create_coded_const_param(
                short_name="RID_RQ",
                byte_position=2,
                coded_value=routine_id,
                bit_length=16,
                semantic="DATA",
            ),
        ),
        constant_prefix=bytes([0x31, 0x03, (routine_id >> 8) & 0xFF, routine_id & 0xFF]),
    )

    response = IRResponse(
        short_name=f"{service_name}_Response",
        params=(
            _create_coded_const_param(
                short_name="SID_PR",
                coded_value=0x71,
                semantic="SERVICE_ID",
            ),
            _create_matching_request_param(
                short_name="SF_PR",
                byte_position=1,
                request_byte_pos=1,
                byte_length=1,
                semantic="SUBFUNCTION",
            ),
            _create_matching_request_param(
                short_name="RID_PR",
                byte_position=2,
                request_byte_pos=2,
                byte_length=2,
                semantic="DATA",
            ),
        ),
        constant_prefix=bytes([0x71, 0x03, (routine_id >> 8) & 0xFF, routine_id & 0xFF]),
    )

    return IRDiagService(
        short_name=service_name,
        service_id=0x31,
        long_name=f"Request Routine Results: {routine_def.name}",
        subfunction=0x03,
        service_type=IRServiceType.POS_RESPONSE_WITH_SUBFUNCTION,
        request=request,
        positive_response=response,
        required_sessions=sessions,
        required_security=security,
    )


# Re-export for convenience
__all__ = [
    "generate_read_did_service",
    "generate_write_did_service",
    "generate_session_control_services",
    "generate_security_access_services",
    "generate_ecu_reset_services",
    "generate_routine_services",
    # Helper functions for creating params with explicit types
    "_create_coded_const_param",
    "_create_matching_request_param",
    "_create_value_param",
]
