"""Fixtures for validation tests."""

from __future__ import annotations

from datetime import date

import pytest
from yaml_to_mdd.models.access_patterns import AccessPattern
from yaml_to_mdd.models.dids import DIDDefinition
from yaml_to_mdd.models.dtcs import DTCDefinition
from yaml_to_mdd.models.ecu import Ecu
from yaml_to_mdd.models.meta import Meta
from yaml_to_mdd.models.root import DiagnosticDescription
from yaml_to_mdd.models.security import SecurityLevel
from yaml_to_mdd.models.services import Services
from yaml_to_mdd.models.sessions import Session
from yaml_to_mdd.models.types import TypeDefinition


@pytest.fixture
def minimal_meta() -> Meta:
    """Create minimal meta model."""
    return Meta(
        author="Test Author",
        domain="powertrain",
        created=date(2024, 1, 15),
        revision="1.0.0",
        description="Test document for validation tests",
    )


@pytest.fixture
def minimal_ecu() -> Ecu:
    """Create minimal ECU model."""
    from yaml_to_mdd.models.ecu import Addressing, DoIPAddressing

    return Ecu(
        id="TEST_ECU",
        name="Test ECU",
        addressing=Addressing(
            doip=DoIPAddressing(
                ip="192.168.1.100",
                logical_address=0x0010,
                tester_address=0x0F00,
            ),
        ),
    )


@pytest.fixture
def minimal_sessions() -> dict[str, Session]:
    """Create minimal sessions."""
    return {
        "default": Session(id=0x01, alias="Default Session"),
        "extended": Session(id=0x03, alias="Extended Diagnostic Session"),
    }


@pytest.fixture
def minimal_services() -> Services:
    """Create minimal services configuration."""
    from yaml_to_mdd.models.services import ReadDataByIdentifierConfig

    return Services(
        readDataByIdentifier=ReadDataByIdentifierConfig(enabled=True),
    )


@pytest.fixture
def minimal_access_patterns() -> dict[str, AccessPattern]:
    """Create minimal access patterns."""
    return {
        "standard_read": AccessPattern(
            sessions="any",
            security="none",
            authentication="none",
        ),
    }


@pytest.fixture
def minimal_doc(
    minimal_meta: Meta,
    minimal_ecu: Ecu,
    minimal_sessions: dict[str, Session],
    minimal_services: Services,
    minimal_access_patterns: dict[str, AccessPattern],
) -> DiagnosticDescription:
    """Create minimal valid document."""
    return DiagnosticDescription(
        schema_version="opensovd.cda.diagdesc/v1",
        meta=minimal_meta,
        ecu=minimal_ecu,
        sessions=minimal_sessions,
        services=minimal_services,
        access_patterns=minimal_access_patterns,
    )


@pytest.fixture
def doc_with_types(minimal_doc: DiagnosticDescription) -> DiagnosticDescription:
    """Create document with type definitions."""
    types = {
        "VIN": TypeDefinition(
            base="ascii",
            length=17,
            description="Vehicle Identification Number",
        ),
        "Temperature": TypeDefinition(
            base="u8",
            unit="°C",
            description="Temperature value",
        ),
    }
    return DiagnosticDescription(**{**minimal_doc.model_dump(), "types": types})


@pytest.fixture
def doc_with_valid_dids(doc_with_types: DiagnosticDescription) -> DiagnosticDescription:
    """Create document with valid DID references."""
    dids = {
        0xF190: DIDDefinition(
            name="VIN",
            description="Vehicle Identification Number",
            type="VIN",
            access="read",
            access_pattern="standard_read",
        ),
        0xF191: DIDDefinition(
            name="Temperature",
            description="Engine temperature",
            type="u8",  # builtin type
            access="read",
        ),
    }
    return DiagnosticDescription(**{**doc_with_types.model_dump(), "dids": dids})


@pytest.fixture
def doc_with_undefined_type(
    minimal_doc: DiagnosticDescription,
) -> DiagnosticDescription:
    """Create document with undefined type reference in DID."""
    dids = {
        0xF190: DIDDefinition(
            name="VIN",
            description="Vehicle Identification Number",
            type="UndefinedType",  # This type doesn't exist
            access="read",
        ),
    }
    return DiagnosticDescription(**{**minimal_doc.model_dump(), "dids": dids})


@pytest.fixture
def doc_with_valid_sessions(
    minimal_doc: DiagnosticDescription,
) -> DiagnosticDescription:
    """Create document with access pattern referencing valid sessions."""
    access_patterns = {
        "extended_rw": AccessPattern(
            sessions=["extended"],
            security="none",
            authentication="none",
        ),
    }
    return DiagnosticDescription(**{**minimal_doc.model_dump(), "access_patterns": access_patterns})


