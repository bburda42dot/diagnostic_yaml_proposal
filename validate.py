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


def _param_path_exists(
    param_path: str, response_outputs: dict[str, dict] | list[dict] | None
) -> bool:
    """
    Check if a dotted param_path exists within response_outputs structure.

    response_outputs can be:
      - dict: { "paramName": { "name": ..., "children": [...] } }
      - list: [ { "name": "paramName", "children": [...] } ]

    Example: param_path="hardware.version" should match:
      response_outputs:
        hardware:
          name: hardware
          children:
            - name: version
    """
    if not response_outputs or not param_path:
        return False

    parts = param_path.split(".")

    def find_in_dict_outputs(
        outputs: dict[str, dict], remaining_parts: list[str]
    ) -> bool:
        if not remaining_parts:
            return True
        target = remaining_parts[0]
        # Check if the key matches directly
        if target in outputs:
            if len(remaining_parts) == 1:
                return True
            entry = outputs[target]
            children = entry.get("children") if isinstance(entry, dict) else None
            if children:
                return find_in_list_outputs(children, remaining_parts[1:])
        # Also check by name property within dict values
        for key, value in outputs.items():
            if isinstance(value, dict) and value.get("name") == target:
                if len(remaining_parts) == 1:
                    return True
                children = value.get("children")
                if children:
                    return find_in_list_outputs(children, remaining_parts[1:])
        return False

    def find_in_list_outputs(outputs: list[dict], remaining_parts: list[str]) -> bool:
        if not remaining_parts:
            return True
        target = remaining_parts[0]
        for output in outputs:
            if isinstance(output, dict) and output.get("name") == target:
                if len(remaining_parts) == 1:
                    return True
                children = output.get("children")
                if children:
                    return find_in_list_outputs(children, remaining_parts[1:])
        return False

    if isinstance(response_outputs, dict):
        return find_in_dict_outputs(response_outputs, parts)
    elif isinstance(response_outputs, list):
        return find_in_list_outputs(response_outputs, parts)
    return False


def _load_schema(schema_path: str) -> dict[str, Any]:
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _find_all_param_ids(
    response_outputs: dict | list | None, prefix: str = ""
) -> list[tuple[str, str]]:
    """
    Recursively find all param_id values in response_outputs structure.
    Returns list of (param_id, location_path) tuples.
    """
    results = []
    if not response_outputs:
        return results

    if isinstance(response_outputs, dict):
        for key, value in response_outputs.items():
            if isinstance(value, dict):
                param_id = value.get("param_id")
                if param_id:
                    results.append((param_id, f"{prefix}{key}"))
                children = value.get("children")
                if children:
                    results.extend(_find_all_param_ids(children, f"{prefix}{key}."))
    elif isinstance(response_outputs, list):
        for i, item in enumerate(response_outputs):
            if isinstance(item, dict):
                param_id = item.get("param_id")
                name = item.get("name", f"[{i}]")
                if param_id:
                    results.append((param_id, f"{prefix}{name}"))
                children = item.get("children")
                if children:
                    results.extend(_find_all_param_ids(children, f"{prefix}{name}."))
    return results


def _param_id_exists(param_id: str, response_outputs: dict | list | None) -> bool:
    """Check if a param_id exists in response_outputs structure."""
    all_ids = _find_all_param_ids(response_outputs)
    return any(pid == param_id for pid, _ in all_ids)


