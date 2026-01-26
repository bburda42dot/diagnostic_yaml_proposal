"""Generate diagnostic services from YAML definitions."""

from __future__ import annotations

from yaml_to_mdd.ir.services import (
    IRDiagService,
    IRParam,
    IRRequest,
    IRResponse,
    IRServiceType,
)
from yaml_to_mdd.models.dids import DIDDefinition
from yaml_to_mdd.models.routines import RoutineDefinition


def generate_read_did_service(
    did_id: int,
    did_def: DIDDefinition,
    dop_name: str,
    sessions: tuple[str, ...] = (),
    security: tuple[str, ...] = (),
) -> IRDiagService:
    """Generate ReadDataByIdentifier service for a DID.

    Args:
    ----
        did_id: DID identifier (0x0000-0xFFFF).
        did_def: DID definition from YAML.
        dop_name: Name of the DOP for this DID's data.
        sessions: Required sessions.
        security: Required security levels.

    Returns:
    -------
        IRDiagService for reading this DID.

    """
    service_name = f"Read_{did_def.name}"

    # Request: [SID=0x22][DID_HI][DID_LO]
    request = IRRequest(
        short_name=f"{service_name}_Request",
        params=(
            IRParam(
                short_name="ServiceID",
                byte_position=0,
                semantic="SERVICE_ID",
            ),
            IRParam(
                short_name="DID",
                byte_position=1,
                dop_ref="DOP_DID",
                semantic="DATA",
            ),
        ),
        constant_prefix=bytes([0x22, (did_id >> 8) & 0xFF, did_id & 0xFF]),
    )

    # Response: [SID+0x40=0x62][DID_HI][DID_LO][DATA...]
    response = IRResponse(
        short_name=f"{service_name}_Response",
        params=(
            IRParam(
                short_name="ServiceID",
                byte_position=0,
                semantic="SERVICE_ID",
            ),
            IRParam(
                short_name="DID",
                byte_position=1,
                dop_ref="DOP_DID",
            ),
            IRParam(
                short_name=did_def.name,
                byte_position=3,
                dop_ref=dop_name,
                semantic="DATA",
            ),
        ),
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
    sessions: tuple[str, ...] = (),
    security: tuple[str, ...] = (),
) -> IRDiagService:
    """Generate WriteDataByIdentifier service for a DID.

    Args:
    ----
        did_id: DID identifier.
        did_def: DID definition.
        dop_name: DOP name for data.
        sessions: Required sessions.
        security: Required security levels.

    Returns:
    -------
        IRDiagService for writing this DID.

    """
    service_name = f"Write_{did_def.name}"

    # Request: [SID=0x2E][DID_HI][DID_LO][DATA...]
    request = IRRequest(
        short_name=f"{service_name}_Request",
        params=(
            IRParam(short_name="ServiceID", byte_position=0, semantic="SERVICE_ID"),
            IRParam(short_name="DID", byte_position=1, dop_ref="DOP_DID"),
            IRParam(
                short_name=did_def.name,
                byte_position=3,
                dop_ref=dop_name,
                semantic="DATA",
            ),
        ),
        constant_prefix=bytes([0x2E, (did_id >> 8) & 0xFF, did_id & 0xFF]),
    )

    # Response: [SID+0x40=0x6E][DID_HI][DID_LO]
    response = IRResponse(
        short_name=f"{service_name}_Response",
        params=(
            IRParam(short_name="ServiceID", byte_position=0, semantic="SERVICE_ID"),
            IRParam(short_name="DID", byte_position=1, dop_ref="DOP_DID"),
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
    request_params = [
        IRParam(short_name="ServiceID", byte_position=0, semantic="SERVICE_ID"),
        IRParam(short_name="Subfunction", byte_position=1, semantic="SUBFUNCTION"),
        IRParam(short_name="RoutineID", byte_position=2, dop_ref="DOP_RID"),
    ]

    request = IRRequest(
        short_name=f"{service_name}_Request",
        params=tuple(request_params),
        constant_prefix=bytes([0x31, 0x01, (routine_id >> 8) & 0xFF, routine_id & 0xFF]),
    )

    response = IRResponse(
        short_name=f"{service_name}_Response",
        params=(
            IRParam(short_name="ServiceID", byte_position=0, semantic="SERVICE_ID"),
            IRParam(short_name="Subfunction", byte_position=1, semantic="SUBFUNCTION"),
            IRParam(short_name="RoutineID", byte_position=2, dop_ref="DOP_RID"),
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
            IRParam(short_name="ServiceID", byte_position=0, semantic="SERVICE_ID"),
            IRParam(short_name="Subfunction", byte_position=1, semantic="SUBFUNCTION"),
            IRParam(short_name="RoutineID", byte_position=2, dop_ref="DOP_RID"),
        ),
        constant_prefix=bytes([0x31, 0x02, (routine_id >> 8) & 0xFF, routine_id & 0xFF]),
    )

    response = IRResponse(
        short_name=f"{service_name}_Response",
        params=(
            IRParam(short_name="ServiceID", byte_position=0),
            IRParam(short_name="Subfunction", byte_position=1),
            IRParam(short_name="RoutineID", byte_position=2),
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
            IRParam(short_name="ServiceID", byte_position=0),
            IRParam(short_name="Subfunction", byte_position=1),
            IRParam(short_name="RoutineID", byte_position=2),
        ),
        constant_prefix=bytes([0x31, 0x03, (routine_id >> 8) & 0xFF, routine_id & 0xFF]),
    )

    response = IRResponse(
        short_name=f"{service_name}_Response",
        params=(
            IRParam(short_name="ServiceID", byte_position=0),
            IRParam(short_name="Subfunction", byte_position=1),
            IRParam(short_name="RoutineID", byte_position=2),
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
    "generate_routine_services",
]
