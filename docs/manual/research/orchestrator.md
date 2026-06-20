# 背景
我在设计自己的sdlc工作流。目前我本仓库已有以下核心skill：
- sdlc-repository-memory-\*：用于管理本仓库记忆
- sdlc-roadmap: 用于管理指定功能的迭代优化，是对openspec的补充，因为openspec没有将相关的迭代串联起来
- sdlc-evalops: 用于skill开发的指令触发，指令遵循的评估（语义评估）
- superpowers：开源skill插件，核心用到brainstorming和tdd，对应简单开发任务直接走superpowers完整工作流成，不走openspec
- openspec：开源skill插件，用于处理复杂开发需求
- sdlc-orchestrator：用于开发工作流编排，编排以上skill互相协作

我使用opencode作为我的ai-cli
# 目前痛点

我在openspec change进行归档后，想稳定触发memory sync，以及roadmap状态更新。但是因为openspec是外来skill，在不hack他们的前提下，很难做到稳定触发，目前是肯定不会触发。
现在需要优化这些skill的协作机制，来保证工作流按预期稳定流转

# 目前已尝试方案
## 工作流加状态机方案
目前已经实现，详情参见本仓库代码。
但也存在痛点，后续如果加入新的skill，更新workflow和状态机估计有点复杂（迭代复杂）

# 目标
探索是否存在其他相对轻量方案，能达到同样的效果

# 方向
我目前在学习claude code harness，看看里面对应的核心概念能否有助于我目前这个问题的解决。需要你帮忙评估方向是否正确，方案是否可行
## 方向1：Agent和Subagent协作
- 将sdlc-orchestrator作为主Agent，来orchestrate相应的sdlc-subagents
- sdlc-subagents：
	- memory agent：关联memory相关的skill
	- roadmap agent：关联roadmap skill
	- spec agent：关联openspec，superpowers，eval skill
- subagents完成任务后，需要将结果反馈给主agent，主agent根据反馈结果进行subagents的再调度

## 方向2：Hooks
- 利用hook功能进行强制校验，比如openspec 执行完archive，hook校验当前状态是否是archive succeed，如果是，强制触发memory sync和roadmap update（但具体实现细节我没深入思考，而且opencode貌似也没有这种机制，之前了解过好像要自研插件？）