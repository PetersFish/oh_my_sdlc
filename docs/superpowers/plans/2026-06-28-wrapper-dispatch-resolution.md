# Wrapper Dispatch Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace execute-in-Python wrapper adapters with resolution-only wrapper dispatch specs, then have `dev-orchestrator` dynamically invoke resolved skills and validate provider-specific results for `spec` and `memory`.

**Architecture:** Python becomes the deterministic resolution layer: it reads provider registry + distributed project config and returns `dispatch + verifier + contract`. `dev-orchestrator` becomes the runtime execution layer: it resolves a dispatch spec, invokes the resolved skill, runs a provider-specific verifier, normalizes the verified result, and only then hands a structured envelope to `workflow.py after-dispatch`.

**Tech Stack:** Python, YAML, pytest, SDLC workflow runtime, OpenCode skill/task/bash tools

---

### Task 1: Rename wrapper execution module into resolution-only module

**Files:**
- Create: `skills/_lib/wrapper_resolution.py`
- Modify: `skills/_lib/provider_registry_loader.py`
- Modify: `tests/test_wrapper_contracts.py`
- Modify: `.opencode/skills/_lib/wrapper_resolution.py`
- Modify: `.claude/skills/_lib/wrapper_resolution.py`
- Modify: `.cursor/skills/_lib/wrapper_resolution.py`
- Delete: `skills/_lib/wrapper_adapters.py`
- Delete: `.opencode/skills/_lib/wrapper_adapters.py`
- Delete: `.claude/skills/_lib/wrapper_adapters.py`
- Delete: `.cursor/skills/_lib/wrapper_adapters.py`
- Test: `tests/test_wrapper_contracts.py`

- [ ] **Step 1: Write the failing test**

```python
class TestWrapperDispatchResolution(unittest.TestCase):
    def test_resolve_wrapper_dispatch_replaces_old_execute_adapter_shape(self):
        resolved = resolve_wrapper_dispatch(
            module="spec",
            capability="create",
            workflow_run_id="run-1",
            phase="create_change",
            action="create",
            flow_type="spec-flow",
            repo_root=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
            extra_inputs={"change_id": "demo-change"},
        )
        self.assertEqual(resolved.module, "spec")
        self.assertEqual(resolved.capability, "create")
        self.assertEqual(resolved.provider, "openspec")
        self.assertEqual(resolved.dispatch["kind"], "skill")
        self.assertEqual(resolved.dispatch["target"], "openspec-propose")
        self.assertEqual(resolved.verifier["target"], "openspec.create")
        self.assertEqual(resolved.result_contract, "spec_change")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_wrapper_contracts.py -q -k "resolve_wrapper_dispatch_replaces_old_execute_adapter_shape"`
Expected: FAIL with import or symbol error because `wrapper_resolution.py` and `resolve_wrapper_dispatch` do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# skills/_lib/wrapper_resolution.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .provider_registry_loader import resolve_provider_dispatch_spec
from .wrapper_contracts import WRAPPER_REGISTRY, make_blocker


@dataclass
class WrapperDispatchResolution:
    module: str
    capability: str
    provider: str
    dispatch: Dict[str, Any]
    verifier: Dict[str, Any]
    result_contract: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    blockers: List[Dict[str, str]] = field(default_factory=list)


