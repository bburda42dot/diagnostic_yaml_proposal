"""Models for the meta section of diagnostic description."""

from __future__ import annotations

import re
from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Semantic version pattern: MAJOR.MINOR.PATCH[-prerelease][+build]
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$")


class RevisionEntry(BaseModel):
    """A single entry in the revision history.

    Represents one version change in the document history, tracking
    what changed, when, and by whom.

    Example:
    -------
        ```yaml
        - version: "1.0.0"
          date: "2024-01-15"
          author: "John Doe"
          changes: "Initial release"
        ```

    """

    model_config = ConfigDict(extra="forbid")

    version: Annotated[
        str,
        Field(
            description="Version number in semver format (e.g., '1.0.0')",
            examples=["1.0.0", "2.1.0-beta.1"],
        ),
    ]
    date: Annotated[
        date,
        Field(description="Date of this revision"),
    ]
    author: Annotated[
        str,
        Field(
            min_length=1,
            description="Author of this revision",
        ),
    ]
    changes: Annotated[
        str,
        Field(
            min_length=1,
            description="Description of changes in this revision",
        ),
    ]

    @field_validator("version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        """Validate that version follows semantic versioning."""
        if not SEMVER_PATTERN.match(v):
            raise ValueError(
                f"Invalid semver format: '{v}'. "
                "Expected format: MAJOR.MINOR.PATCH[-prerelease][+build]"
            )
        return v


class Meta(BaseModel):
    """Document metadata section.

    Contains information about the document itself, including authorship,
    creation date, version, and optional revision history.

    Example:
    -------
        ```yaml
        meta:
          author: "John Doe"
          domain: "Powertrain"
          created: "2024-01-15"
          revision: "1.0.0"
          description: "Engine Control Module diagnostic description"
          tags:
            - engine
            - powertrain
        ```

    """

    model_config = ConfigDict(extra="forbid")

    author: Annotated[
        str,
        Field(
            min_length=1,
            description="Document author name or team",
            examples=["John Doe", "Powertrain Team"],
        ),
    ]
    domain: Annotated[
        str,
        Field(
            min_length=1,
            description="Domain or area this ECU belongs to",
            examples=["Powertrain", "Body", "Chassis", "Infotainment"],
        ),
    ]
    created: Annotated[
        date,
        Field(description="Document creation date"),
    ]
    revision: Annotated[
        str,
        Field(
            description="Current document version in semver format",
            examples=["1.0.0", "2.1.0-beta.1"],
        ),
    ]
    description: Annotated[
        str,
        Field(
            min_length=1,
            description="Human-readable description of the ECU or document",
        ),
    ]
    tags: Annotated[
        list[str] | None,
        Field(
            default=None,
            description="Optional tags for categorization and searching",
            examples=[["engine", "powertrain"], ["abs", "chassis"]],
        ),
    ]
    revisions: Annotated[
        list[RevisionEntry] | None,
        Field(
            default=None,
            description="Optional revision history",
        ),
    ]

    @field_validator("revision")
    @classmethod
    def validate_revision_semver(cls, v: str) -> str:
        """Validate that revision follows semantic versioning."""
        if not SEMVER_PATTERN.match(v):
            raise ValueError(
                f"Invalid semver format: '{v}'. "
                "Expected format: MAJOR.MINOR.PATCH[-prerelease][+build]"
            )
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags_not_empty(cls, v: list[str] | None) -> list[str] | None:
        """Validate that tags list is not empty if provided."""
        if v is not None and len(v) == 0:
            raise ValueError("Tags list cannot be empty if provided")
        return v
