# 本机其他 agent 任务探测（agent-tasks-listing）

> 目录下脚本用于探测本机非千问办公的 coding agent 历史任务（qoder / codex / claudecode / qoderwork 已支持解析）。
> 用 `python3` 调用，**建议 `run_in_background` 后台执行**（脚本只读本地存档，不依赖 dws auth；前台会长时间阻塞其它任务）。stdout 只输出 JSON，日志走 stderr。

## 先探测装了哪些 agent（首次建台账时用它确定同步范围）

```bash
python3 scripts/agent-tasks-listing/agent_discovery.py
# 输出 summary.recommendedDefaults = 可立即同步的 agent id（probe 已完整支持且有存档）
```

首次建个人台账时：跑完 discovery 后，用 AskUserQuestion 问用户「要同步哪些 agent 的台账」（千问办公默认勾选，本地 agent 逐个勾选），把选择结果记到 memory，后续同步只同步选中的 agent。

## 拉任务列表（输出对齐 qwenwork.tasks，默认近一天）

```bash
# 默认近一天（日常增量同步用这个，不要拉全部）
python3 scripts/agent-tasks-listing/agent_task_probe.py --list --since-days 1

# 指定 agent / 条数
python3 scripts/agent-tasks-listing/agent_task_probe.py --list --agent qoder --limit 20

# 全量（仅首次建台账做基线时用）
python3 scripts/agent-tasks-listing/agent_task_probe.py --list
```

> stdout 默认就是纯 JSON，**没有 `--json` 参数**，别加。
> **默认不要用裸 `--list` 拉全部**：本地 agent 存档量大且变化慢，日常同步用 `--since-days 1` 近一天即可；只有首次建台账做基线时才允许全量。

返回每条任务字段：`chatId`（`qoder:xxx` / `codex:xxx` / `claudecode:xxx` / `qoderwork:xxx`）、`title`、`status`、`createdAt`、`updatedAt`、`chatType`、`sourceChatId`，以及扩展 `agent/summary/cwd/messageCount/file/outputFiles`。写入台账时：`chatId` **去掉 agent 前缀写裸 ID**（`qoder:abc` → 写 `abc`）→「任务ID」，`agent` →「Agent类型」，`summary` →「一句话摘要」。前缀只用于 probe 命令寻址（如 `--detail`），不得写进台账。其中 `outputFiles` 是本机探测到的该任务产出文件列表，每项 `{path, exists}`，可直接用于「产出物/工作文件」上传判断（exists=true 才上传）。

## 拉详情 / 搜索

```bash
python3 scripts/agent-tasks-listing/agent_task_probe.py --detail "qoder:<sessionId>"
python3 scripts/agent-tasks-listing/agent_task_probe.py --search "<关键词>"
```

## 验证 probe（v2 自带回归）

```bash
python3 scripts/agent-tasks-listing/verify_probe.py
# 逐 agent --list / --detail / --agent all 校验字段契约、outputFiles 结构、去重，全绿才通过
```

## 已知限制（写 reference 必读）

- 只扫本机存档，拿不到云上/在线 agent；`qoderwork` 仅能扫到本机工作区输出，不是千问办公实时任务（千问办公走 qwenwork.tasks）。
- 状态统一映射 `completed`（本机存档落盘即视为已结束），**拿不到 running**，与 qwenwork.tasks 的实时状态机不同。
- probe 的 `chatId` 带 agent 前缀，但**仅用于 CLI 寻址**（`--detail "qoder:xxx"`）；台账「任务ID」一律写裸 ID（qwenwork 本就裸），agent 区分由「Agent类型」字段承担。读已有台账去重时先剥前缀归一化再比较，避免历史前缀残留把同一任务当新增；去重键是「任务ID + Agent类型 + 创建人」。
- `outputFiles` 的 `exists` 基于本机文件系统；跨机器交接时只引用已上传到台账附件的 fileToken，不引用本地 path。
- `agent_discovery.py` 的 AGENT_REGISTRY 可扩展新增 agent。

## 沙箱与权限（实测结论，2026-08-14）

- 千问办公本地 Bash 可直接读取 `~/.qoder/projects`、`~/.codex/sessions` 等 home 目录下存档，**无需额外授权**（已实测 qoder 3280 / codex 172 个会话文件均正常读取）。
- 脚本对读不到的目录或损坏文件**静默跳过**（读取失败只写 stderr，不报错中断）。若发现任务数明显偏少，先看 stderr 有无 `读取失败` 日志，再判断是否被系统权限（如 macOS TCC 对 ~/Documents 等）挡住。
- 若未来换环境出现权限限制，应引导用户在系统设置里授权千问办公访问对应目录，而不是静默继续；不要让 probe 在拿不到数据时假装同步成功。
