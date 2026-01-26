"""Validators for data consistency checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from yaml_to_mdd.validation.base import BaseValidator
from yaml_to_mdd.validation.errors import ErrorCodes, ValidationResult

if TYPE_CHECKING:
    from yaml_to_mdd.models.root import DiagnosticDescription


class UniqueSessionIdValidator(BaseValidator):
    """Validates that session IDs are unique."""

    def validate(
        self,
        doc: DiagnosticDescription,
        result: ValidationResult,
    ) -> None:
        """Check for duplicate session IDs."""
        if not doc.sessions:
            return

        seen_ids: dict[int, str] = {}

        for session_name, session_def in doc.sessions.items():
            session_id = session_def.id

            if session_id in seen_ids:
                result.add_error(
                    code=ErrorCodes.E100_DUPLICATE_ID,
                    message=(
                        f"Session '{session_name}' has duplicate ID {session_id:#04x}, "
                        f"already used by '{seen_ids[session_id]}'"
                    ),
                    path=f"sessions.{session_name}.id",
                    suggestion="Each session must have a unique ID",
                )
            else:
                seen_ids[session_id] = session_name


class UniqueSecurityLevelValidator(BaseValidator):
    """Validates that security levels use proper odd/even subfunctions and are unique."""

    def validate(
        self,
        doc: DiagnosticDescription,
        result: ValidationResult,
    ) -> None:
        """Check security level consistency."""
        if not doc.security:
            return

        seen_seed_requests: dict[int, str] = {}
        seen_key_sends: dict[int, str] = {}

        for level_name, level_def in doc.security.items():
            seed_request = level_def.seed_request
            key_send = level_def.key_send

            # Check odd/even pairing (Pydantic already validates this, but we add context)
            # These checks are redundant with Pydantic validators but provide
            # better error messages in the validation result

            # Check expected pairing (seed_request + 1 should equal key_send)
            expected_key_send = seed_request + 1
            if key_send != expected_key_send:
                result.add_warning(
                    code=ErrorCodes.W010_MISMATCHED_SECURITY_PAIR,
                    message=(
                        f"Security level '{level_name}' key_send ({key_send:#04x}) "
                        f"doesn't match expected value ({expected_key_send:#04x})"
                    ),
                    path=f"security.{level_name}.key_send",
                    suggestion="Usually key_send = seed_request + 1",
                )

            # Check for duplicate seed_request values
            if seed_request in seen_seed_requests:
                result.add_error(
                    code=ErrorCodes.E100_DUPLICATE_ID,
                    message=(
                        f"Security level '{level_name}' has duplicate seed_request "
                        f"{seed_request:#04x}, already used by "
                        f"'{seen_seed_requests[seed_request]}'"
                    ),
                    path=f"security.{level_name}.seed_request",
                )
            else:
                seen_seed_requests[seed_request] = level_name

            # Check for duplicate key_send values
            if key_send in seen_key_sends:
                result.add_error(
                    code=ErrorCodes.E100_DUPLICATE_ID,
                    message=(
                        f"Security level '{level_name}' has duplicate key_send "
                        f"{key_send:#04x}, already used by "
                        f"'{seen_key_sends[key_send]}'"
                    ),
                    path=f"security.{level_name}.key_send",
                )
            else:
                seen_key_sends[key_send] = level_name


class DIDRangeValidator(BaseValidator):
    """Validates that DID addresses are in valid UDS ranges."""

    # Standard DID ranges per ISO 14229
    DID_RANGES = [
        (0x0000, 0x00FF, "ISO Reserved"),
        (0x0100, 0x01FF, "Vehicle Manufacturer Specific"),
        (0x0200, 0x02FF, "Network Configuration"),
        (0xF000, 0xF0FF, "Vehicle Manufacturer Specific (System Supplier)"),
        (0xF100, 0xF1FF, "Vehicle Identification"),
        (0xF200, 0xF2FF, "Stored Data"),
        (0xF300, 0xF3FF, "Input/Output"),
        (0xF400, 0xF4FF, "Routine Identifier"),
        (0xF500, 0xF5FF, "ISO Reserved"),
        (0xF600, 0xF6FF, "ODX File Identifier"),
        (0xF700, 0xF7FF, "ISO Reserved"),
        (0xF800, 0xF8FF, "System Supplier Specific"),
        (0xF900, 0xF9FF, "System Supplier Specific"),
        (0xFA00, 0xFAFF, "System Supplier Specific"),
        (0xFB00, 0xFBFF, "System Supplier Specific"),
        (0xFC00, 0xFCFF, "System Supplier Specific"),
        (0xFD00, 0xFDFF, "Reserved for OBD"),
        (0xFE00, 0xFEFF, "System Supplier Specific"),
        (0xFF00, 0xFFFF, "ISO Reserved"),
    ]

    def validate(
        self,
        doc: DiagnosticDescription,
        result: ValidationResult,
    ) -> None:
        """Check DID addresses are within valid 16-bit range."""
        if not doc.dids:
            return

        for did_addr, _did_def in doc.dids.items():
            if not 0x0000 <= did_addr <= 0xFFFF:
                result.add_error(
                    code=ErrorCodes.E201_INVALID_DID_ADDRESS,
                    message=(
                        f"DID address {did_addr:#06x} is out of valid range " "(0x0000-0xFFFF)"
                    ),
                    path=f"dids.{did_addr:#06x}",
                )


class DTCFormatValidator(BaseValidator):
    """Validates DTC format follows SAE J2012 conventions."""

    def validate(
        self,
        doc: DiagnosticDescription,
        result: ValidationResult,
    ) -> None:
        """Check DTC SAE field format follows SAE J2012 conventions."""
        if not doc.dtcs:
            return

        for dtc_code, dtc_def in doc.dtcs.items():
            # Check SAE field format (P0123, B0123, etc.)
            sae_code = dtc_def.sae
            if sae_code and len(sae_code) == 5:
                prefix = sae_code[0].upper()
                if prefix not in ("P", "B", "C", "U"):
                    result.add_error(
                        code=ErrorCodes.E302_INVALID_DTC_FORMAT,
                        message=(
                            f"DTC {dtc_code} SAE code '{sae_code}' has invalid "
                            f"prefix '{prefix}', must be P/B/C/U"
                        ),
                        path=f"dtcs.{dtc_code}.sae",
                        suggestion=(
                            "Use P for Powertrain, B for Body, " "C for Chassis, U for Network"
                        ),
                    )

                # Check numeric part (should be 4 decimal digits for SAE J2012)
                numeric_part = sae_code[1:]
                if not numeric_part.isdigit():
                    result.add_error(
                        code=ErrorCodes.E302_INVALID_DTC_FORMAT,
                        message=(
                            f"DTC {dtc_code} SAE code '{sae_code}' has invalid "
                            "numeric part, must be 4 decimal digits"
                        ),
                        path=f"dtcs.{dtc_code}.sae",
                    )


class RoutineIdRangeValidator(BaseValidator):
    """Validates that routine IDs are in valid UDS ranges."""

    def validate(
        self,
        doc: DiagnosticDescription,
        result: ValidationResult,
    ) -> None:
        """Check routine IDs are within valid 16-bit range."""
        if not doc.routines:
            return

        for routine_id, _routine_def in doc.routines.items():
            if not 0x0000 <= routine_id <= 0xFFFF:
                result.add_error(
                    code=ErrorCodes.E200_VALUE_OUT_OF_RANGE,
                    message=(
                        f"Routine ID {routine_id:#06x} is out of valid range " "(0x0000-0xFFFF)"
                    ),
                    path=f"routines.{routine_id:#06x}",
                )


class UnusedDefinitionsValidator(BaseValidator):
    """Warns about unused type definitions."""

    def validate(
        self,
        doc: DiagnosticDescription,
        result: ValidationResult,
    ) -> None:
        """Check for unused types, sessions, security levels."""
        self._check_unused_types(doc, result)
        self._check_unused_sessions(doc, result)

    def _check_unused_types(
        self,
        doc: DiagnosticDescription,
        result: ValidationResult,
    ) -> None:
        """Check for unused type definitions."""
        if not doc.types:
            return

        used_types: set[str] = set()

        # Collect types used in DIDs
        if doc.dids:
            for _did_addr, did_def in doc.dids.items():
                if isinstance(did_def.type, str):
                    used_types.add(did_def.type)

        # Collect types used in routines
        if doc.routines:
            for _routine_id, routine_def in doc.routines.items():
                params = getattr(routine_def, "parameters", None)
                if params:
                    for section in [
                        "start_request",
                        "start_response",
                        "result_response",
                    ]:
                        param_list = getattr(params, section, None)
                        if param_list:
                            for param in param_list:
                                used_types.add(param.type)

        # Find unused types
        for type_name in doc.types:
            if type_name not in used_types:
                result.add_warning(
                    code=ErrorCodes.W001_UNUSED_TYPE,
                    message=f"Type '{type_name}' is defined but never used",
                    path=f"types.{type_name}",
                    suggestion="Remove unused type or reference it in DIDs/routines",
                )

    def _check_unused_sessions(
        self,
        doc: DiagnosticDescription,
        result: ValidationResult,
    ) -> None:
        """Check for unused session definitions."""
        if not doc.sessions:
            return

        used_sessions: set[str] = set()

        # Collect sessions used in access patterns
        if doc.access_patterns:
            for _pattern_name, pattern in doc.access_patterns.items():
                sessions = pattern.sessions
                if sessions == "any":
                    # "any" means all sessions are used
                    return
                if isinstance(sessions, list):
                    used_sessions.update(sessions)

        # Collect sessions used in security levels
        if doc.security:
            for _level_name, level_def in doc.security.items():
                allowed = getattr(level_def, "allowed_sessions", [])
                if allowed:
                    used_sessions.update(allowed)

        # Find unused sessions
        for session_name in doc.sessions:
            if session_name not in used_sessions:
                result.add_warning(
                    code=ErrorCodes.W002_UNUSED_SESSION,
                    message=f"Session '{session_name}' is defined but never used",
                    path=f"sessions.{session_name}",
                    suggestion="Remove unused session or reference it in access_patterns",
                )
