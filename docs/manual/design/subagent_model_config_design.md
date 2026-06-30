# 背景

当前 SDLC agent 体系已经拆分为 `dev-orchestrator`、`plan-agent`、`implement-agent`、`test-agent`、`review-agent`、`finish-agent` 等角色，但这些 agent 默认跟随同一个 LLM 模型运行。从 token 经济和任务适配角度看，这不合理：

1. `implement-agent` 和 `finish-agent` 是高 token 消耗角色，更适合使用中等成本模型，例如 `deepseek-v4-pro`。
2. `dev-orchestrator`、`plan-agent`、`review-agent` 更依赖复杂判断、设计理解和质量把关，更适合使用高智能模型，例如 `gpt-5.5`。
3. `test-agent` 需要独立验证能力，但不一定需要最高档模型，可以使用高档但略低成本的模型，例如 `gpt-5.4`。
4. 后续模型升级时，用户希望可以集中调整，而不是逐个修改 agent prompt 或运行配置。

OpenCode 原生支持在 agent frontmatter 中声明 `model` 和 `variant`，例如：

```yaml
model: openai/gpt-5.5
variant: medium
```

因此本轮不需要引入复杂 runtime resolver，也不需要改变 OpenCode agent 加载机制。更合适的短期方案是：用集中配置描述各 agent 的模型档位，再把有效配置渲染到各 AI CLI 的 agent markdown frontmatter 中。

同时，本设计需要为后续方案 3 预留迁移路径：未来上线时可以从“渲染到 markdown frontmatter”升级为“运行时读取 effective config 并动态解析模型”，但本轮工作不能因此变得过重。

# 设计目标

本设计本轮解决以下问题：

1. 支持按 subagent 角色配置不同模型。
2. 支持按 4 个统一档位管理模型：`xhigh`、`high`、`medium`、`low`。
3. 支持每个档位声明 `model`，并支持声明或覆盖 `variant`。
4. 默认 `variant` 为 `medium`，用户可在 profile 或 agent 级别覆盖。
5. 区分 canonical 模板配置和各 AI CLI 目录中的 effective config。
6. 区分两层同步：Template sync 和 Effective config render。
7. 提供无需用户手动记命令的自然语言安装/刷新路径。
8. 新增脚本应复用公共 helper，避免复制 `install_agents.py` 中已有逻辑。

# 非目标

本轮不解决以下问题：

1. 不实现完整 runtime model resolver。
2. 不实现 OmO 风格的 category fallback chain、provider capability normalize 或 runtime fallback。
3. 不改造 OpenCode 本身的 agent 加载机制。
4. 不把模型配置直接硬编码进 canonical `agents/*.md`。
5. 不要求用户手动编辑 derived agent markdown 文件。
6. 不让 `sdlc-project-bootstrap` 直接解析 YAML 或修改 agent frontmatter。

# 当前问题分析

## 1. 单模型运行造成成本与能力错配

当前所有 SDLC agent 默认跟随同一个模型。这会产生两类问题：

1. 高消耗实现类 agent 使用最高档模型，成本不必要地升高。
2. 规划、审查、路由等需要高判断力的 agent 如果使用中低档模型，容易导致设计偏差、路由错误或 review gate 不够锋利。

因此模型配置不应只是一项全局设置，而应跟 agent 角色绑定。

## 2. 直接改 agent frontmatter 不够动态

最简单的做法是在每个 canonical `agents/*.md` 中直接写入 `model` 和 `variant`。但这会带来几个问题：

1. 模型升级时要修改多个 prompt 文件。
2. 模型配置和 prompt 内容耦合，不利于维护。
3. 不同 AI CLI target 可能希望使用不同模型配置，canonical 文件无法表达这种差异。
4. 后续迁移 runtime resolver 时，需要再把散落在 frontmatter 中的配置抽出来。

因此 canonical agent prompt 应保持模型无关，模型配置应集中管理。

## 3. 只读 canonical config 无法支持本地差异

如果安装或激活时始终读取 `agents/config/model-profiles.yaml`，用户对 `.opencode/agents/config/model-profiles.yaml` 的本地调整就无法生效。

更合理的模型是两层配置：

1. `agents/config/model-profiles.yaml` 是 canonical 模板。
2. `<ai-cli-dir>/agents/config/model-profiles.yaml` 是该 CLI target 的 effective config。

