# 背景
superpowers和openspec都有自己的设计文档存储地址，因此目前plan-agent的handoff文档有点多余，甚至容易给实现带来偏离

# 目标
调整plan-agent及其上下游的md文档，满足以下要求：
- 当用户通过dev-orchestrator和llm进行头脑风暴时，允许dev-orchestrator调用superpowers的brainstorming技能进行问题边界确认。注意：只做确认，确认完毕后直接调用plan-agent进行具体设计
- 当dev-orchestrator给plan-agent分发任务前，会和用户确认flow-type：1）如果是lightweight-flow，则直接用superpowers的brainstorming的brainstorming和writing-plans完成任务设计；2）如果是spec-flow，则使用对应的spec provider来创建spec。完成文件创建后，不在生成handoffs文件，只是将产生的文件路径返回给dev-orchestrator。如果仍有需要澄清的问题，则抛出问题。
- 用户确认方案通过后，dev-orchestrator将设计文件路径信息作为上下文的一部分，dispatch implement-agent，implement-agent结合设计文档进行任务实现。1）如果是lightweight-flow，使用superpowers工作流程 2）如果是spec-flow，使用apply_change

# 开放问题
目前把plan集成到dev-orchestrator里面，感觉交互有点重，因为每次dev-orchestrator都得把上下文打包给plan-agent做具体的事情，延长长，可能打断心流。
是否把plan-agent拆出来比较好。比如拆成plan-builder和plan-executor，目前我看omo就是这么设计的。
plan-builder负责和用户头脑风暴，生成handoff文件，这个文件包含设计文档的具体位置（superpowers和spec模式的文档位置不同）。生成结束后，返给用户一个workflow run id，提示用户粘贴到plan-executor里执行。
plan-executor完成除了现有plan-agent之外的调度任务。