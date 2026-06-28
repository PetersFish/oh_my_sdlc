#!/usr/bin/env python3
"""Tests for wrapper contracts and agent evidence envelope contracts."""

import json
import os
import pathlib
import sys
import tempfile
import unittest

SKILLS_LIB = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "skills", "_lib",
)
if SKILLS_LIB not in sys.path:
    sys.path.insert(0, os.path.abspath(os.path.join(SKILLS_LIB, "..")))

from _lib.wrapper_contracts import (
    EvidenceEnvelope,
    WRAPPER_REGISTRY,
    EVIDENCE_ENVELOPE_KEYS,
    REQUIRED_ENVELOPE_KEYS,
    VALID_AGENT_STATUSES,
    VALID_FLOW_TYPES,
    HANDOFF_SECTIONS,
    HANDOFF_METADATA_KEYS,
    RAW_LOG_META_KEYS,
    PHASE_AGENT_MAP,
    CANONICAL_AGENT_NAMES,
    VALID_AGENT_NAMES,
    CHANGE_PHASES,
    check_parallel_disjoint,
    validate_evidence_envelope,
    validate_handoff_structure,
    validate_raw_log_entry,
    validate_contract_inputs,
    canonical_agent_name,
    is_agent_allowed_in_phase,
    make_evidence_envelope,
    make_blocker,
    make_raw_log_entry,
    logs_optional_policy,
    get_wrapper,
    resolve_wrapper_provider_blockers,
)
from _lib.wrapper_adapters import (
    implementation_wrapper_adapter,
    spec_wrapper_adapter,
)


class TestEvidenceEnvelope(unittest.TestCase):
    """Task 1.10: specialized agents emit shared evidence envelope with required top-level fields."""

    def test_envelope_has_all_top_level_keys(self):
        envelope = make_evidence_envelope(
            agent="implement-agent",
            status="success",
            phase="apply_change",
            slice_id="slice-1",
            flow_type="spec-flow",
            evidence={"focused_tests": [{"command": "pytest -k test_x", "result": "pass"}]},
            artifacts={"handoff_path": "/tmp/handoff.md"},
            blockers=[],
            recommended_next_action="dispatch_test_agent",
        )
        d = envelope.to_dict()
        for key in EVIDENCE_ENVELOPE_KEYS:
            self.assertIn(key, d, f"Missing envelope key: {key}")

    def test_envelope_rejects_missing_required_keys(self):
        errors = validate_evidence_envelope({})
        self.assertTrue(any("missing required envelope keys" in e for e in errors))

    def test_envelope_rejects_invalid_status(self):
        errors = validate_evidence_envelope({
            "agent": "plan-agent",
            "status": "bogus",
            "phase": "create_change",
            "evidence": {},
        })
        self.assertTrue(any("invalid status" in e for e in errors))

    def test_envelope_rejects_invalid_flow_type(self):
        errors = validate_evidence_envelope({
            "agent": "plan-agent",
            "status": "success",
            "phase": "create_change",
            "flow_type": "garbage-flow",
            "evidence": {},
        })
        self.assertTrue(any("invalid flow_type" in e for e in errors))

    def test_envelope_validates_minimal_success(self):
        errors = validate_evidence_envelope({
            "agent": "plan-agent",
            "status": "success",
            "phase": "create_change",
            "evidence": {},
        })
        self.assertEqual(errors, [])

    def test_focused_tests_must_be_array_when_present(self):
        errors = validate_evidence_envelope({
            "agent": "implement-agent",
            "status": "success",
            "phase": "apply_change",
            "evidence": {"focused_tests": "not_an_array"},
        })
        self.assertTrue(any("focused_tests must be an array" in e for e in errors))

        errors = validate_evidence_envelope({
            "agent": "implement-agent",
            "status": "success",
            "phase": "apply_change",
            "evidence": {"focused_tests": [{"command": "pytest", "result": "pass"}]},
        })
        self.assertEqual(errors, [])

    def test_envelope_to_json_serializable(self):
        envelope = make_evidence_envelope(
            agent="test-agent",
            status="failed",
            phase="apply_change",
            slice_id="slice-2",
        )
        raw = envelope.to_json()
        parsed = json.loads(raw)
        self.assertEqual(parsed["agent"], "test-agent")
        self.assertEqual(parsed["status"], "failed")

    def test_envelope_validate_detects_allowed_statuses(self):
        for status in VALID_AGENT_STATUSES:
            errors = validate_evidence_envelope({
                "agent": "plan-agent",
                "status": status,
                "phase": "create_change",
                "evidence": {},
            })
            self.assertEqual(errors, [], f"Status {status!r} should be valid")


