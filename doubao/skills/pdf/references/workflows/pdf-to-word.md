# PDF 转 Word

> PDF 转 Word 任务需使用基于`create_agent`的专用Multi-Agent工作流。本文档是工作流的**入口路由**。不要直接开工，接下来请只阅读你自己那一份 Agent 文档，不要把其他角色的文档拉进上下文——上下文隔离是本工作流的显式设计。

## 工作流拓扑

```
MainAgent            读 pdf-to-word-main.md，负责对用户交互
  └── OrganizerAgent 读 pdf-to-word-organizer.md，负责管理分配任务给 SubAgent，检查并合并结果
        └── SubAgent 读 pdf-to-word-sub.md，负责DOCX重建、审计与修复
```

每一层的启动都通过 `create_agent`。上游把必要输入传给下游（路径、页码范围、用户交付要求），**不要**把上游读过的文档内容复述给下游——下游会自己去读它那一份。

## 各 Agent 文档索引

| Agent | 文档 |
|-------|-----|
| MainAgent | pdf-to-word-main.md |
| OrganizerAgent | pdf-to-word-organizer.md |
| SubAgent | pdf-to-word-sub.md |
