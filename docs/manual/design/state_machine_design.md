# 背景
我发现目前workflow.py更偏向于函数式编程，随着功能越来越多，迭代出现问题的概率越来越大，因此需要进行重构

# 新思路
我的workflow.py里面的状态机可能需要重新优化一下：
## Rule1：面向对象
- 需要面向对象编程
- 标准状态机设计模式
- 杜绝if-else设计，避免扩展困难

## Rule2：状态定义
- workflow状态列表：

| phase     | sub-phase      | state          | flow-type        | required               | 进入时机                      | 执行动作                                                                                                                                                                                  |
| --------- | -------------- | -------------- | ---------------- | ---------------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| plan      | create-roadmap | running / done | unkown           | optional               | 创建完roadmap item           | 创建完roadmap item时，提示用户是否要review roadmap item（accept / delay）                                                                                                                           |
| plan      | review-roadmap | running / done | unkown           | optional               | 评审完roadmap item           | 评审完roadmap item时，提示用户是否要create spec或write plans（让用户选择工作流类型）                                                                                                                           |
| plan      | create-spec    | running / done | spec-flow        | if is spec flow        | 触发new change前进行标记         | 完成new change后，提示是否要继续implement，还是人工review（后期规划：提供llm review command）                                                                                                                  |
| plan      | write-plans    | running / done | lightweight-flow | if is lightweight-flow | 触发writing-plans前进行标记      | 完成writing-plans后，提示是否要继续implement                                                                                                                                                     |
| implement | apply-spec     | running / done | spec-flow        | if is spec flow        | new change的artifacts生成结束后 | 完成implement后，自动流转到review phase（后期规划：执行中提供learnings（用于自学习）, issues（用于向上汇报）记录能力）                                                                                                        |
| implement | execute-plans  | running / done | lightweight-flow | if is lightweight-flow | writing-plans完成后          | 完成implement后，自动流转到review phase（后期规划：执行中提供learnings（用于自学习）, issues（用于向上汇报）记录能力）                                                                                                        |
| review    | /              | running / done | all              | yes                    | implement完成后              | 1. Requesting/receiving code review(superpowers skill)<br>2. 如果发现问题，进行上报（问题位置，具体问题，修复方向）                                                                                              |
| finalize  | /              | running / done | all              | yes                    | verification完成后           | 1. spec-archive (if spec flow)<br>2. verification-before-completion (if lightweight-flow)<br>3. mark roadmap done(if roadmap item exists)<br>4. memory sync (if needed, judge by llm) |
| done      | /              | /              | all              | yes                    | finalize成功后               | 更新workfow状态为done                                                                                                                                                                      |

- roadmap状态列表：

| phase | 进入时机                     |
| ----- | ------------------------ |
| idea  | workflow完成roadmap item创建 |
| ready | workflow完成roadmap it评审   |
| done  | workflow完成finalize       |

## Rule3：状态转换限定
- workflow状态的合法转换：

| from         | to        | condition                              | special action                                                                    |
| ------------ | --------- | -------------------------------------- | --------------------------------------------------------------------------------- |
| user request | plan      |                                        |                                                                                   |
| plan         | implement | user confirmed                         |                                                                                   |
| implement    | review    | automatic                              |                                                                                   |
| review       | plan      | bad smell / bug/  critical issue found | specify auto fix plan (max 2 rounds - configureable, else need user confirmation) |
| review       | finalize  | review passed(minor issue allowed)     |                                                                                   |
| finalize     | plan      | finalize actions failed                | specify fix plan (need user confirmation)                                         |
| finalize     | done      |                                        |                                                                                   |

- roadmap状态的合法转换：

| from         | to    | condition                      | special action |
| ------------ | ----- | ------------------------------ | -------------- |
| user request | idea  | receive create roadmap command | /              |
| idea         | ready | roadmap review passed          | /              |
| ready        | done  | workflow finalizing            | /              |
- 不合法的状态转换需要报错提示，并列举合法的转换方向，以及转换条件
# Question
- roadmap需要专门提供一个python文件用于控制状态转化吗
- 直接改workflow.py风险高不高，是否要新起一个文件来实现
- 目前workflow.py代码行数巨高，迭代非常费token，定位代码具体位置困难，感觉需要更加模块化的设计