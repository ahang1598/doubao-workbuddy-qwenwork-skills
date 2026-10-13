# PAT 错误处理改造方案

> 文档位置：`docs/pat-error-handling.md`
> 作者：梁超磊(七谏)
> 最后更新：2026-05-11

本文档给出 `store-inspection-skills-group` 代码库中「PAT 权限错误处理」
的完整改造方案，包括背景、设计决策、每个文件的修改细节、实施顺序与验证
方法。按本文档执行即可完成落地，无需再翻阅历史聊天记录。

---

## 一、问题背景

### 1.1 触发现象

在 2026-05-11 凌晨的定时派发任务中出现如下故障链：

1. `dispatch init` 调用 `aitable_record_create` 写入任务记录表时返回错误
   `PAT_MEDIUM_RISK_NO_PERMISSION`；
2. `task_record_service.upsert_task_record` 的 `except Exception` 把异常
   **静默吞掉**，仅打一条 error 日志后 return；
3. 上层 `dispatch init` 以为派发记录已落库，成功返回 exit=0；
4. 随后的 `dispatch notify` / `query_today_tasks` / `reminder` 等命令
   在任务记录表里**找不到这条记录**，用户侧表现为“派发消失”。

### 1.2 错误码含义

`PAT_*_NO_PERMISSION` 属于 dws CLI 的 Personal Access Token 权限检查失败：

| 错误码 | 含义 |
| --- | --- |
| `PAT_NO_PERMISSION` | 低风险 scope 未授予 |
| `PAT_MEDIUM_RISK_NO_PERMISSION` | 中风险 scope 未授予（写数据类典型场景） |
| `PAT_HIGH_RISK_NO_PERMISSION` | 高风险 scope 未授予（涉及财务、组织架构等） |

这类错误**是确定性失败**（scope 没开就是没开），不会因为重试而成功，
属于需要用户 / Agent 授权后才能恢复的状态。

### 1.3 根因定位

代码侧有三层缺陷叠加：

1. **识别缺失**：`dws_client._run` 未对 `PAT_*` 错误码做特殊识别，
   依赖通用重试白名单逻辑（虽然 PAT 错误恰好不在白名单里不会被重试，
   但也没有给上层任何“这是权限错误”的信号）；
2. **分类错误**：`task_record_service.upsert_task_record` 用
   `except Exception` 一刀切吞掉所有异常，包括主键写入失败；
3. **提示缺失**：`cli.py` 对所有 `StoreTaskDispatcherError` 统一输出
   `str(exc)` 并返回 exit=1，用户看不到可操作的授权指引，定时任务宿主
   也无法用退出码区分“要人介入授权”和“普通业务失败”。

---

## 二、dws 官方能力盘点

改造前必须先确认 dws CLI 自己对 PAT 错误提供了哪些能力，避免在
Python 侧重复造轮子。

### 2.1 两种运行模式

`dws pat --help` 里明确描述了 **Host-owned PAT 开关**：

> 当且仅当环境变量 `DINGTALK_DWS_AGENTCODE` 非空时，CLI 命中 PAT
> 固定以 `stderr JSON + exit=4` 的 host-owned 形式返回，由宿主处理
> 全部 UI / 交互 / 回调节奏 / 重试逻辑，CLI 侧不再拉起任何本地
> 浏览器 / 轮询。

由此派生出两条处理路径：

**普通用户模式**（未设置 `DINGTALK_DWS_AGENTCODE`）：CLI 自己弹浏览器
让用户完成授权，skill 侧只需识别到失败后提示“请在浏览器完成授权
后重试”。

**Host-owned 模式**（定时任务、Agent 子进程等无人值守场景）：CLI 立刻
失败返回 `exit=4` + 结构化 JSON，宿主（即本 skill）负责诊断、授权、
重试、闭环。

### 2.2 官方提供的命令族

```
dws recovery execute --last         # 读取最近失败快照，返回恢复分析包
dws recovery plan --last            # 基于快照生成恢复计划（下一步动作）
dws pat chmod <scope>... --agentCode <code>
                    --grant-type once|session|permanent
                    [--session-id <sid>]   # 执行授权
dws recovery finalize --event-id <id>
                    --outcome recovered|failed|handoff
                    [--execution-file <path>]   # 回写闭环
```

