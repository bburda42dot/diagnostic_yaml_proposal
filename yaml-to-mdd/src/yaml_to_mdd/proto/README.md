# Protobuf Schema

This directory contains the Protobuf schema file for the MDD (Machine-readable Diagnostic Description) container format.

## Files

- `file_format.proto` - Container format schema

## Regenerating Python Bindings

To regenerate Python bindings after schema changes:

```bash
poetry run generate-proto
```

Generated code will be placed in `../proto_generated/`.

## Schema Overview

### MDDFile (Root Message)

The top-level container for MDD files:

```protobuf
message MDDFile {
  string version = 1;
  repeated FeatureFlag feature_flags = 2;
  string ecu_name = 3;
  string revision = 4;
  map<string, string> metadata = 5;
  repeated Chunk chunks = 6;
  optional Signature chunksSignature = 7;
}
```

### Chunk

A data block within the MDD file:

```protobuf
message Chunk {
  DataType type = 1;
  optional string name = 2;
  map<string, string> metadata = 3;
  repeated Signature signatures = 4;
  optional string compression_algorithm = 5;
  optional uint64 uncompressed_size = 6;
  optional Encryption encryption = 7;
  optional string mimeType = 9;
  optional bytes data = 8;
}
```

### DataType Enum

```protobuf
enum DataType {
  DIAGNOSTIC_DESCRIPTION = 0;  // FlatBuffers diagnostic data
  JAR_FILE = 1;               // Associated JAR file
  JAR_FILE_PARTIAL = 2;       // Partial JAR content
  EMBEDDED_FILE = 3;          // Embedded file (ODX-F, firmware)
  VENDOR_SPECIFIC = 1024;     // Vendor-specific data
}
```

## MDD File Structure

```
┌─────────────────────────────────────┐
│           MDDFile (Protobuf)        │
├─────────────────────────────────────┤
│ version: "1.0.0"                    │
│ ecu_name: "ECU_XYZ"                 │
│ revision: "1.2.3"                   │
│ metadata: {...}                     │
├─────────────────────────────────────┤
│ chunks[0]: DIAGNOSTIC_DESCRIPTION   │
│   data: <FlatBuffers binary>        │
├─────────────────────────────────────┤
│ chunks[1]: EMBEDDED_FILE (optional) │
│   data: <embedded file bytes>       │
├─────────────────────────────────────┤
│ chunksSignature (optional)          │
└─────────────────────────────────────┘
```

## Copyright

Copyright (c) 2025 The Contributors to Eclipse OpenSOVD
Licensed under Apache License 2.0
