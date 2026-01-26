"""Tests for root DiagnosticDescription model."""

from typing import Any

import pytest
from pydantic import ValidationError
from yaml_to_mdd.models.root import DiagnosticDescription

# Valid meta data for tests
VALID_META = {
    "author": "Test Author",
    "domain": "Test Domain",
    "created": "2024-01-15",
    "revision": "1.0.0",
    "description": "Test description",
}

# Valid ECU data for tests
VALID_ECU = {
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


class TestDiagnosticDescriptionSchema:
    """Tests for schema version validation."""

    def test_accepts_valid_schema_version(self) -> None:
        """Should accept the valid schema version."""
        data = {
            "schema": "opensovd.cda.diagdesc/v1",
            "meta": VALID_META,
            "ecu": VALID_ECU,
            "sessions": {},
            "services": {},
            "access_patterns": {},
        }
        model = DiagnosticDescription.model_validate(data)
        assert model.schema_version == "opensovd.cda.diagdesc/v1"

    def test_rejects_invalid_schema_version(self) -> None:
        """Should reject invalid schema versions."""
        data = {
            "schema": "invalid/v1",
            "meta": VALID_META,
            "ecu": VALID_ECU,
            "sessions": {},
            "services": {},
            "access_patterns": {},
        }
        with pytest.raises(ValidationError) as exc_info:
            DiagnosticDescription.model_validate(data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "schema" in str(errors[0]["loc"])

    def test_rejects_missing_schema(self) -> None:
        """Should reject missing schema field."""
        data = {
            "meta": VALID_META,
            "ecu": VALID_ECU,
            "sessions": {},
            "services": {},
            "access_patterns": {},
        }
        with pytest.raises(ValidationError) as exc_info:
            DiagnosticDescription.model_validate(data)

        errors = exc_info.value.errors()
        assert any("schema" in str(e["loc"]) for e in errors)


class TestDiagnosticDescriptionRequiredFields:
    """Tests for required fields."""

    @pytest.fixture
    def valid_base_data(self) -> dict[str, Any]:
        """Return minimal valid data."""
        return {
            "schema": "opensovd.cda.diagdesc/v1",
            "meta": VALID_META,
            "ecu": VALID_ECU,
            "sessions": {},
            "services": {},
            "access_patterns": {},
        }

    def test_all_required_fields_present(self, valid_base_data: dict[str, Any]) -> None:
        """Should accept all required fields."""
        model = DiagnosticDescription.model_validate(valid_base_data)
        assert model is not None

    @pytest.mark.parametrize("field", ["meta", "ecu", "sessions", "services"])
    def test_missing_required_field(self, valid_base_data: dict[str, Any], field: str) -> None:
        """Should reject missing required fields."""
        del valid_base_data[field]
        with pytest.raises(ValidationError) as exc_info:
            DiagnosticDescription.model_validate(valid_base_data)

        errors = exc_info.value.errors()
        assert any(field in str(e["loc"]) for e in errors)


class TestDiagnosticDescriptionOptionalFields:
    """Tests for optional fields."""

    @pytest.fixture
    def valid_base_data(self) -> dict[str, Any]:
        """Return minimal valid data."""
        return {
            "schema": "opensovd.cda.diagdesc/v1",
            "meta": VALID_META,
            "ecu": VALID_ECU,
            "sessions": {},
            "services": {},
            "access_patterns": {},
        }

    @pytest.mark.parametrize(
        "field",
        [
            "security",
            "authentication",
            "state_model",
            "variants",
            "identification",
            "types",
            "dids",
            "routines",
            "dtc_config",
            "dtcs",
            "annotations",
            "audience",
            "sdgs",
            "comparams",
            "ecu_jobs",
        ],
    )
    def test_optional_fields_default_to_none(
        self, valid_base_data: dict[str, Any], field: str
    ) -> None:
        """Optional fields should default to None."""
        model = DiagnosticDescription.model_validate(valid_base_data)
        assert getattr(model, field) is None

    def test_x_oem_with_alias(self, valid_base_data: dict[str, Any]) -> None:
        """Should accept x-oem field via alias."""
        valid_base_data["x-oem"] = {"custom_field": "value"}
        model = DiagnosticDescription.model_validate(valid_base_data)
        assert model.x_oem == {"custom_field": "value"}


class TestDiagnosticDescriptionExtraFields:
    """Tests for extra field handling."""

    def test_rejects_extra_fields(self) -> None:
        """Should reject unknown fields (extra='forbid')."""
        data = {
            "schema": "opensovd.cda.diagdesc/v1",
            "meta": VALID_META,
            "ecu": VALID_ECU,
            "sessions": {},
            "services": {},
            "access_patterns": {},
            "unknown_field": "value",  # Extra field
        }
        with pytest.raises(ValidationError) as exc_info:
            DiagnosticDescription.model_validate(data)

        errors = exc_info.value.errors()
        assert any("extra" in str(e["type"]) for e in errors)