短期方案 1 通过 effective config 渲染 agent markdown；后续方案 3 则可以让 runtime resolver 直接读取同一个 effective config。

## 4. 同步语义需要拆分

本需求天然包含两层同步：

1. Template sync：把 canonical agent prompt 和 canonical config 模板分发到 AI CLI 目录。
2. Effective config render：把 AI CLI 目录里的 effective config 激活到 agent markdown frontmatter。

如果都塞进 `install_agents.py`，脚本职责会变模糊。用户修改 effective config 后只是想刷新 frontmatter，不一定想重新安装或同步 canonical 模板。

因此需要把底层脚本拆开，再提供一个用户级聚合入口。

# 设计原则

## 原则 1：canonical prompt 不绑定模型

`agents/*.md` 是 canonical prompt source，应表达角色职责、权限和输出契约，不应表达本地模型选择。

模型选择属于部署配置，应由 `agents/config/model-profiles.yaml` 模板和 target effective config 管理。

## 原则 2：配置分层，保护用户本地修改

canonical config 只作为模板。target config 一旦存在，默认不覆盖。

这保证用户可以在 `.opencode/agents/config/model-profiles.yaml` 或其他 CLI target 中做本地调整，而不会被后续安装覆盖。

## 原则 3：激活 derived artifact，不手改 derived artifact

`<ai-cli-dir>/agents/*.md` 是安装和激活后的 derived artifact。

用户可以改 effective config，但不应手动维护 generated agent markdown 中的 `model` 和 `variant`。刷新 agent markdown 应通过 `activate_agents_config.py` 或聚合入口完成。

因此，`model` 和 `variant` 不属于 canonical prompt drift 的比较范围。它们是 target effective config 的激活结果，只应由 activation 阶段负责生成和校验。

## 原则 4：底层脚本职责单一，上层入口对话化

底层脚本需要语义清晰：

1. `install_agents.py` 负责 Template sync。
2. `activate_agents_config.py` 负责 Effective config render。
3. `setup_agents.py` 负责聚合安装和激活。

用户不应该被要求记住这些命令。自然语言入口由 `sdlc-project-bootstrap` 或 LLM 调用 `setup_agents.py` 完成。

## 原则 5：公共 helper 必须复用

新增脚本不应复制 `install_agents.py` 中已有的 source/target 解析、扫描、hash、metadata、YAML 解析、frontmatter 处理逻辑。

公共逻辑应抽到独立 helper 模块，避免后续迭代时出现三份脚本行为漂移。

# 解决方案

## 一、模型档位配置

新增 canonical 模板配置：

`agents/config/model-profiles.yaml`

建议初始内容：

```yaml
schema_version: 1

defaults:
  variant: medium

profiles:
  xhigh:
    description: "极高智能模型，用于 orchestration / planning / review"
    model: openai/gpt-5.5

  high:
    description: "高智能模型，用于 verification 或较复杂判断"
    model: openai/gpt-5.4

  medium:
    description: "中等成本实现模型，用于高 token 消耗的实现工作"
    model: deepseek/deepseek-v4-pro

  low:
    description: "低成本快速模型，用于轻量任务"
    model: deepseek/deepseek-v4-flash

agents:
  dev-orchestrator:
    profile: xhigh
  plan-agent:
    profile: xhigh
  review-agent:
    profile: xhigh
  test-agent:
    profile: high
  implement-agent:
    profile: medium
  finish-agent:
    profile: medium
```

4 个 profile key 固定采用英文 ASCII：

1. `xhigh`：极高档。
2. `high`：高档。
3. `medium`：中档。
4. `low`：低档。

`variant` 默认值为 `medium`。如果用户需要更高或更低思考深度，可以在 profile 或 agent 级别覆盖。

profile 级覆盖示例：

```yaml
profiles:
  xhigh:
    model: openai/gpt-5.5
    variant: xhigh
```

agent 级覆盖示例：

```yaml
agents:
  test-agent:
    profile: high
    variant: low
```

agent 也可以直接覆盖模型：

```yaml
agents:
  implement-agent:
    profile: medium
    model: deepseek/deepseek-v4-pro
    variant: medium
```

## 二、配置解析规则

`model` 解析优先级：

1. `agents.<agent>.model`
2. `profiles.<profile>.model`
3. 缺失则报错

`variant` 解析优先级：

1. `agents.<agent>.variant`
2. `profiles.<profile>.variant`
3. `defaults.variant`
4. 脚本兜底 `medium`

