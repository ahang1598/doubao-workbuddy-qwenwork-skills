# 共享参考（shared）文档索引

> 术语 / 硬约束 / 占位符 / 字段字典的**单一来源**。SKILL.md / setup/ / runtime/ 引用本目录文件，
> 严禁在其它文档复制完整内容，避免漂移。

---

## 主题 → 文档 速查表

| 想查 | 跳转 |
| :--- | :--- |
| 某个名词是什么意思（Skill / AI表格 / task_id / ...） | [glossary.md#术语表](./glossary.md#术语表) |
| 系统架构 / 表 / 字段命名规则 | [glossary.md#系统架构概览](./glossary.md#系统架构概览) |
| 配置文件 / sync_state 存储位置 | [glossary.md#数据--配置位置](./glossary.md#数据--配置位置) |
| ID 生成规则（template_id / task_id / ...） | [glossary.md#id-生成策略](./glossary.md#id-生成策略) |
| 时区与 cron 约定 | [glossary.md#时区与时间格式](./glossary.md#时区与时间格式) |
| 硬约束完整规则（H1 ~ H6） | [hard-constraints.md](./hard-constraints.md) |
| 派发 / 提醒消息支持哪些占位符 | [placeholders.md](./placeholders.md) |
| Markdown 渲染规则与 extra_info 行为 | [placeholders.md](./placeholders.md) |
| 表 / 字段定义、统计口径 | [data-model.md](./data-model.md) |

---

## 使用约定

- 任何 SKILL.md / setup / runtime 文档涉及术语、硬约束、占位符、字段定义时，**只能链接到本目录**，不要复制粘贴段落。
- 本目录文件的修改属于「跨阶段影响」改动，需同步检查 setup / runtime 文档中的链接锚点是否仍然有效。
