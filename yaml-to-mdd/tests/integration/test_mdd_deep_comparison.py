"""Deep MDD structure comparison tests.

These tests compare detailed internal structures between YAML-generated
and ODX-generated MDD files to identify specific differences.

Run with: pytest tests/integration/test_mdd_deep_comparison.py -v -s
"""

from __future__ import annotations

import gzip
import lzma
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from yaml_to_mdd.converters.mdd_writer import FILE_MAGIC, convert_yaml_to_mdd
from yaml_to_mdd.fbs_generated.dataformat.EcuData import EcuData
from yaml_to_mdd.fbs_generated.dataformat.ParamSpecificData import ParamSpecificData
from yaml_to_mdd.proto_generated import MDDFile

# Path to golden test files
GOLDEN_DIR = Path(__file__).parent / "golden"


@dataclass
class ParamDetail:
    """Detailed parameter information."""

    short_name: str
    byte_position: int | None = None
    bit_position: int | None = None
    semantic: str | None = None
    specific_data_type: int = 0  # ParamSpecificData enum
    # CodedConst details
    coded_value: str | None = None
    diag_coded_type_base: int | None = None  # DataType enum
    diag_coded_type_bit_length: int | None = None
    # Value details
    has_dop: bool = False


@dataclass
class ServiceDetail:
    """Detailed service information."""

    short_name: str
    request_params: list[ParamDetail] = field(default_factory=list)
    pos_response_count: int = 0
    neg_response_count: int = 0
    pos_response_params: list[list[ParamDetail]] = field(default_factory=list)


@dataclass
class VariantDetail:
    """Detailed variant information."""

    short_name: str
    is_base_variant: bool = False
    services_count: int = 0
    state_charts_count: int = 0
    com_param_refs_count: int = 0
    parent_refs_count: int = 0
    pattern_count: int = 0
    matching_params: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class DeepMDDStructure:
    """Deep structure analysis of MDD file."""

    # File-level info
    file_size: int = 0
    ecu_name: str = ""
    revision: str = ""
    chunk_count: int = 0
    chunk_compression: str = ""
    chunk_data_size: int = 0
    decompressed_size: int = 0

    # Variant details
    variants_count: int = 0
    variants: list[VariantDetail] = field(default_factory=list)

    # Service details (from base variant)
    services: dict[str, ServiceDetail] = field(default_factory=dict)

    # Protocol info
    has_protocol_refs: bool = False

    # EcuSharedData
    has_ecu_shared_data: bool = False
    shared_data_dops_count: int = 0


