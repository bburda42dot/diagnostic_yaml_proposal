#!/usr/bin/env python3
"""Generate Python bindings from Protobuf schema.

Usage:
    poetry run generate-proto
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def find_protoc() -> Path | None:
    """Find the protoc compiler."""
    protoc = shutil.which("protoc")
    if protoc:
        return Path(protoc)
    return None


def check_protoc_version(protoc: Path) -> str:
    """Get protoc version."""
    result = subprocess.run(
        [str(protoc), "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def main() -> int:
    """Generate Protobuf Python bindings."""
    # Determine paths
    script_dir = Path(__file__).parent
    src_dir = script_dir.parent
    proto_dir = src_dir / "proto"
    output_dir = src_dir / "proto_generated"
    schema_file = proto_dir / "file_format.proto"

    # Verify schema exists
    if not schema_file.exists():
        print(f"Error: Schema file not found: {schema_file}")
        print("Make sure the Protobuf schema is in src/yaml_to_mdd/proto/")
        return 1

    # Find protoc
    protoc = find_protoc()
    if not protoc:
        print("Error: protoc not found. Please install Protocol Buffers compiler.")
        print("  Ubuntu/Debian: sudo apt-get install protobuf-compiler")
        print("  macOS: brew install protobuf")
        return 1

    # Check version
    version = check_protoc_version(protoc)
    print(f"Using protoc: {protoc} ({version})")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate Python bindings with type stubs
    print(f"Generating Protobuf Python bindings from {schema_file.name}...")
    try:
        result = subprocess.run(
            [
                str(protoc),
                f"--proto_path={proto_dir}",
                f"--python_out={output_dir}",
                f"--pyi_out={output_dir}",
                str(schema_file),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print(f"Error: protoc failed with exit code {result.returncode}")
            print(result.stderr)
            return 1

    except subprocess.CalledProcessError as e:
        print(f"Error running protoc: {e}")
        return 1

    # Create __init__.py for the generated package
    init_content = '''\
# Auto-generated Protobuf bindings
# Do not edit manually - regenerate with: poetry run generate-proto
#
# Copyright (c) 2025 The Contributors to Eclipse OpenSOVD
# Licensed under Apache License 2.0

"""Generated Protobuf bindings for MDD file format.

This package contains auto-generated Python code from the
file_format.proto Protobuf schema.

To regenerate, run:
    poetry run generate-proto
"""

from yaml_to_mdd.proto_generated.file_format_pb2 import (
    Chunk,
    Encryption,
    MDDFile,
    Signature,
)

__all__ = [
    "Chunk",
    "Encryption",
    "MDDFile",
    "Signature",
]
'''
    init_file = output_dir / "__init__.py"
    init_file.write_text(init_content)

    # Count generated files
    py_files = list(output_dir.glob("*.py"))
    pyi_files = list(output_dir.glob("*.pyi"))
    print("\nGeneration complete!")
    print(f"Output directory: {output_dir}")
    print(f"Generated {len(py_files)} Python files, {len(pyi_files)} type stub files")

    return 0


if __name__ == "__main__":
    sys.exit(main())
