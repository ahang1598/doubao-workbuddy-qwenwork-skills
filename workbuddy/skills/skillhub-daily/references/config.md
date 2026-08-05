# SkillHub 每日推荐 - 用户配置

## 0. 环境版本验证（首次必做）

在开始配置前，请先验证环境版本：

**Windows (PowerShell / CMD)**：
```powershell
python --version
node --version
```

**macOS / Linux (Bash / Zsh)**：
```bash
python3 --version
node --version
```

**版本要求**：

| 工具 | 最低版本 | 推荐版本 | 用途 |
|------|----------|----------|------|
| Python | 3.10+ | 3.11+ | 核心数据抓取脚本 |
| Node.js | 18.0+ | 20.0+ | IMA 知识库存储（可选） |

如果版本不符合：
- Python：前往 https://www.python.org/downloads/ 下载安装
- Node.js：前往 https://nodejs.org/ 下载 LTS 版本

---

## 1. 存储通道

存储通道由调度方（定时任务 prompt 或用户指令）指定。本文件记录各通道的凭证和偏好。

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `IMA_ENABLED` | 是否启用 IMA 知识库存储 | `false` |
| `LARK_ENABLED` | 是否启用飞书云文档存储 | `false` |
| `LOCAL_ENABLED` | 是否启用本地存储 | `true` |
| `OBSIDIAN_ENABLED` | 是否启用 Obsidian 同步 | `false` |
| `OBSIDIAN_VAULT` | Obsidian vault 路径 | （空） |

---

## 2. IMA 知识库配置

凭证来源优先级：
1. **环境变量** `IMA_CLIENT_ID` / `IMA_API_KEY` / `IMA_KB_ID`（最高优先级）
2. `references/config.json`（本目录下）
3. `~/.qclaw/skills/ima-skill/config.json`（qclaw 环境）
4. `~/.workbuddy/skills/ima-skill/config.json`（WorkBuddy 环境）
5. `~/.openclaw/skills/ima-skill/config.json`（OpenClaw 环境）

首次使用时填写 `references/config.json`：
```json
{
  "ima_client_id": "",
  "ima_api_key": "",
  "ima_kb_id": ""
}
```

> 凭证留空 = 不启用 IMA。填写后不再询问。

### 知识库 ID 获取

1. 打开 IMA，创建一个"SkillHub 简报"专用知识库
2. 进入知识库，复制 URL 中的长 ID（格式如 `<your_ima_kb_id>=`，约 44 字符）
3. 填入 `ima_kb_id` 字段（**请勿将真实 ID 上传到公开仓库**）

---

## 3. 飞书文档配置

| 平台 | 配置方式 |
|------|---------|
| **qclaw** | 自动使用已配置的飞书应用凭证 |
| **WorkBuddy** | 需安装 lark-cli 并执行 `lark-cli auth login` |
| **OpenClaw** | 需安装 lark-cli 并执行 `lark-cli auth login` |
| **Hermes** | 需安装 lark-cli 并执行 `lark-cli auth login` |

可选配置：

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `LARK_FOLDER_TOKEN` | 飞书目标文件夹 token | （空=根目录） |
| `OBSIDIAN_VAULT` | Obsidian Vault 路径 | （空，例如 `<your_vault_path>`） |

启用 Obsidian 后，简报会复制到 `{OBSIDIAN_VAULT}/SkillHub/YYYY-MM-DD.md`。

---

## 5. 通知说明

**本 Skill 不负责通知推送。** 推送由外部编排负责：

| 平台 | 推送机制 |
|------|---------|
| qclaw cron | `delivery.announce` → 飞书/微信 |
| WorkBuddy 定时任务 | 渠道对话直接展示 |
| OpenClaw cron | `delivery.announce` → 飞书/微信 |
| 手动触发 | 当前对话中输出 |
| 纯脚本 | 外部管道（如 `tee` / 文件输出） |

详见 [platform-adapters.md](platform-adapters.md)。

---

## 6. 自动化定时任务配置

### 6.1 跨平台 Cron 模板

详见 [prompt-templates.md](prompt-templates.md) — 包含 qclaw / WorkBuddy / OpenClaw / Hermes / 纯脚本的完整模板。

### 6.2 Windows 任务计划程序（纯脚本模式）

**图形化配置**：
1. 打开"任务计划程序"（Win+R → `taskschd.msc`）
2. 点击右侧"创建任务"
3. 配置如下：

| 选项卡 | 字段 | 配置 |
|--------|------|------|
| 常规 | 名称 | SkillHub 每日推荐 |
| 触发器 | 新建 → 每日 | 06:00 |
| 操作 | 新建 → 启动程序 | 程序：`python` |
| 操作 | 参数 | `scripts\skillhub_daily.py --slim --no-html --data-dir ./data` |
| 操作 | 起始于 | `C:\path\to\skillhub-daily` |
| 条件 | 唤醒计算机运行 | ✅ 勾选 |

**PowerShell 一键创建（管理员权限）**：

```powershell
$action = New-ScheduledTaskAction -Execute "python" -Argument "scripts\skillhub_daily.py --slim --no-html --data-dir ./data" -WorkingDirectory "C:\path\to\skillhub-daily"
$trigger = New-ScheduledTaskTrigger -Daily -At "06:00"
Register-ScheduledTask -TaskName "SkillHub 每日推荐" -Action $action -Trigger $trigger -Description "每日扫描 SkillHub 并生成推荐简报"
```

### 6.3 Linux/macOS Crontab

```bash
# 编辑 crontab
crontab -e

# 添加任务（每日 06:00）
0 6 * * * cd /path/to/skillhub-daily && python scripts/skillhub_daily.py --slim --no-html --data-dir ./data
```

---

## 7. 目录结构

```
skillhub-daily/
├── SKILL.md                    # 技能说明（Agent 入口）
├── README.md                   # 快速上手
├── _meta.json                  # 元数据
├── .gitignore
├── scripts/
│   ├── skillhub_daily.py       # 数据抓取+分析引擎
│   └── push_to_ima.py          # IMA 推送脚本
├── references/
│   ├── setup-wizard.md         # 首次安装模式选择
│   ├── platform-adapters.md    # 跨平台适配
│   ├── prompt-templates.md     # Cron 提示词模板
│   ├── briefing-template.md    # 简报格式模板
│   ├── config.md               # 本文件
│   └── source-contract.md      # API 接口契约
└── data/                       # 运行时数据（gitignore）
    ├── potential.json
    ├── potential_slim.json
    ├── snapshots/
    ├── reports/
    ├── latest.json
    └── dates.json
```

---

## 8. 故障排查

| 问题 | 解决方案 |
|------|---------|
| Python 版本过低 | 升级到 3.10+ 或安装 `python3.10` |
| Node 未安装 | 仅 IMA 推送需要，可不装 |
| IMA 推送失败 | 检查凭证、检查 `ima_kb_id` 是否有效 |
| 飞书文档为空 | 确认走 `create` + `write` + `read` 三步 |
| 简报无个性化 | 模式 A 需确保 MEMORY.md 存在且有内容 |
| Cron 不执行 | 检查时区、系统时间、cron 服务状态 |
| 凭证未生效 | 环境变量优先级高于 config.json |

更多问题见 [platform-adapters.md](platform-adapters.md) 故障排查章节。
