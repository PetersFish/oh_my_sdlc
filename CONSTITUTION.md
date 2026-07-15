# Project Constitution

## 1. Purpose

This document defines the highest-level architectural and engineering principles of this repository.

The project SHALL use a hybrid model:

> LLMs perform semantic reasoning and implementation.  
> A deterministic kernel protects workflow integrity.

The project SHALL avoid both extremes:

- relying entirely on prompt compliance;
- encoding every reasoning path into a deterministic workflow engine.

---

## 2. Authority

When instructions conflict, use this precedence:

1. Explicit user requirements
2. `CONSTITUTION.md`
3. Accepted specifications and designs
4. Root `AGENTS.md`
5. Agent- and skill-specific instructions
6. Local implementation conventions

Lower-level instructions SHALL NOT weaken constitutional invariants without an explicit amendment.

---

## 3. Separation of Responsibilities

### LLM responsibilities

LLMs are responsible for semantic decisions, including:

- understanding requirements;
- deciding whether and how to decompose work;
- choosing implementation and recovery strategies;
- writing and reviewing code;
- interpreting failures and review findings;
- deciding when to retry, replan, escalate, or request human input.

### Deterministic kernel responsibilities

The deterministic kernel is responsible for:

- validating state and evidence;
- enforcing stable invariants;
- blocking invalid transitions;
- preserving recoverable progress;
- reporting missing, stale, unrelated, or inconsistent evidence;
- exposing allowed and forbidden next actions;
- providing structured recovery guidance.

The kernel SHALL NOT replace planning, architecture, implementation, review judgment, or semantic diagnosis.

---

## 4. Guardrails, Not Autopilot

The preferred execution loop is:

1. The LLM selects and performs an action.
2. The kernel validates the result.
3. Valid results may advance.
4. Invalid results are blocked with structured diagnostics.
5. The LLM chooses the concrete repair.

Kernel diagnostics SHOULD include:

- reason code;
- violated invariant;
- expected and observed facts;
- relevant identities and artifact paths;
- allowed actions;
- forbidden actions;
- whether human judgment is required.

The kernel SHOULD report constraints and facts, not prescribe code patches or architectural answers.

---

## 5. Encode Only Stable Invariants

Deterministic code SHALL encode only rules that are:

- mechanically verifiable;
- stable across models and tasks;
- important enough to block or constrain execution.

Appropriate invariants include:

- evidence belongs to the current run and dispatch;
- required implementation and review evidence exists;
- unresolved blocking findings prevent completion;
- completed work is not silently re-dispatched;
- workflow completion requires all mandatory gates;
- durable state remains valid and recoverable;
- canonical and derived artifacts do not drift.

A new runtime rule MUST NOT be added merely because one agent once made a mistake.

Before adding a rule, verify that clearer instructions, better artifacts, or review guidance would not solve the problem more simply.

---

## 6. Keep Semantic Decisions Outside the Kernel

Unless a stable mechanical rule exists, the kernel SHALL NOT decide:

- whether work needs slicing;
- how slices are defined;
- whether a blocker is caused by context, model capability, permissions, planning, or implementation;
- whether to retry, upgrade the model, replan, split work, or escalate;
- how review findings should be interpreted or repaired;
- whether architecture, scope, or test coverage is sufficient.

The kernel may expose evidence for these decisions but SHALL defer judgment to an LLM or human.

---

## 7. Minimize Durable State

Persist only authoritative facts required for integrity, recovery, or audit, such as:

- stable identifiers;
- lifecycle status;
- attempt and dispatch identity;
- base and head revisions;
- artifact and evidence references;
- explicit decisions and blockers.

Prefer deriving values such as:

- readiness;
- next task;
- aggregate completion;
- dispatchability;
- active-item summaries.

The same fact SHOULD NOT be independently mutable in multiple locations.

When duplication is unavoidable, one source MUST be authoritative and consistency MUST be verified.

---

## 8. Keep State Vocabulary Small

Prefer a compact lifecycle such as:

- `pending`
- `running`
- `blocked`
- `passed`
- `cancelled`

State describes lifecycle position.

Evidence, findings, and reason codes describe why the system is in that state.

Do not create a new state for every failure cause.

---

## 9. Evidence Must Have Provenance

Evidence SHALL have clear execution provenance, preferably based on:

- run identity;
- phase identity;
- dispatch identity.

Task, change, or slice identifiers may be metadata but SHOULD NOT be overloaded as the sole evidence namespace.

The system SHALL reject evidence that is:

- from another run or dispatch;
- associated with unrelated work;
- stale;
- missing required provenance;
- only an unsupported assertion where executable evidence is required.

Identity fallback rules SHALL be minimized, explicit, and tested.

---

## 10. Recovery Guidance

Recovery behavior SHOULD distinguish three classes.

### Mechanical failures

The kernel may provide a direct corrective action for:

- malformed state;
- missing fields;
- unknown identifiers;
- illegal transitions;
- missing artifacts;
- stale dispatch tokens.

### Workflow failures

