# skill-taxonomy

A new `skills/TAXONOMY.md` document that defines skill prefix semantics, type classification, and trigger conflict resolution priorities.

## ADDED Requirements

### Requirement: TAXONOMY.md exists in skills directory

The file `skills/TAXONOMY.md` SHALL exist at the top level of the skills directory and SHALL contain human-readable documentation of the skill classification system.

#### Scenario: File exists
- **WHEN** checking `skills/TAXONOMY.md`
- **THEN** the file exists and contains structured markdown content

### Requirement: TAXONOMY.md documents prefix semantics

TAXONOMY.md SHALL include a table or section mapping each domain prefix to its semantic meaning:
- `qa-*`: instant Q&A / coaching skills (no durable artifacts)
- `research-*`: durable local research topic lifecycle management
- `sdlc-*`: software development lifecycle skills (memory, OpenSpec gates)
- `transform-*`: atomic content transformation / rendering skills
- `study-*`: composite skills that orchestrate learning note generation
- `media-*`: media reading, routing, and OCR skills
- `integration-*`: external service integration skills
- `ops-*`: operational / backup skills
- `meta-skill-*`: skills about managing skills themselves

#### Scenario: All prefixes documented
- **WHEN** reading TAXONOMY.md
- **THEN** all 9 prefix groups are listed with their semantic meanings

### Requirement: TAXONOMY.md classifies skill types

TAXONOMY.md SHALL classify skills into types: `atomic` (single-purpose render/transform), `composite` (orchestrates multiple atomic skills), `adapter` (thin wrapper delegating to core), and `qa` (conversational coaching).

#### Scenario: Type classification present
- **WHEN** reading TAXONOMY.md
- **THEN** at least atomic, composite, adapter, and qa types are described

### Requirement: TAXONOMY.md defines trigger conflict priorities

TAXONOMY.md SHALL document the conflict resolution order when multiple skills could match a user request: (1) explicit user skill name wins, (2) adapter-gate skills before core skills, (3) composite orchestrators before atomic renderers, (4) specific-domain skills before general-purpose skills.

#### Scenario: Priority rules documented
- **WHEN** reading TAXONOMY.md
- **THEN** a section describes which skill should win when trigger descriptions overlap
