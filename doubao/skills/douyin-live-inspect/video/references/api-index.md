# 视频内部接口

<!-- CAPABILITY_ROUTES_START -->
## 产品范围内的内部路由（生成）

先遵循产品边界，再按需读取一份 leaf。表内命令是内部实现，不向用户展示；不得通过 Schema 或其他资源扩展本产品范围。

| 业务意图 | 命令入口 | 叶子文档 |
| --- | --- | --- |
| 列出视频质检项目 | `node ../scripts/api.mjs --operation 'content/+video-project-list'` | [leaf](video-project-list.md) |
| 获取视频质检报告 | `node ../scripts/api.mjs --operation 'content/+video-report-get'` | [leaf](video-report-get.md) |
| 获取视频质检场景 | `node ../scripts/api.mjs --operation 'content/+video-scenario-get'` | [leaf](video-scenario-get.md) |
| 列出视频质检场景 | `node ../scripts/api.mjs --operation 'content/+video-scenario-list'` | [leaf](video-scenario-list.md) |
| 创建视频质检任务 | `node ../scripts/api.mjs --operation 'content/+video-task-create'` | [leaf](video-task-create.md) |
| 结束视频质检任务 | `node ../scripts/api.mjs --operation 'content/+video-task-end'` | [leaf](video-task-end.md) |
| 获取视频质检任务 | `node ../scripts/api.mjs --operation 'content/+video-task-get'` | [leaf](video-task-get.md) |
| 列出视频质检任务 | `node ../scripts/api.mjs --operation 'content/+video-task-list'` | [leaf](video-task-list.md) |
<!-- CAPABILITY_ROUTES_END -->
