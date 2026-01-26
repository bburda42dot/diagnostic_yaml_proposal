"""Fixtures for converter tests."""

from typing import Any

import pytest


@pytest.fixture
def valid_base_data() -> dict[str, Any]:
    """Return valid base data for creating DiagnosticDescription."""
    return {
        "schema": "opensovd.cda.diagdesc/v1",
        "meta": {
            "author": "Test Author",
            "domain": "Powertrain",
            "created": "2024-01-01",
            "revision": "1.0.0",
            "description": "Test ECU description",
        },
        "ecu": {
            "id": "ECM_V1",
            "name": "Engine Control Module",
            "addressing": {"can": {}},
        },
        "sessions": {
            "default": {"id": "0x01"},
            "programming": {"id": "0x02"},
            "extended": {"id": "0x03"},
        },
        "services": {
            "diagnosticSessionControl": {"enabled": True},
            "readDataByIdentifier": {"enabled": True},
            "writeDataByIdentifier": {"enabled": True},
        },
        "access_patterns": {
            "standard_read": {
                "sessions": ["default", "extended"],
                "security": "none",
                "authentication": "none",
            },
        },
    }


@pytest.fixture
def valid_base_data_with_security(valid_base_data: dict[str, Any]) -> dict[str, Any]:
    """Return base data with security levels."""
    return {
        **valid_base_data,
        "security": {
            "level1": {
                "level": 1,
                "algorithm": "xor",
            },
        },
    }
