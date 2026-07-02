#!/usr/bin/env python3
"""Tests for wrapper contracts and agent evidence envelope contracts."""

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml

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
)
from _lib.provider_registry_loader import ResolvedProvider, resolve_provider_dispatch_spec
from _lib.provider_verifiers import get_provider_verifier, verify_provider_artifacts
from _lib.wrapper_resolution import WrapperResolutionBlocked, resolve_wrapper_dispatch


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
                           "finish-agent", "finish_agent",
                           "roadmap-agent", "roadmap_agent"):
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
    "test-agent", "review-agent", "finish-agent", "roadmap-agent",
]

AGENT_DIRS = [".opencode", ".claude", ".cursor"]

AGENT_SUBAGENTS = [n for n in AGENT_NAMES if n != "dev-orchestrator"]

REQUIRED_SKILLS_MAP = {
    "dev-orchestrator": ["sdlc-repository-memory-load", "brainstorming"],
    "plan-agent": ["brainstorming", "writing-plans"],
    "implement-agent": ["test-driven-development", "systematic-debugging", "executing-plans", "using-git-worktrees", "implementation-contract-discipline"],
    "test-agent": ["systematic-debugging", "behavioral-test-design", "sdlc-evalops"],
    "review-agent": ["requesting-code-review", "receiving-code-review", "verification-before-completion"],
    "finish-agent": ["finishing-a-development-branch", "sdlc-openspec-memory-sync", "sdlc-repository-memory-sync", "sdlc-roadmap"],
    "roadmap-agent": ["sdlc-roadmap", "sdlc-repository-memory-load"],
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

    def test_all_agents_use_permission_only_not_legacy_tools(self):
        for name in AGENT_NAMES:
            fm = _read_agent_frontmatter(".opencode", name)
            self.assertNotIn("tools", fm, f"{name}: legacy tools config should be removed")

    def test_dev_orchestrator_edit_is_deny(self):
        fm = _read_agent_frontmatter(".opencode", "dev-orchestrator")
        self.assertEqual(fm["permission"]["edit"], "deny")

    def test_agent_frontmatter_only_uses_valid_fields(self):
        for name in AGENT_NAMES:
            fm = _read_agent_frontmatter(".opencode", name)
            unknown = set(fm.keys()) - self.VALID_FRONTMATTER_FIELDS
            self.assertEqual(unknown, set(),
                           f"{name}: unknown frontmatter fields: {unknown}")

    def test_plan_agent_edit_is_allow(self):
        fm = _read_agent_frontmatter(".opencode", "plan-agent")
        self.assertEqual(fm["permission"]["edit"], "allow")

    def test_implement_agent_edit_is_allow(self):
        fm = _read_agent_frontmatter(".opencode", "implement-agent")
        self.assertEqual(fm["permission"]["edit"], "allow")

    def test_test_agent_edit_is_allow(self):
        fm = _read_agent_frontmatter(".opencode", "test-agent")
        self.assertEqual(fm["permission"]["edit"], "allow")

    def test_review_agent_edit_is_allow(self):
        fm = _read_agent_frontmatter(".opencode", "review-agent")
        self.assertEqual(fm["permission"]["edit"], "allow")

    def test_review_agent_does_not_allow_pytest_commands(self):
        fm = _read_agent_frontmatter(".opencode", "review-agent")
        bash_rules = fm["permission"].get("bash", {})
        self.assertNotIn("python3 -m pytest *", bash_rules)
        self.assertNotIn("pytest *", bash_rules)

    def test_finish_agent_edit_is_allow(self):
        fm = _read_agent_frontmatter(".opencode", "finish-agent")
        self.assertEqual(fm["permission"]["edit"], "allow")

    def test_all_agents_deny_generic_bash_fallback(self):
        for name in AGENT_NAMES:
            fm = _read_agent_frontmatter(".opencode", name)
            bash_rules = fm["permission"].get("bash", {})
            if isinstance(bash_rules, dict):
                self.assertEqual(
                    bash_rules.get("*"),
                    "deny",
                    f"{name}: generic bash fallback must be denied",
                )

    def test_bash_deny_rule_precedes_specific_allows(self):
        for name in AGENT_NAMES:
            fm = _read_agent_frontmatter(".opencode", name)
            bash_rules = fm["permission"].get("bash", {})
            if isinstance(bash_rules, dict):
                self.assertEqual(
                    next(iter(bash_rules)),
                    "*",
                    f"{name}: bash deny catch-all must come before specific allow rules",
                )

    def test_all_agents_explicitly_allow_read_search_permissions(self):
        for name in AGENT_NAMES:
            fm = _read_agent_frontmatter(".opencode", name)
            permission = fm["permission"]
            self.assertEqual(permission.get("read"), "allow", f"{name}: read should be allow")
            self.assertEqual(permission.get("grep"), "allow", f"{name}: grep should be allow")
            self.assertEqual(permission.get("glob"), "allow", f"{name}: glob should be allow")

    def test_dev_orchestrator_skill_deny_rule_precedes_specific_allows(self):
        fm = _read_agent_frontmatter(".opencode", "dev-orchestrator")
        skill_rules = fm["permission"].get("skill", {})
        self.assertIsInstance(skill_rules, dict)
        self.assertEqual(
            next(iter(skill_rules)),
            "*",
            "dev-orchestrator: skill deny catch-all must come before specific allow rules",
        )

    def test_implement_agent_allows_observational_git_only(self):
        fm = _read_agent_frontmatter(".opencode", "implement-agent")
        bash_rules = fm["permission"].get("bash", {})
        for command in (
            "git status*",
            "git diff*",
            "git log*",
            "git branch*",
            "git worktree*",
            "git check-ignore*",
        ):
            self.assertEqual(
                bash_rules.get(command),
                "allow",
                f"implement-agent missing observational git allow for {command}",
            )

    def test_finish_agent_allows_observational_git_completion_commands(self):
        fm = _read_agent_frontmatter(".opencode", "finish-agent")
        bash_rules = fm["permission"].get("bash", {})
        for command in ("git status*", "git diff*", "git log*", "git branch*", "git worktree*"):
            self.assertEqual(
                bash_rules.get(command),
                "allow",
                f"finish-agent missing observational git allow for {command}",
            )

    def test_plan_agent_allows_openspec_create_commands(self):
        """plan-agent needs openspec new/status/instructions/list for spec-flow create_change phase."""
        fm = _read_agent_frontmatter(".opencode", "plan-agent")
        bash_rules = fm["permission"].get("bash", {})
        for command in (
            "openspec new change*",
            "openspec status*",
            "openspec instructions*",
            "openspec list*",
        ):
            self.assertEqual(
                bash_rules.get(command),
                "allow",
                f"plan-agent missing openspec create-phase allow for {command}",
            )

    def test_implement_agent_allows_openspec_apply_commands(self):
        """implement-agent needs openspec apply/status/instructions/list for spec-flow apply_change phase."""
        fm = _read_agent_frontmatter(".opencode", "implement-agent")
        bash_rules = fm["permission"].get("bash", {})
        for command in (
            "openspec new change*",
            "openspec status*",
            "openspec instructions*",
            "openspec list*",
            "openspec apply*",
        ):
            self.assertEqual(
                bash_rules.get(command),
                "allow",
                f"implement-agent missing openspec apply-phase allow for {command}",
            )

    def test_finish_agent_allows_openspec_archive_commands(self):
        """finish-agent needs openspec archive/status/list for spec-flow archive_change phase."""
        fm = _read_agent_frontmatter(".opencode", "finish-agent")
        bash_rules = fm["permission"].get("bash", {})
        for command in (
            "openspec status*",
            "openspec list*",
            "openspec archive*",
        ):
            self.assertEqual(
                bash_rules.get(command),
                "allow",
                f"finish-agent missing openspec archive-phase allow for {command}",
            )

    def test_review_agent_denies_openspec_mutation_commands(self):
        """review-agent must NOT allow openspec mutation commands (create/apply/archive)."""
        fm = _read_agent_frontmatter(".opencode", "review-agent")
        bash_rules = fm["permission"].get("bash", {})
        for command in (
            "openspec new change*",
            "openspec apply*",
            "openspec archive*",
        ):
            self.assertNotEqual(
                bash_rules.get(command),
                "allow",
                f"review-agent should not allow openspec mutation command: {command}",
            )

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
                self.assertEqual(
                    opencode_fm.get("tools"),
                    target_fm.get("tools"),
                    f"{name}: tools mismatch in {target}"
                )

    def test_canonical_agent_tools_match_opencode_copy(self):
        for name in AGENT_NAMES:
            canonical_fm = _read_agent_frontmatter("", name)
            opencode_fm = _read_agent_frontmatter(".opencode", name)
            self.assertEqual(
                canonical_fm.get("tools"),
                opencode_fm.get("tools"),
                f"{name}: canonical tools must match .opencode copy",
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

    def test_worker_agents_write_active_run_artifacts(self):
        for name in ("plan-agent", "implement-agent", "test-agent", "review-agent", "finish-agent"):
            body = self._read_agent_body(name)
            self.assertIn(".ai/workflows/runs/active/<run_id>/", body,
                          f"{name}: missing active run artifact path")
            self.assertNotIn(".ai/workflows/runs/<run_id>/", body,
                             f"{name}: stale split run artifact path")

    def test_dev_orchestrator_mentions_dispatch_hooks(self):
        body = self._read_agent_body("dev-orchestrator")
        self.assertIn("before_dispatch", body)
        self.assertIn("after_dispatch", body)

    def test_dev_orchestrator_mentions_phase_agent_mapping(self):
        body = self._read_agent_body("dev-orchestrator")
        self.assertIn("create_change", body)
        self.assertIn("apply_change", body)
        self.assertIn("archive_change", body)

    def test_dev_orchestrator_mentions_workflow_entry_commands(self):
        body = self._read_agent_body("dev-orchestrator")
        self.assertIn("verify-foundations", body)
        self.assertIn("workflow.py start", body)
        self.assertIn("workflow.py resume", body)
        self.assertIn("workflow.py ensure-run", body)

    def test_dev_orchestrator_requires_explicit_flow_type_on_start(self):
        body = self._read_agent_body("dev-orchestrator")
        self.assertIn("--flow-type <flow-type>", body)
        self.assertIn("pass that exact value", body)

    def test_dev_orchestrator_uses_spec_change_public_subject_type(self):
        body = self._read_agent_body("dev-orchestrator")
        self.assertIn("spec_change", body)
        self.assertNotIn("openspec_change run", body)

    def test_dev_orchestrator_requires_run_confirmation_for_ambiguous_active_runs(self):
        body = self._read_agent_body("dev-orchestrator")
        self.assertIn("If the active run is unrelated or the match is unclear", body)
        self.assertIn("ask the user to confirm whether to reuse it", body)
        self.assertIn("continue that run", body)
        self.assertIn("start a new run", body)

    def test_dev_orchestrator_keeps_dispatch_hooks_after_run_confirmation(self):
        body = self._read_agent_body("dev-orchestrator")
        self.assertIn("Only after the run is confirmed usable may you call `before-dispatch`", body)
        self.assertIn("call workflow.py start or ensure-run first", body)

    def test_implement_agent_mentions_tdd_loop(self):
        body = self._read_agent_body("implement-agent")
        self.assertIn("failing test", body.lower())
        self.assertIn("focused_tests", body)

    def test_implement_agent_success_example_uses_boolean_contract_fields(self):
        body = self._read_agent_body("implement-agent")
        self.assertIn('"tasks_complete": true', body)
        self.assertIn('"tdd_passed": true', body)
        self.assertNotIn('"tasks_complete": "true|false"', body)
        self.assertNotIn('"tdd_passed": "true|false"', body)

    def test_implement_agent_includes_blocked_and_failed_examples(self):
        body = self._read_agent_body("implement-agent")
        self.assertIn('"status": "blocked"', body)
        self.assertIn('"status": "failed"', body)

    def test_implement_agent_forbids_claiming_pass_when_commands_not_run(self):
        for target in ("", ".opencode", ".claude", ".cursor"):
            path = _agent_path(target, "implement-agent")
            with open(path) as f:
                content = f.read()
            idx = content.find("\n---", 3)
            body = content[idx + 4:] if idx != -1 else ""
            label = target or "canonical"
            self.assertIn("not_run", body, f"{label}: missing not_run guidance")
            self.assertIn("requires_verification", body, f"{label}: missing requires_verification guidance")
            self.assertIn("must not report `pass`", body.lower(), f"{label}: missing explicit no-fake-pass rule")

    def test_implement_agent_honesty_guidance_matches_opencode_copy(self):
        canonical_path = _agent_path("", "implement-agent")
        opencode_path = _agent_path(".opencode", "implement-agent")
        with open(canonical_path) as f:
            canonical = f.read()
        with open(opencode_path) as f:
            opencode = f.read()
        for marker in ("not_run", "requires_verification", "must not report `pass`"):
            self.assertEqual(
                marker in canonical,
                marker in opencode,
                f"implement-agent: marker {marker!r} drifted between canonical and .opencode copy",
            )

    def test_review_agent_includes_blocked_routing_examples(self):
        body = self._read_agent_body("review-agent")
        self.assertIn('"status": "blocked"', body)
        self.assertIn('"recommended_next_action": "dispatch_implement_agent"', body)
        self.assertIn('"recommended_next_action": "dispatch_plan_agent"', body)

    def test_test_agent_mentions_overfit(self):
        body = self._read_agent_body("test-agent")
        self.assertIn("overfit", body)

    def test_test_agent_mentions_verification_sequence(self):
        body = self._read_agent_body("test-agent")
        self.assertIn("focused test", body.lower())
        self.assertIn("regression", body.lower())

    def test_test_agent_routing_table_uses_documented_failure_reasons_only(self):
        body = self._read_agent_body("test-agent")
        self.assertIn("verification_failure, overfit_detected", body)
        self.assertNotIn("regression_failure", body)

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

    def test_plan_agent_uses_provider_agnostic_spec_gate(self):
        body = self._read_agent_body("plan-agent")
        self.assertIn("spec_artifacts_done", body)
        self.assertIn("criteria_satisfied", body)
        self.assertNotIn("openspec_artifacts_done", body)

    def test_plan_agent_requires_resolved_dispatch_and_provider_verification(self):
        body = self._read_agent_body("plan-agent")
        self.assertIn("resolved wrapper dispatch", body.lower())
        self.assertIn("missing_resolved_dispatch", body)
        self.assertIn("provider verifier", body.lower())
        self.assertIn("must not return success", body.lower())

    def test_plan_agent_distributed_copies_match_contract_markers(self):
        for target in (".opencode", ".claude", ".cursor"):
            path = _agent_path(target, "plan-agent")
            with open(path) as f:
                content = f.read()
            idx = content.find("\n---", 3)
            body = content[idx + 4:] if idx != -1 else ""
            self.assertIn("spec_artifacts_done", body, f"{target} plan-agent missing provider-agnostic spec gate")
            self.assertIn("criteria_satisfied", body, f"{target} plan-agent missing criteria_satisfied contract")
            self.assertNotIn("openspec_artifacts_done", body, f"{target} plan-agent leaked provider-specific gate")

    def test_implement_agent_requires_resolved_dispatch_for_spec_flow(self):
        body = self._read_agent_body("implement-agent")
        self.assertIn("resolved wrapper dispatch", body.lower())
        self.assertIn("missing_resolved_dispatch", body)
        self.assertIn("provider verifier", body.lower())
        self.assertIn("spec wrapper via resolved provider dispatch", body.lower())

    def test_finish_agent_mentions_hooks(self):
        body = self._read_agent_body("finish-agent")
        self.assertIn("memory_sync", body)
        self.assertIn("roadmap_done_if_relevant", body)

    def test_finish_agent_requires_resolved_dispatch_for_spec_flow(self):
        body = self._read_agent_body("finish-agent")
        self.assertIn("resolved wrapper dispatch", body.lower())
        self.assertIn("missing_resolved_dispatch", body)
        self.assertIn("provider verifier", body.lower())
        self.assertIn("spec wrapper via resolved provider dispatch", body.lower())

    def test_finish_agent_includes_blocked_and_failed_examples(self):
        body = self._read_agent_body("finish-agent")
        self.assertIn('"status": "blocked"', body)
        self.assertIn('"status": "failed"', body)

    def test_review_agent_waits_for_test_evidence(self):
        body = self._read_agent_body("review-agent")
        self.assertIn("verification_passed", body)

    def test_review_agent_does_not_describe_local_test_execution(self):
        body = self._read_agent_body("review-agent").lower()
        self.assertNotIn("verification commands", body)
        self.assertNotIn("confirms green", body)

    def test_non_implementation_agents_limit_writes_to_workflow_artifacts(self):
        for name in ("plan-agent", "test-agent", "review-agent", "finish-agent"):
            body = self._read_agent_body(name).lower()
            self.assertIn("workflow artifact", body, f"{name}: missing workflow artifact boundary")
            self.assertIn("must not modify source", body, f"{name}: missing source-edit prohibition")

    def test_subagents_define_must_first_tool_policy_without_bash_degradation(self):
        required_markers = (
            "sdlc-repository-memory-load",
            "codegraph",
            "glob",
            "grep",
            "read",
            "context7",
            "tavily-search",
            "headroom",
            "must stop and return a blocker",
            "must not degrade to bash exploration",
            "observational git",
        )
        for name in AGENT_SUBAGENTS:
            body = self._read_agent_body(name).lower()
            for marker in required_markers:
                self.assertIn(marker, body, f"{name}: missing tool-policy marker {marker!r}")


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


class TestWrapperDispatchResolution(unittest.TestCase):
    def _make_repo_root_with_provider_config(self, config_text: str) -> pathlib.Path:
        return self._make_repo_root_with_provider_configs({".opencode": config_text})

    def _make_repo_root_with_provider_configs(self, config_by_dir: dict[str, str]) -> pathlib.Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        repo_root = pathlib.Path(temp_dir.name)
        for client_dir, config_text in config_by_dir.items():
            config_dir = repo_root / client_dir
            config_dir.mkdir(parents=True)
            (config_dir / "sdlc-providers.yaml").write_text(config_text)
        return repo_root

    def test_resolves_dispatch_verifier_and_contract_specs(self):
        repo_root = pathlib.Path(__file__).resolve().parent.parent

        spec_resolved = resolve_provider_dispatch_spec(
            module="spec",
            capability="create",
            repo_root=repo_root,
        )
        self.assertIsNotNone(spec_resolved)
        self.assertEqual(spec_resolved.provider, "openspec")
        self.assertEqual(spec_resolved.dispatch["kind"], "skill")
        self.assertEqual(spec_resolved.dispatch["target"], "openspec-propose")
        self.assertEqual(spec_resolved.verifier["target"], "openspec.create")
        self.assertEqual(spec_resolved.result_contract, "spec_change")

        memory_resolved = resolve_provider_dispatch_spec(
            module="memory",
            capability="repository_sync",
            repo_root=repo_root,
        )
        self.assertIsNotNone(memory_resolved)
        self.assertEqual(memory_resolved.provider, "local")
        self.assertEqual(memory_resolved.dispatch["kind"], "skill")
        self.assertEqual(memory_resolved.dispatch["target"], "sdlc-repository-memory-sync")
        self.assertEqual(memory_resolved.verifier["target"], "local.repository_sync")
        self.assertEqual(memory_resolved.result_contract, "memory_sync")

    def test_resolve_wrapper_dispatch_replaces_old_execute_adapter_shape(self):
        repo_root = pathlib.Path(__file__).resolve().parent.parent

        resolved = resolve_wrapper_dispatch(
            module="spec",
            capability="create",
            workflow_run_id="run-1",
            phase="create_change",
            action="create",
            flow_type="spec-flow",
            repo_root=repo_root,
        )

        self.assertEqual(resolved.module, "spec")
        self.assertEqual(resolved.capability, "create")
        self.assertEqual(resolved.provider, "openspec")
        self.assertEqual(resolved.dispatch["kind"], "skill")
        self.assertEqual(resolved.dispatch["target"], "openspec-propose")
        self.assertEqual(resolved.verifier["target"], "openspec.create")
        self.assertEqual(resolved.result_contract, "spec_change")

    def test_resolve_wrapper_dispatch_supports_spec_apply(self):
        repo_root = pathlib.Path(__file__).resolve().parent.parent

        resolved = resolve_wrapper_dispatch(
            module="spec",
            capability="apply",
            workflow_run_id="run-1",
            phase="apply_change",
            action="apply",
            flow_type="spec-flow",
            repo_root=repo_root,
        )

        self.assertEqual(resolved.module, "spec")
        self.assertEqual(resolved.capability, "apply")
        self.assertEqual(resolved.provider, "openspec")
        self.assertEqual(resolved.dispatch["kind"], "skill")
        self.assertEqual(resolved.dispatch["target"], "openspec-apply-change")
        self.assertEqual(resolved.verifier["target"], "openspec.apply")
        self.assertEqual(resolved.result_contract, "spec_change")

    def test_resolve_wrapper_dispatch_supports_spec_archive(self):
        repo_root = pathlib.Path(__file__).resolve().parent.parent

        resolved = resolve_wrapper_dispatch(
            module="spec",
            capability="archive",
            workflow_run_id="run-1",
            phase="archive_change",
            action="archive",
            flow_type="spec-flow",
            repo_root=repo_root,
        )

        self.assertEqual(resolved.module, "spec")
        self.assertEqual(resolved.capability, "archive")
        self.assertEqual(resolved.provider, "openspec")
        self.assertEqual(resolved.dispatch["kind"], "skill")
        self.assertEqual(resolved.dispatch["target"], "openspec-archive-change")
        self.assertEqual(resolved.verifier["target"], "openspec.archive")
        self.assertEqual(resolved.result_contract, "spec_change")

    def test_resolve_wrapper_dispatch_propagates_registry_native_result_contract(self):
        repo_root = pathlib.Path(__file__).resolve().parent.parent

        resolved = resolve_wrapper_dispatch(
            module="memory",
            capability="repository_sync",
            workflow_run_id="run-1",
            phase="apply_change",
            action="repository_sync",
            flow_type="spec-flow",
            repo_root=repo_root,
        )

        self.assertEqual(resolved.module, "memory")
        self.assertEqual(resolved.capability, "repository_sync")
        self.assertEqual(resolved.provider, "local")
        self.assertEqual(resolved.dispatch["kind"], "skill")
        self.assertEqual(resolved.dispatch["target"], "sdlc-repository-memory-sync")
        self.assertEqual(resolved.verifier["target"], "local.repository_sync")
        self.assertEqual(resolved.result_contract, "memory_sync")

    def test_resolve_provider_dispatch_spec_blocks_resolution_for_configured_provider_mismatch(self):
        repo_root = self._make_repo_root_with_provider_config(
            "spec:\n  provider: missing-provider\n"
        )

        resolved = resolve_provider_dispatch_spec(
            module="spec",
            capability="create",
            repo_root=repo_root,
        )

        self.assertIsNone(resolved)

    def test_resolve_provider_dispatch_spec_blocks_resolution_for_unsupported_configured_capability(self):
        repo_root = self._make_repo_root_with_provider_config(
            "spec:\n  provider: openspec\n"
        )

        resolved = resolve_provider_dispatch_spec(
            module="spec",
            capability="continue",
            repo_root=repo_root,
        )

        self.assertIsNone(resolved)

    def test_resolve_wrapper_dispatch_blocks_resolution_with_structured_blocker_details(self):
        repo_root = self._make_repo_root_with_provider_config(
            "spec:\n  provider: missing-provider\n"
        )

        with self.assertRaises(WrapperResolutionBlocked) as ctx:
            resolve_wrapper_dispatch(
                module="spec",
                capability="create",
                workflow_run_id="run-1",
                phase="create_change",
                action="create",
                flow_type="spec-flow",
                repo_root=repo_root,
            )

        self.assertTrue(hasattr(ctx.exception, "blockers"))
        self.assertEqual(ctx.exception.blockers[0]["reason"], "unknown_provider")
        self.assertIn("recommended_action", ctx.exception.blockers[0])

    def test_resolve_wrapper_dispatch_blocks_on_distributed_provider_config_mismatch(self):
        repo_root = self._make_repo_root_with_provider_configs({
            ".opencode": "spec:\n  provider: openspec\n",
            ".cursor": "spec:\n  provider: github/spec-kit\n",
        })

        with self.assertRaises(WrapperResolutionBlocked) as ctx:
            resolve_wrapper_dispatch(
                module="spec",
                capability="create",
                workflow_run_id="run-1",
                phase="create_change",
                action="create",
                flow_type="spec-flow",
                repo_root=repo_root,
            )

        self.assertEqual(
            ctx.exception.blockers[0]["reason"],
            "distributed_provider_config_mismatch",
        )

    def test_wrapper_resolution_blocked_is_not_a_value_error(self):
        self.assertTrue(issubclass(WrapperResolutionBlocked, Exception))
        self.assertFalse(issubclass(WrapperResolutionBlocked, ValueError))

    def test_resolve_wrapper_dispatch_blocks_on_unsupported_dispatch_kind(self):
        unsupported = ResolvedProvider(
            module="spec",
            provider="openspec",
            capability="create",
            dispatch_kind="command",
            dispatch_target="python3 do-something.py",
            dispatch={"kind": "command", "target": "python3 do-something.py"},
            verifier={"target": "openspec.create"},
            result_contract="spec_change",
        )

        with mock.patch("_lib.wrapper_resolution.resolve_wrapper_provider_blockers", return_value=[]), \
             mock.patch("_lib.wrapper_resolution.load_registry", return_value={}), \
             mock.patch("_lib.wrapper_resolution.load_consistent_provider_config", return_value=({}, [])), \
             mock.patch("_lib.wrapper_resolution.resolve_provider", return_value=unsupported):
            with self.assertRaises(WrapperResolutionBlocked) as ctx:
                resolve_wrapper_dispatch(
                    module="spec",
                    capability="create",
                    workflow_run_id="run-1",
                    phase="create_change",
                    action="create",
                    flow_type="spec-flow",
                    repo_root=pathlib.Path(__file__).resolve().parent.parent,
                )

        self.assertEqual(ctx.exception.blockers[0]["reason"], "unsupported_dispatch_kind")

    def test_resolve_wrapper_dispatch_falls_back_to_resolved_legacy_fields(self):
        resolved_provider = ResolvedProvider(
            module="spec",
            provider="openspec",
            capability="create",
            dispatch_kind="skill",
            dispatch_target="openspec-propose",
            dispatch={},
            verifier={},
            result_contract="",
        )

        with mock.patch("_lib.wrapper_resolution.resolve_wrapper_provider_blockers", return_value=[]), \
             mock.patch("_lib.wrapper_resolution.load_registry", return_value={}), \
             mock.patch("_lib.wrapper_resolution.load_consistent_provider_config", return_value=({}, [])), \
             mock.patch("_lib.wrapper_resolution.resolve_provider", return_value=resolved_provider):
            resolved = resolve_wrapper_dispatch(
                module="spec",
                capability="create",
                workflow_run_id="run-1",
                phase="create_change",
                action="create",
                flow_type="spec-flow",
                repo_root=pathlib.Path(__file__).resolve().parent.parent,
            )

        self.assertEqual(resolved.dispatch, {"kind": "skill", "target": "openspec-propose"})
        self.assertEqual(resolved.verifier, {"target": "openspec.create"})
        self.assertEqual(resolved.result_contract, "spec_result")


class TestProviderVerifiers(unittest.TestCase):
    def _make_openspec_change(self, repo_root: pathlib.Path, change_id: str) -> pathlib.Path:
        change_dir = repo_root / "openspec" / "changes" / change_id
        (change_dir / "specs").mkdir(parents=True)
        (change_dir / "proposal.md").write_text("# Proposal\n", encoding="utf-8")
        (change_dir / "design.md").write_text("# Design\n", encoding="utf-8")
        (change_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
        (change_dir / "specs" / "feature.md").write_text("# Spec\n", encoding="utf-8")
        return change_dir

    def test_openspec_create_verifier_succeeds_when_required_change_artifacts_exist(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = pathlib.Path(tmp_dir)
            self._make_openspec_change(repo_root, "demo-change")

            blockers = verify_provider_artifacts(
                "openspec.create",
                repo_root=repo_root,
                change_id="demo-change",
            )

        self.assertEqual(blockers, [])

    def test_openspec_create_verifier_blocks_when_required_artifact_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = pathlib.Path(tmp_dir)
            change_dir = self._make_openspec_change(repo_root, "demo-change")
            (change_dir / "tasks.md").unlink()

            blockers = verify_provider_artifacts(
                "openspec.create",
                repo_root=repo_root,
                change_id="demo-change",
            )

        self.assertEqual(blockers[0]["reason"], "missing_required_artifact")
        self.assertIn("tasks.md", blockers[0]["message"])

    def test_openspec_apply_verifier_succeeds_when_tasks_artifact_observable(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = pathlib.Path(tmp_dir)
            change_dir = self._make_openspec_change(repo_root, "demo-change")
            (change_dir / "tasks.md").write_text(
                "# Tasks\n\n- [x] Implement wrapper apply\n",
                encoding="utf-8",
            )

            blockers = verify_provider_artifacts(
                "openspec.apply",
                repo_root=repo_root,
                change_id="demo-change",
            )

        self.assertEqual(blockers, [])

    def test_openspec_apply_verifier_blocks_when_tasks_are_not_observable(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = pathlib.Path(tmp_dir)
            change_dir = self._make_openspec_change(repo_root, "demo-change")
            (change_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")

            blockers = verify_provider_artifacts(
                "openspec.apply",
                repo_root=repo_root,
                change_id="demo-change",
            )

        self.assertEqual(blockers[0]["reason"], "tasks_state_not_observed")
        self.assertIn("tasks.md", blockers[0]["message"])

    def test_openspec_archive_verifier_succeeds_when_archive_artifacts_exist(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = pathlib.Path(tmp_dir)
            archive_dir = repo_root / "openspec" / "changes" / "archive" / "2026-07-01-demo-change"
            (archive_dir / "specs").mkdir(parents=True)
            (archive_dir / "proposal.md").write_text("# Proposal\n", encoding="utf-8")
            (archive_dir / "design.md").write_text("# Design\n", encoding="utf-8")
            (archive_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
            (archive_dir / "specs" / "feature.md").write_text("# Spec\n", encoding="utf-8")

            blockers = verify_provider_artifacts(
                "openspec.archive",
                repo_root=repo_root,
                change_id="demo-change",
            )

        self.assertEqual(blockers, [])

    def test_openspec_archive_verifier_blocks_when_archive_artifacts_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = pathlib.Path(tmp_dir)
            archive_dir = repo_root / "openspec" / "changes" / "archive" / "2026-07-01-demo-change"
            archive_dir.mkdir(parents=True)

            blockers = verify_provider_artifacts(
                "openspec.archive",
                repo_root=repo_root,
                change_id="demo-change",
            )

        self.assertEqual(blockers[0]["reason"], "missing_required_artifact")
        self.assertIn("proposal.md", blockers[0]["message"])

    def test_local_repository_sync_verifier_reports_success_from_memory_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = pathlib.Path(tmp_dir)
            memory_dir = repo_root / ".ai" / "memory"
            memory_dir.mkdir(parents=True)
            (memory_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "repository_id": "demo",
                        "memory_version": 1,
                        "git": {
                            "available": True,
                            "has_commits": True,
                            "head": "abc123",
                            "last_synced_commit": "abc123",
                            "worktree_state": "clean",
                        },
                        "pending_snapshots": [],
                        "last_sync": {"timestamp": "2026-06-28T00:00:00Z", "commit": "abc123"},
                    }
                ),
                encoding="utf-8",
            )
            (memory_dir / "index.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "generated_at": "2026-06-28T00:00:00Z",
                        "entries": [],
                    }
                ),
                encoding="utf-8",
            )

            verifier = get_provider_verifier("local.repository_sync")
            self.assertIsNotNone(verifier)
            blockers = verify_provider_artifacts("local.repository_sync", repo_root=repo_root)

        self.assertEqual(blockers, [])

    def test_local_repository_sync_verifier_blocks_when_manifest_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = pathlib.Path(tmp_dir)
            memory_dir = repo_root / ".ai" / "memory"
            memory_dir.mkdir(parents=True)
            (memory_dir / "index.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "generated_at": "2026-06-28T00:00:00Z",
                        "entries": [],
                    }
                ),
                encoding="utf-8",
            )

            blockers = verify_provider_artifacts("local.repository_sync", repo_root=repo_root)

        self.assertEqual(blockers[0]["reason"], "memory_sync_artifacts_missing")
        self.assertIn("manifest.json", blockers[0]["message"])


class TestResultContractNormalizers(unittest.TestCase):
    """Task 5: contract normalizers for spec_change and memory_sync.

    Normalizers map provider-verifier results into stable evidence envelopes
    that are provider-verifier-agnostic.  A normalization failure or missing
    contract returns a structured blocker rather than a silent envelope.
    """

    @classmethod
    def setUpClass(cls):
        from _lib.result_contracts import (
            normalize_spec_change,
            normalize_memory_sync,
            normalize_result,
        )
        cls.normalize_spec_change = staticmethod(normalize_spec_change)
        cls.normalize_memory_sync = staticmethod(normalize_memory_sync)
        cls.normalize_result = staticmethod(normalize_result)

    # -- spec_change normalizer -------------------------------------------------

    def test_normalize_spec_change_success_envelope(self):
        raw = {
            "change_id": "demo-change",
            "status": "success",
            "artifact_paths": [
                "openspec/changes/demo-change/proposal.md",
                "openspec/changes/demo-change/tasks.md",
            ],
            "handoff_path": ".ai/workflows/runs/run-1/handoffs/slice-1/plan-agent.md",
        }
        result = self.normalize_spec_change(raw)
        self.assertEqual(result["change_id"], "demo-change")
        self.assertEqual(result["status"], "success")
        self.assertIn("artifact_paths", result)
        self.assertEqual(len(result["artifact_paths"]), 2)
        self.assertEqual(
            result["handoff_path"],
            ".ai/workflows/runs/run-1/handoffs/slice-1/plan-agent.md",
        )

    def test_normalize_spec_change_missing_change_id_blocks(self):
        raw = {"status": "success", "artifact_paths": []}
        result = self.normalize_spec_change(raw)
        self.assertIn("reason", result)
        self.assertEqual(result["reason"], "missing_change_id")

    def test_normalize_spec_change_missing_status_blocks(self):
        raw = {"change_id": "demo-change", "artifact_paths": []}
        result = self.normalize_spec_change(raw)
        self.assertIn("reason", result)
        self.assertEqual(result["reason"], "missing_status")

    def test_normalize_spec_change_handoff_path_absent_still_valid(self):
        raw = {
            "change_id": "demo-change",
            "status": "success",
            "artifact_paths": [],
        }
        result = self.normalize_spec_change(raw)
        self.assertEqual(result["status"], "success")
        self.assertIsNone(result.get("handoff_path"))

    def test_normalize_spec_change_failed_status_propagated(self):
        raw = {
            "change_id": "demo-change",
            "status": "failed",
            "artifact_paths": [],
        }
        result = self.normalize_spec_change(raw)
        self.assertEqual(result["status"], "failed")

    def test_normalize_spec_change_blocked_status_propagated(self):
        raw = {
            "change_id": "demo-change",
            "status": "blocked",
            "artifact_paths": [],
        }
        result = self.normalize_spec_change(raw)
        self.assertEqual(result["status"], "blocked")

    # -- memory_sync normalizer -------------------------------------------------

    def test_normalize_memory_sync_success_envelope(self):
        raw = {
            "status": "success",
            "loaded": {"timestamp": "2026-06-28T00:00:00Z", "entries_count": 5},
            "synced": {"last_sync": "2026-06-28T00:00:00Z", "commit": "abc123"},
        }
        result = self.normalize_memory_sync(raw)
        self.assertEqual(result["status"], "success")
        self.assertIn("loaded", result)
        self.assertIn("synced", result)
        self.assertEqual(result["loaded"]["entries_count"], 5)

    def test_normalize_memory_sync_missing_status_blocks(self):
        raw = {"loaded": {}, "synced": {}}
        result = self.normalize_memory_sync(raw)
        self.assertIn("reason", result)
        self.assertEqual(result["reason"], "missing_status")

    def test_normalize_memory_sync_without_loaded_still_valid(self):
        raw = {
            "status": "success",
            "synced": {"last_sync": "2026-06-28T00:00:00Z"},
        }
        result = self.normalize_memory_sync(raw)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result.get("loaded"), {})

    def test_normalize_memory_sync_without_synced_still_valid(self):
        raw = {
            "status": "success",
            "loaded": {"timestamp": "2026-06-28T00:00:00Z"},
        }
        result = self.normalize_memory_sync(raw)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result.get("synced"), {})

    def test_normalize_memory_sync_propagates_report_references(self):
        raw = {
            "status": "success",
            "loaded": {},
            "synced": {"last_sync": "2026-06-28T00:00:00Z"},
            "report_path": ".ai/memory/reports/sync-2026.md",
        }
        result = self.normalize_memory_sync(raw)
        self.assertEqual(
            result.get("report_path"),
            ".ai/memory/reports/sync-2026.md",
        )

    def test_normalize_memory_sync_propagates_queue_references(self):
        raw = {
            "status": "success",
            "loaded": {},
            "synced": {},
            "review_queue_path": ".ai/memory/review-queue.json",
        }
        result = self.normalize_memory_sync(raw)
        self.assertEqual(
            result.get("review_queue_path"),
            ".ai/memory/review-queue.json",
        )

    # -- normalize_result dispatcher -------------------------------------------

    def test_normalize_result_dispatches_spec_change(self):
        raw = {
            "change_id": "demo-change",
            "status": "success",
            "artifact_paths": [],
        }
        result = self.normalize_result("spec_change", raw)
        self.assertEqual(result["change_id"], "demo-change")
        self.assertEqual(result["status"], "success")

    def test_normalize_result_dispatches_memory_sync(self):
        raw = {
            "status": "success",
            "loaded": {},
            "synced": {"last_sync": "2026-06-28T00:00:00Z"},
        }
        result = self.normalize_result("memory_sync", raw)
        self.assertEqual(result["status"], "success")
        self.assertIn("synced", result)

    def test_normalize_result_unknown_contract_blocks(self):
        raw = {"change_id": "demo-change", "status": "success"}
        result = self.normalize_result("nonexistent_contract", raw)
        self.assertIn("reason", result)
        self.assertEqual(result["reason"], "unknown_contract")

    def test_normalize_result_normalization_failure_blocks(self):
        raw = {"status": "success"}  # missing change_id for spec_change
        result = self.normalize_result("spec_change", raw)
        self.assertIn("reason", result)
        self.assertEqual(result["reason"], "missing_change_id")


class TestProviderRegistryDefinition(unittest.TestCase):
    def _read_registry(self):
        registry_path = pathlib.Path(__file__).resolve().parent.parent / "skills" / "_lib" / "provider_registry.yaml"
        return yaml.safe_load(registry_path.read_text(encoding="utf-8"))

    def test_registry_uses_version_2_dispatch_shape(self):
        registry = self._read_registry()
        self.assertEqual(registry["version"], 2)

        openspec = registry["modules"]["spec"]["providers"]["openspec"]
        self.assertNotIn("backend", openspec)
        self.assertIn("dispatch", openspec)
        self.assertIn("verifier", openspec)
        self.assertIn("result_contract", openspec)

    def test_registry_only_exposes_currently_verified_capabilities(self):
        registry = self._read_registry()
        spec_caps = {name for name, supported in registry["modules"]["spec"]["providers"]["openspec"]["capabilities"].items() if supported}
        memory_caps = {name for name, supported in registry["modules"]["memory"]["providers"]["local"]["capabilities"].items() if supported}

        self.assertEqual(spec_caps, {"create", "apply", "archive"})
        self.assertEqual(memory_caps, {"repository_sync"})


class TestResolveDispatchCLI(unittest.TestCase):
    def _run_cli(self, *args: str):
        script = pathlib.Path(__file__).resolve().parent.parent / "skills" / "_lib" / "resolve_dispatch_cli.py"
        return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, check=False)

    def test_cli_outputs_nested_dispatch_and_verifier_specs(self):
        repo_root = pathlib.Path(__file__).resolve().parent.parent
        result = self._run_cli("spec", "create", "run-1", "create_change", "create", "spec-flow", str(repo_root))

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["dispatch"]["kind"], "skill")
        self.assertEqual(payload["dispatch"]["target"], "openspec-propose")
        self.assertEqual(payload["verifier"]["target"], "openspec.create")
        self.assertEqual(payload["result_contract"], "spec_change")
        self.assertNotIn("kind", payload)
        self.assertNotIn("target", payload)
        self.assertNotIn("verifier_target", payload)

    def test_cli_surfaces_structured_blockers_for_resolution_failures(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = pathlib.Path(tmp_dir)
            (repo_root / ".opencode").mkdir()
            (repo_root / ".cursor").mkdir()
            (repo_root / ".opencode" / "sdlc-providers.yaml").write_text("spec:\n  provider: openspec\n")
            (repo_root / ".cursor" / "sdlc-providers.yaml").write_text("spec:\n  provider: github/spec-kit\n")

            result = self._run_cli("spec", "create", "run-1", "create_change", "create", "spec-flow", str(repo_root))

        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["blockers"][0]["reason"], "distributed_provider_config_mismatch")


