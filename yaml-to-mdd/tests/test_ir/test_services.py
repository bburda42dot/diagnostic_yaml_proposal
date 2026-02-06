"""Tests for IR service models."""

from yaml_to_mdd.ir.services import (
    IRDiagService,
    IRParam,
    IRParamType,
    IRRequest,
    IRResponse,
    IRServiceType,
)
from yaml_to_mdd.ir.types import (
    IRDOP,
    IRDataType,
    IRDiagCodedType,
    IRDiagCodedTypeName,
)


class TestIRParamType:
    """Tests for IRParamType enum."""

    def test_values_match_flatbuffers_enum(self) -> None:
        """Verify enum values match FlatBuffers ParamSpecificData."""
        assert IRParamType.NONE.value == 0
        assert IRParamType.CODED_CONST.value == 1
        assert IRParamType.MATCHING_REQUEST_PARAM.value == 3
        assert IRParamType.VALUE.value == 7

    def test_all_expected_types_exist(self) -> None:
        """Verify all required param types are defined."""
        required = [
            "NONE",
            "CODED_CONST",
            "DYNAMIC",
            "MATCHING_REQUEST_PARAM",
            "NRC_CONST",
            "PHYS_CONST",
            "RESERVED",
            "VALUE",
            "TABLE_ENTRY",
            "TABLE_KEY",
            "TABLE_STRUCT",
            "SYSTEM",
            "LENGTH_KEY_REF",
        ]
        for name in required:
            assert hasattr(IRParamType, name), f"Missing IRParamType.{name}"

    def test_none_is_invalid_state(self) -> None:
        """NONE should be 0 to match FlatBuffers default (unset = invalid)."""
        assert IRParamType.NONE.value == 0


class TestIRServiceType:
    """Tests for IRServiceType enum."""

    def test_service_type_values(self) -> None:
        """Should have correct service type values."""
        assert IRServiceType.REQUEST_ONLY.value == 0
        assert IRServiceType.POS_RESPONSE.value == 1
        assert IRServiceType.POS_RESPONSE_WITH_SUBFUNCTION.value == 2
        assert IRServiceType.NEG_RESPONSE.value == 3
        assert IRServiceType.UNKNOWN.value == 255


class TestIRParam:
    """Tests for IRParam dataclass."""

    def test_simple_param(self) -> None:
        """Should create simple parameter."""
        param = IRParam(
            short_name="EngineSpeed",
            byte_position=2,
        )
        assert param.short_name == "EngineSpeed"
        assert param.byte_position == 2

    def test_param_with_all_fields(self) -> None:
        """Should create parameter with all fields."""
        param = IRParam(
            short_name="ServiceID",
            long_name="Service Identifier",
            byte_position=0,
            bit_position=0,
            dop_ref="UInt8_DOP",
            semantic="SERVICE_ID",
        )
        assert param.long_name == "Service Identifier"
        assert param.dop_ref == "UInt8_DOP"
        assert param.semantic == "SERVICE_ID"

    def test_param_default_values(self) -> None:
        """Should have correct default values."""
        param = IRParam(short_name="Test")
        assert param.byte_position is None  # Changed from 0 to None for byte parity
        assert param.bit_position is None
        assert param.dop_ref is None

    def test_param_is_frozen(self) -> None:
        """Param should be immutable."""
        param = IRParam(short_name="Test")
        try:
            param.short_name = "Changed"  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass  # Expected


