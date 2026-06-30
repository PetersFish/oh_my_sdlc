# Subagent Permissions And Tooling Design Review Plan

**Scope:** Review and strengthen `docs/manual/design/subagent_permissions_and_tooling_design.md` for goals 1-3 only.

## Objective
Refine the proposal into an implementation-ready direction that reduces meaningless authorization interruptions, preserves least privilege through role-bounded prompt/test constraints, and defines executable MUST-first tool usage rules without any bash exploration fallback.

## Review Conclusion
The proposal is ready to move forward once tightened in four places:
1. Separate goals 1-3 from gate-quality and legacy-cleanup content so the change stays bounded.
2. Make non-implementation-agent write boundaries explicit under the chosen model: `edit: allow` plus prompt/test constraints.
3. Rewrite the Tool Usage Policy as decision rules with required exceptions and no bash exploration fallback.
4. Define remaining read-only git permissions as observational only, not as a substitute exploration path.

## Recommended Design Refinements

### 1. Hard-split in-scope vs out-of-scope content
Keep this design focused on:
- permission/frontmatter updates for relevant agents
- unified tool-usage policy
- role-specific tool constraints

Move or clearly mark as deferred:
- gate-strengthening details for `test-agent`, `review-agent`, `finish-agent`
- legacy cleanup such as `_migrate_legacy_artifacts`

Recommended document change:
- add a short “This iteration implements only goals 1-3” statement near the top
- convert sections IV and V into “follow-up proposal / deferred work” notes or remove them from this execution plan

### 2. Make least-privilege model explicit under `edit: allow`
Because the chosen path is `edit: allow` for non-implementation agents, the design should explicitly state:
- `plan-agent`, `test-agent`, `review-agent`, `finish-agent` may write workflow artifacts only
- they must not modify source, tests, prompts outside their own governed artifact scope, configs, or user docs
- this boundary is enforced by prompt contract and prompt tests, not runtime path-scoped permissions

Recommended executable wording:
- “`edit: allow` exists solely because workflow artifacts require writes; it is not delegation of general repository editing authority.”

### 3. Rewrite Tool Usage Policy into executable rules
The current policy should be converted from broad guidance into rule tables per need type.

Recommended rule shape:
- **Repository/code understanding:** MUST load `sdlc-repository-memory-load` first when the task depends on prior repo decisions/history; MUST prefer `codegraph_*` for structural code questions; MAY skip memory/codegraph for doc-only or single-known-file artifact work.
- **File discovery / text lookup / file reading:** MUST prefer `Glob` / `Grep` / `Read`; shell search commands are not an approved fallback path.
- **Library/framework/API docs:** MUST use `context7`.
- **Current external practice / recent changes:** MUST use `tavily-search`.
- **Large outputs:** SHOULD use `headroom` before carrying logs/results forward.
- **Skill usage:** MUST invoke an applicable skill before acting.

Required exception/fallback semantics:
- if the task is doc-only or artifact-only and does not require repo structure understanding, memory/codegraph are not mandatory
- if a preferred tool is unavailable, unindexed, or demonstrably insufficient, the agent must stop and return a blocker or route for remediation rather than degrading to bash exploration
- observational git commands do not become a substitute for file/code discovery

### 4. Normalize the observational git policy
The approved shell model is now observational git only.

Recommended whitelist intent:
- allow only read-only git inspection relevant to the role: `git status`, `git diff`, `git log`, and where justified `git branch`, `git worktree`, `git check-ignore`
- define these as workflow-state or repository-state inspection only
- explicitly forbid treating git or shell as a general codebase exploration channel

Recommended refinement:
- define which roles get which git commands instead of copying one broad set everywhere
- mirror that intent in frontmatter and prompt-contract tests
- explicitly keep destructive git/shell commands denied

### 5. Make enforcement and verification planning concrete
For goals 1-3, planning-level verification should cover:
- frontmatter permission assertions per agent
- prompt text assertions for write-boundary language
- prompt text assertions for MUST-first tool policy and explicit no-bash-degradation language
- negative tests ensuring destructive git/shell commands remain blocked
- scenario-level review checklist proving common paths no longer hit meaningless authorization prompts and do not silently fall back to bash exploration

## Suggested Implementation Order
1. Trim the design to goals 1-3 only.
2. Finalize per-agent permission matrix and role-specific observational git allowances.
3. Add the unified Tool Usage Policy with exception/remediation language and explicit no-bash-degradation rule.
4. Add role-specific write-boundary language for non-implementation agents.
5. Define prompt-contract test expectations for permissions, tool rules, denied commands, and blocker behavior when preferred tools are unavailable.
6. Reserve gate-quality strengthening and legacy cleanup for a follow-up change.

## Focused Verification Strategy
- `tests/test_wrapper_contracts.py`: frontmatter and prompt contract assertions
- agent-by-agent prompt review against a checklist:
  - artifact-only write boundary present
  - MUST-first tools present
  - exception/remediation language present
  - no bash exploration fallback allowed
  - destructive commands remain blocked
- manual scenario review for:
  - `plan-agent` writing plan/handoff without edit interruption
  - `implement-agent` using observational git inspection without reintroducing shell-heavy exploration
  - `test/review/finish` writing artifacts without implying general code-edit authority
  - unavailable-tool cases returning blockers/remediation rather than degrading to bash exploration

## Non-Blocking Risks
- Prompt-only write boundaries still rely on prompt discipline; accidental drift remains possible without strong tests.
- No-bash-degradation rules may surface more blockers when high-level tools are unavailable; this is acceptable but should be expected.
- Too many MUST rules can create prompt bloat; exception language must stay short and reusable.

## Assumptions
- Canonical changes will target `agents/*.md` first, then be distributed to `.opencode/agents/`, `.claude/agents/`, and `.cursor/agents/`.
- `tests/test_wrapper_contracts.py` is the primary static enforcement point for this iteration.
- Gate-quality strengthening and legacy cleanup remain intentionally out of scope for this approval cycle.