def parse_mdd_deep(mdd_path: Path) -> DeepMDDStructure:
    """Parse MDD file and extract deep structure details."""
    with open(mdd_path, "rb") as f:
        raw_data = f.read()

    structure = DeepMDDStructure(file_size=len(raw_data))

    if not raw_data.startswith(FILE_MAGIC):
        raise ValueError(f"Invalid MDD file: {mdd_path}")

    # Parse protobuf
    mdd = MDDFile()
    mdd.ParseFromString(raw_data[len(FILE_MAGIC) :])

    structure.ecu_name = mdd.ecu_name
    structure.revision = mdd.revision
    structure.chunk_count = len(mdd.chunks)

    # Find and decompress diagnostic chunk
    fbs_data = None
    for chunk in mdd.chunks:
        if chunk.type == 0 or chunk.name == "diagnostic_description":
            structure.chunk_compression = chunk.compression_algorithm or "none"
            structure.chunk_data_size = len(chunk.data)

            if chunk.compression_algorithm == "lzma":
                fbs_data = lzma.decompress(chunk.data)
            elif chunk.compression_algorithm == "gzip":
                fbs_data = gzip.decompress(chunk.data)
            else:
                fbs_data = chunk.data

            structure.decompressed_size = len(fbs_data)
            break

    if fbs_data is None:
        return structure

    # Parse FlatBuffers
    ecu_data = EcuData.GetRootAs(fbs_data, 0)

    # Parse variants
    structure.variants_count = ecu_data.VariantsLength()

    for i in range(ecu_data.VariantsLength()):
        variant = ecu_data.Variants(i)
        if variant is None:
            continue

        diag_layer = variant.DiagLayer()
        v_detail = VariantDetail(
            short_name=(
                diag_layer.ShortName().decode()
                if diag_layer and diag_layer.ShortName()
                else f"variant_{i}"
            ),
            is_base_variant=variant.IsBaseVariant(),
        )

        if diag_layer:
            v_detail.services_count = diag_layer.DiagServicesLength()
            v_detail.state_charts_count = diag_layer.StateChartsLength()
            v_detail.com_param_refs_count = diag_layer.ComParamRefsLength()

        # Parent refs
        if hasattr(variant, "ParentRefsLength"):
            v_detail.parent_refs_count = variant.ParentRefsLength()
            if v_detail.parent_refs_count > 0:
                structure.has_protocol_refs = True

        # Variant patterns
        v_detail.pattern_count = variant.VariantPatternLength()
        for j in range(variant.VariantPatternLength()):
            pattern = variant.VariantPattern(j)
            if pattern:
                # Handle both schema versions
                mp_length = 0
                get_mp = None
                if hasattr(pattern, "MatchingParametersLength"):
                    mp_length = pattern.MatchingParametersLength()
                    get_mp = pattern.MatchingParameters
                elif hasattr(pattern, "MatchingParameterLength"):
                    mp_length = pattern.MatchingParameterLength()
                    get_mp = pattern.MatchingParameter

                for k in range(mp_length):
                    mp = get_mp(k) if get_mp else None
                    if mp:
                        mp_info: dict[str, Any] = {
                            "expected_value": (
                                mp.ExpectedValue().decode()
                                if mp.ExpectedValue()
                                else None
                            ),
                            "has_diag_service": mp.DiagService() is not None,
                            "has_out_param": mp.OutParam() is not None,
                        }
                        if mp.DiagService():
                            dc = mp.DiagService().DiagComm()
                            mp_info["diag_service_name"] = (
                                dc.ShortName().decode()
                                if dc and dc.ShortName()
                                else None
                            )
                        if mp.OutParam():
                            out_param = mp.OutParam()
                            mp_info["out_param_name"] = (
                                out_param.ShortName().decode()
                                if out_param and out_param.ShortName()
                                else None
                            )
                        v_detail.matching_params.append(mp_info)

        structure.variants.append(v_detail)

        # Extract services from base variant
        if variant.IsBaseVariant() and diag_layer:
            _extract_services_deep(diag_layer, structure)

    # EcuSharedData
    if hasattr(ecu_data, "EcuSharedData"):
        ecu_shared = ecu_data.EcuSharedData()
        if ecu_shared:
            structure.has_ecu_shared_data = True
            if hasattr(ecu_shared, "DopsLength"):
                structure.shared_data_dops_count = ecu_shared.DopsLength()

    return structure


def _extract_services_deep(diag_layer: Any, structure: DeepMDDStructure) -> None:
    """Extract detailed service information."""
    from yaml_to_mdd.fbs_generated.dataformat.CodedConst import CodedConst
    from yaml_to_mdd.fbs_generated.dataformat.StandardLengthType import (
        StandardLengthType,
    )
    from yaml_to_mdd.fbs_generated.dataformat.Value import Value

    for i in range(diag_layer.DiagServicesLength()):
        service = diag_layer.DiagServices(i)
        if service is None:
            continue

        dc = service.DiagComm()
        svc_name = dc.ShortName().decode() if dc and dc.ShortName() else f"service_{i}"

        svc_detail = ServiceDetail(short_name=svc_name)

        # Request params
        request = service.Request()
        if request:
            for j in range(request.ParamsLength()):
                param = request.Params(j)
                if param:
                    p_detail = _extract_param_detail(param)
                    svc_detail.request_params.append(p_detail)

        # Positive responses
        svc_detail.pos_response_count = service.PosResponsesLength()
        for j in range(service.PosResponsesLength()):
            resp = service.PosResponses(j)
            if resp:
                resp_params: list[ParamDetail] = []
                for k in range(resp.ParamsLength()):
                    param = resp.Params(k)
                    if param:
                        resp_params.append(_extract_param_detail(param))
                svc_detail.pos_response_params.append(resp_params)

        # Negative responses
        svc_detail.neg_response_count = service.NegResponsesLength()

        structure.services[svc_name] = svc_detail


