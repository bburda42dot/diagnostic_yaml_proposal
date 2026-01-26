# FlatBuffers Schema

This directory contains the FlatBuffers schema file for the MDD (Machine-readable
Diagnostic Description) format.

## Files

- `diagnostic_description.fbs` - Main schema file defining all data structures
- `diagnostic_description.fbs.original` - Original schema from odx-converter

## Schema Modifications

The schema has been slightly modified from the original `odx-converter` version
to support Python code generation. Specifically:

- Replaced `union SimpleOrComplexValueEntry` with a `ValueEntry` wrapper table
- This is because Python FlatBuffers does not support vectors of unions

## Regenerating Python Bindings

To regenerate Python bindings after schema changes:

```bash
./scripts/generate_flatbuffers.sh
```

Generated code will be placed in `../fbs_generated/`.

## Requirements

- `flatc` compiler version 24.x or later
- Install on Ubuntu: Download from GitHub releases
- Install on macOS: `brew install flatbuffers`

## Schema Overview

The schema defines the following main structures:

### DiagService
Represents a diagnostic service (e.g., ReadDataByIdentifier, WriteDataByIdentifier).

### DOP (Data Object Property)
Defines how data is encoded/decoded, including:
- Physical type (int, float, string, etc.)
- Computational method (linear, table, identical)
- Byte order

### Param
Request/response parameters with position and length information.

### DiagCodedType
Low-level data type encoding including:
- Standard length type (fixed bit length)
- Min-max length type (variable length with termination)
- Leading length info type (length prefix)

## Key Enums

- `DataType` - Base data types (A_INT_32, A_UINT_32, A_ASCIISTRING, etc.)
- `DiagCodedTypeName` - Encoding types (STANDARD_LENGTH_TYPE, etc.)
- `CompuCategory` - Computation categories (IDENTICAL, LINEAR, SCALE_LINEAR, etc.)

## Copyright

Copyright (c) 2025 The Contributors to Eclipse OpenSOVD
Licensed under Apache License 2.0