The kernel should provide valid recovery categories, such as:

- dispatch review;
- dispatch remediation;
- restore evidence;
- resume blocked work;
- repeat verification;
- request human judgment.

### Semantic failures

The kernel should report facts and defer judgment for:

- ambiguous requirements;
- architectural disagreement;
- disputed review findings;
- inadequate decomposition;
- scope conflicts;
- uncertain test adequacy.

Retries SHALL NOT repeat the same action with unchanged context, model capability, permissions, and constraints.

---

## 11. Progressive Determinism

New workflow behavior SHOULD begin with the least complex safe mechanism:

1. clear instruction;
2. structured agent output;
3. durable artifact;
4. deterministic validation;
5. blocking invariant;
6. additional state or transitions only when proven necessary.

Do not begin with a generalized state machine when a prompt, artifact, validator, or review gate is sufficient.

---

## 12. Complexity Budget

Changes that add any of the following MUST justify their cost:

- lifecycle states;
- transitions;
- evidence namespaces;
- identifier fallbacks;
- persisted derived fields;
- recovery branches;
- phase-specific hard-coded rules;
- synchronization copies;
- compatibility modes.

The design MUST explain:

- which invariant is protected;
- why simpler mechanisms are insufficient;
- how state-space growth remains bounded;
- how the behavior is tested;
- what existing complexity can be removed.

If implementation complexity grows faster than integrity value, simplify the design.

---

## 13. Sequential Before Parallel

Sequential task or slice execution is the default.

Parallel execution SHALL NOT be introduced until the project has stable:

- sequential execution;
- workspace isolation;
- dependency semantics;
- conflict detection;
- remediation ownership;
- aggregate verification;
- partial-failure recovery.

Future parallelism is not sufficient justification for present-day scheduler complexity.

---

## 14. Durable Handoffs and Git Evidence

Large briefs, reports, review packages, findings, and test evidence SHOULD be stored in files rather than repeatedly embedded in prompts or runtime state.

Git SHOULD be treated as an authoritative implementation record.

Where applicable, record:

- base revision;
- head revision;
- reviewed revision range;
- accepted commits.

Review evidence SHALL cover the complete relevant revision range.

Durable progress SHOULD be reconcilable with Git after context loss or session restart.

---

## 15. Review Boundaries

Implementation self-review does not replace independent review.

The workflow SHOULD distinguish:

- task- or slice-scoped review;
- aggregate whole-change review.

The kernel may enforce the existence and required verdicts of review gates.

It SHALL NOT decide substantive code quality, architecture, or specification correctness.

---

## 16. Model Independence

Critical workflow integrity SHALL NOT depend on one model remembering every instruction.

Model independence should come from:

- explicit task briefs;
- stable result contracts;
- evidence provenance;
- deterministic validation;
- durable progress;
- bounded permissions;
- independent review;
- structured recovery diagnostics.

The system SHALL assume that any model may omit steps, lose context, repeat work, or attempt invalid transitions.

These failures should be visible and recoverable, not prevented by encoding all model behavior.

---

## 17. Testing Principles

Kernel tests SHALL focus on observable invariants and public contracts.

They SHOULD verify that:

- valid state and evidence are accepted;
- invalid or unrelated evidence is rejected;
- illegal transitions are blocked;
- diagnostics identify the violated invariant;
- recovery preserves durable progress;
- derived state remains consistent;
- canonical and distributed artifacts do not drift.

Tests SHOULD NOT lock in incidental implementation details or agent reasoning strategies.

Disproportionate test growth for a small capability is a signal to review the abstraction.

---

## 18. Required Design Questions

Before changing workflow runtime, state, dispatch, evidence, recovery, slicing, or agent contracts, answer:

1. Is this a semantic decision or a mechanical invariant?
2. Must failure block progression?
3. Could clearer instructions or artifacts solve it?
4. What is the authoritative source of truth?
5. Is new state derived from existing facts?
6. Could this duplicate a mutable fact?
7. What diagnostic will the LLM receive?
8. Does the diagnostic report facts or prescribe implementation?
9. Does the design add speculative concurrency or flexibility?
10. What can be removed instead of added?

A design that cannot answer these clearly SHOULD be simplified before implementation.

---

## 19. Constitutional Anti-Patterns

Avoid:

- encoding every agent mistake as a runtime rule;
- adding a state for every failure cause;
- persisting reliably derivable values;
- mixing run, change, slice, task, and default identities;
- accepting evidence without dispatch provenance;
- making the kernel decide semantic correctness;
- retrying without changing failure conditions;
- designing parallel scheduling before sequential execution is stable;
- duplicating contracts without one authoritative source;
- treating more deterministic code as automatically more reliable.

---

## 20. Final Principle

> Use deterministic mechanisms to protect truth, identity, evidence, progression, and recovery.  
> Use LLM reasoning to understand, design, implement, diagnose, and adapt.

The deterministic kernel is a guardrail, not a substitute for intelligence.

The LLM is autonomous within the guardrails, but cannot redefine them during execution.