class TestHandoffArtifacts(unittest.TestCase):
    """Task 1.11: cross-agent handoff artifacts use required Markdown sections."""

    def test_handoff_structure_requires_all_sections(self):
        content = "\n".join(f"## {s}\ncontent" for s in HANDOFF_SECTIONS)
        missing = validate_handoff_structure(content)
        self.assertEqual(missing, [])

    def test_handoff_structure_detects_missing_sections(self):
        content = "## Metadata\ncontent"
        missing = validate_handoff_structure(content)
        self.assertGreater(len(missing), 0)
        self.assertNotIn("Metadata", missing)

    def test_handoff_metadata_keys_are_defined(self):
        self.assertIn("Run ID", HANDOFF_METADATA_KEYS)
        self.assertIn("Slice ID", HANDOFF_METADATA_KEYS)
        self.assertIn("Agent", HANDOFF_METADATA_KEYS)
        self.assertIn("Phase", HANDOFF_METADATA_KEYS)
        self.assertIn("Flow Type", HANDOFF_METADATA_KEYS)
        self.assertIn("Status", HANDOFF_METADATA_KEYS)
        self.assertIn("Recommended Next Agent", HANDOFF_METADATA_KEYS)


class TestRawLogs(unittest.TestCase):
    """Task 1.12: raw logs exposed through artifacts.raw_log_paths[] with metadata."""

    def test_raw_log_entry_has_required_metadata(self):
        entry = make_raw_log_entry(
            path="/tmp/logs/test.log",
            kind="pytest",
            command="pytest -k test_x",
            result="pass",
        )
        for key in RAW_LOG_META_KEYS:
            self.assertIn(key, entry, f"Missing raw log metadata key: {key}")

    def test_raw_log_validation_rejects_missing_metadata(self):
        errors = validate_raw_log_entry({"path": "/tmp/log"})
        self.assertGreater(len(errors), 0)

    def test_raw_log_validation_accepts_complete_entry(self):
        entry = make_raw_log_entry("/tmp/log", "pytest", "pytest tests/", "pass")
        errors = validate_raw_log_entry(entry)
        self.assertEqual(errors, [])

    def test_logs_optional_policy(self):
        self.assertTrue(logs_optional_policy("failed"))
        self.assertTrue(logs_optional_policy("blocked"))
        self.assertFalse(logs_optional_policy("success"))


class TestParallelDispatch(unittest.TestCase):
    """Task 1.5: dev-orchestrator rejects parallel dispatch when packages share files/modules."""

    def test_disjoint_packages_pass(self):
        packages = [
            {"slice_id": "a", "files": ["src/a.py"]},
            {"slice_id": "b", "files": ["src/b.py"]},
        ]
        blocker = check_parallel_disjoint(packages)
        self.assertIsNone(blocker)

    def test_shared_file_in_parallel_packages_triggers_blocker(self):
        packages = [
            {"slice_id": "a", "files": ["src/shared.py"]},
            {"slice_id": "b", "files": ["src/shared.py"]},
        ]
        blocker = check_parallel_disjoint(packages)
        self.assertIsNotNone(blocker)
        self.assertEqual(blocker["reason"], "shared_file_in_parallel_packages")

    def test_shared_module_in_parallel_packages_triggers_blocker(self):
        packages = [
            {"slice_id": "a", "modules": ["core"]},
            {"slice_id": "b", "modules": ["core"]},
        ]
        blocker = check_parallel_disjoint(packages)
        self.assertIsNotNone(blocker)
        self.assertEqual(blocker["reason"], "shared_module_in_parallel_packages")

    def test_empty_packages_are_safe(self):
        blocker = check_parallel_disjoint([])
        self.assertIsNone(blocker)

        packages = [
            {"slice_id": "a"},
            {"slice_id": "b"},
        ]
        blocker = check_parallel_disjoint(packages)
        self.assertIsNone(blocker)

    def test_mixed_disjoint_and_shared(self):
        packages = [
            {"slice_id": "a", "files": ["src/a.py"], "modules": ["util_a"]},
            {"slice_id": "b", "files": ["src/b.py"], "modules": ["util_a"]},
        ]
        blocker = check_parallel_disjoint(packages)
        self.assertIsNotNone(blocker)
        self.assertIn("util_a", blocker["message"])