校验规则：

1. `schema_version` 必须等于 `1`。
2. `profiles` 必须是 mapping。
3. `agents` 必须是 mapping。
4. agent 引用的 profile 必须存在。
5. 每个 agent 必须能解析出 `model`。
6. `model` 必须包含 provider 前缀，形如 `provider/model`。
7. `variant` 如果存在，必须是非空字符串。

本轮不做 provider capability normalize。如果某 provider 不支持某个 `variant`，由 OpenCode 或后续 runtime resolver 处理。本轮只负责把用户配置透传到 agent frontmatter。

## 三、两层同步

### 1. Template sync

Template sync 由 `scripts/install_agents.py` 负责。

职责：

1. 从 canonical `agents/*.md` 分发 agent prompt 到 `<ai-cli-dir>/agents/*.md`。
2. 从 canonical `agents/config/model-profiles.yaml` 初始化 `<ai-cli-dir>/agents/config/model-profiles.yaml`。
3. 如果 target config 已存在，默认不覆盖，只提示 canonical template 与 target config 可能不同。
4. 写入或更新 `.agent-install.json` metadata。
5. 不注入 `model` 或 `variant`。

Template sync 可以覆盖 target agent markdown 的 canonical 内容，包括 `description`、`mode`、`permission` 和正文。`model` 与 `variant` 不由该阶段负责保留或生成；它们会在后续 Effective config render 阶段根据 target effective config 重新写入。

默认行为：

1. 首次安装时复制 config template。
2. 后续安装时不覆盖已有 target config。
3. `--force` 可以覆盖 target agent markdown prompt，但仍不覆盖 target config。

单独运行 `install_agents.py --force` 后，target agent markdown 可能处于“prompt 已同步但模型配置未激活”的中间状态。正常用户入口应使用 `setup_agents.py`，由它在 Template sync 后继续执行 Effective config render。

如需未来支持覆盖 target config，应使用独立显式参数，例如 `--sync-config-template` 或 `--force-config`，避免误覆盖用户本地模型配置。本轮默认不实现覆盖 target config 的自动行为。

### 2. Effective config render

Effective config render 由 `scripts/activate_agents_config.py` 负责。

职责：

1. 读取 `<ai-cli-dir>/agents/config/model-profiles.yaml`。
2. 扫描 `<ai-cli-dir>/agents/*.md`。
3. 根据 effective config 解析每个 agent 的 `model` 和 `variant`。
4. 更新 target agent markdown frontmatter 中的 `model` 和 `variant`。
5. 保留 frontmatter 中的其他字段和正文内容。
6. 不复制 canonical prompt。
7. 不覆盖 target config。

支持参数：

1. `--target <dir>`：指定 AI CLI agents 目录。
2. `--global`：使用默认全局 OpenCode agents 目录。
3. `--check`：只检查，不写入。若 target markdown 与 effective config 不一致，返回非零退出码。
4. `--dry-run`：显示将更新的 agent，不写入。

用户修改 `<ai-cli-dir>/agents/config/model-profiles.yaml` 后，只需要重新执行 activation，即可把配置刷新到 `<ai-cli-dir>/agents/*.md`。

如果 Template sync 刚刚覆盖了 target agent markdown，activation 必须重新写入 `model` 和 `variant`，保证最终文件中的模型配置来自 target effective config，而不是 canonical prompt。

## 四、用户级聚合入口

新增 `scripts/setup_agents.py`，作为用户级脚本入口。

职责：

1. 调用 Template sync。
2. 调用 Effective config render。
3. 统一处理 `--target`、`--global`、`--force`、`--check`、`--dry-run` 等常用参数。
4. 不直接实现 YAML 解析、frontmatter 渲染或 metadata 写入逻辑。

推荐内部流程：

1. `install_agents.py` 完成 canonical prompt 和 config template 初始化。
2. `activate_agents_config.py` 根据 target effective config 激活 `model` 和 `variant`。

这意味着 `setup_agents.py --force` 的最终效果是：先把 canonical prompt 内容覆盖到 target agent markdown，再用 target effective config 重新写回 `model` 和 `variant`。用户不需要关心中间状态。

用户改 target config 后也可以继续使用同一入口刷新：

```bash
python3 scripts/setup_agents.py --target ./.opencode/agents --force
```

但文档和 skill 应优先提供自然语言入口，而不是要求用户记住命令。

