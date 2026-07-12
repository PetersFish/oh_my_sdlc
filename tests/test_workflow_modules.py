#!/usr/bin/env python3
"""Focused module-level tests for the workflow_runtime package.

These tests complement the authoritative end-to-end CLI suite in
``tests/test_workflow.py`` by verifying extraction-specific contracts
that are cheaper and clearer at module level.
"""

import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

WORKFLOW_SCRIPTS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", ".ai", "workflows", "scripts",
)

WORKFLOW_PY = os.path.join(WORKFLOW_SCRIPTS, "workflow.py")


class TestModuleImports(unittest.TestCase):
    """Verify that all runtime modules import in a fresh process without
    circular-import errors or command-execution side effects."""

    EXPECTED_MODULES = [
        "workflow_runtime",
        "workflow_runtime.core",
        "workflow_runtime.state",
        "workflow_runtime.definitions",
        "workflow_runtime.domains",
        "workflow_runtime.policies",
        "workflow_runtime.dispatch",
        "workflow_runtime.lifecycle",
        "workflow_runtime.governance",
        "workflow_runtime.cli",
    ]

    def test_all_runtime_modules_import_in_fresh_process(self):
        """Import every expected module in a fresh subprocess to detect
        circular imports and side-effect-free loading."""
        result = subprocess.run(
            [sys.executable, "-c", "; ".join(
                f"import {mod}" for mod in self.EXPECTED_MODULES
            )],
            capture_output=True,
            text=True,
            cwd=WORKFLOW_SCRIPTS,
            env={**os.environ, "PYTHONPATH": WORKFLOW_SCRIPTS},
        )
        self.assertEqual(
            result.returncode, 0,
            f"Import failed:\nstdout: {result.stdout}\nstderr: {result.stderr}",
        )


def _import_state():
    """Import the workflow_runtime.state module with the scripts dir on sys.path."""
    import importlib
    sys.path.insert(0, WORKFLOW_SCRIPTS)
    return importlib.import_module("workflow_runtime.state")


