---
name: skillhub-daily
description: 'SkillHub 每日推荐 - 扫描 skillhub.cn 全站 Top100 + 7 大分类各 Top20（共 240 个 Skill），

  基于用户痛点精准推荐高价值 Skill，支持 IMA/飞书/Obsidian 多通道存储。

  触发词：每日推荐、SkillHub 日报、潜力Skill、帮我推荐技能。

  支持两种使用模式：常规 Skills 模式（对话触发）/ Cron 定时任务模式。

'
version: 6.2.0
metadata:
  author: SkillHub-Community
  platforms:
    - qclaw
    - workbuddy
    - openclaw
    - hermes
    - script
  modes:
    - interactive
    - cron
license: MIT
github: https://github.com/skillhub-community/skillhub-daily
display_name: "SkillHub 每日推荐"
display_name_en: "SkillHub Daily Recommendations"
description_zh: "基于 SkillHub (skillhub.cn) 全站数据，每日扫描 Top100 热门 Skill 与 7 大分类各 Top20（共 240 个），结合用户工作痛点精准推荐高价值 Skill。支持常规对话触发与 Cron 定时任务双模式，简报可推送至 IMA 知识库、飞书云文档、Obsidian 或本地存储。"
description_en: "Daily scan of SkillHub (skillhub.cn) Top 100 + Top 20 in each of 7 categories (240 Skills total), delivering personalized high-value Skill recommendations based on user pain points. Supports both conversational triggers and Cron scheduled tasks, with briefings pushable to IMA KB, Feishu docs, Obsidian, or local storage."
visibility: "public"
---

# SkillHub 每日推荐 v6.2

每日扫描 SkillHub (skillhub.cn)，基于用户痛点精准推荐高价值 Skill，输出结构化简报。

**核心特点**：
- 🎯 **痛点驱动**：先理解用户需要什么，再推荐什么，不推热门推对路
- 💎 **信息差优先**：收藏率比下载量更真实——"试了就留下"比"试试就扔"更有价值
- 🔄 **跨平台适配**：同一套 SKILL.md，WorkBuddy / qclaw / OpenClaw / Hermes / 纯脚本自动适配
- 🔌 **双模式支持**：常规 Skills 模式（对话触发） / Cron 定时任务模式
- 📦 **多通道存储**：IMA 知识库 / 飞书云文档 / Obsidian / 本地四通道并存

## ⚠️ 首次使用必读

**Skill 加载后，必须主动询问用户使用模式：**

> "欢迎使用 SkillHub 每日推荐！请选择使用模式：
>
> **🔵 模式 A：常规 Skills 模式**（推荐新手）
> - 在对话中说"每日推荐"、"SkillHub 日报"等触发词即可调用
> - 每次执行自动扫描你的记忆文件，发现新痛点
>
> **🟢 模式 B：Cron 定时任务模式**（推荐重度用户）
> - 在 Agent 平台配置定时任务（如每日 07:00 自动执行）
> - 痛点列表在 prompt 中预设，不需要每次扫描记忆
> - 简报自动推送到飞书/微信/IMA 知识库
>
> 请输入 A 或 B。"

详细对比见 [references/setup-wizard.md](references/setup-wizard.md)

## 前置检查

在执行 Skill 前，先验证环境：

```bash
python --version    # 需要 ≥ 3.10
node --version      # 需要 ≥ 18（仅 IMA 推送需要）
```

脚本会自动检测 Python 版本，若当前解释器过低会尝试回退到 `python3.10`/`python3.11`/`python3.12`。

## 执行流程

```
步骤 1: 模式识别（常规/Cron）→ 决定痛点来源
步骤 2: 记忆扫描 → 提取痛点（Cron 模式从 prompt 读取）
步骤 3: 数据抓取 → potential_slim.json
步骤 4: 痛点 × 类别交叉匹配 → 精准选品
步骤 5: 生成简报 → 保存到 data/reports/
步骤 6: 多通道存储（IMA/飞书/Obsidian/本地）
步骤 7: 输出对话摘要（200 字以内）
```

### 步骤 1：模式识别

| 调用方式 | 模式 | 痛点来源 |
|---------|------|---------|
| 对话中触发词 | 常规模式 | 动态扫描 MEMORY.md + 最近 3 天日志 + gbrain |
| Cron 定时任务 | Cron 模式 | **直接使用 prompt 中给出的痛点**，不重复扫描 |
| 纯脚本 | - | 无痛点，使用通用推荐 |

