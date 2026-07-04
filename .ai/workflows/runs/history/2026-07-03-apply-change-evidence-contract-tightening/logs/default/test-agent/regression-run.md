# Test-Agent Raw Log: Full Regression Run

## Command
python3 -m pytest tests/ -v

## Result
1007 passed, 50 subtests passed in 39.14s

## Sync Checks
- python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check → OK
- python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check-distributed → OK

## Focused Tests
- python3 -m pytest tests/test_sync_all_distributed.py -v → 1 passed
- python3 -m pytest tests/test_workflow.py -k "TestApplyChangeHandoffHistory or TestApplyChangeVerificationBasis or after_dispatch" -v → 32 passed
- python3 -m pytest tests/test_workflow.py tests/test_wrapper_contracts.py -v → 437 passed, 28 subtests passed
