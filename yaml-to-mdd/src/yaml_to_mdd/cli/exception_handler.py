"""CLI exception handling."""

from __future__ import annotations

import traceback
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

import typer
from pydantic import ValidationError as PydanticValidationError
from rich.console import Console
from rich.panel import Panel

from yaml_to_mdd.validation.validator import ValidationError

T = TypeVar("T")

console = Console(stderr=True)


def handle_exceptions(
    verbose: bool = False,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Handle exceptions in CLI commands with formatted output.

    Args:
    ----
        verbose: Whether to show full tracebacks.

    Returns:
    -------
        Decorator function.

    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: object, **kwargs: object) -> T:
            try:
                return func(*args, **kwargs)
            except ValidationError as e:
                _handle_validation_error(e, verbose)
                raise typer.Exit(1) from None
            except PydanticValidationError as e:
                _handle_pydantic_error(e, verbose)
                raise typer.Exit(1) from None
            except FileNotFoundError as e:
                _handle_file_error(e, verbose)
                raise typer.Exit(1) from None
            except PermissionError as e:
                _handle_permission_error(e, verbose)
                raise typer.Exit(1) from None
            except Exception as e:
                _handle_generic_error(e, verbose)
                raise typer.Exit(1) from None

        return wrapper

    return decorator


def _handle_validation_error(error: ValidationError, verbose: bool) -> None:
    """Handle semantic validation errors."""
    from yaml_to_mdd.cli.error_formatter import ErrorFormatter

    formatter = ErrorFormatter(console)
    formatter.format_validation_result(error.result)


def _handle_pydantic_error(error: PydanticValidationError, verbose: bool) -> None:
    """Handle Pydantic validation errors."""
    from yaml_to_mdd.cli.pydantic_errors import (
        format_pydantic_location,
        get_suggestion_for_error,
        translate_pydantic_error,
    )

    console.print("[red bold]Schema Validation Failed[/red bold]")
    console.print()

    for err in error.errors():
        location = format_pydantic_location(err["loc"])
        msg = translate_pydantic_error(err)
        suggestion = get_suggestion_for_error(err)

        console.print(f"[red]✗[/red] {location}")
        console.print(f"  {msg}")
        console.print(f"  [dim]({err['type']})[/dim]")

        if suggestion:
            console.print(f"  [green]💡 {suggestion}[/green]")

        console.print()

    if verbose:
        console.print("[dim]Full error:[/dim]")
        console.print(str(error))


def _handle_file_error(error: FileNotFoundError, verbose: bool) -> None:
    """Handle file not found errors."""
    filename = error.filename or "unknown"
    console.print(
        Panel(
            f"[red]File not found: {filename}[/red]\n\n"
            "Please check that the file path is correct.",
            title="Error",
            border_style="red",
        )
    )


def _handle_permission_error(error: PermissionError, verbose: bool) -> None:
    """Handle permission errors."""
    filename = error.filename or "unknown"
    console.print(
        Panel(
            f"[red]Permission denied: {filename}[/red]\n\n" "Check file permissions and try again.",
            title="Error",
            border_style="red",
        )
    )


def _handle_generic_error(error: Exception, verbose: bool) -> None:
    """Handle unexpected errors."""
    console.print(
        Panel(
            f"[red]An unexpected error occurred:[/red]\n{error}",
            title="Error",
            border_style="red",
        )
    )

    if verbose:
        console.print("\n[dim]Traceback:[/dim]")
        console.print(traceback.format_exc())
    else:
        console.print("\n[dim]Use --verbose for full traceback[/dim]")
