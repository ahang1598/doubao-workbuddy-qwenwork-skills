# 配置时（setup）文档索引

> 仅在「绑定 AI表格 / 维护门店 / 维护模板 / 分享配置」等**一次性或偶发**操作时加载本目录。
> 每天高频运行的派发 / 催办 / 报表 / 统计请改读 `../runtime/`。

---

## 场景 → 文档 速查表

| 场景 | 跳转 |
| :--- | :--- |
| 第一次拿到 Skill 怎么用 / `init validate` 报告未初始化 | [01-init.md#首次使用](./01-init.md#首次使用) |
| 新建 / 切换 / 重置 AI 表格绑定 | [01-init.md#命令参数先查--h再读决策点](./01-init.md#命令参数先查--h再读决策点) |
| 添加 / 修改 / 暂停 / 删除门店 | [02-store.md#维护门店清单](./02-store.md#维护门店清单) |
| 直接在 AI 表格中管理门店（批量 / 自助） | [02-store.md#直接在-AI-表格中管理门店](./02-store.md#直接在-AI-表格中管理门店) |
| 通过 dws 通讯录查询店长 UserID | [02-store.md#步骤-1先通过通讯录查询店长信息](./02-store.md#步骤-1先通过通讯录查询店长信息) |
| 创建 / 启停 / 更新巡店模板 | [03-template.md#创建巡店模版](./03-template.md#创建巡店模版) |
| 起草派发 / 提醒消息文案（Agent 起草 + 一稿即写入） | [template-message-drafting.md](./template-message-drafting.md) |
| 把当前巡店配置分享给同事 | [04-share.md#分享配置发送方](./04-share.md#分享配置发送方) |
| 收到他人分享的 BASE_ID | [04-share.md#接收他人分享的配置](./04-share.md#接收他人分享的配置) |

> 完整子命令清单以 `uv run python scripts/cli.py <init|store|template|share> --help` 为准，本目录文档只承担「业务决策」。

---

## 共同前置约束

- 任何业务操作前先 `uv run python scripts/cli.py init validate`（步骤 1，见 SKILL.md 工作流）
- 删除 / 重置必须二次确认，详见 `../shared/hard-constraints.md#H3`
- 多模板时未指定 ID 必须先列模板让用户确认，详见 `../shared/hard-constraints.md#H5`
- 字段定义、占位符见 `../shared/data-model.md` 与 `../shared/placeholders.md`