## 五、自然语言安装和刷新入口

用户明确不希望手动记脚本命令。因此 `sdlc-project-bootstrap` 应承接自然语言入口，但不承接底层实现逻辑。

设计为：

1. `sdlc-project-bootstrap` 增加 Agent Setup 步骤。
2. 该步骤只调用 `scripts/setup_agents.py`。
3. `sdlc-project-bootstrap` 不解析 `model-profiles.yaml`。
4. `sdlc-project-bootstrap` 不直接修改 agent markdown frontmatter。
5. 用户可以通过自然语言触发安装或刷新。

示例自然语言入口：

```text
帮我 bootstrap 这个项目，启用 opencode agents
```

执行效果：

1. 初始化项目基础设施。
2. 分发 canonical agents。
3. 初始化 target effective config。
4. 激活 target config 到 agent markdown。

另一个刷新场景：

```text
我改了 .opencode/agents/config/model-profiles.yaml，帮我刷新 agents
```

执行效果：

1. 调用 `setup_agents.py` 或 activation 路径。
2. 使用 target effective config 重新渲染 target agent markdown。
3. 提醒用户重启 OpenCode，使新 agent frontmatter 生效。

这种分工既满足“用户不用敲命令”，也保持实现职责清晰。

## 六、公共 helper 复用

新增公共 helper 模块：

`scripts/agent_config_lib.py`

该模块承接所有可复用逻辑，避免 `install_agents.py`、`activate_agents_config.py`、`setup_agents.py` 重复定义。

建议提供能力：

1. canonical source 解析：
   - 默认 source：`agents/`
   - canonical config：`agents/config/model-profiles.yaml`
2. target 解析：
   - `--target ./.opencode/agents`
   - `--global` → `~/.config/opencode/agents`
3. agent markdown 扫描：
   - 只处理 `*.md`
   - 跳过 `.agent-install.json`、`.DS_Store`、`config/`
4. metadata 处理：
   - 读取和写入 `.agent-install.json`
   - 记录 source repo、source ref、installed files hash
5. YAML config 读取和校验：
   - `schema_version`
   - `defaults`
   - `profiles`
   - `agents`
6. effective model 解析：
   - `model` priority
   - `variant` priority
7. frontmatter 处理：
   - 读取 YAML frontmatter
   - 更新或插入 `model`、`variant`
   - 保留其他 frontmatter 字段和正文
8. hash 和 compare：
   - 原始 markdown hash
   - activated markdown hash
   - check 模式 drift 输出
   - canonical prompt compare 时忽略 `model` 和 `variant`

现有 `install_agents.py` 中的以下逻辑应迁移到 helper：

1. `_canonical_source`
2. `_source_repo_root`
3. `_git_source_ref`
4. `_scan_dir`
5. `_write_metadata`
6. `_global_target`

迁移后，三个 CLI 脚本只保留参数解析和编排逻辑。

# 脚本行为设计

## `install_agents.py`

定位：Template sync。

行为：

1. 扫描 canonical `agents/*.md`。
2. 复制 markdown prompt 到 target。
3. 初始化 target config：
   - source：`agents/config/model-profiles.yaml`
   - target：`<target>/config/model-profiles.yaml`
4. target config 已存在时不覆盖。
5. 写入 `.agent-install.json`。
6. 不写入 `model` 或 `variant`。

`--check` 语义：

1. 检查 target prompt 是否与 canonical prompt 一致。
2. 检查 target config 是否存在。
3. 如果 canonical config 与 target config 不同，只提示，不失败。
4. 不检查 activation drift；activation drift 属于 `activate_agents_config.py --check`。

比较 canonical prompt 与 target prompt 时，必须先规范化 frontmatter，并忽略 `model` 和 `variant` 字段。也就是说：

1. target agent markdown 中存在由 activation 写入的 `model` 和 `variant`，不算 prompt drift。
2. target agent markdown 的 `model` 或 `variant` 与 canonical 不同，不算 prompt drift。
3. target agent markdown 的其他 frontmatter 字段不同，仍算 prompt drift。
4. target agent markdown 的正文不同，仍算 prompt drift。

## `activate_agents_config.py`

定位：Effective config render。

行为：

1. 读取 target effective config。
2. 对每个 target agent markdown 解析有效 `model` 和 `variant`。
3. 更新 frontmatter。
4. 输出每个被更新 agent 的 model/profile 信息。

`--check` 语义：

