# Troubleshooting — 常见报错与解法

> 按"现象 → 根因 → 解法"三段式组织。遇到问题先看 `~/.qwenworkcn/dingtalk-monitor/logs/poll.log`，再对照下表定位。

## 1. 认证 / DWS 连接器类

### 1.1 `dws auth status` 报 未认证 / accessToken invalid / 401

**现象**：poll.log 出现 `auth failed`、`Unauthorized`、`401`；或 `dws chat +chat-messages` 直接返回空。

**根因**：DWS 连接器授权过期（默认 accessToken 2 小时，refreshToken 30 天）。

**解法（按优先级）**：

1. **优先让 token_refresher 静默续期**：poll.py 已集成，如果 `config.json` 里存有 `refresh_token`，会自动调 refresh API 后回写。什么都不用做，等下一轮 poll 即可。
2. **手动重登**：终端执行 `dws auth login`（浏览器完成 OAuth）。**注意不要在千问办公里 disconnect/reconnect DWS 连接器**——那会覆盖 Keychain 里的 token 为 MCP authCode 短 token，破坏 refresh 链路。
3. **多组织下认错身份**：加 `--profile <corpId:userId>`。查身份：`dws profile list --format json`。

### 1.2 `dws` 命令找不到 / 权限拒绝

**现象**：LaunchAgent 日志报 `dws: command not found`；或 subprocess 调用返回 `[pending-post-tool-use]`。

**根因**：外部脚本（LaunchAgent / schtasks / subprocess）看不到千问办公的 managed dws wrapper，只能用 standalone。managed wrapper 仅在千问办公自身的 Bash 上下文有效。

**解法**：

- macOS 外部脚本用 `~/.local/bin/dws`（standalone 全路径）。
- Windows 依次找 `%USERPROFILE%\.local\bin\dws.exe`、`.cmd`、千问办公安装目录下的 dws。
- 所有写操作必须加 `-y` 跳过确认（`dws chat +chat-add-bot ... -y`），否则 subprocess 会阻塞返回空。

### 1.3 每次 poll 都弹浏览器让你重登

**根因**：poll.py 里被误改成自动调 `dws auth login`。**绝不允许**——每次都会新开一个浏览器窗口。

**解法**：确认 poll.py 里 auth 失败分支只写日志 + token_refresher 静默续期，不主动 login。

## 2. 消息 / 轮询类

### 2.1 群里 @机器人 后完全没反应

**排查顺序**：

1. `launchctl list | grep dingtalk-monitor`（macOS）或 `schtasks /Query /TN dingtalk-monitor`（Windows）确认定时任务在跑。
2. 看 poll.log 有没有 `poll ok` 心跳（每 30–60s 一条）。
3. `dws chat +chat-messages --id <openConversationId>` 手动拉一次，看能否收到测试消息。**Stream 模式只收纯文本 @mention**，不会推卡片消息和其他机器人的消息——想监听卡片必须走主动拉取。
4. 机器人没进群：`dws chat +chat-add-bot --robot-code <AppKey> --id <openConversationId>`；返回 `500043` = 已在群，忽略。
5. **最隐蔽的根因**：处理任务里跑了试探性命令（如 `dws aitable --help`），触发 Bash 权限确认无人值守，任务挂死。治本 → processor-prompt.md 写死命令序列，或任务改用自动批准模式。

### 2.2 Agent 自己在回复自己（无限自回复循环）

**现象**：枫发 1 条，Agent 回了 2 条以上；poll.log 里能看到「[互动卡片]」和「龙衔 · 处理中」被当新消息又触发任务。

**根因**：card 任务以本人身份发的「处理中 / 已完成」卡片被下一轮 poll 消费。仅按 sender 名过滤 `小龙助手` 无法识别本人身份发出的 Agent 回复。

**解法**（poll.py 已内建，勿删）：

- **内容签名过滤**：跳过 `[互动卡片]` 占位符 + `<身份> · ` 开头的卡片消息（正则由 bot_priority 自动生成）。
- **自回复抑制窗口**：触发 card 任务时登记 10 分钟 `state.self_reply_windows`，窗口内本人身份消息一律跳过。
- **processor-prompt.md 卡片规范**：`## <身份> · <标题>` 开头、不复述 @原文（复述会骗过群 @strict 检查）。

副作用：抑制窗口内用户手动发的真实消息也会被跳过，这是权衡后的结果。

### 2.3 消息被重复处理 / 处理过的消息又来一遍

**根因**：`poll-state.json` 没写回，或 message_id 计算错。

**解法**：

- 检查 poll-state.json 是否可读可写；权限不对就 `chmod 644`。
- 单聊消息用 `senderId` + `conversationId` 组合去重（部分单聊 API 不返回 messageId）。
- 时间窗默认 10min，太长会消费历史消息，太短会漏；不建议改。

### 2.4 `self_bot_names` 把用户本人也过滤了

**现象**：card 模式回复后，用户自己在群里发的真实消息也被跳过。

**根因**：`self_bot_names` 里加了用户花名。card 模式下 Agent 回复的 sender 就是用户本人，用花名过滤会误伤真实消息。

