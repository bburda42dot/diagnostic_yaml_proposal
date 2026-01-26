"""YAML/JSON file loading utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from yaml_to_mdd.models.root import DiagnosticDescription


class LoaderError(Exception):
    """Error during YAML/JSON file loading."""

    def __init__(self, message: str, path: Path | None = None) -> None:
        """Initialize LoaderError.

        Args:
        ----
            message: Error message describing what went wrong.
            path: Optional path to the file that caused the error.

        """
        self.path = path
        super().__init__(f"{path}: {message}" if path else message)


def load_yaml_file(path: Path) -> dict[str, Any]:
    """Load a YAML or JSON file and return the raw dictionary.

    Args:
    ----
        path: Path to the YAML or JSON file.

    Returns:
    -------
        Parsed dictionary from the file.

    Raises:
    ------
        LoaderError: If the file cannot be loaded or parsed.

    """
    if not path.exists():
        raise LoaderError(f"File not found: {path}", path)

    if not path.is_file():
        raise LoaderError(f"Not a file: {path}", path)

    suffix = path.suffix.lower()
    if suffix not in {".yaml", ".yml", ".json"}:
        raise LoaderError(
            f"Unsupported file extension: {suffix}. Use .yaml, .yml, or .json",
            path,
        )

    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise LoaderError(f"YAML parsing error: {e}", path) from e
    except OSError as e:
        raise LoaderError(f"File read error: {e}", path) from e

    if data is None:
        raise LoaderError("File is empty", path)

    if not isinstance(data, dict):
        raise LoaderError(
            f"Expected dictionary at root level, got {type(data).__name__}",
            path,
        )

    return data


def load_diagnostic_description(path: Path) -> DiagnosticDescription:
    """Load and validate a diagnostic description from a YAML/JSON file.

    Args:
    ----
        path: Path to the diagnostic description file.

    Returns:
    -------
        Validated DiagnosticDescription model instance.

    Raises:
    ------
        LoaderError: If the file cannot be loaded.
        ValidationError: If the file content is invalid.

    """
    data = load_yaml_file(path)

    try:
        return DiagnosticDescription.model_validate(data)
    except ValidationError:
        # Re-raise as-is for now; could wrap with more context
        raise


def validate_diagnostic_description(path: Path) -> list[str]:
    """Validate a diagnostic description file and return list of errors.

    This is a non-throwing version of load_diagnostic_description,
    useful for validation CLI commands.

    Args:
    ----
        path: Path to the diagnostic description file.

    Returns:
    -------
        List of error messages (empty if valid).

    """
    errors: list[str] = []

    try:
        data = load_yaml_file(path)
    except LoaderError as e:
        return [str(e)]

    try:
        DiagnosticDescription.model_validate(data)
    except ValidationError as e:
        for error in e.errors():
            loc = ".".join(str(x) for x in error["loc"])
            msg = error["msg"]
            errors.append(f"{loc}: {msg}")

    return errors
