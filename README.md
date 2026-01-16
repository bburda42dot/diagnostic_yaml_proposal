# diagnostic_yaml_proposal

This directory defines the **OpenSOVD CDA Diagnostic Description** document format via a JSON Schema.

The schema is the normative reference. Documents can be authored as **JSON** or **YAML** (YAML is commonly used for readability), but they must validate against `schema.json`.

## Overview

The schema describes diagnostic capabilities of an ECU for automotive diagnostics and is designed to be:

- **Strict by default**: most objects use `additionalProperties: false` to catch typos.
- **Minimal**: only core information is required; many sections are optional.
- **Standards-aligned**: models UDS services (ISO 14229), DoIP (ISO 13400), and CAN addressing (ISO 15765).
- **Extensible**: OEM-specific data can live under `x-oem` (intentionally loosely validated).

## File Structure

```bash
diagnostic_yaml_proposal/
├── schema.json       # JSON Schema for v1
├── example-ecm.yml   # Example diagnostic description (YAML) that should validate against schema.json
├── validate.py       # Local validator (loads YAML and validates against schema.json)
├── LICENSE
└── README.md         # This file
```

## Schema Version

Current version: `opensovd.cda.diagdesc/v1`

Every document must include:

```yaml
schema: opensovd.cda.diagdesc/v1
```

`schema.json` enforces this exact string.

## Document Encoding Notes

### Hex scalars

Many fields accept either:

- an **integer** (e.g. `61456`), or
- a **hex string** in the form `0x...` (e.g. `"0xF010"`).

For YAML authors, unquoted `0xF190` may be parsed as an integer by some YAML parsers; this is why the schema often allows both representations.

### Hex keys in YAML maps

Sections like `dids`, `dtcs`, and `routines` are modeled as maps where the *keys* are the numeric identifiers (e.g. DID 0xF190). JSON Schema cannot reliably validate YAML map keys that may be parsed as integers vs strings, so the schema intentionally does **not** enforce key patterns for those maps.

## Root Document Structure

Root is a strict object (`additionalProperties: false`).

### Required top-level fields

- `schema`: must be `opensovd.cda.diagdesc/v1`
- `meta`: document metadata
- `ecu`: ECU identity + addressing
- `sessions`: diagnostic sessions supported by the ECU
- `services`: UDS services supported (enable/disable + optional constraints)
- `access_patterns`: reusable access control definitions

### Optional top-level fields

- `security`: UDS 0x27 security access levels
- `authentication`: UDS 0x29 authentication roles and anti-brute-force settings
- `types`: reusable data type definitions
- `dids`: Data Identifiers (0x22/0x2E/0x2F)
- `routines`: Routine Control definitions (0x31)
- `dtc_config`: shared configuration for DTC snapshots / extended data
- `dtcs`: Diagnostic Trouble Codes (0x19)
- `x-oem`: OEM extensions (free-form object)

## References and Cross-Links

The schema uses **string references** across sections (e.g. an access pattern name referenced by a DID). These are semantically meaningful, but most of them are not validated at the JSON Schema level (JSON Schema does not naturally express “map key exists elsewhere” constraints).

Common references:

- **Session name**: keys under `sessions` (e.g. `default`, `extended`)
- **Security level name**: keys under `security` (e.g. `level_01`)
- **Authentication role name**: keys under `authentication.roles` (e.g. `factory`)
- **Access pattern name**: keys under `access_patterns` (e.g. `public`, `secured_write`)
- **Type name**: keys under `types`
- **Snapshot / extended-data names**: keys under `dtc_config.snapshots` / `dtc_config.extended_data`

The example document in this repo is [example-ecm.yml](example-ecm.yml).

## Quick Start

```yaml
schema: "opensovd.cda.diagdesc/v1"

meta:
  author: "Your Team"
  domain: "Variant"
  created: "2026-01-12"
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
  readDataByIdentifier:
    enabled: true
  writeDataByIdentifier:
    enabled: false

access_patterns:
  public:
    sessions: any
    security: none
    authentication: none
```

## Validation

`schema.json` is JSON Schema draft 2020-12.

- If your document is JSON, validate it directly.
- If your document is YAML, parse it as YAML first (producing a JSON-like object), then validate that object against the schema.

Tip: because the root object is strict, unknown top-level keys will fail validation.

Local validation helper (YAML + schema):

```bash
python3 diagnostic_yaml_proposal/validate.py
```

## Schema Sections

This section explains the main schema blocks as defined in `schema.json`.

### 1. `meta`

Document metadata:

- Required: `author`, `domain`, `created` (date), `revision` (semver), `description`
- Optional: `tags` (string list), `revisions[]` (changelog entries)

### 2. `ecu`

ECU identity and addressing.

