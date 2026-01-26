"""Models for the access_patterns section of diagnostic description."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from yaml_to_mdd.models.common import HexInt8

# Special values for "any" session access or "none" for security/auth
SessionsValue = Literal["any"] | list[str]
SecurityValue = Literal["none"] | list[str]
AuthenticationValue = Literal["none"] | list[str]


class AccessPattern(BaseModel):
    """An access pattern defining session, security, and authentication requirements.

    Access patterns are reusable definitions that can be referenced by DIDs,
    services, and routines to specify access control.

    Example:
    -------
        ```yaml
        extended_rw:
          sessions:
            - extended
            - programming
          security:
            - level_1
          authentication: none
        ```

    """

    model_config = ConfigDict(extra="forbid")

    sessions: Annotated[
        SessionsValue,
        Field(
            description=(
                "Session requirement. "
                "Use 'any' for all sessions, or list specific session names."
            ),
        ),
    ]

    security: Annotated[
        SecurityValue,
        Field(
            description=(
                "Security level requirement. "
                "Use 'none' for no security, or list required security levels."
            ),
        ),
    ]

    authentication: Annotated[
        AuthenticationValue,
        Field(
            description=(
                "Authentication requirement. "
                "Use 'none' for no authentication, or list required roles."
            ),
        ),
    ]

    nrc_on_fail: Annotated[
        HexInt8 | None,
        Field(
            default=None,
            description=(
                "Negative Response Code to return if access is denied. "
                "Common values: 0x22 (conditionsNotCorrect), "
                "0x33 (securityAccessDenied), 0x35 (invalidKey)"
            ),
        ),
    ]

    @field_validator("sessions", mode="before")
    @classmethod
    def validate_sessions(cls, v: Any) -> SessionsValue:
        """Validate sessions field."""
        if v == "any":
            return "any"
        if isinstance(v, str):
            # Single session name as string -> convert to list
            return [v]
        if isinstance(v, list):
            if not all(isinstance(item, str) for item in v):
                raise ValueError("Session names must be strings")
            return v
        raise ValueError("sessions must be 'any' or a list of session names")

    @field_validator("security", mode="before")
    @classmethod
    def validate_security(cls, v: Any) -> SecurityValue:
        """Validate security field."""
        if v == "none":
            return "none"
        if isinstance(v, str):
            # Single security level as string -> convert to list
            return [v]
        if isinstance(v, list):
            if not all(isinstance(item, str) for item in v):
                raise ValueError("Security level names must be strings")
            return v
        raise ValueError("security must be 'none' or a list of security level names")

    @field_validator("authentication", mode="before")
    @classmethod
    def validate_authentication(cls, v: Any) -> AuthenticationValue:
        """Validate authentication field."""
        if v == "none":
            return "none"
        if isinstance(v, str):
            # Single role as string -> convert to list
            return [v]
        if isinstance(v, list):
            if not all(isinstance(item, str) for item in v):
                raise ValueError("Authentication role names must be strings")
            return v
        raise ValueError("authentication must be 'none' or a list of role names")

    def requires_session(self, session_name: str) -> bool:
        """Check if this pattern allows the given session."""
        if self.sessions == "any":
            return True
        return session_name in self.sessions

    def requires_security(self) -> bool:
        """Check if this pattern requires any security level."""
        return self.security != "none"

    def requires_authentication(self) -> bool:
        """Check if this pattern requires any authentication."""
        return self.authentication != "none"


# Type alias for the access_patterns section
AccessPatterns = dict[str, AccessPattern]
