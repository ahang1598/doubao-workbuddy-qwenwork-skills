# SkillHub 每日推荐 - 跨平台适配说明

> 本文档说明 skillhub-daily 在不同 Agent 平台上的安装、配置和使用方式。

## 支持的平台

| 平台 | 类型 | 模式 A | 模式 B (Cron) | 凭证位置 | 推送方式 |
|------|------|--------|---------------|---------|---------|
| **qclaw** | 腾讯系 | ✅ | ✅ | `~/.qclaw/skills/ima-skill/config.json` | Cron `announce` |
| **WorkBuddy** | 腾讯系 | ✅ | ✅ | `~/.workbuddy/skills/ima-skill/config.json` | 渠道对话 |
| **OpenClaw** | 开源 | ✅ | ✅ | `~/.openclaw/skills/ima-skill/config.json` | Cron `announce` |
| **Hermes** | 开源 | ✅ | ✅ | 平台特定 | webhook/API |
| **纯脚本** | CLI | ❌ | ❌ | 环境变量 | 外部管道 |

---

## 1. qclaw（腾讯系）

### 安装

```bash
# 方式 1：复制到 skills 目录
cp -r skillhub-daily/ ~/.qclaw/skills/

# 方式 2：使用 skillhub CLI
skillhub install skillhub-daily
```

### 凭证配置

编辑 `~/.qclaw/skills/ima-skill/config.json`：
```json
{
  "ima_client_id": "replace-me",
  "ima_api_key": "replace-me",
  "ima_kb_id": "replace-me"
}
```

或者使用环境变量（优先级更高）：
```bash
export IMA_CLIENT_ID=replace-me
export IMA_API_KEY=replace-me
export IMA_KB_ID=replace-me
```

### Cron 定时任务示例

**飞书推送**（每日 07:00）：
```json
{
  "schedule": { "kind": "cron", "expr": "0 7 * * *", "tz": "Asia/Shanghai" },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "执行 skillhub-daily Skill：按 SKILL.md 步骤 1-7 完成每日推荐。\n痛点：YouTube字幕提取、股票分析、n8n工作流、Markdown转换、桌面自动化、文档管理\n存储：飞书云文档"
  },
  "delivery": { "mode": "announce", "channel": "feishu" }
}
```

**微信推送**（每日 09:20）：
```json
{
  "schedule": { "kind": "cron", "expr": "20 9 * * *", "tz": "Asia/Shanghai" },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "执行 skillhub-daily Skill：按 SKILL.md 步骤 1-7 完成每日推荐。\n痛点：YouTube字幕提取、股票分析、n8n工作流、Markdown转换、桌面自动化、文档管理\n存储：IMA知识库"
  },
  "delivery": { "mode": "announce", "channel": "qclaw-weixin" }
}
```

### 注意事项

- qclaw 微信渠道仅支持纯文本推送，因此输出摘要必须 ≤150 字
- 飞书渠道支持 Markdown，但表格会简化
- IMA 推送会自动 `create` + `add_knowledge`，无需手动操作

---

## 2. WorkBuddy（腾讯系）

### 安装

```bash
cp -r skillhub-daily/ ~/.workbuddy/skills/
```

### 凭证配置

编辑 `~/.workbuddy/skills/ima-skill/config.json`，格式同 qclaw。

### 定时任务配置

在 WorkBuddy 项目级创建定时任务：
1. 打开 WorkBuddy
2. 进入"任务模式"
3. 创建新任务，cron 表达式 `0 7 * * *`
4. 复制 [prompt-templates.md](prompt-templates.md) 中的提示词
5. 启用"完成后通知到：微信/飞书"

### 渠道差异

| 渠道 | 支持 Markdown | 支持表格 | 限制 |
|------|--------------|---------|------|
| 微信 | ❌ | ❌ | 纯文本 ≤150 字 |
| 飞书 | ✅ | ✅ | 表格简化 |
| IMA 知识库 | ✅ | ✅ | 完整 Markdown |

---

## 3. OpenClaw（开源通用）

### 安装

```bash
cp -r skillhub-daily/ ~/.openclaw/skills/
```

### 凭证配置

```bash
mkdir -p ~/.openclaw/skills/ima-skill/
cat > ~/.openclaw/skills/ima-skill/config.json <<EOF
{
  "ima_client_id": "replace-me",
  "ima_api_key": "replace-me",
  "ima_kb_id": "replace-me"
}
EOF
```

### Cron 定时任务

OpenClaw 使用 `crontab`：
```bash
# 编辑 crontab
crontab -e

# 添加任务
0 7 * * * cd ~/.openclaw/skills/skillhub-daily && python scripts/skillhub_daily.py --slim --no-html --data-dir ./data
```

或者使用 OpenClaw Agent 调度：
```json
{
  "schedule": { "kind": "cron", "expr": "0 7 * * *", "tz": "Asia/Shanghai" },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "执行 skillhub-daily Skill..."
  },
  "delivery": { "mode": "announce", "channel": "feishu" }
}
```

---

## 4. Hermes（开源通用）

### 安装

参考 Hermes 官方文档，将本目录复制到 `~/.hermes/skills/` 或对应位置。

### 凭证配置

Hermes 通常使用环境变量：
```bash
export IMA_CLIENT_ID="..."
export IMA_API_KEY="..."
export IMA_KB_ID="..."
```

### 定时任务

Hermes 通过 webhook 或 API 回调：
```bash
# 使用 curl 触发
curl -X POST https://hermes.example.com/api/v1/skills/skillhub-daily/execute \
  -H "Authorization: Bearer replace-me" \
  -d '{"pain_points": [...], "storage": "ima"}'
```

详见 Hermes 官方文档。

---

## 5. 纯脚本模式

### 适用场景

- CI/CD 流水线
- 容器化部署
- 不想安装 Agent 平台

### 使用方式

```bash
# 仅数据抓取（无个性化）
python scripts/skillhub_daily.py --slim --no-html --data-dir ./data

# 手动推送 IMA
python scripts/push_to_ima.py data/reports/2026-06-03-briefing.md "SkillHub 每日简报"
```

### 凭证配置

纯脚本模式**必须**使用环境变量：
```bash
export IMA_CLIENT_ID="..."
export IMA_API_KEY="..."
export IMA_KB_ID="..."
```

---

## 平台选择建议

| 用户类型 | 推荐平台 | 模式 |
|---------|---------|------|
| 腾讯系用户 | qclaw / WorkBuddy | B (Cron) |
| 探索性用户 | 任意 | A (手动) |
| 自动化爱好者 | OpenClaw | B (Cron) |
| 开发者 | 纯脚本 + CI/CD | - |

---

## 故障排查

| 问题 | 解决方案 |
|------|---------|
| 凭证未生效 | 检查环境变量优先级（环境 > config.json） |
| Cron 不执行 | 检查系统时间、时区配置 |
| 推送失败 | 查看 `data/logs/` |
| 痛点不匹配 | 更新 prompt 中的痛点列表 |
| Python 版本过低 | 升级到 3.10+，或安装 `python3.10` |

详见 [setup-wizard.md](setup-wizard.md) 故障排查章节。