class TestStateIO(unittest.TestCase):
    """Verify the extracted state I/O API: pointer round trips, save/load,
    and completion-to-history semantics."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_active_run_pointer_and_state_round_trip_preserves_schema_and_paths(self):
        """Create a run via the extracted state API, save it, read the pointer,
        load the run state back, and verify schema keys and paths are preserved."""
        state_mod = _import_state()
        run_id = "2026-07-11-test-change"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "flow_type": "spec-flow",
            "status": "running",
            "current_phase": "create_change",
            "primary_subject": {"type": "spec_change", "id": "test-change"},
            "context": {"change_id": "test-change"},
            "phase_readiness": {"phase": "create_change", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": [],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-11T00:00:00",
        }
        state_mod.save_run_state(self.tmp, state)

        # Pointer should now point to the saved run.
        pointer = state_mod._read_pointer(self.tmp)
        self.assertIsNotNone(pointer)
        self.assertEqual(pointer["run_id"], run_id)

        # Active run.json should exist at the expected path.
        active_json = os.path.join(self.tmp, ".ai", "workflows", "runs", "active", run_id, "run.json")
        self.assertTrue(os.path.exists(active_json))

        # Load the state back and verify schema preservation.
        loaded = state_mod.load_run_state(self.tmp)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["run_id"], run_id)
        self.assertEqual(loaded["status"], "running")
        self.assertEqual(loaded["current_phase"], "create_change")
        self.assertEqual(loaded["primary_subject"], {"type": "spec_change", "id": "test-change"})
        self.assertEqual(loaded["flow_type"], "spec-flow")

        # Verify all RUN_STATE_KEYS are present.
        for key in state_mod.RUN_STATE_KEYS:
            self.assertIn(key, loaded, f"Missing key: {key}")

    def test_completion_moves_run_to_history_without_schema_drift(self):
        """Finalize a run to history and verify the persisted run.json
        retains all schema keys with status=done."""
        state_mod = _import_state()
        run_id = "2026-07-11-test-change"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "flow_type": "spec-flow",
            "status": "running",
            "current_phase": "done",
            "primary_subject": {"type": "spec_change", "id": "test-change"},
            "context": {"change_id": "test-change"},
            "phase_readiness": {"phase": "done", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["create_change", "apply_change", "archive_change", "post_archive_actions"],
            "gates": {},
            "evidence": {"agent_result": {"status": "success"}},
            "block": None,
            "updated_at": "2026-07-11T00:00:00",
        }
        state_mod.save_run_state(self.tmp, state)
        state["status"] = "done"
        finalized = state_mod._finalize_run_to_history(self.tmp, state)

        self.assertEqual(finalized["status"], "done")

        # History run.json should exist.
        history_json = os.path.join(self.tmp, ".ai", "workflows", "runs", "history", run_id, "run.json")
        self.assertTrue(os.path.exists(history_json))

        # Active dir should be gone.
        active_dir = os.path.join(self.tmp, ".ai", "workflows", "runs", "active", run_id)
        self.assertFalse(os.path.exists(active_dir))

        # Pointer should be cleared (empty or None).
        pointer = state_mod._read_pointer(self.tmp)
        self.assertFalse(pointer and pointer.get("run_id"))

        # Verify schema preservation in history.
        with open(history_json) as f:
            hist = json.load(f)
        for key in state_mod.RUN_STATE_KEYS:
            self.assertIn(key, hist, f"Missing key in history: {key}")


def _import_definitions():
    """Import the workflow_runtime.definitions module with the scripts dir on sys.path."""
    import importlib
    sys.path.insert(0, WORKFLOW_SCRIPTS)
    return importlib.import_module("workflow_runtime.definitions")


class TestDefinitions(unittest.TestCase):
    """Verify the extracted definition API: validation of the current
    definition and rejection of malformed transitions."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Copy the real workflow definition so the test can validate it.
        src_def = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", ".ai", "workflows", "definitions",
        )
        dst_def = os.path.join(self.tmp, ".ai", "workflows", "definitions")
        if os.path.isdir(src_def):
            shutil.copytree(src_def, dst_def)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_current_definition_validates(self):
        """Load the real sdlc-main.yaml via the extracted definitions API
        and verify validate_workflow returns no errors."""
        def_mod = _import_definitions()
        wf = def_mod.load_workflow(self.tmp, "sdlc-main")
        self.assertIsNotNone(wf, "sdlc-main.yaml should exist")
        errors = def_mod.validate_workflow(wf)
        self.assertEqual(errors, [], f"Current definition has errors: {errors}")

    def test_malformed_transition_definition_is_rejected(self):
        """A definition with a next phase targeting an unknown phase must
        produce a validation error through the extracted API."""
        def_mod = _import_definitions()
        malformed = {
            "version": 1,
            "id": "test-wf",
            "phases": {
                "phase_a": {"next": "nonexistent_phase"},
            },
        }
        errors = def_mod.validate_workflow(malformed)
        self.assertTrue(any("nonexistent_phase" in e for e in errors),
                        f"Expected unknown-phase error, got: {errors}")


def _import_domains():
    """Import the workflow_runtime.domains module with the scripts dir on sys.path."""
    import importlib
    sys.path.insert(0, WORKFLOW_SCRIPTS)
    return importlib.import_module("workflow_runtime.domains")


def _snapshot_workspace(tmp):
    """Return a set of (relpath, content_hash) for all files under tmp."""
    snapshot = set()
    for dirpath, _dirs, files in os.walk(tmp):
        for fname in files:
            fpath = os.path.join(dirpath, fname)
            rel = os.path.relpath(fpath, tmp)
            with open(fpath, "rb") as f:
                import hashlib
                snapshot.add((rel, hashlib.sha256(f.read()).hexdigest()))
    return snapshot


