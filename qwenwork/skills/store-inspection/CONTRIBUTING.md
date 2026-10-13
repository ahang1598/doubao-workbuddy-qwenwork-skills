# 贡献指南

> 面向 **修改本仓库代码的开发者**。Skill 使用方与运维人员请分别看 `SKILL.md` 与 `deploy/DEPLOY.md`。

## 项目分层架构

本仓库采用 **6 层单向依赖** 的分层架构，所有 Python 代码集中在 `scripts/` 目录下。

```
┌──────────────────────────────────────────────────────────────────┐
│ scripts/cli.py             ← CLI 入口（argparse 装配 + 异常兜底）│
└────────────────┬─────────────────────────────────────────────────┘
                 ▼
┌──────────────────────────────────────────────────────────────────┐
│ scripts/commands/          ← 命令层（BaseCommand + 装饰器自动注册）│
│   ├── base.py / registry.py                                      │
│   ├── init_cmd / store_cmd / template_cmd / dispatch_cmd / ...   │
└────────────────┬─────────────────────────────────────────────────┘
                 ▼
┌──────────────────────────────────────────────────────────────────┐
│ scripts/app.py             ← 应用层（AppContext IoC 容器）        │
│   - cached_property 懒加载所有 Service                            │
│   - 全局共享 DwsClient + MappingCache                             │
└────────────────┬─────────────────────────────────────────────────┘
                 ▼
┌──────────────────────────────────────────────────────────────────┐
│ scripts/services/          ← 服务层（业务用例编排）               │
│   ├── initializer / store_service / template_service             │
│   ├── messenger / dispatcher / reminder                          │
│   ├── sync_engine / summary / monitor                            │
└──────┬─────────────────────────────────┬─────────────────────────┘
       ▼                                 ▼
┌──────────────────────────┐   ┌──────────────────────────────────┐
│ scripts/infrastructure/  │   │ scripts/domain/                  │
│  ← 基础设施（外部 IO）   │   │  ← 领域（纯函数 + 数据结构）      │
│  - dws_client            │   │  - exceptions / schema / filters │
│  - config / sync_state   │   │  - records / form_link_builder   │
│  - mapping_cache         │   │                                  │
└──────────┬───────────────┘   └──────────────────────────────────┘
           ▼
┌──────────────────────────────────────────────────────────────────┐
│ scripts/utils/             ← 通用工具（无业务依赖）              │
│   - cron / output                                                │
└──────────────────────────────────────────────────────────────────┘
```

### 各层职责

#### domain/ — 领域层

**纯领域知识**，不涉及任何 IO，不依赖 infrastructure。

- `exceptions.py` ：所有自定义异常（`StoreTaskDispatcherError` 体系）。
- `schema.py`     ：4 张表的字段定义（单一数据源）。
- `filters.py`    ：dws record query 的 filter 结构化 JSON 构造助手。
- `records.py`    ：dws record 与业务 dict 的相互转换助手（依赖 mapping_cache 拿 fieldId）。
- `form_link_builder.py` ：表单链接 + prefill 拼接。

#### infrastructure/ — 基础设施层

**与外部世界的所有 IO 都集中在这里**，便于测试统一 mock。

- `dws_client.py`    ：dws CLI 子进程封装，自动追加 `-y -f json`，含 3 次指数退避重试。
- `config.py`        ：`.aone_copilot/store-inspection/config.json` 读写。
- `sync_state.py`    ：sync_state.json（增量同步游标）。
- `mapping_cache.py` ：tableId / fieldId 会话级缓存。

#### services/ — 服务层

业务用例的核心实现。每个 Service 类都是无状态的"动词"集合，依赖 infrastructure + domain。

- 基础服务：`initializer / store_service / template_service / messenger / monitor`
- 编排服务：`dispatcher / reminder / sync_engine / summary`

#### app.py — 应用层（IoC 容器）

`AppContext` 通过 `functools.cached_property` 懒加载所有 Service，
保证一次 CLI 调用内复用同一份 `DwsClient` 与 `MappingCache`。
测试中可继承 `AppContext` 并覆盖 `cached_property` 注入 mock。

#### commands/ — 命令层

**混合命令注册模式**：

- 基类 `BaseCommand` 定义 `name / help / configure(parser)` 三件事。
- 类装饰器 `@register_command` 把子类注册到全局 `registry`。
- `load_all_commands()` 用 `pkgutil.iter_modules` 自动扫描本包内模块。

#### cli.py — 入口

仅做三件事：触发命令注册 → 装配 argparse → 派发到 `args.func(args, ctx)`，并兜底异常。

### 命名约定

- 文件名 `xxx_cmd.py` / `xxx_service.py`：避免与 Python 标准模块冲突，明确层归属。
- 服务类名保留业务语义（如 `StoreManager` / `TemplateManager` / `Dispatcher`），不强行加 `Service` 后缀。
- 私有辅助函数 / 模块级常量统一以下划线开头（`_extract_xxx`、`_DEFAULT_COLUMNS`）。

### 允许 / 禁止的依赖

