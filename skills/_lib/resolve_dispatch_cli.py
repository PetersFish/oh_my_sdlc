#!/usr/bin/env python3
"""Minimal CLI shim for dev-orchestrator to resolve wrapper dispatch specs.

Usage:
  python3 skills/_lib/resolve_dispatch_cli.py <module> <capability> <run_id> <phase> <action> <flow_type> [repo_root]

Output (JSON):
  {
    "module": "spec",
    "capability": "create",
    "provider": "openspec",
    "dispatch": {
      "kind": "skill",
      "target": "openspec-propose"
    },
    "verifier": {
      "target": "openspec.create"
    },
    "result_contract": "spec_change"
  }

Exits non-zero with error JSON on resolution failures.
"""

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.dirname(SCRIPT_DIR)
if SKILLS_DIR not in sys.path:
    sys.path.insert(0, SKILLS_DIR)

from _lib.wrapper_resolution import WrapperResolutionBlocked, resolve_wrapper_dispatch


def main():
    if len(sys.argv) < 7:
        print(json.dumps({
            "error": "usage: resolve_dispatch_cli.py <module> <capability> <run_id> <phase> <action> <flow_type> [repo_root]",
        }))
        sys.exit(1)

    module = sys.argv[1]
    capability = sys.argv[2]
    run_id = sys.argv[3]
    phase = sys.argv[4]
    action = sys.argv[5]
    flow_type = sys.argv[6]
    repo_root = sys.argv[7] if len(sys.argv) > 7 else "."

    try:
        resolved = resolve_wrapper_dispatch(
            module=module,
            capability=capability,
            workflow_run_id=run_id,
            phase=phase,
            action=action,
            flow_type=flow_type,
            repo_root=repo_root,
        )
        result = {
            "module": resolved.module,
            "capability": resolved.capability,
            "provider": resolved.provider,
            "dispatch": resolved.dispatch,
            "verifier": resolved.verifier,
            "result_contract": resolved.result_contract,
        }
        print(json.dumps(result))
    except WrapperResolutionBlocked as exc:
        print(json.dumps({
            "error": str(exc),
            "blockers": exc.blockers,
        }))
        sys.exit(1)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