Required: `id`, `name`, `addressing`.

`ecu.addressing` supports:

- `doip`:
  - Required: `ip`, `logical_address`, `tester_address`
  - Optional: `port`, `functional_address`, `routing_activation`
- `can`:
  - Optional: `physical_request`, `physical_response`, `functional_request` (all hex32)
- `timing`:
  - Optional: `p2_ms`, `p2_star_ms`, `s3_ms`

### 3. Sessions (`sessions`)

Defines available diagnostic sessions per ISO 14229-1:

| Session         | ID     | Description                            |
| --------------- | ------ | -------------------------------------- |
| `default`       | 0x01   | Default session, limited functionality |
| `programming`   | 0x02   | ECU reprogramming mode                 |
| `extended`      | 0x03   | Extended diagnostic session            |
| OEM (0x40-0x7E) | varies | Manufacturer/supplier specific         |

```yaml
sessions:
  default:
    id: 0x01
  extended:
    id: 0x03
  programming:
    id: 0x02
    requires_unlock: true
```

Each session is a map entry `session_name -> session`:

- Required: `id` (hex8)
- Optional: `alias`, `requires_unlock`, `timing.p2_ms`, `timing.p2_star_ms`

### 4. Security (`security`)

Security access levels per UDS 0x27:

```yaml
security:
  level_01:
    level: 1
    seed_request: 0x01      # Odd subfunction
    key_send: 0x02          # Even subfunction
    seed_size: 16
    key_size: 16
    algorithm: "aes_cmac_v1"
    max_attempts: 3
    delay_on_fail_ms: 10000
    allowed_sessions: [extended, programming]
```

`security` is a map `level_name -> security_level`.

Each security level requires:

- `level` (uint8)
- `seed_request` / `key_send` (hex8)
- `seed_size` / `key_size` (uint8)
- `algorithm` (string)
- `max_attempts` (uint8)
- `delay_on_fail_ms` (uint32)
- `allowed_sessions` (string list)

### 5. Authentication (`authentication`)

Optional UDS 0x29-related configuration.

- `anti_brute_force`: `max_attempts`, `delay_initial_s`, `delay_max_s`, `delay_multiplier`
- `roles`: map `role_name -> role` where each role requires:
  - `id` (hex8)
  - `timeout_s` (uint16)
  - `certificate_ref` (string)
  - `allowed_sessions` (string list)
  - `proof_of_ownership` (boolean)

### 6. Services (`services`)

`services` is a strict object with known UDS services as properties. Each service entry requires at least:

- `enabled: true|false`

Some services support additional constraints (selected examples):

- `diagnosticSessionControl.subfunctions`: hex8 list or name->hex8 map
- `ecuReset.subfunctions`: name->hex8 map
- `readMemoryByAddress` / `writeMemoryByAddress`: `alfid`, `max_length`, and allowed `regions[]`
- `requestDownload` / `requestUpload`: `max_number_of_block_length` and `regions[]`
- `requestFileTransfer.max_file_size`: uint64 (number or numeric string)
- `routineControl.subfunctions`: list of `startRoutine|stopRoutine|requestResults`
- `inputOutputControlByIdentifier.control_types`: list of allowed control type strings

The schema defines a helper `hex8_list_or_map` used by multiple services.

Supported service keys in `services` (each is optional, but if present must conform to its schema):

- `diagnosticSessionControl`: optional `subfunctions` (hex8 list or name->hex8 map)
- `ecuReset`: optional `subfunctions` (name->hex8 map)
- `securityAccess`: no additional fields
- `authentication`: optional `subfunctions` (hex8 list or name->hex8 map)
- `testerPresent`: no additional fields
- `controlDTCSetting`: no additional fields
- `clearDiagnosticInformation`: no additional fields
- `readDataByIdentifier`: no additional fields
- `writeDataByIdentifier`: no additional fields
- `inputOutputControlByIdentifier`: optional `control_types` (enum list)
- `routineControl`: optional `subfunctions` (`startRoutine|stopRoutine|requestResults`)
- `readDTCInformation`: optional `subfunctions` (hex8 list)
- `communicationControl`: optional `subfunctions`, `communication_types` (hex8 list), `nrc_on_fail` (hex8)
- `responseOnEvent`: optional `subfunctions`, `max_active_events` (uint8)
- `linkControl`: optional `subfunctions`
- `readMemoryByAddress`: optional `alfid` (hex8), `max_length` (uint16), `regions[]`
- `writeMemoryByAddress`: optional `alfid` (hex8), `max_length` (uint16), `regions[]`
- `readScalingDataByIdentifier`: optional `dids[]` (hex16)
- `readDataByPeriodicIdentifier`: optional `subfunctions`, `supported_periods_ms[]` (uint16), `identifiers[]` (hex8)
- `dynamicallyDefineDataIdentifier`: optional `subfunctions`, `max_dynamic_dids` (uint16), `allow_by_identifier` (bool), `allow_by_memory_address` (bool)
- `requestDownload`: optional `max_number_of_block_length` (uint32), `regions[]`
- `requestUpload`: optional `max_number_of_block_length` (uint32), `regions[]`
- `transferData`: optional `max_block_sequence_counter` (uint8)
- `requestTransferExit`: no additional fields
- `requestFileTransfer`: optional `subfunctions`, `max_file_size` (uint64)
- `securedDataTransmission`: optional `subfunctions`