失败快照默认存储位置：`<dws-bin-dir>/.dws/recovery/last_error.json`（dws 可执行文件所在目录下 `.dws/recovery/`，具体路径以 `dws --version` 报告的安装位置为准）。

### 2.3 推导出的核心结论

**dws 已经把「诊断 → 规划 → 授权 → 闭环」整条状态机做完了**。
Python 侧需要的只是“识别 + 粘合”，不是“重建”。这一判断直接决定了
下面的设计原则。

---

## 三、设计原则

### 3.1 不封装 DwsPermissionError

前一版方案曾尝试新增 `DwsPermissionError(DwsError)` 专用异常类，
经过重新评估后**明确放弃**，原因如下。

**第一，dws CLI 本身已是结构化出口**。Host-owned 返回 `stderr JSON +
exit=4`，普通模式返回带 `code: PAT_*_NO_PERMISSION` 的 stdout JSON。
两种形态都能用 `json.loads` 直接消费，无需再包一层 Python 异常。
真正需要的是一个**无状态纯函数** `detect_pat_failure(retcode, stdout, stderr) -> Optional[dict]`。

**第二，封装异常是信息的有损单向转换**。为避免丢字段，异常类要不停
新增属性（`required_scopes` / `grant_options` / `agent_code` /
`session_id` / `event_id` / ...），最终变成“一个比 CompletedProcess
还重的 CompletedProcess”。不如让结构化 dict 透明穿透到 service 层。

**第三，`user_hint()` 在复刻官方的 `recovery plan`**。自己拼
`dws pat chmod ...` 字符串等于重新实现一遍官方逻辑，未来 scope 命名
规则或授权默认值变更时会出现本地版本与官方行为漂移。正确做法是
直接调 `dws recovery plan --last` 拿计划。

**第四，真正该封装的是业务语义**。对 `task_record_service` 而言，
它关心的是“主键写入是否成功”，而不是“底层是 PAT 错还是网络错”。
失败原因属于 `cause`，应复用现有 `DwsError.code`，而不是新开异常类
让业务层 try/except 多写一套分支。

### 3.2 四层架构

```
┌───────────────────────────────────────────────────┐
│  用户提示层  (scripts/cli.py)                       │
│  DwsError.code ∈ PAT_* → 输出指引 + exit=4          │
├───────────────────────────────────────────────────┤
│  业务分类层  (scripts/services/*)                   │
│  PAT 错误向上抛（主键写入）；非 PAT 降级（辅助调用）   │
├───────────────────────────────────────────────────┤
│  恢复层（可选）(scripts/infrastructure/pat_recovery.py)│
│  封装 dws recovery execute/plan/finalize            │
├───────────────────────────────────────────────────┤
│  识别层  (scripts/infrastructure/pat_errors.py)     │
│  纯函数 detect_pat_failure(retcode, stdout, stderr) │
└───────────────────────────────────────────────────┘
```

**不新增任何异常类**；新增两个模块文件；对四个现有文件做最小侵入式修改。

---

## 四、文件级修改清单

下文按文件维度列出每处改动，含背景、关键代码、验证点。

### 4.1 [新增] `scripts/infrastructure/pat_errors.py`

**作用**：整个方案的地基，提供 PAT 错误识别的纯函数 API。

**核心内容**：

