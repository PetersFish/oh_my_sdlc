---
id: RM-EVAL-004
title: "Promptfoo Eval 加速：并发 + 增量运行"
status: ready
stage: v2
priority: p0
order: 40
depends_on: []
openspec_change: evalops-concurrency-incremental-eval
created_at: 2026-06-16
started_at: null
completed_at: null
---

# Goal

让 `sdlc-evalops` 的 Promptfoo golden eval 从全量串行变为可配置并发 + 可跑新增/失败用例，降低常规验证成本。

# Problem Context

当前 Promptfoo golden eval 在 case 数量增长后仍以全量串行方式运行，单次验证可能超过 10 分钟，导致常规迭代和回归验证效率很低。EvalOps 需要保留最终全量门禁能力，同时为日常开发提供更快的并发运行和增量重跑路径。

# Scope

## In

- 在 `.ai/evals/model-matrix.yaml` 的 `run_policy` 增加 `max_concurrency`、`max_parallel_models`。
- `run-promptfoo-eval.py` 支持读取并发配置并传给 `promptfoo eval --max-concurrency N`。
- `run-eval-matrix.py` 支持 `concurrent.futures` 并行跑多个 model entry（当 `run_policy.parallel: true`）。
- 支持 `--only-new`：只跑上次全量跑之后新增/修改的 golden cases。
- 支持 `--only-failed --failed-from latest|full`：可重跑最近一次运行失败的 cases，或最近一次全量运行失败的 cases。
- 新增本地 run index（如 `reports/run-index.json`），记录 case 运行状态和时间戳。
- 报告 summary 中标注本次是 `full`、`only-new` 还是 `only-failed`。
- 新模板和 live `model-matrix.yaml` 默认使用适度加速：`max_concurrency: 3`、`parallel: true`、`max_parallel_models: 2`。
- 兼容旧配置：缺少新增 `run_policy` 字段时仍可运行，并使用安全 fallback。

## Out

- 不做 source-level 影响面分析。
- 不做跨 target 自动选择 affected cases。
- 不做 CI 集成。
- 不做 `promptfoo` 工具本身的修改。

# Design Notes

## Key Decisions

- `reports/run-index.json` 作为本地审计状态，记录每次运行的 mode（`full`、`only-new`、`only-failed`）、Git baseline、case 文件状态、失败集合和报告路径。
- `--only-new` 使用 Git diff，并以上一次成功完成的 full run 在 run index 中记录的 baseline 为比较基准；它只选择相对该 baseline 新增或内容发生变化的 golden case 文件对应的 case。
- `--only-failed` 支持 `--failed-from latest|full`，分别面向快速 retry 和回到最近全量门禁失败集合的场景。
- Promptfoo case 级并发由 `run_policy.max_concurrency` 控制；矩阵 model 级并发由 `run_policy.parallel` 和 `run_policy.max_parallel_models` 控制。
- 默认配置从纯串行改为适度加速：case 并发 3、model 并行开启、最多 2 个 model entry 并行，避免一次性放大到不可控的 provider 压力。

## Tradeoffs

- 选择 Git diff 而不是 mtime，是为了避免 checkout、复制文件、格式化工具造成的时间戳噪声；代价是运行环境需要可用的 Git baseline。
- 选择 last full run baseline 而不是当前 merge-base，是为了让增量 eval 语义绑定到“上次已完整验证”的状态，而不是绑定到分支拓扑。
- 选择 `ThreadPoolExecutor` 处理 model 级并行，因为每个 model run 主要是外部 `promptfoo` 子进程和网络 I/O；不引入更重的进程池抽象。

## Initial Approach

先扩展 runner 配置读取和报告元数据，再引入 run index，最后把 single-target runner 与 matrix runner 的选择逻辑对齐。实现应保持 Promptfoo exports 仍为派生产物，canonical case YAML 不被运行过程改写。

## Open Questions

- 当没有可用 Git baseline（例如首次运行或非 Git 环境）时，`--only-new` 应拒绝运行并提示先执行 full run，还是自动退化为 full run？

# Acceptance Criteria

- `python run-promptfoo-eval.py <target-id>` 默认仍跑全部 golden cases，并在新配置下使用 `max_concurrency: 3`。
- 配置 `max_concurrency: 5` 后，Promptfoo 命令使用 `--max-concurrency 5`。
- `--only-new` 根据 run index 中最近 full run 的 Git baseline，只导出并运行新增/修改过的 golden cases。
- `--only-failed --failed-from latest` 只运行最近一次运行失败的 cases。
- `--only-failed --failed-from full` 只运行最近一次 full run 失败的 cases。
- 每次运行后更新 run index。
- 报告路径仍写入 `.ai/evals/targets/<target-id>/reports/<run-id>/`。
- 无新 case 或失败 case 时，脚本清晰退出并说明无需运行。
- 矩阵 runner 在 `parallel: true` 时通过 `ThreadPoolExecutor` 并发执行多 model entry，并遵守 `max_parallel_models: 2` 默认上限。

# Promotion Notes

边界清晰、风险可控：主要修改 runner 脚本和 model-matrix 配置，不进入 source-level 影响面分析。RM-EVAL-003 已取消，本项不再依赖它；隐藏目录发现规则已由仓库协作规则兜底。

# Completion Notes
