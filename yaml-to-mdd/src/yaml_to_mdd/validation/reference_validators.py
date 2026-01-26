"""Validators for cross-references between YAML sections."""

from __future__ import annotations

from typing import TYPE_CHECKING

from yaml_to_mdd.validation.base import BaseValidator
from yaml_to_mdd.validation.errors import ErrorCodes, ValidationResult

if TYPE_CHECKING:
    from yaml_to_mdd.models.root import DiagnosticDescription


class TypeReferenceValidator(BaseValidator):
    """Validates that type references point to defined types."""

    # Built-in types that are always valid
    BUILTIN_TYPES = frozenset(
        {
            "u8",
            "u16",
            "u24",
            "u32",
            "u64",
            "i8",
            "i16",
            "i32",
            "i64",
            "f32",
            "f64",
            "bool",
            "string",
            "bytes",
            "ascii",
        }
    )

    def validate(
        self,
        doc: DiagnosticDescription,
        result: ValidationResult,
    ) -> None:
        """Validate type references in DIDs and routines."""
        defined_types: set[str] = set()

        if doc.types:
            defined_types = set(doc.types.keys())

        # All valid types = defined + builtins
        valid_types = defined_types | self.BUILTIN_TYPES

        # Check DID type references
        if doc.dids:
            for did_addr, did_def in doc.dids.items():
                # Check if it's a reference to a named type that doesn't exist
                if isinstance(did_def.type, str) and did_def.type not in valid_types:
                    result.add_error(
                        code=ErrorCodes.E001_UNDEFINED_TYPE,
                        message=(
                            f"DID {did_addr:#06x} references undefined type " f"'{did_def.type}'"
                        ),
                        path=f"dids.{did_addr:#06x}.type",
                        suggestion=f"Define '{did_def.type}' in the 'types' section",
                        referenced_type=did_def.type,
                        available_types=list(defined_types),
                    )

        # Check routine parameter type references
        if doc.routines:
            for routine_id, routine_def in doc.routines.items():
                self._validate_routine_params(routine_id, routine_def, valid_types, result)

    def _validate_routine_params(
        self,
        routine_id: int,
        routine_def: object,
        valid_types: set[str],
        result: ValidationResult,
    ) -> None:
        """Validate type references in routine parameters."""
        params = getattr(routine_def, "parameters", None)
        if not params:
            return

        # Check start parameters
        start_request = getattr(params, "start_request", None)
        if start_request:
            for param in start_request:
                if param.type not in valid_types:
                    result.add_error(
                        code=ErrorCodes.E001_UNDEFINED_TYPE,
                        message=(
                            f"Routine {routine_id:#06x} start request parameter "
                            f"'{param.name}' references undefined type '{param.type}'"
                        ),
                        path=f"routines.{routine_id:#06x}.parameters.start_request.{param.name}.type",
                        suggestion=f"Define '{param.type}' in the 'types' section",
                    )

        start_response = getattr(params, "start_response", None)
        if start_response:
            for param in start_response:
                if param.type not in valid_types:
                    result.add_error(
                        code=ErrorCodes.E001_UNDEFINED_TYPE,
                        message=(
                            f"Routine {routine_id:#06x} start response parameter "
                            f"'{param.name}' references undefined type '{param.type}'"
                        ),
                        path=f"routines.{routine_id:#06x}.parameters.start_response.{param.name}.type",
                        suggestion=f"Define '{param.type}' in the 'types' section",
                    )

        result_response = getattr(params, "result_response", None)
        if result_response:
            for param in result_response:
                if param.type not in valid_types:
                    result.add_error(
                        code=ErrorCodes.E001_UNDEFINED_TYPE,
                        message=(
                            f"Routine {routine_id:#06x} result response parameter "
                            f"'{param.name}' references undefined type '{param.type}'"
                        ),
                        path=f"routines.{routine_id:#06x}.parameters.result_response.{param.name}.type",
                        suggestion=f"Define '{param.type}' in the 'types' section",
                    )


