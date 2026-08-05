# SkillHub 每日推荐 - Cron 定时任务提示词模板

> 本文档提供多平台的 Cron 定时任务提示词模板，复制即可使用。

## 通用提示词结构

每个 Cron 任务 prompt 应包含以下部分：

```
执行 skillhub-daily Skill：按 SKILL.md 步骤 1-7 完成每日推荐。

# 痛点（请直接使用，不再扫描记忆）
- [痛点1]
- [痛点2]
- [痛点3]
- [痛点4]（可选）
- [痛点5]（可选）
- [痛点6]（可选）

# 存储通道
[IMA知识库 / 飞书云文档 / 本地 / Obsidian]

# 知识库 ID（如使用 IMA）
[replace-me]

# 飞书文件夹 Token（如使用飞书且指定文件夹）
[your_folder_token]（留空=根目录）

# Obsidian Vault 路径（如使用 Obsidian）
[your_vault_path]

# 输出要求
完成后输出 200 字以内的对话摘要（无表格）。
```

---

## 模板 1：qclaw 飞书推送（推荐）

**适用平台**：qclaw  
**存储**：飞书云文档  
**推送渠道**：飞书  
**Cron**：每日 07:00

```json
{
  "schedule": { "kind": "cron", "expr": "0 7 * * *", "tz": "Asia/Shanghai" },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "请执行 skillhub-daily Skill，按 SKILL.md 步骤 1-7 完成每日推荐。\n\n# 痛点（请直接使用，不再扫描记忆）\n- YouTube 字幕提取\n- 股票分析\n- n8n 工作流\n- Markdown 转换\n- 桌面自动化\n- 文档管理\n\n# 存储通道\n飞书云文档\n\n请完成后输出 200 字以内的对话摘要（无表格）。"
  },
  "delivery": { "mode": "announce", "channel": "feishu" }
}
```

---

## 模板 2：qclaw 微信推送（IMA 知识库）

**适用平台**：qclaw  
**存储**：IMA 知识库  
**推送渠道**：微信  
**Cron**：每日 09:20

```json
{
  "schedule": { "kind": "cron", "expr": "20 9 * * *", "tz": "Asia/Shanghai" },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "请执行 skillhub-daily Skill，按 SKILL.md 步骤 1-7 完成每日推荐。\n\n# 痛点（请直接使用，不再扫描记忆）\n- YouTube 字幕提取\n- 股票分析\n- n8n 工作流\n- Markdown 转换\n- 桌面自动化\n- 文档管理\n\n# 存储通道\nIMA 知识库\n\n# 知识库 ID（请替换为你的真实 ID）\n<your_ima_kb_id>=\n\n请完成后输出 150 字以内的纯文本摘要（微信限制）。"
  },
  "delivery": { "mode": "announce", "channel": "qclaw-weixin" }
}
```

---

## 模板 3：WorkBuddy 飞书推送

**适用平台**：WorkBuddy  
**存储**：飞书云文档  
**推送渠道**：飞书  
**Cron**：每日 07:00

**WorkBuddy 项目级定时任务 prompt**：

```
执行 skillhub-daily Skill，按 SKILL.md 步骤 1-7 完成每日推荐。

# 痛点
- YouTube 字幕提取
- 股票分析
- n8n 工作流
- Markdown 转换
- 桌面自动化
- 文档管理

# 存储通道
飞书云文档

# 通知渠道
完成后通知到：飞书
```

**WorkBuddy 渠道级定时任务 prompt**（搜索 IMA 简报并推送）：

```
每天 09:20 搜索 IMA 知识库中今日创建的 SkillHub 简报，读取内容并概括 150 字纯文本推送到微信。
```

---

## 模板 4：OpenClaw Cron（CLI 模式）

**适用平台**：OpenClaw（CLI 调用）  
**存储**：本地  
**Cron**：每日 06:00

```bash
# crontab -e
0 6 * * * cd /home/user/.openclaw/skills/skillhub-daily && /usr/bin/python3 scripts/skillhub_daily.py --slim --no-html --data-dir ./data
```

**或者 OpenClaw Agent 调度**：

```json
{
  "schedule": { "kind": "cron", "expr": "0 6 * * *", "tz": "Asia/Shanghai" },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "执行 skillhub-daily Skill：按 SKILL.md 步骤 1-7 完成每日推荐。\n\n# 痛点\n- YouTube 字幕提取\n- 股票分析\n- n8n 工作流\n- Markdown 转换\n- 桌面自动化\n- 文档管理\n\n# 存储通道\n本地存储（仅生成 data/reports/YYYY-MM-DD-briefing.md）\n\n# 输出\n完成后输出 200 字以内的对话摘要。"
  },
  "delivery": { "mode": "announce", "channel": "console" }
}
```

