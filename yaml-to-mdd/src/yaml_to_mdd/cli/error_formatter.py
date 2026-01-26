"""Error message formatting with Rich."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

if TYPE_CHECKING:
    from yaml_to_mdd.validation.errors import (
        ValidationIssue,
        ValidationLocation,
        ValidationResult,
    )


class ErrorFormatter:
    """Formats validation errors for terminal display."""

    def __init__(
        self,
        console: Console | None = None,
        show_context: bool = True,
        max_context_lines: int = 3,
    ) -> None:
        """Initialize formatter.

        Args:
        ----
            console: Rich Console for output.
            show_context: Whether to show source context.
            max_context_lines: Max lines of context to show.

        """
        self.console = console or Console(stderr=True)
        self.show_context = show_context
        self.max_context_lines = max_context_lines

    def format_validation_result(
        self,
        result: ValidationResult,
        source_path: Path | None = None,
        source_content: str | None = None,
    ) -> None:
        """Format and print validation result.

        Args:
        ----
            result: The validation result to format.
            source_path: Path to source file (for display).
            source_content: Source content for context snippets.

        """
        if result.is_valid and not result.warnings:
            self._print_success("Validation passed")
            return

        # Summary panel
        error_count = len(result.errors)
        warning_count = len(result.warnings)

        summary = self._build_summary(error_count, warning_count, source_path)
        self.console.print(summary)
        self.console.print()

        # Print errors first
        for issue in result.errors:
            self._print_issue(issue, source_content, "red")

        # Then warnings
        for issue in result.warnings:
            self._print_issue(issue, source_content, "yellow")

        # Final count
        self.console.print()
        if error_count > 0:
            self.console.print(f"[red bold]✗ {error_count} error(s)[/red bold]", end="")
        if warning_count > 0:
            if error_count > 0:
                self.console.print(", ", end="")
            self.console.print(f"[yellow]{warning_count} warning(s)[/yellow]", end="")
        self.console.print()

    def _build_summary(
        self,
        errors: int,
        warnings: int,
        source_path: Path | None,
    ) -> Panel:
        """Build summary panel."""
        title = "Validation Failed" if errors > 0 else "Validation Warnings"
        style = "red" if errors > 0 else "yellow"

        content = Text()
        if source_path:
            content.append(f"File: {source_path}\n", style="dim")

        if errors > 0:
            content.append(f"Errors: {errors}", style="red bold")
        if warnings > 0:
            if errors > 0:
                content.append("  ")
            content.append(f"Warnings: {warnings}", style="yellow")

        return Panel(content, title=title, border_style=style)

    def _print_issue(
        self,
        issue: ValidationIssue,
        source_content: str | None,
        color: str,
    ) -> None:
        """Print a single issue."""
        # Header line
        severity = issue.severity.value.upper()
        self.console.print(
            f"[{color} bold]{severity}[/{color} bold] "
            f"[{color}][{issue.code}][/{color}] "
            f"{issue.message}"
        )

        # Location
        if issue.location:
            self.console.print(f"  [dim]at {issue.location}[/dim]")

        # Source context
        if self.show_context and source_content and issue.location:
            context = self._get_source_context(source_content, issue.location)
            if context:
                self.console.print(context)

        # Suggestion
        if issue.suggestion:
            self.console.print(f"  [green]💡 {issue.suggestion}[/green]")

        self.console.print()

    def _get_source_context(
        self,
        source: str,
        location: ValidationLocation,
    ) -> Syntax | None:
        """Get source context around the error location."""
        if location.line is None:
            return None

        lines = source.splitlines()
        line_no = location.line - 1  # Convert to 0-indexed

        if line_no < 0 or line_no >= len(lines):
            return None

        # Get context lines
        start = max(0, line_no - self.max_context_lines)
        end = min(len(lines), line_no + self.max_context_lines + 1)

        context_lines = lines[start:end]
        context = "\n".join(context_lines)

        return Syntax(
            context,
            "yaml",
            line_numbers=True,
            start_line=start + 1,
            highlight_lines={location.line},
            theme="monokai",
        )

    def _print_success(self, message: str) -> None:
        """Print success message."""
        self.console.print(f"[green]✓ {message}[/green]")


class ErrorTree:
    """Display errors as a tree structure grouped by category."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize error tree formatter.

        Args:
        ----
            console: Rich Console for output.

        """
        self.console = console or Console(stderr=True)

    def print_result(self, result: ValidationResult) -> None:
        """Print validation result as tree."""
        tree = Tree("[bold]Validation Issues[/bold]")

        # Group by path prefix
        by_section: dict[str, list[ValidationIssue]] = {}

        for issue in result.issues:
            section = issue.location.path.split(".")[0] if issue.location else "general"
            by_section.setdefault(section, []).append(issue)

        for section, issues in sorted(by_section.items()):
            section_node = tree.add(f"[cyan]{section}[/cyan] ({len(issues)} issues)")

            for issue in issues:
                color = "red" if issue.severity.value == "error" else "yellow"
                section_node.add(f"[{color}]{issue.code}[/{color}] {issue.message}")

        self.console.print(tree)


class ErrorTable:
    """Display errors as a table."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize error table formatter.

        Args:
        ----
            console: Rich Console for output.

        """
        self.console = console or Console(stderr=True)

    def print_result(self, result: ValidationResult) -> None:
        """Print validation result as table."""
        table = Table(title="Validation Issues")

        table.add_column("Code", style="cyan", width=6)
        table.add_column("Severity", width=8)
        table.add_column("Location", style="dim")
        table.add_column("Message")

        for issue in result.issues:
            severity_style = "red" if issue.severity.value == "error" else "yellow"
            severity = f"[{severity_style}]{issue.severity.value.upper()}[/{severity_style}]"

            location = str(issue.location) if issue.location else "-"

            table.add_row(
                issue.code,
                severity,
                location,
                issue.message,
            )

        self.console.print(table)
