# SkillHub 每日推荐 - 首次安装向导

> 本文档指导用户在首次安装 skillhub-daily 时选择合适的使用模式。

## 启动对话

当用户首次安装本 Skill（或者首次说"每日推荐"等触发词）时，**必须**主动询问以下问题：

> "欢迎使用 SkillHub 每日推荐！请先选择使用模式：
>
> **🔵 模式 A：常规 Skills 模式**（推荐新手）
> - 在对话中随时说"每日推荐"、"SkillHub 日报"等触发词即可调用
> - 每次执行时自动扫描您的记忆文件，发现新的痛点
> - 适合：偶尔使用、探索性发现
>
> **🟢 模式 B：Cron 定时任务模式**（推荐重度用户）
> - 在 Agent 平台配置定时任务（如每日 07:00 自动执行）
> - 痛点列表在 prompt 中预设，不需要每次扫描记忆
> - 简报自动推送到飞书/微信/IMA 知识库
> - 适合：每日固定阅读、自动化工作流
>
> 请输入 **A** 或 **B** 继续。"

---

## 模式 A：常规 Skills 模式

### A.1 配置步骤

#### 1. 安装 Skill

将本目录复制到对应平台：

| 平台 | 安装位置 |
|------|---------|
| qclaw | `~/.qclaw/skills/skillhub-daily/` |
| WorkBuddy | `~/.workbuddy/skills/skillhub-daily/` |
| OpenClaw | `~/.openclaw/skills/skillhub-daily/` |
| Hermes | 平台对应目录 |

或者使用 `skillhub install` 命令安装。

#### 2. 验证环境

```bash
# Windows
python --version
node --version

# macOS/Linux
python3 --version
node --version
```

**版本要求**：Python 3.10+，Node.js 18+（可选，仅 IMA 推送需要）

#### 3. （可选）配置 IMA 推送

编辑 `references/config.json`：
```json
{
  "ima_client_id": "replace-me",
  "ima_api_key": "replace-me",
  "ima_kb_id": "replace-me"
}
```

不填 = 不启用 IMA。

#### 4. 触发使用

在对话中输入任意触发词：
- "每日推荐"
- "SkillHub 日报"
- "看看有什么好 Skill"
- "帮我推荐技能"
- "潜力 Skill"

### A.2 使用流程

```
用户说触发词
   ↓
Agent 扫描 MEMORY.md + 最近 3 天日志
   ↓
提取 3-6 个核心痛点
   ↓
运行 skillhub_daily.py 抓取数据
   ↓
痛点 × 类别交叉匹配
   ↓
生成简报 + 存储（IMA/飞书/本地）
   ↓
输出对话摘要
```

---

## 模式 B：Cron 定时任务模式

### B.1 配置步骤

#### 1-3. 同模式 A 的 1-3 步

#### 4. 选择目标平台

确定你的 Agent 平台（qclaw / WorkBuddy / OpenClaw / Hermes），参考：
- [platform-adapters.md](platform-adapters.md) - 各平台配置方式
- [prompt-templates.md](prompt-templates.md) - 定时任务提示词模板

#### 5. 准备痛点列表

回顾你近期的 3-6 个核心痛点（来自 MEMORY.md 或主观判断），例如：
- YouTube 字幕提取
- 股票分析
- n8n 工作流
- Markdown 转换
- 桌面自动化
- 文档管理

#### 6. 创建定时任务

**qclaw 示例**（详见 [prompt-templates.md](prompt-templates.md)）：

```json
{
  "schedule": { "kind": "cron", "expr": "0 7 * * *", "tz": "Asia/Shanghai" },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "请执行 skillhub-daily Skill，按 SKILL.md 步骤 1-7 完成每日推荐。\n\n# 痛点（请直接使用，不再扫描记忆）\n- YouTube 字幕提取\n- 股票分析\n- n8n 工作流\n- Markdown 转换\n- 桌面自动化\n- 文档管理\n\n# 存储通道\nIMA 知识库\n\n# 知识库 ID（请替换为你的真实 ID）\n<your_ima_kb_id>=\n\n请完成后输出 200 字以内的对话摘要。"
  },
  "delivery": { "mode": "announce", "channel": "feishu" }
}
```

#### 7. 验证定时任务

1. 手动触发一次（qclaw: `trigger` / WorkBuddy: 测试运行）
2. 检查简报是否生成到 `data/reports/`
3. 检查是否推送到目标渠道
4. 确认无误后启用定时执行

### B.2 使用流程

```
定时触发（每日 07:00）
   ↓
Agent 接收 prompt（含预设痛点）
   ↓
直接使用 prompt 中的痛点（不重复扫描）
   ↓
运行 skillhub_daily.py 抓取数据
   ↓
痛点 × 类别交叉匹配
   ↓
生成简报 + 存储（IMA/飞书/Obsidian）
   ↓
输出对话摘要（200 字以内）
   ↓
delivery.announce → 推送到飞书/微信
```

---

## 模式切换

如果想从 A 切换到 B（或反之），只需：
1. 告诉 Agent "切换到 Cron 模式" 或 "切换到常规模式"
2. Agent 会重新走对应模式的配置向导

---

## 常见问题

### Q1: 两种模式可以同时用吗？

**可以。** 例如：
- 模式 A 用于探索性触发（"看看有什么好 Skill"）
- 模式 B 用于每日定时（07:00 推送简报）

两者互不冲突，但需要注意避免在 24 小时内重复生成简报（提示用户避免打扰）。

### Q2: Cron 模式下痛点列表多久更新一次？

**建议每 1-2 周更新一次。** 更新方式：
1. 修改定时任务的 prompt 中的痛点列表
2. 或者重新扫描 MEMORY.md 提取新痛点

### Q3: 模式 B 推送失败怎么办？

检查清单：
- [ ] IMA/飞书凭证是否正确
- [ ] 知识库 ID 是否有效
- [ ] 网络是否能访问 api.skillhub.cn
- [ ] 查看 `data/logs/` 中的错误日志

### Q4: 可以先试用 A 再升级到 B 吗？

**强烈推荐。** 先用模式 A 跑几天，体验推荐质量，然后：
1. 确定你满意的痛点列表
2. 创建 Cron 定时任务
3. 切换到模式 B