class TestPhaseAgentMapping(unittest.TestCase):
    """Verify phase-agent mapping and canonical agent name resolution."""

    def test_plan_agent_only_in_create_change(self):
        self.assertTrue(is_agent_allowed_in_phase("plan-agent", "create_change"))
        self.assertFalse(is_agent_allowed_in_phase("plan-agent", "apply_change"))
        self.assertFalse(is_agent_allowed_in_phase("plan-agent", "archive_change"))

    def test_implement_test_review_in_apply_change(self):
        for agent in ("implement-agent", "test-agent", "review-agent"):
            self.assertTrue(
                is_agent_allowed_in_phase(agent, "apply_change"),
                f"{agent} should be allowed in apply_change",
            )
            self.assertFalse(
                is_agent_allowed_in_phase(agent, "create_change"),
                f"{agent} should NOT be allowed in create_change",
            )

    def test_finish_agent_in_archive_and_post_archive(self):
        self.assertTrue(is_agent_allowed_in_phase("finish-agent", "archive_change"))
        self.assertTrue(is_agent_allowed_in_phase("finish-agent", "post_archive_actions"))
        self.assertFalse(is_agent_allowed_in_phase("finish-agent", "apply_change"))
        self.assertFalse(is_agent_allowed_in_phase("finish-agent", "create_change"))

    def test_canonical_agent_name_accepts_dash_and_underscore(self):
        for input_name in ("plan-agent", "plan_agent",
                           "implement-agent", "implement_agent",
                           "test-agent", "test_agent",
                           "review-agent", "review_agent",
                           "finish-agent", "finish_agent"):
            canonical = canonical_agent_name(input_name)
            self.assertIsNotNone(canonical, f"Should accept {input_name!r}")
            self.assertIn("-", canonical, f"Canonical form should use dashes: {canonical!r}")

    def test_canonical_agent_name_rejects_invalid(self):
        self.assertIsNone(canonical_agent_name("garbage-agent"))
        self.assertIsNone(canonical_agent_name(""))

    def test_unknown_phase_denies_all_agents(self):
        for agent in VALID_AGENT_NAMES:
            if canonical_agent_name(agent):
                self.assertFalse(
                    is_agent_allowed_in_phase(agent, "bogus_phase"),
                    f"{agent!r} should not be allowed in bogus phase",
                )


class TestWrapperContracts(unittest.TestCase):
    """Task 3.7: wrapper contracts exist for all lifecycle modules."""

    def test_all_modules_have_wrapper_contracts(self):
        expected_modules = {
            "spec", "memory", "roadmap", "eval",
            "planning", "implementation", "testing", "review", "finish", "verification",
        }
        for module in expected_modules:
            contract = get_wrapper(module)
            self.assertIsNotNone(contract, f"Missing wrapper contract for module: {module}")

    def test_each_contract_defines_evidence_keys(self):
        for module, contract in WRAPPER_REGISTRY.items():
            self.assertIsInstance(contract.evidence_keys, list,
                                  f"{module}: evidence_keys should be a list")

    def test_each_contract_defines_failure_modes(self):
        for module, contract in WRAPPER_REGISTRY.items():
            self.assertIsInstance(contract.failure_modes, list,
                                  f"{module}: failure_modes should be a list")

    def test_each_contract_defines_remediation(self):
        for module, contract in WRAPPER_REGISTRY.items():
            self.assertIsInstance(contract.remediation, list,
                                  f"{module}: remediation should be a list")


class TestContractInputs(unittest.TestCase):
    """Verify contract input validation."""

    def test_missing_required_inputs_detected(self):
        missing = validate_contract_inputs({})
        self.assertGreater(len(missing), 0)
        for key in ("workflow_run_id", "phase", "action", "flow_type"):
            self.assertIn(key, missing)

    def test_complete_inputs_pass(self):
        inputs = {
            "workflow_run_id": "run-1",
            "phase": "apply_change",
            "action": "implement",
            "flow_type": "spec-flow",
        }
        missing = validate_contract_inputs(inputs)
        self.assertEqual(missing, [])


