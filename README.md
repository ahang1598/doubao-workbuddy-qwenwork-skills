# AI Skills & Experts Archive

归档本机各 AI 工具（Doubao、WorkBuddy、QwenWork、ChatGPT）的 skills、experts 及插件市场内容，通过定时任务每日自动同步、提交并推送。

## 目录结构

```text
.
├── doubao/          # 豆包（skills）
├── workbuddy/       # WorkBuddy（skills / experts / connectors）
├── qwenwork/        # QwenWork（skills / experts / connectors）
├── chatgpt/         # ChatGPT Codex（system skills / plugins）
├── scripts/         # 同步脚本与计划任务注册
└── README-*.md      # 各平台索引（自动生成）
```

各平台目录内含：

- `SUMMARY.md` — 按用途分组的导航索引
- `change-logs/` — 每次同步的变更记录
- `archive/deleted/` — 已删除内容归档

## 平台索引

| Platform | Directory | Index |
| --- | --- | --- |
| Doubao | `doubao/` | [README-doubao.md](README-doubao.md) |
| WorkBuddy | `workbuddy/` | [README-workbuddy.md](README-workbuddy.md) |
| QwenWork | `qwenwork/` | [README-qwenwork.md](README-qwenwork.md) |
| ChatGPT | `chatgpt/` | [README-chatgpt.md](README-chatgpt.md) |

## 使用

手动同步单个平台：

```bash
python3 scripts/sync_platform.py --platform <doubao|workbuddy|qwenwork|chatgpt>
```

常用选项：

- `--commit --push` — 同步后自动提交并推送
- `--dry-run` — 仅预览变更，不写入
- `--refresh-docs` — 强制刷新索引文档

同步脚本会更新平台数据、生成 `README-<platform>.md` 与各目录的 `SUMMARY.md`，并写入 `change-logs/` 变更记录。

## 自动同步

Windows 计划任务每天 18:00 在 WSL 中运行各平台同步（范围互不重叠）：

```powershell
# 注册/更新计划任务（默认 Ubuntu-22.04，每天 18:00）
powershell -File scripts/register-windows-task.ps1
```
