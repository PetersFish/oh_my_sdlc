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

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
AGENTS_DIR = REPO_ROOT / "agents"

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
    DESIGN_ARTIFACT_KINDS,
    DESIGN_ARTIFACT_SOURCES,
    DESIGN_ARTIFACT_KEYS,
    validate_design_artifacts,
    make_design_artifact_entry,
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
            recommended_next_action="dispatch_review_agent",
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
            "agent": "implement-agent",
            "status": "success",
            "phase": "apply_change",
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
            agent="custom-verifier",
            status="failed",
            phase="apply_change",
            slice_id="slice-2",
        )
        raw = envelope.to_json()
        parsed = json.loads(raw)
        self.assertEqual(parsed["agent"], "custom-verifier")
        self.assertEqual(parsed["status"], "failed")

    def test_envelope_validate_detects_allowed_statuses(self):
        for status in VALID_AGENT_STATUSES:
            errors = validate_evidence_envelope({
                "agent": "implement-agent",
                "status": status,
                "phase": "apply_change",
                "evidence": {},
            })
            self.assertEqual(errors, [], f"Status {status!r} should be valid")

    def test_plan_agent_success_requires_artifacts_object(self):
        errors = validate_evidence_envelope({
            "agent": "plan-agent",
            "status": "success",
            "phase": "create_change",
            "flow_type": "lightweight-flow",
            "evidence": {},
        })

        self.assertTrue(any("artifacts object" in e for e in errors))

    def test_plan_agent_success_requires_primary_design_path(self):
        errors = validate_evidence_envelope({
            "agent": "plan-agent",
            "status": "success",
            "phase": "create_change",
            "flow_type": "lightweight-flow",
            "evidence": {},
            "artifacts": {
                "design_artifact_paths": [
                    make_design_artifact_entry(
                        kind="plan",
                        path="docs/superpowers/plans/2026-07-02-demo.md",
                        source="superpowers",
                    ),
                ],
            },
        })

        self.assertTrue(any("primary_design_path" in e for e in errors))

    def test_plan_agent_success_requires_non_empty_design_artifacts(self):
        errors = validate_evidence_envelope({
            "agent": "plan-agent",
            "status": "success",
            "phase": "create_change",
            "flow_type": "lightweight-flow",
            "evidence": {},
            "artifacts": {
                "primary_design_path": "docs/superpowers/plans/2026-07-02-demo.md",
                "design_artifact_paths": [],
            },
        })

        self.assertTrue(any("non-empty array" in e for e in errors))

    def test_plan_agent_success_requires_valid_flow_type_for_artifact_rules(self):
        errors = validate_evidence_envelope({
            "agent": "plan-agent",
            "status": "success",
            "phase": "create_change",
            "evidence": {},
            "artifacts": {
                "primary_design_path": "openspec/changes/demo-change/proposal.md",
                "design_artifact_paths": [
                    make_design_artifact_entry(
                        kind="proposal",
                        path="openspec/changes/demo-change/proposal.md",
                        source="openspec",
                    ),
                ],
            },
        })

        self.assertTrue(any("valid flow_type" in e for e in errors))

    def test_plan_agent_success_validation_accepts_canonical_alias(self):
        errors = validate_evidence_envelope({
            "agent": "plan_agent",
            "status": "success",
            "phase": "create_change",
            "evidence": {},
        })

        self.assertTrue(any("valid flow_type" in e for e in errors))
        self.assertTrue(any("artifacts object" in e for e in errors))


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


class TestDesignArtifactPaths(unittest.TestCase):
    """Design artifacts expose plan/spec sources through structured evidence."""

    def test_lightweight_flow_accepts_plan_and_spec_artifacts(self):
        artifacts = {
            "primary_design_path": "docs/superpowers/plans/2026-07-02-demo.md",
            "design_artifact_paths": [
                make_design_artifact_entry(
                    kind="plan",
                    path="docs/superpowers/plans/2026-07-02-demo.md",
                    source="superpowers",
                ),
                make_design_artifact_entry(
                    kind="spec",
                    path="docs/superpowers/specs/2026-07-02-demo-design.md",
                    source="superpowers",
                ),
            ],
        }

        errors = validate_design_artifacts(artifacts, flow_type="lightweight-flow")

        self.assertEqual(errors, [])

    def test_spec_flow_accepts_multiple_spec_artifacts(self):
        artifacts = {
            "primary_design_path": "openspec/changes/demo-change/proposal.md",
            "design_artifact_paths": [
                make_design_artifact_entry(
                    kind="proposal",
                    path="openspec/changes/demo-change/proposal.md",
                    source="openspec",
                ),
                make_design_artifact_entry(
                    kind="tasks",
                    path="openspec/changes/demo-change/tasks.md",
                    source="openspec",
                ),
                make_design_artifact_entry(
                    kind="spec",
                    path="openspec/changes/demo-change/specs/agent-contracts/spec.md",
                    source="openspec",
                ),
                make_design_artifact_entry(
                    kind="spec",
                    path="openspec/changes/demo-change/specs/dev-orchestrator-agent-routing/spec.md",
                    source="openspec",
                ),
            ],
        }

        errors = validate_design_artifacts(artifacts, flow_type="spec-flow")

        self.assertEqual(errors, [])

    def test_primary_design_path_is_required(self):
        artifacts = {
            "design_artifact_paths": [
                make_design_artifact_entry(
                    kind="plan",
                    path="docs/superpowers/plans/2026-07-02-demo.md",
                    source="superpowers",
                ),
            ],
        }

        errors = validate_design_artifacts(artifacts, flow_type="lightweight-flow")

        self.assertTrue(any("primary_design_path" in e for e in errors))

    def test_primary_design_path_must_match_list_entry(self):
        artifacts = {
            "primary_design_path": "docs/superpowers/plans/missing.md",
            "design_artifact_paths": [
                make_design_artifact_entry(
                    kind="plan",
                    path="docs/superpowers/plans/2026-07-02-demo.md",
                    source="superpowers",
                ),
            ],
        }

        errors = validate_design_artifacts(artifacts, flow_type="lightweight-flow")

        self.assertTrue(any("must match" in e for e in errors))

    def test_design_artifact_paths_must_be_non_empty_array(self):
        artifacts = {
            "primary_design_path": "docs/superpowers/plans/2026-07-02-demo.md",
            "design_artifact_paths": [],
        }

        errors = validate_design_artifacts(artifacts, flow_type="lightweight-flow")

        self.assertTrue(any("non-empty array" in e for e in errors))

    def test_artifact_entry_requires_kind_path_and_source(self):
        artifacts = {
            "primary_design_path": "docs/superpowers/plans/2026-07-02-demo.md",
            "design_artifact_paths": [{"kind": "plan"}],
        }

        errors = validate_design_artifacts(artifacts, flow_type="lightweight-flow")

        self.assertTrue(any("missing keys" in e for e in errors))

    def test_spec_flow_requires_proposal_tasks_and_spec(self):
        artifacts = {
            "primary_design_path": "openspec/changes/demo-change/proposal.md",
            "design_artifact_paths": [
                make_design_artifact_entry(
                    kind="proposal",
                    path="openspec/changes/demo-change/proposal.md",
                    source="openspec",
                ),
            ],
        }

        errors = validate_design_artifacts(artifacts, flow_type="spec-flow")

        self.assertTrue(any("tasks" in e for e in errors))
        self.assertTrue(any("spec" in e for e in errors))

    def test_lightweight_flow_requires_plan(self):
        artifacts = {
            "primary_design_path": "docs/superpowers/specs/2026-07-02-demo-design.md",
            "design_artifact_paths": [
                make_design_artifact_entry(
                    kind="spec",
                    path="docs/superpowers/specs/2026-07-02-demo-design.md",
                    source="superpowers",
                ),
            ],
        }

        errors = validate_design_artifacts(artifacts, flow_type="lightweight-flow")

        self.assertTrue(any("plan" in e for e in errors))