class TestIRParamExtended:
    """Tests for extended IRParam with param_type."""

    def test_default_param_type_is_value(self) -> None:
        """Default param_type should be VALUE."""
        param = IRParam(short_name="test")
        assert param.param_type == IRParamType.VALUE

    def test_coded_const_param(self) -> None:
        """Create a CODED_CONST param with all fields."""
        diag_type = IRDiagCodedType(
            type_name=IRDiagCodedTypeName.STANDARD_LENGTH_TYPE,
            base_data_type=IRDataType.A_UINT_32,
            bit_length=8,
        )
        param = IRParam(
            short_name="SID_RQ",
            byte_position=0,
            semantic="SERVICE_ID",
            param_type=IRParamType.CODED_CONST,
            coded_value=0x22,
            coded_diag_type=diag_type,
            bit_length=8,
        )
        assert param.param_type == IRParamType.CODED_CONST
        assert param.coded_value == 0x22
        assert param.coded_diag_type is not None

    def test_matching_request_param(self) -> None:
        """Create a MATCHING_REQUEST_PARAM."""
        param = IRParam(
            short_name="DID_PR",
            byte_position=1,
            semantic="DID",
            param_type=IRParamType.MATCHING_REQUEST_PARAM,
            matching_request_byte_pos=1,
            matching_byte_length=2,
        )
        assert param.param_type == IRParamType.MATCHING_REQUEST_PARAM
        assert param.matching_request_byte_pos == 1
        assert param.matching_byte_length == 2

    def test_value_param_with_dop(self) -> None:
        """Create a VALUE param with full DOP."""
        dop = IRDOP(short_name="DOP_Identification")
        param = IRParam(
            short_name="Identification",
            byte_position=3,
            semantic="DATA",
            param_type=IRParamType.VALUE,
            dop=dop,
        )
        assert param.param_type == IRParamType.VALUE
        assert param.dop is not None
        assert param.dop.short_name == "DOP_Identification"

    def test_backward_compat_dop_ref(self) -> None:
        """dop_ref should still work for backward compatibility."""
        param = IRParam(
            short_name="test",
            dop_ref="some_dop",
        )
        assert param.dop_ref == "some_dop"


class TestIRRequest:
    """Tests for IRRequest dataclass."""

    def test_empty_request(self) -> None:
        """Should create request with no parameters."""
        request = IRRequest(short_name="EmptyRequest")
        assert request.short_name == "EmptyRequest"
        assert request.params == ()

    def test_request_with_params(self) -> None:
        """Should create request with parameters."""
        params = (
            IRParam(short_name="ServiceID", byte_position=0, semantic="SERVICE_ID"),
            IRParam(short_name="DID", byte_position=1, semantic="DATA"),
        )
        request = IRRequest(
            short_name="ReadDID_Request",
            params=params,
        )
        assert len(request.params) == 2
        assert request.params[0].semantic == "SERVICE_ID"

    def test_request_with_constant_prefix(self) -> None:
        """Should create request with constant prefix."""
        request = IRRequest(
            short_name="ReadDID_Request",
            constant_prefix=b"\x22\xf1\x90",
        )
        assert request.constant_prefix == b"\x22\xf1\x90"

    def test_request_is_frozen(self) -> None:
        """Request should be immutable."""
        request = IRRequest(short_name="Test")
        try:
            request.short_name = "Changed"  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass  # Expected


class TestIRResponse:
    """Tests for IRResponse dataclass."""

    def test_empty_response(self) -> None:
        """Should create response with no parameters."""
        response = IRResponse(short_name="EmptyResponse")
        assert response.short_name == "EmptyResponse"
        assert response.params == ()

    def test_response_with_params(self) -> None:
        """Should create response with parameters."""
        params = (
            IRParam(short_name="ServiceID", byte_position=0),
            IRParam(short_name="DID", byte_position=1),
            IRParam(short_name="Data", byte_position=3),
        )
        response = IRResponse(
            short_name="ReadDID_Response",
            params=params,
        )
        assert len(response.params) == 3

    def test_response_with_constant_prefix(self) -> None:
        """Should create response with constant prefix."""
        response = IRResponse(
            short_name="ReadDID_Response",
            constant_prefix=b"\x62\xf1\x90",
        )
        assert response.constant_prefix == b"\x62\xf1\x90"