---

## 模板 5：Hermes Webhook 触发

**适用平台**：Hermes  
**存储**：IMA 知识库  
**Cron**：每日 07:00

```bash
0 7 * * * curl -X POST https://hermes.example.com/api/v1/skills/skillhub-daily/execute \
  -H "Authorization: Bearer ${HERMES_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "pain_points": [
      "YouTube 字幕提取",
      "股票分析",
      "n8n 工作流",
      "Markdown 转换",
      "桌面自动化",
      "文档管理"
    ],
    "storage": "ima",
    "ima_kb_id": "<your_ima_kb_id>=",
    "output_summary": true
  }'
```

---

## 模板 6：纯脚本 + 手动推送

**适用场景**：CI/CD、容器化、开发者  
**存储**：本地 + 手动 IMA 推送

```bash
#!/bin/bash
# run_skillhub_daily.sh

set -e

SKILL_DIR="/path/to/skillhub-daily"
DATE=$(date +%Y-%m-%d)
BRIEFING="${SKILL_DIR}/data/reports/${DATE}-briefing.md"

# 1. 数据抓取
cd "${SKILL_DIR}"
python scripts/skillhub_daily.py --slim --no-html --data-dir ./data

# 2. 检查简报
if [ ! -f "${BRIEFING}" ]; then
    echo "ERROR: Briefing not found: ${BRIEFING}"
    exit 1
fi

# 3. 推送到 IMA（如已配置凭证）
if [ -n "${IMA_CLIENT_ID}" ] && [ -n "${IMA_API_KEY}" ]; then
    python scripts/push_to_ima.py "${BRIEFING}" "SkillHub 每日简报 | ${DATE}"
fi

echo "Done! Briefing: ${BRIEFING}"
```

**Crontab**：
```bash
0 7 * * * /path/to/run_skillhub_daily.sh >> /var/log/skillhub-daily.log 2>&1
```

---

## 模板 7：Obsidian 同步（个人知识库）

**适用平台**：任意  
**存储**：Obsidian Vault  
**Cron**：每日 07:00

```json
{
  "schedule": { "kind": "cron", "expr": "0 7 * * *", "tz": "Asia/Shanghai" },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "执行 skillhub-daily Skill：按 SKILL.md 步骤 1-7 完成每日推荐。\n\n# 痛点\n- YouTube 字幕提取\n- 股票分析\n- n8n 工作流\n- Markdown 转换\n- 桌面自动化\n- 文档管理\n\n# 存储通道\nObsidian（复制简报到 {OBSIDIAN_VAULT}/SkillHub/YYYY-MM-DD.md）\n\n# Obsidian Vault 路径（请替换为你的真实路径）\n<your_obsidian_vault_path>\n\n# 附加操作\n- 简报已生成到本地\n- 复制到 Obsidian\n- 不推送微信/飞书"
  },
  "delivery": { "mode": "announce", "channel": "console" }
}
```

---

## 痛点列表示例（可直接复制）

### 通用痛点（6 个）

```
- YouTube 字幕提取
- 股票分析
- n8n 工作流
- Markdown 转换
- 桌面自动化
- 文档管理
```

### 投研类（金融）

```
- 财报数据抓取
- 竞品对比
- 行业研报整理
- 量化策略回测
- 舆情监控
- 投资组合管理
```

### 开发类

```
- 代码 review
- 自动化部署
- 单元测试生成
- API 调试
- 日志分析
- 性能监控
```

### AI/Agent 类

```
- Prompt 工程
- RAG 检索增强
- Agent 编排
- MCP 协议集成
- 模型微调
- 推理优化
```

### 办公效率类

```
- 会议纪要
- 邮件分类
- 日程管理
- 文档协作
- 飞书自动化
- 微信运营
```

### 自定义痛点

直接列出你近期的痛点即可，例如：
```
- 短视频脚本生成
- PPT 自动排版
- 客户跟进提醒
- 团队日报汇总
```

---

## 最佳实践

1. **痛点数量控制在 3-6 个**——太少不够精准，太多匹配分散
2. **痛点要具体**——避免"提高效率"这种泛泛的描述
3. **每 1-2 周更新痛点**——根据工作重心变化
4. **Cron 时间错开**——避免与 IMA、飞书等推送任务冲突
5. **首次使用先手动测试**——确认无误后再启用 Cron

---

## 验证清单

Cron 任务创建后，请逐项验证：

- [ ] 手动触发一次，确认简报生成
- [ ] 确认存储到目标通道（IMA/飞书/Obsidian）
- [ ] 确认对话摘要正常输出
- [ ] 确认推送渠道收到通知
- [ ] 检查 `data/logs/` 无错误
- [ ] 启用定时执行
- [ ] 24 小时后检查是否自动执行
