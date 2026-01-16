#!/usr/bin/env python3

import glob
import ipaddress
import json
import os
import sys
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker


def _format_error(path: str, error) -> str:
    loc = "/".join(str(p) for p in error.path)
    if loc:
        loc = f"/{loc}"
    return f"- {path}{loc}: {error.message}"


def _load_schema(schema_path: str) -> dict[str, Any]:
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    root = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(root, "schema.json")
    schema = _load_schema(schema_path)

    checker = FormatChecker()

    @checker.checks("ipv4")
    def _is_ipv4(value: str) -> bool:
        try:
            ipaddress.IPv4Address(value)
            return True
        except Exception:
            return False

    @checker.checks("ipv6")
    def _is_ipv6(value: str) -> bool:
        try:
            ipaddress.IPv6Address(value)
            return True
        except Exception:
            return False

    validator = Draft202012Validator(schema, format_checker=checker)

    exit_code = 0
    for path in sorted(glob.glob(os.path.join(root, "*.yml")) + glob.glob(os.path.join(root, "*.yaml"))):
        base = os.path.basename(path)
        if base == "schema.yml":
            print(f"⊘ {base} (skipped - pseudocode documentation)")
            continue

        print(f"Validating {base}...")
        with open(path, "r", encoding="utf-8") as f:
            instance = yaml.safe_load(f)

        errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
        if errors:
            print(f"✗ {base} failed schema validation:")
            for err in errors[:50]:
                print(_format_error(base, err))
            if len(errors) > 50:
                print(f"  ... {len(errors) - 50} more errors")
            exit_code = 1
        else:
            print(f"✓ {base} validates against schema.json")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
