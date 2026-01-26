"""Pytest configuration and shared fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def minimal_ecu_yaml(fixtures_dir: Path) -> Path:
    """Return path to minimal-ecu.yml test file."""
    return fixtures_dir.parent.parent.parent / "diagnostic_yaml" / "minimal-ecu.yml"


@pytest.fixture
def example_ecm_yaml(fixtures_dir: Path) -> Path:
    """Return path to example-ecm.yml test file."""
    return fixtures_dir.parent.parent.parent / "diagnostic_yaml" / "example-ecm.yml"
