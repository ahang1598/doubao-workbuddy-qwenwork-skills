# 门店任务中心自动派发系统 (store-inspection)

基于钉钉 AI 表格（Aitable）和 `dws` CLI 工具，实现门店巡店任务的全自动派发、提醒、上报与汇总闭环。

> 详细需求见 [docs/requirements-store-inspection.md](./docs/requirements-uv run python scripts/cli.py.md)。

## 架构概览

```
┌──────────────────┐    ┌────────────────────┐    ┌──────────────────────┐
│  Aone Copilot    │    │   Agent 定时器     │    │  钉钉 AI表格          │
│  Skill (Agent)   │    │  （外部周期调度）  │    │ 3 固定表 + 动态表    │
└────────┬─────────┘    └────────┬───────────┘    └──────────┬───────────┘
         │                       │                            ▲
         │ store-inspection CLI 子命令                   │
         ▼                       ▼                            │
   ┌────────────────────────────────────────────────────────────┐
   │  store_inspection Python 包                           │
   │  init / store / template / dispatch / summary / monitor    │
   └────────────────────────┬───────────────────────────────────┘
                            │ subprocess
                            ▼
              dws (-y -f json)
```

- **Skill 模式**：管理者通过 Aone Copilot 自然语言对话触发，由 `.aone_copilot/skills/store-inspection/SKILL.md` 引导 Agent 调用 CLI。
- **定时调度由 Agent 定时器完成**：本系统不内置 daemon / cron，所有 CLI 子命令都是一次性调用；周期性派发、提醒、汇总通过 Agent 定时器（或外部任意调度器）按计划触发对应子命令实现。

## 3 张固定表 + 2 张动态表

**3 张固定表**（系统初始化时创建，表名硬编码不可改）：

| 表名 | 职责 |
| :--- | :--- |
| 门店清单 | 门店与店长的对应关系（基础数据） |
| 巡店模版 | 任务"蓝图"：派发范围 + 自定义字段 + 时间策略 |
| 任务记录 | 每次派发的任务元信息（task_id / 表 ID / form_url / 统计） |

**2 张动态表**（每次派发时自动创建，与任务一对一）：

| 表名 | 职责 |
| :--- | :--- |
| `{模版名称}-{YYYYMMDD}` | 动态任务表，店长通过表单视图填写巡检数据 |
| `{模版名称}-{YYYYMMDD}-通知` | 动态通知表，记录每次派发的通知发送明细 |

> ⚠️ **3 张固定表的表名禁止修改**，是系统识别表的唯一稳定标识。
> 动态表由系统按命名规则自动管理，不要手动改名。

## 快速开始

### 1. 前置条件

- Python ≥ 3.9
- `dws` CLI 已安装在 `dws`
- 当前钉钉账号具备 AI 表格读写、单聊消息发送、通讯录读取权限
- 通过 `dws contact user get-self` 校验 corpId 与 AI表格 归属一致

### 2. 安装

```bash
pip install -e .[dev]
```

### 3. 系统初始化（任选其一）

```bash
# 模式 A：新建 AI表格
uv run python scripts/cli.py init create --name "门店巡店任务中心"

# 模式 B：从已有 AI表格 中查询选择
uv run python scripts/cli.py init query --keyword 巡店

# 模式 C：通过 URL 或 BASE_ID 绑定
uv run python scripts/cli.py init url "https://docs.dingtalk.com/i/nodes/BAS_xxx?..."
```

### 4. 维护门店与模板

```bash
uv run python scripts/cli.py store add --store-id S001 --store-name 北京朝阳店 \
    --tags 华北,旗舰店 --manager-user-id u_zhangsan --manager-name 张三

uv run python scripts/cli.py template create --name 每日巡检 \
    --description "请完成今日巡检：{表单链接}" \
    --form-id viw_xxx --form-base-url "https://..."
```

### 5. 配置定时调度（由 Agent 定时器完成）

本系统不内置定时器。需要周期性派发 / 汇总 / 提醒时，请在 **Aone Copilot Agent
的定时器**（或任意外部调度器）中按计划周期性调用对应 CLI 子命令，例如：