def resolve_wrapper_dispatch(...):
    # validate wrapper contract + resolve provider/config + return spec only
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_wrapper_contracts.py -q -k "resolve_wrapper_dispatch_replaces_old_execute_adapter_shape"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/wrapper_resolution.py skills/_lib/provider_registry_loader.py tests/test_wrapper_contracts.py .opencode/skills/_lib/wrapper_resolution.py .claude/skills/_lib/wrapper_resolution.py .cursor/skills/_lib/wrapper_resolution.py
git commit -m "refactor: rename wrapper adapters to resolution"
```

### Task 2: Upgrade provider registry from backend strings to dispatch/verifier/contract specs

**Files:**
- Modify: `skills/_lib/provider_registry.yaml`
- Modify: `skills/_lib/provider_registry_loader.py`
- Modify: `tests/test_wrapper_contracts.py`
- Modify: `.opencode/skills/_lib/provider_registry.yaml`
- Modify: `.claude/skills/_lib/provider_registry.yaml`
- Modify: `.cursor/skills/_lib/provider_registry.yaml`
- Test: `tests/test_wrapper_contracts.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_spec_create_resolves_dispatch_verifier_and_contract(self):
    spec = resolve_provider_dispatch_spec("spec", "create", repo_root=self.repo_root)
    self.assertEqual(spec.provider, "openspec")
    self.assertEqual(spec.dispatch["kind"], "skill")
    self.assertEqual(spec.dispatch["target"], "openspec-propose")
    self.assertEqual(spec.verifier["target"], "openspec.create")
    self.assertEqual(spec.result_contract, "spec_change")


def test_memory_repository_sync_resolves_dispatch_verifier_and_contract(self):
    spec = resolve_provider_dispatch_spec("memory", "repository_sync", repo_root=self.repo_root)
    self.assertEqual(spec.provider, "local")
    self.assertEqual(spec.dispatch["target"], "sdlc-repository-memory-sync")
    self.assertEqual(spec.verifier["target"], "local.repository_sync")
    self.assertEqual(spec.result_contract, "memory_sync")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_wrapper_contracts.py -q -k "resolves_dispatch_verifier_and_contract"`
Expected: FAIL because registry/loader still expose old backend-only shape.

- [ ] **Step 3: Write minimal implementation**

```yaml
# skills/_lib/provider_registry.yaml
version: 2
modules:
  spec:
    default_provider: openspec
    contract: spec_change
    providers:
      openspec:
        capabilities:
          create: true
        dispatch:
          create:
            kind: skill
            target: openspec-propose
        verifier:
          create:
            kind: provider
            target: openspec.create
