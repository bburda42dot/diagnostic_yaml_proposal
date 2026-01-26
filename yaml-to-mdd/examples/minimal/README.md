# Minimal ECU Example

This example shows the minimum required fields for a valid diagnostic description file.

## Required Sections

1. **schema** - Schema version identifier (`opensovd.cda.diagdesc/v1`)
2. **meta** - Document metadata (author, domain, created, revision, description)
3. **ecu** - ECU identification and addressing
4. **sessions** - At least one diagnostic session
5. **services** - Service configurations
6. **access_patterns** - At least one access pattern

## File Contents

The `minimal-ecu.yaml` file demonstrates:
- Basic ECU with DoIP addressing
- Default session (0x01)
- Standard services enabled
- A single VIN DID for reading

## Usage

### Validate the file

```bash
poetry run yaml-to-mdd validate minimal-ecu.yaml
```

### Convert to MDD

```bash
poetry run yaml-to-mdd convert minimal-ecu.yaml -o minimal-ecu.mdd
```

### Show file information

```bash
poetry run yaml-to-mdd info minimal-ecu.yaml
```

## Next Steps

Once you're comfortable with the minimal example, explore:
- `../basic/` - Common features like types, DIDs, and DTCs
- `../../diagnostic_yaml/example-ecm.yml` - Full-featured example with all schema features
