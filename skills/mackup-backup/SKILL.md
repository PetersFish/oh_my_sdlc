---
name: mackup-backup
description: Backs up user-specified directories via Mackup; appends to an existing application cfg when paths are related (e.g. same parent like .cursor), otherwise creates a new application (user confirms app name for multiple dirs); when ambiguous, asks user to choose which cfg to append to or to create new. Use when the user explicitly invokes this skill, or asks to back up specified directories (e.g. "请帮忙备份指定目录"), including paths from screenshots or attachments.
---

# mackup-backup

通过 Mackup 将用户指定的目录加入备份。若与已有应用相关则追加到该应用的 cfg；否则新起一个应用。决策困难时与用户确认。

## 触发时机

在以下情况应用本技能：

1. **显式调用**：用户 @mackup-backup 或指名「用 mackup-backup 技能」。
2. **备份意图**：用户表达要备份指定目录，例如：
   - 「请帮忙备份指定目录」
   - 「用 mackup 备份这些目录/这些路径」
   - 「把这些目录加入 mackup 备份」

---

## 1. 收集要备份的路径

- **来源**：用户消息中的文字列表（路径或目录名）；或截图/附件中解析出的目录或文件路径。
- **路径规范**：写入 Mackup 配置时一律使用 **相对 Home 的形式**（如 `.cursor/skills`、`.config/foo`），不带 `~` 或绝对路径。若用户给出 `~/.cursor/skills` 或 `/Users/xxx/.cursor/skills`，先规范为 `.cursor/skills` 再写入 cfg。
- 若从截图/附件解析，先将解析出的路径列出请用户确认，再规范为相对 Home 形式，继续后续步骤。

---

## 2. 检查是否追加到已有应用（否则新起一个）

**在创建新 cfg 或让用户确认新应用名之前**，先做此检查。

- 读取 `~/.mackup.cfg` 的 `[applications_to_sync]`，以及 `~/.mackup/` 下已有的自定义应用 cfg（如 `cursor-assets.cfg`）。若 `~/.mackup` 为符号链接，则读取链接目标目录下的 `*.cfg`。
- **相关性**：若本次要备份的路径与某个已有应用的 cfg 中路径「同属一类」（例如已有应用备份了 `.cursor/skills`，本次要备份 `.cursor/commands`，则都属 `.cursor` 下），视为可 **追加到该应用**，在对应 cfg 的 `[configuration_files]` 中追加新路径，不新建 cfg，也不再问新应用名。
- **决策规则**：
  - **唯一明确相关**：只有一个已有应用的 cfg 中路径与本次路径明显同域（如同属 `.cursor`、同属 `.config`）→ 直接采用「追加到该 cfg」，并告知用户将追加到哪个应用下。
  - **存在决策困难**：多个已有应用都相关、或既可能追加又可能新起一个 → **必须与用户确认**。示例话术：「本次目录与现有应用 A、B 都有关联。请选择：1) 追加到 A 的 cfg；2) 追加到 B 的 cfg；3) 新起一个应用（请给出应用名）。」
  - **无相关应用**：没有任何已有应用与本次路径明显相关 → 按「新起一个应用」处理，进入步骤 3 让用户确认应用名。
- 判断相关性时可依据路径前缀、共同父目录（如 `.cursor`、`.config`）等。

---

## 3. 确定应用名称（仅当新起应用时）

若上一步已决定「追加到已有应用」，**跳过本步**。

- **单目录**：可建议默认应用名（如 `.cursor/skills` → `cursor-skills`），并简短询问用户是否采用或修改。
- **多目录**：必须明确提示用户确认 **Mackup 应用名称**（即 `applications_to_sync` 中的名字，以及 cfg 文件名）。说明示例：「这些目录将作为 Mackup 的**一个**应用一起备份。请确认应用名称（仅小写字母、数字、连字符，如 `my-tools` 或 `cursor-assets`）：」
- 应用名即 `~/.mackup/<应用名>.cfg` 的文件名，以及 `~/.mackup.cfg` 里 `[applications_to_sync]` 下的一行。

---

## 4. 创建/更新 Mackup 配置

- **追加到已有 cfg**：打开 `~/.mackup/<已有应用名>.cfg`（若为符号链接则写链接目标路径），在 `[configuration_files]` 小节下追加本次新路径，每行一个、相对 HOME，不重复已有行。不修改 `~/.mackup.cfg`（该应用已在 sync 中）。
- **新起应用**：
  - 在 **Mackup 根目录** 下创建 `~/.mackup/<应用名>.cfg`（若 `~/.mackup` 为符号链接，则写入链接目标目录）。
  - 文件内容：`[application]` 小节 `name = <显示名>`（可与应用名相同或更可读）；`[configuration_files]` 小节下每行一个相对 HOME 的路径。
  - 在 `~/.mackup.cfg` 的 `[applications_to_sync]` 中增加一行 `<应用名>`（若已存在则跳过），不删除其他应用。

---

## 5. 执行备份与验证

- 执行：`mackup -f backup`（`-f` 避免交互确认）。
- 验证：可检查 Mackup 存储目录（由 `~/.mackup.cfg` 的 `[storage]` 决定）下是否出现对应路径；若 `~/.mackup` 为符号链接，新创建或修改的 cfg 会出现在链接目标目录中。

---

## 注意事项

- 技能与配置文件仅放在 `~/.cursor/skills/`，不要放在 `~/.cursor/skills-cursor/`。
- 不要假定 `~/.mackup` 一定不是符号链接；创建或修改 cfg 时若遇符号链接，在链接目标目录操作。
- 应用名仅使用小写字母、数字、连字符，并在让用户确认时明确提醒。