**解法**：`self_bot_names` **只放机器人名**（如 `小龙助手`），本人身份靠自回复抑制窗口 + 内容签名过滤挡。

### 2.5 `PREPARE_CALL_TOOL_ERROR` / MCP 调用偶发失败

**根因**：dingtalk-pre-mcp HTTP MCP 服务器偶发抖动。

**解法**：poll.py 已内建重试，通常下一轮就恢复；连续 3 轮以上失败再查网络或服务端状态。

## 3. AI 表格存档类

### 3.1 每次都新建"问题收集表"，没复用

**根因**：没走"先查后建"逻辑。

**解法**：processor-prompt.md 里的存档步骤必须先 `dws aitable base list --format json` + 按 `dataSheetName == "问题收集表"` 精确匹配，命中 → 直接 `record create`；未命中才 `table create` + 建字段。

### 3.2 AI 表格 record 写入失败：`payload too large` / `richText 破碎`

**根因**：长 `--records`（含 richText 富文本）内联 JSON 在命令行会因转义 / 引号截断而破碎。

**解法**：先把 records 写到本地 JSON 文件，再用 `--records-file <path>` 导入。

### 3.3 `aitable base list` 分页缺 `nextCursor`

**根因**：dws skill shortcut 版把 JSON 精简过。

**解法**：改用原子命令 `dws aitable base list --format json`，字段路径 `data.nextCursor`；每页 max 10 条。

### 3.4 `table get` 拿字段 ID 拿不到

**根因**：路径 `.data.fields` 不存在。

**解法**：正确路径 `.data.tables[0].fields[]`，可用 `--jq '.data.tables[0].fields[]'`。

### 3.5 上传附件到 AI 表格 record 失败

**根因**：dws skill 内置的 `upload_attachment.py` 写死了命令名为 `dws`，subprocess 走 managed wrapper 被拦截。

**解法**：复制 `upload_attachment.py` 到工作区，把 cmd 改成 standalone 全路径 + 加 `-y`，然后本地运行。

## 4. 机器人 / 发消息类

### 4.1 `dws chat +chat-add-bot` 返回 500043

**含义**：机器人已经在群里，**不是报错**，忽略即可。

### 4.2 发卡片没反应 / 发出去后消息不显示

**排查**：

- 卡片必须以本人身份发（`+messages-send-card`），不需要 robotCode。
- 机器人发消息只能发 Markdown（`+messages-send-by-bot` + robotCode），发不了卡片。
- Stream 模式的机器人推送不到群内其他机器人发的消息。

### 4.3 贴表情失败 / 表情 id 错

**根因**：dws 表情命令是 `message add-text-emotion`，不是 `+messages-add-emoji`。

**解法**：emotion id 从 `~/.qwenworkcn/dingtalk-monitor/emotion-cache.json` 读取；缓存为空时 `dws message list-emotions --format json` 重建缓存。

## 5. 定时任务 / 平台类

### 5.1 macOS LaunchAgent 不跑

**排查**：

1. `launchctl list | grep dingtalk-monitor` 有无条目。
2. plist 里 `StartInterval` 建议 30，太短容易撞频控。
3. Python 路径用 `which python3` 检测出的绝对路径，不要写 `python3` 依赖 PATH。
4. 日志目录必须存在且可写。

### 5.2 Windows schtasks 只能 1 分钟粒度

**解法**：写一个 `poll_twice.bat`，里面 `python poll.py && timeout 30 && python poll.py`，实现 30s 双击。

### 5.3 千问办公 cron 最小间隔 1 分钟

**根因**：千问办公内置 cron 底线是 1min。要 30s 只能用 OS 层定时器（LaunchAgent / schtasks）。

## 6. 常用快速自检命令

```bash
# 认证
dws auth status --format json

# 定时任务
launchctl list | grep dingtalk-monitor        # macOS
schtasks /Query /TN dingtalk-monitor           # Windows

# 最近 poll 心跳
tail -n 50 ~/.qwenworkcn/dingtalk-monitor/logs/poll.log

# 手动拉一次群消息
dws chat +chat-messages --id <openConversationId> --format json

# 手动拉一次单聊
dws chat +messages-list-direct --user <userId> --format json

# 查 AI 表格是否有"问题收集表"
dws aitable table list --base-id <baseId> --format json --jq '.data.tables[] | .name'

# 强制清除自回复抑制窗口（调试用）
python3 -c "import json,pathlib; p=pathlib.Path('~/.qwenworkcn/dingtalk-monitor/poll-state.json').expanduser(); d=json.loads(p.read_text()); d['self_reply_windows']={}; p.write_text(json.dumps(d))"
```

## 7. 什么时候找人 / 提 issue

- 上表都对不上：把 `poll.log` 最近 200 行 + `config.json`（**隐去 robot_code / refresh_token**）一起丢给千问办公 Agent，让它按现象 → 根因 → 解法反推。
- MCP 服务端异常（连续多轮 `PREPARE_CALL_TOOL_ERROR`）：反馈到 dingtalk-pre-mcp 团队。
- dws CLI bug：`dws --version` + 复现命令 + 错误 JSON，提到 DWS 项目 issue。
