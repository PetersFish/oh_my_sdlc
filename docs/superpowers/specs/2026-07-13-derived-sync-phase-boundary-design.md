# Derived Artifact Sync Phase Boundary

## Context

During `apply_change`, `implement-agent` ran `sync_derived_artifacts.py --fix` and
`install_skill.py` to synchronize canonical source changes to distributed copies
(`.opencode/`, `.claude/`, `.cursor/`). This produced 100+ extra dirty files
(`.skill-install.json` timestamp churn, distributed agent/skill copies, template
copies) in the live worktree. `review-agent` then blocked repeatedly with
`review_change_set_mismatch` because the structured `changed_files` list could
not reconcile with the much larger live Git state.

## Goals

- `implement-agent` never produces derived-artifact write churn during `apply_change`.
- `finish-agent` owns write-producing derived-artifact sync as part of post-review cleanup.
- `install_skill.py` is a no-op (preserves existing `.skill-install.json` byte-for-byte)
  when the target payload hash is unchanged.
- Review scope stays bounded to source/test/template canonical changes.

## Non-Goals

- No changes to `sync_derived_artifacts.py --check` (read-only validation).
- No changes to `sync_templates.py` live→canonical sync logic.
- No changes to `setup_agents.py` activation logic.
- No new workflow phases or runtime state.

## Decisions

### 1. implement-agent Must Not Run Derived Sync (Check or Fix)

During `apply_change`, `implement-agent`:

- MUST NOT run `sync_derived_artifacts.py --fix`.
- MUST NOT run `setup_agents.py --force`.
- MUST NOT run `install_skill.py`.
- MUST NOT run `sync_derived_artifacts.py --check` or `sync_templates.py --check`.

Modifying canonical `agents/`, `skills/`, or workflow templates always
produces distributed-copy drift — this is expected, not an error. Running
`--check` would always report drift and serve no purpose during
`apply_change`. Drift detection and repair is owned by `finish-agent`
during `post_archive_actions`.

### 2. finish-agent Owns Write-Producing Derived Sync

`finish-agent` already has a "Derived Artifact Sync" section. The contract is
strengthened:

- After review passes and source changes are accepted, `finish-agent` runs
  `sync_derived_artifacts.py --fix` (incremental or full as appropriate).
- Generated derived-artifact changes are recorded as finish cleanup evidence,
  not as implementation change-set evidence.
- `finish-agent` must re-run `--check` after `--fix` and block until clean.

### 3. install_skill.py No-Op on Unchanged Payload

`install_skill.py` currently always `shutil.rmtree` + `shutil.copytree` +
writes `.skill-install.json` with a fresh `installed_at` timestamp. This causes
timestamp churn even when nothing changed.

New behavior:

- Before installing, compute the source payload hash.
- Load the existing target `.skill-install.json` (if present) and compare
  `payload_hash`.
- If `payload_hash` matches AND the target file list matches the source file
  list: skip `rmtree`/`copytree`/metadata write entirely. Print the existing
  metadata. Return 0.
- If `payload_hash` differs OR target is missing OR file list differs: install
  normally (rmtree, copytree, write fresh metadata).

This ensures `install_skill.py` is idempotent: running it twice with no source
change produces zero file modifications.

### 4. Permission Rules

`implement-agent` bash permissions: add `sync_derived_artifacts.py --fix` to the
deny list (or remove it from the allow pattern so only `--check` is allowed).

`finish-agent` bash permissions: already allows `python3 scripts/*` which covers
`sync_derived_artifacts.py --fix`. No change needed.

## Affected Areas

- `agents/implement-agent.md` — Derived Sync Restriction section + permission rules
- `agents/finish-agent.md` — Derived Artifact Sync section (strengthen wording)
- `skills/meta-skill-lifecycle-governance/scripts/install_skill.py` — no-op logic
- `skills/meta-skill-lifecycle-governance/scripts/lifecycle_utils.py` — no change needed
- `tests/test_wrapper_contracts.py` — implement/finish agent contract tests
- `tests/test_install_skill.py` (new or existing) — no-op behavior tests
- Distributed copies under `.opencode/agents/`, `.claude/agents/`, `.cursor/agents/`
- Distributed copies under `.opencode/skills/meta-skill-lifecycle-governance/scripts/`

## Acceptance Criteria

- `implement-agent` prompt explicitly forbids `--fix`, `--force`, and
  `install_skill.py` during `apply_change`.
- `finish-agent` prompt explicitly owns write-producing derived sync.
- `install_skill.py` with unchanged payload produces zero file modifications
  (`.skill-install.json` byte-identical, target tree untouched).
- `install_skill.py` with changed payload installs normally and writes fresh
  metadata.
- Contract tests assert the permission/forbidden-action rules.
- Existing tests continue to pass.