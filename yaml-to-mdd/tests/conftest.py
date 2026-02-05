"""Pytest configuration and shared fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def minimal_ecu_yaml() -> Path:
    """Return path to minimal-ecu.yml test file."""
    return Path(__file__).parent.parent.parent / "yaml-schema" / "minimal-ecu.yml"


@pytest.fixture
def example_ecm_yaml() -> Path:
    """Return path to example-ecm.yml test file."""
    return Path(__file__).parent.parent.parent / "yaml-schema" / "example-ecm.yml"
