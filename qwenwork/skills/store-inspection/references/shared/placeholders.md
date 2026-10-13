# 消息占位符 / Markdown 渲染规则（唯一来源）

> 派发与提醒消息渲染相关的全部约定。`setup/03-template.md` 与 `runtime/01-dispatch.md`
> 用到时一律链接到本文件，禁止重复粘贴占位符表。

---

## 渲染相关字段（仅 2 个）

模板里参与消息渲染的字段只有 2 个：

| 模板字段 | CLI 参数 | 用途 |
| :--- | :--- | :--- |
| `message_title` | `--message-title` | 派发消息**标题**（钉钉消息列表显示）。**提醒消息复用同一份**，第 N 次提醒（N≥2）由 messenger 自动加 `【第N次提醒】` 前缀 |
| `dispatch_message` | `--dispatch-message` / `--dispatch-message-file` | 派发消息**正文**（Markdown）。**提醒消息复用同一份模板** |

> [!NOTE]
> `description` 字段重构后改为「模板介绍文本」（管理后台展示用，**不参与消息渲染**）。
> 老库残留的 `remind_topic` / `remind_message` 字段已废弃，CLI 完全忽略，
> `init --auto-repair` 不会主动删除（避免误删用户数据），但也不再补齐。
> 新建 AI表格 不会包含这两个字段。

---

## 占位符表（中英文等价，可混用）

| 中文占位符 | 英文别名 | 渲染时替换为 |
| :--- | :--- | :--- |
| `{门店名称}` | `{store_name}` | 该门店在「门店清单」表里的名称 |
| `{店长姓名}` | `{manager_name}` | 该门店店长姓名 |
| `{派发时间}` | `{dispatch_time}` | 当前派发的时间戳 |
| `{任务名称}` | `{task_name}` | 模板名称（如"每日巡检"） |
| `{任务表名}` | `{task_table_name}` | 当次派发动态任务表名（如"每日巡检-20260427"） |
| `{表单链接}` | `{form_link}` | 店长用于填写的分享链接（未在模板里使用时会自动追加在末尾） |
| `{截止时间}` | `{deadline_str}` | 派发时间 + `expected_duration` 计算得到的截止时刻；模板未配置时长则为空 |
| `{额外信息}` | `{extra_info}` | 派发命令 `--extra-info` 透传的内容；详见下文 |

任一字段为空时，由 messenger 在发送时 fallback 到 `scripts/domain/message_defaults.py` 中的内置默认 Markdown 文案。

---

## `--scene` 场景化 dispatch_message（模板层）

`template create --scene <场景>` 在默认 Markdown 模板基础上自动插入场景特有字段行，
生成场景化的 `dispatch_message` 写入模板表。该内容**随模板持久化**，后续派发/提醒均复用。

| 场景标识 | 中文名 | 自动插入行 |
| :--- | :--- | :--- |
| `inspection` | 巡店检查 | `- **检查项目**：{字段1}、{字段2}…`（取自 `custom_fields` 的 `name`） |
| `morning-meeting` | 早会 | `- **会议议程**：{字段名}…` |
| `inventory` | 盘点 | `- **盘点范围**：{字段名}…` |

- 不传 `--scene` → 使用纯通用默认模板（无场景行）
- 同时传了 `--dispatch-message` / `--dispatch-message-file` → 显式模板优先，`--scene` 不覆盖
- 创建前预览中会展示 `dispatch_message_preview`，用户确认后才写入

---

## `--message-override` 一次性覆盖（派发层）

`dispatch notify --message-override <MARKDOWN>` / `--message-override-file <FILE>` 允许
本次派发使用一次性自定义消息正文，**不会写入模板表的 `dispatch_message` 字段**。

- 优先级：`--message-override` > 模板表 `dispatch_message` > 内置默认模板
- 标题仍从模板表 `message_title` 读取（override 仅覆盖正文）
- 适用场景：用户说"这次用 xxx 格式发"但不想永久修改模板

---

## `{额外信息}` / extra_info 行为

- 由 `dispatch init` / `dispatch notify` 的 `--extra-info "<TEXT>"` 透传。
- 同时**持久化到任务记录的 `extra_info` 字段**，后续提醒消息复用同一份内容（除非 `dispatch notify --extra-info` 显式覆盖）。
- 模板**已使用** `{额外信息}` / `{extra_info}` 占位符 → 按占位符位置替换。
- 模板**未使用**该占位符且 `extra_info` 非空 → messenger 自动以 `> 📌 {extra_info}` 引用块形式追加到正文末尾（在表单链接之前）。

---

## 提醒消息（自动复用派发模板）

提醒消息**没有独立模板字段**，由 `messenger.send_remind_message` 在派发模板基础上自动加工：

- **正文**：与派发完全一致（同一份 `dispatch_message` + 默认模板兜底 + extra_info 处理）。
- **标题**：复用 `message_title`；**第 N 次提醒（N≥2）** 自动在标题前加 `【第N次提醒】` 前缀；
  第 1 次提醒标题与派发完全一致（不加前缀）。
- **额外信息**：从任务记录的 `extra_info` 字段读取，确保派发与历次提醒展示一致。

`reminder.py` 在每次发送提醒时把任务记录的 `reminder_round` 字段 `+1` 写回，
作为下一次提醒的标题前缀编号依据。

---

## 默认 Markdown 文案示例（派发与提醒同形）

```markdown
### {任务名称}

**{店长姓名}** 你好，今日有新的巡检任务待处理：

- **门店**：{门店名称}
- **任务表**：{任务表名}
- **派发时间**：{派发时间}
- **截止时间**：{截止时间}
- **额外信息**：{额外信息}

请尽快点击下方链接填写：

[👉 立即填写]({表单链接})
```

---

## 渲染样例（用户视角）

参数：店长=张三 / 门店=北京朝阳店 / 任务=每日巡检 / 任务表=每日巡检-20260427

**派发消息**：
> ⏰ 北京朝阳店 巡检任务
>
> ### 每日巡检
>
> **张三** 你好，**北京朝阳店** 今天的巡检任务待处理：
>
> - **任务表**：每日巡检-20260427
> - **截止时间**：2026-04-27 18:00
>
> [👉 立即填写](https://docs.dingtalk.com/notable/share/form/...)

**第 2 次提醒**（标题自动前缀，正文不变）：
> 【第2次提醒】⏰ 北京朝阳店 巡检任务
>
> ### 每日巡检
> ...（正文同上）
