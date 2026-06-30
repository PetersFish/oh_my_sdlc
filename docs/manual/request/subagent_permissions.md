# 背景
目前很多subagent有写文件的需求，主要是写handoffs，但是目前的很多文件编辑权限都被控制了，导致subagent经常被权限拦截，要求用户授权，非常打断用户开放的心流。

目前权限拦截遇到以下一些情况，我人肉识别并记录的：
implement-agent需要加grep，head，git branch、worktree、check-ignore权限（只要不是commit，remove之类的操作，其他查看型的git操作要允许）;finish-agent也一样，像find、ls这样的bash脚本也是要允许，这些在opencode里有抽象成tool吗，比如Glob，Read这些; plan-agent需要开cat权限。test-agent 不能访问write tool，mcp功能也要加上。

然后deepseek v4 pro模型在调用mcp，skill层面有点弱，不会自动去获取拿来用，感觉需要告知。
目前有几个mcp我希望deepseek-v4-pro能够积极用起来
- mcp codegraph & sdlc-repository-memory-load skill：当要理解当前代码库代码时，务必调用
- tavily-search：如果需要调研最新技术时，务必要用
- context7：如果要参考最新的代码范例时，务必要用
- headroom：用于压缩上下文的，能用的地方务必要用，特别是需要压缩命令行执行结果等场景


# 目标
- 调整sdlc subagents的权限，达到最优控制
- 提示deepseek-v4-pro的工具（skill，mcp）调用能力

需要修改:
- 其实历史数据修复我并不太关心,最关心的是 实现偏离 spec / 预期 没被 test / review / finish gate 拦住,这个需要优化一下.
- 至于历史run订正,我手动订正好了.
- _migrate_legacy_artifacts如果删除安全,可以删除