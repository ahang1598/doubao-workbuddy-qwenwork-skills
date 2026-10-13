## Pipeline 工作流框架最佳实践

### 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI 命令层                              │
│  commands/meituan.py                                        │
│  python cli.py meituan check-login                          │
│  python cli.py meituan search 麦当劳                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   Workflow 编排层（业务代码）                  │
│  services/meituan/workflow.py                                │
│  组装 Pipeline，暴露 run_check_login() / run_search()        │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│            浏览器自动化 Pipeline（基础设施，统一入口）          │
│  services/browser_pipeline/                                  │
│  Pipeline + PipelineStep + DetachedWorkerStep                │
│  DetachedBrowserWorker + 启动器 + 子进程 runner              │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   CDP 浏览器底层服务                           │
│  services/browser/cdp_launcher.py                            │
│  services/browser/browser.py                                 │
│  services/browser/finder.py                                  │
└─────────────────────────────────────────────────────────────┘
```

业务代码只需从一个包 import：

```python
from services.browser_pipeline import (
    Pipeline, PipelineStep, PipelineContext, StepResult, StepStatus,
    DetachedWorkerStep, DetachedBrowserWorker, WorkerResult,
    is_worker_alive, read_worker_result,
)
```

---

### 核心概念

#### Pipeline（流水线调度器）

按顺序执行注册的 Step，支持运行时动态管理：

```python
from services.browser_pipeline import Pipeline

pipeline = Pipeline(name="my-workflow")
pipeline.add_step(StepA())
pipeline.add_step(StepB())
pipeline.insert_step(1, StepMiddle())   # 在 A 和 B 之间插入
pipeline.remove_step("step_b")          # 按名称移除
pipeline.replace_step("step_a", NewA()) # 按名称替换
context = pipeline.execute(param1="value1")
```

#### PipelineStep（步骤基类）

每个步骤独立实现，只需关注自己的逻辑：

```python
from services.browser_pipeline import PipelineStep, PipelineContext, StepResult, StepStatus

class MyStep(PipelineStep):
    @property
    def name(self) -> str:
        return "my_step"

    def execute(self, context: PipelineContext) -> StepResult:
        value = context.get("param1")
        context.set("output_key", result_data)
        return StepResult(step_name=self.name, status=StepStatus.SUCCESS)

    # 可选：条件跳过
    def should_skip(self, context: PipelineContext) -> bool:
        return not context.get("is_ready", False)

    # 可选：流水线中止后仍执行（用于清理步骤）
    @property
    def run_on_abort(self) -> bool:
        return True
```

#### PipelineContext（共享上下文）

步骤间通过 context 传递数据，避免直接耦合：

```python
context.set("key", value)       # 写入
context.get("key", default)     # 读取
context.abort("原因")            # 中止后续步骤
context.results                  # 所有步骤的执行结果
```

---

### DetachedBrowserWorker（子进程浏览器任务）

#### 解决的问题

Playwright 主进程退出时，所有 page 被关闭。但很多场景需要：
**主进程退出 → 浏览器窗口保持 → 用户操作 → agent 后续再接管**

#### 工作原理

```
主进程 (CLI)                         子进程 (detached worker)
┌──────────────┐                    ┌──────────────────────┐
│ Pipeline     │                    │                      │
│  └ Step ─────┼── launch_detached ─▶ 连接 CDP 浏览器      │
│              │    _worker()       │ 创建 page            │
│ 返回 handle  │                    │ 执行 worker.run()    │
│ 主进程退出 ✅ │                    │ 写结果到 JSON 文件    │
└──────────────┘                    │ 退出                 │
                                    └──────────────────────┘
```

#### 编写新的 Worker（3 步）

**第 1 步**：继承 `DetachedBrowserWorker`

```python
from services.browser_pipeline import DetachedBrowserWorker, WorkerResult
from playwright.sync_api import Browser, Page

class MyPlatformLoginWorker(DetachedBrowserWorker):
    @property
    def worker_name(self) -> str:
        return "myplatform-login"

    @property
    def default_timeout_seconds(self) -> int:
        return 120

    @property
    def device_name(self) -> str | None:
        return "iphone14"

    def run(self, browser: Browser, page: Page) -> WorkerResult:
        page.goto("https://myplatform.com/login")
        return WorkerResult(status="success", message="登录成功")
```

**第 2 步**：继承 `DetachedWorkerStep` 创建 Step

```python
from services.browser_pipeline import DetachedWorkerStep, PipelineContext
from .my_worker import MyPlatformLoginWorker

class CheckLoginStep(DetachedWorkerStep):
    """需要用户介入的登录步骤。"""
    worker_class = MyPlatformLoginWorker
    abort_after_launch = True
    timeout = 120

    @property
    def name(self) -> str:
        return "check_login"

    def build_abort_message(self, handle) -> str:
        return f"请在浏览器中完成登录 (PID={handle.worker_pid})"
