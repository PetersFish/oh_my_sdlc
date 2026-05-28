# Action Dispatch

Map user intent to the closest research action. The user does not need to memorize subcommands.

## Dispatch Table

| User intent | Action |
|---|---|
| "初始化 research 目录", "set up research workflow" | `init` |
| "帮我调研 X", "open a research topic for X", "research X and save it" | `new`, then `refine` |
| "优化这个 request", "这个 request 能不能改得更适合模型执行" | `refine` |
| "基于这个 request 开始做", "start this topic" | `start`, then usually `run` |
| "执行调研", "run this research", "生成 solution" | `run` |
| "重新调研", "rerun with latest info", "这个 done 课题再调研一次" | `rerun`; if in `done/`, confirm move to `running/` first |
| "归档", "当前轮结束", "mark done" | `archive` with confirmation |
| "现在有哪些课题", "看一下状态", "status" | `status` |
| "提炼长期知识", "生成 wiki 候选", "extract reusable knowledge" | `extract-wiki` candidate generation |
| "把这次新增要求同步到后续 rerun" | Request Drift Sync; confirm before overwriting `request.md` |

## Near Misses

Do not use this workflow for:

- One-off factual questions that do not need durable topic files.
- Simple translation, rewriting, or summarization unrelated to a research topic.
- Code-only implementation or debugging tasks.
- Exam review or course practice that should use a course-specific skill.
- Requests that only sync existing notes to Notion.

If the request is ambiguous, ask one short question: whether the user wants a durable local research topic under `research/` or just a direct answer.

## Action Sequencing

- `new` with a brief topic normally leads to `refine`, not an immediate `run`.
- `start` can be followed by `run` when the request is already complete.
- `run` must create a timestamped snapshot before updating root `solution.md`.
- `rerun` always creates a new snapshot and compares against previous runs when useful.
- `extract-wiki` produces candidates first; writing wiki pages is a separate explicit action.

## Confirmation Language

Use concise confirmation prompts for high-impact actions:

- `request.md`: "I will overwrite `<path>/request.md` with the refined request and log the rationale in `dialogue.md`. Proceed?"
- Archive: "I will move `<topic>` from `running/` to `done/` and update `meta.yaml`. Proceed?"
- Done rerun: "I will move `<topic>` from `done/` back to `running/` and create a new immutable run. Proceed?"
- Wiki write: "I will write these candidates into `research/wiki/`. Proceed?"
