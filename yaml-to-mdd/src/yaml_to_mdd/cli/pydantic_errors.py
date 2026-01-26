"""Translate Pydantic errors to user-friendly messages."""

from __future__ import annotations

from pydantic_core import ErrorDetails

# Translation map for Pydantic error types
ERROR_TRANSLATIONS: dict[str, str] = {
    "missing": "This field is required but was not provided",
    "extra_forbidden": "This field is not allowed in this context",
    "string_type": "Must be a string",
    "int_type": "Must be an integer",
    "bool_type": "Must be true or false",
    "list_type": "Must be a list",
    "dict_type": "Must be an object/dictionary",
    "literal_error": "Must be one of the allowed values",
    "value_error": "Invalid value",
    "json_invalid": "Invalid JSON format",
    "string_pattern_mismatch": "Does not match the required pattern",
    "string_too_short": "String is too short",
    "string_too_long": "String is too long",
    "greater_than": "Value is too small",
    "less_than": "Value is too large",
    "url_scheme": "Invalid URL scheme",
}


def translate_pydantic_error(error: ErrorDetails) -> str:
    """Translate a Pydantic error to a user-friendly message.

    Args:
    ----
        error: The Pydantic error details.

    Returns:
    -------
        User-friendly error message.

    """
    error_type = error["type"]
    msg = error["msg"]
    ctx = error.get("ctx", {})

    # Ensure ctx is a dict (it can be None)
    if ctx is None:
        ctx = {}

    # Check for specific translations, fallback to Pydantic's message
    base_msg = ERROR_TRANSLATIONS.get(error_type, msg)

    # Add context-specific details
    if error_type == "literal_error":
        expected = ctx.get("expected", "unknown")
        base_msg = f"Must be one of: {expected}"

    elif error_type == "string_pattern_mismatch":
        pattern = ctx.get("pattern", "")
        base_msg = f"Does not match pattern: {pattern}"

    elif error_type == "string_too_short":
        min_length = ctx.get("min_length", 0)
        base_msg = f"Must be at least {min_length} characters"

    elif error_type == "string_too_long":
        max_length = ctx.get("max_length", 0)
        base_msg = f"Must be at most {max_length} characters"

    elif error_type == "greater_than":
        gt = ctx.get("gt", 0)
        base_msg = f"Must be greater than {gt}"

    elif error_type == "less_than":
        lt = ctx.get("lt", 0)
        base_msg = f"Must be less than {lt}"

    return base_msg


def format_pydantic_location(loc: tuple[str | int, ...]) -> str:
    """Format Pydantic location tuple to readable path.

    Args:
    ----
        loc: Location tuple from Pydantic error.

    Returns:
    -------
        Formatted path string.

    """
    parts: list[str] = []
    for part in loc:
        if isinstance(part, int):
            parts.append(f"[{part}]")
        else:
            if parts:
                parts.append(".")
            parts.append(str(part))

    return "".join(parts)


def get_suggestion_for_error(error: ErrorDetails) -> str | None:
    """Get a suggestion for how to fix the error.

    Args:
    ----
        error: The Pydantic error details.

    Returns:
    -------
        Suggestion string or None.

    """
    error_type = error["type"]
    ctx = error.get("ctx", {})

    # Ensure ctx is a dict
    if ctx is None:
        ctx = {}

    suggestions: dict[str, str] = {
        "missing": "Add the required field to your YAML",
        "extra_forbidden": "Remove this field or check for typos",
        "literal_error": (
            f"Use one of the allowed values: " f"{ctx.get('expected', 'check documentation')}"
        ),
        "string_pattern_mismatch": ("Check the format requirements in the documentation"),
        "json_invalid": "Validate your YAML syntax with a YAML validator",
    }

    return suggestions.get(error_type)