class TestBlockerConstruction(unittest.TestCase):
    """Test structured blocker building."""

    def test_make_blocker_has_required_fields(self):
        blocker = make_blocker(
            reason="test_failure",
            message="Focused test failed",
            recommended_action="back_to_implement",
        )
        self.assertEqual(blocker["reason"], "test_failure")
        self.assertEqual(blocker["message"], "Focused test failed")
        self.assertEqual(blocker["recommended_action"], "back_to_implement")


class TestAgentVerificationSequence(unittest.TestCase):
    """Task 1.7: test-agent reruns focused tests, checks overfit, runs broader regression/integration."""

    def test_testing_wrapper_has_verification_evidence_keys(self):
        contract = get_wrapper("testing")
        self.assertIsNotNone(contract)
        self.assertIn("verification_passed", contract.evidence_keys)
        self.assertIn("overfit_check_passed", contract.evidence_keys)
        self.assertIn("regression_passed", contract.evidence_keys)

    def test_testing_wrapper_defines_overfit_failure_mode(self):
        contract = get_wrapper("testing")
        modes = {m["mode"] for m in contract.failure_modes}
        self.assertIn("verification_failure", modes)
        self.assertIn("overfit_detected", modes)

    def test_implementation_wrapper_has_tdd_evidence_keys(self):
        contract = get_wrapper("implementation")
        self.assertIsNotNone(contract)
        self.assertIn("tasks_complete", contract.evidence_keys)
        self.assertIn("tdd_passed", contract.evidence_keys)
        self.assertIn("focused_tests_passed", contract.evidence_keys)


class TestAgentFailureRouting(unittest.TestCase):
    """Task 1.8: test-agent emits verification failures back to implement-agent by default;
    escalates to plan-agent for requirement/design ambiguity."""

    def test_testing_wrapper_failure_routes_to_implement(self):
        contract = get_wrapper("testing")
        modes = {m["mode"] for m in contract.failure_modes}
        self.assertIn("verification_failure", modes)
        action = next((r["action"] for r in contract.remediation
                       if r["for"] == "verification_failure"), "")
        self.assertIn("implement", action.lower())

    def test_overfit_failure_routes_to_implement(self):
        contract = get_wrapper("testing")
        remediation = {r["for"]: r["action"] for r in contract.remediation}
        action = remediation.get("overfit_detected", "")
        self.assertIn("implement", action.lower())

    def test_testing_remediation_has_back_to_implement(self):
        contract = get_wrapper("testing")
        actions = {r["for"]: r["action"] for r in contract.remediation}
        for key in ("verification_failure", "overfit_detected"):
            self.assertIn(key, actions, f"Missing remediation for {key}")
            self.assertTrue(
                "implement" in actions[key].lower() or "back" in actions[key].lower(),
                f"Remediation for {key} should route to implement-agent",
            )

    def test_plan_agent_escalates_ambiguous_requirements(self):
        contract = get_wrapper("planning")
        modes = {m["mode"]: m for m in contract.failure_modes}
        self.assertIn("ambiguous_requirements", modes)
        self.assertEqual(modes["ambiguous_requirements"]["blocks_phase"], "true")

    def test_test_agent_routes_to_plan_for_ambiguity(self):
        contract = get_wrapper("testing")
        modes = {m["mode"] for m in contract.failure_modes}
        self.assertIn("verification_failure", modes)


class TestNormalizedResultContract(unittest.TestCase):
    """Task 1.3: dev-orchestrator returns normalized result dict via evidence envelope,
    never directly writes .ai/workflows/runs/ files."""

    def test_evidence_envelope_never_writes_filesystem(self):
        import tempfile, os
        envelope = make_evidence_envelope(
            agent="implement-agent",
            status="success",
            phase="apply_change",
            slice_id="slice-1",
            flow_type="spec-flow",
            evidence={"focused_tests": [{"command": "pytest -k test", "result": "pass"}]},
        )
        d = envelope.to_dict()
        self.assertEqual(d["agent"], "implement-agent")

    def test_normalized_result_contains_all_gate_fields(self):
        envelope = make_evidence_envelope(
            agent="test-agent",
            status="success",
            phase="apply_change",
            slice_id="slice-2",
            flow_type="spec-flow",
            evidence={"verification_passed": True},
            artifacts={"handoff_path": "/path/to/handoff.md"},
            blockers=[],
            recommended_next_action="dispatch_review_agent",
        )
        d = envelope.to_dict()
        for key in ("agent", "status", "phase", "evidence", "artifacts", "blockers",
                     "recommended_next_action"):
            self.assertIn(key, d, f"Missing gate field: {key}")