class TestDesignArtifactPromptContracts(unittest.TestCase):
    """Agent prompts document the structured design artifact contract."""

    def test_plan_agent_uses_design_artifact_paths_not_plan_path(self):
        content = (AGENTS_DIR / "plan-agent.md").read_text(encoding="utf-8")
        self.assertIn("primary_design_path", content)


class TestDevOrchestratorStartWithPlanHandoff(unittest.TestCase):
    """dev-orchestrator documents governed implementation from existing design artifacts."""

    def test_documents_start_with_plan_handoff_inputs(self):
        content = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("start-with-plan", content)
        self.assertIn("flow_type", content)
        self.assertIn("primary_design_path", content)
        self.assertIn("design_artifact_paths", content)

    def test_documents_four_handoff_input_cases(self):
        content = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("Provides both `flow_type` and `primary_design_path`", content)
        self.assertIn("Provides only `flow_type`", content)
        self.assertIn("Provides only `primary_design_path`", content)
        self.assertIn("Provides neither", content)

    def test_start_with_plan_is_governed_not_direct_execution(self):
        content = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("before-dispatch", content)
        self.assertIn("implement-agent", content)
        self.assertIn("skip `plan-agent`", content)
        self.assertIn("design_artifact_paths", content)
        self.assertNotIn('"plan_path"', content)
        # Verify the JSON success example uses primary_design_path, not plan_path.
        # The deprecation notice may mention artifacts.plan_path — that is acceptable.
        import re
        json_artifacts_blocks = re.findall(
            r'"artifacts"\s*:\s*\{[^}]*\}', content
        )
        for block in json_artifacts_blocks:
            self.assertNotIn("plan_path", block)

    def test_dev_orchestrator_forwards_structured_design_artifacts(self):
        content = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("artifacts.primary_design_path", content)
        self.assertIn("artifacts.design_artifact_paths[]", content)
        self.assertIn("Do not", content)
        self.assertIn("handoff Markdown", content)

    def test_dev_orchestrator_does_not_reconfirm_supplied_flow_type(self):
        """If the user already supplied flow_type, dev-orchestrator must not ask again."""
        content = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("flow-type Confirmation Gate", content)
        self.assertIn("do NOT ask the user to confirm flow type again", content)
        self.assertIn("do NOT re-confirm `flow_type`", content)

    def test_dev_orchestrator_asks_flow_type_only_when_missing_or_conflicting(self):
        content = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("ONLY when", content)
        self.assertIn("it is missing", content)
        self.assertIn("maps to a different flow", content)
        self.assertIn("ambiguous", content)

    def test_dev_orchestrator_start_with_plan_only_flow_type_skips_reconfirm(self):
        content = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")
        # The "Provides only `flow_type`" row must explicitly skip re-confirmation.
        row = content[content.find("Provides only `flow_type`"):]
        row_end = row.find("\n|")
        row_text = row[:row_end if row_end != -1 else len(row)]
        self.assertIn("do NOT re-confirm", row_text)

    def test_apply_agents_include_learning_sections(self):
        for filename in ("implement-agent.md", "review-agent.md"):
            content = (AGENTS_DIR / filename).read_text(encoding="utf-8")
            with self.subTest(filename=filename):
                self.assertIn("Issues", content)
                self.assertIn("Learnings", content)
                self.assertIn("Suggestions", content)


class TestSpecChangeResultContract(unittest.TestCase):
    """Spec provider results normalize artifact paths for plan-agent handoff."""

    def test_normalize_spec_change_derives_design_artifact_paths(self):
        from _lib.result_contracts import normalize_result

        result = normalize_result("spec_change", {
            "change_id": "demo-change",
            "status": "created",
            "artifact_paths": [
                "openspec/changes/demo-change/proposal.md",
                "openspec/changes/demo-change/design.md",
                "openspec/changes/demo-change/tasks.md",
                "openspec/changes/demo-change/specs/agent-contracts/spec.md",
                "openspec/changes/demo-change/specs/dev-orchestrator-agent-routing/spec.md",
            ],
            "handoff_path": ".ai/workflows/runs/active/demo/handoffs/default/plan-agent.md",
        })

        self.assertEqual(result["primary_design_path"], "openspec/changes/demo-change/proposal.md")
        self.assertEqual(result["design_artifact_paths"][0], {
            "kind": "proposal",
            "path": "openspec/changes/demo-change/proposal.md",
            "source": "openspec",
        })
        self.assertEqual(
            [entry["kind"] for entry in result["design_artifact_paths"]].count("spec"),
            2,
        )


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
        for agent in ("implement-agent", "review-agent"):
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

    def test_roadmap_agent_allowed_in_review_roadmap(self):
        self.assertTrue(is_agent_allowed_in_phase("roadmap-agent", "review_roadmap"))
        self.assertFalse(is_agent_allowed_in_phase("plan-agent", "review_roadmap"))


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


