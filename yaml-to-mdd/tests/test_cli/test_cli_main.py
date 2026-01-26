"""Tests for the CLI module."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner
from yaml_to_mdd import __version__
from yaml_to_mdd.cli import app

if TYPE_CHECKING:
    pass


runner = CliRunner()


class TestVersion:
    """Tests for version option."""

    def test_version_long(self) -> None:
        """Test --version flag."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.stdout

    def test_version_short(self) -> None:
        """Test -v flag."""
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert __version__ in result.stdout

    def test_version_with_command_still_shows_version(self) -> None:
        """Test that --version takes precedence (eager option)."""
        result = runner.invoke(app, ["--version", "validate", "dummy.yaml"])
        assert result.exit_code == 0
        assert __version__ in result.stdout


class TestNoArgs:
    """Tests for no arguments behavior."""

    def test_no_args_shows_help(self) -> None:
        """Test that no arguments shows help."""
        result = runner.invoke(app)
        assert result.exit_code == 0
        assert "yaml-to-mdd" in result.stdout
        assert "validate" in result.stdout
        assert "convert" in result.stdout


class TestValidateCommand:
    """Tests for the validate command."""

    def test_validate_valid_file(self, tmp_path: Path, valid_yaml_content: str) -> None:
        """Test validating a valid file."""
        yaml_file = tmp_path / "valid.yaml"
        yaml_file.write_text(valid_yaml_content)

        result = runner.invoke(app, ["validate", str(yaml_file)])
        assert result.exit_code == 0
        assert "valid" in result.stdout.lower()

    def test_validate_nonexistent_file(self) -> None:
        """Test validating a nonexistent file."""
        result = runner.invoke(app, ["validate", "nonexistent.yaml"])
        assert result.exit_code != 0

    def test_validate_invalid_yaml(self, tmp_path: Path) -> None:
        """Test validating invalid YAML syntax."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("not: valid: yaml: [")

        result = runner.invoke(app, ["validate", str(yaml_file)])
        assert result.exit_code == 1

    def test_validate_invalid_schema(self, tmp_path: Path) -> None:
        """Test validating file that doesn't match schema."""
        yaml_file = tmp_path / "bad_schema.yaml"
        yaml_file.write_text(
            """\
schema: wrong_schema
meta:
  author: test
"""
        )

        result = runner.invoke(app, ["validate", str(yaml_file)])
        assert result.exit_code == 1

    def test_validate_quiet_success(self, tmp_path: Path, valid_yaml_content: str) -> None:
        """Test validate with --quiet on valid file produces no output."""
        yaml_file = tmp_path / "valid.yaml"
        yaml_file.write_text(valid_yaml_content)

        result = runner.invoke(app, ["validate", "--quiet", str(yaml_file)])
        assert result.exit_code == 0
        # Should be minimal output
        assert "✓" not in result.stdout

    def test_validate_quiet_failure(self, tmp_path: Path) -> None:
        """Test validate with --quiet on invalid file still shows errors."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("schema: wrong")

        result = runner.invoke(app, ["validate", "--quiet", str(yaml_file)])
        assert result.exit_code == 1

    def test_validate_with_summary(self, tmp_path: Path, valid_yaml_content: str) -> None:
        """Test validate with --summary shows document summary."""
        yaml_file = tmp_path / "valid.yaml"
        yaml_file.write_text(valid_yaml_content)

        result = runner.invoke(app, ["validate", "--summary", str(yaml_file)])
        assert result.exit_code == 0
        assert "valid" in result.stdout.lower()
        # Summary should include ECU info
        assert "ECU" in result.stdout or "Author" in result.stdout

    def test_validate_short_options(self, tmp_path: Path, valid_yaml_content: str) -> None:
        """Test validate with short options -q -s."""
        yaml_file = tmp_path / "valid.yaml"
        yaml_file.write_text(valid_yaml_content)

        # -q should work
        result = runner.invoke(app, ["validate", "-q", str(yaml_file)])
        assert result.exit_code == 0

        # -s should work (but -q takes precedence in suppressing)
        result = runner.invoke(app, ["validate", "-s", str(yaml_file)])
        assert result.exit_code == 0


class TestConvertCommand:
    """Tests for the convert command."""

    def test_convert_valid_file(self, tmp_path: Path, valid_yaml_content: str) -> None:
        """Test converting a valid file."""
        yaml_file = tmp_path / "valid.yaml"
        yaml_file.write_text(valid_yaml_content)

        result = runner.invoke(app, ["convert", str(yaml_file)])
        # Should succeed and write MDD file
        assert result.exit_code == 0
        assert "wrote" in result.stdout.lower()
        # Output file should exist
        assert (tmp_path / "valid.mdd").exists()

    def test_convert_with_output(self, tmp_path: Path, valid_yaml_content: str) -> None:
        """Test converting with explicit output path."""
        yaml_file = tmp_path / "valid.yaml"
        yaml_file.write_text(valid_yaml_content)
        output_file = tmp_path / "output.mdd"

        result = runner.invoke(app, ["convert", str(yaml_file), "-o", str(output_file)])
        assert result.exit_code == 0

    def test_convert_nonexistent_file(self) -> None:
        """Test converting a nonexistent file."""
        result = runner.invoke(app, ["convert", "nonexistent.yaml"])
        assert result.exit_code != 0

    def test_convert_invalid_yaml(self, tmp_path: Path) -> None:
        """Test converting invalid YAML fails validation."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("not: valid: yaml: [")

        result = runner.invoke(app, ["convert", str(yaml_file)])
        assert result.exit_code == 1
        assert "failed" in result.stdout.lower() or "error" in result.stdout.lower()

    def test_convert_output_exists_no_force(self, tmp_path: Path, valid_yaml_content: str) -> None:
        """Test converting when output file exists without --force."""
        yaml_file = tmp_path / "valid.yaml"
        yaml_file.write_text(valid_yaml_content)
        output_file = tmp_path / "valid.mdd"
        output_file.write_text("existing content")

        result = runner.invoke(app, ["convert", str(yaml_file)])
        assert result.exit_code == 1
        assert "exists" in result.stdout.lower()

    def test_convert_output_exists_with_force(
        self, tmp_path: Path, valid_yaml_content: str
    ) -> None:
        """Test converting when output file exists with --force."""
        yaml_file = tmp_path / "valid.yaml"
        yaml_file.write_text(valid_yaml_content)
        output_file = tmp_path / "valid.mdd"
        output_file.write_text("existing content")

        result = runner.invoke(app, ["convert", str(yaml_file), "--force"])
        assert result.exit_code == 0

    def test_convert_dry_run(self, tmp_path: Path, valid_yaml_content: str) -> None:
        """Test converting with --dry-run doesn't write file."""
        yaml_file = tmp_path / "valid.yaml"
        yaml_file.write_text(valid_yaml_content)

        result = runner.invoke(app, ["convert", str(yaml_file), "--dry-run"])
        assert result.exit_code == 0
        assert "would write" in result.stdout.lower()
        # Output file should not exist
        assert not (tmp_path / "valid.mdd").exists()

    def test_convert_dry_run_skips_existing_check(
        self, tmp_path: Path, valid_yaml_content: str
    ) -> None:
        """Test that --dry-run doesn't care about existing output file."""
        yaml_file = tmp_path / "valid.yaml"
        yaml_file.write_text(valid_yaml_content)
        output_file = tmp_path / "valid.mdd"
        output_file.write_text("existing content")

        result = runner.invoke(app, ["convert", str(yaml_file), "--dry-run"])
        assert result.exit_code == 0

    def test_convert_verbose(self, tmp_path: Path, valid_yaml_content: str) -> None:
        """Test converting with --verbose shows progress."""
        yaml_file = tmp_path / "valid.yaml"
        yaml_file.write_text(valid_yaml_content)

        result = runner.invoke(app, ["convert", str(yaml_file), "--verbose"])
        assert result.exit_code == 0
        # Should show details like Schema/ECU/DOPs
        assert "schema" in result.stdout.lower() or "ecu" in result.stdout.lower()

    def test_convert_short_options(self, tmp_path: Path, valid_yaml_content: str) -> None:
        """Test convert with short options -o -f -V."""
        yaml_file = tmp_path / "valid.yaml"
        yaml_file.write_text(valid_yaml_content)
        output_file = tmp_path / "out.mdd"

        # -o for output
        result = runner.invoke(app, ["convert", str(yaml_file), "-o", str(output_file)])
        assert result.exit_code == 0

        # -f for force
        result = runner.invoke(app, ["convert", str(yaml_file), "-o", str(output_file), "-f"])
        assert result.exit_code == 0

        # -V for verbose
        result = runner.invoke(app, ["convert", str(yaml_file), "-V", "--dry-run"])
        assert result.exit_code == 0


class TestHelpText:
    """Tests for help text."""

    def test_main_help(self) -> None:
        """Test main help text."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "yaml-to-mdd" in result.stdout.lower()
        assert "validate" in result.stdout
        assert "convert" in result.stdout
        assert "info" in result.stdout

    def test_validate_help(self) -> None:
        """Test validate command help."""
        result = runner.invoke(app, ["validate", "--help"])
        assert result.exit_code == 0
        assert "validate" in result.stdout.lower()
        assert "--quiet" in result.stdout
        assert "--summary" in result.stdout

    def test_convert_help(self) -> None:
        """Test convert command help."""
        result = runner.invoke(app, ["convert", "--help"])
        assert result.exit_code == 0
        assert "convert" in result.stdout.lower()
        assert "--output" in result.stdout
        assert "--force" in result.stdout
        assert "--dry-run" in result.stdout
        assert "--verbose" in result.stdout
        assert "--compression" in result.stdout

    def test_info_help(self) -> None:
        """Test info command help."""
        result = runner.invoke(app, ["info", "--help"])
        assert result.exit_code == 0
        assert "info" in result.stdout.lower()


class TestInfoCommand:
    """Tests for the info command."""

    def test_info_yaml_file(self, tmp_path: Path, valid_yaml_content: str) -> None:
        """Test info for YAML file shows document info."""
        yaml_file = tmp_path / "valid.yaml"
        yaml_file.write_text(valid_yaml_content)

        result = runner.invoke(app, ["info", str(yaml_file)])
        assert result.exit_code == 0
        assert "TEST_ECU" in result.stdout
        assert "YAML" in result.stdout or "yaml" in result.stdout.lower()

    def test_info_mdd_file(self, tmp_path: Path, valid_yaml_content: str) -> None:
        """Test info for MDD file shows file contents."""
        yaml_file = tmp_path / "valid.yaml"
        yaml_file.write_text(valid_yaml_content)
        mdd_file = tmp_path / "valid.mdd"

        # First convert to MDD
        runner.invoke(app, ["convert", str(yaml_file), "-o", str(mdd_file)])
        assert mdd_file.exists()

        # Then get info
        result = runner.invoke(app, ["info", str(mdd_file)])
        assert result.exit_code == 0
        assert "MDD" in result.stdout or "mdd" in result.stdout.lower()
        assert "TEST_ECU" in result.stdout

    def test_info_unknown_file_type(self, tmp_path: Path) -> None:
        """Test info for unknown file type fails."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("some content")

        result = runner.invoke(app, ["info", str(txt_file)])
        assert result.exit_code == 1
        assert "unknown" in result.stdout.lower() or "supported" in result.stdout.lower()

    def test_info_nonexistent_file(self) -> None:
        """Test info for nonexistent file fails."""
        result = runner.invoke(app, ["info", "nonexistent.yaml"])
        assert result.exit_code != 0


@pytest.fixture
def valid_yaml_content() -> str:
    """Return valid YAML content for testing.

    Note: This matches the current Pydantic model structure.
    The model will need updates in future tasks to match the full schema.
    """
    return """\
schema: opensovd.cda.diagdesc/v1

meta:
  author: Test Author
  domain: Powertrain
  created: "2025-01-01"
  revision: "1.0.0"
  description: Test diagnostic description

ecu:
  id: TEST_ECU
  name: Test ECU
  default_addressing_mode: physical
  addressing:
    doip:
      ip: "192.168.1.100"
      port: 13400
      logical_address: 0x0100
      tester_address: 0x0001

sessions:
  default:
    id: 0x01
  extended:
    id: 0x03

types:
  test_type:
    base: u8

services:
  diagnosticSessionControl:
    enabled: true
  readDataByIdentifier:
    enabled: true

access_patterns:
  public:
    sessions: any
    security: none
    authentication: none
"""
