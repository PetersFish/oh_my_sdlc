# 目前痛点问
- 安装完sdlc-govenance插件后，发现18 条 dangling archive findings，但是之前貌似没有考虑对dangling arhcive的处理机制。我的想法是，遇到deangling archive，补齐对应archive的workflow，对应的roadmap记录
- 目前workflow创建run的时机需要靠人工指令触发，不够强制，很可能导致我发出指令创建roadmap，或创建change后，workflow run却没有创建的场景。我需要一个强触发的方案