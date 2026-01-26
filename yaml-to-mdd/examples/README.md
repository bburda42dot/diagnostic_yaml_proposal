# Example Diagnostic Descriptions

This directory contains example YAML files demonstrating the OpenSOVD CDA diagnostic description schema.

## Directory Structure

```
examples/
├── README.md           # This file
├── minimal/            # Bare minimum required configuration
│   ├── minimal-ecu.yaml
│   └── README.md
└── basic/              # Common features for typical ECUs
    ├── basic-ecu.yaml
    └── README.md
```

## Examples Overview

### Minimal Example (`minimal/`)

The absolute minimum required for a valid diagnostic description:
- Schema version
- Basic metadata
- ECU identification with DoIP addressing
- Default session
- Basic services
- One access pattern

**Use this as a starting template for new ECU definitions.**

### Basic Example (`basic/`)

Demonstrates common features used in most real-world ECUs:
- Multiple sessions (default, extended, programming)
- Security access levels
- Custom type definitions with scaling
- Identification DIDs (VIN, part numbers)
- Live data DIDs (engine parameters)
- Writable DIDs with security
- DTC configuration with snapshots

**Use this for typical powertrain/chassis ECUs.**

### Full Example

For the most comprehensive example with all schema features, see:
- `../diagnostic_yaml/example-ecm.yml`

This includes advanced features:
- Variant detection (bootloader vs application)
- State model configuration
- Authentication (0x29)
- Routines with parameters
- Memory operations
- ECU Jobs
- Audience filtering
- SDGs and annotations

## Quick Start

```bash
# Navigate to yaml-to-mdd directory
cd opensovd-server/yaml-to-mdd

# Validate all examples
poetry run yaml-to-mdd validate examples/minimal/minimal-ecu.yaml
poetry run yaml-to-mdd validate examples/basic/basic-ecu.yaml

# Convert to MDD
poetry run yaml-to-mdd convert examples/basic/basic-ecu.yaml -o examples/basic/basic-ecu.mdd

# Show summary
poetry run yaml-to-mdd validate examples/basic/basic-ecu.yaml --summary
```

## Related Documentation

- [README.md](../README.md) - Project overview and installation
- [doc/design.md](../doc/design.md) - Architecture and design
- [diagnostic_yaml/SCHEMA.md](../../diagnostic_yaml/SCHEMA.md) - Complete schema reference
- [diagnostic_yaml/ODX_YAML_MAPPING.md](../../diagnostic_yaml/ODX_YAML_MAPPING.md) - ODX to YAML mapping
