# Diagnostic YAML Schema

This directory defines the **OpenSOVD CDA Diagnostic Description** document format via a JSON Schema.

## Overview

The schema describes diagnostic capabilities of an ECU for automotive diagnostics and is designed to be:

- **Strict by default**: most objects use `additionalProperties: false` to catch typos
- **Minimal**: only core information is required; many sections are optional
- **Standards-aligned**: models UDS services (ISO 14229), DoIP (ISO 13400), and CAN addressing (ISO 15765)
- **Extensible**: OEM-specific data can live under `x-oem`

## Files

| File                                       | Description                                           |
| ------------------------------------------ | ----------------------------------------------------- |
| [schema.json](schema.json)                 | JSON Schema (draft 2020-12) - the normative reference |
| [SCHEMA.md](SCHEMA.md)                     | Detailed schema documentation with examples           |
| [ODX_YAML_MAPPING.md](ODX_YAML_MAPPING.md) | Mapping between ODX and YAML concepts                 |
| [example-ecm.yml](example-ecm.yml)         | Complete example: Engine Control Module               |
| [minimal-ecu.yml](minimal-ecu.yml)         | Minimal valid configuration                           |
| [validate.py](validate.py)                 | Python script to validate YAML against schema         |

## Schema Version

Current version: `opensovd.cda.diagdesc/v1`

Every document must include:

```yaml
schema: opensovd.cda.diagdesc/v1
```

## Quick Start

### Minimal Configuration

```yaml
schema: "opensovd.cda.diagdesc/v1"

meta:
  author: "Your Team"
  domain: "Production"
  created: "2026-01-26"
  revision: "1.0.0"
  description: "My ECU Configuration"

ecu:
  id: "MY_ECU"
  name: "My Electronic Control Unit"
  addressing:
    doip:
      ip: "192.168.0.50"
      port: 13400
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

### Validation

```bash
# Install dependencies
pip install pyyaml jsonschema

# Validate your YAML
python validate.py your-ecu.yml

# Or validate multiple files
python validate.py example-ecm.yml minimal-ecu.yml
```

## Document Structure

### Required Top-Level Fields

| Field             | Description                                |
| ----------------- | ------------------------------------------ |
| `schema`          | Must be `opensovd.cda.diagdesc/v1`         |
| `meta`            | Document metadata (author, revision, etc.) |
| `ecu`             | ECU identity and addressing (DoIP/CAN)     |
| `sessions`        | Diagnostic sessions supported              |
| `services`        | UDS services enabled/configured            |
| `access_patterns` | Reusable access control definitions        |

### Optional Top-Level Fields

| Field            | Description                           |
| ---------------- | ------------------------------------- |
| `security`       | UDS 0x27 security access levels       |
| `authentication` | UDS 0x29 authentication configuration |
| `types`          | Reusable data type definitions        |
| `dids`           | Data Identifiers (0x22/0x2E/0x2F)     |
| `routines`       | Routine Control definitions (0x31)    |
| `dtc_config`     | DTC snapshot/extended data config     |
| `dtcs`           | Diagnostic Trouble Codes (0x19)       |
| `x-oem`          | OEM-specific extensions               |

## Hex Values

Many fields accept either integers or hex strings:

```yaml
# Both are valid:
logical_address: 3584      # Integer
logical_address: 0x0E00    # Hex string (quoted in YAML)
logical_address: "0x0E00"  # Explicit string
```

## Supported UDS Services

| SID                                                      | Service                        | Support     |
| -------------------------------------------------------- | ------------------------------ | ----------- |
| 0x10                                                     | DiagnosticSessionControl       | Full        |
| 0x11                                                     | ECUReset                       | Full        |
| 0x14                                                     | ClearDiagnosticInformation     | Full        |
| 0x19                                                     | ReadDTCInformation             | Full        |
| 0x22                                                     | ReadDataByIdentifier           | Full        |
| 0x27                                                     | SecurityAccess                 | Full        |
| 0x29                                                     | Authentication                 | Full        |
| 0x2E                                                     | WriteDataByIdentifier          | Full        |
| 0x2F                                                     | InputOutputControlByIdentifier | Full        |
| 0x31                                                     | RoutineControl                 | Full        |
| 0x3E                                                     | TesterPresent                  | Full        |
| 0x23, 0x24, 0x28, 0x2A, 0x2C, 0x34-0x38, 0x3D, 0x84-0x87 | Other services                 | Enable only |

## Further Reading

- [SCHEMA.md](SCHEMA.md) - Complete schema reference with all fields documented
- [ODX_YAML_MAPPING.md](ODX_YAML_MAPPING.md) - How ODX concepts map to YAML
- [example-ecm.yml](example-ecm.yml) - Full example with DIDs, DTCs, routines, security
