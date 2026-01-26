"""Tests for pydantic error translation."""


from yaml_to_mdd.cli.pydantic_errors import (
    format_pydantic_location,
    get_suggestion_for_error,
    translate_pydantic_error,
)


class TestTranslatePydanticError:
    """Tests for translate_pydantic_error."""

    def test_missing_field_translation(self) -> None:
        """Should translate missing field error."""
        error = {"type": "missing", "msg": "Field required", "loc": ("field",)}

        result = translate_pydantic_error(error)  # type: ignore[arg-type]

        assert "required" in result.lower()

    def test_extra_field_translation(self) -> None:
        """Should translate extra forbidden field error."""
        error = {
            "type": "extra_forbidden",
            "msg": "Extra inputs not allowed",
            "loc": ("extra",),
        }

        result = translate_pydantic_error(error)  # type: ignore[arg-type]

        assert "not allowed" in result.lower()

    def test_literal_error_with_context(self) -> None:
        """Should include expected values for literal error."""
        error = {
            "type": "literal_error",
            "msg": "Input should be...",
            "loc": ("field",),
            "ctx": {"expected": "'a', 'b', or 'c'"},
        }

        result = translate_pydantic_error(error)  # type: ignore[arg-type]

        assert "'a', 'b', or 'c'" in result

    def test_string_too_short_with_context(self) -> None:
        """Should include min length for string_too_short error."""
        error = {
            "type": "string_too_short",
            "msg": "String too short",
            "loc": ("field",),
            "ctx": {"min_length": 5},
        }

        result = translate_pydantic_error(error)  # type: ignore[arg-type]

        assert "5" in result

    def test_unknown_error_uses_fallback(self) -> None:
        """Should use original message for unknown error types."""
        error = {
            "type": "unknown_type",
            "msg": "Custom error message",
            "loc": ("field",),
        }

        result = translate_pydantic_error(error)  # type: ignore[arg-type]

        assert "Custom error message" in result

    def test_handles_none_context(self) -> None:
        """Should handle None context gracefully."""
        error = {
            "type": "missing",
            "msg": "Field required",
            "loc": ("field",),
            "ctx": None,
        }

        result = translate_pydantic_error(error)  # type: ignore[arg-type]

        assert "required" in result.lower()


class TestFormatPydanticLocation:
    """Tests for format_pydantic_location."""

    def test_simple_path(self) -> None:
        """Should format simple path."""
        loc = ("meta", "author")

        result = format_pydantic_location(loc)

        assert result == "meta.author"

    def test_path_with_index(self) -> None:
        """Should format path with array index."""
        loc = ("dids", 0, "type")

        result = format_pydantic_location(loc)

        assert result == "dids[0].type"

    def test_nested_indices(self) -> None:
        """Should format nested indices correctly."""
        loc = ("routines", 0, "parameters", 1)

        result = format_pydantic_location(loc)

        assert result == "routines[0].parameters[1]"

    def test_single_element(self) -> None:
        """Should format single element."""
        loc = ("field",)

        result = format_pydantic_location(loc)

        assert result == "field"

    def test_empty_location(self) -> None:
        """Should handle empty location."""
        loc: tuple[str | int, ...] = ()

        result = format_pydantic_location(loc)

        assert result == ""


class TestGetSuggestionForError:
    """Tests for get_suggestion_for_error."""

    def test_missing_field_suggestion(self) -> None:
        """Should provide suggestion for missing field."""
        error = {"type": "missing", "msg": "Field required", "loc": ("field",)}

        result = get_suggestion_for_error(error)  # type: ignore[arg-type]

        assert result is not None
        assert "YAML" in result

    def test_extra_field_suggestion(self) -> None:
        """Should provide suggestion for extra field."""
        error = {"type": "extra_forbidden", "msg": "Extra inputs", "loc": ("field",)}

        result = get_suggestion_for_error(error)  # type: ignore[arg-type]

        assert result is not None
        assert "remove" in result.lower() or "typo" in result.lower()

    def test_no_suggestion_for_unknown(self) -> None:
        """Should return None for unknown error types."""
        error = {"type": "unknown_type", "msg": "Some error", "loc": ("field",)}

        result = get_suggestion_for_error(error)  # type: ignore[arg-type]

        assert result is None