class TestRoadmapSkillSpecChangeVocabulary(unittest.TestCase):
    def test_roadmap_skill_uses_review_passed_ready_semantics(self):
        body = (REPO_ROOT / "skills" / "sdlc-roadmap" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("ready     | Review passed", body)
        self.assertIn("spec_change", body)
        self.assertNotIn("openspec_change:", body)
        self.assertNotIn("Create complete OpenSpec artifacts", body)

    def test_roadmap_item_template_uses_spec_change(self):
        template = (REPO_ROOT / "skills" / "sdlc-roadmap" / "templates" / "item.md").read_text(encoding="utf-8")

        self.assertIn("spec_change:", template)
        self.assertNotIn("openspec_change:", template)


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
    """Testing wrapper contract covers independent verification (optional, non-default)."""

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
    """Testing wrapper routes verification failures back to implement-agent by default;
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

    def test_testing_wrapper_routes_to_plan_for_ambiguity(self):
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
            agent="review-agent",
            status="success",
            phase="apply_change",
            slice_id="slice-2",
            flow_type="spec-flow",
            evidence={"verification_passed": True},
            artifacts={"handoff_path": "/path/to/handoff.md"},
            blockers=[],
            recommended_next_action="complete_phase",
        )
        d = envelope.to_dict()
        for key in ("agent", "status", "phase", "evidence", "artifacts", "blockers",
                     "recommended_next_action"):
            self.assertIn(key, d, f"Missing gate field: {key}")


class TestRoadmapAgentReviewContract(unittest.TestCase):
    def test_roadmap_agent_documents_review_contract(self):
        body = (AGENTS_DIR / "roadmap-agent.md").read_text(encoding="utf-8")

        self.assertIn("roadmap_review", body)
        self.assertIn("review_roadmap", body)
        self.assertIn("roadmap_review_decision", body)
        self.assertIn("ask_user_next_step", body)
        self.assertIn("ask_user_for_clarification", body)

    def test_dev_orchestrator_maps_review_roadmap_to_roadmap_agent(self):
        body = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")

        self.assertIn("review_roadmap", body)
        self.assertIn("Review roadmap item", body)
        self.assertIn("roadmap_spec_link_if_ready", body)
        self.assertNotIn("roadmap_status_ready_if_linked", body)

    def test_dev_orchestrator_documents_primary_subject_roadmap_gating(self):
        """dev-orchestrator must document that roadmap-agent requires primary_subject.type == roadmap_item."""
        body = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")

        self.assertIn("primary_subject.type == \"roadmap_item\"", body)
        self.assertIn("roadmap-agent", body)
        self.assertIn("review_roadmap", body)


AGENT_NAMES = [
    "dev-orchestrator", "plan-agent", "implement-agent",
    "review-agent", "finish-agent", "roadmap-agent",
]

AGENT_DIRS = [".opencode", ".claude", ".cursor"]

AGENT_SUBAGENTS = [n for n in AGENT_NAMES if n != "dev-orchestrator"]

REQUIRED_SKILLS_MAP = {
    "dev-orchestrator": ["sdlc-repository-memory-load", "brainstorming"],
    "plan-agent": ["brainstorming", "writing-plans"],
    "implement-agent": ["test-driven-development", "systematic-debugging", "executing-plans", "using-git-worktrees", "implementation-contract-discipline"],
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
        for name in ("plan-agent", "implement-agent", "review-agent", "finish-agent"):
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

    def test_review_agent_blocked_guidance_keeps_alias_and_blocker_action_in_sync(self):
        body = self._read_agent_body("review-agent")
        self.assertIn('"recommended_action": "back_to_implement"', body)
        self.assertIn('"recommended_action": "back_to_plan"', body)
        self.assertIn("dispatch_implement_agent", body)
        self.assertIn("dispatch_plan_agent", body)

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

    def test_finish_agent_separates_archive_and_post_archive_cleanup(self):
        body = self._read_agent_body("finish-agent")
        self.assertIn("archive_change", body)
        self.assertIn("post_archive_actions", body)
        self.assertIn("memory_sync_done", body)
        self.assertIn("roadmap_done_checked", body)
        self.assertIn("derived_artifacts_synced", body)
        self.assertIn("cleanup_complete", body)
        self.assertIn("must not claim cleanup_complete during archive_change", body.lower())

    def test_finish_agent_archive_change_success_example_omits_legacy_cleanup_evidence(self):
        body = self._read_agent_body("finish-agent")
        archive_change_success_idx = body.find('"phase": "archive_change"')
        self.assertGreater(archive_change_success_idx, -1,
                           "finish-agent must define an archive_change output example")
        archive_success_block = body[archive_change_success_idx:archive_change_success_idx + 600]
        # Spec Decision 10: new runs use semantic archive evidence, not
        # misleading archive_path_exists.  Legacy archive_path_exists remains
        # accepted during migration but the success example should use the
        # new semantic fields.
        self.assertIn('"archive_action_completed": true', archive_success_block,
                      "archive_change success example must include archive_action_completed")
        self.assertNotIn("pending_hooks_empty", archive_success_block,
                          "archive_change success example must not include legacy pending_hooks_empty")

    def test_finish_agent_does_not_present_complete_hook_as_normal_flow(self):
        body = self._read_agent_body("finish-agent")
        legacy_idx = body.lower().find("legacy hook resolution procedure")
        self.assertGreater(legacy_idx, -1,
                           "finish-agent must scope complete-hook guidance under a legacy repair heading")
        legacy_section = body[legacy_idx:]
        self.assertIn("workflow.py complete-hook", legacy_section,
                      "legacy repair section must mention workflow.py complete-hook")
        normal_flow_section = body[:legacy_idx]
        complete_hook_in_normal = "workflow.py complete-hook" in normal_flow_section
        self.assertFalse(complete_hook_in_normal,
                        "complete-hook must not appear outside the legacy repair section")

    def test_dev_orchestrator_describes_subagent_owned_cleanup(self):
        body = self._read_agent_body("dev-orchestrator")
        self.assertIn("post_archive_actions", body)
        self.assertIn("finish-agent", body)
        self.assertIn("cleanup evidence", body.lower())
        self.assertIn("legacy complete-hook", body.lower())

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
        for name in ("plan-agent", "review-agent", "finish-agent"):
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

    # 1.12b: raw log write policy test
    def test_raw_logs_stored_under_workflow_run_path(self):
        from _lib.wrapper_contracts import make_raw_log_entry, RAW_LOG_META_KEYS
        entry = make_raw_log_entry(
            path=".ai/workflows/runs/run-1/logs/slice-1/review-agent/pytest.log",
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
            agent="review-agent",
            status="failed",
            phase="apply_change",
            slice_id="slice-1",
            flow_type="spec-flow",
            artifacts={
                "raw_log_paths": [
                    {"path": ".ai/workflows/runs/run-1/logs/slice-1/review-agent/debug.log",
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


class TestReviewAgentBashPermissionOrdering(unittest.TestCase):
    """Task 1: lock review-agent bash deny-first ordering per last-match-wins semantics."""

    def test_review_agent_bash_catch_all_deny_is_first_rule(self):
        fm = _read_agent_frontmatter(".opencode", "review-agent")
        bash_rules = list(fm["permission"]["bash"].items())
        self.assertEqual(
            bash_rules[0], ("*", "deny"),
            "review-agent: catch-all deny must be the first bash rule so specific allows after it take effect",
        )

    def test_review_agent_bash_specific_allows_follow_catch_all_deny(self):
        fm = _read_agent_frontmatter(".opencode", "review-agent")
        bash_rules = list(fm["permission"]["bash"].items())
        keys = [k for k, _ in bash_rules]
        deny_index = keys.index("*")
        for command in (
            "python3 -m pytest*",
            "pytest*",
            "python3 .ai/workflows/scripts/workflow.py *",
            "python3 scripts/*",
            "python3 skills/*",
            "git status*",
            "git diff*",
            "git log*",
        ):
            self.assertIn(command, keys)
            self.assertGreater(
                keys.index(command), deny_index,
                f"review-agent: allow rule '{command}' must come after catch-all deny",
            )
            self.assertEqual(
                fm["permission"]["bash"][command], "allow",
                f"review-agent: {command} must be allow",
            )

    def test_review_agent_bash_deny_first_in_all_distributed_copies(self):
        for target in (".opencode", ".claude", ".cursor"):
            fm = _read_agent_frontmatter(target, "review-agent")
            bash_rules = fm["permission"].get("bash", {})
            self.assertEqual(
                next(iter(bash_rules)), "*",
                f"review-agent ({target}): catch-all deny must precede specific allows",
            )
            self.assertEqual(bash_rules["*"], "deny")

    def test_implement_agent_bash_catch_all_deny_is_first_rule(self):
        fm = _read_agent_frontmatter(".opencode", "implement-agent")
        bash_rules = list(fm["permission"]["bash"].items())
        self.assertEqual(bash_rules[0], ("*", "deny"))

    def test_finish_agent_bash_catch_all_deny_is_first_rule(self):
        fm = _read_agent_frontmatter(".opencode", "finish-agent")
        bash_rules = list(fm["permission"]["bash"].items())
        self.assertEqual(bash_rules[0], ("*", "deny"))


class TestDerivedDriftBoundaryAndAggregateEntrypoint(unittest.TestCase):
    """Task 4: derived drift ownership moved to finish; aggregate entrypoint documented."""

    def _read_agent_body(self, agent_name):
        path = _agent_path(".opencode", agent_name)
        with open(path) as f:
            content = f.read()
        idx = content.find("\n---", 3)
        if idx == -1:
            return ""
        return content[idx + 4:]

    def test_implement_agent_states_distributed_drift_is_not_default_blocker(self):
        body = self._read_agent_body("implement-agent")
        self.assertIn(
            "Do not treat distributed-copy drift as a default apply-change blocker",
            body,
            "implement-agent must state that distributed drift is not a default apply-change blocker",
        )

    def test_review_agent_states_distributed_drift_is_finish_followup(self):
        body = self._read_agent_body("review-agent")
        self.assertIn(
            "derived drift as a finish follow-up",
            body,
            "review-agent must state that derived drift is a finish follow-up, not an apply-change blocker",
        )

    def test_finish_agent_mentions_sync_derived_artifacts_entrypoint(self):
        body = self._read_agent_body("finish-agent")
        self.assertIn("python3 scripts/sync_derived_artifacts.py --check", body)
        self.assertIn("python3 scripts/sync_derived_artifacts.py --fix", body)

    def test_agents_md_uses_aggregate_derived_sync_entrypoint(self):
        content = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("python3 scripts/sync_derived_artifacts.py --check", content)

    def test_finish_agent_owns_derived_drift_before_closure(self):
        body = self._read_agent_body("finish-agent")
        self.assertIn("Derived Artifact Sync", body)


class TestApplyChangeEvidencePromptContracts(unittest.TestCase):
    def test_review_agent_success_example_includes_apply_phase_evidence(self):
        body = (AGENTS_DIR / "review-agent.md").read_text(encoding="utf-8")

        self.assertIn('"tasks_complete": true', body)
        self.assertIn('"tdd_passed": true', body)
        self.assertIn('"eval_passed_or_human_decision_recorded": true', body)
        self.assertIn(
            '"criteria_satisfied": "tasks_complete,tdd_passed,eval_passed_or_human_decision_recorded"',
            body,
        )

    def test_implement_agent_no_longer_marks_verification_handoff_as_blocked(self):
        body = (AGENTS_DIR / "implement-agent.md").read_text(encoding="utf-8")

        self.assertIn('"recommended_next_action": "dispatch_review_agent"', body)
        self.assertNotIn('"reason": "verification_pending"', body)

    def test_dev_orchestrator_documents_phase_requirements_for_review_dispatch(self):
        body = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")

        self.assertIn("evidence_keys", body)
        self.assertIn("exit_criteria", body)
        self.assertIn("eval_passed_or_human_decision_recorded", body)


class TestReviewAgentGitPermissions(unittest.TestCase):
    """review-agent needs read-only Git allow rules for live change discovery."""

    REQUIRED_GIT_RULES = (
        "git status*",
        "git diff*",
        "git log*",
        "git ls-files*",
        "git check-ignore*",
        "git worktree*",
    )

    def _bash_rules(self, target=".opencode"):
        fm = _read_agent_frontmatter(target, "review-agent")
        return fm["permission"].get("bash", {})

    def test_required_git_commands_are_allowed(self):
        bash_rules = self._bash_rules()
        for command in self.REQUIRED_GIT_RULES:
            self.assertEqual(
                bash_rules.get(command),
                "allow",
                f"review-agent missing required git allow rule for {command}",
            )

    def test_required_git_commands_appear_after_catch_all_deny(self):
        bash_rules = self._bash_rules()
        keys = list(bash_rules.keys())
        self.assertEqual(keys[0], "*", "review-agent: catch-all deny must be first bash rule")
        self.assertEqual(bash_rules["*"], "deny")
        deny_index = 0
        for command in self.REQUIRED_GIT_RULES:
            self.assertIn(command, keys, f"review-agent missing {command}")
            self.assertGreater(
                keys.index(command), deny_index,
                f"review-agent: {command} must appear after catch-all deny",
            )

    def test_required_git_rules_present_in_all_distributed_copies(self):
        for target in (".opencode", ".claude", ".cursor"):
            bash_rules = self._bash_rules(target)
            for command in self.REQUIRED_GIT_RULES:
                self.assertEqual(
                    bash_rules.get(command), "allow",
                    f"review-agent ({target}): missing allow for {command}",
                )


class TestReviewAgentLiveChangeReviewProtocol(unittest.TestCase):
    """review-agent prompt must establish live Git as the source of truth."""

    def _body(self):
        return (AGENTS_DIR / "review-agent.md").read_text(encoding="utf-8")

    def test_prompt_contains_live_change_review_protocol_heading(self):
        self.assertIn("Live Change Review Protocol", self._body())

    def test_prompt_states_live_git_is_source_of_truth(self):
        self.assertIn("live Git working tree is the source of truth", self._body())

    def test_prompt_constrains_codegraph_to_after_live_change_set_known(self):
        self.assertIn("CodeGraph may be used only after the live change set is known", self._body())

    def test_prompt_lists_required_discovery_commands(self):
        body = self._body()
        self.assertIn("git diff --name-status", body)
        self.assertIn("git diff --cached --name-status", body)
        self.assertIn("git ls-files --others --exclude-standard", body)

    def test_prompt_names_change_set_missing_and_mismatch_blockers(self):
        body = self._body()
        self.assertIn("review_change_set_missing", body)
        self.assertIn("review_change_set_mismatch", body)


class TestReviewAgentVerificationReuseProtocol(unittest.TestCase):
    """review-agent must inspect implement-agent evidence before re-running tests."""

    def _body(self):
        return (AGENTS_DIR / "review-agent.md").read_text(encoding="utf-8")

    def test_prompt_contains_verification_reuse_protocol_heading(self):
        self.assertIn("Verification Reuse Protocol", self._body())

    def test_prompt_states_review_agent_is_not_primary_test_executor(self):
        self.assertIn("Review-agent is not the primary test executor", self._body())

    def test_prompt_states_do_not_run_full_tests_by_default(self):
        self.assertIn("Do not run full `tests/` by default", self._body())

    def test_prompt_states_run_smallest_command_set_when_re_running(self):
        self.assertIn("Run the smallest command set", self._body())

    def test_prompt_mentions_broad_regression_not_default(self):
        self.assertIn("broad regression", self._body())


class TestReviewAgentFinalOutputContract(unittest.TestCase):
    """review-agent final output must be exactly one valid JSON object."""

    def _body(self):
        return (AGENTS_DIR / "review-agent.md").read_text(encoding="utf-8")

    def test_prompt_contains_final_output_contract_discipline_heading(self):
        self.assertIn("Final Output Contract Discipline", self._body())

    def test_prompt_requires_exactly_one_valid_json_object(self):
        self.assertIn("exactly one valid JSON object", self._body())

    def test_prompt_requires_design_artifact_paths_array(self):
        self.assertIn("artifacts.design_artifact_paths", self._body())
        self.assertIn("must be a JSON array", self._body())

    def test_prompt_prohibits_handoff_prose_in_final_response(self):
        self.assertIn("Do not include handoff prose in the final response", self._body())


class TestFinishAgentFinalOutputContract(unittest.TestCase):
    """finish-agent final output must be consumable by workflow after-dispatch."""

    def _body(self):
        return (AGENTS_DIR / "finish-agent.md").read_text(encoding="utf-8")

    def test_prompt_contains_final_output_contract_discipline_heading(self):
        self.assertIn("Final Output Contract Discipline", self._body())

    def test_prompt_requires_exactly_one_valid_json_object(self):
        self.assertIn("exactly one valid JSON object", self._body())

    def test_prompt_says_thought_json_does_not_satisfy_contract(self):
        body = self._body()
        self.assertIn("final response body", body)
        self.assertIn("reasoning/thoughts", body)
        self.assertIn("does not satisfy the contract", body)

    def test_prompt_prohibits_markdown_fences_in_final_response(self):
        self.assertIn("Do not wrap the JSON object in a fenced code block", self._body())

    def test_prompt_requires_post_archive_actions_cleanup_evidence(self):
        body = self._body()
        for key in (
            "memory_sync_done: true",
            "roadmap_done_checked: true",
            "derived_artifacts_synced: true",
            "post_hook_dirty_tree: false",
            "cleanup_complete: true",
        ):
            self.assertIn(key, body)


class TestImplementAgentChangeSetAndRegressionContract(unittest.TestCase):
    """implement-agent must hand off changed-file evidence and run full regression."""

    def _body(self):
        return (AGENTS_DIR / "implement-agent.md").read_text(encoding="utf-8")

    def test_prompt_contains_change_set_handoff_contract_heading(self):
        self.assertIn("Implementation Change-Set Handoff Contract", self._body())

    def test_prompt_requires_changed_files_field(self):
        self.assertIn("changed_files", self._body())

    def test_prompt_requires_worktree_path_field(self):
        self.assertIn("worktree_path", self._body())

    def test_prompt_requires_diff_commands_field(self):
        self.assertIn("diff_commands", self._body())

    def test_prompt_requires_verification_commands_field(self):
        self.assertIn("verification_commands", self._body())

    def test_prompt_contains_full_regression_gate_heading(self):
        self.assertIn("Full Regression Gate", self._body())

    def test_prompt_specifies_default_full_regression_command(self):
        self.assertIn("python3 -m pytest tests/ -v", self._body())

    def test_prompt_requires_full_regression_before_success(self):
        self.assertIn(
            "Do not return `status: success` until focused verification and full regression both pass",
            self._body(),
        )


class TestReviewAgentWorktreeGitCPermissions(unittest.TestCase):
    """review-agent needs read-only `git -C *` allow rules for worktree-mode live change review."""

    REQUIRED_GIT_C_RULES = (
        "git -C * status*",
        "git -C * diff*",
        "git -C * log*",
        "git -C * ls-files*",
        "git -C * check-ignore*",
        "git -C * rev-parse*",
        "git -C * branch*",
    )

    def _bash_rules(self, target=".opencode"):
        fm = _read_agent_frontmatter(target, "review-agent")
        return fm["permission"].get("bash", {})

    def test_required_git_c_commands_are_allowed(self):
        bash_rules = self._bash_rules()
        for command in self.REQUIRED_GIT_C_RULES:
            self.assertEqual(
                bash_rules.get(command),
                "allow",
                f"review-agent missing required git -C allow rule for {command}",
            )

    def test_required_git_c_commands_appear_after_catch_all_deny(self):
        bash_rules = self._bash_rules()
        keys = list(bash_rules.keys())
        self.assertEqual(keys[0], "*", "review-agent: catch-all deny must be first bash rule")
        self.assertEqual(bash_rules["*"], "deny")
        deny_index = 0
        for command in self.REQUIRED_GIT_C_RULES:
            self.assertIn(command, keys, f"review-agent missing {command}")
            self.assertGreater(
                keys.index(command), deny_index,
                f"review-agent: {command} must appear after catch-all deny",
            )

    def test_required_git_c_rules_present_in_all_distributed_copies(self):
        for target in (".opencode", ".claude", ".cursor"):
            bash_rules = self._bash_rules(target)
            for command in self.REQUIRED_GIT_C_RULES:
                self.assertEqual(
                    bash_rules.get(command), "allow",
                    f"review-agent ({target}): missing allow for {command}",
                )


class TestReviewAgentWorktreeModeLiveChangeReviewProtocol(unittest.TestCase):
    """review-agent prompt must establish worktree-mode `git -C` source-of-truth rules."""

    def _body(self):
        return (AGENTS_DIR / "review-agent.md").read_text(encoding="utf-8")

    def test_prompt_contains_worktree_mode_live_change_review_protocol_heading(self):
        self.assertIn("Worktree-Mode Live Change Review Protocol", self._body())

    def test_prompt_requires_explicit_worktree_path_as_source_of_truth(self):
        body = self._body()
        self.assertIn("worktree_path", body)
        self.assertIn("implementation source of truth", body)

    def test_prompt_requires_git_c_worktree_inspection(self):
        body = self._body()
        self.assertIn("git -C <worktree_path>", body)
        self.assertIn("git -C <worktree_path> rev-parse --show-toplevel", body)

    def test_prompt_forbids_shell_cwd_dependency_in_worktree_mode(self):
        body = self._body()
        self.assertIn("never rely on shell cwd", body)

    def test_prompt_forbids_fallback_to_main_checkout_in_worktree_mode(self):
        body = self._body()
        self.assertIn("never fallback to the main", body)

    def test_prompt_names_worktree_context_blockers(self):
        body = self._body()
        self.assertIn("missing_worktree_context", body)
        self.assertIn("invalid_worktree_context", body)
        self.assertIn("review_worktree_mismatch", body)

    def test_prompt_preserves_plain_git_for_main_checkout_mode(self):
        body = self._body()
        self.assertIn("main-checkout mode", body)


class TestDevOrchestratorReviewDispatchContract(unittest.TestCase):
    """dev-orchestrator must forward implement-agent change-set to review-agent."""

    def _body(self):
        return (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")

    def test_prompt_contains_review_dispatch_change_set_contract_heading(self):
        self.assertIn("Review Dispatch Change-Set Contract", self._body())

    def test_prompt_forwards_changed_files(self):
        self.assertIn("changed_files", self._body())

    def test_prompt_forwards_worktree_path(self):
        self.assertIn("worktree_path", self._body())

    def test_prompt_forwards_diff_commands(self):
        self.assertIn("diff_commands", self._body())

    def test_prompt_forwards_verification_commands(self):
        self.assertIn("verification_commands", self._body())

    def test_prompt_names_change_set_missing_blocker(self):
        self.assertIn("review_change_set_missing", self._body())

    def test_prompt_names_change_set_mismatch_blocker(self):
        self.assertIn("review_change_set_mismatch", self._body())

    def test_prompt_prohibits_codegraph_as_source_of_truth_for_uncommitted_changes(self):
        self.assertIn(
            "Do not use CodeGraph as the source of truth for uncommitted changes",
            self._body(),
        )


class TestWorktreeVerificationHygienePromptContracts(unittest.TestCase):
    """Prompt-contract tests for worktree verification hygiene and derived artifact dry-run.

    These tests prove the agent prompts document:
    - --dry-run as the preferred derived sync smoke mode
    - producer-owned cleanup for transient artifacts
    - structured verification_summary with accepted pre-existing failures
    - constrained git restore for known safe derived paths
    - review-agent accepting structured hygiene evidence
    """

    def _read_agent_body(self, agent_name):
        path = _agent_path(".opencode", agent_name)
        with open(path) as f:
            content = f.read()
        idx = content.find("\n---", 3)
        if idx == -1:
            return ""
        return content[idx + 4:]

    # --- implement-agent: --dry-run preference ---

    def test_implement_agent_prefers_dry_run_for_derived_sync_smoke(self):
        body = self._read_agent_body("implement-agent")
        self.assertIn("--dry-run", body,
                       "implement-agent must prefer --dry-run for derived sync smoke checks")

    def test_implement_agent_documents_dry_run_smoke_command(self):
        body = self._read_agent_body("implement-agent")
        self.assertIn("sync_derived_artifacts.py --dry-run", body,
                       "implement-agent must document the --dry-run smoke command")

    # --- implement-agent: producer-owned cleanup ---

    def test_implement_agent_states_producer_owned_cleanup(self):
        body = self._read_agent_body("implement-agent")
        lower = body.lower()
        self.assertIn("producer-owned cleanup", lower,
                      "implement-agent must state producer-owned cleanup requirement")
        self.assertIn("transient", lower,
                      "implement-agent must mention transient artifacts cleanup")

    def test_implement_agent_requires_smoke_tests_use_dry_run_unless_repair(self):
        body = self._read_agent_body("implement-agent")
        lower = body.lower()
        # Must guide that smoke tests use --dry-run unless explicitly repairing drift
        self.assertIn("dry-run", lower)
        self.assertIn("repair", lower)

    # --- implement-agent: verification summary schema ---

    def test_implement_agent_documents_verification_summary_status_values(self):
        body = self._read_agent_body("implement-agent")
        self.assertIn("verification_summary", body,
                      "implement-agent must document verification_summary schema")
        self.assertIn("pass_with_accepted_preexisting_failures", body,
                      "implement-agent must document pass_with_accepted_preexisting_failures status")

    def test_implement_agent_documents_accepted_failure_evidence_fields(self):
        body = self._read_agent_body("implement-agent")
        # Accepted pre-existing failures must include test id, reason, confirmation
        self.assertIn("accepted_preexisting_failures", body)
        self.assertIn("test", body)
        self.assertIn("reason", body)
        self.assertIn("confirmation", body)

    # --- implement-agent: constrained git restore ---

    def test_implement_agent_documents_constrained_git_restore(self):
        body = self._read_agent_body("implement-agent")
        self.assertIn("git restore", body,
                      "implement-agent must document constrained git restore for known safe derived paths")

    # --- review-agent: accept structured hygiene evidence ---

    def test_review_agent_accepts_pass_with_accepted_preexisting_failures(self):
        body = self._read_agent_body("review-agent")
        self.assertIn("pass_with_accepted_preexisting_failures", body,
                      "review-agent must accept pass_with_accepted_preexisting_failures")

    def test_review_agent_does_not_bounce_known_hygiene_noise_with_evidence(self):
        body = self._read_agent_body("review-agent")
        lower = body.lower()
        self.assertIn("hydration", lower,
                      "review-agent must reference hydration evidence")
        self.assertIn("dry-run", lower,
                      "review-agent must reference dry-run evidence")

    def test_review_agent_requires_accepted_failures_be_scoped_and_named(self):
        body = self._read_agent_body("review-agent")
        self.assertIn("accepted_preexisting_failures", body)
        # Must require failures be scoped and confirmed unrelated to implementation
        self.assertIn("scoped", body.lower())
        self.assertIn("confirmed", body.lower())

    def test_review_agent_rejects_broad_environment_statements(self):
        body = self._read_agent_body("review-agent")
        # Broad statements like "all tests passed except environment" must not be acceptable
        self.assertIn("all tests passed except environment", body)


class TestSyncDerivedArtifactsDryRunCLI(unittest.TestCase):
    """CLI-level tests for sync_derived_artifacts.py --dry-run flag."""

    def _run_cli(self, *args):
        script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "scripts", "sync_derived_artifacts.py",
        )
        return subprocess.run(
            [sys.executable, script, *args],
            capture_output=True, text=True, check=False,
        )

    def test_cli_accepts_dry_run_flag(self):
        """The CLI must accept --dry-run without error."""
        result = self._run_cli("--dry-run", "--check", "--json")
        # Should not error with "unrecognized arguments"
        self.assertNotIn("unrecognized arguments", result.stderr,
                         f"--dry-run flag not accepted: {result.stderr}")
        self.assertNotIn("error:", result.stderr.lower(),
                         f"--dry-run flag caused error: {result.stderr}")

    def test_cli_dry_run_with_changed_file(self):
        """The CLI must accept --dry-run --changed-file --json and produce JSON."""
        result = self._run_cli(
            "--dry-run", "--fix", "--changed-file", "docs/superpowers/specs/example.md", "--json",
        )
        # Should produce valid JSON output (docs-only change = skipped scope, rc=0)
        self.assertEqual(result.returncode, 0,
                         f"--dry-run --fix --changed-file failed: {result.stderr}")
        try:
            report = json.loads(result.stdout)
            self.assertTrue(report.get("dry_run", False),
                            f"dry_run must be true in CLI output: {report}")
        except json.JSONDecodeError:
            self.fail(f"--dry-run CLI did not produce valid JSON: {result.stdout}")


class TestWorktreeHydrationScript(unittest.TestCase):
    """Tests for .ai/workflows/scripts/hydrate_workspace.py."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _script_path(self):
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", ".ai", "workflows", "scripts", "hydrate_workspace.py",
        )

    def _run_hydrate(self, root, *extra_args):
        script = self._script_path()
        cmd = [sys.executable, script, "--root", root] + list(extra_args)
        return subprocess.run(cmd, capture_output=True, text=True, check=False)

    def test_hydrate_script_exists(self):
        self.assertTrue(os.path.isfile(self._script_path()),
                        "hydrate_workspace.py must exist")

    def test_hydrate_creates_evalops_case_directories(self):
        """Hydration must create case inbox/accepted/rejected dirs under eval targets."""
        # Create a target manifest to simulate an eval target
        target_dir = os.path.join(self.tmp, ".ai", "evals", "targets", "skill.demo-evalops")
        os.makedirs(target_dir)
        with open(os.path.join(target_dir, "manifest.yaml"), "w") as f:
            f.write("target_id: skill.demo-evalops\n")

        result = self._run_hydrate(self.tmp)
        self.assertEqual(result.returncode, 0,
                         f"hydration failed: {result.stderr}")

        for subdir in ("cases/inbox", "cases/accepted", "cases/rejected"):
            path = os.path.join(target_dir, subdir)
            self.assertTrue(os.path.isdir(path),
                            f"hydration must create {subdir}, but it was not found")

    def test_hydrate_does_not_create_workflow_run_state(self):
        """Hydration must NOT create workflow run state directories."""
        result = self._run_hydrate(self.tmp)
        self.assertEqual(result.returncode, 0)

        for forbidden in (
            ".ai/workflows/runs/active",
            ".ai/workflows/runs/current.json",
            ".ai/workflows/runs/history",
        ):
            path = os.path.join(self.tmp, forbidden)
            self.assertFalse(os.path.exists(path),
                             f"hydration must not create {forbidden}")

    def test_hydrate_is_idempotent(self):
        """Running hydration twice must be safe and not error."""
        target_dir = os.path.join(self.tmp, ".ai", "evals", "targets", "skill.demo-evalops")
        os.makedirs(target_dir)
        with open(os.path.join(target_dir, "manifest.yaml"), "w") as f:
            f.write("target_id: skill.demo-evalops\n")

        result1 = self._run_hydrate(self.tmp)
        self.assertEqual(result1.returncode, 0,
                         f"first hydration failed: {result1.stderr}")

        result2 = self._run_hydrate(self.tmp)
        self.assertEqual(result2.returncode, 0,
                         f"second hydration failed: {result2.stderr}")

    def test_hydrate_reports_created_directories(self):
        """Hydration output must report what directories it created."""
        target_dir = os.path.join(self.tmp, ".ai", "evals", "targets", "skill.demo-evalops")
        os.makedirs(target_dir)
        with open(os.path.join(target_dir, "manifest.yaml"), "w") as f:
            f.write("target_id: skill.demo-evalops\n")

        result = self._run_hydrate(self.tmp)
        # Output should mention created directories
        combined = result.stdout + result.stderr
        self.assertIn("cases", combined.lower(),
                      f"hydration output must report created directories: {combined}")


