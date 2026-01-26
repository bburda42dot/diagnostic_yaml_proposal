# Basic ECU Example

This example demonstrates common features used in most ECU diagnostic descriptions:
sessions, security, DIDs, types, and DTCs.

## Features Demonstrated

### Sessions
- **default** (0x01) - Limited functionality
- **extended** (0x03) - Full diagnostic access
- **programming** (0x02) - ECU reprogramming mode

### Security
- **level_01** - Basic security access with XOR algorithm

### Access Patterns
- **public** - Read anywhere, no security
- **extended_read** - Read in default or extended sessions
- **extended_write** - Write in extended session with security
- **programming_only** - Flash programming access

### Types
Custom type definitions with scaling and constraints:
- `rpm_type` - Engine speed with 0.25 scale
- `temperature_type` - Temperature with -40°C offset
- `percentage_type` - 0-100% scaled value
- `voltage_type` - Voltage in mV
- `vin_type` - 17-character VIN
- `part_number_type` - 24-character part number

### DIDs
- **Identification DIDs** (0xF1xx) - VIN, part numbers
- **Live Data DIDs** (0x10xx) - Engine speed, temperature, etc.
- **Writable DIDs** (0x20xx) - Calibration values with security

### DTCs
- Common powertrain DTCs with snapshots and extended data
- Snapshot configuration with freeze frame DIDs
- Occurrence counter for extended data

## Usage

### Validate

```bash
poetry run yaml-to-mdd validate basic-ecu.yaml
```

### Convert

```bash
poetry run yaml-to-mdd convert basic-ecu.yaml -o basic-ecu.mdd
```

### Show summary

```bash
poetry run yaml-to-mdd validate basic-ecu.yaml --summary
```

## Next Steps

For advanced features like variants, routines, memory operations, and audience filtering,
see `../../diagnostic_yaml/example-ecm.yml`.