def _semantic_checks(instance: dict[str, Any], path: str) -> list[str]:
    """
    Perform semantic validation that JSON Schema cannot express:
    - Referenced session names exist
    - Referenced security level names exist
    - Referenced authentication role names exist
    - Referenced access pattern names exist
    - Variant detection_order references valid variant names
    - State model references valid sessions
    - Protocol is_default: exactly one default when multiple protocols
    - param_id uniqueness within service response_outputs
    - response_param_match param_id/param_path references
    """
    errors = []

    # Check protocol is_default rule: if multiple protocols, exactly one must be default
    ecu = instance.get("ecu", {})
    protocols = ecu.get("protocols", {})
    if len(protocols) > 1:
        default_protocols = [
            name
            for name, pdef in protocols.items()
            if isinstance(pdef, dict) and pdef.get("is_default") is True
        ]
        if len(default_protocols) == 0:
            errors.append(
                f"- {path}/ecu/protocols: multiple protocols defined but none has is_default: true"
            )
        elif len(default_protocols) > 1:
            errors.append(
                f"- {path}/ecu/protocols: multiple protocols have is_default: true ({', '.join(default_protocols)}), exactly one expected"
            )

    # Collect defined names
    session_names = set(instance.get("sessions", {}).keys())
    security_names = set(instance.get("security", {}).keys())
    auth_roles = set(instance.get("authentication", {}).get("roles", {}).keys())
    access_patterns = set(instance.get("access_patterns", {}).keys())
    variant_names = set(instance.get("variants", {}).get("definitions", {}).keys())

    allowed_state_tokens = {"none", "unchanged", "from_request"}

    # Check state_model references
    state_model = instance.get("state_model", {})
    if state_model:
        initial = state_model.get("initial_state", {})
        if initial.get("session") and initial["session"] not in session_names:
            errors.append(
                f"- {path}/state_model/initial_state/session: "
                f"references undefined session '{initial['session']}'"
            )

        initial_security = initial.get("security")
        if (
            isinstance(initial_security, str)
            and initial_security not in allowed_state_tokens
            and initial_security not in security_names
        ):
            errors.append(
                f"- {path}/state_model/initial_state/security: "
                f"references undefined security level '{initial_security}'"
            )

        transitions = state_model.get("session_transitions", {})
        for from_session, to_sessions in transitions.items():
            if from_session not in session_names:
                errors.append(
                    f"- {path}/state_model/session_transitions: "
                    f"source session '{from_session}' is not defined"
                )
            for to_session in to_sessions or []:
                if to_session not in session_names:
                    errors.append(
                        f"- {path}/state_model/session_transitions/{from_session}: "
                        f"target session '{to_session}' is not defined"
                    )

    # Check security level allowed_sessions
    for level_name, level_def in instance.get("security", {}).items():
        for sess in level_def.get("allowed_sessions", []):
            if sess not in session_names:
                errors.append(
                    f"- {path}/security/{level_name}/allowed_sessions: "
                    f"references undefined session '{sess}'"
                )

    # Check authentication role allowed_sessions
    for role_name, role_def in (
        instance.get("authentication", {}).get("roles", {}).items()
    ):
        for sess in role_def.get("allowed_sessions", []):
            if sess not in session_names:
                errors.append(
                    f"- {path}/authentication/roles/{role_name}/allowed_sessions: "
                    f"references undefined session '{sess}'"
                )

    # Check access pattern references
    for pattern_name, pattern_def in instance.get("access_patterns", {}).items():
        sessions = pattern_def.get("sessions")
        if isinstance(sessions, list):
            for sess in sessions:
                if sess not in session_names:
                    errors.append(
                        f"- {path}/access_patterns/{pattern_name}/sessions: "
                        f"references undefined session '{sess}'"
                    )

        security = pattern_def.get("security")
        if isinstance(security, list):
            for sec in security:
                if sec not in security_names:
                    errors.append(
                        f"- {path}/access_patterns/{pattern_name}/security: "
                        f"references undefined security level '{sec}'"
                    )

        auth = pattern_def.get("authentication")
        if isinstance(auth, list):
            for role in auth:
                if role not in auth_roles:
                    errors.append(
                        f"- {path}/access_patterns/{pattern_name}/authentication: "
                        f"references undefined authentication role '{role}'"
                    )

    # Check DID access pattern references
    for did_id, did_def in instance.get("dids", {}).items():
        access = did_def.get("access")
        if access and access not in access_patterns:
            errors.append(
                f"- {path}/dids/{did_id}/access: "
                f"references undefined access pattern '{access}'"
            )

    # Check routine access pattern references
    for routine_id, routine_def in instance.get("routines", {}).items():
        access = routine_def.get("access")
        if access and access not in access_patterns:
            errors.append(
                f"- {path}/routines/{routine_id}/access: "
                f"references undefined access pattern '{access}'"
            )

    # Check variants
    variants = instance.get("variants", {})
    if variants:
        detection_order = variants.get("detection_order", [])
        for var_name in detection_order:
            if var_name not in variant_names:
                errors.append(
                    f"- {path}/variants/detection_order: "
                    f"references undefined variant '{var_name}'"
                )

        fallback = variants.get("fallback")
        if fallback and fallback not in variant_names:
            errors.append(
                f"- {path}/variants/fallback: "
                f"references undefined variant '{fallback}'"
            )

        # Collect expected_idents names for ident_ref validation
        expected_idents = set(
            instance.get("identification", {}).get("expected_idents", {}).keys()
        )

        # Check variant definitions for ident_ref, probe_context, and state_model overrides
        for vname, vdef in variants.get("definitions", {}).items():
            detect = vdef.get("detect") or {}

            # Check ident_ref references
            ident_ref = detect.get("ident_ref")
            if ident_ref and ident_ref not in expected_idents:
                errors.append(
                    f"- {path}/variants/definitions/{vname}/detect/ident_ref: "
                    f"references undefined expected_ident '{ident_ref}'"
                )

            # Check probe_context references
            probe_ctx = detect.get("probe_context") or {}
            if probe_ctx.get("session") and probe_ctx["session"] not in session_names:
                errors.append(
                    f"- {path}/variants/definitions/{vname}/detect/probe_context/session: "
                    f"references undefined session '{probe_ctx['session']}'"
                )
            if (
                probe_ctx.get("security")
                and probe_ctx["security"] not in security_names
                and probe_ctx["security"] != "none"
            ):
                errors.append(
                    f"- {path}/variants/definitions/{vname}/detect/probe_context/security: "
                    f"references undefined security level '{probe_ctx['security']}'"
                )
            if (
                probe_ctx.get("authentication")
                and probe_ctx["authentication"] not in auth_roles
                and probe_ctx["authentication"] != "none"
            ):
                errors.append(
                    f"- {path}/variants/definitions/{vname}/detect/probe_context/authentication: "
                    f"references undefined authentication role '{probe_ctx['authentication']}'"
                )

            # Check state_model overrides
            v_state_model = (vdef.get("overrides") or {}).get("state_model") or {}
            v_initial = v_state_model.get("initial_state") or {}
            v_sess = v_initial.get("session")
            if v_sess and v_sess not in session_names:
                errors.append(
                    f"- {path}/variants/definitions/{vname}/overrides/state_model/initial_state/session: "
                    f"references undefined session '{v_sess}'"
                )

            v_sec = v_initial.get("security")
            if (
                isinstance(v_sec, str)
                and v_sec not in allowed_state_tokens
                and v_sec not in security_names
            ):
                errors.append(
                    f"- {path}/variants/definitions/{vname}/overrides/state_model/initial_state/security: "
                    f"references undefined security level '{v_sec}'"
                )

    # Check identification expected_idents probe_context references
    identification = instance.get("identification", {})
    # Collect service names for response_param_match validation (early)
    services = instance.get("services", {})
    service_names = set(services.keys())

    for ident_name, ident_def in identification.get("expected_idents", {}).items():
        probe_ctx = ident_def.get("probe_context") or {}
        if probe_ctx.get("session") and probe_ctx["session"] not in session_names:
            errors.append(
                f"- {path}/identification/expected_idents/{ident_name}/probe_context/session: "
                f"references undefined session '{probe_ctx['session']}'"
            )
        if (
            probe_ctx.get("security")
            and probe_ctx["security"] not in security_names
            and probe_ctx["security"] != "none"
        ):
            errors.append(
                f"- {path}/identification/expected_idents/{ident_name}/probe_context/security: "
                f"references undefined security level '{probe_ctx['security']}'"
            )
        if (
            probe_ctx.get("authentication")
            and probe_ctx["authentication"] not in auth_roles
            and probe_ctx["authentication"] != "none"
        ):
            errors.append(
                f"- {path}/identification/expected_idents/{ident_name}/probe_context/authentication: "
                f"references undefined authentication role '{probe_ctx['authentication']}'"
            )

    # Check service state_effects for explicit security/auth references
    # Also check param_id uniqueness in response_outputs
    for sname, sdef in services.items():
        state_effects = (sdef or {}).get("state_effects") or {}
        # Collect all nested effect objects
        candidate_effects: list[dict[str, Any]] = []
        for val in state_effects.values():
            if isinstance(val, dict):
                candidate_effects.append(val)

        for eff in candidate_effects:
            sec = eff.get("security")
            if (
                isinstance(sec, str)
                and sec not in allowed_state_tokens
                and sec not in security_names
            ):
                errors.append(
                    f"- {path}/services/{sname}/state_effects/security: "
                    f"references undefined security level '{sec}'"
                )

            role = eff.get("authentication_role")
            if (
                isinstance(role, str)
                and role not in {"none", "unchanged", "from_request"}
                and role not in auth_roles
            ):
                errors.append(
                    f"- {path}/services/{sname}/state_effects/authentication_role: "
                    f"references undefined authentication role '{role}'"
                )

        # Check param_id uniqueness within service response_outputs
        resp_outputs = (sdef or {}).get("response_outputs")
        if resp_outputs:
            all_param_ids = _find_all_param_ids(resp_outputs)
            seen_ids: dict[str, str] = {}
            for param_id, location in all_param_ids:
                if param_id in seen_ids:
                    errors.append(
                        f"- {path}/services/{sname}/response_outputs: "
                        f"duplicate param_id '{param_id}' at '{location}' (already defined at '{seen_ids[param_id]}')"
                    )
                else:
                    seen_ids[param_id] = location

    # Helper to validate response_param_match (supports both param_path and param_id)
    def _validate_response_param_match(rpm: dict, context_path: str) -> None:
        svc = rpm.get("service")
        if svc and svc not in service_names:
            errors.append(f"- {context_path}: references undefined service '{svc}'")
            return

        param_path = rpm.get("param_path")
        param_id = rpm.get("param_id")

        # Validate oneOf: exactly one of param_path or param_id must be specified
        if param_path and param_id:
            errors.append(
                f"- {context_path}: specify either param_path or param_id, not both"
            )
        elif not param_path and not param_id:
            errors.append(
                f"- {context_path}: must specify either param_path or param_id"
            )

        if svc and svc in service_names:
            svc_def = services.get(svc, {}) or {}
            resp_outputs = svc_def.get("response_outputs")

            if param_path and resp_outputs:
                if not _param_path_exists(param_path, resp_outputs):
                    errors.append(
                        f"- {context_path}/param_path: '{param_path}' not found in services/{svc}/response_outputs"
                    )

            if param_id and resp_outputs:
                if not _param_id_exists(param_id, resp_outputs):
                    errors.append(
                        f"- {context_path}/param_id: '{param_id}' not found in services/{svc}/response_outputs"
                    )

    # Check variant definitions for response_param_match references
    for vname, vdef in variants.get("definitions", {}).items():
        detect = vdef.get("detect") or {}
        rpm = detect.get("response_param_match")
        if rpm:
            _validate_response_param_match(
                rpm, f"{path}/variants/definitions/{vname}/detect/response_param_match"
            )

        # Check match_all and match_any conditions for response_param_match
        for cond_list_name in ["match_all", "match_any"]:
            for i, cond in enumerate(detect.get(cond_list_name, [])):
                rpm = cond.get("response_param_match")
                if rpm:
                    _validate_response_param_match(
                        rpm,
                        f"{path}/variants/definitions/{vname}/detect/{cond_list_name}[{i}]/response_param_match",
                    )

    # Check identification expected_idents conditions for response_param_match (using new validation)
    for ident_name, ident_def in identification.get("expected_idents", {}).items():
        for i, cond in enumerate(ident_def.get("conditions", [])):
            rpm = cond.get("response_param_match")
            if rpm:
                _validate_response_param_match(
                    rpm,
                    f"{path}/identification/expected_idents/{ident_name}/conditions[{i}]/response_param_match",
                )

    # Check audience structure (just warn if strange values, schema handles type validation)
    audience = instance.get("audience", {})
    valid_audience_flags = {
        "supplier",
        "development",
        "manufacturing",
        "aftersales",
        "aftermarket",
        "groups",
    }
    for key in audience.keys():
        if key not in valid_audience_flags:
            errors.append(
                f"- {path}/audience: unexpected key '{key}' (valid: {valid_audience_flags})"
            )

    return errors


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

    # Determine files to validate
    if len(sys.argv) > 1:
        # Accept explicit file paths from command line
        files_to_validate = sys.argv[1:]
    else:
        # Default: validate all *.yml/*.yaml files in the script directory
        files_to_validate = sorted(
            glob.glob(os.path.join(root, "*.yml"))
            + glob.glob(os.path.join(root, "*.yaml"))
        )

    exit_code = 0
    for path in files_to_validate:
        base = os.path.basename(path)
        if base == "schema.yml":
            print(f"⊘ {base} (skipped - pseudocode documentation)")
            continue

        if not os.path.isfile(path):
            print(f"✗ {path}: file not found")
            exit_code = 1
            continue

        print(f"Validating {base}...")
        with open(path, "r", encoding="utf-8") as f:
            instance = yaml.safe_load(f)

        # JSON Schema validation
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

        # Semantic validation
        semantic_errors = _semantic_checks(instance, base)
        if semantic_errors:
            print(f"✗ {base} failed semantic validation:")
            for err in semantic_errors[:50]:
                print(err)
            if len(semantic_errors) > 50:
                print(f"  ... {len(semantic_errors) - 50} more errors")
            exit_code = 1
        elif not errors:
            print(f"✓ {base} passes semantic checks")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