1. 读取 target config。
2. 计算每个 agent 应有的 frontmatter。
3. 如果 target markdown 不一致，输出 drift 并返回非零退出码。

activation check 只负责检查 `model` 和 `variant` 是否与 target effective config 一致。用户修改 `<ai-cli-dir>/agents/config/model-profiles.yaml` 后如果没有重新激活，该检查必须报 drift。

## `setup_agents.py`

定位：用户级聚合入口。

行为：

1. 默认先执行 Template sync。
2. 再执行 Effective config render。
3. 输出统一 summary。
4. 提醒用户重启 OpenCode 或对应 AI CLI。

`--check` 语义：

1. 先运行 `install_agents.py --check`。
2. 再运行 `activate_agents_config.py --check`。
3. 任一检查失败则返回非零退出码。

两段检查组合后的含义是：

1. canonical prompt 内容一致性由 Template sync check 保证，但忽略 `model` 和 `variant`。
2. `model` 和 `variant` 一致性由 activation check 保证。
3. 只有两者都通过，target agents 才被视为整体一致。

# 与方案 3 的迁移关系

本设计不是一次性方案。它刻意把配置结构设计成 runtime resolver 可继承的数据层。

未来方案 3 可继承：

1. `agents/config/model-profiles.yaml` 的 schema。
2. `<ai-cli-dir>/agents/config/model-profiles.yaml` 的 effective config 位置。
3. `xhigh/high/medium/low` profile 命名。
4. `model` 和 `variant` 解析优先级。
5. 配置校验逻辑。
6. helper 中的 YAML loader 和 resolver。
7. 大部分测试 fixtures。

未来方案 3 会替换或弱化：

1. frontmatter render。
2. activation drift check。
3. 依赖重启 AI CLI 才生效的流程。

迁移后，runtime resolver 可以直接读取 `<ai-cli-dir>/agents/config/model-profiles.yaml`，并在 dispatch 或 agent selection 时解析模型。届时 `activate_agents_config.py` 可以保留为兼容工具，也可以降级为迁移辅助命令。

# 测试策略

## helper 级测试

新增或扩展测试，覆盖：

1. 加载合法 `model-profiles.yaml`。
2. 拒绝错误 `schema_version`。
3. 拒绝 unknown profile。
4. 拒绝缺少 provider 前缀的 `model`。
5. `model` 解析优先级：agent override 高于 profile。
6. `variant` 解析优先级：agent override 高于 profile，高于 defaults，高于脚本兜底。
7. frontmatter 更新时保留其他字段和正文。

## `install_agents.py` 测试

扩展 `tests/test_install_agents.py`：

1. 首次安装复制 canonical agent markdown。
2. 首次安装复制 config template 到 `target/config/model-profiles.yaml`。
3. target config 已存在时默认不覆盖。
4. install 阶段不注入 `model` 或 `variant`。
5. `--check` 能发现 prompt drift。
6. `--check` 不因 target config 与 canonical template 不同而失败。
7. `--check` 忽略 target markdown 中的 `model` 和 `variant` 差异。
8. target markdown 只有 `model` 或 `variant` 与 canonical 不同，不算 prompt drift。
9. target markdown 的 `permission` 或正文不同，仍算 prompt drift。

## `activate_agents_config.py` 测试

新增测试文件，例如 `tests/test_activate_agents_config.py`：

1. 使用 target config 注入 `model` 和默认 `variant: medium`。
2. profile-level `variant` 覆盖默认值。
3. agent-level `variant` 覆盖 profile 值。
4. agent-level `model` 覆盖 profile model。
5. unknown profile 失败。
6. invalid model 失败。
7. `--check` 能发现 target config 修改后 markdown 未刷新。
8. Template sync 覆盖 target markdown 后，activation 能重新写入 `model` 和 `variant`。

## `setup_agents.py` 测试

新增测试文件，例如 `tests/test_setup_agents.py`：

1. 一次执行完成 install + activation。
2. `--check` 同时覆盖 template sync 和 effective config render drift。
3. `--dry-run` 不写文件。
4. 子步骤失败时返回非零退出码，并保留清晰错误信息。
5. `--force` 先覆盖 canonical prompt，再重新激活 `model` 和 `variant`。
6. `--check` 在 prompt 仅存在 `model` / `variant` 差异时不报 template drift，但 activation 不一致时会报 activation drift。

## `sdlc-project-bootstrap` 测试

