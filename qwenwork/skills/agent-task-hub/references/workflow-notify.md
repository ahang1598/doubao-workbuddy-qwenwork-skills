# 交接通知自动化（workflow-notify）

> 团队模式建表后，附两条自动化：① 指定人交接通知；② 待认领群通知（有团队群时）。
> 命令：`dws aitable workflow create --base-id <BASE_ID> --dsl @<模板文件> --locale zh-CN`，`--dsl` 是 `workflow-dsl/v1` JSON。详细节点规范见 `dws aitable workflow edit-example`。
> 建自动化的执行顺序与脚本渲染命令见 `create-ledger.md` 步骤 7；本文件只讲 DSL 语义和必须校验的点。

## 模板文件

- 指定人交接通知模板：`templates/handoff-notify-workflow.json`（`<...>` 占位符，用时替换真实 fieldId）
- 待认领群通知模板：`templates/claim-notify-workflow.json`
- 团队台账交接通知实例：`examples/team-handoff-notify-workflow.json`（使用合成示例坐标 `tbl_team_handoff` / `fld_assignee` / `fld_notice`，**不是真实坐标**；执行前仍需渲染成真实 fieldId）

执行前把模板里 `<...>` 换成真实值：fieldId 来自 `table get`，其余结构原样用。

写临时 DSL 后必须检查占位符已替换完：

```bash
rg '<[^>]+>' <临时JSON文件>
# 期望无输出；有输出就不要 create workflow
```

## 交接通知（指定人）语义

- 触发：`WhenRecordCreated` + `mustHaveFields=<任务交接对象fieldId>`；`where EXIST` 保证创建子记录时已填交接对象才触发。
- 不要依赖「先创建记录、再更新父记录」来补触发。交接时子记录创建动作本身就是通知时机；父记录更新只用于汇总状态，不承担通知触发。
- 父任务不要写「任务交接对象」；指定人只写在交接子记录上，避免父任务和子记录双重通知。
- 发送对象：`to.users` 用 `{ "ref": "$.start.<任务交接对象fieldId>[*]" }` 直接发给刚填上去的人。
- `sender: { "type": "person" }` 表示以流程配置者本人发，更友好；也可省略走系统机器人。
- 字段里多人时末尾 `[*]` 必带；单人也建议带 `[*]`（编译器会按运行时 schema 归一化）。
- 团队表现有字段「负责人」改名「任务交接对象」后，fieldId 不变，只改 fieldName；DSL 里用 fieldId 即可。
- 通知正文直接 `ref` 通知文案 richText 字段（`content: [{ "ref": "$.start.<通知文案fieldId>" }]`）。该字段用 markdown 写入，已实测会在通知里渲染成加粗/标题/列表，不要再用拼接 text/ref 的方式分块拼正文。
- 通知文案由 `scripts/render-notice.py` 确定性生成（三块：`**任务**`/`**交接说明**`/`**接手方式**`，加粗标签 + 引用块 prompt，样式已实机验证），原样嵌入、禁止自由组装；sanitize 自动把摘要中裸写文件名（`.md`/`.py` 等撞国家码 TLD 会被渲染器 autolink）与裸 URL 包反引号、折叠显式链接——仅行内代码可抑制是实机结论。
- 「一句话摘要」只用于台账列表检索，不再进通知正文。
- 自动化 `SendMessage.content` 里引用 richText 字段会按 markdown 渲染；普通 `text` 片段仍是纯文本，不要写 Markdown 链接。
- 交接通知必须开启卡片按钮：`isButtonsEnabled=true`，按钮名 `去查看`，`action.type=link`，`url.ref=$.start.rowUrl`，用于直接定位到本条交接子记录。
- 正文不再放团队台账链接，也不写“查看详情”；这些信息打进「通知文案」markdown 里（如需团队台账链接，写裸 `https://...`）。
- 接手方式必须写进「通知文案」markdown，给出可定位的 prompt，且包含 skill 名称和任务标题：`使用 agent-task-hub 接手「<任务标题>」`。不要写“接手这条交接任务”这种离开卡片后指代不明的说法。
- 不要提示接任者手工回填「任务ID + Agent类型」；这些由接手流程自动回填。
- 已存在同名自动化不等于可用；若旧流程仍是 `WhenRecordUpdated`，必须标记为待迁移，不能作为新交接流程的验证通过依据。

## 待认领群通知语义

- 触发：`WhenRecordCreated` + `where` 判断「交接状态」=待认领（option 用真实 optionId）。
- 发送对象：`to.conversations` 传 `{ "group": "cid_xxx" }`（团队群）；群 cid 由建表时问用户提供（或 `dws chat group search` 查）。
- 若无团队群，此条自动化不建，待认领任务只留在台账里等成员主动认领。
- 待认领群通知同样用「通知文案」richText 承载短说明 + 卡片按钮定位记录；认领方式写进 markdown：`使用 agent-task-hub 认领「<任务标题>」`，不要把完整六块摘要直接刷到群里。

## 交接状态联动（可选的第三条自动化，暂不默认建）

若希望「子记录状态变化 → 父记录交接状态联动」，可用：
`WhenRecordUpdated`(监听子记录「状态」) → `FindRecords`(按父记录找到父任务) → `UpdateRecord`(target=match，更新父任务「交接状态」)。此条较复杂，建议先由同步 agent 计算，暂不落自动化。