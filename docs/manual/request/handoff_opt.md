# 背景
- superpowers和openspec都有自己的设计文档存储地址，因此目前plan-agent的plan文档有点多余，甚至容易给实现带来偏离
- 其他handoffs文件需要补充部分信息，方便llm自学习，已经开发迭代优化工作流

# 调整
调整plan-agent及其上下游的md文档，满足以下要求：
- 当用户通过dev-orchestrator和llm进行头脑风暴时，允许dev-orchestrator调用superpowers的brainstorming技能进行问题边界确认。注意：只做确认，确认完毕后直接调用plan-agent进行具体设计
- 当dev-orchestrator给plan-agent分发任务前，会和用户确认flow-type：1）如果是lightweight-flow，则直接用superpowers的brainstorming的brainstorming和writing-plans完成任务设计，原先些什么文件，写哪里，不变，遵循superpowers原始工作流；2）如果是spec-flow，则使用对应的spec provider来创建spec。完成文件创建后，不在生成plans文件，只是将产生的文件路径放在handoffs文件里返回给dev-orchestrator。如果仍有需要澄清的问题，则抛出问题。
- 关于artifacts.plan_path：直接去除，相应的设计文档（superpowers的spec和plan，spec-flow的change）在handoffs里引用相应的文件路径，并强调其他依赖plan-agent的agent要着重关注这块内容

关于每个agent的handoffs内容在原有的基础上需要追加：
- plan-agent：1）设计文档地址，2）key decisions：dev-orchestrator和plan-agent的交互留下的历史决策，3）open questions：存留待讨论问题（作为下次交互的关键上下文）
- implement-agent：issues - 执行过程中遇到的一些问题记录，leanings - 以及如何解决的，suggestions - 后期如何避免(方便开发迭代优化工作流)
- test-agent：同implement-agent
- review-agent：同implement-agent