@pytest.fixture
def doc_with_undefined_session(
    minimal_doc: DiagnosticDescription,
) -> DiagnosticDescription:
    """Create document with access pattern referencing undefined session."""
    access_patterns = {
        "bad_pattern": AccessPattern(
            sessions=["nonexistent_session"],
            security="none",
            authentication="none",
        ),
    }
    return DiagnosticDescription(**{**minimal_doc.model_dump(), "access_patterns": access_patterns})


@pytest.fixture
def doc_with_any_session(minimal_doc: DiagnosticDescription) -> DiagnosticDescription:
    """Create document with access pattern using 'any' sessions."""
    access_patterns = {
        "any_session_pattern": AccessPattern(
            sessions="any",
            security="none",
            authentication="none",
        ),
    }
    return DiagnosticDescription(**{**minimal_doc.model_dump(), "access_patterns": access_patterns})


@pytest.fixture
def doc_with_valid_security(
    minimal_doc: DiagnosticDescription,
) -> DiagnosticDescription:
    """Create document with valid security levels."""
    security = {
        "level_1": SecurityLevel(
            level=1,
            seed_request=0x01,
            key_send=0x02,
            seed_size=4,
            key_size=4,
            algorithm="XOR",
            max_attempts=3,
            delay_on_fail_ms=10000,
            allowed_sessions=["extended"],
        ),
    }
    access_patterns = {
        "secured": AccessPattern(
            sessions=["extended"],
            security=["level_1"],
            authentication="none",
        ),
    }
    return DiagnosticDescription(
        **{
            **minimal_doc.model_dump(),
            "security": security,
            "access_patterns": access_patterns,
        }
    )


@pytest.fixture
def doc_with_undefined_security(
    minimal_doc: DiagnosticDescription,
) -> DiagnosticDescription:
    """Create document with access pattern referencing undefined security."""
    access_patterns = {
        "bad_security": AccessPattern(
            sessions="any",
            security=["nonexistent_level"],
            authentication="none",
        ),
    }
    return DiagnosticDescription(**{**minimal_doc.model_dump(), "access_patterns": access_patterns})


@pytest.fixture
def doc_with_duplicate_session_ids(
    minimal_doc: DiagnosticDescription,
) -> DiagnosticDescription:
    """Create document with duplicate session IDs."""
    sessions = {
        "session_a": Session(id=0x01, alias="Session A"),
        "session_b": Session(id=0x01, alias="Session B"),  # Same ID!
    }
    return DiagnosticDescription(**{**minimal_doc.model_dump(), "sessions": sessions})


@pytest.fixture
def doc_with_mismatched_security_pair(
    minimal_doc: DiagnosticDescription,
) -> DiagnosticDescription:
    """Create document with security level having mismatched seed/key pair."""
    security = {
        "level_1": SecurityLevel(
            level=1,
            seed_request=0x01,
            key_send=0x04,  # Should be 0x02!
            seed_size=4,
            key_size=4,
            algorithm="XOR",
            max_attempts=3,
            delay_on_fail_ms=10000,
            allowed_sessions=["extended"],
        ),
    }
    return DiagnosticDescription(**{**minimal_doc.model_dump(), "security": security})


@pytest.fixture
def doc_with_undefined_access_pattern(
    minimal_doc: DiagnosticDescription,
) -> DiagnosticDescription:
    """Create document with DID referencing undefined access pattern."""
    dids = {
        0xF190: DIDDefinition(
            name="VIN",
            type="u8",
            access="read",
            access_pattern="nonexistent_pattern",
        ),
    }
    return DiagnosticDescription(**{**minimal_doc.model_dump(), "dids": dids})


@pytest.fixture
def doc_with_unused_type(minimal_doc: DiagnosticDescription) -> DiagnosticDescription:
    """Create document with unused type definition."""
    types = {
        "UnusedType": TypeDefinition(
            base="u8",
            description="This type is never used",
        ),
    }
    return DiagnosticDescription(**{**minimal_doc.model_dump(), "types": types})


@pytest.fixture
def doc_with_dtc_valid_prefix(
    minimal_doc: DiagnosticDescription,
) -> DiagnosticDescription:
    """Create document with valid DTC format."""
    dtcs = {
        0x010203: DTCDefinition(
            name="Valid Powertrain DTC",
            sae="P0123",  # Valid SAE prefix
            description="DTC with valid prefix",
        ),
    }
    return DiagnosticDescription(**{**minimal_doc.model_dump(), "dtcs": dtcs})
