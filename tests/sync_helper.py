#!/usr/bin/env python3
"""DEPRECATED: This helper has been removed.

Tests now use read-only drift checks. Use:
  python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root .
"""
import sys
print("ERROR: sync_helper.py is deprecated and has been removed.", file=sys.stderr)
print("Use: python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root .", file=sys.stderr)
sys.exit(1)