class TestDevOrchestratorWrapperDispatch(unittest.TestCase):
    """Task 6: dev-orchestrator resolves, dispatches, verifies, and normalizes kind=skill.

    The dev-orchestrator prompt must teach the resolve→dispatch→verify→normalize
    flow for wrapper-backed modules (spec and memory), using resolve_wrapper_dispatch,
    dispatch spec kind/target, provider verifiers, and result contract normalizers.
    """

    def _read_agent_body(self, agent_name):
        path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", ".opencode", "agents", f"{agent_name}.md",
        )
        with open(path) as f:
            content = f.read()
        idx = content.find("\n---", 3)
        if idx == -1:
            return ""
        return content[idx + 4:]

    def test_dev_orchestrator_references_wrapper_dispatch_resolution(self):
        """Prompt must teach resolve_wrapper_dispatch for dynamic dispatch routing."""
        body = self._read_agent_body("dev-orchestrator")
        self.assertIn("resolve_wrapper_dispatch", body,
                       "dev-orchestrator must reference resolve_wrapper_dispatch for wrapper dispatch")

    def test_dev_orchestrator_wrapper_dispatch_mentions_kind_and_target(self):
        """Prompt must mention dispatch spec kind and target fields."""
        body = self._read_agent_body("dev-orchestrator")
        self.assertIn("kind", body.lower(),
                       "dev-orchestrator must reference dispatch kind for dynamic routing")
        self.assertIn("target", body.lower(),
                       "dev-orchestrator must reference dispatch target for dynamic routing")

    def test_dev_orchestrator_wrapper_dispatch_mentions_verifier(self):
        """Prompt must mention provider verifier for wrapper-backed module dispatch."""
        body = self._read_agent_body("dev-orchestrator")
        self.assertIn("verifier", body.lower(),
                       "dev-orchestrator must reference provider verifier for wrapper dispatch")

    def test_dev_orchestrator_wrapper_dispatch_mentions_normalize_and_result_contract(self):
        """Prompt must mention result contract normalization after verification."""
        body = self._read_agent_body("dev-orchestrator")
        self.assertIn("normalize", body.lower(),
                       "dev-orchestrator must reference normalization of verification results")
        self.assertIn("result_contract", body,
                       "dev-orchestrator must reference result_contract for normalization")

    def test_dev_orchestrator_mentions_spec_lifecycle_phase_capability_mapping(self):
        body = self._read_agent_body("dev-orchestrator").lower()
        self.assertIn("create_change", body)
        self.assertIn("spec create", body)
        self.assertIn("apply_change", body)
        self.assertIn("spec apply", body)
        self.assertIn("archive_change", body)
        self.assertIn("spec archive", body)

    def test_dev_orchestrator_requires_user_confirmation_before_block_remediation(self):
        body = self._read_agent_body("dev-orchestrator").lower()
        self.assertIn("before any automatic blocker remediation", body)
        self.assertIn("ask the user", body)
        self.assertIn("recommended option", body)
        self.assertIn("other options", body)

    def test_dev_orchestrator_prompt_models_nested_dispatch_spec(self):
        body = self._read_agent_body("dev-orchestrator")
        self.assertIn('"dispatch": {', body)
        self.assertIn('"verifier": {', body)
        self.assertNotIn('"verifier_target"', body)

    def test_dev_orchestrator_dynamic_resolution_displaces_hardcoded_routing(self):
        """Prompt must use dynamic wrapper resolution, not hardcoded backend routing.

        The dispatch routing logic must use resolve_wrapper_dispatch to determine
        which skill to invoke for wrapper-backed modules.  Hardcoded routing patterns
        like "use `openspec-propose` for spec creation" or "load `sdlc-repository-memory-sync`
        for memory sync" indicate the old static dispatch approach and must be absent.
        """
        body = self._read_agent_body("dev-orchestrator")
        # Dynamic resolution must be present
        self.assertIn("resolve_wrapper_dispatch", body,
                       "dev-orchestrator must use resolve_wrapper_dispatch for dynamic dispatch")

        # The prompt must NOT contain a static dispatch routing rule that says
        # "when you need X, use Y skill" — that's the old hardcoded pattern.
        static_routing_phrases = [
            "use the openspec-",
            "load the sdlc-repository-",
            "invoke openspec-",
            "run openspec-",
        ]
        for phrase in static_routing_phrases:
            self.assertNotIn(
                phrase.lower(), body.lower(),
                f"dev-orchestrator must not use static routing phrase '{phrase}' — "
                f"use resolve_wrapper_dispatch with kind/target instead"
            )

    def test_dev_orchestrator_claude_cursor_copies_match_opencode_for_wrapper_dispatch(self):
        """Claude and Cursor copies of dev-orchestrator must also have wrapper dispatch language."""
        opencode_body = self._read_agent_body("dev-orchestrator")
        self.assertIn("resolve_wrapper_dispatch", opencode_body,
                       "opencode copy must have resolve_wrapper_dispatch first")

        for target_dir in [".claude", ".cursor"]:
            path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", target_dir, "agents", "dev-orchestrator.md",
            )
            with open(path) as f:
                content = f.read()
            idx = content.find("\n---", 3)
            body = content[idx + 4:] if idx != -1 else ""
            self.assertIn("resolve_wrapper_dispatch", body,
                          f"{target_dir}/agents/dev-orchestrator.md must mirror wrapper dispatch changes")


if __name__ == "__main__":
    unittest.main(verbosity=2)