```

```python
@dataclass
class ProviderDispatchSpec:
    module: str
    provider: str
    capability: str
    dispatch: Dict[str, Any]
    verifier: Dict[str, Any]
    result_contract: str
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_wrapper_contracts.py -q -k "resolves_dispatch_verifier_and_contract"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/provider_registry.yaml skills/_lib/provider_registry_loader.py tests/test_wrapper_contracts.py .opencode/skills/_lib/provider_registry.yaml .claude/skills/_lib/provider_registry.yaml .cursor/skills/_lib/provider_registry.yaml
git commit -m "feat: add wrapper dispatch registry specs"
```

### Task 3: Preserve fail-closed provider validation in the new resolution path

**Files:**
- Modify: `skills/_lib/wrapper_resolution.py`
- Modify: `skills/_lib/provider_registry_loader.py`
- Modify: `tests/test_wrapper_contracts.py`
- Test: `tests/test_wrapper_contracts.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_provider_config_mismatch_blocks_resolution(self):
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / ".opencode").mkdir(); (root / ".cursor").mkdir(); (root / ".claude").mkdir()
        (root / ".opencode" / "sdlc-providers.yaml").write_text("version: 1
spec:
  provider: openspec
")
        (root / ".cursor" / "sdlc-providers.yaml").write_text("version: 1
spec:
  provider: github/spec-kit
")
        with self.assertRaises(WrapperResolutionBlocked):
            resolve_wrapper_dispatch(..., module="spec", capability="create", repo_root=str(root))


def test_unsupported_capability_blocks_resolution(self):
    with self.assertRaises(WrapperResolutionBlocked):
        resolve_wrapper_dispatch(..., module="memory", capability="archive", repo_root=self.repo_root)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_wrapper_contracts.py -q -k "blocks_resolution"`
Expected: FAIL because the new resolution path does not yet raise structured blockers consistently.

- [ ] **Step 3: Write minimal implementation**

```python
class WrapperResolutionBlocked(Exception):
    def __init__(self, blockers: List[Dict[str, str]]):
        self.blockers = blockers
        super().__init__(blockers[0]["reason"] if blockers else "wrapper_resolution_blocked")


def resolve_wrapper_dispatch(...):
    blockers = resolve_wrapper_provider_blockers(module, capability, repo_root=repo_root)
    if blockers:
        raise WrapperResolutionBlocked(blockers)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_wrapper_contracts.py -q -k "blocks_resolution"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/wrapper_resolution.py skills/_lib/provider_registry_loader.py tests/test_wrapper_contracts.py
git commit -m "test: preserve fail-closed wrapper resolution"
```

### Task 4: Add provider-specific verifier registry for `openspec` and `local`

**Files:**
- Create: `skills/_lib/provider_verifiers.py`
- Modify: `tests/test_wrapper_contracts.py`
- Test: `tests/test_wrapper_contracts.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_openspec_create_verifier_succeeds_when_change_artifacts_exist(self):
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        change = root / "openspec" / "changes" / "demo-change"
        change.mkdir(parents=True)
        for name in ["proposal.md", "design.md", "tasks.md"]:
            (change / name).write_text("ok")
        result = verify_provider_result(
            verifier_target="openspec.create",
            module="spec",
            capability="create",
            provider="openspec",
            repo_root=str(root),
            inputs={"change_id": "demo-change"},
        )
        self.assertEqual(result["status"], "success")


def test_openspec_create_verifier_blocks_when_required_artifact_missing(self):
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        change = root / "openspec" / "changes" / "demo-change"
        change.mkdir(parents=True)
        (change / "proposal.md").write_text("ok")
        result = verify_provider_result(...)
        self.assertEqual(result["status"], "blocked")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_wrapper_contracts.py -q -k "openspec_create_verifier"`
Expected: FAIL because `provider_verifiers.py` and `verify_provider_result` do not exist.

- [ ] **Step 3: Write minimal implementation**

```python
# skills/_lib/provider_verifiers.py
from pathlib import Path


def _verify_openspec_create(repo_root: str, inputs: dict) -> dict:
    change_id = inputs["change_id"]
    change_dir = Path(repo_root) / "openspec" / "changes" / change_id
    required = [change_dir / "proposal.md", change_dir / "design.md", change_dir / "tasks.md"]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        return {"status": "blocked", "blockers": [{"reason": "missing_required_artifacts", "message": ", ".join(missing)}]}
    return {"status": "success", "evidence": {"change_id": change_id, "artifact_paths": [str(p) for p in required]}}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_wrapper_contracts.py -q -k "openspec_create_verifier"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/provider_verifiers.py tests/test_wrapper_contracts.py
git commit -m "feat: add provider result verifiers"
```

### Task 5: Add contract normalizers for `spec_change` and `memory_sync`

**Files:**
- Create: `skills/_lib/result_contracts.py`
- Modify: `tests/test_wrapper_contracts.py`
- Test: `tests/test_wrapper_contracts.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_spec_change_normalizer_emits_stable_envelope_fields(self):
    envelope = normalize_contract_result(
        contract="spec_change",
        verification_result={
            "status": "success",
            "evidence": {"change_id": "demo-change", "artifact_paths": ["a", "b"]},
            "artifacts": {"handoff_path": "openspec/changes/demo-change/tasks.md"},
        },
        phase="create_change",
        flow_type="spec-flow",
        slice_id=None,
    )
    self.assertEqual(envelope.status, "success")
    self.assertEqual(envelope.evidence["change_id"], "demo-change")
    self.assertIn("handoff_path", envelope.artifacts)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_wrapper_contracts.py -q -k "normalizer_emits_stable_envelope_fields"`
Expected: FAIL because `normalize_contract_result` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
# skills/_lib/result_contracts.py
from .wrapper_contracts import make_evidence_envelope


def normalize_contract_result(contract: str, verification_result: dict, phase: str, flow_type: str, slice_id: str | None):
    return make_evidence_envelope(
        agent=f"wrapper:{contract}",
        status=verification_result.get("status", "blocked"),
        phase=phase,
        slice_id=slice_id,
        flow_type=flow_type,
        evidence=verification_result.get("evidence", {}),
        artifacts=verification_result.get("artifacts", {}),
        blockers=verification_result.get("blockers", []),
        recommended_next_action=verification_result.get("recommended_next_action", "continue"),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_wrapper_contracts.py -q -k "normalizer_emits_stable_envelope_fields"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/result_contracts.py tests/test_wrapper_contracts.py
git commit -m "feat: normalize wrapper contract results"
```

### Task 6: Teach `dev-orchestrator` to resolve, dispatch, verify, and normalize `kind=skill`

**Files:**
- Modify: `AGENTS.md` or the dev-orchestrator instruction source in the runtime prompt path that defines wrapper execution behavior
- Modify: `tests/test_wrapper_contracts.py`
- Modify: `tests/test_workflow.py`
- Test: `tests/test_wrapper_contracts.py`
- Test: `tests/test_workflow.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_dev_orchestrator_resolves_skill_dispatch_instead_of_hardcoding_backend_name(self):
    body = self._read_dev_orchestrator_prompt()
    self.assertIn("resolve_wrapper_dispatch", body)
    self.assertIn("dispatch.kind", body)
    self.assertIn("provider-specific verifier", body)


def test_after_dispatch_receives_only_normalized_envelopes(self):
    result = {
        "agent": "wrapper:spec",
        "status": "success",
        "phase": "create_change",
        "flow_type": "spec-flow",
        "evidence": {"change_id": "demo-change"},
        "artifacts": {"handoff_path": "openspec/changes/demo-change/tasks.md"},
        "blockers": [],
        "recommended_next_action": "complete_phase",
    }
    out = self.run_workflow("after-dispatch", "--agent", "plan-agent", "--value", json.dumps(result))
    self.assertEqual(out["recommended_next_action"], "complete_phase")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_wrapper_contracts.py tests/test_workflow.py -q -k "resolve_wrapper_dispatch or normalized_envelopes"`
Expected: FAIL because dev-orchestrator guidance still assumes old wrapper shape.

- [ ] **Step 3: Write minimal implementation**

```text
For wrapper-backed modules, dev-orchestrator must:
1. call resolve_wrapper_dispatch(...)
2. execute dispatch.kind=skill by invoking the resolved skill target
3. run the resolved provider verifier
4. normalize through the resolved contract
5. send only the normalized envelope to workflow.py after-dispatch
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_wrapper_contracts.py tests/test_workflow.py -q -k "resolve_wrapper_dispatch or normalized_envelopes"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_wrapper_contracts.py tests/test_workflow.py AGENTS.md
git commit -m "feat: route wrapper backends through resolution flow"
```

### Task 7: Sync governed copies and run regression verification

**Files:**
- Modify: `skills/sdlc-project-bootstrap/templates/workflow/workflow.py` (only if workflow runtime changed)
- Modify: project-level distributed skill copies under `.opencode/`, `.claude/`, `.cursor/`
- Test: `tests/test_wrapper_contracts.py`
- Test: `tests/test_workflow.py`

- [ ] **Step 1: Write the failing verification command expectation**

```text
A successful implementation must leave all governed copies in sync and all wrapper/workflow behavior tests green.
```

- [ ] **Step 2: Run verification to observe current failure or drift**

Run: `python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check && python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check-distributed`
Expected: If files were changed but not copied yet, one of these commands fails.

- [ ] **Step 3: Write minimal implementation**

```bash
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root .
python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --distribute
```

- [ ] **Step 4: Run tests to verify everything passes**

Run: `python3 -m pytest tests/test_wrapper_contracts.py tests/test_workflow.py -q && python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check && python3 skills/sdlc-project-bootstrap/scripts/sync_templates.py --root . --check-distributed`
Expected: PASS, sync checks OK.

- [ ] **Step 5: Commit**

```bash
git add skills/ .opencode/ .claude/ .cursor/ tests/
git commit -m "test: verify wrapper dispatch resolution flow"
```