class TestIRDiagService:
    """Tests for IRDiagService dataclass."""

    def test_minimal_service(self) -> None:
        """Should create minimal service."""
        service = IRDiagService(
            short_name="TestService",
            service_id=0x22,
        )
        assert service.short_name == "TestService"
        assert service.service_id == 0x22

    def test_read_did_service(self) -> None:
        """Should create ReadDataByIdentifier service."""
        service = IRDiagService(
            short_name="ReadDID_0xF190",
            service_id=0x22,
            service_type=IRServiceType.POS_RESPONSE,
            required_sessions=("default", "extended"),
        )
        assert service.service_id == 0x22
        assert "default" in service.required_sessions
        assert "extended" in service.required_sessions

    def test_service_with_subfunction(self) -> None:
        """Should create service with subfunction."""
        service = IRDiagService(
            short_name="DiagnosticSession_Extended",
            service_id=0x10,
            subfunction=0x03,
            service_type=IRServiceType.POS_RESPONSE_WITH_SUBFUNCTION,
        )
        assert service.subfunction == 0x03
        assert service.service_type == IRServiceType.POS_RESPONSE_WITH_SUBFUNCTION

    def test_service_with_request_response(self) -> None:
        """Should create service with request and response."""
        request = IRRequest(
            short_name="ReadDID_Request",
            params=(IRParam(short_name="DID", byte_position=1),),
        )
        response = IRResponse(
            short_name="ReadDID_PosResponse",
            params=(
                IRParam(short_name="DID", byte_position=1),
                IRParam(short_name="Data", byte_position=3),
            ),
        )
        service = IRDiagService(
            short_name="ReadDID",
            service_id=0x22,
            request=request,
            positive_response=response,
        )
        assert service.request is not None
        assert service.positive_response is not None
        assert len(service.positive_response.params) == 2

    def test_service_with_security(self) -> None:
        """Should create service with security requirements."""
        service = IRDiagService(
            short_name="WriteData",
            service_id=0x2E,
            required_security=("level1", "level3"),
        )
        assert "level1" in service.required_security
        assert "level3" in service.required_security

    def test_service_with_addressing(self) -> None:
        """Should create service with addressing mode."""
        service = IRDiagService(
            short_name="TesterPresent",
            service_id=0x3E,
            addressing_mode="both",
        )
        assert service.addressing_mode == "both"

    def test_service_default_values(self) -> None:
        """Should have correct default values."""
        service = IRDiagService(
            short_name="Test",
            service_id=0x22,
        )
        assert service.service_type == IRServiceType.POS_RESPONSE
        assert service.addressing_mode == "physical"
        assert service.required_sessions == ()
        assert service.required_security == ()

    def test_service_with_audience(self) -> None:
        """Should create service with audience filtering."""
        service = IRDiagService(
            short_name="DebugService",
            service_id=0xFE,
            audience_enabled=("development", "aftermarket"),
            audience_disabled=("production",),
        )
        assert "development" in service.audience_enabled  # type: ignore[operator]
        assert "production" in service.audience_disabled  # type: ignore[operator]

    def test_service_is_hashable(self) -> None:
        """Service should be hashable."""
        svc1 = IRDiagService(short_name="Svc1", service_id=0x22)
        svc2 = IRDiagService(short_name="Svc2", service_id=0x2E)
        svc_set = {svc1, svc2}
        assert len(svc_set) == 2

    def test_service_hash_includes_subfunction(self) -> None:
        """Services with different subfunctions should have different hashes."""
        svc1 = IRDiagService(short_name="Session", service_id=0x10, subfunction=0x01)
        svc2 = IRDiagService(short_name="Session", service_id=0x10, subfunction=0x03)
        assert hash(svc1) != hash(svc2)

    def test_service_is_frozen(self) -> None:
        """Service should be immutable."""
        service = IRDiagService(short_name="Test", service_id=0x22)
        try:
            service.service_id = 0x2E  # type: ignore[misc]
            raise AssertionError("Expected FrozenInstanceError")
        except AttributeError:
            pass  # Expected
