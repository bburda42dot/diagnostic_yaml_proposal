"""MDD file reader for parsing and comparing MDD files.

This module provides functionality to read MDD files (Protobuf container
with FlatBuffers payload) and extract structured data for comparison.
"""

from __future__ import annotations

import gzip
import lzma
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from yaml_to_mdd.converters.mdd_writer import FILE_MAGIC
from yaml_to_mdd.fbs_generated.dataformat.EcuData import EcuData
from yaml_to_mdd.proto_generated import MDDFile


@dataclass
class ComParamInfo:
    """Communication parameter information."""

    short_name: str
    value: str | None = None
    sub_params: dict[str, str] = field(default_factory=dict)


@dataclass
class ProtocolInfo:
    """Protocol layer information."""

    short_name: str
    com_params: list[ComParamInfo] = field(default_factory=list)


@dataclass
class MDDStructure:
    """Normalized structure of an MDD file for comparison.

    This class represents the key properties of an MDD file in a format
    that can be easily compared between generated and reference MDDs.
    """

    # ECU-level metadata
    ecu_name: str
    revision: str
    metadata: dict[str, str] = field(default_factory=dict)

    # Variants (name -> pattern mapping)
    variants: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Sessions (name -> id mapping)
    sessions: dict[str, int] = field(default_factory=dict)

    # Security levels (set of level numbers)
    security_levels: set[int] = field(default_factory=set)

    # Services (set of short names)
    services: set[str] = field(default_factory=set)

    # State charts (name -> states set)
    state_charts: dict[str, set[str]] = field(default_factory=dict)

    # Protocol layers
    protocols: list[ProtocolInfo] = field(default_factory=list)

    # Communication parameters (extracted across all layers)
    com_params: dict[str, ComParamInfo] = field(default_factory=dict)

    # DoIP-specific addresses (for convenience)
    doip_logical_ecu_address: int | None = None
    doip_logical_gateway_address: int | None = None
    doip_logical_functional_address: int | None = None
    doip_tester_address: int | None = None


