# API Usage Examples

This document provides practical examples for using yaml-to-mdd programmatically.

## Loading Diagnostic Descriptions

### From a File

```python
from pathlib import Path
from yaml_to_mdd.models import load_diagnostic_description

# Load and validate YAML file
doc = load_diagnostic_description(Path("path/to/ecu.yaml"))

# Access document structure
print(f"Schema: {doc.schema_version}")
print(f"ECU: {doc.ecu.name} ({doc.ecu.id})")
print(f"Sessions: {list(doc.sessions.keys())}")
print(f"DIDs: {len(doc.dids) if doc.dids else 0}")
print(f"DTCs: {len(doc.dtcs) if doc.dtcs else 0}")
```

### From a Dictionary

```python
from yaml_to_mdd.models.root import DiagnosticDescription

data = {
    "schema": "opensovd.cda.diagdesc/v1",
    "meta": {
        "author": "Test",
        "domain": "Test",
        "created": "2026-01-22",
        "revision": "1.0.0",
        "description": "Test ECU"
    },
    "ecu": {
        "id": "TEST_ECU",
        "name": "Test ECU",
        "protocols": {
            "doip": {
                "protocol_short_name": "UDSonDoIP",
                "is_default": True
            }
        },
        "default_addressing_mode": "physical",
        "addressing": {
            "doip": {
                "ip": "192.168.0.10",
                "port": 13400,
                "logical_address": 0x0E00,
                "tester_address": 0x0E80
            }
        }
    },
    "sessions": {
        "default": {"id": 0x01}
    },
    "services": {
        "diagnosticSessionControl": {"enabled": True},
        "readDataByIdentifier": {"enabled": True}
    },
    "access_patterns": {
        "public": {
            "sessions": "any",
            "security": "none",
            "authentication": "none"
        }
    }
}

doc = DiagnosticDescription.model_validate(data)
```

## Validation

### Basic Validation (List of Errors)

```python
from pathlib import Path
from yaml_to_mdd.models import validate_diagnostic_description

# Returns list of error strings (empty if valid)
errors = validate_diagnostic_description(Path("ecu.yaml"))

if errors:
    print("Validation failed:")
    for error in errors:
        print(f"  - {error}")
else:
    print("File is valid!")
```

### Semantic Validation

```python
from yaml_to_mdd.models import load_diagnostic_description
from yaml_to_mdd.validation.validator import DiagnosticValidator

doc = load_diagnostic_description(Path("ecu.yaml"))

validator = DiagnosticValidator()
result = validator.validate(doc)

if result.is_valid:
    print("Validation passed!")
    if result.warnings:
        print(f"Warnings: {len(result.warnings)}")
        for warning in result.warnings:
            print(f"  - {warning.message}")
else:
    print("Validation failed!")
    for error in result.errors:
        location = error.location.path if error.location else "unknown"
        print(f"  - [{error.code}] {location}: {error.message}")
```

## Conversion

### Basic Conversion

```python
from pathlib import Path
from yaml_to_mdd.models import load_diagnostic_description
from yaml_to_mdd.transform.transformer import YamlToIRTransformer
from yaml_to_mdd.converters import MDDWriter

# Load YAML
doc = load_diagnostic_description(Path("ecu.yaml"))

# Transform to IR (Intermediate Representation)
transformer = YamlToIRTransformer()
ir_db = transformer.transform(doc)

# Write MDD file
writer = MDDWriter()
writer.write(ir_db, Path("ecu.mdd"))
```

### With Compression

```python
# lzma compression (default)
writer = MDDWriter(compression="lzma")
writer.write(ir_db, Path("ecu.mdd"))

# gzip compression
writer = MDDWriter(compression="gzip")
writer.write(ir_db, Path("ecu.mdd"))

# zstd compression (better ratio, requires zstandard package)
writer = MDDWriter(compression="zstd")
writer.write(ir_db, Path("ecu.mdd"))

# No compression
writer = MDDWriter(compression=None)
writer.write(ir_db, Path("ecu.mdd"))
```

### Get MDD Bytes Without Writing

```python
writer = MDDWriter(compression="lzma")
mdd_bytes = writer.write_bytes(ir_db)

print(f"MDD size: {len(mdd_bytes)} bytes")

# Use bytes for other purposes (e.g., send over network)
# ...
```

