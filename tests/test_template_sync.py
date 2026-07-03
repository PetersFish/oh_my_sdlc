#!/usr/bin/env python3
"""Test that template workflow.py is synced with live workflow.py."""
import hashlib
from pathlib import Path

def test_template_workflow_synced():
    """Verify canonical template matches live workflow.py."""
    root = Path(__file__).parent.parent
    live = root / ".ai/workflows/scripts/workflow.py"
    tmpl = root / "skills/sdlc-project-bootstrap/templates/workflow/workflow.py"
    
    assert live.exists(), f"Live file not found: {live}"
    assert tmpl.exists(), f"Template file not found: {tmpl}"
    
    live_hash = hashlib.sha256(live.read_bytes()).hexdigest()
    tmpl_hash = hashlib.sha256(tmpl.read_bytes()).hexdigest()
    
    assert live_hash == tmpl_hash, (
        f"Template workflow.py is stale. "
        f"Live: {live_hash[:12]}, Template: {tmpl_hash[:12]}. "
        f"Run sync_templates.py to fix."
    )

if __name__ == "__main__":
    test_template_workflow_synced()
    print("PASS: template workflow.py is synced")
