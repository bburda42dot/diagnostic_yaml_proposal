"""Models for the sessions section of diagnostic description."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from yaml_to_mdd.models.common import HexInt8


class SessionTiming(BaseModel):
    """Session-specific timing overrides.

    Allows sessions to have different timing parameters than the ECU defaults.

    Example:
    -------
        ```yaml
        timing:
          p2_ms: 100
          p2_star_ms: 10000
        ```

    """

    model_config = ConfigDict(extra="forbid")

    p2_ms: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            le=65535,
            description="P2 timeout override for this session (ms)",
        ),
    ]
    p2_star_ms: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            le=65535,
            description="P2* timeout override for this session (ms)",
        ),
    ]


class Session(BaseModel):
    """A single diagnostic session definition.

    Represents a UDS diagnostic session with its subfunction ID,
    optional human-readable alias, and session-specific settings.

    Example:
    -------
        ```yaml
        extended:
          id: 0x03
          alias: "ExtendedDiagnosticSession"
          requires_unlock: false
          timing:
            p2_ms: 50
        ```

    """

    model_config = ConfigDict(extra="forbid")

    id: Annotated[
        HexInt8,
        Field(
            description="Session subfunction ID (0x01-0xFF)",
            examples=["0x01", "0x02", "0x03"],
        ),
    ]
    alias: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description="Human-readable session name/alias",
            examples=["DefaultSession", "ProgrammingSession"],
        ),
    ]
    requires_unlock: Annotated[
        bool | None,
        Field(
            default=None,
            description="Whether this session requires security unlock to enter",
        ),
    ]
    timing: Annotated[
        SessionTiming | None,
        Field(
            default=None,
            description="Session-specific timing parameter overrides",
        ),
    ]


# Type alias for the sessions dictionary
# Key is session name (e.g., "default", "extended"), value is Session definition
Sessions = dict[str, Session]