### 7. Access Patterns (`access_patterns`)

Reusable access control definitions combining sessions, security, and authentication:

```yaml
access_patterns:
  public:
    sessions: any          # 'any' = all sessions defined in 'sessions' section
    security: none
    authentication: none
    
  secured_write:
    sessions: [extended]   # Explicit list of session names
    security: [level_01]   # Required security levels (0x27)
    authentication: none
    
  factory_access:
    sessions: [extended, programming]
    security: [level_01]
    authentication: [factory, oem]  # Required authentication roles (0x29)
```

Each access pattern is a map entry `pattern_name -> access_pattern`.

Required fields:

- `sessions`: either `"any"` or a list of session names
- `security`: either `"none"` or a list of security level names
- `authentication`: either `"none"` or a list of authentication role names

Optional fields:

- `nrc_on_fail`: hex8 (generic NRC if access is denied due to pattern-level failure)

### Negative Response Codes (NRC)

Common NRCs per ISO 14229-1:

| NRC  | Name                                  | Description                             |
| ---- | ------------------------------------- | --------------------------------------- |
| 0x10 | generalReject                         | General reject                          |
| 0x11 | serviceNotSupported                   | Service not supported                   |
| 0x12 | subFunctionNotSupported               | Sub-function not supported              |
| 0x13 | incorrectMessageLengthOrInvalidFormat | Incorrect message length                |
| 0x22 | conditionsNotCorrect                  | Conditions not correct                  |
| 0x24 | requestSequenceError                  | Request sequence error                  |
| 0x31 | requestOutOfRange                     | Request out of range                    |
| 0x33 | securityAccessDenied                  | Security access denied                  |
| 0x35 | invalidKey                            | Invalid key                             |
| 0x36 | exceedNumberOfAttempts                | Exceed number of attempts               |
| 0x37 | requiredTimeDelayNotExpired           | Required time delay not expired         |
| 0x70 | uploadDownloadNotAccepted             | Upload/download not accepted            |
| 0x71 | transferDataSuspended                 | Transfer data suspended                 |
| 0x72 | generalProgrammingFailure             | General programming failure             |
| 0x73 | wrongBlockSequenceCounter             | Wrong block sequence counter            |
| 0x7F | serviceNotSupportedInActiveSession    | Service not supported in active session |
| 0x81 | rpmTooHigh                            | RPM too high                            |
| 0x82 | rpmTooLow                             | RPM too low                             |
| 0x83 | engineIsRunning                       | Engine is running                       |
| 0x84 | engineIsNotRunning                    | Engine is not running                   |
| 0x85 | engineRunTimeTooLow                   | Engine run time too low                 |
| 0x86 | temperatureTooHigh                    | Temperature too high                    |
| 0x87 | temperatureTooLow                     | Temperature too low                     |
| 0x88 | vehicleSpeedTooHigh                   | Vehicle speed too high                  |
| 0x89 | vehicleSpeedTooLow                    | Vehicle speed too low                   |
| 0x92 | voltageTooHigh                        | Voltage too high                        |
| 0x93 | voltageTooLow                         | Voltage too low                         |

### 8. Types (`types`)

Data type definitions with physical conversion (linear: `physical = internal * scale + offset`):

```yaml
types:
  temperature:
    base: u8
    scale: 1
    offset: -40
    unit: "degC"
    constraints:
      physical: [-40, 215]
      
  session_enum:
    base: u8
    enum:
      0x01: defaultSession
      0x02: programmingSession
      0x03: extendedDiagnosticSession
```

`types` is a map `type_name -> type_definition` where a type is one of:

- **Atomic type** (`base: u8|u16|...|ascii|bytes`) with optional:
  - `endian: big|little`
  - `length` (used for `ascii`/`bytes`)
  - `scale` / `offset` (numeric conversions)
  - `unit`, `pattern`
  - `constraints.internal` / `constraints.physical`: `[min, max]`
  - `validation.forbidden_characters`: string list
  - `validation.forbidden_values`: list of integer or `0x...` strings
