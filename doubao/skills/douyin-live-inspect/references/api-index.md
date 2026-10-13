# 正式直播内部接口

<!-- CAPABILITY_ROUTES_START -->
#### 产品范围内的内部路由（生成）

先遵循产品边界，再按需读取一份 leaf。表内命令是内部实现，不向用户展示；不得通过 Schema 或其他资源扩展本产品范围。

| 业务意图 | 命令入口 | 叶子文档 |
| --- | --- | --- |
| 列出直播质检项目 | `node scripts/api.mjs --operation 'quality/+project-list'` | [leaf](project-list.md) |
| 获取单任务直播质检报告 | `node scripts/api.mjs --operation 'quality/+report-get'` | [leaf](report-get.md) |
| 获取直播质检场景 | `node scripts/api.mjs --operation 'quality/+scenario-get'` | [leaf](scenario-get.md) |
| 列出直播质检场景 | `node scripts/api.mjs --operation 'quality/+scenario-list'` | [leaf](scenario-list.md) |
| 列出直播质检截图 | `node scripts/api.mjs --operation 'quality/+screenshot-list'` | [leaf](screenshot-list.md) |
| 创建直播质检任务 | `node scripts/api.mjs --operation 'quality/+task-create'` | [leaf](task-create.md) |
| 结束直播质检任务 | `node scripts/api.mjs --operation 'quality/+task-end'` | [leaf](task-end.md) |
| 获取直播质检任务 | `node scripts/api.mjs --operation 'quality/+task-get'` | [leaf](task-get.md) |
| 列出直播质检任务 | `node scripts/api.mjs --operation 'quality/+task-list'` | [leaf](task-list.md) |
<!-- CAPABILITY_ROUTES_END -->