```python
"""PAT 权限错误识别工具。

本模块只做"识别"，不做"恢复"。恢复逻辑由 pat_recovery.py 承担。
不新增异常类，识别结果以结构化 dict 返回，字段对齐 dws CLI 原始载荷。
"""
from __future__ import annotations

import json
import re
from typing import Optional

# PAT 权限未授予的已知错误码。dws 服务端新增错误码也会以 PAT_ 前缀 +
# PERMISSION 关键字命名，因此下面的识别逻辑采用"白名单 + 模式"双轨。
PAT_PERMISSION_ERROR_CODES = frozenset({
    "PAT_NO_PERMISSION",
    "PAT_MEDIUM_RISK_NO_PERMISSION",
    "PAT_HIGH_RISK_NO_PERMISSION",
})

_PAT_CODE_PATTERN = re.compile(r"\bPAT_[A-Z_]*PERMISSION[A-Z_]*\b")


def is_pat_code(code: Optional[str]) -> bool:
    """判断错误码字符串是否属于 PAT 权限未授予场景。"""
    if not code:
        return False
    upper = str(code).upper()
    if upper in PAT_PERMISSION_ERROR_CODES:
        return True
    return bool(_PAT_CODE_PATTERN.search(upper))


def detect_pat_failure(
    returncode: int,
    stdout: str,
    stderr: str,
) -> Optional[dict]:
    """识别一次 dws CLI 调用是否为 PAT 权限失败。

    Returns:
        命中时返回 dws 原始错误载荷 dict（至少含 ``code`` 字段，通常还含
        ``message`` / ``requiredScopes`` / ``grantOptions`` / ``agentCode``
        / ``sessionId`` / ``eventId`` 等）；否则返回 ``None``。

    识别顺序：
        1. Host-owned 模式的硬契约：``returncode == 4`` 且 stderr 为结构化 JSON；
        2. 普通模式：stdout 可解析为 JSON 且 ``code`` / ``error.code`` 命中；
        3. 兜底文本匹配：stderr 中出现 PAT_* 错误码字面量。
    """
    # 路径 1：Host-owned exit=4 硬契约
    if returncode == 4:
        payload = _try_parse_json(stderr)
        if isinstance(payload, dict):
            inner = payload.get("error") if isinstance(payload.get("error"), dict) else payload
            if is_pat_code(inner.get("code")):
                return inner
            # exit=4 但 code 无法识别，仍按 PAT 失败处理（契约兜底）
            return inner or payload

    # 路径 2：普通模式 JSON 载荷
    payload = _try_parse_json(stdout)
    if isinstance(payload, dict):
        inner = payload.get("error") if isinstance(payload.get("error"), dict) else payload
        if is_pat_code(inner.get("code")):
            return inner

    # 路径 3：stderr 文本兜底（某些旧版本仅把错误码写在 stderr）
    if stderr:
        match = _PAT_CODE_PATTERN.search(stderr.upper())
        if match:
            return {"code": match.group(0), "message": stderr.strip()}

    return None


def _try_parse_json(text: str) -> Optional[dict]:
    """宽松 JSON 解析：失败返回 None，不抛异常。"""
    if not text:
        return None
    text = text.strip()
    if not text or text[0] not in "{[":
        return None
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return None


__all__ = [
    "PAT_PERMISSION_ERROR_CODES",
    "is_pat_code",
    "detect_pat_failure",
]
```

**测试覆盖**：`tests/test_pat_errors.py`，覆盖三条识别路径与至少四条
否定路径（普通 DwsError、网络超时、非 JSON 输出、空字符串）。

---

### 4.2 [新增] `scripts/infrastructure/pat_recovery.py`

**作用**：薄封装 dws 官方 recovery 命令族，为用户提示与将来的
自动授权闭环提供入口。**当前版本只做诊断与提示，不自动执行 `pat chmod`**
（授权是敏感动作，需要显式开关）。

**核心内容**：

```python
"""PAT 权限错误恢复辅助器。

只做两件事：
  1. 调用 ``dws recovery execute --last`` 读取最近失败快照；
  2. 把快照渲染成面向用户 / Agent 的授权指引文本。

**刻意不做**：
  * 自动执行 ``dws pat chmod``（授权为敏感动作，必须显式开关）；
  * 在 Python 侧拼接命令字符串（优先展示 dws 原始 payload 字段，减少漂移）。
"""
from __future__ import annotations

import logging
import os
from typing import Literal, Optional

from scripts.infrastructure.dws_client import DwsClient

logger = logging.getLogger(__name__)

Outcome = Literal["recovered", "failed", "handoff"]


class PatRecoveryHelper:
    """封装 dws recovery 命令族。"""

    def __init__(self, client: DwsClient) -> None:
        self.client = client

    def read_last_event(self) -> Optional[dict]:
        """读取最近一次 PAT 失败快照。无快照或读取失败时返回 None。"""
        try:
            payload = self.client.run_raw(["recovery", "execute", "--last"])
        except Exception as exc:  # pragma: no cover - 兜底降级
            logger.debug("recovery execute --last 失败，跳过: %s", exc)
            return None
        if isinstance(payload, dict) and payload.get("error"):
            return None
        return payload if isinstance(payload, dict) else None

    def explain_for_user(self, pat_payload: dict) -> str:
        """把 PAT 失败 payload 渲染成面向用户的授权指引。

        指引优先展示 dws 原始字段（scope 清单、grant 选项），
        避免自拼命令字符串导致与官方行为漂移。
        """
        host_owned = bool(os.environ.get("DINGTALK_DWS_AGENTCODE"))
        lines = ["权限不足：dws CLI 返回 PAT 权限错误"]

        scopes = pat_payload.get("requiredScopes") or []
        if scopes:
            lines.append("需授予以下 scope：")
            for item in scopes:
                if isinstance(item, dict):
                    scope = item.get("scope", "<unknown>")
                    display = item.get("displayName", "")
                    product = item.get("productName", "")
                    suffix = f" ({product} / {display})" if display else ""
                    lines.append(f"  • {scope}{suffix}")
                else:
                    lines.append(f"  • {item}")

        if host_owned:
            lines.append(
                "Host-owned 模式：请调用 `dws recovery plan --last` 获取"
                "恢复计划，并执行返回的 `dws pat chmod ...` 指令完成授权，"
                "成功后调用 `dws recovery finalize --event-id <id> "
                "--outcome recovered` 闭环。",
            )
        else:
            lines.append("请在浏览器完成授权后重试原命令。")

        event_id = pat_payload.get("eventId")
        if event_id:
            lines.append(f"关联事件 ID：{event_id}")
        return "\n".join(lines)

    def finalize(self, event_id: str, outcome: Outcome) -> None:
        """回写恢复闭环结果。失败仅记日志，不向上抛。"""
        try:
            self.client.run_raw([
                "recovery", "finalize",
                "--event-id", event_id,
                "--outcome", outcome,
            ])
        except Exception as exc:  # pragma: no cover
            logger.warning("recovery finalize 失败: %s", exc)