class TestSdlcOrchestratorManualTrigger(unittest.TestCase):
    """Task 1.6: sdlc-orchestrator is manual-trigger only."""

    def test_frontmatter_description_rejects_auto_trigger_phrases(self):
        skill_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "skills", "sdlc-orchestrator",
        )
        skill_path = os.path.join(skill_dir, "SKILL.md")
        if not os.path.exists(skill_path):
            self.skipTest("sdlc-orchestrator SKILL.md not found")

        with open(skill_path) as f:
            content = f.read()

        self.assertIn("manual invocation only", content.lower())
        self.assertIn(
            'Do NOT auto-trigger on "new development task"', content)


AGENT_NAMES = [
    "dev-orchestrator", "plan-agent", "implement-agent",
    "test-agent", "review-agent", "finish-agent",
]

AGENT_DIRS = [".opencode", ".claude", ".cursor"]

AGENT_SUBAGENTS = [n for n in AGENT_NAMES if n != "dev-orchestrator"]

REQUIRED_SKILLS_MAP = {
    "dev-orchestrator": ["sdlc-repository-memory-load", "brainstorming"],
    "plan-agent": ["brainstorming", "writing-plans"],
    "implement-agent": ["test-driven-development", "executing-plans", "using-git-worktrees", "implementation-contract-discipline"],
    "test-agent": ["systematic-debugging", "behavioral-test-design", "sdlc-evalops"],
    "review-agent": ["requesting-code-review", "receiving-code-review", "verification-before-completion"],
    "finish-agent": ["finishing-a-development-branch", "sdlc-openspec-memory-sync", "sdlc-repository-memory-sync", "sdlc-roadmap"],
}

ENVELOPE_CONTRACT_MARKERS = [
    "evidence envelope", "handoff artifact", "raw log",
    "artifacts.handoff_path", "artifacts.raw_log_paths",
]


def _agent_path(agent_dir, agent_name):
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", agent_dir, "agents", f"{agent_name}.md",
    )


def _read_agent_frontmatter(agent_dir, agent_name):
    path = _agent_path(agent_dir, agent_name)
    from support.frontmatter import read_frontmatter
    return read_frontmatter(pathlib.Path(path))


# Import here to avoid module-level import issues


class TestAgentFilesExist(unittest.TestCase):
    """Agent .md files exist in all client directories."""

    def test_all_agent_files_exist_in_opencode(self):
        for name in AGENT_NAMES:
            path = _agent_path(".opencode", name)
            self.assertTrue(os.path.exists(path), f"Missing agent file: {path}")

    def test_all_agent_files_exist_in_claude(self):
        for name in AGENT_NAMES:
            path = _agent_path(".claude", name)
            self.assertTrue(os.path.exists(path), f"Missing agent file: {path}")

    def test_all_agent_files_exist_in_cursor(self):
        for name in AGENT_NAMES:
            path = _agent_path(".cursor", name)
            self.assertTrue(os.path.exists(path), f"Missing agent file: {path}")

    def test_no_agent_named_skill_dirs(self):
        """Agent names must NOT have stale empty skill directories.
        Agents are opencode agents (*/agents/*.md), not skills (*/skills/*/SKILL.md)."""
        agent_names_set = set(AGENT_NAMES) | {"sdlc-dev-orchestrator"}
        for client_dir in AGENT_DIRS:
            skills_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", client_dir, "skills",
            )
            if not os.path.isdir(skills_dir):
                continue
            for entry in os.listdir(skills_dir):
                entry_path = os.path.join(skills_dir, entry)
                if entry in agent_names_set:
                    self.assertFalse(
                        os.path.isdir(entry_path),
                        f"Stale skill dir for agent: {entry_path} (agents belong in {client_dir}/agents/, not skills/)",
                    )


