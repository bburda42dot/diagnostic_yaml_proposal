"""Tests for audience filtering."""

import pytest
from yaml_to_mdd.models.audience import (
    AudienceConfig,
    AudienceSet,
    StandardAudience,
    parse_audience_set,
)


class TestAudienceSet:
    """Tests for AudienceSet."""

    def test_empty_set_allows_all(self) -> None:
        """Empty set should allow all audiences."""
        audience_set = AudienceSet()

        assert audience_set.is_accessible(StandardAudience.PRODUCTION) is True
        assert audience_set.is_accessible(StandardAudience.DEVELOPMENT) is True
        assert audience_set.is_accessible("custom") is True

    def test_include_restricts_access(self) -> None:
        """Include list should restrict to specified audiences."""
        audience_set = AudienceSet(include=[StandardAudience.DEVELOPMENT])

        assert audience_set.is_accessible(StandardAudience.DEVELOPMENT) is True
        assert audience_set.is_accessible(StandardAudience.PRODUCTION) is False

    def test_exclude_denies_access(self) -> None:
        """Exclude list should deny specified audiences."""
        audience_set = AudienceSet(exclude=[StandardAudience.AFTERMARKET])

        assert audience_set.is_accessible(StandardAudience.DEVELOPMENT) is True
        assert audience_set.is_accessible(StandardAudience.AFTERMARKET) is False

    def test_exclude_takes_priority(self) -> None:
        """Exclude should override include."""
        audience_set = AudienceSet(
            include=[StandardAudience.DEVELOPMENT, StandardAudience.PRODUCTION],
            exclude=[StandardAudience.PRODUCTION],
        )

        assert audience_set.is_accessible(StandardAudience.DEVELOPMENT) is True
        assert audience_set.is_accessible(StandardAudience.PRODUCTION) is False

    def test_none_audience_always_allowed(self) -> None:
        """None audience (no filter) should always be allowed."""
        audience_set = AudienceSet(include=[StandardAudience.DEVELOPMENT])

        assert audience_set.is_accessible(None) is True

    def test_string_audience_matching(self) -> None:
        """Should match string audiences correctly."""
        audience_set = AudienceSet(include=["custom_audience"])

        assert audience_set.is_accessible("custom_audience") is True
        assert audience_set.is_accessible("other_audience") is False

    def test_mixed_enum_and_string(self) -> None:
        """Should handle mixed enum and string audiences."""
        audience_set = AudienceSet(include=[StandardAudience.DEVELOPMENT, "custom_audience"])

        assert audience_set.is_accessible(StandardAudience.DEVELOPMENT) is True
        assert audience_set.is_accessible("custom_audience") is True
        assert audience_set.is_accessible(StandardAudience.PRODUCTION) is False


class TestAudienceConfig:
    """Tests for AudienceConfig."""

    def test_default_config(self) -> None:
        """Should have sensible defaults."""
        config = AudienceConfig()

        assert config.default == StandardAudience.PRODUCTION

    def test_hierarchy_expansion(self) -> None:
        """Should expand audience hierarchy."""
        config = AudienceConfig(
            hierarchy={
                "development": ["production", "aftermarket"],
                "production": ["aftermarket"],
            }
        )

        dev_audiences = config.get_effective_audiences("development")

        assert "development" in dev_audiences
        assert "production" in dev_audiences
        assert "aftermarket" in dev_audiences

    def test_no_hierarchy(self) -> None:
        """Should work without hierarchy."""
        config = AudienceConfig()

        audiences = config.get_effective_audiences("production")

        assert audiences == {"production"}

    def test_hierarchy_cycle_protection(self) -> None:
        """Should handle cycles in hierarchy gracefully."""
        config = AudienceConfig(
            hierarchy={
                "a": ["b"],
                "b": ["c"],
                "c": ["a"],  # Cycle
            }
        )

        audiences = config.get_effective_audiences("a")

        # Should contain all without infinite loop
        assert "a" in audiences
        assert "b" in audiences
        assert "c" in audiences

    def test_hierarchy_with_enum(self) -> None:
        """Should work with enum values in hierarchy."""
        config = AudienceConfig(
            hierarchy={
                "development": ["production"],
            }
        )

        audiences = config.get_effective_audiences(StandardAudience.DEVELOPMENT)

        assert "development" in audiences
        assert "production" in audiences


class TestParseAudienceSet:
    """Tests for parse_audience_set helper function."""

    def test_parse_none(self) -> None:
        """Should return None for None input."""
        assert parse_audience_set(None) is None

    def test_parse_dict(self) -> None:
        """Should parse dict with include/exclude."""
        result = parse_audience_set({"include": ["development"], "exclude": ["aftermarket"]})

        assert result is not None
        assert result.is_accessible(StandardAudience.DEVELOPMENT) is True
        assert result.is_accessible(StandardAudience.AFTERMARKET) is False

    def test_parse_list_shorthand(self) -> None:
        """Should parse list as include shorthand."""
        result = parse_audience_set(["development", "oem"])

        assert result is not None
        assert result.is_accessible(StandardAudience.DEVELOPMENT) is True
        assert result.is_accessible(StandardAudience.OEM) is True
        assert result.is_accessible(StandardAudience.PRODUCTION) is False

    def test_parse_already_audience_set(self) -> None:
        """Should pass through existing AudienceSet."""
        original = AudienceSet(include=[StandardAudience.DEVELOPMENT])
        result = parse_audience_set(original)

        assert result is original

    def test_parse_invalid_type_raises(self) -> None:
        """Should raise for invalid types."""
        with pytest.raises(ValueError, match="Invalid audience format"):
            parse_audience_set(123)


class TestAudienceSetWithHierarchy:
    """Tests for AudienceSet.is_accessible_with_hierarchy."""

    def test_hierarchy_access(self) -> None:
        """Should grant access via hierarchy."""
        audience_set = AudienceSet(include=[StandardAudience.PRODUCTION])
        effective = {"development", "production", "aftermarket"}

        # Development has production in its effective audiences
        assert (
            audience_set.is_accessible_with_hierarchy(StandardAudience.DEVELOPMENT, effective)
            is True
        )

    def test_hierarchy_excludes_respected(self) -> None:
        """Excludes should still be respected with hierarchy."""
        audience_set = AudienceSet(
            include=[StandardAudience.PRODUCTION],
            exclude=[StandardAudience.DEVELOPMENT],
        )
        effective = {"development", "production", "aftermarket"}

        # Even though development includes production, explicit exclude blocks it
        assert (
            audience_set.is_accessible_with_hierarchy(StandardAudience.DEVELOPMENT, effective)
            is False
        )
