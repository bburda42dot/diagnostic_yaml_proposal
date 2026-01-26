"""Tests for AudienceFilter class."""

from datetime import date

import pytest
from yaml_to_mdd.filter.audience_filter import AudienceFilter
from yaml_to_mdd.models import (
    DiagnosticDescription,
)
from yaml_to_mdd.models.audience import (
    AudienceConfig,
    StandardAudience,
)


@pytest.fixture
def minimal_doc_data() -> dict:
    """Return minimal valid document data."""
    return {
        "schema": "opensovd.cda.diagdesc/v1",
        "meta": {
            "author": "Test",
            "domain": "Test",
            "description": "Test document",
            "revision": "1.0.0",
            "created": str(date.today()),
        },
        "ecu": {
            "id": "TEST_ECU",
            "name": "Test ECU",
            "addressing": {
                "doip": {
                    "ip": "192.168.1.100",
                    "logical_address": "0x0001",
                    "tester_address": "0x0F00",
                    "functional_address": "0x0002",
                }
            },
        },
        "sessions": {
            "default": {"id": "0x01", "alias": "Default Session"},
            "extended": {"id": "0x03", "alias": "Extended Session"},
        },
        "services": {
            "diagnosticSessionControl": {"enabled": True},
        },
    }


@pytest.fixture
def doc_with_audiences(minimal_doc_data: dict) -> DiagnosticDescription:
    """Create document with audience-tagged items."""
    data = minimal_doc_data.copy()

    # Add DIDs with different audience restrictions
    data["dids"] = {
        "0xF190": {
            "name": "VIN",
            "type": {"base": "ascii", "length": 17},
            "access": "read",
            # No audience - available to all
        },
        "0xF191": {
            "name": "ECU Hardware Number",
            "type": {"base": "ascii", "length": 20},
            "access": "read",
            "audience": {"include": ["production", "development"]},
            # Aftermarket cannot read this
        },
        "0xFFFF": {
            "name": "Debug Data",
            "type": {"base": "bytes", "length": 256},
            "access": "read_write",
            "audience": {"include": ["development"]},
            # Only development can access
        },
        "0x0100": {
            "name": "OEM Specific DID",
            "type": {"base": "u32"},
            "access": "read",
            "audience": {"include": ["oem", "development"], "exclude": ["aftermarket"]},
        },
    }

    # Add custom types
    data["types"] = {
        "VIN_Type": {
            "base": "ascii",
            "length": 17,
        },
    }

    return DiagnosticDescription.model_validate(data)


