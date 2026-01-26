"""Tests for DTCs section models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from yaml_to_mdd.models.dtcs import (
    DTCConfig,
    DTCDefinition,
    DTCExtendedDataDefinition,
    DTCGroup,
    DTCs,
    DTCSnapshotDataRecord,
    DTCSnapshotDefinition,
)


class TestDTCSnapshotDefinition:
    """Tests for DTCSnapshotDefinition model."""

    def test_minimal_snapshot(self) -> None:
        """Should accept minimal snapshot definition."""
        snapshot = DTCSnapshotDefinition(
            record_number=0x01,
            dids=[0xF190],
        )
        assert snapshot.record_number == 0x01
        assert snapshot.dids == [0xF190]
        assert snapshot.trigger is None
        assert snapshot.update is None

    def test_full_snapshot(self) -> None:
        """Should accept full snapshot definition."""
        snapshot = DTCSnapshotDefinition(
            record_number="0x01",  # type: ignore[arg-type]
            dids=["0xF190", "0x1234"],  # type: ignore[list-item]
            trigger="firstFault",
            update=False,
        )
        assert snapshot.record_number == 0x01
        assert snapshot.dids is not None
        assert len(snapshot.dids) == 2
        assert 0xF190 in snapshot.dids
        assert 0x1234 in snapshot.dids
        assert snapshot.trigger == "firstFault"
        assert snapshot.update is False

    def test_snapshot_with_update_true(self) -> None:
        """Should accept snapshot with update=True."""
        snapshot = DTCSnapshotDefinition(
            record_number=0x02,
            dids=[0xF190],
            trigger="mostRecent",
            update=True,
        )
        assert snapshot.update is True

    def test_snapshot_with_data_field(self) -> None:
        """Should accept snapshot with detailed data records."""
        snapshot = DTCSnapshotDefinition(
            record_number=0x01,
            description="Freeze frame at fault",
            data=[
                DTCSnapshotDataRecord(did=0xF190, name="VIN"),
                DTCSnapshotDataRecord(did=0x1234, name="Engine RPM"),
            ],
        )
        assert snapshot.record_number == 0x01
        assert snapshot.description == "Freeze frame at fault"
        assert snapshot.data is not None
        assert len(snapshot.data) == 2
        assert snapshot.data[0].name == "VIN"

    def test_empty_dids_allowed(self) -> None:
        """Should allow snapshot with empty DIDs list (data field used instead)."""
        snapshot = DTCSnapshotDefinition(
            record_number=0x01,
            dids=[],
        )
        assert snapshot.dids == []

    def test_reject_extra_fields(self) -> None:
        """Should reject extra fields."""
        with pytest.raises(ValidationError) as exc_info:
            DTCSnapshotDefinition(
                record_number=0x01,
                dids=[0xF190],
                unknown="field",  # type: ignore[call-arg]
            )
        assert "Extra inputs are not permitted" in str(exc_info.value)


class TestDTCExtendedDataDefinition:
    """Tests for DTCExtendedDataDefinition model."""

    def test_minimal_extended_data(self) -> None:
        """Should accept minimal extended data definition."""
        ext_data = DTCExtendedDataDefinition(
            record_number=0x01,
        )
        assert ext_data.record_number == 0x01
        assert ext_data.type is None
        assert ext_data.trigger is None

    def test_with_type(self) -> None:
        """Should accept extended data with type."""
        ext_data = DTCExtendedDataDefinition(
            record_number=0x01,
            type="u8",
        )
        assert ext_data.type == "u8"

    def test_with_trigger(self) -> None:
        """Should accept extended data with trigger."""
        ext_data = DTCExtendedDataDefinition(
            record_number=0x01,
            type="u16",
            trigger="onStatusChange",
        )
        assert ext_data.trigger == "onStatusChange"

    def test_hex_record_number(self) -> None:
        """Should accept hex string for record number."""
        ext_data = DTCExtendedDataDefinition(
            record_number="0xFF",  # type: ignore[arg-type]
        )
        assert ext_data.record_number == 0xFF

    def test_reject_extra_fields(self) -> None:
        """Should reject extra fields."""
        with pytest.raises(ValidationError) as exc_info:
            DTCExtendedDataDefinition(
                record_number=0x01,
                invalid="field",  # type: ignore[call-arg]
            )
        assert "Extra inputs are not permitted" in str(exc_info.value)


class TestDTCConfig:
    """Tests for DTCConfig model."""

    def test_minimal_config(self) -> None:
        """Should accept minimal (empty) config."""
        config = DTCConfig()
        assert config.status_availability_mask is None
        assert config.snapshots is None
        assert config.extended_data is None

    def test_with_status_mask(self) -> None:
        """Should accept config with status mask."""
        config = DTCConfig(
            status_availability_mask=0xFF,
        )
        assert config.status_availability_mask == 0xFF

    def test_with_status_mask_hex_string(self) -> None:
        """Should accept hex string for status mask."""
        config = DTCConfig(
            status_availability_mask="0x7F",  # type: ignore[arg-type]
        )
        assert config.status_availability_mask == 0x7F

    def test_full_config(self) -> None:
        """Should accept full config."""
        config = DTCConfig(
            status_availability_mask=0xFF,
            snapshots={
                "standard": DTCSnapshotDefinition(
                    record_number=0x01,
                    dids=[0xF190],
                ),
            },
            extended_data={
                "counter": DTCExtendedDataDefinition(
                    record_number=0x01,
                    type="u8",
                ),
            },
        )
        assert config.status_availability_mask == 0xFF
        assert config.snapshots is not None
        assert "standard" in config.snapshots
        assert config.extended_data is not None
        assert "counter" in config.extended_data

    def test_multiple_snapshots(self) -> None:
        """Should accept multiple snapshot definitions."""
        config = DTCConfig(
            snapshots={
                "first_fault": DTCSnapshotDefinition(
                    record_number=0x01,
                    dids=[0xF190],
                    trigger="firstFault",
                ),
                "most_recent": DTCSnapshotDefinition(
                    record_number=0x02,
                    dids=[0xF190, 0x1234],
                    trigger="mostRecent",
                ),
            },
        )
        assert len(config.snapshots) == 2

    def test_reject_extra_fields(self) -> None:
        """Should reject extra fields."""
        with pytest.raises(ValidationError) as exc_info:
            DTCConfig(
                invalid="field",  # type: ignore[call-arg]
            )
        assert "Extra inputs are not permitted" in str(exc_info.value)


class TestDTCDefinition:
    """Tests for DTCDefinition model."""

    def test_minimal_dtc(self) -> None:
        """Should accept minimal DTC definition."""
        dtc = DTCDefinition(
            name="TestFault",
        )
        assert dtc.name == "TestFault"
        assert dtc.sae is None
        assert dtc.description is None
        assert dtc.severity is None

    def test_full_dtc(self) -> None:
        """Should accept full DTC definition."""
        dtc = DTCDefinition(
            name="EngineOvertemperature",
            sae="P0217",
            description="Engine coolant temperature exceeds safe limit",
            severity=3,  # CHECK_AT_NEXT_HALT
            snapshots=["standard_snapshot"],
            extended_data=["occurrence_counter"],
        )
        assert dtc.name == "EngineOvertemperature"
        assert dtc.sae == "P0217"
        assert dtc.description == "Engine coolant temperature exceeds safe limit"
        assert dtc.severity == 3
        assert dtc.snapshots is not None
        assert "standard_snapshot" in dtc.snapshots
        assert dtc.extended_data is not None
        assert "occurrence_counter" in dtc.extended_data


class TestDTCDefinitionSAEValidation:
    """Tests for SAE format validation."""

    def test_sae_powertrain(self) -> None:
        """Should accept powertrain DTC (P code)."""
        dtc = DTCDefinition(name="Test", sae="P0123")
        assert dtc.sae == "P0123"

    def test_sae_body(self) -> None:
        """Should accept body DTC (B code)."""
        dtc = DTCDefinition(name="Test", sae="B1234")
        assert dtc.sae == "B1234"

    def test_sae_chassis(self) -> None:
        """Should accept chassis DTC (C code)."""
        dtc = DTCDefinition(name="Test", sae="C0001")
        assert dtc.sae == "C0001"

    def test_sae_network(self) -> None:
        """Should accept network DTC (U code)."""
        dtc = DTCDefinition(name="Test", sae="U0100")
        assert dtc.sae == "U0100"

    def test_sae_lowercase_converted(self) -> None:
        """Should convert lowercase SAE code to uppercase."""
        dtc = DTCDefinition(name="Test", sae="p0123")
        assert dtc.sae == "P0123"

    def test_sae_mixed_case(self) -> None:
        """Should handle mixed case SAE codes."""
        dtc = DTCDefinition(name="Test", sae="P0aBC")
        assert dtc.sae == "P0ABC"

    def test_sae_manufacturer_codes(self) -> None:
        """Should accept manufacturer-specific codes (1-3 second digit)."""
        for prefix in ["P", "B", "C", "U"]:
            for digit in ["1", "2", "3"]:
                dtc = DTCDefinition(name="Test", sae=f"{prefix}{digit}123")
                assert dtc.sae == f"{prefix}{digit}123"

    def test_sae_optional(self) -> None:
        """Should allow DTC without SAE code."""
        dtc = DTCDefinition(name="Test")
        assert dtc.sae is None

    def test_reject_invalid_sae_prefix(self) -> None:
        """Should reject invalid SAE prefix."""
        with pytest.raises(ValidationError) as exc_info:
            DTCDefinition(name="Test", sae="X0123")
        assert "Invalid SAE DTC format" in str(exc_info.value)

    def test_reject_invalid_sae_second_digit(self) -> None:
        """Should reject invalid second digit (must be 0-3)."""
        with pytest.raises(ValidationError) as exc_info:
            DTCDefinition(name="Test", sae="P4123")
        assert "Invalid SAE DTC format" in str(exc_info.value)

    def test_reject_sae_too_short(self) -> None:
        """Should reject SAE code that is too short."""
        with pytest.raises(ValidationError) as exc_info:
            DTCDefinition(name="Test", sae="P012")
        assert "Invalid SAE DTC format" in str(exc_info.value)

    def test_reject_sae_too_long(self) -> None:
        """Should reject SAE code that is too long."""
        with pytest.raises(ValidationError) as exc_info:
            DTCDefinition(name="Test", sae="P01234")
        assert "Invalid SAE DTC format" in str(exc_info.value)

    def test_reject_sae_invalid_hex(self) -> None:
        """Should reject SAE code with invalid hex characters."""
        with pytest.raises(ValidationError) as exc_info:
            DTCDefinition(name="Test", sae="P0GHI")
        assert "Invalid SAE DTC format" in str(exc_info.value)


class TestDTCDefinitionSeverity:
    """Tests for DTC severity validation."""

    def test_severity_int_values(self) -> None:
        """Should accept DTCSeverity int values (1-4)."""
        dtc = DTCDefinition(name="Test", severity=1)
        assert dtc.severity == 1

    def test_severity_all_valid_values(self) -> None:
        """Should accept all valid severity values (1-4)."""
        for sev in [1, 2, 3, 4]:
            dtc = DTCDefinition(name="Test", severity=sev)
            assert dtc.severity == sev

    def test_severity_reject_zero(self) -> None:
        """Should reject severity of 0."""
        with pytest.raises(ValidationError):
            DTCDefinition(name="Test", severity=0)

    def test_severity_reject_negative(self) -> None:
        """Should reject negative severity."""
        with pytest.raises(ValidationError):
            DTCDefinition(name="Test", severity=-1)

    def test_severity_reject_over_four(self) -> None:
        """Should reject severity > 4."""
        with pytest.raises(ValidationError):
            DTCDefinition(name="Test", severity=5)


class TestDTCsDict:
    """Tests for DTCsDict parsing."""

    def test_parse_hex_string_keys(self) -> None:
        """Should parse hex string keys."""
        data = {
            "0x123456": {"name": "Fault1"},
            "0xABCDEF": {"name": "Fault2"},
        }
        dtcs = DTCs.model_validate(data)
        assert 0x123456 in dtcs
        assert 0xABCDEF in dtcs
        assert dtcs[0x123456].name == "Fault1"
        assert dtcs[0xABCDEF].name == "Fault2"

    def test_parse_lowercase_hex(self) -> None:
        """Should parse lowercase hex strings."""
        data = {
            "0xabcdef": {"name": "Test"},
        }
        dtcs = DTCs.model_validate(data)
        assert 0xABCDEF in dtcs

    def test_parse_integer_keys(self) -> None:
        """Should parse integer keys."""
        data = {
            1193046: {"name": "Fault1"},  # 0x123456
        }
        dtcs = DTCs.model_validate(data)
        assert 0x123456 in dtcs

    def test_parse_decimal_string_keys(self) -> None:
        """Should parse decimal string keys."""
        data = {
            "1193046": {"name": "Test"},  # 0x123456
        }
        dtcs = DTCs.model_validate(data)
        assert 0x123456 in dtcs

    def test_boundary_values(self) -> None:
        """Should accept boundary values."""
        data = {
            "0x000000": {"name": "Min"},
            "0xFFFFFF": {"name": "Max"},
        }
        dtcs = DTCs.model_validate(data)
        assert 0x000000 in dtcs
        assert 0xFFFFFF in dtcs

    def test_reject_out_of_range_dtc(self) -> None:
        """Should reject DTC > 0xFFFFFF."""
        data = {
            "0x1000000": {"name": "Invalid"},
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            DTCs.model_validate(data)
        assert "out of range" in str(exc_info.value).lower()

    def test_reject_negative_dtc(self) -> None:
        """Should reject negative DTC."""
        data = {
            -1: {"name": "Invalid"},
        }
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            DTCs.model_validate(data)
        assert "out of range" in str(exc_info.value).lower()

    def test_reject_non_dict(self) -> None:
        """Should reject non-dict input."""
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            DTCs.model_validate([])  # type: ignore[arg-type]
        assert "must be a dictionary" in str(exc_info.value).lower()

    def test_empty_dtcs(self) -> None:
        """Should accept empty DTCs dict."""
        dtcs = DTCs.model_validate({})
        assert len(dtcs) == 0


class TestDTCsInRoot:
    """Tests for DTCs integrated with root model."""

    def test_dtcs_in_document(self) -> None:
        """Should parse DTCs in full document."""
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
            "dtc_config": {
                "status_availability_mask": "0xFF",
                "snapshots": {
                    "standard": {
                        "record_number": "0x01",
                        "dids": ["0xF190"],
                    },
                },
            },
            "dtcs": {
                "0x123456": {
                    "name": "EngineOvertemperature",
                    "sae": "P0217",
                    "description": "Engine coolant too hot",
                    "severity": 4,  # maintenance_only (int value)
                    "snapshots": ["standard"],
                },
            },
        }

        doc = DiagnosticDescription.model_validate(data)
        assert doc.dtc_config is not None
        assert doc.dtc_config.status_availability_mask == 0xFF
        assert doc.dtc_config.snapshots is not None
        assert "standard" in doc.dtc_config.snapshots
        assert doc.dtcs is not None
        assert 0x123456 in doc.dtcs
        assert doc.dtcs[0x123456].sae == "P0217"
        assert doc.dtcs[0x123456].severity == 4

    def test_dtcs_none_by_default(self) -> None:
        """Should default DTCs to None when not provided."""
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
        assert doc.dtc_config is None
        assert doc.dtcs is None

    def test_dtc_config_without_dtcs(self) -> None:
        """Should allow dtc_config without dtcs."""
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
            "dtc_config": {
                "status_availability_mask": "0xFF",
            },
        }

        doc = DiagnosticDescription.model_validate(data)
        assert doc.dtc_config is not None
        assert doc.dtcs is None

    def test_multiple_dtcs_in_document(self) -> None:
        """Should parse multiple DTCs in document."""
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
            "dtcs": {
                "0x123456": {"name": "Fault1", "sae": "P0123"},
                "0x234567": {"name": "Fault2", "sae": "B1234"},
                "0x345678": {"name": "Fault3", "sae": "C0001"},
                "0x456789": {"name": "Fault4", "sae": "U0100"},
            },
        }

        doc = DiagnosticDescription.model_validate(data)
        assert doc.dtcs is not None
        assert len(doc.dtcs) == 4
        assert doc.dtcs[0x123456].sae == "P0123"
        assert doc.dtcs[0x234567].sae == "B1234"
        assert doc.dtcs[0x345678].sae == "C0001"
        assert doc.dtcs[0x456789].sae == "U0100"


class TestDTCSnapshotDataRecord:
    """Tests for DTCSnapshotDataRecord model."""

    def test_basic_record(self) -> None:
        """Should create basic snapshot data record."""
        record = DTCSnapshotDataRecord(did=0xF190)
        assert record.did == 0xF190
        assert record.name is None
        assert record.description is None

    def test_with_name(self) -> None:
        """Should allow custom name."""
        record = DTCSnapshotDataRecord(
            did=0xF190,
            name="Vehicle Identification Number",
        )
        assert record.name == "Vehicle Identification Number"

    def test_with_description(self) -> None:
        """Should allow description."""
        record = DTCSnapshotDataRecord(
            did=0xF190,
            name="VIN",
            description="Vehicle ID at fault time",
        )
        assert record.description == "Vehicle ID at fault time"

    def test_hex_string_did(self) -> None:
        """Should parse hex string DID."""
        record = DTCSnapshotDataRecord(did="0xF190")  # type: ignore
        assert record.did == 0xF190


class TestDTCGroup:
    """Tests for DTCGroup model."""

    def test_basic_group(self) -> None:
        """Should create basic DTC group."""
        group = DTCGroup(name="Powertrain DTCs")
        assert group.name == "Powertrain DTCs"
        assert group.description is None
        assert group.group_id is None
        assert group.dtcs == []

    def test_full_group(self) -> None:
        """Should create group with all fields."""
        group = DTCGroup(
            name="Emissions Related",
            description="All emissions-related DTCs",
            group_id=0x000033,
            dtcs=["P0100", "P0101", "P0102"],
        )
        assert group.name == "Emissions Related"
        assert group.description == "All emissions-related DTCs"
        assert group.group_id == 0x000033
        assert len(group.dtcs) == 3

    def test_hex_string_group_id(self) -> None:
        """Should parse hex string group ID."""
        group = DTCGroup(
            name="Test",
            group_id="0x000100",  # type: ignore
        )
        assert group.group_id == 0x000100


class TestDTCConfigEnhanced:
    """Tests for enhanced DTCConfig model."""

    def test_default_snapshots(self) -> None:
        """Should accept default_snapshots field."""
        config = DTCConfig(
            default_snapshots={
                "standard": DTCSnapshotDefinition(
                    record_number=0x01,
                    dids=[0xF190],
                ),
            },
        )
        assert config.default_snapshots is not None
        assert "standard" in config.default_snapshots

    def test_default_extended_data(self) -> None:
        """Should accept default_extended_data field."""
        config = DTCConfig(
            default_extended_data={
                "counter": DTCExtendedDataDefinition(
                    record_number=0x01,
                    name="OccurrenceCounter",
                    type="u8",
                ),
            },
        )
        assert config.default_extended_data is not None
        assert "counter" in config.default_extended_data

    def test_groups(self) -> None:
        """Should accept groups field."""
        config = DTCConfig(
            groups={
                "powertrain": DTCGroup(
                    name="Powertrain DTCs",
                    group_id=0x000100,
                    dtcs=["P0100", "P0101"],
                ),
            },
        )
        assert config.groups is not None
        assert "powertrain" in config.groups
        assert config.groups["powertrain"].group_id == 0x000100


class TestDTCDefinitionEnhanced:
    """Tests for enhanced DTCDefinition fields."""

    def test_functional_unit(self) -> None:
        """Should accept functional_unit field."""
        dtc = DTCDefinition(
            name="Test",
            functional_unit=0x01,
        )
        assert dtc.functional_unit == 0x01

    def test_aging_counter_threshold(self) -> None:
        """Should accept aging_counter_threshold field."""
        dtc = DTCDefinition(
            name="Test",
            aging_counter_threshold=40,
        )
        assert dtc.aging_counter_threshold == 40

    def test_aged_counter_threshold(self) -> None:
        """Should accept aged_counter_threshold field."""
        dtc = DTCDefinition(
            name="Test",
            aged_counter_threshold=200,
        )
        assert dtc.aged_counter_threshold == 200

    def test_priority(self) -> None:
        """Should accept priority field."""
        dtc = DTCDefinition(
            name="Test",
            priority=5,
        )
        assert dtc.priority == 5

    def test_inline_snapshot_definitions(self) -> None:
        """Should accept inline snapshot definitions."""
        dtc = DTCDefinition(
            name="Test",
            snapshots=[
                DTCSnapshotDefinition(
                    record_number=0x01,
                    dids=[0xF190],
                ),
            ],
        )
        assert dtc.snapshots is not None
        assert len(dtc.snapshots) == 1

    def test_inline_extended_data_definitions(self) -> None:
        """Should accept inline extended data definitions."""
        dtc = DTCDefinition(
            name="Test",
            extended_data=[
                DTCExtendedDataDefinition(
                    record_number=0x01,
                    name="Counter",
                    type="u8",
                ),
            ],
        )
        assert dtc.extended_data is not None
        assert len(dtc.extended_data) == 1

    def test_full_dtc_definition(self) -> None:
        """Should create complete DTC definition with all fields."""
        dtc = DTCDefinition(
            name="EngineOvertemperature",
            sae="P0217",
            description="Engine coolant exceeds safe limit",
            severity=1,  # CHECK_IMMEDIATELY (1)
            functional_unit=0x01,
            aging_counter_threshold=40,
            aged_counter_threshold=200,
            priority=5,
            snapshots=[
                DTCSnapshotDefinition(
                    record_number=0x01,
                    data=[
                        DTCSnapshotDataRecord(did=0xF190, name="VIN"),
                    ],
                ),
            ],
            extended_data=[
                DTCExtendedDataDefinition(
                    record_number=0x01,
                    name="OccurrenceCounter",
                    type="u8",
                ),
            ],
        )
        assert dtc.name == "EngineOvertemperature"
        assert dtc.sae == "P0217"
        assert dtc.severity == 1
        assert dtc.functional_unit == 0x01
        assert dtc.aging_counter_threshold == 40
        assert dtc.priority == 5
