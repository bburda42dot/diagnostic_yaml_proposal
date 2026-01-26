"""Base validator class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from yaml_to_mdd.validation.errors import ValidationResult

if TYPE_CHECKING:
    from yaml_to_mdd.models.root import DiagnosticDescription


class BaseValidator(ABC):
    """Base class for validators."""

    @abstractmethod
    def validate(
        self,
        doc: DiagnosticDescription,
        result: ValidationResult,
    ) -> None:
        """Validate the document and add issues to result.

        Args:
        ----
            doc: The diagnostic description to validate.
            result: The result object to add issues to.

        """
        ...


class CompositeValidator(BaseValidator):
    """Combines multiple validators."""

    def __init__(self, validators: list[BaseValidator] | None = None) -> None:
        """Initialize with optional list of validators.

        Args:
        ----
            validators: List of validators to combine.

        """
        self.validators = validators or []

    def add(self, validator: BaseValidator) -> None:
        """Add a validator.

        Args:
        ----
            validator: Validator to add.

        """
        self.validators.append(validator)

    def validate(
        self,
        doc: DiagnosticDescription,
        result: ValidationResult,
    ) -> None:
        """Run all validators.

        Args:
        ----
            doc: The diagnostic description to validate.
            result: The result object to add issues to.

        """
        for validator in self.validators:
            validator.validate(doc, result)