def _extract_param_detail(param: Any) -> ParamDetail:
    """Extract detailed parameter information."""
    from yaml_to_mdd.fbs_generated.dataformat.CodedConst import CodedConst
    from yaml_to_mdd.fbs_generated.dataformat.StandardLengthType import (
        StandardLengthType,
    )
    from yaml_to_mdd.fbs_generated.dataformat.Value import Value

    p = ParamDetail(
        short_name=param.ShortName().decode() if param.ShortName() else "?",
        byte_position=param.BytePosition(),
        bit_position=param.BitPosition(),
        semantic=param.Semantic().decode() if param.Semantic() else None,
        specific_data_type=param.SpecificDataType(),
    )

    # Extract CodedConst details
    if param.SpecificDataType() == ParamSpecificData.CodedConst:
        sd = param.SpecificData()
        if sd:
            cc = CodedConst()
            cc.Init(sd.Bytes, sd.Pos)
            p.coded_value = cc.CodedValue().decode() if cc.CodedValue() else None
            dct = cc.DiagCodedType()
            if dct:
                p.diag_coded_type_base = dct.BaseDataType()
                # Try to get bit length from StandardLengthType
                if dct.SpecificDataType() == 4:  # StandardLengthType
                    slt_data = dct.SpecificData()
                    if slt_data:
                        slt = StandardLengthType()
                        slt.Init(slt_data.Bytes, slt_data.Pos)
                        p.diag_coded_type_bit_length = slt.BitLength()

    # Check for Value with DOP
    elif param.SpecificDataType() == ParamSpecificData.Value:
        sd = param.SpecificData()
        if sd:
            val = Value()
            val.Init(sd.Bytes, sd.Pos)
            p.has_dop = val.Dop() is not None

    return p


