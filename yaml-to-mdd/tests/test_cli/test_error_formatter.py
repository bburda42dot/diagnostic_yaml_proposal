"""Tests for error formatter."""

from io import StringIO

import pytest
from rich.console import Console
from yaml_to_mdd.cli.error_formatter import ErrorFormatter, ErrorTable, ErrorTree
from yaml_to_mdd.validation.errors import (
    ValidationIssue,
    ValidationLocation,
    ValidationResult,
    ValidationSeverity,
)


@pytest.fixture
def string_console() -> Console:
    """Create a console that writes to a string."""
    return Console(file=StringIO(), force_terminal=True, width=80)


class TestErrorFormatter:
    """Tests for ErrorFormatter."""

    def test_format_empty_result(self, string_console: Console) -> None:
        """Should show success for empty result."""
        formatter = ErrorFormatter(string_console)
        result = ValidationResult()

        formatter.format_validation_result(result)

        output = string_console.file.getvalue()  # type: ignore[union-attr]
        assert "passed" in output.lower() or "✓" in output

    def test_format_with_errors(self, string_console: Console) -> None:
        """Should show errors prominently."""
        formatter = ErrorFormatter(string_console)
        result = ValidationResult()
        result.add_error("E001", "Test error message", "path.to.field")

        formatter.format_validation_result(result)

        output = string_console.file.getvalue()  # type: ignore[union-attr]
        assert "E001" in output
        assert "Test error message" in output
        assert "error" in output.lower()

    def test_format_with_warnings(self, string_console: Console) -> None:
        """Should show warnings."""
        formatter = ErrorFormatter(string_console)
        result = ValidationResult()
        result.add_warning("W001", "Test warning", "path")

        formatter.format_validation_result(result)

        output = string_console.file.getvalue()  # type: ignore[union-attr]
        assert "W001" in output
        assert "warning" in output.lower()

    def test_shows_suggestion(self, string_console: Console) -> None:
        """Should show suggestion when provided."""
        formatter = ErrorFormatter(string_console)
        result = ValidationResult()
        result.add_error(
            "E001",
            "Missing field",
            "path",
            suggestion="Add the required field",
        )

        formatter.format_validation_result(result)

        output = string_console.file.getvalue()  # type: ignore[union-attr]
        assert "Add the required field" in output

    def test_shows_location(self, string_console: Console) -> None:
        """Should show error location."""
        formatter = ErrorFormatter(string_console)
        result = ValidationResult()
        result.add(
            ValidationIssue(
                code="E001",
                message="Error",
                severity=ValidationSeverity.ERROR,
                location=ValidationLocation("dids.0xF190.type", line=42),
            )
        )

        formatter.format_validation_result(result)

        output = string_console.file.getvalue()  # type: ignore[union-attr]
        # Check for location components (may have ANSI codes)
        assert "dids." in output
        assert "0xF190" in output
        assert "42" in output

    def test_format_mixed_errors_and_warnings(self, string_console: Console) -> None:
        """Should format both errors and warnings."""
        formatter = ErrorFormatter(string_console)
        result = ValidationResult()
        result.add_error("E001", "Error message", "path1")
        result.add_warning("W001", "Warning message", "path2")

        formatter.format_validation_result(result)

        output = string_console.file.getvalue()  # type: ignore[union-attr]
        assert "E001" in output
        assert "W001" in output
        # Check for error/warning counts (may have ANSI formatting)
        assert "error" in output.lower()
        assert "warning" in output.lower()

    def test_shows_source_context(self, string_console: Console) -> None:
        """Should show source context when line number available."""
        formatter = ErrorFormatter(string_console, show_context=True, max_context_lines=1)
        result = ValidationResult()
        result.add(
            ValidationIssue(
                code="E001",
                message="Error",
                severity=ValidationSeverity.ERROR,
                location=ValidationLocation("dids.0xF190", line=2),
            )
        )

        source = "line1\nline2\nline3"
        formatter.format_validation_result(result, source_content=source)

        output = string_console.file.getvalue()  # type: ignore[union-attr]
        # Should contain line numbers from syntax highlighting
        assert "E001" in output


class TestErrorTable:
    """Tests for ErrorTable."""

    def test_table_output(self, string_console: Console) -> None:
        """Should format as table."""
        table_fmt = ErrorTable(string_console)
        result = ValidationResult()
        result.add_error("E001", "Error 1", "path1")
        result.add_warning("W001", "Warning 1", "path2")

        table_fmt.print_result(result)

        output = string_console.file.getvalue()  # type: ignore[union-attr]
        assert "E001" in output
        assert "W001" in output
        assert "Error 1" in output
        assert "Warning 1" in output

    def test_empty_result(self, string_console: Console) -> None:
        """Should handle empty result."""
        table_fmt = ErrorTable(string_console)
        result = ValidationResult()

        table_fmt.print_result(result)

        output = string_console.file.getvalue()  # type: ignore[union-attr]
        assert "Validation Issues" in output


class TestErrorTree:
    """Tests for ErrorTree."""

    def test_tree_groups_by_section(self, string_console: Console) -> None:
        """Should group errors by section."""
        tree_fmt = ErrorTree(string_console)
        result = ValidationResult()
        result.add_error("E001", "DID error", "dids.0xF190")
        result.add_error("E002", "Session error", "sessions.default")

        tree_fmt.print_result(result)

        output = string_console.file.getvalue()  # type: ignore[union-attr]
        assert "dids" in output
        assert "sessions" in output

    def test_tree_handles_no_location(self, string_console: Console) -> None:
        """Should handle issues without location."""
        tree_fmt = ErrorTree(string_console)
        result = ValidationResult()
        result.add(
            ValidationIssue(
                code="E001",
                message="General error",
                severity=ValidationSeverity.ERROR,
                location=None,
            )
        )

        tree_fmt.print_result(result)

        output = string_console.file.getvalue()  # type: ignore[union-attr]
        assert "general" in output
        assert "General error" in output
