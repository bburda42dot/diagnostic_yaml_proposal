"""Models for the security section of diagnostic description."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from yaml_to_mdd.models.common import HexInt8


class SecurityLevel(BaseModel):
    """A security access level definition.

    Security levels define seed-key authentication parameters for
    the SecurityAccess (0x27) UDS service.

    Example:
    -------
        ```yaml
        level_1:
          level: 1
          seed_request: 0x01
          key_send: 0x02
          seed_size: 4
          key_size: 4
          algorithm: SecurityAlgo_XOR
          max_attempts: 3
          delay_on_fail_ms: 10000
          allowed_sessions:
            - extended
        ```

    """

    model_config = ConfigDict(extra="forbid")

    level: Annotated[
        int,
        Field(
            ge=0,
            le=255,
            description="Security level number (typically 1, 2, etc.)",
        ),
    ]

    seed_request: Annotated[
        HexInt8,
        Field(
            description=(
                "Subfunction byte for seed request (odd number). "
                "E.g., 0x01 for level 1, 0x03 for level 2."
            ),
        ),
    ]

    key_send: Annotated[
        HexInt8,
        Field(
            description=(
                "Subfunction byte for key send (even number). "
                "E.g., 0x02 for level 1, 0x04 for level 2."
            ),
        ),
    ]

    seed_size: Annotated[
        int,
        Field(
            ge=1,
            le=255,
            description="Size of the seed in bytes",
        ),
    ]

    key_size: Annotated[
        int,
        Field(
            ge=1,
            le=255,
            description="Size of the key in bytes",
        ),
    ]

    algorithm: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Algorithm identifier for seed-to-key calculation. "
                "E.g., 'SecurityAlgo_XOR', 'SecurityAlgo_AES128'"
            ),
        ),
    ]

    max_attempts: Annotated[
        int,
        Field(
            ge=1,
            le=255,
            description="Maximum failed attempts before lockout",
        ),
    ]

    delay_on_fail_ms: Annotated[
        int,
        Field(
            ge=0,
            description="Delay in milliseconds after failed attempt(s)",
        ),
    ]

    allowed_sessions: Annotated[
        list[str],
        Field(
            min_length=1,
            description=(
                "List of session names where this security level can be used. "
                "References to sessions section."
            ),
        ),
    ]

    # Optional fields
    delay_on_lockout_ms: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            description="Delay after max_attempts exceeded (lockout delay)",
        ),
    ]

    power_cycle_resets: Annotated[
        bool | None,
        Field(
            default=None,
            description="Whether power cycle resets the failed attempt counter",
        ),
    ]

    @field_validator("seed_request")
    @classmethod
    def validate_seed_request_odd(cls, v: int) -> int:
        """Validate that seed_request is an odd number."""
        if v % 2 == 0:
            raise ValueError(
                f"seed_request must be odd (got {v}). " "Odd subfunctions are for seed requests."
            )
        return v

    @field_validator("key_send")
    @classmethod
    def validate_key_send_even(cls, v: int) -> int:
        """Validate that key_send is an even number."""
        if v % 2 != 0:
            raise ValueError(
                f"key_send must be even (got {v}). " "Even subfunctions are for key sends."
            )
        return v


# Type alias for the security section
Security = dict[str, SecurityLevel]
