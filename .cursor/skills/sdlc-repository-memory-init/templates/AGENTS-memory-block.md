## Repository Memory

If `.ai/memory/index.json` exists and the task involves planning, editing, reviewing, or continuing work in this repository, load relevant repository memory first using `sdlc-repository-memory-load`.

For existing repositories, `.ai-memory/index.json` is a supported legacy fallback when `.ai/memory/index.json` does not exist.

Do not load `.ai/memory/sync-history/`, `.ai/memory/sessions/`, `.ai/memory/snapshots/`, `.ai/memory/tmp/`, `.ai/memory/cache/`, or `.ai/memory/review-queue.json` by default.
