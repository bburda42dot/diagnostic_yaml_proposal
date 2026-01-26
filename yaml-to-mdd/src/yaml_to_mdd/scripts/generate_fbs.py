#!/usr/bin/env python3
"""Generate Python bindings from FlatBuffers schema.

Usage:
    poetry run generate-fbs
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path


def find_flatc() -> Path | None:
    """Find the flatc compiler."""
    # Check common locations
    locations = [
        Path("/usr/local/bin/flatc"),
        Path("/usr/bin/flatc"),
    ]

    for loc in locations:
        if loc.exists():
            return loc

    # Check PATH
    flatc = shutil.which("flatc")
    if flatc:
        return Path(flatc)

    return None


def check_flatc_version(flatc: Path) -> str:
    """Get flatc version and check if it supports our schema."""
    result = subprocess.run(
        [str(flatc), "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    version = result.stdout.strip()

    # Extract version number
    match = re.search(r"(\d+)\.(\d+)\.?(\d+)?", version)
    if match:
        major = int(match.group(1))
        if major < 24:
            print(f"Warning: flatc version {version} is older than recommended (24.x)")
            print("You may encounter issues with complex schema features.")

    return version


def fix_imports(output_dir: Path) -> None:
    """Fix relative imports in generated files for package compatibility."""
    dataformat_dir = output_dir / "dataformat"
    if not dataformat_dir.exists():
        return

    for py_file in dataformat_dir.glob("*.py"):
        content = py_file.read_text()
        original = content
        # Fix imports: from dataformat.X import X -> from .X import X
        content = re.sub(
            r"from dataformat\.(\w+) import (\w+)",
            r"from .\1 import \2",
            content,
        )
        # Fix imports: import dataformat.X -> from . import X
        content = re.sub(
            r"^import dataformat\.(\w+)$",
            r"from . import \1",
            content,
            flags=re.MULTILINE,
        )
        if content != original:
            py_file.write_text(content)


def main() -> int:
    """Generate FlatBuffers Python bindings."""
    # Determine paths
    script_dir = Path(__file__).parent
    src_dir = script_dir.parent
    fbs_dir = src_dir / "fbs"
    output_dir = src_dir / "fbs_generated"
    schema_file = fbs_dir / "diagnostic_description.fbs"

    # Verify schema exists
    if not schema_file.exists():
        print(f"Error: Schema file not found: {schema_file}")
        print("Make sure the FlatBuffers schema is in src/yaml_to_mdd/fbs/")
        return 1

    # Find flatc
    flatc = find_flatc()
    if not flatc:
        print("Error: flatc not found. Please install FlatBuffers compiler.")
        print("  Ubuntu/Debian: sudo apt-get install flatbuffers-compiler")
        print("  macOS: brew install flatbuffers")
        print("  Or download from: https://github.com/google/flatbuffers/releases")
        return 1

    # Check version
    version = check_flatc_version(flatc)
    print(f"Using flatc: {flatc} ({version})")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate Python bindings
    print(f"Generating Python bindings from {schema_file.name}...")
    try:
        result = subprocess.run(
            [
                str(flatc),
                "--python",
                "--gen-mutable",
                "--gen-object-api",
                "-o",
                str(output_dir),
                str(schema_file),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print(f"Error: flatc failed with exit code {result.returncode}")
            print(result.stderr)
            return 1

    except subprocess.CalledProcessError as e:
        print(f"Error running flatc: {e}")
        return 1

    # Fix imports for package compatibility
    print("Fixing imports for package compatibility...")
    fix_imports(output_dir)

    # Create __init__.py for the generated package
    init_file = output_dir / "__init__.py"
    init_file.write_text(
        '''\
# Auto-generated FlatBuffers bindings
# Do not edit manually - regenerate with: poetry run generate-fbs
#
# Copyright (c) 2025 The Contributors to Eclipse OpenSOVD
# Licensed under Apache License 2.0

"""Generated FlatBuffers bindings for MDD format.

This package contains auto-generated Python code from the
diagnostic_description.fbs FlatBuffers schema.

To regenerate, run:
    poetry run generate-fbs
"""

from yaml_to_mdd.fbs_generated import dataformat

__all__ = ["dataformat"]
'''
    )

    # Create __init__.py for dataformat subpackage if needed
    dataformat_dir = output_dir / "dataformat"
    if dataformat_dir.exists():
        dataformat_init = dataformat_dir / "__init__.py"
        if not dataformat_init.exists():
            dataformat_init.write_text(
                '''\
# Auto-generated FlatBuffers bindings - dataformat namespace
# Do not edit manually

"""Generated dataformat types from diagnostic_description.fbs."""
'''
            )

    # Count generated files
    py_files = list(output_dir.rglob("*.py"))
    print("\nGeneration complete!")
    print(f"Output directory: {output_dir}")
    print(f"Generated {len(py_files)} Python files")

    return 0


if __name__ == "__main__":
    sys.exit(main())
