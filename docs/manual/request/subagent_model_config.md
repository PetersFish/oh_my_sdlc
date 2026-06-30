# 背景
目前dev-orchestrator以及其对应的subagent默认都使用同一个llm模型，从token经济的角度看不太合理
implement-agent属于实现agent，需要耗费大量token，我希望用deepseek-v4-pro这样的中等模型跑
finish-agent也一样；
而dev-orchestrator，plan-agent，review-agent需要智能一点的模型跑，比如gpt5.5
而test-agent感觉用gpt5.4也可以。

然后我想实习这些agent的模型可配置化，以后模型升级了，支持我动态调整

因此需要一个支可配置化的方案，来实现我的需求

# 目标
调研，并设计一个可行方案，支持我的可配置化需求。必要时，可以参考omo这个项目：https://github.com/code-yeongyu/oh-my-openagent