### 步骤 2：记忆扫描（仅模式 A）

**痛点来源**（按优先级）：

| 优先级 | 来源 | 路径 | 平台 |
|--------|------|------|------|
| 1 | 工作区每日日志 | `memory/YYYY-MM-DD.md`（最近 3 天） | OpenClaw/Hermes/qclaw |
| 2 | 工作区长期记忆 | `MEMORY.md` | OpenClaw/Hermes/qclaw |
| 3 | GBrain 知识库 | `gbrain search <topic>` | 有 gbrain 时 |
| 4 | 用户级记忆 | 平台特定 | WorkBuddy |

**痛点 → 分类映射**：

| 痛点关键词 | 映射分类 |
|-----------|---------|
| 投研/金融/量化/股票/财报 | `data-analysis` |
| AI/Agent/MCP/RAG/模型 | `ai-intelligence` |
| 开发/调试/部署/CI/CD | `developer-tools` |
| 小红书/设计/卡片/文案 | `content-creation` |
| 自动化/效率/飞书/同步 | `productivity` |
| 安全/合规/审计/扫描 | `security-compliance` |
| 协作/会议/文档/邮件 | `communication-collaboration` |

### 步骤 3：数据抓取

```bash
cd ${SKILL_DIR}
python scripts/skillhub_daily.py --slim --no-html --data-dir ./data
```

- `${SKILL_DIR}` = 本 SKILL.md 所在目录的绝对路径
- `--slim`：裁剪冗余字段，保留 240 个 Skill 完整覆盖，体积减少 ~32%
- `--no-html`：跳过 HTML 报告

**输出**：
- `data/potential_slim.json`：结构化数据
- `data/snapshots/YYYY-MM-DD.json`：每日快照
- `data/reports/YYYY-MM-DD-briefing.md`：原始简报

### 步骤 4：痛点 × 类别交叉匹配

读取 `data/potential_slim.json` 中的 `category_analysis` + `category_skills`，按痛点匹配分类。

**匹配规则**：
1. 每个痛点 → 1-2 个分类 → 找该分类中匹配的 Skill
2. **必须查看** `hidden_gems_in_category`（收藏率高但不在 Top100 的——真正信息差）
3. 筛选结果：
   - **今日推荐**：3-5 个最匹配痛点的 Skill
   - **被埋没的金子**：收藏率 Top5 但排名 > 20 的
   - **全站潜力 Top10**：按 `potential_score` 排序

### 步骤 5：生成简报

保存到 `data/reports/YYYY-MM-DD-briefing.md`

**格式严格遵循** [references/briefing-template.md](references/briefing-template.md)：

- 标题：含完整日期
- 痛点行：3-6 个核心痛点
- 今日推荐：3-5 个，每个含匹配痛点 + 推荐理由 100-150 字 + 核心能力 + 安装命令
- 被埋没的金子：5 列表格
- 全站潜力 Top10：6 列表格
- 分类速览：7 大分类
- 页脚：生成时间 + 扫描范围 + 个性化说明

### 步骤 6：多通道存储

**存储通道由调度方指定**：

#### 通道 A：IMA 知识库

```bash
python scripts/push_to_ima.py "data/reports/YYYY-MM-DD-briefing.md" "SkillHub 每日简报 | YYYY-MM-DD"
```

**凭证来源**（优先级）：环境变量 → `references/config.json` → `~/.qclaw/skills/ima-skill/config.json` → `~/.workbuddy/skills/ima-skill/config.json`

#### 通道 B：飞书云文档

```bash
# qclaw / OpenClaw
feishu_doc create
feishu_doc write
feishu_doc read  # 验证

# WorkBuddy / Hermes
lark-cli doc create/write
```

⚠️ 飞书文档必须三步：create → write → read 验证

#### 通道 C：本地存储

简报已保存到 `data/reports/`，无需额外操作。

#### 通道 D：Obsidian

复制简报到 `{OBSIDIAN_VAULT}/SkillHub/YYYY-MM-DD.md`

### 步骤 7：输出对话摘要

**直接在当前对话中输出摘要**——Cron 任务的对话上下文本身就是推送通道（飞书/微信），不需要额外推送步骤。

**摘要格式**（200 字以内，无表格）：

