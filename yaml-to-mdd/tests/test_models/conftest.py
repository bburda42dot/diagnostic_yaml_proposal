"""Shared test fixtures for model tests."""

from typing import Any

import pytest


@pytest.fixture
def valid_meta() -> dict[str, Any]:
    """Return valid meta section data."""
    return {
        "author": "Test Author",
        "domain": "Test Domain",
        "created": "2024-01-15",
        "revision": "1.0.0",
        "description": "Test description",
    }


@pytest.fixture
def valid_ecu() -> dict[str, Any]:
    """Return valid ECU section data."""
    return {
        "id": "ECM_V1",
        "name": "Engine Control Module",
        "addressing": {
            "doip": {
                "ip": "192.168.1.100",
                "logical_address": "0x0010",
                "tester_address": "0x0F00",
            }
        },
    }


@pytest.fixture
def valid_base_data(valid_meta: dict[str, Any], valid_ecu: dict[str, Any]) -> dict[str, Any]:
    """Return minimal valid DiagnosticDescription data."""
    return {
        "schema": "opensovd.cda.diagdesc/v1",
        "meta": valid_meta,
        "ecu": valid_ecu,
        "sessions": {},
        "services": {},
        "access_patterns": {},
    }
