"""Tests for routines section models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from yaml_to_mdd.models.routines import (
    RoutineDefinition,
    RoutineOperationParams,
    RoutineParameter,
    RoutineParameters,
    Routines,
)
from yaml_to_mdd.models.types import TypeDefinition


class TestRoutineParameter:
    """Tests for RoutineParameter model."""

    def test_minimal_parameter(self) -> None:
        """Should accept minimal parameter."""
        param = RoutineParameter(
            name="address",
            type="u32",
        )
        assert param.name == "address"
        assert param.type == "u32"
        assert param.description is None
        assert param.optional is None

    def test_full_parameter(self) -> None:
        """Should accept full parameter with all fields."""
        param = RoutineParameter(
            name="memorySize",
            type="u32",
            description="Size of memory block in bytes",
            optional=False,
        )
        assert param.description == "Size of memory block in bytes"
        assert param.optional is False

    def test_optional_parameter(self) -> None:
        """Should accept optional parameter flag."""
        param = RoutineParameter(
            name="checksum",
            type="u16",
            optional=True,
        )
        assert param.optional is True

    def test_custom_type_reference(self) -> None:
        """Should accept custom type reference."""
        param = RoutineParameter(
            name="status",
            type="EraseStatusType",
        )
        assert param.type == "EraseStatusType"

    def test_inline_type_definition(self) -> None:
        """Should accept inline type definition."""
        param = RoutineParameter(
            name="cylinderMask",
            type={"base": "u8"},  # type: ignore[arg-type]
        )
        assert isinstance(param.type, TypeDefinition)
        assert param.type.base.value == "u8"

    def test_reject_empty_name(self) -> None:
        """Should reject empty parameter name."""
        with pytest.raises(ValidationError) as exc_info:
            RoutineParameter(name="", type="u32")
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_reject_extra_fields(self) -> None:
        """Should reject extra fields (extra=forbid)."""
        with pytest.raises(ValidationError) as exc_info:
            RoutineParameter(
                name="test",
                type="u8",
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "Extra inputs are not permitted" in str(exc_info.value)


class TestRoutineOperationParams:
    """Tests for RoutineOperationParams model."""

    def test_empty_params(self) -> None:
        """Should accept empty params."""
        params = RoutineOperationParams()
        assert params.input is None
        assert params.output is None

    def test_input_params(self) -> None:
        """Should accept input parameters."""
        params = RoutineOperationParams(
            input=[
                RoutineParameter(name="address", type="u32"),
                RoutineParameter(name="size", type="u32"),
            ]
        )
        assert params.input is not None
        assert len(params.input) == 2
        assert params.input[0].name == "address"

    def test_output_params(self) -> None:
        """Should accept output parameters."""
        params = RoutineOperationParams(
            output=[
                RoutineParameter(name="status", type="u8"),
            ]
        )
        assert params.output is not None
        assert len(params.output) == 1

    def test_both_input_output(self) -> None:
        """Should accept both input and output parameters."""
        params = RoutineOperationParams(
            input=[RoutineParameter(name="cmd", type="u8")],
            output=[RoutineParameter(name="result", type="u16")],
        )
        assert params.input is not None
        assert params.output is not None


class TestRoutineParameters:
    """Tests for RoutineParameters model."""

    def test_empty_parameters(self) -> None:
        """Should accept empty parameters (all None)."""
        params = RoutineParameters()
        assert params.start is None
        assert params.stop is None
        assert params.result is None

    def test_start_only(self) -> None:
        """Should accept start-only parameters."""
        params = RoutineParameters(
            start=RoutineOperationParams(
                input=[
                    RoutineParameter(name="address", type="u32"),
                    RoutineParameter(name="size", type="u32"),
                ],
                output=[
                    RoutineParameter(name="status", type="u8"),
                ],
            ),
        )
        assert params.start is not None
        assert params.start.input is not None
        assert len(params.start.input) == 2
        assert params.start.output is not None
        assert len(params.start.output) == 1
        assert params.stop is None
        assert params.result is None

    def test_result_only(self) -> None:
        """Should accept result-only parameters."""
        params = RoutineParameters(
            result=RoutineOperationParams(
                output=[
                    RoutineParameter(name="finalStatus", type="u8"),
                    RoutineParameter(name="errorCode", type="u16"),
                ],
            ),
        )
        assert params.result is not None
        assert params.result.output is not None
        assert len(params.result.output) == 2
        assert params.start is None

    def test_all_operations(self) -> None:
        """Should accept parameters for all operations."""
        params = RoutineParameters(
            start=RoutineOperationParams(
                input=[RoutineParameter(name="startParam", type="u8")],
                output=[RoutineParameter(name="startResult", type="u8")],
            ),
            stop=RoutineOperationParams(
                input=[RoutineParameter(name="stopParam", type="u8")],
                output=[RoutineParameter(name="stopResult", type="u8")],
            ),
            result=RoutineOperationParams(
                input=[RoutineParameter(name="resultParam", type="u8")],
                output=[RoutineParameter(name="resultData", type="u8")],
            ),
        )
        assert params.start is not None
        assert params.stop is not None
        assert params.result is not None

    def test_reject_extra_fields(self) -> None:
        """Should reject extra fields."""
        with pytest.raises(ValidationError) as exc_info:
            RoutineParameters(unknown_phase=RoutineOperationParams())  # type: ignore[call-arg]
        assert "Extra inputs are not permitted" in str(exc_info.value)


class TestRoutineDefinition:
    """Tests for RoutineDefinition model."""

    def test_minimal_routine(self) -> None:
        """Should accept minimal routine definition."""
        routine = RoutineDefinition(
            name="TestRoutine",
            access="extended_read",
            operations=["start"],
        )
        assert routine.name == "TestRoutine"
        assert routine.access == "extended_read"
        assert "start" in routine.operations
        assert routine.description is None
        assert routine.parameters is None

    def test_full_routine(self) -> None:
        """Should accept full routine definition."""
        routine = RoutineDefinition(
            name="EraseMemory",
            description="Erase flash memory for reprogramming",
            access="programming_write",
            operations=["start", "result"],
            audience={"tier": "supplier"},
            annotations={"custom": "value"},
        )
        assert routine.name == "EraseMemory"
        assert routine.description == "Erase flash memory for reprogramming"
        assert routine.audience == {"tier": "supplier"}
        assert routine.annotations == {"custom": "value"}

    def test_operations_from_strings(self) -> None:
        """Should accept operations as strings."""
        routine = RoutineDefinition(
            name="TestRoutine",
            access="extended_read",
            operations=["start", "result"],
        )
        assert routine.supports_start() is True
        assert routine.supports_stop() is False
        assert routine.supports_result() is True

    def test_all_operations(self) -> None:
        """Should accept routine with all operations."""
        routine = RoutineDefinition(
            name="LongRunningTest",
            access="extended_read",
            operations=["start", "stop", "result"],
        )
        assert routine.supports_start() is True
        assert routine.supports_stop() is True
        assert routine.supports_result() is True

    def test_with_parameters(self) -> None:
        """Should accept routine with parameters."""
        routine = RoutineDefinition(
            name="EraseMemory",
            access="programming_write",
            operations=["start", "result"],
            parameters=RoutineParameters(
                start=RoutineOperationParams(
                    input=[
                        RoutineParameter(name="address", type="u32"),
                        RoutineParameter(name="size", type="u32"),
                    ],
                ),
                result=RoutineOperationParams(
                    output=[
                        RoutineParameter(name="status", type="u8"),
                    ],
                ),
            ),
        )
        assert routine.parameters is not None
        assert routine.parameters.start is not None
        assert routine.parameters.start.input is not None
        assert len(routine.parameters.start.input) == 2
        assert routine.parameters.result is not None
        assert routine.parameters.result.output is not None
        assert len(routine.parameters.result.output) == 1

    def test_supports_start(self) -> None:
        """Should correctly check start support."""
        with_start = RoutineDefinition(name="Test", access="read", operations=["start"])
        without_start = RoutineDefinition(name="Test", access="read", operations=["result"])
        assert with_start.supports_start() is True
        assert without_start.supports_start() is False

    def test_supports_stop(self) -> None:
        """Should correctly check stop support."""
        with_stop = RoutineDefinition(
            name="Test",
            access="read",
            operations=["start", "stop"],
        )
        without_stop = RoutineDefinition(name="Test", access="read", operations=["start"])
        assert with_stop.supports_stop() is True
        assert without_stop.supports_stop() is False

    def test_supports_result(self) -> None:
        """Should correctly check result support."""
        with_result = RoutineDefinition(name="Test", access="read", operations=["result"])
        without_result = RoutineDefinition(name="Test", access="read", operations=["start"])
        assert with_result.supports_result() is True
        assert without_result.supports_result() is False

    def test_reject_empty_operations(self) -> None:
        """Should reject routine with empty operations."""
        with pytest.raises(ValidationError) as exc_info:
            RoutineDefinition(
                name="TestRoutine",
                access="extended_read",
                operations=[],
            )
        assert "at least 1 item" in str(exc_info.value).lower()

    def test_reject_invalid_operation(self) -> None:
        """Should reject invalid operation value."""
        with pytest.raises(ValidationError) as exc_info:
            RoutineDefinition(
                name="TestRoutine",
                access="extended_read",
                operations=["invalid"],  # type: ignore[list-item]
            )
        assert "validation error" in str(exc_info.value).lower()

    def test_reject_empty_name(self) -> None:
        """Should reject empty routine name."""
        with pytest.raises(ValidationError) as exc_info:
            RoutineDefinition(
                name="",
                access="read",
                operations=["start"],
            )
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_allow_extra_fields(self) -> None:
        """Should allow extra fields (x-oem extensions)."""
        routine = RoutineDefinition(
            name="Test",
            access="read",
            operations=["start"],
            **{"x-custom": "value"},  # type: ignore[arg-type]
        )
        # extra=allow means this should work
        assert routine.name == "Test"


class TestRoutinesDict:
    """Tests for RoutinesDict parsing."""

    def test_parse_hex_string_keys(self) -> None:
        """Should parse hex string keys."""
        data = {
            "0xFF00": {
                "name": "EraseMemory",
                "access": "programming",
                "operations": ["start"],
            },
            "0xF001": {
                "name": "CheckConditions",
                "access": "extended",
                "operations": ["start", "result"],
            },
        }
        routines = Routines.model_validate(data)
        assert 0xFF00 in routines
        assert 0xF001 in routines
        assert routines[0xFF00].name == "EraseMemory"
        assert routines[0xF001].name == "CheckConditions"

    def test_parse_lowercase_hex(self) -> None:
        """Should parse lowercase hex strings."""
        data = {
            "0xff00": {
                "name": "Test",
                "access": "read",
                "operations": ["start"],
            },
        }
        routines = Routines.model_validate(data)
        assert 0xFF00 in routines

    def test_parse_integer_keys(self) -> None:
        """Should parse integer keys."""
        data = {
            65280: {  # 0xFF00
                "name": "EraseMemory",
                "access": "programming",
                "operations": ["start"],
            },
        }
        routines = Routines.model_validate(data)
        assert 0xFF00 in routines

    def test_parse_decimal_string_keys(self) -> None:
        """Should parse decimal string keys."""
        data = {
            "256": {  # 0x0100
                "name": "Test",
                "access": "read",
                "operations": ["start"],
            },
        }
        routines = Routines.model_validate(data)
        assert 0x0100 in routines

    def test_mixed_key_types(self) -> None:
        """Should handle mixed key types."""
        data = {
            "0xFF00": {
                "name": "Routine1",
                "access": "read",
                "operations": ["start"],
            },
            61697: {  # 0xF101
                "name": "Routine2",
                "access": "read",
                "operations": ["start"],
            },
        }
        routines = Routines.model_validate(data)
        assert 0xFF00 in routines
        assert 0xF101 in routines

    def test_boundary_values(self) -> None:
        """Should accept boundary values."""
        data = {
            "0x0000": {
                "name": "MinRoutine",
                "access": "read",
                "operations": ["start"],
            },
            "0xFFFF": {
                "name": "MaxRoutine",
                "access": "read",
                "operations": ["start"],
            },
        }
        routines = Routines.model_validate(data)
        assert 0x0000 in routines
        assert 0xFFFF in routines

    def test_reject_out_of_range_routine_id(self) -> None:
        """Should reject routine ID > 0xFFFF."""
        data = {
            "0x10000": {
                "name": "Invalid",
                "access": "read",
                "operations": ["start"],
            },
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            Routines.model_validate(data)
        assert "out of range" in str(exc_info.value).lower()

    def test_reject_negative_routine_id(self) -> None:
        """Should reject negative routine ID."""
        data = {
            -1: {
                "name": "Invalid",
                "access": "read",
                "operations": ["start"],
            },
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            Routines.model_validate(data)
        assert "out of range" in str(exc_info.value).lower()

    def test_reject_non_dict(self) -> None:
        """Should reject non-dict input."""
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            Routines.model_validate([])  # type: ignore[arg-type]
        assert "must be a dictionary" in str(exc_info.value).lower()

    def test_empty_routines(self) -> None:
        """Should accept empty routines dict."""
        routines = Routines.model_validate({})
        assert len(routines) == 0


class TestRoutinesInRoot:
    """Tests for routines integrated with root model."""

    def test_routines_in_document(self) -> None:
        """Should parse routines in full document."""
        from yaml_to_mdd.models.root import DiagnosticDescription

        data = {
            "schema": "opensovd.cda.diagdesc/v1",
            "meta": {
                "author": "Test",
                "domain": "Test",
                "created": "2024-01-01",
                "revision": "1.0.0",
                "description": "Test",
            },
            "ecu": {
                "id": "TEST",
                "name": "Test ECU",
                "addressing": {"can": {}},
            },
            "sessions": {"default": {"id": "0x01"}},
            "services": {},
            "access_patterns": {
                "programming_write": {
                    "sessions": ["programming"],
                    "security": ["level_1"],
                    "authentication": "none",
                },
            },
            "routines": {
                "0xFF00": {
                    "name": "EraseMemory",
                    "description": "Erase flash memory",
                    "access": "programming_write",
                    "operations": ["start", "result"],
                    "parameters": {
                        "start": {
                            "input": [
                                {"name": "address", "type": "u32"},
                                {"name": "size", "type": "u32"},
                            ],
                        },
                    },
                },
            },
        }

        doc = DiagnosticDescription.model_validate(data)
        assert doc.routines is not None
        assert 0xFF00 in doc.routines
        assert doc.routines[0xFF00].name == "EraseMemory"
        assert doc.routines[0xFF00].supports_start() is True
        assert doc.routines[0xFF00].supports_result() is True
        assert doc.routines[0xFF00].supports_stop() is False

    def test_routines_none_by_default(self) -> None:
        """Should default routines to None when not provided."""
        from yaml_to_mdd.models.root import DiagnosticDescription

        data = {
            "schema": "opensovd.cda.diagdesc/v1",
            "meta": {
                "author": "Test",
                "domain": "Test",
                "created": "2024-01-01",
                "revision": "1.0.0",
                "description": "Test",
            },
            "ecu": {
                "id": "TEST",
                "name": "Test ECU",
                "addressing": {"can": {}},
            },
            "sessions": {"default": {"id": "0x01"}},
            "services": {},
        }

        doc = DiagnosticDescription.model_validate(data)
        assert doc.routines is None

    def test_multiple_routines_in_document(self) -> None:
        """Should parse multiple routines in document."""
        from yaml_to_mdd.models.root import DiagnosticDescription

        data = {
            "schema": "opensovd.cda.diagdesc/v1",
            "meta": {
                "author": "Test",
                "domain": "Test",
                "created": "2024-01-01",
                "revision": "1.0.0",
                "description": "Test",
            },
            "ecu": {
                "id": "TEST",
                "name": "Test ECU",
                "addressing": {"can": {}},
            },
            "sessions": {"default": {"id": "0x01"}},
            "services": {},
            "routines": {
                "0xFF00": {
                    "name": "EraseMemory",
                    "access": "prog",
                    "operations": ["start"],
                },
                "0xFF01": {
                    "name": "CheckPreconditions",
                    "access": "ext",
                    "operations": ["start", "result"],
                },
                "0xFF02": {
                    "name": "LongTest",
                    "access": "ext",
                    "operations": ["start", "stop", "result"],
                },
            },
        }

        doc = DiagnosticDescription.model_validate(data)
        assert doc.routines is not None
        assert len(doc.routines) == 3
        assert doc.routines[0xFF00].name == "EraseMemory"
        assert doc.routines[0xFF01].name == "CheckPreconditions"
        assert doc.routines[0xFF02].name == "LongTest"
        assert doc.routines[0xFF02].supports_stop() is True


class TestRoutineParametersCombinations:
    """Additional tests for parameter combinations."""

    def test_start_with_no_response(self) -> None:
        """Should accept start request without response params."""
        routine = RoutineDefinition(
            name="SimpleStart",
            access="read",
            operations=["start"],
            parameters=RoutineParameters(
                start=RoutineOperationParams(
                    input=[RoutineParameter(name="param", type="u8")],
                ),
            ),
        )
        assert routine.parameters is not None
        assert routine.parameters.start is not None
        assert routine.parameters.start.input is not None
        assert routine.parameters.start.output is None

    def test_response_only(self) -> None:
        """Should accept response-only parameters."""
        routine = RoutineDefinition(
            name="StatusCheck",
            access="read",
            operations=["start", "result"],
            parameters=RoutineParameters(
                start=RoutineOperationParams(
                    output=[RoutineParameter(name="immediate", type="u8")],
                ),
                result=RoutineOperationParams(
                    output=[RoutineParameter(name="final", type="u16")],
                ),
            ),
        )
        assert routine.parameters is not None
        assert routine.parameters.start is not None
        assert routine.parameters.start.input is None
        assert routine.parameters.start.output is not None
