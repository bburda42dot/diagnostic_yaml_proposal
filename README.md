# Diagnostic YAML Proposal

A proposal for using **YAML** as a human-friendly alternative to ODX for describing ECU diagnostic capabilities.

## Why YAML Instead of ODX?

| Aspect | ODX (ISO 22901) | Diagnostic YAML |
|--------|-----------------|-----------------|
| **Format** | XML-based, verbose | YAML/JSON, concise |
| **Readability** | Complex, tool-dependent | Human-readable, git-friendly |
| **Learning curve** | Steep, requires specialized tools | Minimal, standard text editors |
| **Version control** | Difficult diffs | Clean, line-by-line diffs |
| **Tooling** | Expensive commercial tools | Open-source, standard toolchains |
| **Validation** | Custom parsers | JSON Schema (widely supported) |

## Overview

This repository provides:

1. **JSON Schema** (`schema.json`) - Formal definition of the diagnostic YAML format
2. **yaml-to-mdd** - Python tool to convert YAML to MDD (binary format for OpenSOVD CDA)
3. **Run script** (`run-cda.sh`) - End-to-end script to start Classic Diagnostic Adapter with YAML config
4. **Examples** - Sample YAML configurations for various use cases

The schema describes diagnostic capabilities of an ECU and is designed to be:

- **Strict by default**: most objects use `additionalProperties: false` to catch typos
- **Minimal**: only core information is required; many sections are optional
- **Standards-aligned**: models UDS services (ISO 14229), DoIP (ISO 13400), and CAN addressing (ISO 15765)
- **Extensible**: OEM-specific data can live under `x-oem`

## Repository Structure

```
diagnostic_yaml_proposal/
├── schema.json           # JSON Schema (v1)
├── SCHEMA.md             # Detailed schema documentation
├── ODX_YAML_MAPPING.md   # Mapping between ODX and YAML concepts
├── example-ecm.yml       # Example: Engine Control Module
├── minimal-ecu.yml       # Example: Minimal valid configuration
├── validate.py           # Schema validator script
├── run-cda.sh            # Script to run OpenSOVD CDA with YAML
├── yaml-to-mdd/          # YAML to MDD converter tool
│   ├── pyproject.toml    # Python project configuration
│   ├── src/              # Source code
│   ├── tests/            # Test suite
│   ├── examples/         # Additional examples
│   └── doc/              # Documentation
└── README.md             # This file
```

## Quick Start

### 1. Validate your YAML

```bash
# Install dependencies
pip install pyyaml jsonschema

# Validate against schema
python validate.py example-ecm.yml
```

### 2. Convert YAML to MDD

```bash
cd yaml-to-mdd

# Install the converter
pip install -e .

# Or with Poetry
poetry install

# Convert YAML to MDD
yaml-to-mdd convert ../example-ecm.yml -o output.mdd
```

### 3. Run OpenSOVD Classic Diagnostic Adapter

```bash
# Using the convenience script (from repo root)
./run-cda.sh example-ecm.yml

# Or manually with Docker
docker run -p 8080:8080 \
    -v $(pwd)/output.mdd:/data/ecu.mdd \
    ghcr.io/eclipse-opensovd/classic-diagnostic-adapter:latest
```

## Example YAML

```yaml
schema: "opensovd.cda.diagdesc/v1"

meta:
  author: "Your Team"
  domain: "Production"
  created: "2026-01-26"
  revision: "1.0.0"
  description: "Engine Control Module"

ecu:
  id: "ECM_01"
  name: "Engine Control Module"
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
```

See [example-ecm.yml](example-ecm.yml) for a complete example with DIDs, DTCs, routines, and security.

## Schema Documentation

- [SCHEMA.md](SCHEMA.md) - Detailed schema reference
- [ODX_YAML_MAPPING.md](ODX_YAML_MAPPING.md) - Mapping between ODX and YAML concepts

### Schema Version

Current version: `opensovd.cda.diagdesc/v1`

Every document must include:

```yaml
schema: opensovd.cda.diagdesc/v1
```

## yaml-to-mdd Converter

The `yaml-to-mdd` tool converts Diagnostic YAML to MDD binary format used by OpenSOVD Classic Diagnostic Adapter.

### Installation

```bash
cd yaml-to-mdd
pip install -e .
# Or with Poetry
poetry install
```

### Usage

```bash
# Convert YAML to MDD
yaml-to-mdd convert input.yaml -o output.mdd

# Validate only (no output)
yaml-to-mdd convert input.yaml --validate-only

# Verbose output
yaml-to-mdd convert input.yaml -o output.mdd -v
```

For more details, see [yaml-to-mdd/README.md](yaml-to-mdd/README.md).

## Related Projects

- [OpenSOVD Classic Diagnostic Adapter](https://github.com/eclipse-opensovd/classic-diagnostic-adapter) - SOVD gateway for classic UDS diagnostics
- [odxtools](https://github.com/mercedes-benz/odxtools) - Python library for ODX files

## Contributing

Contributions are welcome! Please open an issue or pull request.

## License

See [LICENSE](LICENSE).
