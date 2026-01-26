"""Convert YAML type definitions to IR DOPs."""

from __future__ import annotations

from yaml_to_mdd.ir.types import (
    IRDOP,
    IRCompuCategory,
    IRCompuMethod,
    IRCompuScale,
    IRDataType,
    IRDiagCodedType,
    IRDiagCodedTypeName,
)
from yaml_to_mdd.models.types import BaseType, Endianness, TypeDefinition

# Mapping from YAML base types to IR data types and default bit lengths
BASE_TYPE_TO_IR: dict[BaseType, tuple[IRDataType, int]] = {
    BaseType.U8: (IRDataType.A_UINT_32, 8),
    BaseType.U16: (IRDataType.A_UINT_32, 16),
    BaseType.U32: (IRDataType.A_UINT_32, 32),
    BaseType.U64: (IRDataType.A_UINT_32, 64),
    BaseType.I8: (IRDataType.A_INT_32, 8),
    BaseType.I16: (IRDataType.A_INT_32, 16),
    BaseType.I32: (IRDataType.A_INT_32, 32),
    BaseType.I64: (IRDataType.A_INT_32, 64),
    BaseType.F32: (IRDataType.A_FLOAT_32, 32),
    BaseType.F64: (IRDataType.A_FLOAT_64, 64),
    BaseType.ASCII: (IRDataType.A_ASCIISTRING, 0),
    BaseType.UTF8: (IRDataType.A_UTF_8_STRING, 0),
    BaseType.BYTES: (IRDataType.A_BYTEFIELD, 0),
    BaseType.BOOL: (IRDataType.A_UINT_32, 8),
}


def create_compu_method_for_type(type_def: TypeDefinition) -> IRCompuMethod | None:
    """Create computation method from type definition.

    Args:
    ----
        type_def: The YAML type definition.

    Returns:
    -------
        IRCompuMethod or None if no conversion needed.

    """
    # Check for enum mapping
    if type_def.enum is not None:
        scales = []
        for internal, text in type_def.enum.items():
            # Handle both int and str keys
            if isinstance(internal, str):
                internal_val = int(internal, 16) if internal.startswith("0x") else int(internal)
            else:
                internal_val = internal

            scales.append(
                IRCompuScale(
                    internal_value=internal_val,
                    text_value=str(text),
                )
            )

        return IRCompuMethod(
            category=IRCompuCategory.TEXT_TABLE,
            scales=tuple(scales),
        )

    # Check for linear scaling
    if type_def.scale is not None or type_def.offset is not None:
        scale = IRCompuScale(
            factor=type_def.scale or 1.0,
            offset=type_def.offset or 0.0,
        )
        return IRCompuMethod(
            category=IRCompuCategory.LINEAR,
            scales=(scale,),
            unit=type_def.unit,
        )

    # No conversion needed
    return None


def create_diag_coded_type(type_def: TypeDefinition) -> IRDiagCodedType:
    """Create diagnostic coded type from type definition.

    Args:
    ----
        type_def: The YAML type definition.

    Returns:
    -------
        IRDiagCodedType for wire encoding.

    """
    base_ir_type, default_bit_length = BASE_TYPE_TO_IR.get(
        type_def.base,
        (IRDataType.A_BYTEFIELD, 0),
    )

    # Calculate bit length
    if type_def.base in (BaseType.ASCII, BaseType.UTF8, BaseType.BYTES):
        # String/bytes: use length field (in bytes, convert to bits)
        bit_length = (type_def.length or 1) * 8
    elif type_def.bit_length is not None:
        # Explicit bit_length override
        bit_length = type_def.bit_length
    else:
        bit_length = default_bit_length

    # Determine byte order
    is_big_endian = True
    if type_def.endian == Endianness.LITTLE:
        is_big_endian = False

    return IRDiagCodedType(
        type_name=IRDiagCodedTypeName.STANDARD_LENGTH_TYPE,
        base_data_type=base_ir_type,
        bit_length=bit_length,
        is_high_low_byte_order=is_big_endian,
    )


def determine_physical_type(
    type_def: TypeDefinition,
    compu_method: IRCompuMethod | None,
) -> IRDataType:
    """Determine the physical data type after conversion.

    Args:
    ----
        type_def: The YAML type definition.
        compu_method: The computation method (if any).

    Returns:
    -------
        IRDataType for the physical value.

    """
    # Enum produces string
    if compu_method and compu_method.category == IRCompuCategory.TEXT_TABLE:
        return IRDataType.A_ASCIISTRING

    # Float types
    if type_def.base == BaseType.F32:
        return IRDataType.A_FLOAT_32
    if type_def.base == BaseType.F64:
        return IRDataType.A_FLOAT_64

    # String types
    if type_def.base in (BaseType.ASCII, BaseType.UTF8):
        return IRDataType.A_ASCIISTRING

    # Bytes
    if type_def.base == BaseType.BYTES:
        return IRDataType.A_BYTEFIELD

    # Signed integers
    if type_def.base in (BaseType.I8, BaseType.I16, BaseType.I32, BaseType.I64):
        return IRDataType.A_INT_32

    # Unsigned integers (including bool)
    return IRDataType.A_UINT_32


def type_definition_to_dop(
    name: str,
    type_def: TypeDefinition,
) -> IRDOP:
    """Convert a TypeDefinition to an IR DOP.

    Args:
    ----
        name: Short name for the DOP.
        type_def: The YAML type definition.

    Returns:
    -------
        IRDOP instance.

    """
    diag_coded_type = create_diag_coded_type(type_def)
    compu_method = create_compu_method_for_type(type_def)
    physical_type = determine_physical_type(type_def, compu_method)

    return IRDOP(
        short_name=name,
        diag_coded_type=diag_coded_type,
        compu_method=compu_method,
        physical_type=physical_type,
        unit=type_def.unit,
    )
