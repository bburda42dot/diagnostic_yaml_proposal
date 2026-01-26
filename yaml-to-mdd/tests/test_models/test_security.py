"""Tests for security section models."""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError
from yaml_to_mdd.models.security import Security, SecurityLevel


class TestSecurityLevel:
    """Tests for SecurityLevel model."""

    def test_minimal_security_level(self) -> None:
        """Should accept minimal security level with all required fields."""
        level = SecurityLevel(
            level=1,
            seed_request=0x01,
            key_send=0x02,
            seed_size=4,
            key_size=4,
            algorithm="SecurityAlgo_XOR",
            max_attempts=3,
            delay_on_fail_ms=10000,
            allowed_sessions=["extended"],
        )
        assert level.level == 1
        assert level.seed_request == 0x01
        assert level.key_send == 0x02
        assert level.algorithm == "SecurityAlgo_XOR"

    def test_security_level_hex_strings(self) -> None:
        """Should accept hex strings for seed_request and key_send."""
        level = SecurityLevel(
            level=1,
            seed_request="0x01",  # type: ignore[arg-type]
            key_send="0x02",  # type: ignore[arg-type]
            seed_size=4,
            key_size=4,
            algorithm="SecurityAlgo_XOR",
            max_attempts=3,
            delay_on_fail_ms=10000,
            allowed_sessions=["extended"],
        )
        assert level.seed_request == 0x01
        assert level.key_send == 0x02

    def test_security_level_2(self) -> None:
        """Should accept level 2 configuration."""
        level = SecurityLevel(
            level=2,
            seed_request=0x03,  # Next odd after 0x01
            key_send=0x04,  # Next even after 0x02
            seed_size=8,
            key_size=8,
            algorithm="SecurityAlgo_AES128",
            max_attempts=3,
            delay_on_fail_ms=30000,
            allowed_sessions=["programming"],
        )
        assert level.level == 2
        assert level.seed_request == 0x03
        assert level.key_send == 0x04

    def test_multiple_allowed_sessions(self) -> None:
        """Should accept multiple allowed sessions."""
        level = SecurityLevel(
            level=1,
            seed_request=0x01,
            key_send=0x02,
            seed_size=4,
            key_size=4,
            algorithm="XOR",
            max_attempts=3,
            delay_on_fail_ms=10000,
            allowed_sessions=["extended", "programming"],
        )
        assert len(level.allowed_sessions) == 2
        assert "extended" in level.allowed_sessions
        assert "programming" in level.allowed_sessions

    def test_optional_fields(self) -> None:
        """Should accept optional fields."""
        level = SecurityLevel(
            level=1,
            seed_request=0x01,
            key_send=0x02,
            seed_size=4,
            key_size=4,
            algorithm="XOR",
            max_attempts=3,
            delay_on_fail_ms=10000,
            allowed_sessions=["extended"],
            delay_on_lockout_ms=60000,
            power_cycle_resets=True,
        )
        assert level.delay_on_lockout_ms == 60000
        assert level.power_cycle_resets is True

    def test_optional_fields_default_none(self) -> None:
        """Should default optional fields to None."""
        level = SecurityLevel(
            level=1,
            seed_request=0x01,
            key_send=0x02,
            seed_size=4,
            key_size=4,
            algorithm="XOR",
            max_attempts=3,
            delay_on_fail_ms=10000,
            allowed_sessions=["extended"],
        )
        assert level.delay_on_lockout_ms is None
        assert level.power_cycle_resets is None

    def test_reject_even_seed_request(self) -> None:
        """Should reject even seed_request value."""
        with pytest.raises(ValidationError) as exc_info:
            SecurityLevel(
                level=1,
                seed_request=0x02,  # Even - invalid!
                key_send=0x02,
                seed_size=4,
                key_size=4,
                algorithm="XOR",
                max_attempts=3,
                delay_on_fail_ms=10000,
                allowed_sessions=["extended"],
            )
        assert "seed_request must be odd" in str(exc_info.value)

    def test_reject_odd_key_send(self) -> None:
        """Should reject odd key_send value."""
        with pytest.raises(ValidationError) as exc_info:
            SecurityLevel(
                level=1,
                seed_request=0x01,
                key_send=0x03,  # Odd - invalid!
                seed_size=4,
                key_size=4,
                algorithm="XOR",
                max_attempts=3,
                delay_on_fail_ms=10000,
                allowed_sessions=["extended"],
            )
        assert "key_send must be even" in str(exc_info.value)

    def test_reject_empty_allowed_sessions(self) -> None:
        """Should reject empty allowed_sessions list."""
        with pytest.raises(ValidationError):
            SecurityLevel(
                level=1,
                seed_request=0x01,
                key_send=0x02,
                seed_size=4,
                key_size=4,
                algorithm="XOR",
                max_attempts=3,
                delay_on_fail_ms=10000,
                allowed_sessions=[],  # Empty - invalid!
            )

    def test_reject_zero_seed_size(self) -> None:
        """Should reject zero seed_size."""
        with pytest.raises(ValidationError):
            SecurityLevel(
                level=1,
                seed_request=0x01,
                key_send=0x02,
                seed_size=0,  # Zero - invalid!
                key_size=4,
                algorithm="XOR",
                max_attempts=3,
                delay_on_fail_ms=10000,
                allowed_sessions=["extended"],
            )

    def test_reject_zero_key_size(self) -> None:
        """Should reject zero key_size."""
        with pytest.raises(ValidationError):
            SecurityLevel(
                level=1,
                seed_request=0x01,
                key_send=0x02,
                seed_size=4,
                key_size=0,  # Zero - invalid!
                algorithm="XOR",
                max_attempts=3,
                delay_on_fail_ms=10000,
                allowed_sessions=["extended"],
            )

    def test_reject_empty_algorithm(self) -> None:
        """Should reject empty algorithm string."""
        with pytest.raises(ValidationError):
            SecurityLevel(
                level=1,
                seed_request=0x01,
                key_send=0x02,
                seed_size=4,
                key_size=4,
                algorithm="",  # Empty - invalid!
                max_attempts=3,
                delay_on_fail_ms=10000,
                allowed_sessions=["extended"],
            )

    def test_reject_zero_max_attempts(self) -> None:
        """Should reject zero max_attempts."""
        with pytest.raises(ValidationError):
            SecurityLevel(
                level=1,
                seed_request=0x01,
                key_send=0x02,
                seed_size=4,
                key_size=4,
                algorithm="XOR",
                max_attempts=0,  # Zero - invalid!
                delay_on_fail_ms=10000,
                allowed_sessions=["extended"],
            )

    def test_reject_negative_delay(self) -> None:
        """Should reject negative delay_on_fail_ms."""
        with pytest.raises(ValidationError):
            SecurityLevel(
                level=1,
                seed_request=0x01,
                key_send=0x02,
                seed_size=4,
                key_size=4,
                algorithm="XOR",
                max_attempts=3,
                delay_on_fail_ms=-1000,  # Negative - invalid!
                allowed_sessions=["extended"],
            )

    def test_reject_extra_fields(self) -> None:
        """Should reject extra fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            SecurityLevel(
                level=1,
                seed_request=0x01,
                key_send=0x02,
                seed_size=4,
                key_size=4,
                algorithm="XOR",
                max_attempts=3,
                delay_on_fail_ms=10000,
                allowed_sessions=["extended"],
                unknown_field="value",  # type: ignore[call-arg]
            )


class TestSecurityLevelSubfunctionPairs:
    """Tests for valid subfunction pairs."""

    @pytest.mark.parametrize(
        ("seed", "key"),
        [
            (0x01, 0x02),  # Level 1
            (0x03, 0x04),  # Level 2
            (0x05, 0x06),  # Level 3
            (0x11, 0x12),  # Extended level
            (0x61, 0x62),  # OEM level
            (0xFF, 0xFE),  # Special case - odd max, even below
        ],
    )
    def test_valid_subfunction_pairs(self, seed: int, key: int) -> None:
        """Should accept valid odd/even subfunction pairs."""
        level = SecurityLevel(
            level=1,
            seed_request=seed,
            key_send=key,
            seed_size=4,
            key_size=4,
            algorithm="XOR",
            max_attempts=3,
            delay_on_fail_ms=10000,
            allowed_sessions=["extended"],
        )
        assert level.seed_request == seed
        assert level.key_send == key

    @pytest.mark.parametrize(
        ("seed", "key", "error_field"),
        [
            (0x02, 0x02, "seed_request"),  # Even seed
            (0x01, 0x03, "key_send"),  # Odd key
            (0x00, 0x02, "seed_request"),  # Zero is even
            (0xFE, 0xFE, "seed_request"),  # Even seed
        ],
    )
    def test_invalid_subfunction_pairs(self, seed: int, key: int, error_field: str) -> None:
        """Should reject invalid subfunction pairs."""
        with pytest.raises(ValidationError) as exc_info:
            SecurityLevel(
                level=1,
                seed_request=seed,
                key_send=key,
                seed_size=4,
                key_size=4,
                algorithm="XOR",
                max_attempts=3,
                delay_on_fail_ms=10000,
                allowed_sessions=["extended"],
            )
        assert error_field in str(exc_info.value)


class TestSecurity:
    """Tests for Security dict type."""

    def test_parse_security_dict(self) -> None:
        """Should parse dictionary of security levels."""
        data = {
            "level_1": {
                "level": 1,
                "seed_request": "0x01",
                "key_send": "0x02",
                "seed_size": 4,
                "key_size": 4,
                "algorithm": "XOR",
                "max_attempts": 3,
                "delay_on_fail_ms": 10000,
                "allowed_sessions": ["extended"],
            },
            "level_2": {
                "level": 2,
                "seed_request": "0x03",
                "key_send": "0x04",
                "seed_size": 8,
                "key_size": 8,
                "algorithm": "AES128",
                "max_attempts": 3,
                "delay_on_fail_ms": 30000,
                "allowed_sessions": ["programming"],
            },
        }

        adapter = TypeAdapter(Security)
        security = adapter.validate_python(data)

        assert len(security) == 2
        assert "level_1" in security
        assert "level_2" in security
        assert security["level_1"].level == 1
        assert security["level_2"].level == 2

    def test_empty_security_dict(self) -> None:
        """Should accept empty security dict."""
        adapter = TypeAdapter(Security)
        security = adapter.validate_python({})

        assert len(security) == 0


class TestSecurityInRoot:
    """Tests for security integrated with root model."""

    def test_security_in_document(self) -> None:
        """Should parse security in full document."""
        from yaml_to_mdd.models.root import DiagnosticDescription

        data = {
            "schema": "opensovd.cda.diagdesc/v1",
            "meta": {
                "author": "Test",
                "domain": "Test",
                "created": "2024-01-01",
                "revision": "1.0.0",
                "description": "Test",
            },
            "ecu": {
                "id": "TEST",
                "name": "Test ECU",
                "addressing": {"can": {}},
            },
            "sessions": {"default": {"id": "0x01"}},
            "services": {},
            "security": {
                "level_1": {
                    "level": 1,
                    "seed_request": "0x01",
                    "key_send": "0x02",
                    "seed_size": 4,
                    "key_size": 4,
                    "algorithm": "SecurityAlgo_XOR",
                    "max_attempts": 3,
                    "delay_on_fail_ms": 10000,
                    "allowed_sessions": ["extended"],
                },
            },
        }

        doc = DiagnosticDescription.model_validate(data)
        assert doc.security is not None
        assert "level_1" in doc.security
        assert doc.security["level_1"].algorithm == "SecurityAlgo_XOR"

    def test_security_optional(self) -> None:
        """Should allow security to be None."""
        from yaml_to_mdd.models.root import DiagnosticDescription

        data = {
            "schema": "opensovd.cda.diagdesc/v1",
            "meta": {
                "author": "Test",
                "domain": "Test",
                "created": "2024-01-01",
                "revision": "1.0.0",
                "description": "Test",
            },
            "ecu": {
                "id": "TEST",
                "name": "Test ECU",
                "addressing": {"can": {}},
            },
            "sessions": {"default": {"id": "0x01"}},
            "services": {},
        }

        doc = DiagnosticDescription.model_validate(data)
        assert doc.security is None

    def test_security_multiple_levels(self) -> None:
        """Should parse multiple security levels."""
        from yaml_to_mdd.models.root import DiagnosticDescription

        data = {
            "schema": "opensovd.cda.diagdesc/v1",
            "meta": {
                "author": "Test",
                "domain": "Test",
                "created": "2024-01-01",
                "revision": "1.0.0",
                "description": "Test",
            },
            "ecu": {
                "id": "TEST",
                "name": "Test ECU",
                "addressing": {"can": {}},
            },
            "sessions": {"default": {"id": "0x01"}},
            "services": {},
            "security": {
                "oem_level1": {
                    "level": 1,
                    "seed_request": "0x01",
                    "key_send": "0x02",
                    "seed_size": 4,
                    "key_size": 4,
                    "algorithm": "SecurityAlgo_XOR",
                    "max_attempts": 3,
                    "delay_on_fail_ms": 10000,
                    "allowed_sessions": ["extended"],
                },
                "oem_level2": {
                    "level": 2,
                    "seed_request": "0x03",
                    "key_send": "0x04",
                    "seed_size": 8,
                    "key_size": 8,
                    "algorithm": "SecurityAlgo_AES128",
                    "max_attempts": 3,
                    "delay_on_fail_ms": 30000,
                    "allowed_sessions": ["programming"],
                    "delay_on_lockout_ms": 60000,
                    "power_cycle_resets": True,
                },
            },
        }

        doc = DiagnosticDescription.model_validate(data)
        assert doc.security is not None
        assert len(doc.security) == 2
        assert doc.security["oem_level1"].seed_size == 4
        assert doc.security["oem_level2"].seed_size == 8
        assert doc.security["oem_level2"].delay_on_lockout_ms == 60000