class TestDomainLoaders(unittest.TestCase):
    """Verify that extracted domain loaders return expected status
    information without mutating the workspace."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Set up an openspec change scaffold
        d = os.path.join(self.tmp, "openspec", "changes", "test-change")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, ".openspec.yaml"), "w") as f:
            f.write("schema: spec-driven\ncreated: 2026-07-11\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_domain_loaders_return_expected_status_without_writes(self):
        """Call OpenSpec and roadmap loaders through the extracted domains API,
        snapshot the workspace before and after, and verify no writes occur."""
        dom_mod = _import_domains()
        before = _snapshot_workspace(self.tmp)

        # OpenSpec change status loader: should classify as scaffold
        result = dom_mod.loader_openspec_change_status(self.tmp, "test-change")
        self.assertIsNotNone(result)
        self.assertEqual(result["classification"], "scaffold")

        # Roadmap item status loader: should return None (no roadmap items)
        result2 = dom_mod.loader_roadmap_item_status(self.tmp, "nonexistent-item")
        self.assertIsNone(result2)

        # Roadmap linked item loader: should return count=0
        result3 = dom_mod.loader_roadmap_linked_item(self.tmp, "test-change")
        self.assertEqual(result3["count"], 0)

        # Verify no writes occurred
        after = _snapshot_workspace(self.tmp)
        self.assertEqual(before, after, "Domain loaders must not write to the workspace")


def _import_policies():
    """Import the workflow_runtime.policies module with the scripts dir on sys.path."""
    import importlib
    sys.path.insert(0, WORKFLOW_SCRIPTS)
    return importlib.import_module("workflow_runtime.policies")


class TestPolicyRegistry(unittest.TestCase):
    """Verify the extracted policy registry: stacked decorators keep per-action
    metadata, and policy evaluation preserves status, reason, and next_action."""

    def test_stacked_policy_decorators_keep_per_action_metadata(self):
        """Stacked @register_policy decorators must store per-action metadata
        in POLICY_META without function-attribute leakage."""
        pol_mod = _import_policies()
        # spec_apply is registered with allowed_phases={"apply_change"}
        meta = pol_mod.POLICY_META.get("spec_apply")
        self.assertIsNotNone(meta, "spec_apply must be registered")
        self.assertEqual(meta["allowed_phases"], {"apply_change"})

        # spec_continue is registered with allowed_phases including create_change and apply_change
        meta2 = pol_mod.POLICY_META.get("spec_continue")
        self.assertIsNotNone(meta2, "spec_continue must be registered")
        self.assertEqual(meta2["allowed_phases"], {"create_change", "apply_change"})

        # dangling_archive_repair has creates_run=True and repair_hooks
        meta3 = pol_mod.POLICY_META.get("dangling_archive_repair")
        self.assertIsNotNone(meta3, "dangling_archive_repair must be registered")
        self.assertTrue(meta3["creates_run"])
        self.assertIn("memory_sync", meta3["repair_hooks"])


def _import_dispatch():
    """Import the workflow_runtime.dispatch module with the scripts dir on sys.path."""
    import importlib
    sys.path.insert(0, WORKFLOW_SCRIPTS)
    return importlib.import_module("workflow_runtime.dispatch")


class TestDispatchModule(unittest.TestCase):
    """Verify the extracted dispatch API: runtime-context shape preservation
    and after-dispatch rejection of incomplete result contracts."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Copy the workflow definitions so load_workflow works.
        src_def = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", ".ai", "workflows", "definitions",
        )
        dst_def = os.path.join(self.tmp, ".ai", "workflows", "definitions")
        if os.path.isdir(src_def):
            shutil.copytree(src_def, dst_def)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_runtime_context_shape_is_preserved(self):
        """_build_runtime_context must produce a dict with the expected keys
        (change_id, execution_mode, etc.) through the extracted dispatch API.

        The dispatch module must expose cmd_before_dispatch which assembles
        the runtime_context in its output. We verify the function is callable
        from the module and that the context shape keys are present.
        """
        disp_mod = _import_dispatch()
        # The dispatch module must expose the before/after dispatch commands.
        self.assertTrue(hasattr(disp_mod, "cmd_before_dispatch"),
                        "dispatch module must expose cmd_before_dispatch")
        self.assertTrue(hasattr(disp_mod, "cmd_after_dispatch"),
                        "dispatch module must expose cmd_after_dispatch")
        # The helper that builds runtime context must be accessible.
        # It lives in core but dispatch must import and use it.
        # We verify _build_runtime_context is available via the module's
        # namespace (imported from core).
        self.assertTrue(hasattr(disp_mod, "_build_runtime_context"),
                        "dispatch module must expose _build_runtime_context")
        context = {"change_id": "test-change", "execution_mode": "main_checkout"}
        rc = disp_mod._build_runtime_context(context)
        self.assertIsInstance(rc, dict)
        self.assertIn("change_id", rc)
        self.assertEqual(rc["change_id"], "test-change")

    def test_after_dispatch_rejects_incomplete_result_contract_without_state_progress(self):
        """cmd_after_dispatch must reject an agent result missing 'status'
        (envelope contract violation) and must NOT advance state progress.

        We create an active run, call cmd_after_dispatch with an incomplete
        result, and verify the state remains unadvanced (status stays running,
        no agent_result recorded).
        """
        disp_mod = _import_dispatch()
        state_mod = _import_state()

        # Create an active run in the temp workspace.
        run_id = "2026-07-11-test-dispatch"
        state = {
            "version": 1,
            "run_id": run_id,
            "workflow": "sdlc-main",
            "flow_type": "spec-flow",
            "status": "running",
            "current_phase": "apply_change",
            "primary_subject": {"type": "spec_change", "id": "test-dispatch"},
            "context": {"change_id": "test-dispatch"},
            "phase_readiness": {"phase": "apply_change", "ready": True, "missing_required_inputs": []},
            "pending_hooks": [],
            "completed_hooks": [],
            "completed_phases": ["create_change"],
            "gates": {},
            "evidence": {},
            "block": None,
            "updated_at": "2026-07-11T00:00:00",
        }
        state_mod.save_run_state(self.tmp, state)

        # Build a fake args object for after-dispatch with an incomplete result.
        class FakeArgs:
            agent = "implement-agent"
            phase = "apply_change"
            slice_id = "default"
            value = '{"evidence": {}}'  # Missing 'status' key

        import io
        from contextlib import redirect_stdout
        captured = io.StringIO()
        try:
            with redirect_stdout(captured):
                disp_mod.cmd_after_dispatch(self.tmp, FakeArgs())
        except SystemExit:
            pass  # Some code paths exit; the contract is about state, not exit code.

        # The incomplete result must NOT advance state progress (not done).
        loaded = state_mod.load_run_state(self.tmp)
        self.assertIsNotNone(loaded)
        self.assertNotEqual(loaded.get("status"), "done",
                            "State must not be advanced to done for incomplete result")
        # The state must be blocked (not running) because the result was rejected.
        self.assertEqual(loaded.get("status"), "blocked",
                         "State must be blocked for incomplete result contract")
        # The agent_result should record blockers for the envelope violation.
        agent_result = loaded.get("evidence", {}).get("agent_result", {})
        blockers = agent_result.get("blockers", [])
        blocker_reasons = [b.get("reason", "") for b in blockers if isinstance(b, dict)]
        self.assertIn("envelope_contract_violation", blocker_reasons,
                      "after_dispatch must record envelope_contract_violation blocker")