class TestAudienceFilter:
    """Tests for AudienceFilter."""

    def test_filter_removes_restricted_dids(
        self,
        doc_with_audiences: DiagnosticDescription,
    ) -> None:
        """Should remove DIDs not accessible to audience."""
        filter_obj = AudienceFilter(StandardAudience.AFTERMARKET)

        filtered = filter_obj.filter(doc_with_audiences)

        # Aftermarket should only see VIN (no restrictions)
        assert filtered.dids is not None
        assert len(filtered.dids) == 1
        assert 0xF190 in filtered.dids  # VIN - no restrictions
        assert 0xF191 not in filtered.dids  # production/dev only
        assert 0xFFFF not in filtered.dids  # development only
        assert 0x0100 not in filtered.dids  # explicitly excluded

    def test_filter_keeps_unrestricted(
        self,
        doc_with_audiences: DiagnosticDescription,
    ) -> None:
        """Should keep items with no audience restriction."""
        filter_obj = AudienceFilter(StandardAudience.AFTERMARKET)

        filtered = filter_obj.filter(doc_with_audiences)

        # VIN has no audience restriction, should be visible
        assert filtered.dids is not None
        assert 0xF190 in filtered.dids

    def test_development_sees_all(
        self,
        doc_with_audiences: DiagnosticDescription,
    ) -> None:
        """Development should see all items it's included in."""
        filter_obj = AudienceFilter(StandardAudience.DEVELOPMENT)

        filtered = filter_obj.filter(doc_with_audiences)

        assert filtered.dids is not None
        # Development is included in all or has no restriction
        assert 0xF190 in filtered.dids  # No restriction
        assert 0xF191 in filtered.dids  # Includes development
        assert 0xFFFF in filtered.dids  # Development only
        assert 0x0100 in filtered.dids  # Includes development

    def test_production_sees_production_items(
        self,
        doc_with_audiences: DiagnosticDescription,
    ) -> None:
        """Production should see production-accessible items."""
        filter_obj = AudienceFilter(StandardAudience.PRODUCTION)

        filtered = filter_obj.filter(doc_with_audiences)

        assert filtered.dids is not None
        assert 0xF190 in filtered.dids  # No restriction
        assert 0xF191 in filtered.dids  # Includes production
        assert 0xFFFF not in filtered.dids  # Development only
        assert 0x0100 not in filtered.dids  # OEM/dev only

    def test_filter_summary(
        self,
        doc_with_audiences: DiagnosticDescription,
    ) -> None:
        """Should provide accurate filter summary."""
        filter_obj = AudienceFilter(StandardAudience.AFTERMARKET)

        filtered = filter_obj.filter(doc_with_audiences)
        summary = filter_obj.get_filter_summary(doc_with_audiences, filtered)

        assert summary["audience"] == "aftermarket"
        assert "removed" in summary
        assert summary["removed"]["dids"] == 3  # 4 -> 1
        assert all(v >= 0 for v in summary["removed"].values())

    def test_filter_with_hierarchy(
        self,
        doc_with_audiences: DiagnosticDescription,
    ) -> None:
        """Should respect audience hierarchy."""
        config = AudienceConfig(
            hierarchy={
                "development": ["production", "aftermarket"],
                "production": ["aftermarket"],
            }
        )
        filter_obj = AudienceFilter(StandardAudience.DEVELOPMENT, config)

        filtered = filter_obj.filter(doc_with_audiences)

        # With hierarchy, development should see everything except explicitly excluded
        assert filtered.dids is not None
        assert 0xF190 in filtered.dids
        assert 0xF191 in filtered.dids
        assert 0xFFFF in filtered.dids
        assert 0x0100 in filtered.dids

    def test_filter_preserves_original(
        self,
        doc_with_audiences: DiagnosticDescription,
    ) -> None:
        """Should not modify the original document."""
        original_dids_count = len(doc_with_audiences.dids) if doc_with_audiences.dids else 0

        filter_obj = AudienceFilter(StandardAudience.AFTERMARKET)
        _ = filter_obj.filter(doc_with_audiences)

        # Original should be unchanged
        current_dids_count = len(doc_with_audiences.dids) if doc_with_audiences.dids else 0
        assert current_dids_count == original_dids_count

    def test_filter_custom_audience(
        self,
        doc_with_audiences: DiagnosticDescription,
    ) -> None:
        """Should work with custom audience strings."""
        # Add a DID with custom audience
        data = doc_with_audiences.model_dump(by_alias=True)
        data["dids"]["0x1234"] = {
            "name": "Custom DID",
            "type": {"base": "u8"},
            "access": "read",
            "audience": {"include": ["custom_team"]},
        }
        doc = DiagnosticDescription.model_validate(data)

        filter_obj = AudienceFilter("custom_team")
        filtered = filter_obj.filter(doc)

        assert filtered.dids is not None
        # Should see custom_team DID and unrestricted ones
        assert 0x1234 in filtered.dids
        assert 0xF190 in filtered.dids

    def test_filter_empty_dids(self, minimal_doc_data: dict) -> None:
        """Should handle document with no DIDs."""
        doc = DiagnosticDescription.model_validate(minimal_doc_data)

        filter_obj = AudienceFilter(StandardAudience.PRODUCTION)
        filtered = filter_obj.filter(doc)

        # Should not raise, DIDs remain None
        assert filtered.dids is None

    def test_effective_audiences_in_summary(
        self,
        doc_with_audiences: DiagnosticDescription,
    ) -> None:
        """Summary should include effective audiences from hierarchy."""
        config = AudienceConfig(
            hierarchy={
                "development": ["production", "aftermarket"],
            }
        )
        filter_obj = AudienceFilter(StandardAudience.DEVELOPMENT, config)

        filtered = filter_obj.filter(doc_with_audiences)
        summary = filter_obj.get_filter_summary(doc_with_audiences, filtered)

        assert "development" in summary["effective_audiences"]
        assert "production" in summary["effective_audiences"]
        assert "aftermarket" in summary["effective_audiences"]


class TestAudienceFilterServices:
    """Tests for filtering services by audience."""

    def test_filter_services_with_audience(self, minimal_doc_data: dict) -> None:
        """Should filter services by audience."""
        data = minimal_doc_data.copy()
        data["services"] = {
            "diagnosticSessionControl": {"enabled": True},
            "securityAccess": {
                "enabled": True,
                "audience": {"include": ["development"]},
            },
        }
        doc = DiagnosticDescription.model_validate(data)

        filter_obj = AudienceFilter(StandardAudience.PRODUCTION)
        filtered = filter_obj.filter(doc)

        # DSC has no audience, should remain
        assert filtered.services.diagnosticSessionControl is not None
        # SecurityAccess is dev-only, should be removed for production
        assert filtered.services.securityAccess is None