```
📊 SkillHub 今日推荐 | YYYY-MM-DD
基于您的[N]个痛点，今日精选[X]个技能
🎯 [技能1] — [价值]
💎 被埋没的金子：[技能名]（收藏率[X]%，排名#[N]）
📊 今日扫描：240个技能 | 7大分类 | [X]个潜力识别
详情见[存储位置]
```

## 交互规则清单

### 必须做 ✅

- **首次加载必须询问使用模式**（常规 / Cron）
- Cron 模式 prompt 已含痛点时直接使用，不重复扫描
- 步骤 3 必须使用 `--slim` 模式
- 推荐必须包含功能描述 + 解决痛点 + 使用场景
- 必须查看 `hidden_gems_in_category`
- 凭证从配置文件读取，**禁止反复询问用户**

### 何时不应触发 ⚠️

- 用户明确说"不要推荐 SkillHub"或"暂停每日推荐"
- 用户只想单次查询某个 Skill 详情（应直接用搜索功能）
- 用户的网络环境无法访问 skillhub.cn / api.skillhub.cn
- 24 小时内已经执行过完整流程（除非用户主动要求）
- 用户没有明确痛点且未授权访问记忆文件（仅模式 A）
- 当前为调试/测试模式

### 不能做 ❌

- 不能硬编码痛点列表
- 不能减少扫描覆盖量（必须 240 个 Skill/天）
- 不能用下载量代替收藏率做质量判断
- 不能在输出中暴露用户个人信息或 API 密钥
- **不能在步骤 7 之后再调用 message 工具推送**——对话上下文本身就是推送

## 跨平台支持

| 平台 | 模式 A | 模式 B (Cron) | 凭证位置 | 推送方式 |
|------|--------|---------------|---------|---------|
| **qclaw** | ✅ | ✅ | `~/.qclaw/skills/ima-skill/config.json` | Cron `announce` |
| **WorkBuddy** | ✅ | ✅ | `~/.workbuddy/skills/ima-skill/config.json` | 渠道对话 |
| **OpenClaw** | ✅ | ✅ | `~/.openclaw/skills/ima-skill/config.json` | Cron `announce` |
| **Hermes** | ✅ | ✅ | 平台特定 | webhook/API |
| **纯脚本** | ❌ | ❌ | 环境变量 | 外部管道 |

详见 [references/platform-adapters.md](references/platform-adapters.md)

## Cron 定时任务配置

本 Skill 被设计为可由定时任务驱动的无头执行模式。定时任务通过 prompt 指定痛点列表和存储通道，Skill 按指令执行。

**qclaw 飞书推送**（每日 07:00）：

```json
{
  "schedule": { "kind": "cron", "expr": "0 7 * * *", "tz": "Asia/Shanghai" },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "请执行 skillhub-daily Skill，按 SKILL.md 步骤 1-7 完成每日推荐。\n\n# 痛点（请直接使用，不再扫描记忆）\n- YouTube 字幕提取\n- 股票分析\n- n8n 工作流\n- Markdown 转换\n- 桌面自动化\n- 文档管理\n\n# 存储通道\n飞书云文档\n\n请完成后输出 200 字以内的对话摘要。"
  },
  "delivery": { "mode": "announce", "channel": "feishu" }
}
```

更多模板见 [references/prompt-templates.md](references/prompt-templates.md)

## References 索引

| 文件 | 何时加载 |
|------|---------|
| [references/setup-wizard.md](references/setup-wizard.md) | 首次加载 Skill、用户选择模式 A/B 时 |
| [references/platform-adapters.md](references/platform-adapters.md) | 跨平台配置、凭证管理 |
| [references/prompt-templates.md](references/prompt-templates.md) | 配置 Cron 定时任务 |
| [references/briefing-template.md](references/briefing-template.md) | 生成简报时遵循格式 |
| [references/config.md](references/config.md) | 配置 IMA/飞书/Obsidian 凭证 |
| [references/source-contract.md](references/source-contract.md) | 需要了解 API 契约时 |

## 数据源

- **API 基地址**：`https://api.skillhub.cn`（无需认证）
- **主接口**：`GET /api/skills?page=N&pageSize=50&sortBy=downloads&order=desc`
- **分类**：`GET /api/v1/categories` → `GET /api/skills?category={key}&pageSize=20`
- **详情**：`GET /api/v1/skills/{slug}`

## License

MIT