class TestAgentFrontmatter(unittest.TestCase):
    """Agent frontmatter uses valid opencode agent schema fields."""

    VALID_FRONTMATTER_FIELDS = {
        "name", "model", "variant", "description", "mode", "hidden",
        "color", "steps", "permission", "disable", "temperature", "top_p",
        "options", "license", "compatibility", "metadata",
    }

    def test_dev_orchestrator_is_primary_mode(self):
        fm = _read_agent_frontmatter(".opencode", "dev-orchestrator")
        self.assertEqual(fm.get("mode"), "primary")

    def test_subagents_are_subagent_mode(self):
        for name in AGENT_SUBAGENTS:
            fm = _read_agent_frontmatter(".opencode", name)
            self.assertEqual(fm.get("mode"), "subagent",
                           f"{name} should be subagent")

    def test_all_agents_have_description(self):
        for name in AGENT_NAMES:
            fm = _read_agent_frontmatter(".opencode", name)
            self.assertTrue(fm.get("description"), f"{name} missing description")

    def test_all_agents_have_permission(self):
        for name in AGENT_NAMES:
            fm = _read_agent_frontmatter(".opencode", name)
            self.assertIsNotNone(fm.get("permission"), f"{name} missing permission")

    def test_dev_orchestrator_edit_is_deny(self):
        fm = _read_agent_frontmatter(".opencode", "dev-orchestrator")
        self.assertEqual(fm["permission"]["edit"], "deny")

    def test_agent_frontmatter_only_uses_valid_fields(self):
        for name in AGENT_NAMES:
            fm = _read_agent_frontmatter(".opencode", name)
            unknown = set(fm.keys()) - self.VALID_FRONTMATTER_FIELDS
            self.assertEqual(unknown, set(),
                           f"{name}: unknown frontmatter fields: {unknown}")

    def test_plan_agent_edit_is_deny(self):
        fm = _read_agent_frontmatter(".opencode", "plan-agent")
        self.assertEqual(fm["permission"]["edit"], "deny")

    def test_implement_agent_edit_is_allow(self):
        fm = _read_agent_frontmatter(".opencode", "implement-agent")
        self.assertEqual(fm["permission"]["edit"], "allow")

    def test_test_agent_edit_is_deny(self):
        fm = _read_agent_frontmatter(".opencode", "test-agent")
        self.assertEqual(fm["permission"]["edit"], "deny")

    def test_review_agent_edit_is_deny(self):
        fm = _read_agent_frontmatter(".opencode", "review-agent")
        self.assertEqual(fm["permission"]["edit"], "deny")

    def test_finish_agent_edit_is_ask(self):
        fm = _read_agent_frontmatter(".opencode", "finish-agent")
        self.assertEqual(fm["permission"]["edit"], "ask")

    def test_all_agents_have_workflow_py_bash_allow(self):
        for name in AGENT_NAMES:
            fm = _read_agent_frontmatter(".opencode", name)
            bash_rules = fm["permission"].get("bash", {})
            if isinstance(bash_rules, dict):
                self.assertIn(
                    "python3 .ai/workflows/scripts/workflow.py *",
                    bash_rules,
                    f"{name}: missing workflow.py bash rule"
                )

    def test_subagents_task_is_deny(self):
        for name in AGENT_SUBAGENTS:
            fm = _read_agent_frontmatter(".opencode", name)
            self.assertEqual(fm["permission"]["task"], "deny",
                           f"{name}: subagent task should be deny")

    def test_dev_orchestrator_task_is_allow(self):
        fm = _read_agent_frontmatter(".opencode", "dev-orchestrator")
        self.assertEqual(fm["permission"]["task"], "allow")

    def test_subagents_skill_is_allow(self):
        for name in AGENT_SUBAGENTS:
            fm = _read_agent_frontmatter(".opencode", name)
            self.assertEqual(fm["permission"]["skill"], "allow",
                           f"{name}: skill should be allow")

    def test_claude_cursor_copies_match_opencode(self):
        for name in AGENT_NAMES:
            opencode_fm = _read_agent_frontmatter(".opencode", name)
            for target in [".claude", ".cursor"]:
                target_fm = _read_agent_frontmatter(target, name)
                self.assertEqual(
                    opencode_fm.get("mode"), target_fm.get("mode"),
                    f"{name}: mode mismatch in {target}"
                )
                self.assertEqual(
                    opencode_fm.get("permission", {}).get("edit"),
                    target_fm.get("permission", {}).get("edit"),
                    f"{name}: edit permission mismatch in {target}"
                )