扩展 bootstrap 相关测试：

1. bootstrap 可调用 agent setup 步骤。
2. bootstrap 不直接解析 `model-profiles.yaml`。
3. bootstrap 不直接修改 agent markdown frontmatter。
4. agent setup 失败时，bootstrap 报告失败并停止后续依赖步骤。

# 用户工作流

## 首次初始化

用户自然语言：

```text
帮我 bootstrap 这个项目，启用 opencode agents
```

系统行为：

1. `sdlc-project-bootstrap` 执行项目基础设施初始化。
2. Agent Setup 步骤调用 `scripts/setup_agents.py --target ./.opencode/agents`。
3. `setup_agents.py` 完成 Template sync 和 Effective config render。
4. 系统提示用户重启 OpenCode。

## 修改模型配置后刷新

用户修改：

`./.opencode/agents/config/model-profiles.yaml`

然后自然语言：

```text
我改了 .opencode/agents/config/model-profiles.yaml，帮我刷新 agents
```

系统行为：

1. 调用 `scripts/setup_agents.py --target ./.opencode/agents --force`，或只调用 activation 子路径。
2. 读取 target effective config。
3. 更新 `.opencode/agents/*.md` frontmatter。
4. 提示重启 OpenCode。

## 多 CLI target

本设计也适用于其他 target：

```text
帮我刷新 cursor agents 配置
```

对应 target：

`.cursor/agents/`

同理可支持：

`.claude/agents/`

# 风险与处理

## 风险 1：target config 与 canonical template 长期漂移

这是预期行为的一部分，因为 target config 是用户本地 effective config。

处理方式：

1. 默认不覆盖 target config。
2. install/check 时提示 canonical template 与 target config 不同。
3. 如未来需要强制同步模板，使用显式参数，不复用 `--force`。

## 风险 2：provider 不支持某些 variant

本轮不做 capability normalize。

处理方式：

1. 默认 `variant` 使用保守值 `medium`。
2. 用户可按 profile 或 agent 覆盖。
3. 后续方案 3 引入 capability normalize。

## 风险 3：用户忘记重启 OpenCode

OpenCode agent/config 文件通常在启动时加载，运行中不会自动应用所有配置变更。

处理方式：

1. `setup_agents.py` 和 activation 成功后输出重启提示。
2. `sdlc-project-bootstrap` summary 中也提示重启。

## 风险 4：脚本职责重新发散

如果后续在三个 CLI 脚本里分别实现扫描、解析和渲染逻辑，会导致维护成本上升。

处理方式：

1. 公共逻辑必须放入 `scripts/agent_config_lib.py`。
2. 测试优先覆盖 helper 行为。
3. CLI 脚本只做参数解析和编排。

# 实施顺序

建议按以下顺序实施：

1. 新增 `agents/config/model-profiles.yaml`。
2. 抽取 `scripts/agent_config_lib.py`。
3. 调整 `scripts/install_agents.py`，改为 Template sync 语义。
4. 新增 `scripts/activate_agents_config.py`。
5. 新增 `scripts/setup_agents.py`。
6. 扩展 `sdlc-project-bootstrap`，增加 Agent Setup 编排步骤。
7. 增加 helper、install、activate、setup、bootstrap 测试。
8. 更新相关文档和 AGENTS 说明。

# 验收标准

本设计完成后，应满足以下条件：

1. 新项目或现有项目可以通过自然语言触发 agent setup。
2. target 目录存在 `<ai-cli-dir>/agents/config/model-profiles.yaml`。
3. target config 已存在时不会被默认覆盖。
4. target agent markdown 中包含由 effective config 渲染出的 `model` 和 `variant`。
5. 用户修改 target config 后，可以通过自然语言刷新 agent markdown。
6. `install_agents.py`、`activate_agents_config.py`、`setup_agents.py` 复用公共 helper，不重复实现核心逻辑。
7. `install_agents.py --check` 校验 canonical prompt drift 时忽略 `model` 和 `variant`。
8. `activate_agents_config.py --check` 专门校验 `model` 和 `variant` 是否匹配 target effective config。
9. `setup_agents.py --check` 同时发现 prompt drift 和 activation drift。
10. `setup_agents.py --force` 最终产物必须保留由 target effective config 激活出的 `model` 和 `variant`。
11. 方案 3 可以复用本轮配置文件位置、schema、解析规则和测试 fixtures。