## Audience Filtering

Filter diagnostic descriptions for specific audiences (e.g., aftermarket tools).

```python
from yaml_to_mdd.models import load_diagnostic_description
from yaml_to_mdd.models.audience import StandardAudience
from yaml_to_mdd.filter.audience_filter import AudienceFilter

doc = load_diagnostic_description(Path("full-ecu.yaml"))

# Filter for aftermarket audience
filter_obj = AudienceFilter(StandardAudience.AFTERMARKET)
filtered_doc = filter_obj.filter(doc)

# Get summary of what was filtered
summary = filter_obj.get_filter_summary(doc, filtered_doc)
print(f"Removed items: {summary['removed']}")
print(f"Original DIDs: {summary.get('original_dids', 0)}")
print(f"Filtered DIDs: {summary.get('filtered_dids', 0)}")

# Convert filtered document
transformer = YamlToIRTransformer()
ir_db = transformer.transform(filtered_doc)
```

### Custom Audience

```python
# Use a custom audience string
filter_obj = AudienceFilter("oem_partner")
filtered_doc = filter_obj.filter(doc)
```

## Working with IR

### Inspect IR Database

```python
from yaml_to_mdd.transform.transformer import YamlToIRTransformer

transformer = YamlToIRTransformer()
ir_db = transformer.transform(doc)

# Database metadata
print(f"ECU Name: {ir_db.ecu_name}")
print(f"Revision: {ir_db.revision}")
print(f"Author: {ir_db.author}")

# Content counts
print(f"DOPs: {len(ir_db.dops)}")
print(f"Services: {len(ir_db.services)}")
print(f"DTCs: {len(ir_db.dtcs)}")

# Sessions
print("Sessions:")
for name, session_id in ir_db.sessions.items():
    print(f"  {name}: 0x{session_id:02X}")

# DOPs (Data Object Properties)
print("DOPs:")
for dop_name, dop in ir_db.dops.items():
    print(f"  {dop.short_name}: {dop.diag_coded_type.type_name.name}")
```

### Inspect Services

```python
# DID read services
print("DID Read Services:")
for did_id, service_name in ir_db.did_read_services.items():
    print(f"  0x{did_id:04X}: {service_name}")

# DID write services
print("DID Write Services:")
for did_id, service_name in ir_db.did_write_services.items():
    print(f"  0x{did_id:04X}: {service_name}")
```

## Reading MDD Files

### Using MDDReader (Recommended)

```python
from pathlib import Path
from yaml_to_mdd.converters import MDDReader, read_mdd_structure

# Option 1: Using the convenience function
structure = read_mdd_structure(Path("ecu.mdd"))

# Option 2: Using the reader class
reader = MDDReader()
structure = reader.read_structure(Path("ecu.mdd"))

# Access parsed data
print(f"ECU Name: {structure.ecu_name}")
print(f"Revision: {structure.revision}")
print(f"Variants: {list(structure.variants.keys())}")
print(f"Services: {len(structure.services)}")
print(f"Sessions: {structure.sessions}")
print(f"Security Levels: {structure.security_levels}")

# DoIP addressing (if available)
if structure.doip_logical_ecu_address:
    print(f"DoIP ECU Address: 0x{structure.doip_logical_ecu_address:04X}")
```

### Read MDD Metadata (Low-level)

```python
from yaml_to_mdd.proto_generated import MDDFile
from yaml_to_mdd.converters.mdd_writer import FILE_MAGIC

with open("ecu.mdd", "rb") as f:
    data = f.read()

# Strip the 20-byte magic header before parsing Protobuf
mdd = MDDFile()
mdd.ParseFromString(data[len(FILE_MAGIC):])

print(f"Format Version: {mdd.version}")
print(f"ECU Name: {mdd.ecu_name}")
print(f"Revision: {mdd.revision}")
print(f"Chunks: {len(mdd.chunks)}")

# Metadata
for key, value in mdd.metadata.items():
    print(f"  {key}: {value}")
```

### List Chunks