```

```python
from services.browser_pipeline import DetachedWorkerStep, PipelineContext
from .my_search_worker import MyPlatformSearchWorker

class SearchStep(DetachedWorkerStep):
    """不需要用户介入的搜索步骤。"""
    worker_class = MyPlatformSearchWorker
    timeout = 30

    @property
    def name(self) -> str:
        return "search"

    def build_extra_params(self, context: PipelineContext) -> dict:
        return {"keyword": context.get("keyword"), "city": context.get("city")}
```

`DetachedWorkerStep` 基类自动处理：启动 worker → 存 handle 到 context → 构造 StepResult。
子类只需声明 `worker_class` 和 `name`，按需重写钩子：

| 属性/方法 | 默认值 | 说明 |
|---|---|---|
| `worker_class` | 必填 | 要启动的 Worker 类 |
| `abort_after_launch` | `False` | 启动后是否中止 pipeline（用户介入场景设为 `True`） |
| `timeout` | `120` | 超时秒数 |
| `headless` | `False` | 是否无头模式 |
| `build_extra_params(context)` | `{}` | 构造传给 worker 的额外参数 |
| `build_abort_message(handle)` | 通用消息 | 自定义 abort 消息 |

**第 3 步**：agent 监控子进程

```python
from services.browser_pipeline import is_worker_alive, read_worker_result

is_worker_alive(pid)                  # 检查子进程是否存活
result = read_worker_result(path)     # 读取结果 JSON
# result = {"status": "success", "message": "...", "data": {...}}
```

---

### 结果文件协议

Worker 完成后写入 JSON 文件，格式如下：

```json
{
  "status": "success | failed | timeout",
  "message": "描述信息",
  "data": {},
  "worker_class": "services.meituan.steps.meituan_login_worker.MeituanLoginWorker",
  "pid": 12345,
  "timestamp": "2026-04-14T19:00:00"
}
```

---

### 设备模拟

通过 `device_profiles.py` 管理移动端设备配置：

```python
from services.meituan.device_profiles import get_device_profile, DEVICE_REGISTRY

profile = get_device_profile("iphone14")
# profile.user_agent, profile.viewport_width, profile.viewport_height, ...
```

扩展新设备只需在 `DEVICE_REGISTRY` 中注册：

```python
IPHONE_15_PRO = DeviceProfile(
    name="iPhone 15 Pro",
    user_agent="...",
    viewport_width=393,
    viewport_height=852,
    device_scale_factor=3.0,
    is_mobile=True,
    has_touch=True,
)
DEVICE_REGISTRY["iphone15pro"] = IPHONE_15_PRO
```

---

### 文件结构速查

```
services/browser_pipeline/                 # 浏览器自动化 Pipeline（统一基础设施）
├── __init__.py                            # 统一导出所有公开 API
├── pipeline.py                            # Pipeline / PipelineStep / PipelineContext
├── detached_step.py                       # DetachedWorkerStep（Step 基类）
├── detached_worker.py                     # DetachedBrowserWorker（Worker 基类）
├── detached_launcher.py                   # 启动器 + handle + 结果读取
└── _detached_worker_runner.py             # 子进程通用入口

services/browser/                          # 浏览器底层服务
├── cdp_launcher.py                        # CDP 服务管理
├── _cdp_server.py                         # CDP 服务独立进程
├── browser.py                             # 浏览器连接封装
└── finder.py                              # Chrome 查找与下载

services/meituan/                          # 美团业务工作流（纯业务代码）
├── workflow.py                            # 工作流编排入口
├── device_profiles.py                     # 设备模拟配置
├── browser_helper.py                      # 移动端页面创建工具
└── steps/
    ├── check_login.py                     # 登录验证 Step
    ├── search.py                          # 搜索 Step
    ├── meituan_login_worker.py            # 登录 Worker（子进程）
    └── meituan_search_worker.py           # 搜索 Worker（子进程）

commands/
└── meituan.py                             # CLI 入口
```

---

### 设计原则

- **单一入口**：业务代码只需 `from services.browser_pipeline import ...`，一个包搞定
- **基建与业务分离**：browser_pipeline 是基础设施，业务代码只需实现 Step/Worker 和编排
- **步骤独立**：每个 Step 只关注自己的逻辑，通过 Context 传递数据
- **可插拔**：Pipeline 支持运行时 add / insert / remove / replace 步骤
- **进程隔离**：需要用户介入的浏览器任务在子进程中运行，主进程退出不影响
- **协议统一**：所有 Worker 通过相同的 JSON 结果文件协议通信
- **设备可扩展**：通过 `DEVICE_REGISTRY` 注册新设备，Worker 通过 `device_name` 声明
