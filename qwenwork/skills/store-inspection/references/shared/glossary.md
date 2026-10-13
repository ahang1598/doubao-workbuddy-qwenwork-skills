# 术语表 / 系统架构 / ID 与时间约定

> 全局共享参考。SKILL.md / setup/ / runtime/ 各文档遇到术语或架构相关概念时，
> 一律链接到本文件，**不要复制内容**，避免多处不一致。

---

## 术语表

| 术语 | 含义 |
| :--- | :--- |
| **Skill** | 一种「SKILL.md + 子文档」式的可复用 Agent 能力包规范；本仓库实现的 Skill 名为 `store-inspection`，可被任意支持该规范的 Agent 宿主环境加载 |
| **调用方 Agent** | 加载并调用本 Skill 的通用 Agent（不限定具体宿主，例如任意 LLM Agent / IDE 助手 / CLI Agent 等） |
| **外部调度器** | 用户自有的任意周期触发工具（cron / Agent 宿主环境定时器 / k8s CronJob / 任务平台等）；本 Skill **不内置** daemon 也不强依赖某个具体调度器，所有 CLI 子命令都是一次性调用，详见 `hard-constraints.md#H6` |
| **AI表格** | 钉钉 AI 表格的"工作簿"，由 `BASE_ID`（形如 `BAS_xxx`）唯一标识；一个 Skill 实例固定绑定一个 AI表格 |
| **3 张固定表** | 系统识别表，表名硬编码不可改：`门店清单` / `巡店模版` / `任务记录` |
| **动态任务表** | 每次派发动态创建的巡检数据表，命名规则 `{模版名称}-{YYYYMMDD}`（如 `每日巡检-20260424`），店长通过表单视图填写 |
| **动态通知表** | 每次派发动态创建的通知发送明细表，命名规则 `{模版名称}-{YYYYMMDD}-通知`，与动态任务表一对一 |
| **task_id** | 一次派发任务的唯一编号，格式 `TASK_{template_id}_{yyyyMMddHHmm}` |
| **template_id** | 模板唯一编号，格式 `TPL_{yyyyMMddHHmmss}_{rand4}` |
| **store_id** | 门店唯一业务编码，由用户自定义，推荐 `S001` `S002`；一旦创建禁止修改 |
| **form_url** | 店长用于填写巡检表的"表单分享链接"，格式必须包含 `/notable/share/form/` 或 `/share/form/`；首次派发后持久化到任务记录，复用任务直接读取 |
| **骨架字段** | 动态任务表中由系统自动创建的固定字段（`store_id` / `store_name` / `task_id` / `template_id` / `submitted_at` 等）；不可被 `dispatch update-instance` 修改 |
| **自定义字段** | 由模板的 `custom_fields` 定义、追加到动态任务表骨架字段之后的字段；可被店长填写或 `dispatch update-instance` 修改 |

---

## 系统架构概览

```
┌──────────────────┐    ┌────────────────────┐    ┌──────────────────────┐
│  调用方 Agent    │    │  外部调度器(可选)  │    │  钉钉 AI表格 │
│  (加载 Skill)    │    │  cron / 定时平台   │    │  3 固定表 + 动态表    │
└────────┬─────────┘    └────────┬───────────┘    └──────────┬───────────┘
         │                       │                            ▲
         │ store-inspection CLI 子命令                   │
         ▼                       ▼                            │
   ┌────────────────────────────────────────────────────────────┐
   │  scripts/  Python 包                                       │
   │  init / store / template / dispatch / summary / monitor /  │
   │  stats / share                                             │
   └────────────────────────┬───────────────────────────────────┘
                            │ subprocess
                            ▼
                          dws CLI（PATH 中）
```

```
固定表（3 张，init 时创建）：
  门店清单    — 门店与店长基础信息
  巡店模版    — 任务蓝图：派发范围 + 自定义字段定义 + 时间策略
  任务记录    — 每次派发的任务元信息（task_id / 表 ID / form_url / 统计）

动态表（每次派发时创建，2 张一对）：
  「{模版名称}-{YYYYMMDD}」
    字段 = 骨架字段 + 模版自定义字段；店长通过表单视图直接在此表提交
  「{模版名称}-{YYYYMMDD}-通知」
    每次派发的通知发送记录，与任务表一对一
```

> 所有派发 / 提醒 / 汇总都是 CLI 一次性调用，Skill **不内置** daemon。
> 用户若需要周期触发，请自行用任意外部调度器（cron / Agent 宿主环境定时器 / k8s CronJob 等）调用对应 CLI 子命令；详见 `hard-constraints.md#H6`。

---

## ID 生成策略

| ID | 格式 | 生成时机 |
| :--- | :--- | :--- |
| `template_id` | `TPL_{yyyyMMddHHmmss}_{rand4}` | `template create` 时 |
| `task_id` | `TASK_{template_id}_{yyyyMMddHHmm}` | `dispatch init` 时 |
| `notification_id` | `NOTIF_{task_id}_{store_id}` | 写入动态通知表时 |
| `store_id` | 用户自定义，推荐 `S001` `S002` | `store add` 时 |

---

## 时区与时间格式

- 所有时间字段统一**北京时间（`+08:00`）**。
- date 字段格式：`YYYY-MM-DD HH:mm:ss`。
- cron 表达式：按本机时区解释（部署时建议设为 `Asia/Shanghai`）；
  CLI 本身**不消费 cron 字段**，仅作为「期望调度时间」记录给调用方 Agent 的定时器参考。
- 5 段 cron 标准 / 6 段 Quartz（首段为秒）均支持，例：
  - `0 9 * * *` — 每天 09:00（标准）
  - `0 0 9 * * ?` — 每天 09:00（Quartz）

---

## 数据 / 配置位置

| 用途 | 路径 | 说明 |
| :--- | :--- | :--- |
| Skill 配置（base_id） | `$AGENT_WORK_ROOT/workspace/store-inspection/config.json` | 优先路径；`AGENT_WORK_ROOT` 未设置时兜底到 `~/.store-inspection/config.json` |
| 显式覆盖 | 环境变量 `STORE_TASK_DISPATCHER_CONFIG` | 任何环境都可通过此变量直接指定 config.json 绝对路径 |
| Skill 同步状态 | 与 `config.json` 同目录的 `sync_state.json` | CLI 自动读写，记录上次同步时间戳 |
| dws CLI | `dws`（PATH 中） | 统一通过 PATH 查找 |
