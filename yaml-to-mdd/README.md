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
cd opensovd-server/yaml-to-mdd

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

# Convert with compression
poetry run yaml-to-mdd convert input.yml -o output.mdd --compression gzip

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
  -c, --compression  Compression algorithm: gzip, zstd
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

- [x] Basic ECU definition (single ECU, no variants)
- [x] Sessions and timing parameters
- [x] Security levels (0x27)
- [x] DIDs (ReadDataByIdentifier 0x22, WriteDataByIdentifier 0x2E)
- [x] Basic type system (atomic types, enums, linear conversion)
- [x] DTCs with snapshots and extended data
- [x] Access patterns
- [x] Memory regions and data blocks
- [x] Audience filtering
- [x] Compression (gzip, zstd)

### Planned

- [ ] Routines (RoutineControl 0x31) - partial support
- [ ] Variant support and detection
- [ ] Authentication (0x29)
- [ ] Complex types (structs, arrays)
- [ ] ComParams
- [ ] SDGs (Special Data Groups)
- [ ] ECU Jobs

### Nice to Have

- [ ] Reverse conversion (MDD → YAML)
- [ ] ODX export via odxtools integration
- [ ] Round-trip validation

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

# ... see examples/ directory for more
```

## Examples

The `examples/` directory contains sample diagnostic descriptions:

- **`examples/minimal/`** - Bare minimum required for a valid file
- **`examples/basic/`** - Common features: sessions, DIDs, types, DTCs

For a full-featured example with all schema capabilities, see:
- **`../diagnostic_yaml/example-ecm.yml`** - Variants, routines, memory, authentication

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

# Write MDD file
writer = MDDWriter(compression="gzip")
writer.write(ir_db, "my-ecu.mdd")

# Or get bytes without writing
mdd_bytes = writer.write_bytes(ir_db)
```

## Architecture

See [doc/design.md](./doc/design.md) for detailed architecture documentation.

## Related Documentation

- [diagnostic_yaml/SCHEMA.md](../diagnostic_yaml/SCHEMA.md) - Complete YAML schema reference
- [diagnostic_yaml/ODX_YAML_MAPPING.md](../diagnostic_yaml/ODX_YAML_MAPPING.md) - ODX to YAML mapping

## Related Projects

- [odx-converter](https://github.com/eclipse-opensovd/odx-converter) - ODX to MDD converter (Kotlin)
- [classic-diagnostic-adapter](https://github.com/eclipse-opensovd/classic-diagnostic-adapter) - MDD runtime consumer
- [diagnostic_yaml](../diagnostic_yaml/) - YAML schema definition
- [odxtools](https://github.com/mercedes-benz/odxtools) - ODX Python library