class TestTestcontainerMDDComparison:
    """Direct comparison of testcontainer MDD files (ODX vs YAML generated)."""

    TESTCONTAINER_DIR = Path(
        "/home/bartosz-burda/workspace/classic-diagnostic-adapter/testcontainer"
    )

    @pytest.fixture
    def flxc1000_odx_mdd(self) -> Path:
        """FLXC1000 ODX-generated MDD."""
        path = self.TESTCONTAINER_DIR / "odx" / "FLXC1000.mdd"
        if not path.exists():
            pytest.skip(f"ODX MDD not found: {path}")
        return path

    @pytest.fixture
    def flxc1000_yaml_mdd(self) -> Path:
        """FLXC1000 YAML-generated MDD."""
        path = self.TESTCONTAINER_DIR / "yaml" / "FLXC1000_yaml.mdd"
        if not path.exists():
            pytest.skip(f"YAML MDD not found: {path}")
        return path

    @pytest.fixture
    def odx_structure(self, flxc1000_odx_mdd: Path) -> DeepMDDStructure:
        """Parse ODX-generated MDD."""
        return parse_mdd_deep(flxc1000_odx_mdd)

    @pytest.fixture
    def yaml_structure(self, flxc1000_yaml_mdd: Path) -> DeepMDDStructure:
        """Parse YAML-generated MDD."""
        return parse_mdd_deep(flxc1000_yaml_mdd)

    def test_file_sizes_testcontainer(
        self, flxc1000_odx_mdd: Path, flxc1000_yaml_mdd: Path
    ) -> None:
        """Compare file sizes of testcontainer MDDs."""
        odx_size = flxc1000_odx_mdd.stat().st_size
        yaml_size = flxc1000_yaml_mdd.stat().st_size
        diff = abs(odx_size - yaml_size)

        print(f"\n=== TESTCONTAINER FILE SIZE COMPARISON ===")
        print(f"ODX MDD:  {odx_size} bytes")
        print(f"YAML MDD: {yaml_size} bytes")
        print(f"Difference: {diff} bytes ({diff * 100 / odx_size:.2f}%)")

    def test_decompressed_sizes_testcontainer(
        self, odx_structure: DeepMDDStructure, yaml_structure: DeepMDDStructure
    ) -> None:
        """Compare decompressed FlatBuffers sizes."""
        diff = abs(odx_structure.decompressed_size - yaml_structure.decompressed_size)

        print(f"\n=== DECOMPRESSED SIZE COMPARISON ===")
        print(f"ODX:  {odx_structure.decompressed_size} bytes")
        print(f"YAML: {yaml_structure.decompressed_size} bytes")
        print(f"Difference: {diff} bytes")

    def test_variant_details_testcontainer(
        self, odx_structure: DeepMDDStructure, yaml_structure: DeepMDDStructure
    ) -> None:
        """Compare variant details from testcontainer MDDs."""
        print(f"\n=== VARIANT DETAILS (TESTCONTAINER) ===")
        print(
            f"{'Source':<6} {'Name':<30} {'Base':<6} {'Svcs':<6} {'Charts':<8} {'ComParams':<10} {'Parents':<8} {'Patterns':<10}"
        )
        print("-" * 94)

        for v in odx_structure.variants:
            print(
                f"ODX   {v.short_name:<30} {str(v.is_base_variant):<6} "
                f"{v.services_count:<6} {v.state_charts_count:<8} "
                f"{v.com_param_refs_count:<10} {v.parent_refs_count:<8} {v.pattern_count:<10}"
            )

        print("-" * 94)

        for v in yaml_structure.variants:
            print(
                f"YAML  {v.short_name:<30} {str(v.is_base_variant):<6} "
                f"{v.services_count:<6} {v.state_charts_count:<8} "
                f"{v.com_param_refs_count:<10} {v.parent_refs_count:<8} {v.pattern_count:<10}"
            )

    def test_service_count_testcontainer(
        self, odx_structure: DeepMDDStructure, yaml_structure: DeepMDDStructure
    ) -> None:
        """Compare service counts from testcontainer MDDs."""
        odx_services = set(odx_structure.services.keys())
        yaml_services = set(yaml_structure.services.keys())

        print(f"\n=== SERVICE COUNT (TESTCONTAINER) ===")
        print(f"ODX services:  {len(odx_services)}")
        print(f"YAML services: {len(yaml_services)}")

        common = odx_services & yaml_services
        missing = odx_services - yaml_services
        extra = yaml_services - odx_services

        print(f"Common:  {len(common)}")
        if missing:
            print(f"Missing in YAML: {sorted(missing)}")
        if extra:
            print(f"Extra in YAML:   {sorted(extra)}")

    def test_service_request_params_testcontainer(
        self, odx_structure: DeepMDDStructure, yaml_structure: DeepMDDStructure
    ) -> None:
        """Compare service request parameters from testcontainer MDDs."""
        print(f"\n=== SERVICE REQUEST PARAMETERS (TESTCONTAINER) ===")

        common_services = set(odx_structure.services.keys()) & set(
            yaml_structure.services.keys()
        )

        for svc_name in sorted(common_services)[:8]:
            odx_svc = odx_structure.services[svc_name]
            yaml_svc = yaml_structure.services[svc_name]

            print(f"\n{svc_name}:")
            print(f"  ODX params:  {len(odx_svc.request_params)}")
            print(f"  YAML params: {len(yaml_svc.request_params)}")

            max_params = max(len(odx_svc.request_params), len(yaml_svc.request_params))
            for i in range(max_params):
                odx_p = (
                    odx_svc.request_params[i]
                    if i < len(odx_svc.request_params)
                    else None
                )
                yaml_p = (
                    yaml_svc.request_params[i]
                    if i < len(yaml_svc.request_params)
                    else None
                )

                if odx_p and yaml_p:
                    # Check if they differ
                    differs = (
                        odx_p.short_name != yaml_p.short_name
                        or odx_p.byte_position != yaml_p.byte_position
                        or odx_p.specific_data_type != yaml_p.specific_data_type
                        or odx_p.coded_value != yaml_p.coded_value
                    )
                    marker = "  DIFF" if differs else ""
                else:
                    marker = "  MISSING"

                print(f"  Param [{i}]:{marker}")
                if odx_p:
                    print(
                        f"    ODX:  {odx_p.short_name:<20} byte={odx_p.byte_position} "
                        f"type={odx_p.specific_data_type} coded={odx_p.coded_value}"
                    )
                if yaml_p:
                    print(
                        f"    YAML: {yaml_p.short_name:<20} byte={yaml_p.byte_position} "
                        f"type={yaml_p.specific_data_type} coded={yaml_p.coded_value}"
                    )

    def test_matching_params_testcontainer(
        self, odx_structure: DeepMDDStructure, yaml_structure: DeepMDDStructure
    ) -> None:
        """Compare matching parameters from testcontainer MDDs."""
        print(f"\n=== MATCHING PARAMETERS (TESTCONTAINER) ===")

        def show_matching_params(structure: DeepMDDStructure, label: str) -> None:
            for v in structure.variants:
                if v.matching_params:
                    print(f"\n{label} {v.short_name}:")
                    for mp in v.matching_params:
                        print(f"  - expected_value: {mp.get('expected_value')}")
                        print(f"    diag_service: {mp.get('diag_service_name')}")
                        print(f"    out_param: {mp.get('out_param_name')}")

        show_matching_params(odx_structure, "ODX")
        print("-" * 40)
        show_matching_params(yaml_structure, "YAML")

    def test_compression_testcontainer(
        self, odx_structure: DeepMDDStructure, yaml_structure: DeepMDDStructure
    ) -> None:
        """Compare compression settings from testcontainer MDDs."""
        print(f"\n=== COMPRESSION (TESTCONTAINER) ===")
        print(f"ODX compression:  {odx_structure.chunk_compression}")
        print(f"YAML compression: {yaml_structure.chunk_compression}")
        print(f"ODX compressed size:   {odx_structure.chunk_data_size}")
        print(f"YAML compressed size:  {yaml_structure.chunk_data_size}")


