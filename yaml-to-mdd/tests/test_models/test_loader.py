"""Tests for YAML/JSON loader utilities."""

from pathlib import Path
from textwrap import dedent

import pytest
from yaml_to_mdd.models.loader import (
    LoaderError,
    load_yaml_file,
    validate_diagnostic_description,
)


class TestLoadYamlFile:
    """Tests for load_yaml_file function."""

    def test_load_valid_yaml(self, tmp_path: Path) -> None:
        """Should load valid YAML file."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value\nnumber: 42")

        data = load_yaml_file(yaml_file)
        assert data == {"key": "value", "number": 42}

    def test_load_valid_json(self, tmp_path: Path) -> None:
        """Should load valid JSON file."""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": "value", "number": 42}')

        data = load_yaml_file(json_file)
        assert data == {"key": "value", "number": 42}

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Should raise LoaderError for missing file."""
        with pytest.raises(LoaderError, match="File not found"):
            load_yaml_file(tmp_path / "nonexistent.yaml")

    def test_unsupported_extension(self, tmp_path: Path) -> None:
        """Should raise LoaderError for unsupported extension."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("content")

        with pytest.raises(LoaderError, match="Unsupported file extension"):
            load_yaml_file(txt_file)

    def test_empty_file(self, tmp_path: Path) -> None:
        """Should raise LoaderError for empty file."""
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")

        with pytest.raises(LoaderError, match="File is empty"):
            load_yaml_file(empty_file)

    def test_invalid_yaml_syntax(self, tmp_path: Path) -> None:
        """Should raise LoaderError for invalid YAML."""
        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text("key: [unclosed bracket")

        with pytest.raises(LoaderError, match="YAML parsing error"):
            load_yaml_file(invalid_file)

    def test_non_dict_root(self, tmp_path: Path) -> None:
        """Should raise LoaderError if root is not a dict."""
        list_file = tmp_path / "list.yaml"
        list_file.write_text("- item1\n- item2")

        with pytest.raises(LoaderError, match="Expected dictionary"):
            load_yaml_file(list_file)


class TestValidateDiagnosticDescription:
    """Tests for validate_diagnostic_description function."""

    def test_valid_file_returns_empty_list(self, tmp_path: Path) -> None:
        """Should return empty list for valid file."""
        yaml_content = dedent(
            """
            schema: opensovd.cda.diagdesc/v1
            meta:
              author: Test Author
              domain: Test Domain
              created: "2024-01-15"
              revision: "1.0.0"
              description: Test description
            ecu:
              id: ECM_V1
              name: Engine Control Module
              addressing:
                doip:
                  ip: "192.168.1.100"
                  logical_address: "0x0010"
                  tester_address: "0x0F00"
            sessions: {}
            services: {}
            access_patterns: {}
        """
        )
        yaml_file = tmp_path / "valid.yaml"
        yaml_file.write_text(yaml_content)

        errors = validate_diagnostic_description(yaml_file)
        assert errors == []

    def test_invalid_file_returns_errors(self, tmp_path: Path) -> None:
        """Should return error list for invalid file."""
        yaml_content = dedent(
            """
            schema: invalid/v1
            meta:
              author: Test Author
              domain: Test Domain
              created: "2024-01-15"
              revision: "1.0.0"
              description: Test description
            ecu:
              id: ECM_V1
              name: Engine Control Module
              addressing:
                doip:
                  ip: "192.168.1.100"
                  logical_address: "0x0010"
                  tester_address: "0x0F00"
            sessions: {}
            services: {}
            access_patterns: {}
        """
        )
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(yaml_content)

        errors = validate_diagnostic_description(yaml_file)
        assert len(errors) > 0
        assert any("schema" in e for e in errors)

    def test_missing_file_returns_error(self, tmp_path: Path) -> None:
        """Should return error for missing file."""
        errors = validate_diagnostic_description(tmp_path / "missing.yaml")
        assert len(errors) == 1
        assert "not found" in errors[0].lower()
