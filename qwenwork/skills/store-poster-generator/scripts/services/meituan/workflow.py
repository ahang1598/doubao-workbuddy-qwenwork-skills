"""
美团工作流入口。

暴露三个原子操作供 agent / CLI 调用：
1. run_check_login()  — 检测登录状态（detached，不打断）
2. run_login()        — 打开登录页（detached，打断），等待用户手动登录
3. run_search()       — 执行关键词搜索（detached）

agent 编排示例：
    ctx = run_check_login()            # detached worker 检测登录
    # 读取 result_file 获取 logged_in
    if not logged_in:
        run_login()                    # 打断，等用户操作
        ctx = run_check_login()        # 再次检测
    run_search(keyword="麦当劳")
"""

from services.browser_pipeline import Pipeline, PipelineContext
from services.meituan.steps.check_login import create_step as create_check_login_step
from services.meituan.steps.login import create_step as create_login_step
from services.meituan.steps.search import create_step as create_search_step


def run_check_login() -> PipelineContext:
    """检测美团登录状态（detached，不打断）。

    Returns:
        PipelineContext，包含 worker_pid、result_file 等信息。
        agent 通过读取 result_file 获取 logged_in 状态。
    """
    pipeline = Pipeline(name="meituan-check-login")
    pipeline.add_step(create_check_login_step())
    return pipeline.execute()


def run_login(*, timeout: int = 120) -> PipelineContext:
    """打开美团登录页面（detached，打断 pipeline）。

    启动 detached worker 子进程打开登录页面，
    主进程立即返回，等待用户在浏览器中完成登录。

    Args:
        timeout: 登录超时秒数

    Returns:
        PipelineContext，包含 worker_pid、result_file 等信息
    """
    pipeline = Pipeline(name="meituan-login")
    pipeline.add_step(create_login_step(timeout=timeout))
    return pipeline.execute()


def run_search(
    keyword: str,
    *,
    city: str = "hangzhou",
) -> PipelineContext:
    """执行美团搜索（detached）。

    启动 detached worker 子进程执行搜索，
    主进程立即返回 worker 信息。

    Args:
        keyword: 搜索关键词（如 "麦当劳"）
        city: 城市拼音（默认 "hangzhou"）

    Returns:
        PipelineContext，包含 worker_pid、result_file 等信息
    """
    pipeline = Pipeline(name="meituan-search")
    pipeline.add_step(create_search_step())
    return pipeline.execute(keyword=keyword, city=city)