- **Enum type** (`base: u8|u16`, `enum: <map>`)
- **Struct type** (`base: struct`, `size`, `fields[]`), where each field at minimum has `name`.

Note: `struct.fields[]` intentionally allows additional properties to keep the schema flexible; interpretation is implementation-defined.

### 9. DIDs (`dids`)

Data Identifiers for read/write operations:

```yaml
dids:
  0xF190:
    name: "VIN"
    type:
      base: ascii
      length: 17
    access: public
    readable: true        # Default: true
    writable: false       # Default: false
    snapshot: false       # Default: false
    
  0x1001:
    name: "EngineSpeed"
    type: rpm_type        # Reference to types section
    access: public
    readable: true
    writable: false
    snapshot: true        # Can be captured in DTC freeze frame
    
  0x2001:
    name: "FuelPump"
    type:
      base: u8
    access: secured_write
    readable: true
    writable: false
    snapshot: false
    io_control:           # Optional: for InputOutputControl (0x2F)
      enabled: true       # Default: false
      return_control_to_ecu: true
      short_term_adjustment: true
```

Each DID entry requires:

- `name` (string)
- `type`: either a string type reference (to `types`) or an inline type object
- `access`: access pattern name (string)

Optional fields:

- `description`
- `readable`, `writable`, `snapshot` (booleans)
- `io_control`: `enabled` and supported control type flags

Defaults (if your implementation defines them) are not encoded in the schema; the schema only validates presence/shape when fields are provided.

### 10. Routines (`routines`)

Routine Control definitions (UDS 0x31):

```yaml
routines:
  0xFF01:
    name: "CylinderBalanceTest"
    access: secured_write
    operations: [start, stop, result]
    parameters:
      start:
        input:
          - name: cylinderMask
            type:
              base: u8
      result:
        output:
          - name: status
            type:
              base: u8
              enum:
                0: pass
                1: fail
```

Each routine entry requires:

- `name`
- `access` (access pattern name)
- `operations`: list containing any of `start`, `stop`, `result`

Optional:

- `description`
- `parameters`: free-form object (implementation-defined)

### 11. DTC Configuration and DTCs (`dtc_config`, `dtcs`)

`dtc_config` defines reusable snapshot and extended-data record metadata.

- `status_availability_mask` (hex8)
- `snapshots`: map `name -> snapshot_definition`
  - Required: `record_number` (hex8), `dids[]` (hex16)
  - Optional: `trigger` (string), `update` (bool), `x-oem` (object)
- `extended_data`: map `name -> extended_data_definition`
  - Required: `record_number` (hex8)
  - Optional: `type` (type ref or inline type), `trigger` (string), `x-oem` (object)

`dtcs` is a map `dtc -> dtc_definition`.

Each DTC requires:

- `name`
- `sae` (e.g. `P0123`)

Optional fields:

- `description`
- `severity` (1..4)
- `snapshots`: list of snapshot names
- `extended_data`: list of extended-data names
- `x-oem`: free-form object

Diagnostic Trouble Codes:

```yaml
dtc_config:
  status_availability_mask: 0x7F
  snapshots:
    current:
      record_number: 0x01
      trigger: testFailed
      update: true
      dids: [0x1001, 0x1002]
  extended_data:
    occurrenceCounter:
      record_number: 0x01
      type:
        base: u8

dtcs:
  0x012300:
    name: "ThrottlePositionHigh"
    sae: "P0123"
    description: "Throttle Position Sensor A Circuit High"
    severity: 2
    snapshots: [current]
    extended_data: [occurrenceCounter]
```

### 12. OEM Extensions (`x-oem`)

Optional OEM-specific extensions.

This section is intentionally open-ended: `x-oem` is defined as an object without a fixed schema. Use it to attach OEM or project-specific configuration without breaking validation of the standardized parts.

```yaml
x-oem:
  note: "Placeholder for OEM extensions"
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

**Note on "Enable only":** these services can be enabled/disabled via `enabled: true|false`.
If you need to capture more of the UDS-defined behavior (e.g., supported subfunctions, transfer limits, memory regions), optional per-service fields are available in the schema. See the `services` section in `schema.json`.

Example:

```yaml
services:
  readMemoryByAddress:                            # 0x23
    enabled: true
  readScalingDataByIdentifier:                    # 0x24
    enabled: true
  communicationControl:                           # 0x28
    enabled: false
  readDataByPeriodicIdentifier:                   # 0x2A
    enabled: false
  dynamicallyDefineDataIdentifier:                # 0x2C
    enabled: false
  writeMemoryByAddress:                           # 0x3D
    enabled: false
  securedDataTransmission:                        # 0x84
    enabled: false
  responseOnEvent:                                # 0x86
    enabled: false
  linkControl:                                    # 0x87
    enabled: false
```
