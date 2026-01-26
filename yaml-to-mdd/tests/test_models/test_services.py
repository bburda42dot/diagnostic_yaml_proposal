"""Tests for services model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from yaml_to_mdd.models.services import (
    AddressingMode,
    AuthenticationConfig,
    BaseServiceConfig,
    ClearDiagnosticInformationConfig,
    CommunicationControlConfig,
    ControlDTCSettingConfig,
    CustomServiceDefinition,
    DiagnosticSessionControlConfig,
    EcuResetConfig,
    LinkControlConfig,
    ReadDataByIdentifierConfig,
    ReadDTCInformationConfig,
    ResponseOnEventConfig,
    RoutineControlConfig,
    SecurityAccessConfig,
    ServiceRequestLayout,
    Services,
    StateEffect,
    StateEffects,
    TesterPresentConfig,
    WriteDataByIdentifierConfig,
)


class TestAddressingMode:
    """Tests for AddressingMode enum."""

    def test_addressing_mode_values(self) -> None:
        """Test that AddressingMode has expected values."""
        assert AddressingMode.PHYSICAL == "physical"
        assert AddressingMode.FUNCTIONAL == "functional"
        assert AddressingMode.BOTH == "both"

    def test_addressing_mode_from_string(self) -> None:
        """Test creating AddressingMode from string."""
        assert AddressingMode("physical") == AddressingMode.PHYSICAL
        assert AddressingMode("functional") == AddressingMode.FUNCTIONAL
        assert AddressingMode("both") == AddressingMode.BOTH


class TestStateEffect:
    """Tests for StateEffect model."""

    def test_minimal_state_effect(self) -> None:
        """Test StateEffect with no properties set."""
        effect = StateEffect()
        assert effect.session is None
        assert effect.security is None
        assert effect.authentication_role is None

    def test_state_effect_with_session(self) -> None:
        """Test StateEffect with session."""
        effect = StateEffect(session="extended")
        assert effect.session == "extended"
        assert effect.security is None

    def test_state_effect_with_security(self) -> None:
        """Test StateEffect with security."""
        effect = StateEffect(security="level_1")
        assert effect.session is None
        assert effect.security == "level_1"

    def test_state_effect_with_all(self) -> None:
        """Test StateEffect with all fields."""
        effect = StateEffect(
            session="extended",
            security="level_2",
            authentication_role="admin",
        )
        assert effect.session == "extended"
        assert effect.security == "level_2"
        assert effect.authentication_role == "admin"

    def test_state_effect_extra_forbid(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            StateEffect(unknown_field="value")  # type: ignore[call-arg]


class TestStateEffects:
    """Tests for StateEffects model."""

    def test_minimal_state_effects(self) -> None:
        """Test StateEffects with no effects."""
        effects = StateEffects()
        assert effects.on_success is None
        assert effects.on_unlock is None
        assert effects.on_authenticate is None
        assert effects.on_deauthenticate is None

    def test_state_effects_on_success(self) -> None:
        """Test StateEffects with on_success effect."""
        effects = StateEffects(on_success=StateEffect(session="extended"))
        assert effects.on_success is not None
        assert effects.on_success.session == "extended"

    def test_state_effects_multiple(self) -> None:
        """Test StateEffects with multiple effects."""
        effects = StateEffects(
            on_success=StateEffect(session="extended"),
            on_unlock=StateEffect(security="unlocked"),
        )
        assert effects.on_success is not None
        assert effects.on_unlock is not None


class TestBaseServiceConfig:
    """Tests for BaseServiceConfig model."""

    def test_enabled_required(self) -> None:
        """Test that enabled field is required."""
        with pytest.raises(ValidationError, match="enabled"):
            BaseServiceConfig()  # type: ignore[call-arg]

    def test_minimal_config(self) -> None:
        """Test BaseServiceConfig with only enabled field."""
        config = BaseServiceConfig(enabled=True)
        assert config.enabled is True
        assert config.addressing_mode is None
        assert config.request_layout is None

    def test_full_config(self) -> None:
        """Test BaseServiceConfig with all fields."""
        config = BaseServiceConfig(
            enabled=True,
            addressing_mode=AddressingMode.BOTH,
            request_layout=ServiceRequestLayout(params=[{"name": "param1"}]),
        )
        assert config.enabled is True
        assert config.addressing_mode == AddressingMode.BOTH
        assert config.request_layout is not None


class TestDiagnosticSessionControlConfig:
    """Tests for DiagnosticSessionControlConfig model."""

    def test_minimal_config(self) -> None:
        """Test minimal DiagnosticSessionControlConfig."""
        config = DiagnosticSessionControlConfig(enabled=True)
        assert config.enabled is True
        assert config.subfunctions is None
        assert config.state_effects is None

    def test_with_subfunctions_dict(self) -> None:
        """Test with subfunctions as dict."""
        config = DiagnosticSessionControlConfig(
            enabled=True,
            subfunctions={"default": 0x01, "extended": 0x03},
        )
        assert config.subfunctions == {"default": 0x01, "extended": 0x03}

    def test_with_subfunctions_list(self) -> None:
        """Test with subfunctions as list."""
        config = DiagnosticSessionControlConfig(
            enabled=True,
            subfunctions=[0x01, 0x03],
        )
        assert config.subfunctions == [0x01, 0x03]

    def test_with_state_effects(self) -> None:
        """Test with state effects."""
        config = DiagnosticSessionControlConfig(
            enabled=True,
            state_effects=StateEffects(on_success=StateEffect(session="extended")),
        )
        assert config.state_effects is not None
        assert config.state_effects.on_success is not None


class TestSecurityAccessConfig:
    """Tests for SecurityAccessConfig model."""

    def test_minimal_config(self) -> None:
        """Test minimal SecurityAccessConfig."""
        config = SecurityAccessConfig(enabled=True)
        assert config.enabled is True
        assert config.subfunctions is None

    def test_with_subfunctions(self) -> None:
        """Test with subfunctions."""
        config = SecurityAccessConfig(
            enabled=True,
            subfunctions={"requestSeed": 0x01, "sendKey": 0x02},
        )
        assert config.subfunctions == {"requestSeed": 0x01, "sendKey": 0x02}


class TestCommunicationControlConfig:
    """Tests for CommunicationControlConfig model."""

    def test_with_communication_types(self) -> None:
        """Test with communication types."""
        config = CommunicationControlConfig(
            enabled=True,
            communication_types=[0x01, 0x02, 0x03],
        )
        assert config.communication_types == [0x01, 0x02, 0x03]

    def test_with_nrc_on_fail(self) -> None:
        """Test with NRC on fail."""
        config = CommunicationControlConfig(
            enabled=True,
            nrc_on_fail=0x22,
        )
        assert config.nrc_on_fail == 0x22


class TestResponseOnEventConfig:
    """Tests for ResponseOnEventConfig model."""

    def test_with_max_active_events(self) -> None:
        """Test with max active events."""
        config = ResponseOnEventConfig(
            enabled=True,
            max_active_events=5,
        )
        assert config.max_active_events == 5

    def test_max_active_events_range(self) -> None:
        """Test max_active_events range validation."""
        # Valid range
        config = ResponseOnEventConfig(enabled=True, max_active_events=255)
        assert config.max_active_events == 255

        # Invalid - too high
        with pytest.raises(ValidationError, match="max_active_events"):
            ResponseOnEventConfig(enabled=True, max_active_events=256)

        # Invalid - negative
        with pytest.raises(ValidationError, match="max_active_events"):
            ResponseOnEventConfig(enabled=True, max_active_events=-1)


class TestCustomServiceDefinition:
    """Tests for CustomServiceDefinition model."""

    def test_minimal_custom_service(self) -> None:
        """Test minimal custom service definition."""
        service = CustomServiceDefinition(
            sid=0x80,
            name="CustomService",
        )
        assert service.sid == 0x80
        assert service.name == "CustomService"
        assert service.description is None

    def test_full_custom_service(self) -> None:
        """Test full custom service definition."""
        service = CustomServiceDefinition(
            sid=0x80,
            name="CustomService",
            description="A custom OEM service",
            addressing_mode=AddressingMode.PHYSICAL,
            access_pattern="developerAccess",
        )
        assert service.sid == 0x80
        assert service.name == "CustomService"
        assert service.description == "A custom OEM service"
        assert service.addressing_mode == AddressingMode.PHYSICAL
        assert service.access_pattern == "developerAccess"


class TestServices:
    """Tests for Services container model."""

    def test_empty_services(self) -> None:
        """Test Services with no services configured."""
        services = Services()
        assert services.diagnosticSessionControl is None
        assert services.readDataByIdentifier is None
        assert services.securityAccess is None

    def test_single_service(self) -> None:
        """Test Services with single service."""
        services = Services(diagnosticSessionControl=DiagnosticSessionControlConfig(enabled=True))
        assert services.diagnosticSessionControl is not None
        assert services.diagnosticSessionControl.enabled is True

    def test_multiple_services(self) -> None:
        """Test Services with multiple services."""
        services = Services(
            diagnosticSessionControl=DiagnosticSessionControlConfig(enabled=True),
            readDataByIdentifier=ReadDataByIdentifierConfig(enabled=True),
            securityAccess=SecurityAccessConfig(
                enabled=True,
                subfunctions={"requestSeed": 0x01},
            ),
        )
        assert services.diagnosticSessionControl is not None
        assert services.readDataByIdentifier is not None
        assert services.securityAccess is not None

    def test_with_custom_services(self) -> None:
        """Test Services with custom services."""
        services = Services(
            diagnosticSessionControl=DiagnosticSessionControlConfig(enabled=True),
            custom={
                "oemService1": CustomServiceDefinition(
                    sid=0x80,
                    name="OEM Service 1",
                ),
                "oemService2": CustomServiceDefinition(
                    sid=0x81,
                    name="OEM Service 2",
                ),
            },
        )
        assert services.custom is not None
        assert "oemService1" in services.custom
        assert "oemService2" in services.custom

    def test_services_extra_forbid(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            Services(unknownService={"enabled": True})  # type: ignore[call-arg]


class TestServicesIntegration:
    """Integration tests for Services model."""

    def test_full_services_example(self) -> None:
        """Test a realistic services configuration."""
        services = Services(
            diagnosticSessionControl=DiagnosticSessionControlConfig(
                enabled=True,
                addressing_mode=AddressingMode.BOTH,
                subfunctions={"default": 0x01, "extended": 0x03, "programming": 0x02},
                state_effects=StateEffects(on_success=StateEffect(session="extended")),
            ),
            ecuReset=EcuResetConfig(
                enabled=True,
                subfunctions={"hardReset": 0x01, "keyOffOnReset": 0x02},
            ),
            securityAccess=SecurityAccessConfig(
                enabled=True,
                subfunctions={"requestSeed_L1": 0x01, "sendKey_L1": 0x02},
                state_effects=StateEffects(on_unlock=StateEffect(security="unlocked")),
            ),
            readDataByIdentifier=ReadDataByIdentifierConfig(enabled=True),
            writeDataByIdentifier=WriteDataByIdentifierConfig(enabled=False),
            routineControl=RoutineControlConfig(
                enabled=True,
                subfunctions=["startRoutine", "stopRoutine", "requestResults"],
            ),
            testerPresent=TesterPresentConfig(
                enabled=True,
                addressing_mode=AddressingMode.FUNCTIONAL,
            ),
            controlDTCSetting=ControlDTCSettingConfig(enabled=True),
            clearDiagnosticInformation=ClearDiagnosticInformationConfig(enabled=True),
            readDTCInformation=ReadDTCInformationConfig(
                enabled=True,
                subfunctions=[
                    0x01,
                    0x02,
                ],  # reportNumberOfDTCByStatusMask, reportDTCByStatusMask
            ),
        )

        # Verify structure
        assert services.diagnosticSessionControl is not None
        assert services.diagnosticSessionControl.subfunctions == {
            "default": 0x01,
            "extended": 0x03,
            "programming": 0x02,
        }
        assert services.ecuReset is not None
        assert services.securityAccess is not None
        assert services.readDataByIdentifier is not None
        assert services.writeDataByIdentifier is not None
        assert services.writeDataByIdentifier.enabled is False
        assert services.routineControl is not None
        assert services.testerPresent is not None
        assert services.testerPresent.addressing_mode == AddressingMode.FUNCTIONAL


class TestServicesAllConfigs:
    """Tests ensuring all service config types work."""

    @pytest.mark.parametrize(
        "config_class",
        [
            DiagnosticSessionControlConfig,
            EcuResetConfig,
            SecurityAccessConfig,
            CommunicationControlConfig,
            AuthenticationConfig,
            TesterPresentConfig,
            ControlDTCSettingConfig,
            ResponseOnEventConfig,
            LinkControlConfig,
            ReadDataByIdentifierConfig,
            WriteDataByIdentifierConfig,
            RoutineControlConfig,
            ReadDTCInformationConfig,
            ClearDiagnosticInformationConfig,
        ],
    )
    def test_all_service_configs_enabled_required(
        self, config_class: type[BaseServiceConfig]
    ) -> None:
        """Test all service configs require enabled field."""
        with pytest.raises(ValidationError, match="enabled"):
            config_class()  # type: ignore[call-arg]

    @pytest.mark.parametrize(
        "config_class",
        [
            DiagnosticSessionControlConfig,
            EcuResetConfig,
            SecurityAccessConfig,
            CommunicationControlConfig,
            AuthenticationConfig,
            TesterPresentConfig,
            ControlDTCSettingConfig,
            ResponseOnEventConfig,
            LinkControlConfig,
            ReadDataByIdentifierConfig,
            WriteDataByIdentifierConfig,
            RoutineControlConfig,
            ReadDTCInformationConfig,
            ClearDiagnosticInformationConfig,
        ],
    )
    def test_all_service_configs_minimal(self, config_class: type[BaseServiceConfig]) -> None:
        """Test all service configs can be created with just enabled."""
        config = config_class(enabled=True)
        assert config.enabled is True
        assert config.addressing_mode is None
