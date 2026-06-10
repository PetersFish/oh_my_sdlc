# Topic Protocol

This protocol defines the local research filesystem. The filesystem is the source of truth; the skill only coordinates changes.

## Directory Lifecycle

```text
research/
  README.md
  wishlist/
    <topic-slug>/
  running/
    <topic-slug>/
  done/
    <topic-slug>/
  wiki/
    <concept>.md
```

| Directory | Responsibility | Notes |
|---|---|---|
| `wishlist/` | Planned research | Early topics, drafts, or requests that need refinement. |
| `running/` | Active research | Topics currently being refined, run, or rerun. |
| `done/` | Completed phase | Current phase is complete; future reruns remain allowed. |
| `wiki/` | Reusable knowledge | Cross-topic concepts, not task lifecycle state. |

## Topic Root Files

| File | Responsibility |
|---|---|
| `request.md` | Current research request, including refined scope and future rerun guidance. |
| `solution.md` | Current best synthesis derived from the latest accepted run. |
| `meta.yaml` | Machine-readable status, type, tags, run pointers, and rerun hints. |
| `dialogue.md` | Key decisions, clarifications, and rationale that affected request or solution. |
| `sources.md` | Cumulative source index for the topic. |
| `runs/<timestamp>/` | Immutable snapshot for each formal run. |

## Run Snapshot Files

Each formal `run` or `rerun` creates a new timestamped directory:

```text
runs/YYYY-MM-DD-HHmm/
  request.md
  solution.md
  sources.md
  notes.md
  review.md
```

| File | Responsibility |
|---|---|
| `request.md` | Frozen copy of the request used for that run. |
| `solution.md` | Output produced by that run. |
| `sources.md` | Sources used during that run only. |
| `notes.md` | Intermediate findings, rejected options, reasoning notes. |
| `review.md` | User feedback, self-checks, and follow-up quality notes. |

## State Movement

- `new` creates under `wishlist/`.
- `start` moves the whole `wishlist/<topic>/` directory to `running/<topic>/`.
- `archive` moves the whole `running/<topic>/` directory to `done/<topic>/` and updates `meta.yaml` to `status: done`.
- `rerun` on a `done` topic first proposes moving it back to `running/`; ask for confirmation before the move.
- After any lifecycle move, remove now-empty source directories so the old lifecycle path does not linger.
- Verify the source path is gone after the move; if it remains, fix cleanup before claiming the operation is complete.
- Never silently create or mutate a topic in a lifecycle directory that conflicts with `meta.yaml` status; fix status and location together.

## Immutability

- Do not overwrite previous `runs/<timestamp>/` directories.
- Do not edit historical run files as a normal operation.
- If a previous conclusion needs updating, create a new run and update the topic root `solution.md` to point at the new run.