class TestDeepMDDComparison:
    """Deep comparison tests between YAML-generated and ODX-generated MDDs."""

    @pytest.fixture
    def flxc1000_yaml_path(self) -> Path:
        """FLXC1000 YAML source file."""
        path = GOLDEN_DIR / "FLXC1000_yaml.yaml"
        if not path.exists():
            pytest.skip(f"YAML not found: {path}")
        return path

    @pytest.fixture
    def flxc1000_odx_mdd(self) -> Path:
        """FLXC1000 reference MDD from ODX."""
        path = GOLDEN_DIR / "FLXC1000.mdd"
        if not path.exists():
            pytest.skip(f"Reference MDD not found: {path}")
        return path

    @pytest.fixture
    def flxc1000_yaml_mdd(self, flxc1000_yaml_path: Path, tmp_path: Path) -> Path:
        """Generate MDD from YAML."""
        output = tmp_path / "flxc1000_yaml.mdd"
        convert_yaml_to_mdd(flxc1000_yaml_path, output)
        return output

    @pytest.fixture
    def odx_structure(self, flxc1000_odx_mdd: Path) -> DeepMDDStructure:
        """Parse ODX-generated MDD."""
        return parse_mdd_deep(flxc1000_odx_mdd)

    @pytest.fixture
    def yaml_structure(self, flxc1000_yaml_mdd: Path) -> DeepMDDStructure:
        """Parse YAML-generated MDD."""
        return parse_mdd_deep(flxc1000_yaml_mdd)

    def test_file_sizes(
        self, odx_structure: DeepMDDStructure, yaml_structure: DeepMDDStructure
    ) -> None:
        """Compare file sizes."""
        diff = abs(odx_structure.file_size - yaml_structure.file_size)
        print(f"\n=== FILE SIZE COMPARISON ===")
        print(f"ODX MDD:  {odx_structure.file_size} bytes")
        print(f"YAML MDD: {yaml_structure.file_size} bytes")
        print(f"Difference: {diff} bytes")

    def test_decompressed_sizes(
        self, odx_structure: DeepMDDStructure, yaml_structure: DeepMDDStructure
    ) -> None:
        """Compare decompressed FlatBuffers sizes."""
        diff = abs(odx_structure.decompressed_size - yaml_structure.decompressed_size)
        print(f"\n=== DECOMPRESSED SIZE COMPARISON ===")
        print(f"ODX:  {odx_structure.decompressed_size} bytes")
        print(f"YAML: {yaml_structure.decompressed_size} bytes")
        print(f"Difference: {diff} bytes")

    def test_ecu_metadata(
        self, odx_structure: DeepMDDStructure, yaml_structure: DeepMDDStructure
    ) -> None:
        """Compare ECU metadata."""
        print(f"\n=== ECU METADATA ===")
        print(f"ODX ECU name:  '{odx_structure.ecu_name}'")
        print(f"YAML ECU name: '{yaml_structure.ecu_name}'")
        print(f"ODX revision:  '{odx_structure.revision}'")
        print(f"YAML revision: '{yaml_structure.revision}'")

    def test_variant_count(
        self, odx_structure: DeepMDDStructure, yaml_structure: DeepMDDStructure
    ) -> None:
        """Compare variant counts."""
        print(f"\n=== VARIANT COUNT ===")
        print(f"ODX variants:  {odx_structure.variants_count}")
        print(f"YAML variants: {yaml_structure.variants_count}")
        assert odx_structure.variants_count == yaml_structure.variants_count, (
            f"Variant count mismatch: ODX={odx_structure.variants_count}, "
            f"YAML={yaml_structure.variants_count}"
        )

    def test_variant_details(
        self, odx_structure: DeepMDDStructure, yaml_structure: DeepMDDStructure
    ) -> None:
        """Compare variant details."""
        print(f"\n=== VARIANT DETAILS ===")
        print(
            f"{'Name':<30} {'Base':<6} {'Svcs':<6} {'Charts':<8} {'ComParams':<10} {'Parents':<8} {'Patterns':<10}"
        )
        print("-" * 88)

        for v in odx_structure.variants:
            print(
                f"ODX:  {v.short_name:<24} {str(v.is_base_variant):<6} "
                f"{v.services_count:<6} {v.state_charts_count:<8} "
                f"{v.com_param_refs_count:<10} {v.parent_refs_count:<8} {v.pattern_count:<10}"
            )

        print("-" * 88)

        for v in yaml_structure.variants:
            print(
                f"YAML: {v.short_name:<24} {str(v.is_base_variant):<6} "
                f"{v.services_count:<6} {v.state_charts_count:<8} "
                f"{v.com_param_refs_count:<10} {v.parent_refs_count:<8} {v.pattern_count:<10}"
            )

    def test_matching_parameters(
        self, odx_structure: DeepMDDStructure, yaml_structure: DeepMDDStructure
    ) -> None:
        """Compare matching parameters in variant patterns."""
        print(f"\n=== MATCHING PARAMETERS ===")

        for v in odx_structure.variants:
            if v.matching_params:
                print(f"\nODX {v.short_name}:")
                for mp in v.matching_params:
                    print(f"  - expected_value: {mp.get('expected_value')}")
                    print(f"    diag_service: {mp.get('diag_service_name')}")
                    print(f"    out_param: {mp.get('out_param_name')}")

        print("-" * 40)

        for v in yaml_structure.variants:
            if v.matching_params:
                print(f"\nYAML {v.short_name}:")
                for mp in v.matching_params:
                    print(f"  - expected_value: {mp.get('expected_value')}")
                    print(f"    diag_service: {mp.get('diag_service_name')}")
                    print(f"    out_param: {mp.get('out_param_name')}")

    def test_service_names(
        self, odx_structure: DeepMDDStructure, yaml_structure: DeepMDDStructure
    ) -> None:
        """Compare service names."""
        odx_services = set(odx_structure.services.keys())
        yaml_services = set(yaml_structure.services.keys())

        print(f"\n=== SERVICE NAMES ===")
        print(f"ODX services:  {len(odx_services)}")
        print(f"YAML services: {len(yaml_services)}")

        missing = odx_services - yaml_services
        extra = yaml_services - odx_services

        if missing:
            print(f"\nMissing in YAML: {sorted(missing)}")
        if extra:
            print(f"\nExtra in YAML:   {sorted(extra)}")

    def test_service_request_params(
        self, odx_structure: DeepMDDStructure, yaml_structure: DeepMDDStructure
    ) -> None:
        """Compare service request parameters in detail."""
        print(f"\n=== SERVICE REQUEST PARAMETERS ===")

        # Find common services
        common_services = set(odx_structure.services.keys()) & set(
            yaml_structure.services.keys()
        )

        for svc_name in sorted(common_services)[:5]:  # Limit to first 5 for readability
            odx_svc = odx_structure.services[svc_name]
            yaml_svc = yaml_structure.services[svc_name]

            print(f"\n{svc_name}:")
            print(f"  ODX request params:  {len(odx_svc.request_params)}")
            print(f"  YAML request params: {len(yaml_svc.request_params)}")

            # Compare params
            max_params = max(len(odx_svc.request_params), len(yaml_svc.request_params))
            for i in range(max_params):
                odx_p = (
                    odx_svc.request_params[i]
                    if i < len(odx_svc.request_params)
                    else None
                )
                yaml_p = (
                    yaml_svc.request_params[i]
                    if i < len(yaml_svc.request_params)
                    else None
                )

                print(f"\n  Param [{i}]:")
                if odx_p:
                    print(
                        f"    ODX:  {odx_p.short_name:<20} "
                        f"byte={odx_p.byte_position} bit={odx_p.bit_position} "
                        f"type={odx_p.specific_data_type} "
                        f"coded_val={odx_p.coded_value} "
                        f"base_type={odx_p.diag_coded_type_base} "
                        f"bits={odx_p.diag_coded_type_bit_length}"
                    )
                if yaml_p:
                    print(
                        f"    YAML: {yaml_p.short_name:<20} "
                        f"byte={yaml_p.byte_position} bit={yaml_p.bit_position} "
                        f"type={yaml_p.specific_data_type} "
                        f"coded_val={yaml_p.coded_value} "
                        f"base_type={yaml_p.diag_coded_type_base} "
                        f"bits={yaml_p.diag_coded_type_bit_length}"
                    )

    def test_ecu_shared_data(
        self, odx_structure: DeepMDDStructure, yaml_structure: DeepMDDStructure
    ) -> None:
        """Compare EcuSharedData presence."""
        print(f"\n=== ECU SHARED DATA ===")
        print(f"ODX has EcuSharedData:  {odx_structure.has_ecu_shared_data}")
        print(f"YAML has EcuSharedData: {yaml_structure.has_ecu_shared_data}")
        print(f"ODX DOPs count:  {odx_structure.shared_data_dops_count}")
        print(f"YAML DOPs count: {yaml_structure.shared_data_dops_count}")

    def test_compression_info(
        self, odx_structure: DeepMDDStructure, yaml_structure: DeepMDDStructure
    ) -> None:
        """Compare compression settings."""
        print(f"\n=== COMPRESSION INFO ===")
        print(f"ODX compression:  {odx_structure.chunk_compression}")
        print(f"YAML compression: {yaml_structure.chunk_compression}")
        print(f"ODX compressed size:   {odx_structure.chunk_data_size}")
        print(f"YAML compressed size:  {yaml_structure.chunk_data_size}")