| 频率 | 命令示例 | 用途 |
| :--- | :--- | :--- |
| 每天 09:00（步骤 1） | `uv run python scripts/cli.py dispatch init --template-id TPL_xxx` | 建/复用当日任务表，输出 task_id |
| 每天 09:00（步骤 2） | `uv run python scripts/cli.py dispatch notify --task-id <task_id> --on-duplicate skip` | 通知目标门店 |
| 每天 12:00 | `uv run python scripts/cli.py summary run --template-id TPL_xxx` | 推送当日汇总报表 |
| 自定义 | `uv run python scripts/cli.py monitor query --notify-status sent --completion-status pending` | 配合提醒流程查询未完成门店 |

模板里的 `dispatch_time` / `summary_time` 等 cron 字段保留为「期望调度时间」
的元信息（供 Agent 在配置定时器时参考），但 CLI 本身不会读取它们做窗口判断。

部署细节参见 [deploy/DEPLOY.md](./deploy/DEPLOY.md)。

## 单元测试

```bash
PYTHONPATH=. pytest -v --cov=scripts --cov-report=term-missing
```

测试全部 mock `subprocess.run`，不会真实调用 `dws`，可在无网络/无钉钉权限的环境运行。

## 目录结构

```
.
├── pyproject.toml
├── README.md
├── SKILL.md                                    # Skill 触发声明（Aone Copilot 入口，路由器形态）
├── references/                                 # Skill 子文档（按"配置时 / 运行时 / 共享"分层）
│   ├── shared/                                 # 跨阶段共享参考（单一来源）
│   │   ├── glossary.md                         # 术语 / 系统架构 / ID / 时区
│   │   ├── hard-constraints.md                 # 全部硬约束 H1～H6
│   │   ├── placeholders.md                     # 消息占位符 + Markdown 渲染规则
│   │   └── data-model.md                       # 表 / 字段 / 统计口径
│   ├── setup/                                  # 配置时（一次性 / 偶发）
│   │   ├── README.md                           # 场景速查
│   │   ├── 01-init.md                          # init 命令族 + 首次使用处方
│   │   ├── 02-store.md                         # store 命令族 + 维护门店处方
│   │   ├── 03-template.md                      # template 命令族 + 起草消息文案处方
│   │   └── 04-share.md                         # share 命令族 + 分享/接收处方
│   └── runtime/                                # 运行时（高频 / 周期性）
│       ├── README.md                           # 场景 + 命令双向速查
│       ├── 01-dispatch.md                      # dispatch 全部子命令 + 派发处方 + 流程详解
│       ├── 02-monitor.md                       # monitor + 通知明细 + 催办处方
│       ├── 03-summary.md                       # 汇总报表
│       └── 04-stats.md                         # 统计
├── docs/                                       # 仓库内开发文档（不参与 Skill 触发）
│   ├── requirements-store-inspection.md   # 业务需求文档
│   └── feature/                                # 历史 feature 笔记
├── deploy/
│   └── DEPLOY.md                               # Agent 定时器配置说明
├── scripts/                                    # 全部 Python 代码（可执行 + 库）
│   ├── cli.py / app.py
│   ├── commands/                               # 命令层（BaseCommand + 装饰器自动注册）
│   ├── services/                               # 服务编排层
│   ├── infrastructure/                         # 基础设施层（外部 IO）
│   ├── domain/                                 # 领域层（纯函数 + 数据结构）
│   └── utils/                                  # 通用工具
└── tests/                                      # 单元测试（mock dws）
```

> Skill 入口：[`SKILL.md`](./SKILL.md) → 配置时入口 [`references/setup/README.md`](./references/setup/README.md)
> 与运行时入口 [`references/runtime/README.md`](./references/runtime/README.md)。

## 设计要点

- **仅持久化 `BASE_ID`**：5 张表的 `tableId` / 字段的 `fieldId` 通过固定中文表名/字段名实时映射，会话内缓存，避免缓存不一致。
- **状态回写不依赖 AI 表格 automation**：改用主动轮询业务表（默认 5 分钟一次），文档明确指定的方案（dws 不支持 automation 的程序化创建）。
- **派发/提醒/汇总不内置定时器**：所有 CLI 子命令都是一次性调用，定时调度由 Agent 定时器（或任意外部调度器）按计划周期触发对应子命令完成。
- **混合命令注册模式**：`BaseCommand` 基类 + `@register_command` 装饰器 + 自动扫描，新增命令族只需新建文件。
- **Skill 文档分层**：`SKILL.md` 路由器 + `references/{shared,setup,runtime}` 三层；Agent 按操作阶段只加载对应子文档，避免上下文膨胀。