| 来源 | 允许依赖 | 禁止依赖 |
| :--- | :--- | :--- |
| domain | 仅自己 | infrastructure / services / commands |
| infrastructure | domain（exceptions） | services / commands |
| services | domain / infrastructure / utils | commands / cli / 其他 services（除非走 AppContext 注入） |
| commands | app（AppContext） / utils / domain.exceptions | 直接 import services 中的具体实现细节 |
| cli | commands / app / utils / domain.exceptions | services / infrastructure（间接通过 AppContext） |

---

## 添加一个新命令族

以新增 `report` 命令族为例，包含 `report daily / report weekly` 两个子命令。

### 1. 新建命令模块文件

`scripts/commands/report_cmd.py`：

```python
"""``report`` 命令族：临时报表生成。"""

from __future__ import annotations

import argparse

from scripts.app import AppContext
from scripts.commands.base import BaseCommand
from scripts.commands.registry import register_command
from scripts.utils.output import print_json


@register_command
class ReportCommand(BaseCommand):
    name = "report"
    help = "临时报表"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        sub = parser.add_subparsers(dest="subcommand", required=True)

        rd = sub.add_parser("daily", help="生成日报")
        rd.add_argument("--date", required=True, help="YYYY-MM-DD")
        rd.set_defaults(func=_daily)

        rw = sub.add_parser("weekly", help="生成周报")
        rw.add_argument("--week", required=True, help="ISO week, 如 2026-W17")
        rw.set_defaults(func=_weekly)


def _daily(args, ctx: AppContext) -> int:
    print_json({"type": "daily", "date": args.date})
    return 0


def _weekly(args, ctx: AppContext) -> int:
    print_json({"type": "weekly", "week": args.week})
    return 0
```

### 2. 不需要任何额外配置

- 不需要修改 `scripts/commands/__init__.py`
- 不需要修改 `scripts/cli.py`
- 不需要修改 `pyproject.toml`

`load_all_commands()` 启动时会自动 import `report_cmd`，触发装饰器把
`ReportCommand` 注册进 `registry`。

### 3. 验证

```bash
PYTHONPATH=. python -m scripts.cli --help
PYTHONPATH=. python -m scripts.cli report daily --date 2026-04-24
```

### 4. 编写测试

```python
# tests/test_report_command.py
from scripts.commands import load_all_commands, registry
from scripts.commands.report_cmd import ReportCommand


def test_report_registered():
    load_all_commands()
    assert "report" in registry
    assert isinstance(registry["report"], ReportCommand)
```

## 处理函数 (handler) 签名约定

```python
def handler(args: argparse.Namespace, ctx: AppContext) -> int: ...
```

- `args`：argparse 解析后的 Namespace（注意 dest 命名，破折号被自动转下划线）。
- `ctx`：`AppContext` 实例，通过它访问所有 Service。
- 返回值：进程退出码（`0` 成功，`>0` 失败）。

## 输出助手（统一观感）

`scripts/utils/output.py` 提供：

| 函数 | 用途 |
| :--- | :--- |
| `print_json(obj)` | 统一缩进 + `ensure_ascii=False` 的 JSON 输出 |
| `ok(msg)`         | `[OK] {msg}` 写入 stdout |
| `warn(msg)`       | `[WARN] {msg}` 写入 stderr |
| `err(msg)`        | `[ERROR] {msg}` 写入 stderr |
| `split_csv(text)` | 把 `"a,b,c"` 解析成 `["a","b","c"]`（空串/None → None） |
| `parse_iso(text)` | ISO 时间解析，自动补默认时区 |

## 高危子命令的 `--yes` 约定

`store delete`、`init unbind` 等高危命令**统一加二次确认开关**（`--yes` 或 `--confirm`）：

```python
class StoreCommand(BaseCommand):
    name = "store"

    def configure(self, parser):
        sub = parser.add_subparsers(dest="subcommand", required=True)
        sd = sub.add_parser("delete", help="删除门店")
        sd.add_argument("--store-id", required=True)
        self.add_yes_flag(sd, "二次确认（高危操作必填）")
        sd.set_defaults(func=_delete)
```

handler 内显式校验 `args.yes`，否则 `return 2` + `err("...")`。

## 异常处理约定

- 业务可预期错误：在 service 层抛 `StoreTaskDispatcherError`（或其子类），由
  `scripts/cli.py` 的 try/except 捕获并 `err(...)` + `return 1`。
- 不可预期错误：直接抛出，由 CLI 顶层 logger 打 stack 后兜底退出。
- 命令 handler **不应** 自己 try/except 后吞掉异常 —— 让上层统一处理。

## 测试

```bash
PYTHONPATH=. pytest -v --cov=scripts --cov-report=term-missing
```

测试全部 mock `subprocess.run`，不会真实调用 `dws`，可在无网络/无钉钉权限的环境运行。

## 提交前检查

- [ ] `pytest` 全量通过
- [ ] 新增/修改的命令在 `references/setup/` 或 `references/runtime/` 对应文档中补充参数与处方
- [ ] 涉及表结构变更时同步更新 `references/shared/data-model.md` 与 `docs/requirements-store-inspection.md`
- [ ] 涉及高危操作时遵守 `--yes` 约定