__all__ = ["PatRecoveryHelper", "Outcome"]
```

> 注：`DwsClient` 需要补充一个 `run_raw(args: list) -> dict` 公共方法，
> 或直接暴露 `_run` 为 `run`。建议第二阶段一并处理（见 §4.3）。

---

### 4.3 [修改] `scripts/infrastructure/dws_client.py`

四处改动。

#### 改动 A：补 import

在文件顶部 import 区新增：

```python
from scripts.infrastructure.pat_errors import detect_pat_failure
```

#### 改动 B：`_run` 的 `returncode != 0` 分支前置 PAT 识别

原代码（约第 199-222 行）：

```python
if proc.returncode != 0:
    if (
        attempt < self.max_retry
        and _is_retryable(proc.stderr, stdout=proc.stdout)
    ):
        ...
        continue
    code = self._extract_error_code(proc.stdout, proc.stderr)
    raise DwsError(...)
```

改为：

```python
if proc.returncode != 0:
    # 前置识别：PAT 错误是确定性失败，绝不参与重试，
    # 且必须把 dws 原始错误码（PAT_*_NO_PERMISSION）塞进 DwsError.code，
    # 便于 cli 层分类输出授权指引。
    pat_payload = detect_pat_failure(
        proc.returncode, proc.stdout, proc.stderr,
    )
    if pat_payload is not None:
        raise DwsError(
            pat_payload.get("message")
            or proc.stderr.strip()
            or proc.stdout.strip()
            or "dws 命令权限不足",
            code=pat_payload.get("code") or "PAT_NO_PERMISSION",
            stdout=proc.stdout,
            stderr=proc.stderr,
            args_list=list(full_args),
        )

    if (
        attempt < self.max_retry
        and _is_retryable(proc.stderr, stdout=proc.stdout)
    ):
        ...
```

#### 改动 C：AITable `status == "error"` 分支同样前置识别

原代码（约第 241 行）对 AITable 业务失败会抛 `DwsError`；这里要改成
先走 `detect_pat_failure(0, proc.stdout, "")`，命中则按 PAT 错误抛出：

```python
if isinstance(result, dict) and result.get("status") == "error":
    pat_payload = detect_pat_failure(0, proc.stdout, "")
    if pat_payload is not None:
        raise DwsError(
            pat_payload.get("message") or "AITable 命令权限不足",
            code=pat_payload.get("code") or "PAT_NO_PERMISSION",
            stdout=proc.stdout,
            stderr=proc.stderr,
            args_list=list(full_args),
        )
    error_code = self._extract_error_code(proc.stdout, proc.stderr)
    raise DwsError(...)
