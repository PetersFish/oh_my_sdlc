---
id: RM-EVAL-004
title: "Promptfoo Eval 加速：并发 + 增量运行"
status: planned
stage: v2
priority: p0
order: 40
depends_on:
  - RM-EVAL-003
openspec_change: null
created_at: 2026-06-16
started_at: null
completed_at: null
patches: []
---

# Goal

让 `sdlc-evalops` 的 Promptfoo golden eval 从全量串行变为可配置并发 + 可跑新增/失败用例，降低常规验证成本。

# Scope

## In

- 在 `.ai/evals/model-matrix.yaml` 的 `run_policy` 增加 `max_concurrency`、`max_parallel_models`。
- `run-promptfoo-eval.py` 支持读取并发配置并传给 `promptfoo eval --max-concurrency N`。
- `run-eval-matrix.py` 支持 `concurrent.futures` 并行跑多个 model entry（当 `run_policy.parallel: true`）。
- 支持 `--only-new`：只跑上次全量跑之后新增/修改的 golden cases。
- 支持 `--only-failed`：只重跑上次失败的 cases。
- 新增本地 run index（如 `reports/run-index.json`），记录 case 运行状态和时间戳。
- 报告 summary 中标注本次是 `full`、`only-new` 还是 `only-failed`。
- 默认行为不破坏：不配置时保持现有串行全量跑。

## Out

- 不做 source-level 影响面分析。
- 不做跨 target 自动选择 affected cases。
- 不做 CI 集成。
- 不做 `promptfoo` 工具本身的修改。

# Acceptance Criteria

- 不配置时，`python run-promptfoo-eval.py <target-id>` 仍跑全部 golden cases。
- 配置 `max_concurrency: 5` 后，Promptfoo 命令使用 `--max-concurrency 5`。
- `--only-new` 只导出并运行新增/修改过的 golden cases。
- `--only-failed` 只运行上次失败的 cases。
- 每次运行后更新 run index。
- 报告路径仍写入 `.ai/evals/targets/<target-id>/reports/<run-id>/`。
- 无新 case 或失败 case 时，脚本清晰退出并说明无需运行。
- 矩阵 runner 在 `parallel: true` 时可通过 `ThreadPoolExecutor` 并发执行多 model entry。

# Promotion Notes

边界清晰、风险可控：主要修改 runner 脚本和 model-matrix 配置。适合在 RM-EVAL-003（隐藏目录发现加固）完成后再推进，因为需要准确判断已有 eval 状态。

# Completion Notes