class TestDetailedServiceComparison:
    """Detailed per-service comparison tests."""

    @pytest.fixture
    def flxc1000_yaml_path(self) -> Path:
        """FLXC1000 YAML source file."""
        path = GOLDEN_DIR / "FLXC1000_yaml.yaml"
        if not path.exists():
            pytest.skip(f"YAML not found: {path}")
        return path

    @pytest.fixture
    def flxc1000_odx_mdd(self) -> Path:
        """FLXC1000 reference MDD from ODX."""
        path = GOLDEN_DIR / "FLXC1000.mdd"
        if not path.exists():
            pytest.skip(f"Reference MDD not found: {path}")
        return path

    @pytest.fixture
    def flxc1000_yaml_mdd(self, flxc1000_yaml_path: Path, tmp_path: Path) -> Path:
        """Generate MDD from YAML."""
        output = tmp_path / "flxc1000_yaml.mdd"
        convert_yaml_to_mdd(flxc1000_yaml_path, output)
        return output

    @pytest.fixture
    def odx_structure(self, flxc1000_odx_mdd: Path) -> DeepMDDStructure:
        """Parse ODX-generated MDD."""
        return parse_mdd_deep(flxc1000_odx_mdd)

    @pytest.fixture
    def yaml_structure(self, flxc1000_yaml_mdd: Path) -> DeepMDDStructure:
        """Parse YAML-generated MDD."""
        return parse_mdd_deep(flxc1000_yaml_mdd)

    def test_identification_read_service(
        self, odx_structure: DeepMDDStructure, yaml_structure: DeepMDDStructure
    ) -> None:
        """Compare Identification_Read service in detail."""
        svc_name = "Identification_Read"

        print(f"\n=== {svc_name} DETAILED COMPARISON ===")

        odx_svc = odx_structure.services.get(svc_name)
        yaml_svc = yaml_structure.services.get(svc_name)

        if not odx_svc:
            pytest.skip(f"{svc_name} not found in ODX MDD")
        if not yaml_svc:
            pytest.skip(f"{svc_name} not found in YAML MDD")

        print(f"\nRequest params:")
        print(f"  ODX:  {len(odx_svc.request_params)}")
        print(f"  YAML: {len(yaml_svc.request_params)}")

        for i, (odx_p, yaml_p) in enumerate(
            zip(odx_svc.request_params, yaml_svc.request_params)
        ):
            print(f"\n  Param [{i}]:")
            print(
                f"    ODX:  name={odx_p.short_name!r} byte={odx_p.byte_position} bit={odx_p.bit_position}"
            )
            print(
                f"          type={odx_p.specific_data_type} coded={odx_p.coded_value}"
            )
            print(
                f"    YAML: name={yaml_p.short_name!r} byte={yaml_p.byte_position} bit={yaml_p.bit_position}"
            )
            print(
                f"          type={yaml_p.specific_data_type} coded={yaml_p.coded_value}"
            )

        print(f"\nPositive responses:")
        print(f"  ODX count:  {odx_svc.pos_response_count}")
        print(f"  YAML count: {yaml_svc.pos_response_count}")

        for resp_idx in range(
            min(odx_svc.pos_response_count, yaml_svc.pos_response_count)
        ):
            odx_resp = (
                odx_svc.pos_response_params[resp_idx]
                if resp_idx < len(odx_svc.pos_response_params)
                else []
            )
            yaml_resp = (
                yaml_svc.pos_response_params[resp_idx]
                if resp_idx < len(yaml_svc.pos_response_params)
                else []
            )

            print(f"\n  Response [{resp_idx}] params:")
            print(f"    ODX:  {len(odx_resp)}")
            print(f"    YAML: {len(yaml_resp)}")

            for i, odx_p in enumerate(odx_resp):
                print(
                    f"      ODX[{i}]:  {odx_p.short_name!r} type={odx_p.specific_data_type}"
                )
            for i, yaml_p in enumerate(yaml_resp):
                print(
                    f"      YAML[{i}]: {yaml_p.short_name!r} type={yaml_p.specific_data_type}"
                )


