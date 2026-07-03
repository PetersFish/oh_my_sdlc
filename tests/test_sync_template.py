#!/usr/bin/env python3
"""Read-only drift check: verify live and canonical template are in sync."""
import hashlib
from pathlib import Path

def test_template_drift_check():
    """Verify live workflow.py matches canonical template (read-only)."""
    root = Path(__file__).parent.parent
    live = root / ".ai/workflows/scripts/workflow.py"
    tmpl = root / "skills/sdlc-project-bootstrap/templates/workflow/workflow.py"

    assert live.exists(), f"Live file not found: {live}"
    assert tmpl.exists(), f"Canonical template not found: {tmpl}\nRun: python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root ."

    live_hash = hashlib.sha256(live.read_bytes()).hexdigest()
    tmpl_hash = hashlib.sha256(tmpl.read_bytes()).hexdigest()

    assert live_hash == tmpl_hash, (
        f"Template drift detected. Live: {live_hash[:12]}, Template: {tmpl_hash[:12]}\n"
        f"Run: python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root ."
    )

if __name__ == "__main__":
    test_template_drift_check()
    print("PASS: live and canonical template are in sync")
