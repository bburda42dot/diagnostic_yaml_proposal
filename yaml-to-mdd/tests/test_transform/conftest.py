"""Shared test fixtures for transform tests."""

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
def valid_sessions() -> dict[str, Any]:
    """Return valid sessions data."""
    return {
        "default": {"id": 1},
        "programming": {"id": 2},
        "extended": {"id": 3},
    }


@pytest.fixture
def valid_services() -> dict[str, Any]:
    """Return valid services configuration."""
    return {
        "readDataByIdentifier": {
            "enabled": True,
        },
        "writeDataByIdentifier": {
            "enabled": True,
        },
        "routineControl": {
            "enabled": True,
        },
    }


@pytest.fixture
def valid_access_patterns() -> dict[str, Any]:
    """Return valid access patterns."""
    return {
        "standard_read": {
            "sessions": "any",
            "security": "none",
            "authentication": "none",
        },
        "extended_write": {
            "sessions": ["extended"],
            "security": "none",
            "authentication": "none",
        },
        "programming_write": {
            "sessions": ["programming"],
            "security": ["level1"],
            "authentication": "none",
        },
    }


@pytest.fixture
def valid_security() -> dict[str, Any]:
    """Return valid security configuration."""
    return {
        "level1": {
            "level": 1,
            "seed_request": 1,
            "key_send": 2,
            "seed_size": 4,
            "key_size": 4,
            "algorithm": "XOR",
            "max_attempts": 3,
            "delay_on_fail_ms": 10000,
            "allowed_sessions": ["extended"],
        },
    }


@pytest.fixture
def valid_base_data(
    valid_meta: dict[str, Any],
    valid_ecu: dict[str, Any],
    valid_sessions: dict[str, Any],
    valid_services: dict[str, Any],
    valid_access_patterns: dict[str, Any],
) -> dict[str, Any]:
    """Return minimal valid DiagnosticDescription data."""
    return {
        "schema": "opensovd.cda.diagdesc/v1",
        "meta": valid_meta,
        "ecu": valid_ecu,
        "sessions": valid_sessions,
        "services": valid_services,
        "access_patterns": valid_access_patterns,
    }


@pytest.fixture
def valid_base_data_with_security(
    valid_base_data: dict[str, Any],
    valid_security: dict[str, Any],
) -> dict[str, Any]:
    """Return valid base data with security section."""
    return {
        **valid_base_data,
        "security": valid_security,
    }
