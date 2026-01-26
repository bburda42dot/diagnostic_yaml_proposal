"""Tests for Meta section models."""

from datetime import date
from typing import Any

import pytest
from pydantic import ValidationError
from yaml_to_mdd.models.meta import Meta, RevisionEntry


class TestRevisionEntry:
    """Tests for RevisionEntry model."""

    def test_valid_revision_entry(self) -> None:
        """Should accept valid revision entry."""
        entry = RevisionEntry(
            version="1.0.0",
            date=date(2024, 1, 15),
            author="John Doe",
            changes="Initial release",
        )
        assert entry.version == "1.0.0"
        assert entry.date == date(2024, 1, 15)
        assert entry.author == "John Doe"
        assert entry.changes == "Initial release"

    def test_accepts_date_string(self) -> None:
        """Should parse date from string."""
        entry = RevisionEntry(
            version="1.0.0",
            date="2024-01-15",  # type: ignore[arg-type]
            author="John Doe",
            changes="Initial release",
        )
        assert entry.date == date(2024, 1, 15)

    @pytest.mark.parametrize(
        "version",
        [
            "1.0.0",
            "0.1.0",
            "10.20.30",
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0-beta.2",
            "1.0.0+build.123",
            "1.0.0-rc.1+build.456",
        ],
    )
    def test_valid_semver_versions(self, version: str) -> None:
        """Should accept valid semver versions."""
        entry = RevisionEntry(
            version=version,
            date=date(2024, 1, 15),
            author="Author",
            changes="Changes",
        )
        assert entry.version == version

    @pytest.mark.parametrize(
        "version",
        [
            "1.0",  # Missing patch
            "1",  # Only major
            "v1.0.0",  # Leading 'v'
            "1.0.0.0",  # Too many parts
            "a.b.c",  # Non-numeric
            "",  # Empty
        ],
    )
    def test_invalid_semver_versions(self, version: str) -> None:
        """Should reject invalid semver versions."""
        with pytest.raises(ValidationError):
            RevisionEntry(
                version=version,
                date=date(2024, 1, 15),
                author="Author",
                changes="Changes",
            )

    def test_empty_author_rejected(self) -> None:
        """Should reject empty author."""
        with pytest.raises(ValidationError):
            RevisionEntry(
                version="1.0.0",
                date=date(2024, 1, 15),
                author="",
                changes="Changes",
            )

    def test_empty_changes_rejected(self) -> None:
        """Should reject empty changes."""
        with pytest.raises(ValidationError):
            RevisionEntry(
                version="1.0.0",
                date=date(2024, 1, 15),
                author="Author",
                changes="",
            )


class TestMeta:
    """Tests for Meta model."""

    @pytest.fixture
    def valid_meta_data(self) -> dict[str, Any]:
        """Return valid meta data."""
        return {
            "author": "John Doe",
            "domain": "Powertrain",
            "created": "2024-01-15",
            "revision": "1.0.0",
            "description": "Engine Control Module",
        }

    def test_valid_meta_minimal(self, valid_meta_data: dict[str, Any]) -> None:
        """Should accept minimal valid meta."""
        meta = Meta.model_validate(valid_meta_data)
        assert meta.author == "John Doe"
        assert meta.domain == "Powertrain"
        assert meta.created == date(2024, 1, 15)
        assert meta.revision == "1.0.0"
        assert meta.description == "Engine Control Module"
        assert meta.tags is None
        assert meta.revisions is None

    def test_valid_meta_with_tags(self, valid_meta_data: dict[str, Any]) -> None:
        """Should accept meta with tags."""
        valid_meta_data["tags"] = ["engine", "powertrain"]
        meta = Meta.model_validate(valid_meta_data)
        assert meta.tags == ["engine", "powertrain"]

    def test_valid_meta_with_revisions(self, valid_meta_data: dict[str, Any]) -> None:
        """Should accept meta with revision history."""
        valid_meta_data["revisions"] = [
            {
                "version": "1.0.0",
                "date": "2024-01-15",
                "author": "John Doe",
                "changes": "Initial release",
            },
            {
                "version": "0.9.0",
                "date": "2024-01-01",
                "author": "Jane Doe",
                "changes": "Beta release",
            },
        ]
        meta = Meta.model_validate(valid_meta_data)
        assert meta.revisions is not None
        assert len(meta.revisions) == 2
        assert meta.revisions[0].version == "1.0.0"
        assert meta.revisions[1].author == "Jane Doe"

    def test_empty_tags_rejected(self, valid_meta_data: dict[str, Any]) -> None:
        """Should reject empty tags list."""
        valid_meta_data["tags"] = []
        with pytest.raises(ValidationError) as exc_info:
            Meta.model_validate(valid_meta_data)

        errors = exc_info.value.errors()
        assert any("tags" in str(e["loc"]) for e in errors)

    @pytest.mark.parametrize(
        "field",
        ["author", "domain", "created", "revision", "description"],
    )
    def test_missing_required_field(self, valid_meta_data: dict[str, Any], field: str) -> None:
        """Should reject missing required fields."""
        del valid_meta_data[field]
        with pytest.raises(ValidationError):
            Meta.model_validate(valid_meta_data)

    def test_empty_author_rejected(self, valid_meta_data: dict[str, Any]) -> None:
        """Should reject empty author."""
        valid_meta_data["author"] = ""
        with pytest.raises(ValidationError):
            Meta.model_validate(valid_meta_data)

    def test_invalid_date_format(self, valid_meta_data: dict[str, Any]) -> None:
        """Should reject invalid date format."""
        valid_meta_data["created"] = "15-01-2024"  # Wrong format
        with pytest.raises(ValidationError):
            Meta.model_validate(valid_meta_data)

    def test_invalid_revision_semver(self, valid_meta_data: dict[str, Any]) -> None:
        """Should reject invalid revision semver."""
        valid_meta_data["revision"] = "v1.0"
        with pytest.raises(ValidationError):
            Meta.model_validate(valid_meta_data)

    def test_extra_fields_rejected(self, valid_meta_data: dict[str, Any]) -> None:
        """Should reject extra fields."""
        valid_meta_data["unknown_field"] = "value"
        with pytest.raises(ValidationError) as exc_info:
            Meta.model_validate(valid_meta_data)

        errors = exc_info.value.errors()
        assert any("extra" in str(e["type"]) for e in errors)


class TestMetaWithRoot:
    """Tests for Meta integrated with DiagnosticDescription."""

    def test_full_document_with_meta(self) -> None:
        """Should parse full document with proper meta."""
        from yaml_to_mdd.models.root import DiagnosticDescription

        data = {
            "schema": "opensovd.cda.diagdesc/v1",
            "meta": {
                "author": "John Doe",
                "domain": "Powertrain",
                "created": "2024-01-15",
                "revision": "1.0.0",
                "description": "Engine Control Module",
                "tags": ["engine"],
            },
            "ecu": {
                "id": "ECM_V1",
                "name": "Engine Control Module",
                "addressing": {
                    "doip": {
                        "ip": "192.168.1.100",
                        "logical_address": "0x0010",
                        "tester_address": "0x0F00",
                    }
                },
            },
            "sessions": {},
            "services": {},
            "access_patterns": {},
        }

        doc = DiagnosticDescription.model_validate(data)
        assert doc.meta.author == "John Doe"
        assert doc.meta.tags == ["engine"]