```

retcode=0 时 AITable 也可能返回 `PAT_*_NO_PERMISSION`，这条分支覆盖
到位后 PAT 错误码分类才算完整。

#### 改动 D：新增公共方法 `run_raw`

`PatRecoveryHelper` 需要发起 `recovery execute/finalize` 等**不经过
业务方法**的原始调用，在 `DwsClient` 末尾新增：

```python
def run_raw(self, args: list) -> dict:
    """对外暴露原始 _run，用于 recovery / pat 等非业务命令。"""
    return self._run(args)
```

---

### 4.4 [修改] `scripts/services/task_record_service.py`

两处改动，都围绕“PAT 错误必须向上抛”。

#### 改动 A：补 import

```python
from scripts.infrastructure.pat_errors import is_pat_code
```

#### 改动 B：`upsert_task_record` 外层 except（约第 206 行）

原代码：

```python
except Exception as exc:
    logger.error(
        "upsert 任务记录失败 task_id=%s: %s", task_id, exc, exc_info=True
    )
```

改为：

```python
except DwsError as exc:
    # PAT 权限错误必须向上抛：任务记录是派发链路的主键，
    # 静默吞掉会导致 dispatch notify / query_today_tasks
    # 找不到记录，数据一致性破坏。
    if is_pat_code(exc.code):
        logger.error(
            "upsert 任务记录权限不足 task_id=%s code=%s，向上抛以避免"
            "派发链路数据不一致", task_id, exc.code,
        )
        raise
    logger.error(
        "upsert 任务记录失败 task_id=%s: %s", task_id, exc, exc_info=True
    )
except Exception as exc:
    logger.error(
        "upsert 任务记录失败 task_id=%s: %s", task_id, exc, exc_info=True
    )
```

#### 改动 C：查询分支（约第 187 行）

原代码：

```python
except Exception as query_exc:
    logger.warning(...)
    return
```

改为：先判断 `isinstance(query_exc, DwsError) and is_pat_code(query_exc.code)`，
命中则 `raise`；其余情况保持原 `return`。理由：查询失败误判为新建会
产生重复记录，但“权限不足”本身是显性错误，应立即失败。

#### 改动 D：同步更新 docstring

在 `upsert_task_record` 的 docstring 里补充一段：

```
失败时记录 error 日志，不阻断主流程；但 **PAT 权限错误例外**：
任务记录是派发链路的主键，权限失败必须向上抛，以避免下游
``dispatch notify`` / ``query_today_tasks`` / ``reminder`` 找不到
记录导致数据一致性破坏。
```

---

### 4.5 [修改] `scripts/cli.py`

只改 `main()` 的异常捕获链。

#### 改动 A：补 import

```python
from scripts.domain.exceptions import DwsError, StoreTaskDispatcherError
from scripts.infrastructure.pat_errors import detect_pat_failure, is_pat_code
from scripts.infrastructure.pat_recovery import PatRecoveryHelper
```

#### 改动 B：在 `except StoreTaskDispatcherError` 之前插入 PAT 专用分支

原代码（第 122-126 行）：

```python
try:
    return int(args.func(args, ctx) or 0)
except StoreTaskDispatcherError as exc:
    err(str(exc))
    return 1
```

改为：

```python
try:
    return int(args.func(args, ctx) or 0)
except DwsError as exc:
    # PAT 权限错误单独路由：
    #   1. 输出可操作的授权指引（优先用 dws recovery execute --last 的载荷）；
    #   2. 返回 exit=4，对齐 dws 官方 Host-owned PAT 退出码契约，
    #      便于 crontab / Agent 宿主用退出码精确路由。
    if is_pat_code(exc.code):
        payload = detect_pat_failure(0, exc.stdout, exc.stderr) or {
            "code": exc.code,
            "message": exc.message,
        }
        try:
            helper = PatRecoveryHelper(ctx.client)
            latest = helper.read_last_event()
            if latest:
                payload = {**payload, **latest}
            err(helper.explain_for_user(payload))
        except Exception:
            err(f"权限不足：{exc.code} {exc.message}")
        return 4
    err(str(exc))
    return 1
except StoreTaskDispatcherError as exc:
    err(str(exc))
    return 1