class TestParamTypeDistribution:
    """Analyze distribution of parameter types."""

    @pytest.fixture
    def flxc1000_yaml_path(self) -> Path:
        """FLXC1000 YAML source file."""
        path = GOLDEN_DIR / "FLXC1000_yaml.yaml"
        if not path.exists():
            pytest.skip(f"YAML not found: {path}")
        return path

    @pytest.fixture
    def flxc1000_odx_mdd(self) -> Path:
        """FLXC1000 reference MDD from ODX."""
        path = GOLDEN_DIR / "FLXC1000.mdd"
        if not path.exists():
            pytest.skip(f"Reference MDD not found: {path}")
        return path

    @pytest.fixture
    def flxc1000_yaml_mdd(self, flxc1000_yaml_path: Path, tmp_path: Path) -> Path:
        """Generate MDD from YAML."""
        output = tmp_path / "flxc1000_yaml.mdd"
        convert_yaml_to_mdd(flxc1000_yaml_path, output)
        return output

    @pytest.fixture
    def odx_structure(self, flxc1000_odx_mdd: Path) -> DeepMDDStructure:
        """Parse ODX-generated MDD."""
        return parse_mdd_deep(flxc1000_odx_mdd)

    @pytest.fixture
    def yaml_structure(self, flxc1000_yaml_mdd: Path) -> DeepMDDStructure:
        """Parse YAML-generated MDD."""
        return parse_mdd_deep(flxc1000_yaml_mdd)

    def test_param_type_distribution(
        self, odx_structure: DeepMDDStructure, yaml_structure: DeepMDDStructure
    ) -> None:
        """Compare distribution of parameter specific_data_types."""
        from collections import Counter

        # Param type names
        type_names = {
            0: "NONE",
            1: "CodedConst",
            2: "Dynamic",
            3: "MatchingRequestParam",
            4: "NrcConst",
            5: "PhysConst",
            6: "Reserved",
            7: "Value",
            8: "TableEntry",
            9: "TableKey",
            10: "TableStruct",
            11: "System",
            12: "LengthKeyRef",
        }

        def count_param_types(structure: DeepMDDStructure) -> Counter:
            counter: Counter = Counter()
            for svc in structure.services.values():
                for p in svc.request_params:
                    counter[p.specific_data_type] += 1
                for resp_params in svc.pos_response_params:
                    for p in resp_params:
                        counter[p.specific_data_type] += 1
            return counter

        odx_counts = count_param_types(odx_structure)
        yaml_counts = count_param_types(yaml_structure)

        print(f"\n=== PARAMETER TYPE DISTRIBUTION ===")
        print(f"{'Type':<20} {'ODX':<8} {'YAML':<8} {'Diff':<8}")
        print("-" * 44)

        all_types = set(odx_counts.keys()) | set(yaml_counts.keys())
        for t in sorted(all_types):
            odx_c = odx_counts.get(t, 0)
            yaml_c = yaml_counts.get(t, 0)
            diff = yaml_c - odx_c
            name = type_names.get(t, f"Unknown({t})")
            diff_str = f"+{diff}" if diff > 0 else str(diff)
            print(f"{name:<20} {odx_c:<8} {yaml_c:<8} {diff_str:<8}")

        print("-" * 44)
        print(
            f"{'Total':<20} {sum(odx_counts.values()):<8} {sum(yaml_counts.values()):<8}"
        )