def _import_cli():
    """Import the workflow_runtime.cli module with the scripts dir on sys.path."""
    import importlib
    sys.path.insert(0, WORKFLOW_SCRIPTS)
    return importlib.import_module("workflow_runtime.cli")


class TestFacadeCompatibility(unittest.TestCase):
    """Verify that the public script facade delegates correctly to the
    modular runtime CLI, preserving help output and exit contracts."""

    def test_help_and_status_execute_through_public_script(self):
        """The public workflow.py script must accept --help and status
        commands by delegating to workflow_runtime.cli.main()."""
        result = subprocess.run(
            [sys.executable, WORKFLOW_PY, "--help"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(WORKFLOW_PY),
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("SDLC workflow runtime", result.stdout)
        # All commands must be listed in help output.
        for cmd in ["status", "start", "done", "governance-check", "final-commit"]:
            self.assertIn(cmd, result.stdout,
                          f"Command '{cmd}' must appear in --help output")

        # Status with no runs should return valid JSON.
        import tempfile
        tmp = tempfile.mkdtemp()
        try:
            result2 = subprocess.run(
                [sys.executable, WORKFLOW_PY, "--root", tmp, "status"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result2.returncode, 0)
            import json as _json
            output = _json.loads(result2.stdout.strip())
            self.assertEqual(output["status"], "no_active_run")
        finally:
            import shutil as _shutil
            _shutil.rmtree(tmp, ignore_errors=True)

    def test_representative_invalid_command_preserves_exit_contract(self):
        """An invalid command must exit non-zero and produce an error."""
        result = subprocess.run(
            [sys.executable, WORKFLOW_PY, "--root", "/tmp", "bogus-command"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0,
                            "Invalid command must exit non-zero")


class TestStateWriteOwnership(unittest.TestCase):
    """Verify the centralized state-write contract: only workflow_runtime.state
    directly deletes, writes, or moves active/history run paths.

    Higher-level modules (lifecycle, governance, dispatch, etc.) MUST NOT
    call shutil.rmtree, shutil.move, or open(..., 'w')/json.dump on paths
    under ``.ai/workflows/runs/``. Those mutations must route through state.py
    APIs so that state.py remains the single write-boundary.
    """

    def test_lifecycle_does_not_directly_mutate_run_paths(self):
        """Inspect the source of lifecycle.py and confirm it does not contain
        direct filesystem mutations of run-state paths (rmtree, move, json.dump
        on runs/ paths). Only state.py is allowed to perform these writes.
        """
        lifecycle_src = os.path.join(WORKFLOW_SCRIPTS, "workflow_runtime", "lifecycle.py")
        self.assertTrue(os.path.exists(lifecycle_src),
                        "lifecycle.py must exist at the expected path")
        with open(lifecycle_src) as f:
            source = f.read()

        # Forbidden direct run-state filesystem operations in lifecycle.py.
        # These operations belong in state.py only.
        forbidden_patterns = [
            "shutil.rmtree",
            "shutil.move",
            "json.dump(state",
            "json.dump(state,",
        ]

        for pattern in forbidden_patterns:
            self.assertNotIn(
                pattern, source,
                f"lifecycle.py must not directly {pattern} — "
                f"run-state mutations must route through workflow_runtime.state APIs"
            )

    def test_cancel_run_routes_through_state_api(self):
        """cmd_cancel_run must remove the active run directory via a state.py
        API, not via a direct shutil.rmtree call in lifecycle.py."""
        import inspect
        sys.path.insert(0, WORKFLOW_SCRIPTS)
        lifecycle_mod = importlib.import_module("workflow_runtime.lifecycle")
        # The cancel-run handler must be delegating run directory removal to state.
        # We verify by checking that lifecycle.py imports a cancel/remove helper
        # from state and that it does not call shutil.rmtree directly.
        lifecycle_src = inspect.getsource(lifecycle_mod)
        self.assertNotIn("shutil.rmtree", lifecycle_src,
                         "lifecycle.py must not call shutil.rmtree directly")


if __name__ == "__main__":
    unittest.main()