```python
chunk_type_names = {
    0: "DIAGNOSTIC_DESCRIPTION",
    1: "JAR_FILE",
    2: "JAR_FILE_PARTIAL",
    3: "EMBEDDED_FILE",
    4: "VENDOR_SPECIFIC",
}

for i, chunk in enumerate(mdd.chunks):
    type_name = chunk_type_names.get(chunk.type, f"UNKNOWN({chunk.type})")
    size = len(chunk.data) if chunk.data else 0
    compression = chunk.compression_algorithm or "none"
    print(f"Chunk {i}: {type_name}, {size} bytes, compression: {compression}")
```

## Error Handling

### Comprehensive Error Handling

```python
from pathlib import Path
from pydantic import ValidationError
from yaml_to_mdd.models import load_diagnostic_description, LoaderError
from yaml_to_mdd.transform.transformer import YamlToIRTransformer
from yaml_to_mdd.converters import MDDWriter

def convert_file(input_path: str, output_path: str) -> bool:
    """Convert a YAML file to MDD with error handling."""
    try:
        # Load and validate
        doc = load_diagnostic_description(Path(input_path))

        # Transform
        transformer = YamlToIRTransformer()
        ir_db = transformer.transform(doc)

        # Write
        writer = MDDWriter(compression="gzip")
        writer.write(ir_db, Path(output_path))

        print(f"Successfully converted {input_path} to {output_path}")
        return True

    except FileNotFoundError as e:
        print(f"File not found: {e}")
        return False

    except LoaderError as e:
        print(f"Failed to load file: {e}")
        return False

    except ValidationError as e:
        print("Schema validation failed:")
        for error in e.errors():
            loc = ".".join(str(x) for x in error["loc"])
            print(f"  {loc}: {error['msg']}")
        return False

    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

# Usage
convert_file("my-ecu.yaml", "my-ecu.mdd")
```

## Model Reference

### DiagnosticDescription

The root model containing all sections:

```python
from yaml_to_mdd.models.root import DiagnosticDescription

# Required fields
doc.schema_version  # "opensovd.cda.diagdesc/v1"
doc.meta           # Meta - document metadata
doc.ecu            # Ecu - ECU identification
doc.sessions       # dict[str, Session] - session definitions
doc.services       # Services - UDS service configuration

# Optional fields
doc.security       # dict[str, SecurityLevel] | None
doc.access_patterns # dict[str, AccessPattern] | None
doc.types          # dict[str, TypeDefinition] | None
doc.dids           # dict[int, DIDDefinition] | None
doc.routines       # dict[int, RoutineDefinition] | None
doc.dtcs           # dict[int, DTCDefinition] | None
doc.dtc_config     # DTCConfig | None
doc.memory         # MemoryConfig | None
```

### Meta

Document metadata:

```python
from yaml_to_mdd.models.meta import Meta

doc.meta.author       # str
doc.meta.domain       # str
doc.meta.created      # date
doc.meta.revision     # str (semver)
doc.meta.description  # str
doc.meta.tags         # list[str] | None
doc.meta.revisions    # list[RevisionEntry] | None
```

### Ecu

ECU identification and addressing:

```python
from yaml_to_mdd.models.ecu import Ecu

doc.ecu.id                      # str
doc.ecu.name                    # str
doc.ecu.protocols               # dict[str, Protocol] | None
doc.ecu.default_addressing_mode # str | None
doc.ecu.addressing              # Addressing
```

### DIDDefinition

Data Identifier definition:

```python
from yaml_to_mdd.models.dids import DIDDefinition

# Access a DID (keys are integers)
did = doc.dids[0xF190]

did.name           # str
did.description    # str | None
did.type           # TypeDefinition | str (type reference)
did.access         # str (access pattern name)
did.readable       # bool | None (default: True)
did.writable       # bool | None (default: False)
did.snapshot       # bool | None (include in DTC snapshots)
```

### TypeDefinition

Type definitions with conversion:

```python
from yaml_to_mdd.models.types import TypeDefinition, BaseType

type_def = doc.types["temperature_type"]

type_def.base       # BaseType enum (u8, u16, u32, ascii, bytes, etc.)
type_def.endian     # "big" | "little" | None
type_def.length     # int | None (for ascii/bytes)
type_def.scale      # float | None
type_def.offset     # float | None
type_def.unit       # str | None
type_def.enum       # dict[int, str] | None
type_def.constraints # TypeConstraints | None
```
