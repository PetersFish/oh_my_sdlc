#!/usr/bin/env python3
"""Read-only drift check: verify all distributed workflow.py copies match live."""
import hashlib
from pathlib import Path

def test_all_distributed_drift_check():
    """Verify live workflow.py matches canonical and all distributed copies (read-only)."""
    root = Path(__file__).parent.parent
    live = root / ".ai/workflows/scripts/workflow.py"

    assert live.exists(), f"Live file not found: {live}"

    # Canonical template
    canonical = root / "skills/sdlc-project-bootstrap/templates/workflow/workflow.py"

    # Distributed copies
    distributed = [
        root / ".opencode/skills/sdlc-project-bootstrap/templates/workflow/workflow.py",
        root / ".claude/skills/sdlc-project-bootstrap/templates/workflow/workflow.py",
        root / ".cursor/skills/sdlc-project-bootstrap/templates/workflow/workflow.py",
    ]

    live_hash = hashlib.sha256(live.read_bytes()).hexdigest()

    # Check canonical
    assert canonical.exists(), (
        f"Canonical template not found: {canonical}\n"
        f"Run: python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root ."
    )
    assert hashlib.sha256(canonical.read_bytes()).hexdigest() == live_hash, (
        f"Canonical template drift detected.\n"
        f"Run: python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root ."
    )

    # Check distributed copies
    for dist in distributed:
        assert dist.exists(), (
            f"Distributed copy not found: {dist}\n"
            f"Run: python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --distribute"
        )
        assert hashlib.sha256(dist.read_bytes()).hexdigest() == live_hash, (
            f"Distributed copy drift detected: {dist}\n"
            f"Run: python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --distribute"
        )

if __name__ == "__main__":
    test_all_distributed_drift_check()
    print("PASS: all distributed workflow.py copies are in sync")
