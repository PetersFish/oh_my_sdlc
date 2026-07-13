"""cli.py — parser construction, command registration, and exit-code mapping.

Composes command handlers from lifecycle, governance, dispatch, and policies
modules into the public CLI interface.
"""

import argparse
import os
import sys

from workflow_runtime.core import (
    VALID_FLOW_TYPES,
    VALID_SUBJECT_TYPES,
)
from workflow_runtime.policies import (
    cmd_preflight,
    cmd_ensure_run,
)
from workflow_runtime.dispatch import (
    cmd_before_dispatch,
    cmd_after_dispatch,
)
from workflow_runtime.lifecycle import (
    cmd_status,
    cmd_validate,
    cmd_start,
    cmd_resume,
    cmd_readiness,
    cmd_resolve,
    cmd_record_evidence,
    cmd_record_context,
    cmd_complete_phase,
    cmd_complete_hook,
    cmd_cancel_run,
    cmd_advance,
    cmd_block,
    cmd_done,
)
from workflow_runtime.governance import (
    cmd_governance_check,
    cmd_verify_foundations,
    cmd_final_commit,
)
from workflow_runtime.slices import (
    cmd_slice_status,
    cmd_slice_next,
    cmd_slice_block,
    cmd_slice_resume,
    cmd_slice_cancel,
)


COMMANDS = {
    "status",
    "start",
    "resume",
    "readiness",
    "resolve",
    "record-evidence",
    "record-context",
    "complete-phase",
    "complete-hook",
    "advance",
    "block",
    "done",
    "cancel-run",
    "validate",
    "governance-check",
    "preflight",
    "ensure-run",
    "verify-foundations",
    "before-dispatch",
    "after-dispatch",
    "final-commit",
    "slice-status",
    "slice-next",
    "slice-block",
    "slice-resume",
    "slice-cancel",
}


def main():
    parser = argparse.ArgumentParser(description="SDLC workflow runtime")
    parser.add_argument("--root", default=None, help="workspace root path")
    parser.add_argument(
        "command",
        choices=sorted(COMMANDS),
        help="command to execute",
    )
    parser.add_argument("--workflow", default=None, help="workflow id")
    parser.add_argument("--subject-type", default=None, choices=sorted(VALID_SUBJECT_TYPES), help="subject type")
    parser.add_argument("--subject-id", default=None, help="subject id")
    parser.add_argument("--key", default=None, help="evidence key")
    parser.add_argument("--value", default=None, help="evidence value (JSON)")
    parser.add_argument(
        "--exit-criteria-satisfied", default=None, help="comma-separated criteria"
    )
    parser.add_argument("--hook", default=None, help="hook name to complete")
    parser.add_argument("--resolution", default=None, help="resolution value for hook")
    parser.add_argument("--reason", default=None, help="reason for resolution")
    parser.add_argument("--residual-risk", default=None, help="residual risk for deferred")
    parser.add_argument("--branch", default=None, help="branch decision label")
    parser.add_argument("--flow-type", default=None, choices=sorted(VALID_FLOW_TYPES), help="flow type")
    parser.add_argument("--agent", default=None, help="agent name for dispatch hooks")
    parser.add_argument("--phase", default=None, help="phase for dispatch validation")
    parser.add_argument("--slice-id", default=None, help="implementation slice identifier")
    parser.add_argument("--block-type", default=None, help="block type")
    parser.add_argument("--message", default=None, help="block/status message")
    parser.add_argument("--next-allowed", default=None, help="comma-separated next allowed actions")
    parser.add_argument("--action", default=None, help="governed action for preflight/ensure-run")
    parser.add_argument("--run-id", default=None, help="workflow run id for final-commit")
    parser.add_argument("--push", action="store_true", help="push after commit (final-commit)")
    parser.add_argument("--json", action="store_true", help="output as JSON")

    args = parser.parse_args()
    root = args.root or os.getcwd()

    if args.command == "status":
        cmd_status(root, args)
    elif args.command == "validate":
        cmd_validate(root, args)
    elif args.command == "start":
        cmd_start(root, args)
    elif args.command == "resume":
        cmd_resume(root, args)
    elif args.command == "readiness":
        cmd_readiness(root, args)
    elif args.command == "resolve":
        cmd_resolve(root, args)
    elif args.command == "record-evidence":
        cmd_record_evidence(root, args)
    elif args.command == "record-context":
        cmd_record_context(root, args)
    elif args.command == "complete-phase":
        cmd_complete_phase(root, args)
    elif args.command == "complete-hook":
        cmd_complete_hook(root, args)
    elif args.command == "advance":
        cmd_advance(root, args)
    elif args.command == "block":
        cmd_block(root, args)
    elif args.command == "done":
        cmd_done(root, args)
    elif args.command == "cancel-run":
        cmd_cancel_run(root, args)
    elif args.command == "governance-check":
        cmd_governance_check(root, args)
    elif args.command == "preflight":
        cmd_preflight(root, args)
    elif args.command == "ensure-run":
        cmd_ensure_run(root, args)
    elif args.command == "verify-foundations":
        cmd_verify_foundations(root, args)
    elif args.command == "before-dispatch":
        cmd_before_dispatch(root, args)
    elif args.command == "after-dispatch":
        cmd_after_dispatch(root, args)
    elif args.command == "final-commit":
        cmd_final_commit(root, args)
    elif args.command == "slice-status":
        cmd_slice_status(root, args)
    elif args.command == "slice-next":
        cmd_slice_next(root, args)
    elif args.command == "slice-block":
        cmd_slice_block(root, args)
    elif args.command == "slice-resume":
        cmd_slice_resume(root, args)
    elif args.command == "slice-cancel":
        cmd_slice_cancel(root, args)