class TestAgentPromptBody(unittest.TestCase):
    """Agent prompt body contains required contracts and skill references."""

    def _read_agent_body(self, agent_name):
        path = _agent_path(".opencode", agent_name)
        with open(path) as f:
            content = f.read()
        idx = content.find("\n---", 3)
        if idx == -1:
            return ""
        return content[idx + 4:]

    def test_all_agents_reference_evidence_envelope(self):
        for name in AGENT_NAMES:
            body = self._read_agent_body(name)
            self.assertIn("evidence", body.lower(),
                         f"{name}: missing evidence envelope reference")
            self.assertIn("agent", body.lower(),
                         f"{name}: missing agent field reference")

    def test_all_agents_reference_handoff_artifact(self):
        for name in AGENT_NAMES:
            body = self._read_agent_body(name)
            self.assertIn("handoff", body.lower(),
                         f"{name}: missing handoff artifact reference")

    def test_all_agents_reference_raw_logs(self):
        for name in AGENT_NAMES:
            body = self._read_agent_body(name)
            self.assertIn("raw log", body.lower(),
                         f"{name}: missing raw log reference")

    def test_dev_orchestrator_mentions_dispatch_hooks(self):
        body = self._read_agent_body("dev-orchestrator")
        self.assertIn("before_dispatch", body)
        self.assertIn("after_dispatch", body)

    def test_dev_orchestrator_mentions_phase_agent_mapping(self):
        body = self._read_agent_body("dev-orchestrator")
        self.assertIn("create_change", body)
        self.assertIn("apply_change", body)
        self.assertIn("archive_change", body)

    def test_implement_agent_mentions_tdd_loop(self):
        body = self._read_agent_body("implement-agent")
        self.assertIn("failing test", body.lower())
        self.assertIn("focused_tests", body)

    def test_test_agent_mentions_overfit(self):
        body = self._read_agent_body("test-agent")
        self.assertIn("overfit", body)

    def test_test_agent_mentions_verification_sequence(self):
        body = self._read_agent_body("test-agent")
        self.assertIn("focused test", body.lower())
        self.assertIn("regression", body.lower())

    def test_each_agent_mentions_required_skills(self):
        for name in AGENT_NAMES:
            body = self._read_agent_body(name)
            expected = REQUIRED_SKILLS_MAP.get(name, [])
            for skill in expected:
                self.assertIn(skill, body,
                            f"{name}: missing required skill '{skill}' in prompt body")

    def test_subagent_prompt_mentions_flow_type(self):
        for name in AGENT_SUBAGENTS:
            body = self._read_agent_body(name)
            self.assertIn("flow_type", body,
                         f"{name}: missing flow_type handling")

    def test_finish_agent_mentions_hooks(self):
        body = self._read_agent_body("finish-agent")
        self.assertIn("memory_sync", body)
        self.assertIn("roadmap_done_if_relevant", body)

    def test_review_agent_waits_for_test_evidence(self):
        body = self._read_agent_body("review-agent")
        self.assertIn("verification_passed", body)


