"""Models for the routines section of diagnostic description.

Routines are executable procedures accessed via the RoutineControl (0x31) UDS service.
Examples include "EraseMemory", "CheckProgrammingPreconditions", or "ResetLearning".
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from yaml_to_mdd.models.types import TypeDefinition

if TYPE_CHECKING:
    from pydantic_core import core_schema as cs


# Routine operation literals (matching schema enum)
RoutineOperationLiteral = Literal["start", "stop", "result"]


class RoutineParameter(BaseModel):
    """A parameter in a routine request or response.

    Example:
    -------
        ```yaml
        - name: memoryAddress
          type: u32
          description: Start address of memory block
        ```

    """

    model_config = ConfigDict(extra="forbid")

    name: Annotated[
        str,
        Field(
            min_length=1,
            description="Parameter name",
        ),
    ]

    type: Annotated[
        str | TypeDefinition,
        Field(
            description="Type reference (built-in or custom type name) or inline type definition",
        ),
    ]

    description: Annotated[
        str | None,
        Field(
            default=None,
            description="Parameter description",
        ),
    ]

    optional: Annotated[
        bool | None,
        Field(
            default=None,
            description="Whether this parameter is optional",
        ),
    ]


class RoutineOperationParams(BaseModel):
    """Parameters for a single routine operation (input/output).

    Example:
    -------
        ```yaml
        start:
          input:
            - name: memoryAddress
              type: u32
          output:
            - name: status
              type: u8
        ```

    """

    model_config = ConfigDict(extra="forbid")

    input: Annotated[
        list[RoutineParameter] | None,
        Field(
            default=None,
            description="Input parameters for this operation",
        ),
    ]

    output: Annotated[
        list[RoutineParameter] | None,
        Field(
            default=None,
            description="Output parameters for this operation",
        ),
    ]


class RoutineParameters(BaseModel):
    """Parameters for routine operations.

    Organized by operation: start, stop, result.
    Each operation can have input and output parameters.

    Example:
    -------
        ```yaml
        parameters:
          start:
            input:
              - name: memoryAddress
                type: u32
            output:
              - name: status
                type: u8
          result:
            output:
              - name: finalStatus
                type: u8
        ```

    """

    model_config = ConfigDict(extra="forbid")

    start: Annotated[
        RoutineOperationParams | None,
        Field(
            default=None,
            description="Parameters for startRoutine operation",
        ),
    ]

    stop: Annotated[
        RoutineOperationParams | None,
        Field(
            default=None,
            description="Parameters for stopRoutine operation",
        ),
    ]

    result: Annotated[
        RoutineOperationParams | None,
        Field(
            default=None,
            description="Parameters for requestRoutineResults operation",
        ),
    ]


class RoutineDefinition(BaseModel):
    """A control routine definition.

    Routines are executable procedures accessed via RoutineControl (0x31).
    Common examples include memory operations, calibration routines, and
    diagnostic tests.

    Example:
    -------
        ```yaml
        0xFF00:
          name: EraseMemory
          description: Erase flash memory for reprogramming
          access: programming_write
          operations:
            - start
            - result
        ```

    """

    model_config = ConfigDict(extra="allow")  # Allow x-oem, annotations, etc.

    name: Annotated[
        str,
        Field(
            min_length=1,
            description="Human-readable routine name",
        ),
    ]

    description: Annotated[
        str | None,
        Field(
            default=None,
            description="Detailed description of the routine",
        ),
    ]

    access: Annotated[
        str,
        Field(
            description="Access pattern reference (from access_patterns section)",
        ),
    ]

    operations: Annotated[
        list[RoutineOperationLiteral],
        Field(
            min_length=1,
            description="Supported operations: start, stop, result",
        ),
    ]

    parameters: Annotated[
        RoutineParameters | None,
        Field(
            default=None,
            description="Request/response parameters for each operation",
        ),
    ]

    audience: Annotated[
        dict[str, Any] | None,
        Field(
            default=None,
            description="Audience restriction (supplier, development, etc.)",
        ),
    ]

    annotations: Annotated[
        dict[str, Any] | None,
        Field(
            default=None,
            description="Custom annotations",
        ),
    ]

    def supports_start(self) -> bool:
        """Check if this routine supports startRoutine."""
        return "start" in self.operations

    def supports_stop(self) -> bool:
        """Check if this routine supports stopRoutine."""
        return "stop" in self.operations

    def supports_result(self) -> bool:
        """Check if this routine supports requestRoutineResults."""
        return "result" in self.operations


def _parse_routine_key(key: str | int) -> int:
    """Parse a routine key to an integer.

    Args:
    ----
        key: Routine identifier as hex string (e.g., "0xFF00") or integer.

    Returns:
    -------
        Integer representation of the routine ID.

    Raises:
    ------
        ValueError: If key cannot be parsed or is invalid type.

    """
    if isinstance(key, str):
        if key.lower().startswith("0x"):
            return int(key, 16)
        return int(key)
    if isinstance(key, int):
        return key
    raise ValueError(f"Invalid routine key type: {type(key)}")


def _validate_routine_id(routine_id: int) -> None:
    """Validate that routine ID is within 16-bit range.

    Args:
    ----
        routine_id: Routine identifier to validate.

    Raises:
    ------
        ValueError: If routine ID is out of range.

    """
    if not 0 <= routine_id <= 0xFFFF:
        raise ValueError(f"Routine ID {hex(routine_id)} out of range (0x0000-0xFFFF)")


def _validate_routines(value: Any) -> dict[int, RoutineDefinition]:
    """Validate and parse a routines dictionary.

    Args:
    ----
        value: Raw dictionary with routine definitions.

    Returns:
    -------
        Parsed dictionary with integer keys and RoutineDefinition values.

    Raises:
    ------
        ValueError: If value is not a dict or contains invalid data.

    """
    if not isinstance(value, dict):
        raise ValueError("Routines must be a dictionary")

    result: dict[int, RoutineDefinition] = {}
    for key, val in value.items():
        int_key = _parse_routine_key(key)
        _validate_routine_id(int_key)

        if isinstance(val, RoutineDefinition):
            result[int_key] = val
        else:
            result[int_key] = RoutineDefinition.model_validate(val)

    return result


class _RoutinesDictMeta(type):
    """Metaclass for RoutinesDict to support Pydantic validation."""

    def __getattr__(cls, name: str) -> Any:
        """Handle Pydantic attribute access."""
        if name == "model_validate":
            return _validate_routines
        raise AttributeError(f"type object 'RoutinesDict' has no attribute {name!r}")


class RoutinesDict(dict[int, RoutineDefinition], metaclass=_RoutinesDictMeta):
    """Dictionary of routines keyed by their 16-bit identifier.

    Supports hex string keys (e.g., "0xFF00") and integer keys.
    Validates that all keys are in the range 0x0000-0xFFFF.
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: Any,
    ) -> cs.CoreSchema:
        """Get Pydantic core schema for validation."""
        from pydantic_core import core_schema

        return core_schema.no_info_plain_validator_function(_validate_routines)


# Type alias for simpler usage
Routines = RoutinesDict