class MDDReader:
    """Read and parse MDD files.

    Usage:
        reader = MDDReader()
        structure = reader.read_structure(Path("file.mdd"))
    """

    def read_structure(self, mdd_path: Path) -> MDDStructure:
        """Read MDD file and return normalized structure.

        Args:
        ----
            mdd_path: Path to MDD file.

        Returns:
        -------
            MDDStructure with parsed data.

        Raises:
        ------
            FileNotFoundError: If file doesn't exist.
            ValueError: If file format is invalid.

        """
        with open(mdd_path, "rb") as f:
            raw_data = f.read()

        return self.read_structure_from_bytes(raw_data)

    def read_structure_from_bytes(self, raw_data: bytes) -> MDDStructure:
        """Parse MDD from bytes and return normalized structure.

        Args:
        ----
            raw_data: Raw MDD file bytes.

        Returns:
        -------
            MDDStructure with parsed data.

        """
        # Check magic header
        if not raw_data.startswith(FILE_MAGIC):
            raise ValueError(
                f"Invalid MDD file: missing magic header. "
                f"Expected {FILE_MAGIC!r}, got {raw_data[:20]!r}"
            )

        # Parse protobuf container
        mdd = MDDFile()
        mdd.ParseFromString(raw_data[len(FILE_MAGIC) :])

        # Extract metadata
        structure = MDDStructure(
            ecu_name=mdd.ecu_name,
            revision=mdd.revision,
            metadata=dict(mdd.metadata),
        )

        # Find diagnostic description chunk and decompress
        # The chunk name may be "diagnostic_description" (yaml-to-mdd) or ECU name (odxtools)
        for chunk in mdd.chunks:
            # Accept any chunk of type DIAGNOSTIC_DESCRIPTION (type=0)
            # or named "diagnostic_description"
            is_diag_chunk = (
                chunk.type == 0  # DIAGNOSTIC_DESCRIPTION enum value
                or chunk.name == "diagnostic_description"
            )
            if is_diag_chunk:
                fbs_data = self._decompress_chunk(chunk)
                self._parse_flatbuffers(fbs_data, structure)
                break

        return structure

    def _decompress_chunk(self, chunk: Any) -> bytes:
        """Decompress chunk data if compressed.

        Args:
        ----
            chunk: Protobuf chunk message.

        Returns:
        -------
            Decompressed FlatBuffers data.

        """
        data = chunk.data
        compression = chunk.compression_algorithm

        if not compression or compression == "none":
            return data
        elif compression == "lzma":
            return lzma.decompress(data)
        elif compression == "gzip":
            return gzip.decompress(data)
        elif compression == "zstd":
            try:
                import zstandard as zstd

                decompressor = zstd.ZstdDecompressor()
                return decompressor.decompress(data)
            except ImportError:
                raise RuntimeError(
                    "zstandard package required for zstd decompression"
                ) from None
        else:
            raise ValueError(f"Unknown compression algorithm: {compression}")

    def _parse_flatbuffers(self, fbs_data: bytes, structure: MDDStructure) -> None:
        """Parse FlatBuffers EcuData and populate structure.

        Args:
        ----
            fbs_data: Decompressed FlatBuffers data.
            structure: Structure to populate.

        """
        # type: ignore[no-untyped-call]
        ecu_data = EcuData.GetRootAs(fbs_data, 0)

        # Parse variants
        for i in range(ecu_data.VariantsLength()):
            variant = ecu_data.Variants(i)
            if variant is None:
                continue

            diag_layer = variant.DiagLayer()
            if diag_layer is None:
                continue

            variant_name = (
                diag_layer.ShortName().decode("utf-8")
                if diag_layer.ShortName()
                else f"variant_{i}"
            )

            # Extract variant pattern info
            variant_info: dict[str, Any] = {
                "is_base_variant": variant.IsBaseVariant(),
                "patterns": [],
            }

            for j in range(variant.VariantPatternLength()):
                pattern = variant.VariantPattern(j)
                if pattern is not None:
                    # Extract matching parameters
                    # Handle both schema versions (singular/plural naming)
                    if hasattr(pattern, "MatchingParametersLength"):
                        mp_length = pattern.MatchingParametersLength()
                        get_mp = pattern.MatchingParameters
                    elif hasattr(pattern, "MatchingParameterLength"):
                        mp_length = pattern.MatchingParameterLength()
                        get_mp = pattern.MatchingParameter
                    else:
                        mp_length = 0
                        get_mp = None

                    for k in range(mp_length):
                        mp = get_mp(k) if get_mp else None
                        if mp is not None:
                            variant_info["patterns"].append(
                                {
                                    "expected_value": (
                                        mp.ExpectedValue().decode("utf-8")
                                        if mp.ExpectedValue()
                                        else None
                                    ),
                                }
                            )

            structure.variants[variant_name] = variant_info

            # Extract services from this variant's diag layer
            self._extract_services(diag_layer, structure)

            # Extract state charts
            self._extract_state_charts(diag_layer, structure)

            # Extract com params from diag layer
            self._extract_com_params(diag_layer, structure)

            # Extract parent refs (may contain protocol references)
            self._extract_parent_refs(variant, structure)

    def _extract_services(self, diag_layer: Any, structure: MDDStructure) -> None:
        """Extract services from DiagLayer.

        Args:
        ----
            diag_layer: DiagLayer FlatBuffer object.
            structure: Structure to populate.

        """
        for i in range(diag_layer.DiagServicesLength()):
            service = diag_layer.DiagServices(i)
            if service is None:
                continue

            # Service name is in DiagComm, not directly on DiagService
            diag_comm = service.DiagComm()
            if diag_comm is not None:
                short_name = diag_comm.ShortName()
                if short_name:
                    structure.services.add(short_name.decode("utf-8"))

    def _extract_state_charts(self, diag_layer: Any, structure: MDDStructure) -> None:
        """Extract state charts from DiagLayer.

        Args:
        ----
            diag_layer: DiagLayer FlatBuffer object.
            structure: Structure to populate.

        """
        for i in range(diag_layer.StateChartsLength()):
            state_chart = diag_layer.StateCharts(i)
            if state_chart is None:
                continue

            chart_name = (
                state_chart.ShortName().decode("utf-8")
                if state_chart.ShortName()
                else f"chart_{i}"
            )

            states: set[str] = set()
            for j in range(state_chart.StatesLength()):
                state = state_chart.States(j)
                if state is not None and state.ShortName():
                    states.add(state.ShortName().decode("utf-8"))

            structure.state_charts[chart_name] = states

            # Extract security levels from SecurityAccess state chart
            if chart_name == "SecurityAccess":
                for state_name in states:
                    if state_name.startswith("Level_"):
                        try:
                            level = int(state_name.split("_")[1])
                            structure.security_levels.add(level)
                        except (IndexError, ValueError):
                            pass

            # Extract sessions from Session state chart
            if chart_name == "Session":
                for state_name in states:
                    # Map state name to session ID (convention-based)
                    session_ids = {
                        "Default": 0x01,
                        "Programming": 0x02,
                        "Extended": 0x03,
                        "Custom": 0x44,
                    }
                    if state_name in session_ids:
                        sid = session_ids[state_name]
                        structure.sessions[state_name] = sid

    def _extract_com_params(self, diag_layer: Any, structure: MDDStructure) -> None:
        """Extract communication parameters from DiagLayer.

        Args:
        ----
            diag_layer: DiagLayer FlatBuffer object.
            structure: Structure to populate.

        """
        if not hasattr(diag_layer, "ComParamRefsLength"):
            return

        for i in range(diag_layer.ComParamRefsLength()):
            cp_ref = diag_layer.ComParamRefs(i)
            if cp_ref is None:
                continue

            self._process_com_param_ref(cp_ref, structure)

    def _extract_parent_refs(self, variant: Any, structure: MDDStructure) -> None:
        """Extract parent references (including Protocol refs) from variant.

        Args:
        ----
            variant: Variant FlatBuffer object.
            structure: Structure to populate.

        """
        if not hasattr(variant, "ParentRefsLength"):
            return

        for i in range(variant.ParentRefsLength()):
            parent_ref = variant.ParentRefs(i)
            if parent_ref is None:
                continue

            # Check if this is a Protocol reference
            # ParentRefType enum: Variant=0, Protocol=1, FunctionalGroup=2, etc.
            if hasattr(parent_ref, "RefAsProtocol"):
                protocol = parent_ref.RefAsProtocol()
                if protocol is not None:
                    self._extract_protocol(protocol, structure)

    def _extract_protocol(self, protocol: Any, structure: MDDStructure) -> None:
        """Extract protocol information.

        Args:
        ----
            protocol: Protocol FlatBuffer object.
            structure: Structure to populate.

        """
        diag_layer = protocol.DiagLayer() if hasattr(protocol, "DiagLayer") else None
        short_name = ""
        if diag_layer is not None and diag_layer.ShortName():
            short_name = diag_layer.ShortName().decode("utf-8")

        protocol_info = ProtocolInfo(short_name=short_name)

        # Extract com_param_refs from protocol's diag layer
        if diag_layer is not None:
            self._extract_com_params(diag_layer, structure)

        # Extract com_param_spec if present
        if hasattr(protocol, "ComParamSpec"):
            com_param_spec = protocol.ComParamSpec()
            if com_param_spec is not None:
                self._extract_com_param_spec(com_param_spec, structure)

        structure.protocols.append(protocol_info)

    def _extract_com_param_spec(
        self, com_param_spec: Any, structure: MDDStructure
    ) -> None:
        """Extract ComParamSpec information.

        Args:
        ----
            com_param_spec: ComParamSpec FlatBuffer object.
            structure: Structure to populate.

        """
        if not hasattr(com_param_spec, "ProtStacksLength"):
            return

        for i in range(com_param_spec.ProtStacksLength()):
            prot_stack = com_param_spec.ProtStacks(i)
            if prot_stack is None:
                continue

            # Extract comparam_subset_refs
            if hasattr(prot_stack, "ComparamSubsetRefsLength"):
                for j in range(prot_stack.ComparamSubsetRefsLength()):
                    subset = prot_stack.ComparamSubsetRefs(j)
                    if subset is not None:
                        self._extract_com_param_subset(subset, structure)

    def _extract_com_param_subset(self, subset: Any, structure: MDDStructure) -> None:
        """Extract ComParamSubSet information.

        Args:
        ----
            subset: ComParamSubSet FlatBuffer object.
            structure: Structure to populate.

        """
        # Extract regular com params
        if hasattr(subset, "ComParamsLength"):
            for i in range(subset.ComParamsLength()):
                com_param = subset.ComParams(i)
                if com_param is not None:
                    self._process_com_param(com_param, structure)

        # Extract complex com params
        if hasattr(subset, "ComplexComParamsLength"):
            for i in range(subset.ComplexComParamsLength()):
                com_param = subset.ComplexComParams(i)
                if com_param is not None:
                    self._process_com_param(com_param, structure)

    def _process_com_param_ref(self, cp_ref: Any, structure: MDDStructure) -> None:
        """Process a ComParamRef and extract values.

        Args:
        ----
            cp_ref: ComParamRef FlatBuffer object.
            structure: Structure to populate.

        """
        com_param = cp_ref.ComParam() if hasattr(cp_ref, "ComParam") else None
        if com_param is None:
            return

        short_name = ""
        if com_param.ShortName():
            short_name = com_param.ShortName().decode("utf-8")

        # Extract protocol reference if present
        if hasattr(cp_ref, "Protocol"):
            protocol = cp_ref.Protocol()
            if protocol is not None:
                # Check if we already have this protocol
                protocol_name = ""
                proto_diag_layer = (
                    protocol.DiagLayer() if hasattr(protocol, "DiagLayer") else None
                )
                if proto_diag_layer and proto_diag_layer.ShortName():
                    protocol_name = proto_diag_layer.ShortName().decode("utf-8")

                if protocol_name and not any(
                    p.short_name == protocol_name for p in structure.protocols
                ):
                    self._extract_protocol(protocol, structure)

        # Get the value from SimpleValue or ComplexValue
        value = None
        sub_params: dict[str, str] = {}

        if hasattr(cp_ref, "SimpleValue"):
            simple_val = cp_ref.SimpleValue()
            if simple_val is not None and simple_val.Value():
                value = simple_val.Value().decode("utf-8")

        if hasattr(cp_ref, "ComplexValue"):
            complex_val = cp_ref.ComplexValue()
            if complex_val is not None:
                # Extract entries from complex value
                sub_params = self._extract_complex_value(complex_val, com_param)

        param_info = ComParamInfo(
            short_name=short_name,
            value=value,
            sub_params=sub_params,
        )
        structure.com_params[short_name] = param_info

        # Check for DoIP-specific addresses
        self._check_doip_addresses(short_name, value, sub_params, structure)

    def _process_com_param(self, com_param: Any, structure: MDDStructure) -> None:
        """Process a ComParam definition.

        Args:
        ----
            com_param: ComParam FlatBuffer object.
            structure: Structure to populate.

        """
        short_name = ""
        if com_param.ShortName():
            short_name = com_param.ShortName().decode("utf-8")

        # Get default value if this is a regular com param
        value = None
        if hasattr(com_param, "SpecificDataAsRegularComParam"):
            regular = com_param.SpecificDataAsRegularComParam()
            if regular is not None and hasattr(regular, "PhysicalDefaultValue"):
                pdv = regular.PhysicalDefaultValue()
                if pdv:
                    value = pdv.decode("utf-8")

        param_info = ComParamInfo(short_name=short_name, value=value)
        structure.com_params[short_name] = param_info

    def _extract_complex_value(
        self, complex_val: Any, com_param: Any
    ) -> dict[str, str]:
        """Extract values from a ComplexValue.

        Handles two formats:
        1. ValueEntry wrapper tables (old yaml-to-mdd schema)
        2. Union vectors (CDA schema, current yaml-to-mdd output)

        The union vector format stores:
        - entries_type at vtable slot 0 (offset 4): vector of u8 tags
        - entries at vtable slot 1 (offset 6): vector of table offsets

        Args:
        ----
            complex_val: ComplexValue FlatBuffer object.
            com_param: Associated ComParam for sub-param names.

        Returns:
        -------
            Dict mapping sub-param names to values.

        """
        result: dict[str, str] = {}

        # Get sub-param names from complex com param definition
        sub_param_names: list[str] = self._get_sub_param_names(com_param)

        # Try union vector format first (CDA compatible)
        union_result = self._try_read_union_vector(complex_val, sub_param_names)
        if union_result:
            return union_result

        # Fall back to ValueEntry wrapper format
        return self._try_read_value_entry_format(complex_val, sub_param_names)

    def _get_sub_param_names(self, com_param: Any) -> list[str]:
        """Get sub-parameter names from a ComplexComParam definition.

        Args:
        ----
            com_param: ComParam FlatBuffer object.

        Returns:
        -------
            List of sub-parameter short names.

        """
        sub_param_names: list[str] = []

        # First try direct method (CDA style)
        if hasattr(com_param, "SpecificDataAsComplexComParam"):
            complex_cp = com_param.SpecificDataAsComplexComParam()
            if complex_cp is not None and hasattr(complex_cp, "ComParamsLength"):
                for i in range(complex_cp.ComParamsLength()):
                    sub_cp = complex_cp.ComParams(i)
                    if sub_cp is not None and sub_cp.ShortName():
                        sub_param_names.append(sub_cp.ShortName().decode("utf-8"))

        # If that didn't work, try using union type manually (yaml-to-mdd style)
        if not sub_param_names and hasattr(com_param, "SpecificDataType"):
            from yaml_to_mdd.fbs_generated.dataformat.ComParamSpecificData import (
                ComParamSpecificData,
            )
            from yaml_to_mdd.fbs_generated.dataformat.ComplexComParam import (
                ComplexComParam,
            )

            spec_type = com_param.SpecificDataType()
            if spec_type == ComParamSpecificData.ComplexComParam:
                spec_data = com_param.SpecificData()
                if spec_data is not None:
                    # Manually initialize ComplexComParam from the table
                    complex_cp = ComplexComParam()
                    complex_cp.Init(spec_data.Bytes, spec_data.Pos)
                    if complex_cp is not None:
                        for i in range(complex_cp.ComParamsLength()):
                            sub_cp = complex_cp.ComParams(i)
                            if sub_cp is not None and sub_cp.ShortName():
                                sub_param_names.append(
                                    sub_cp.ShortName().decode("utf-8")
                                )

        return sub_param_names

    def _try_read_union_vector(
        self, complex_val: Any, sub_param_names: list[str]
    ) -> dict[str, str]:
        """Try to read ComplexValue entries as union vector format.

        Union vectors have two fields:
        - entries_type (vtable slot 0, offset 4): vector of u8 tags
        - entries (vtable slot 1, offset 6): vector of offsets

        This is the CDA-compatible format.

        Args:
        ----
            complex_val: ComplexValue FlatBuffer object.
            sub_param_names: List of sub-parameter names.

        Returns:
        -------
            Dict mapping sub-param names to values, or empty dict if not union format.

        """
        import flatbuffers

        from yaml_to_mdd.fbs_generated.dataformat.SimpleValue import SimpleValue

        result: dict[str, str] = {}

        try:
            tab = complex_val._tab

            # Check for entries_type at vtable slot 0 (offset 4)
            # This is the distinguishing feature of union vectors
            entries_type_voffset = 4  # First field after vtable header
            entries_type_offset = tab.Offset(entries_type_voffset)
            if entries_type_offset == 0:
                return {}  # No entries_type field, not union vector format

            # Check for entries at vtable slot 1 (offset 6)
            entries_voffset = 6  # Second field
            entries_offset = tab.Offset(entries_voffset)
            if entries_offset == 0:
                return {}  # No entries field

            # Read entries_type vector length
            entries_type_vec_offset = tab.Vector(entries_type_offset)
            entries_type_len = tab.VectorLen(entries_type_offset)

            # Read entries vector length
            entries_len = tab.VectorLen(entries_offset)
            entries_vec_offset = tab.Vector(entries_offset)

            # Lengths must match for valid union vector
            if entries_type_len != entries_len:
                return {}

            # Read each entry based on its type tag
            for i in range(entries_len):
                # Read type tag (u8)
                type_tag = tab.Bytes[entries_type_vec_offset + i]

                # Read entry offset
                entry_pos = entries_vec_offset + i * 4  # 4 bytes per offset
                entry_offset = flatbuffers.encode.Get(
                    flatbuffers.packer.uoffset, tab.Bytes, entry_pos
                )
                entry_table_pos = entry_pos + entry_offset

                # SimpleValue type tag is 1
                if type_tag == 1:
                    simple = SimpleValue()
                    simple.Init(tab.Bytes, entry_table_pos)
                    if simple.Value():
                        key = (
                            sub_param_names[i] if i < len(sub_param_names) else f"_{i}"
                        )
                        result[key] = simple.Value().decode("utf-8")
                # ComplexValue type tag is 2 - could add recursive handling if needed

        except (struct.error, IndexError, Exception):
            return {}  # Not union vector format or read error

        return result

    def _try_read_value_entry_format(
        self, complex_val: Any, sub_param_names: list[str]
    ) -> dict[str, str]:
        """Try to read ComplexValue entries as ValueEntry wrapper format.

        This is the old yaml-to-mdd schema format where entries are wrapped
        in ValueEntry tables.

        Args:
        ----
            complex_val: ComplexValue FlatBuffer object.
            sub_param_names: List of sub-parameter names.

        Returns:
        -------
            Dict mapping sub-param names to values.

        """
        result: dict[str, str] = {}

        if not hasattr(complex_val, "EntriesLength"):
            return result

        for i in range(complex_val.EntriesLength()):
            try:
                entry = complex_val.Entries(i)
                if entry is None:
                    continue

                # ValueEntry wrapper table has a SimpleValue() method
                if hasattr(entry, "SimpleValue"):
                    try:
                        simple = entry.SimpleValue()
                        if simple is not None and simple.Value():
                            key = (
                                sub_param_names[i]
                                if i < len(sub_param_names)
                                else f"_{i}"
                            )
                            result[key] = simple.Value().decode("utf-8")
                            continue
                    except (struct.error, Exception):
                        pass

            except (struct.error, Exception):
                continue

        return result

    def _check_doip_addresses(
        self,
        param_name: str,
        value: str | None,
        sub_params: dict[str, str],
        structure: MDDStructure,
    ) -> None:
        """Check for DoIP-specific addresses and store them.

        Args:
        ----
            param_name: ComParam short name.
            value: Simple value if any.
            sub_params: Sub-parameters if complex.
            structure: Structure to populate.

        """
        try:
            # CP_DoIPLogicalGatewayAddress
            if param_name == "CP_DoIPLogicalGatewayAddress" and value:
                structure.doip_logical_gateway_address = int(value)

            # CP_DoIPLogicalFunctionalAddress
            if param_name == "CP_DoIPLogicalFunctionalAddress" and value:
                structure.doip_logical_functional_address = int(value)

            # CP_DoIPLogicalTesterAddress
            if param_name == "CP_DoIPLogicalTesterAddress" and value:
                structure.doip_tester_address = int(value)

            # CP_UniqueRespIdTable (complex) contains CP_DoIPLogicalEcuAddress
            if param_name == "CP_UniqueRespIdTable":
                if "CP_DoIPLogicalEcuAddress" in sub_params:
                    structure.doip_logical_ecu_address = int(
                        sub_params["CP_DoIPLogicalEcuAddress"]
                    )
        except (ValueError, TypeError):
            pass  # Ignore conversion errors


def read_mdd_structure(mdd_path: Path) -> MDDStructure:
    """Convenience function to read MDD structure.

    Args:
    ----
        mdd_path: Path to MDD file.

    Returns:
    -------
        MDDStructure with parsed data.

    """
    reader = MDDReader()
    return reader.read_structure(mdd_path)
