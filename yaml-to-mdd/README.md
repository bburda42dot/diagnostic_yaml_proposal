# yaml-to-mdd

A converter tool that transforms OpenSOVD CDA Diagnostic Description YAML/JSON files into the MDD (Marvelous Diagnostic Description) binary format used by the Classic Diagnostic Adapter.

## Overview

This tool bridges the gap between human-readable diagnostic descriptions (YAML/JSON) and the optimized binary format (MDD) consumed by diagnostic runtime systems. It enables:

- **Authoring** diagnostic descriptions in a user-friendly YAML format
- **Validating** against the OpenSOVD CDA schema
- **Converting** to the compact MDD binary format
- **Filtering** content by audience (development, production, aftermarket)
- **Iterating** quickly on schema design by identifying missing features

## Installation

### Prerequisites

- Python 3.11+
- Poetry
- FlatBuffers compiler (`flatc`) - [installation guide](https://flatbuffers.dev/flatbuffers_guide_building.html)
- Protocol Buffers compiler (`protoc`) - [installation guide](https://grpc.io/docs/protoc-installation/)

On Debian/Ubuntu:
```bash
apt install flatbuffers-compiler protobuf-compiler
```

### Setup

```bash
# Clone the repository
cd diagnostic_yaml_proposal/yaml-to-mdd

# Install with Poetry
poetry install

# Generate FlatBuffers and Protobuf files
poetry run generate-fbs
poetry run generate-proto

# Verify installation
poetry run yaml-to-mdd --help
```

## Quick Start

```bash
# Validate a YAML file
poetry run yaml-to-mdd validate input.yml

# Validate with summary
poetry run yaml-to-mdd validate input.yml --summary

# Convert a YAML file to MDD
poetry run yaml-to-mdd convert input.yml -o output.mdd

# Convert with compression (default: lzma)
poetry run yaml-to-mdd convert input.yml -o output.mdd --compression lzma

# Convert for specific audience
poetry run yaml-to-mdd convert input.yml -o aftermarket.mdd --audience aftermarket

# Show file information
poetry run yaml-to-mdd info input.yml
poetry run yaml-to-mdd info output.mdd
```

## CLI Commands

### validate

Validate a YAML/JSON diagnostic description file against the schema.

```bash
yaml-to-mdd validate <file> [options]

Options:
  -q, --quiet      Only output errors, no success messages
  -s, --summary    Show summary of document contents
  -f, --format     Output format: text, table, tree
  --verbose        Show verbose output with source context
```

### convert

Convert a YAML/JSON file to MDD binary format.

```bash
yaml-to-mdd convert <file> [options]

Options:
  -o, --output       Output file path (default: input with .mdd extension)
  -a, --audience     Target audience filter (development, production, aftermarket, oem)
  -c, --compression  Compression algorithm: lzma (default), gzip, zstd, none
  -f, --force        Overwrite output file if it exists
  --dry-run          Validate and serialize without writing file
  -V, --verbose      Show detailed conversion progress
```

### info

Display information about a diagnostic file (YAML, JSON, or MDD).

```bash
yaml-to-mdd info <file>
```

### version

```bash
yaml-to-mdd --version
```

## Supported Features

### Current (MVP)

- [x] Basic ECU definition
- [x] Sessions and timing parameters
- [x] Security levels (0x27 SecurityAccess)
- [x] DIDs (ReadDataByIdentifier 0x22, WriteDataByIdentifier 0x2E)
- [x] Basic type system (atomic types, enums, linear conversion)
- [x] DTCs with snapshots and extended data
- [x] Access patterns
- [x] Memory regions and data blocks
- [x] Audience filtering
- [x] Compression (lzma default, gzip, zstd)
- [x] Variants (base + named variants with detection patterns)
- [x] Variant detection (response_param_match for ECU variant identification)
- [x] Routines (RoutineControl 0x31 - start, stop, results)
- [x] Authentication (0x29)
- [x] CommunicationControl (0x28)
- [x] TransferData services (0x34, 0x35, 0x36, 0x37)
- [x] ResetECU (0x11)
- [x] TesterPresent (0x3E)
- [x] ClearDTC (0x14)
- [x] ReadDTCInformation (0x19)

### MDD Comparison Status

The converter produces MDD files that match reference ODX-derived MDDs:

| ECU        | Services | Variants | Status |
| ---------- | -------- | -------- | ------ |
| FLXC1000   | 28/28    | 3/3      | ✓      |
| FLXCNG1000 | 22/22    | 2/2      | ✓      |

### Known Limitations vs ODX-Derived MDD

The converter produces functionally equivalent MDD files but with some differences
compared to ODX-derived (Kotlin odx-converter) output:

| ODX Feature | Status | Notes |
| --- | --- | --- |
| `longName` on DiagComm/DiagLayer | Not emitted | ODX contains multilingual long names; YAML has no equivalent field |
| `functClasses` on DiagLayer | Not emitted | Functional classification metadata from ODX |
| `stateTransitionRefs` on State | Not emitted | ODX state charts carry explicit transition refs |
| ComParams (full ProtStack) | Not converted | YAML `comparams` section is parsed but not serialized to MDD |
| SDGs (Special Data Groups) | Not converted | YAML `sdgs` section is parsed but not serialized to MDD |
| ECU Jobs (SingleEcuJob) | Not converted | YAML `ecu_jobs` section is parsed but not serialized to MDD |
| Complex types (structs, arrays) | Not converted | Struct/array DOPs not yet mapped to MDD |
| Audience gating | Partial | Audience-based filtering works for DIDs/routines but is not serialized as `Audience` tables in MDD |

These gaps mean the generated MDD is typically **smaller** than the ODX-derived
reference (fewer metadata tables), but semantically equivalent for diagnostic
operations. The FlatBuffers object sharing (DiagCodedType, Protocol, DOP,
DiagService) matches the Kotlin reference exactly.

### Planned

- [ ] Complex types (structs, arrays)
- [ ] ComParams serialization to MDD
- [ ] SDGs serialization to MDD
- [ ] ECU Jobs serialization to MDD
- [ ] `longName` / `functClasses` support

### Nice to Have

- [ ] Reverse conversion (MDD → YAML)
- [ ] ODX export via odxtools integration
- [ ] Round-trip validation
- [ ] Auto-generate JSON Schema from Pydantic models

## Input Format

The converter accepts YAML or JSON files conforming to the `opensovd.cda.diagdesc/v1` schema.

```yaml
schema: "opensovd.cda.diagdesc/v1"

meta:
  author: "Your Name"
  domain: "Powertrain"
  created: "2026-01-22"
  revision: "1.0.0"
  description: "My ECU diagnostic description"

ecu:
  id: "MY_ECU"
  name: "My Electronic Control Unit"
  protocols:
    doip:
      protocol_short_name: "UDSonDoIP"
      is_default: true
  addressing:
    doip:
      ip: "192.168.0.50"
      port: 13400
      logical_address: 0x0E00
      tester_address: 0x0E80

sessions:
  default:
    id: 0x01
  extended:
    id: 0x03

services:
  diagnosticSessionControl:
    enabled: true
  readDataByIdentifier:
    enabled: true

access_patterns:
  public:
    sessions: any
    security: none
    authentication: none

# ... see yaml-schema/ for more examples
```

## Examples

Example diagnostic descriptions are in the `yaml-schema/` directory:

- **[`../yaml-schema/minimal-ecu.yml`](../yaml-schema/minimal-ecu.yml)** - Bare minimum required for a valid file
- **[`../yaml-schema/example-ecm.yml`](../yaml-schema/example-ecm.yml)** - Full example with variants, routines, authentication, DTCs

Integration test golden files with multi-variant ECUs:

- **[`tests/integration/golden/FLXC1000_yaml.yaml`](tests/integration/golden/FLXC1000_yaml.yaml)** - 3 variants, 28 services
- **[`tests/integration/golden/FLXCNG1000_yaml.yaml`](tests/integration/golden/FLXCNG1000_yaml.yaml)** - 2 variants, 22 services

## Output Format

The MDD format is a two-layer binary structure:

1. **Container Layer (Protobuf)**: File metadata, chunks, signatures
2. **Data Layer (FlatBuffers)**: Diagnostic descriptions (EcuData)

The format achieves ~95% size reduction compared to ODX XML.

## Development

```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=yaml_to_mdd

# Format code
poetry run ruff format .

# Lint
poetry run ruff check .

# Type check
poetry run mypy src/
```

## Programmatic Use

```python
from yaml_to_mdd.models import load_diagnostic_description, validate_diagnostic_description
from yaml_to_mdd.transform.transformer import YamlToIRTransformer
from yaml_to_mdd.converters import MDDWriter

# Validate a file (returns list of errors)
errors = validate_diagnostic_description("my-ecu.yaml")
if errors:
    for e in errors:
        print(e)

# Load and parse a YAML file
doc = load_diagnostic_description("my-ecu.yaml")
print(f"ECU: {doc.ecu.name}")
print(f"DIDs: {len(doc.dids) if doc.dids else 0}")

# Transform to IR (Intermediate Representation)
transformer = YamlToIRTransformer()
ir_db = transformer.transform(doc)

# Write MDD file (default compression: lzma)
writer = MDDWriter()
writer.write(ir_db, "my-ecu.mdd")

# Or get bytes without writing
mdd_bytes = writer.write_bytes(ir_db)
```

## Architecture

See [doc/design.md](./doc/design.md) for detailed architecture documentation.

## Related Documentation

- [yaml-schema/SCHEMA.md](../yaml-schema/SCHEMA.md) - Complete YAML schema reference
- [yaml-schema/ODX_YAML_MAPPING.md](../yaml-schema/ODX_YAML_MAPPING.md) - ODX to YAML mapping

## Related Projects

- [odx-converter](https://github.com/eclipse-opensovd/odx-converter) - ODX to MDD converter (Kotlin)
- [classic-diagnostic-adapter](https://github.com/eclipse-opensovd/classic-diagnostic-adapter) - MDD runtime consumer
- [yaml-schema/](../yaml-schema/) - YAML schema definition
- [odxtools](https://github.com/mercedes-benz/odxtools) - ODX Python library