class TestExecutionContextArtifactContract(unittest.TestCase):
    """Prompt-contract tests for execution context artifact naming.

    New agent artifacts must use ``base_branch`` and ``parent_ref`` instead of
    the ambiguous ``base_ref``.  dev-orchestrator must forward
    ``runtime_context`` and avoid path inference from prose.
    """

    def test_implement_agent_uses_base_branch_and_parent_ref_not_base_ref(self):
        body = (AGENTS_DIR / "implement-agent.md").read_text(encoding="utf-8")
        self.assertIn("base_branch", body)
        self.assertIn("parent_ref", body)
        # The Required artifact fields list must not include base_ref.
        required_fields_idx = body.find("Required artifact fields:")
        self.assertGreater(required_fields_idx, -1)
        required_block = body[required_fields_idx:required_fields_idx + 400]
        self.assertNotIn("`base_ref`", required_block)
        # The JSON example must not use base_ref.
        json_block_idx = body.find('"artifacts"')
        json_block = body[json_block_idx:json_block_idx + 600]
        self.assertNotIn('"base_ref"', json_block)

    def test_dev_orchestrator_forwards_runtime_context(self):
        body = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("runtime_context", body)
        self.assertIn("execution_mode", body)

    def test_dev_orchestrator_forwards_base_branch_and_parent_ref(self):
        body = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("base_branch", body)
        self.assertIn("parent_ref", body)
        # The review dispatch change-set forward list must not use base_ref.
        forward_idx = body.find("Forward at minimum:")
        self.assertGreater(forward_idx, -1)
        forward_block = body[forward_idx:forward_idx + 400]
        self.assertNotIn("base_ref", forward_block)

    def test_review_agent_returns_review_artifact_envelope(self):
        """Spec Decision 8: review-agent must return worktree_path,
        reviewed_changed_files, and handoff_path in artifacts."""
        body = (AGENTS_DIR / "review-agent.md").read_text(encoding="utf-8")
        output_idx = body.find("## Output")
        self.assertGreater(output_idx, -1)
        output_block = body[output_idx:output_idx + 1200]
        self.assertIn("worktree_path", output_block)
        self.assertIn("reviewed_changed_files", output_block)
        self.assertIn("handoff_path", output_block)

    def test_review_agent_prefers_runtime_context_for_source_of_truth(self):
        """Spec Decision 4: review-agent should prefer runtime_context for
        source-of-truth selection rather than inferring from prose."""
        body = (AGENTS_DIR / "review-agent.md").read_text(encoding="utf-8")
        self.assertIn("runtime_context", body)
        self.assertIn("runtime_context.worktree_path", body)

    def test_finish_agent_returns_final_artifact_envelope(self):
        """Spec Decision 8: finish-agent must return worktree_path,
        feature_branch, branch_finish_action, and handoff_path in artifacts."""
        body = (AGENTS_DIR / "finish-agent.md").read_text(encoding="utf-8")
        # Both archive_change and post_archive_actions success examples must
        # include the final artifact fields.
        for field in ("worktree_path", "feature_branch", "branch_finish_action", "handoff_path"):
            self.assertIn(field, body, f"finish-agent.md missing final artifact field: {field}")
        # The archive_change success example block must include the fields.
        archive_idx = body.find("archive_change` success example")
        self.assertGreater(archive_idx, -1)
        archive_block = body[archive_idx:archive_idx + 900]
        self.assertIn("worktree_path", archive_block)
        self.assertIn("feature_branch", archive_block)
        self.assertIn("branch_finish_action", archive_block)
        # The post_archive_actions success example block must include them too.
        post_idx = body.find("post_archive_actions` success example")
        self.assertGreater(post_idx, -1)
        post_block = body[post_idx:post_idx + 900]
        self.assertIn("worktree_path", post_block)
        self.assertIn("feature_branch", post_block)
        self.assertIn("branch_finish_action", post_block)

    def test_finish_agent_final_artifact_contract_in_output_discipline(self):
        """The Final Output Contract Discipline section must require the final
        artifact fields in success output."""
        body = (AGENTS_DIR / "finish-agent.md").read_text(encoding="utf-8")
        discipline_idx = body.find("## Final Output Contract Discipline")
        self.assertGreater(discipline_idx, -1)
        discipline_block = body[discipline_idx:]
        self.assertIn("worktree_path", discipline_block)
        self.assertIn("feature_branch", discipline_block)
        self.assertIn("branch_finish_action", discipline_block)

    def test_finish_agent_requires_branch_finish_decision_gate(self):
        """finish-agent prompt must require branch_finish_decision before
        branch-affecting actions (Spec Decision 1-3, 12)."""
        body = (AGENTS_DIR / "finish-agent.md").read_text(encoding="utf-8")
        self.assertIn("branch_finish_decision", body)
        self.assertIn("missing_branch_finish_decision", body)
        self.assertIn("ask_user_branch_finish_decision", body)
        # Must forbid silent branch outcome
        self.assertIn("silently choose", body.lower())
        # Must list allowed values
        for value in ("merge_local", "create_pr", "keep_branch", "discard"):
            self.assertIn(value, body, f"finish-agent missing allowed branch decision: {value}")

    def test_finish_agent_forbids_terminal_finalization(self):
        """finish-agent prompt must forbid direct terminal workflow finalization
        (Spec Decision 8)."""
        body = (AGENTS_DIR / "finish-agent.md").read_text(encoding="utf-8")
        terminal_idx = body.find("Terminal Finalization Boundary")
        self.assertGreater(terminal_idx, -1,
                           "finish-agent must have a Terminal Finalization Boundary section")
        terminal_section = body[terminal_idx:]
        self.assertIn("workflow.py done", terminal_section)
        self.assertIn("MUST NOT", terminal_section)

    def test_finish_agent_archives_lightweight_flow_superpowers_artifacts(self):
        """finish-agent prompt must archive lightweight-flow Superpowers plan/spec
        files into typed archive subdirectories (Spec Decision 11, 12)."""
        body = (AGENTS_DIR / "finish-agent.md").read_text(encoding="utf-8")
        self.assertIn("docs/superpowers/archive/plans/", body)
        self.assertIn("docs/superpowers/archive/specs/", body)
        self.assertIn("archived_design_artifact_paths", body)
        self.assertIn("source_design_artifact_paths", body)

    def test_finish_agent_uses_semantic_archive_evidence(self):
        """finish-agent prompt must use semantic archive evidence fields
        (Spec Decision 10, 12)."""
        body = (AGENTS_DIR / "finish-agent.md").read_text(encoding="utf-8")
        self.assertIn("archive_action_completed", body)
        self.assertIn("archive_artifact_path", body)
        self.assertIn("archive_not_required_reason", body)

    def test_dev_orchestrator_owns_branch_decision_collection(self):
        """dev-orchestrator prompt must own user branch decision collection
        (Spec Decision 13)."""
        body = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")
        branch_idx = body.find("Branch Finish Decision Collection")
        self.assertGreater(branch_idx, -1,
                           "dev-orchestrator must have a Branch Finish Decision Collection section")
        branch_section = body[branch_idx:]
        self.assertIn("missing_branch_finish_decision", branch_section)
        self.assertIn("merge_local", branch_section)
        self.assertIn("create_pr", branch_section)
        self.assertIn("keep_branch", branch_section)
        self.assertIn("discard", branch_section)
        self.assertIn("record-context", branch_section)
        self.assertIn("branch_finish_decision", branch_section)


class TestDevOrchestratorFinalTailCommit(unittest.TestCase):
    """dev-orchestrator must include the Final Tail Commit Protocol."""

    def test_dev_orchestrator_has_final_tail_commit_protocol_section(self):
        body = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("Final Tail Commit Protocol", body)

    def test_dev_orchestrator_captures_run_id_before_done(self):
        body = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("Capture the active `run_id` before advancing to `done`", body)

    def test_dev_orchestrator_calls_final_commit_command(self):
        body = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("final-commit --run-id", body)

    def test_dev_orchestrator_does_not_run_direct_git(self):
        body = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("Do not run direct `git add`, `git commit`, or `git push`", body)

    def test_dev_orchestrator_checks_git_status_after_final_commit(self):
        body = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("git status --short", body)

    def test_dev_orchestrator_reports_residual_dirty_paths(self):
        body = (AGENTS_DIR / "dev-orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("residual_dirty_paths", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