class TestExecutableRoutingTests(unittest.TestCase):
    """Tasks 1.5b, 1.7b, 1.8b, 1.12b: executable routing coverage."""

    def _read_agent_body(self, agent_name):
        path = _agent_path(".opencode", agent_name)
        with open(path) as f:
            content = f.read()
        idx = content.find("\n---", 3)
        if idx == -1:
            return ""
        return content[idx + 4:]

    # 1.5b: dev-orchestrator rejects parallel dispatch on shared files/modules
    def test_dev_orchestrator_mentions_parallel_rejection(self):
        body = self._read_agent_body("dev-orchestrator")
        self.assertIn("disjoint", body.lower())

    def test_dev_orchestrator_mentions_parallel_dispatch_guard(self):
        body = self._read_agent_body("dev-orchestrator")
        self.assertIn("parallel", body.lower())

    # 1.7b: test-agent full verification sequence
    def test_test_agent_mentions_rerun_focused_tests_first(self):
        body = self._read_agent_body("test-agent")
        self.assertIn("rerun", body.lower())

    def test_test_agent_mentions_full_verification_sequence(self):
        body = self._read_agent_body("test-agent")
        self.assertIn("rerun focused tests", body.lower())
        self.assertIn("overfit", body.lower())
        self.assertIn("regression", body.lower())
        self.assertIn("integration", body.lower())

    def test_test_agent_mentions_pass_fail_evidence_emission(self):
        body = self._read_agent_body("test-agent")
        self.assertIn("passing", body.lower())
        self.assertIn("evidence", body.lower())

    # 1.8b: test-agent preserves slice_id, escalates to plan-agent on ambiguity
    def test_test_agent_mentions_slice_id_preservation(self):
        body = self._read_agent_body("test-agent")
        self.assertIn("slice_id", body.lower())

    def test_test_agent_mentions_plan_agent_escalation(self):
        body = self._read_agent_body("test-agent")
        self.assertIn("plan-agent", body.lower())
        self.assertIn("ambiguity", body.lower())

    def test_test_agent_mentions_implement_agent_as_default_route(self):
        body = self._read_agent_body("test-agent")
        self.assertIn("implement-agent", body.lower())
        idx = body.lower().find("implement-agent")
        ambiguity_idx = body.lower().find("plan-agent")
        self.assertGreater(ambiguity_idx, -1)

    # 1.12b: raw log write policy test
    def test_raw_logs_stored_under_workflow_run_path(self):
        from _lib.wrapper_contracts import make_raw_log_entry, RAW_LOG_META_KEYS
        entry = make_raw_log_entry(
            path=".ai/workflows/runs/run-1/logs/slice-1/test-agent/pytest.log",
            kind="pytest",
            command="pytest tests/ -v",
            result="fail",
        )
        self.assertTrue(entry["path"].startswith(".ai/workflows/runs/"))
        for key in RAW_LOG_META_KEYS:
            self.assertIn(key, entry)

    def test_raw_logs_artifacts_referenced_from_evidence(self):
        from _lib.wrapper_contracts import make_evidence_envelope
        envelope = make_evidence_envelope(
            agent="test-agent",
            status="failed",
            phase="apply_change",
            slice_id="slice-1",
            flow_type="spec-flow",
            artifacts={
                "raw_log_paths": [
                    {"path": ".ai/workflows/runs/run-1/logs/slice-1/test-agent/debug.log",
                     "kind": "pytest", "command": "pytest -k test", "result": "fail"},
                ],
            },
        )
        d = envelope.to_dict()
        self.assertIn("artifacts", d)
        self.assertIn("raw_log_paths", d["artifacts"])
        self.assertEqual(len(d["artifacts"]["raw_log_paths"]), 1)


class TestExecutableWrapperAdapters(unittest.TestCase):
    """Behavior tests for executable wrapper adapter routing."""

    def test_spec_wrapper_does_not_synthesize_success_evidence(self):
        result = spec_wrapper_adapter(
            workflow_run_id="run-1",
            phase="create_change",
            action="create",
            flow_type="spec-flow",
            change_id="demo-change",
            repo_root=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        )
        self.assertEqual(result.envelope.status, "success")
        self.assertEqual(result.raw_output["backend"], "openspec-propose")
        self.assertNotIn("openspec_artifacts_done", result.envelope.evidence)
        self.assertEqual(result.envelope.evidence["change_id"], "demo-change")

    def test_non_provider_managed_wrapper_is_not_blocked_by_registry_gap(self):
        result = implementation_wrapper_adapter(
            workflow_run_id="run-1",
            phase="apply_change",
            action="apply",
            flow_type="spec-flow",
            slice_id="slice-1",
            tasks=["fix dispatch routing"],
            repo_root=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        )
        reasons = [b.get("reason") for b in result.envelope.blockers]
        self.assertNotIn("not_provider_managed", reasons)

    def test_provider_config_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / ".opencode").mkdir()
            (root / ".cursor").mkdir()
            (root / ".claude").mkdir()
            (root / ".opencode" / "sdlc-providers.yaml").write_text(
                "version: 1\nspec:\n  provider: openspec\nmemory:\n  provider: local\n"
            )
            (root / ".cursor" / "sdlc-providers.yaml").write_text(
                "version: 1\nspec:\n  provider: github/spec-kit\nmemory:\n  provider: local\n"
            )
            blockers = resolve_wrapper_provider_blockers("spec", "create", repo_root=str(root))
            reasons = [b.get("reason") for b in blockers]
            self.assertIn("provider_config_mismatch", reasons)


if __name__ == "__main__":
    unittest.main(verbosity=2)
