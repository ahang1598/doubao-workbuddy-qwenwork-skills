---
name: im-aitable-butler
displayName: AI表格协同应答助手
name_en: im-aitable-butler
description: |
  AI 表格协同应答助手 · 让 IM、Agent 与 AI 表格协同响应你的钉钉消息。@机器人或@你本人， 千问办公 Agent 自动处理并回复（联网查资料 / 读文档 / 查日志 / 执行操作）；消息进度实时可见 （处理中→处理完成状态标签），所有消息自动沉淀到 AI 表格形成问题库（提问人 / 时间 / 来源 / 内容 / 结果 / 状态）。 支持多群 + 单聊监听、机器人 / 本人双身份回复。当用户要求部署钉钉消息监听、搭建群消息自动回复、 配置机器人自动处理、安装 AI 表格协同应答助手时使用。
description_en: |
  Turn a DingTalk group into an AI-powered customer service team. @-mention the bot or yourself and QwenWork Agent handles the request end-to-end (web search / doc reading / log query / action execution), with live status reactions and automatic archival into an AI-Table issue tracker. Supports multi-group + DM monitoring and dual-identity replies (bot Markdown / self dynamic card).
argument-hint: 无需参数，直接触发即可开始部署
category: productivity
install_source: official
install_method: download
skill_id: official_75F5Wutc
enabled_at: 1791893820407
version: 1.0.0
name_zh: AI表格协同应答助手
---

# AI 表格协同应答助手

让 IM、千问办公 Agent 与 AI 表格协同响应你的钉钉消息：IM 收消息 → Agent 处理 → AI 表格沉淀问题库，一键部署到钉钉群。

## 触发词

AI表格协同应答助手 / AI表格协同应答 / IM+AI表格 / 部署钉钉监听 / 消息监听 / 自动回复 / 机器人处理群消息 / 一键部署 / im-aitable-butler

## 产品定位（一句话）

把 IM 的即时性、千问办公 Agent 的处理能力、AI 表格的结构化沉淀能力串成一条协同应答流水线：IM 是入口、Agent 是大脑、AI 表格是记忆。适用于客群答疑、内部报障群、协同沟通群等被重复问题淹没的场景。完整的产品说明、链路图与三张示意图见 `references/产品说明.md`。

三个高光设计（Agent 在给用户介绍时可以主动提到）：

1. **双身份回复**：@机器人 → 机器人 Markdown；@本人花名 → 本人流式卡片（用本人钉钉认证发，群里看不出是数字分身）。
2. **闲聊不打扰**：processor-prompt.md 里内置寒暄识别，纯客套直接静默；有实际问题才触发处理，并贴「处理中 → 处理完成」表情。
3. **消息变资产**：所有处理过的消息自动落到 AI 表格「问题收集表」（提问人 / 时间 / 来源群 / 内容 / 处理结果 / 状态），第一次自动建表、之后复用。

## 前置依赖

本技能依赖 **DWS（钉钉工作台）** 连接器（key: `qwenwork.settings.connector.builtin.dws`）。

- 用途：调用 DWS CLI 与 MCP 拉取钉钉消息、发送消息 / 卡片、绑定机器人、读写 AI 表格
- 类别：builtin
- 认证方式：OAuth（用户在千问办公「设置 → 连接器 → DWS」中完成一次授权）

同时需要本机安装 Python 3、并且千问办公桌面已启动至少一次（生成 `~/.qwenworkcn/mcp-adaptor.config`）。

## 执行步骤

### Step 0 — 连接器就绪性检查（必做）

1. `qw_query` 查 `qwenwork.settings.connector.builtin.dws` 的 `enabled` / `status`。
2. 未启用或未连接时，按白皮书标准流程调 `qw_action` enable / connect / open 设置页，不要硬闯。
3. 命令行侧再跑一次 `dws auth status --format json` 确认 accessToken 有效。

### Step 1 — 加载完整部署指令

读取本技能包内的 `references/一键部署指令.md`，将文件中第一条 `---` 分割线以下的全部内容，作为任务指令严格执行。文件里已经写明：

- 环境检查（macOS / Windows 自动分支）
- AskUserQuestion 收集机器人名 / robot_code / 群 openConversationId / 单聊 / 回复身份 / AI 表格存档
- 生成 `~/.qwenworkcn/dingtalk-monitor/` 全套代码（poll.py / processor-prompt.md / config.json / emotion-cache.json / poll-state.json / logs）
- 注册 LaunchAgent（30s，macOS）或 schtasks（1min，Windows）
- 绑定机器人到群（dws chat +chat-add-bot；500043=已在群）
- 冒烟：发一条 @机器人 消息，观察 poll.log + 群内表情 + AI 表格新记录

### Step 2 — 关键约束（Agent 必须遵守）

- **绝不** disconnect / reconnect 千问办公 DWS 连接器；这会覆盖 Keychain token，破坏 refresh 链路。
- **绝不**自动运行 `dws auth login`（会反复弹浏览器）；auth 失效时只写日志提示用户在终端手动 login。
- `self_bot_names` 只放机器人名，不放用户花名 —— card 模式回复 sender 是用户本人，放进去会过滤本人真实消息。
- AI 表格存档一律先查后建：`dws aitable` 列出目标文档全部子表，按名称匹配「问题收集表」，命中直接复用，未命中才 `table create`。
- 所有 dws 命令失败时记录错误继续，不中断主流程。

### Step 3 — 防自回复循环（poll.py 已内建，勿删）

- 内容签名过滤：跳过 `[互动卡片]` 占位符 + `<身份> · ` 开头的卡片消息。
- 触发 card 任务时登记 10 分钟自我抑制窗口（`state.self_reply_windows`），窗口内本人身份消息一律不再触发。
- `processor-prompt.md` 卡片标题规范：`## <身份> · <标题>`，正文不复述 @原文。

## 输出格式

部署完成后，Agent 应输出：

1. 定时任务 ID / 名称、下一次调度时间。
2. 生成的关键文件绝对路径（poll.py / config.json / logs 目录）。
3. 一句话冒烟验证语，形如「在群 <name> 里发 `@小龙助手 你好` 试试；30 秒内应看到消息被贴上『处理中』表情，随后收到卡片回复，同时 AI 表格『问题收集表』出现新行」。

## 常见错误与恢复

- **UNKNOWN_KEY / INVALID_INPUT**：DWS 连接器 key 写错，正确形态 `qwenwork.settings.connector.builtin.dws`。
- **500043**：机器人已在群，忽略即可。
- **auth 失效**：不要自动 `dws auth login`，提示用户手动跑一次；token_refresher.py 会在下一轮 poll 时先尝试静默续期。
- **消息重复回复**：确认 poll.py 里的自回复抑制窗口和 `[互动卡片]` 过滤未被误删。

完整的排查手册（auth 失效、poll.log 常见报错、AI 表格写入失败、定时任务不跑、发卡片失败、贴表情失败等，含现象 → 根因 → 解法三段式与快速自检命令）见 `references/troubleshooting.md`。遇到用户报障时先按该文件对照定位，再决定是否要 Agent 自动修复。

## 验证

- macOS：`launchctl list | grep dingtalk-monitor` 有条目；Windows：`schtasks /Query /TN dingtalk-monitor`。
- `~/.qwenworkcn/dingtalk-monitor/logs/poll.log` 每 30–60s 有 `poll ok` 记录，无 traceback。
- 群里 @机器人 后：原消息贴表情、收到卡片回复、AI 表格「问题收集表」出现新记录。
