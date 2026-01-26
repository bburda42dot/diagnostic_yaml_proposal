# Diagnostic YAML Proposal

A proposal for using **YAML** as a human-friendly alternative to ODX for describing ECU diagnostic capabilities.

## Why YAML Instead of ODX?

| Aspect              | ODX (ISO 22901)                   | Diagnostic YAML                  |
| ------------------- | --------------------------------- | -------------------------------- |
| **Format**          | XML-based, verbose                | YAML/JSON, concise               |
| **Readability**     | Complex, tool-dependent           | Human-readable, git-friendly     |
| **Learning curve**  | Steep, requires specialized tools | Minimal, standard text editors   |
| **Version control** | Difficult diffs                   | Clean, line-by-line diffs        |
| **Tooling**         | Expensive commercial tools        | Open-source, standard toolchains |
| **Validation**      | Custom parsers                    | JSON Schema (widely supported)   |

## Repository Structure

```
diagnostic_yaml_proposal/
├── yaml-schema/              # YAML schema definition
│   ├── schema.json           # JSON Schema (v1)
│   ├── SCHEMA.md             # Detailed documentation
│   ├── example-ecm.yml       # Example configurations
│   └── validate.py           # Validation script
├── yaml-to-mdd/              # YAML to MDD converter
│   ├── src/                  # Python source code
│   ├── tests/                # Test suite
│   └── pyproject.toml        # Project configuration
├── docker-compose.yml        # Run OpenSOVD CDA
├── run-cda.sh                # Convenience script
└── README.md                 # This file
```

## Components

### 1. YAML Schema (`yaml-schema/`)

JSON Schema defining the diagnostic YAML format. Standards-aligned with ISO 14229 (UDS), ISO 13400 (DoIP), and ISO 15765 (CAN).

**[→ Schema Documentation](yaml-schema/README.md)**

### 2. YAML to MDD Converter (`yaml-to-mdd/`)

Python tool to convert Diagnostic YAML to MDD binary format used by OpenSOVD Classic Diagnostic Adapter.

**[→ Converter Documentation](yaml-to-mdd/README.md)**

### 3. Docker Setup

Run OpenSOVD Classic Diagnostic Adapter with your YAML configuration.

**[→ Docker Setup](#running-opensovd-cda)**

## Quick Start

### 1. Write Your Diagnostic YAML

```yaml
schema: "opensovd.cda.diagdesc/v1"

meta:
  author: "Your Team"
  domain: "Production"
  created: "2026-01-26"
  revision: "1.0.0"
  description: "My ECU"

ecu:
  id: "MY_ECU"
  name: "My Electronic Control Unit"
  addressing:
    doip:
      ip: "192.168.0.50"
      logical_address: 0x0E00
      tester_address: 0x0E80

sessions:
  default:
    id: 0x01

services:
  diagnosticSessionControl:
    enabled: true

access_patterns:
  public:
    sessions: any
    security: none
    authentication: none
```

### 2. Validate

```bash
cd yaml-schema
pip install pyyaml jsonschema
python validate.py your-ecu.yml
```

### 3. Convert to MDD

```bash
cd yaml-to-mdd
pip install -e .
yaml-to-mdd convert ../yaml-schema/your-ecu.yml -o output.mdd
```

### 4. Run OpenSOVD CDA

```bash
# Build and run with docker-compose
./run-cda.sh yaml-schema/example-ecm.yml
```

## Running OpenSOVD CDA

This repository includes a Docker setup to run [OpenSOVD Classic Diagnostic Adapter](https://github.com/eclipse-opensovd/classic-diagnostic-adapter).

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for yaml-to-mdd)

### Using the Convenience Script

```bash
# Convert YAML and start CDA
./run-cda.sh yaml-schema/example-ecm.yml

# Only convert (no Docker)
./run-cda.sh yaml-schema/example-ecm.yml --no-docker

# Custom port
./run-cda.sh yaml-schema/example-ecm.yml --port 9090
```

### Using Docker Compose Directly

```bash
# Build CDA image (first time only)
docker compose build

# Convert your YAML to MDD
cd yaml-to-mdd && pip install -e . && cd ..
yaml-to-mdd convert yaml-schema/example-ecm.yml -o .output/ecu.mdd

# Start CDA
docker compose up
```

CDA will be available at `http://localhost:8080`.

## Related Projects

- [OpenSOVD Classic Diagnostic Adapter](https://github.com/eclipse-opensovd/classic-diagnostic-adapter) - SOVD gateway for classic UDS diagnostics
- [odxtools](https://github.com/mercedes-benz/odxtools) - Python library for ODX files

## Contributing

Contributions are welcome! Please open an issue or pull request.

## License

See [LICENSE](LICENSE).