class SessionReferenceValidator(BaseValidator):
    """Validates that session references point to defined sessions."""

    def validate(
        self,
        doc: DiagnosticDescription,
        result: ValidationResult,
    ) -> None:
        """Validate session references in access patterns."""
        if not doc.sessions:
            return

        defined_sessions = set(doc.sessions.keys())
        defined_sessions.add("any")  # Special value meaning all sessions

        # Check access pattern session references
        if doc.access_patterns:
            for pattern_name, pattern in doc.access_patterns.items():
                sessions = pattern.sessions

                if sessions == "any":
                    continue

                if isinstance(sessions, list):
                    for session in sessions:
                        if session not in defined_sessions:
                            result.add_error(
                                code=ErrorCodes.E002_UNDEFINED_SESSION,
                                message=(
                                    f"Access pattern '{pattern_name}' references "
                                    f"undefined session '{session}'"
                                ),
                                path=f"access_patterns.{pattern_name}.sessions",
                                suggestion=f"Define '{session}' in the 'sessions' section",
                                referenced_session=session,
                                available_sessions=list(defined_sessions),
                            )


class SecurityReferenceValidator(BaseValidator):
    """Validates that security level references are valid."""

    def validate(
        self,
        doc: DiagnosticDescription,
        result: ValidationResult,
    ) -> None:
        """Validate security references in access patterns."""
        defined_security: set[str] = set()

        # Collect defined security levels
        if doc.security:
            defined_security = set(doc.security.keys())

        defined_security.add("none")  # Always valid

        # Check access pattern security references
        if doc.access_patterns:
            for pattern_name, pattern in doc.access_patterns.items():
                security = pattern.security

                if security == "none":
                    continue

                if isinstance(security, list):
                    for sec_level in security:
                        if sec_level not in defined_security:
                            result.add_error(
                                code=ErrorCodes.E003_UNDEFINED_SECURITY,
                                message=(
                                    f"Access pattern '{pattern_name}' references "
                                    f"undefined security level '{sec_level}'"
                                ),
                                path=f"access_patterns.{pattern_name}.security",
                                suggestion=(
                                    f"Define '{sec_level}' in the 'security' section "
                                    "or use 'none'"
                                ),
                            )


class AccessPatternReferenceValidator(BaseValidator):
    """Validates that access pattern references are valid."""

    def validate(
        self,
        doc: DiagnosticDescription,
        result: ValidationResult,
    ) -> None:
        """Validate access pattern references in DIDs and routines."""
        defined_patterns: set[str] = set()

        if doc.access_patterns:
            defined_patterns = set(doc.access_patterns.keys())

        # Check DID access pattern references
        if doc.dids:
            for did_addr, did_def in doc.dids.items():
                access_pattern = getattr(did_def, "access_pattern", None)
                if access_pattern and access_pattern not in defined_patterns:
                    result.add_error(
                        code=ErrorCodes.E004_UNDEFINED_ACCESS_PATTERN,
                        message=(
                            f"DID {did_addr:#06x} references undefined access "
                            f"pattern '{access_pattern}'"
                        ),
                        path=f"dids.{did_addr:#06x}.access_pattern",
                        suggestion=(f"Define '{access_pattern}' in 'access_patterns' section"),
                    )

        # Check routine access pattern references
        if doc.routines:
            for routine_name, routine_def in doc.routines.items():
                access_pattern = getattr(routine_def, "access_pattern", None)
                if access_pattern and access_pattern not in defined_patterns:
                    result.add_error(
                        code=ErrorCodes.E004_UNDEFINED_ACCESS_PATTERN,
                        message=(
                            f"Routine '{routine_name}' references undefined access "
                            f"pattern '{access_pattern}'"
                        ),
                        path=f"routines.{routine_name}.access_pattern",
                        suggestion=(f"Define '{access_pattern}' in 'access_patterns' section"),
                    )