```

> 注：`ctx.client` 需要确认 `AppContext` 暴露了 `client` 属性；若暴露名
> 不同（如 `dws_client`），改为对应属性名即可。

---

## 五、测试计划

### 5.1 新增测试文件

**`tests/test_pat_errors.py`**：纯函数单测，无需 mock。

覆盖正例：
- `returncode=4` + stderr 为结构化 JSON（Host-owned）
- `returncode=4` + stderr JSON `error.code=PAT_MEDIUM_RISK_NO_PERMISSION`（嵌套形态）
- `returncode=1` + stdout JSON `code=PAT_NO_PERMISSION`（普通模式）
- `returncode=1` + stderr 文本含 `PAT_HIGH_RISK_NO_PERMISSION`（兜底）
- 未来新增错误码 `PAT_XXX_PERMISSION_DENIED` 被正则兜住

覆盖反例：
- 普通 `DwsError` stderr 含 `TIMEOUT_ERROR`
- `returncode=0` 业务成功
- `stdout="not json"`、`stderr=""` 等各种空或不规范输入
- `code=None` / `code=""`

**`tests/test_pat_recovery.py`**：mock `DwsClient._run` / `run_raw`。

覆盖：
- `read_last_event` 拿到 payload → 返回 dict
- `read_last_event` CLI 失败 → 返回 None 不抛
- `explain_for_user` 在 Host-owned（env 有 `DINGTALK_DWS_AGENTCODE`）
  与普通模式下输出不同指引
- `explain_for_user` 正确渲染 `requiredScopes` 列表
- `finalize` 捕获底层异常不外抛

### 5.2 修改既有测试

**`tests/test_dws_client.py`**：新增 3 个 case 覆盖改动 B/C：
- retcode=4 + stderr JSON → 抛 `DwsError.code=PAT_*`
- retcode=1 + stdout `code=PAT_*` → 抛 `DwsError.code=PAT_*`，且不重试
- retcode=0 + AITable `status=error` `code=PAT_*` → 抛 `DwsError.code=PAT_*`

**`tests/test_task_record_pat.py`**（新建）：fake DwsClient
让 `aitable_record_create` 抛带 `code=PAT_MEDIUM_RISK_NO_PERMISSION` 的
`DwsError`，断言 `upsert_task_record` **重新抛出**而不是吞掉；
对照组：抛带 `code=TIMEOUT_ERROR` 的 `DwsError`，断言被静默降级。

**`tests/test_cli.py`**：新增两个 case：
- mock `args.func` 抛 `DwsError(code="PAT_MEDIUM_RISK_NO_PERMISSION")`
  → 期望 exit=4，stderr 含“权限不足”关键字
- mock `args.func` 抛普通 `DwsError(code="TIMEOUT_ERROR")`
  → 期望 exit=1，走原路径

### 5.3 删除残留

删除 `tests/test_pat_permission.py`（上一版基于 `DwsPermissionError`
封装方案的测试，与新方案不兼容）。

---

## 六、实施顺序

按依赖关系分四个阶段，每阶段独立提交、独立可回滚。

**阶段 1「识别」**：只提交 `scripts/infrastructure/pat_errors.py` 与
`tests/test_pat_errors.py`。不改任何现有行为，审阅者只需判断识别逻辑
正确性。

**阶段 2「分类」**：提交 `dws_client.py` 的改动 A~D 与
`task_record_service.py` 的改动 A~D；更新 `tests/test_dws_client.py`；
新增 `tests/test_task_record_pat.py`；删除 `tests/test_pat_permission.py`。
这是行为变化的核心阶段，必须跑全量 `pytest`（特别关注
`test_dispatcher.py` 和 `test_dws_client.py` 不回归）。

**阶段 3「用户层」**：新增 `scripts/infrastructure/pat_recovery.py`
与 `tests/test_pat_recovery.py`；修 `cli.py` 的改动 A~B；扩充
`tests/test_cli.py`。对内部逻辑零侵入，只改用户可见输出。

**阶段 4「清理」**：在 `DwsError` 的 docstring 补一行“PAT 相关错误码
见 `pat_errors.PAT_PERMISSION_ERROR_CODES`，不构造专用异常类”；
在 `README.md` 或 `CONTRIBUTING.md` 加一小段“遇到 PAT 权限错误
应该怎么办”的运维说明，指向本文档。

---

## 七、端到端验证

除单测外的两条手工路径。

### 7.1 普通用户模式

本机 `unset DINGTALK_DWS_AGENTCODE`，刻意撤销一个 scope（如
`aitable.record:create`），运行：

```bash
dws-store-inspection dispatch init --template TPL_xxx
```

**预期**：stderr 输出“权限不足：dws CLI 返回 PAT 权限错误 / 需授予
以下 scope：... / 请在浏览器完成授权后重试原命令”，进程 exit code=4。

### 7.2 Host-owned 模式

```bash
export DINGTALK_DWS_AGENTCODE=agt_xxx
dws-store-inspection dispatch init --template TPL_xxx
```

**预期**：stderr 是一段结构化 JSON（dws 原始输出）+ Python 渲染的
“Host-owned 模式：请调用 `dws recovery plan --last` ...”指引，
exit code=4，且 `<dws-bin-dir>/.dws/recovery/last_error.json` 存在
（`<dws-bin-dir>` 为当前环境中 dws 可执行文件所在目录）。

两条路径都通过即视为改造完整。

---

## 八、设计决策记录

审阅或交接时预判会被质疑的点，在此留档。

**为何不把识别逻辑做成 `DwsClient` 的方法**：识别是无状态的、只依赖
三个输入（retcode/stdout/stderr）而非 client 状态，纯函数便于单测，
便于将来移到 `domain/` 或抽成独立 pip 包。

**为何不扩展 `DwsError` 新增 `pat_payload` 字段**：会污染通用契约——
非 PAT 错误时该字段为 `None`，所有使用方都得写 `if err.pat_payload`。
代价是让使用方需要时自己调 `detect_pat_failure(err.stdout, err.stderr)`
重新识别，只是一次字符串解析，可接受。

**为何 cli 返回 exit=4 而非复用 1**：Host-owned 宿主（crontab / Agent
子进程）需要用退出码精确路由，exit=4 对齐 dws 官方约定降低集成成本；
返回 1 会把 PAT 失败和普通业务失败混为一谈，失去“立刻让人授权”的
语义信号。

**为何恢复层不做自动 `dws pat chmod`**：授权是敏感动作，未经用户
同意就自动提权是安全红线；当前版本只做“诊断 + 提示”，自动化留给
将来明确有 `--auto-grant` 开关、或 Host-owned 模式下 Agent 显式决策
后再接入。

**为何用 frozenset + 正则双轨识别错误码**：frozenset 覆盖已知清单，
正则兜住未来新增错误码（如 `PAT_XXX_PERMISSION_DENIED`），保守安全：
宁可把疑似权限错误也视作权限错误（跳过重试 + 提示授权），也不要
把权限错误误判为可重试的瞬时故障。

---

## 九、FAQ

**Q1：如果 dws 未来改掉 exit=4 的契约怎么办？**
A：`detect_pat_failure` 有三条识别路径，exit=4 只是路径 1，路径 2/3
基于错误码字面识别，契约变化不会导致完全失灵。

**Q2：`PatRecoveryHelper` 失败会不会连带整个 cli 崩？**
A：cli.py 的 except 块里对 helper 调用做了 try/except 兜底，失败会
退化为只输出 `code` + `message`，不影响主流程。

**Q3：为什么 task_record_service 的查询分支也要抛 PAT 错误，不能
只在写入分支抛？**
A：查询失败如果静默返回 None，会被上层误判为“记录不存在”从而
走新建分支，可能产生重复记录；而权限错误是显性失败，立即暴露
更安全。

**Q4：非 Host-owned 模式下 CLI 会自己拉浏览器，skill 侧不处理行吗？**
A：可以，但不优雅：用户看到的是浏览器弹窗 + 原脚本以 exit=1 终止，
没有明确的“授权完成后请重试”提示。走本方案后，skill 侧能给出清晰
指引并返回 exit=4，crontab 运维脚本可以据此触发报警 / 人工介入。

**Q5：`DwsPermissionError` 是否以后永远不会封装？**
A：不绝对。如果出现以下信号就应该重新评估：
（1）业务层需要区分“PAT 权限错误”和“普通 DwsError”的分支超过 3 处；
（2）需要在多个独立调用点累积 PAT 错误上下文做汇总处理；
（3）`is_pat_code(err.code)` 的调用点超过 10 处且经常忘记加。
目前距离这三个信号都很远，维持纯函数方案。

---

## 十、附录：一句话总结

**把 dws CLI 的结构化出口当契约来用，不在 Python 侧重新发明一遍。**
新增两个小模块（识别 + 恢复），原有异常体系一字不改，用 exit=4 +
清晰指引把用户带到 dws 官方的授权闭环里。改动量小、风险可控、
与 dws 未来演进保持单向兼容。
