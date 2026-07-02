# 背景
我已经创建了roadmap-agent，加入到dev-orchestrator工作流体系里。
但是目前貌似没有完全融合，他们在协作的时候出现一些问题。需要你定位，并给出优化方案。

# 我的期望
1. 当用户向dev-orchestrator发起review roadmap item的请求时，应当将任务派发给roadmap-agent，来完成item的评审，先llm评审，反馈给用户确认。
2. 如果返回的是通过，则会附带下一个dispatch targent的建议，目前是提问用户要继续创建spec，还是review 下一个item。（如果是继续创建spec，则将任务分发给plan-agent，推进当前工作流。如果是review下一个item，则继续让roadmap-agent查出下一个item是哪个，继续第一步roadmap-agent的动作）
3. 如果是有开放问题需要讨论，用户补充信息，重新dispatch 到roadmap-agent进行下一轮评审。
4. dev-orchestrator在对已有的roadmap item进行操作时，需要校验有没有和他关联的workflow run，如果没有，则需要为其创建关联的workflow run，run中要包含roadmap item的信息（做映射关系用）；如果当前workflow run里有相应的roadmap item的信息，则无需额外动作。

请评估的期望是否合理，是否可行，以及目前我的主子agent设计是否满足

# 开放讨论
1. 关于workflow run的创建。在创建roadmap和plan文件之前，其实都不用创建run，因为都还停留在草稿阶段，很可能用户直接取消了，如果一调用subagent就创建，后续可能会产生一堆垃圾run。这个创建run的时机，你有好的建议吗。我个人想法是，只要创建了roadmap item或plan文件，就创建对应的run。当时如果因为一个需求复杂度高，被拆成多个roadmap item，那是同时创建多个workflow run吗
2. roadmap变成agent会不会太重，我看finish-agent里调用memory-sync，对应memory skill的操作是直接用这个skill，反而更轻量。但问题点是roadmap是有生命周期的，理论上roadmap只要已创建，应该就有对应的workflow run和他映射上，后续方便

针对以上两点，你有没有什么好的建议



