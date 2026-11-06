import datetime
import uuid
import time
import hmac
import base64
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning

from claw_pipe_http import PipeHttpError
from config import Config

# 内网环境使用自签证书,忽略 SSL 验证警告（仅旧沙箱直连形态需要）
urllib3.disable_warnings(InsecureRequestWarning)

logger = logging.getLogger("submit_dr")
logger.addHandler(logging.NullHandler())

# ============================================================
# 退出码契约(与 wait_for_completion_and_download.py 保持一致)
# ============================================================
EXIT_OK = 0
EXIT_FAILED = 2

# ============================================================
# 跨 exec 状态文件
# ============================================================
SESSION_MARKER_FILENAME = ".current_session_dir"

# ============================================================
# 业务限制
# ============================================================
MAX_QUERY_LENGTH = 2000   # query 最长字符数,超过截断并警告
HTTP_TIMEOUT_S = 60        # 提交请求 HTTP 超时

# 白名单:允许带给云端的环境变量(避免泄露敏感配置)
ALLOWED_EXTRA_ENV_KEYS = (
    "DR_SESSION_ID",
    "OPENCLAW_SHELL",
    # 如有其他云端确实需要的字段,按需扩展;不要直接传 dict(os.environ)
)


# ============================================================
# Agent-facing 输出
# ============================================================
def emit_agent_result(exit_code: int, phase: str, message: str, **extra) -> int:
    """统一终态输出。脚本退出前必须调用且只调用一次。"""
    result = {"exit_code": exit_code, "phase": phase, "message": message, **extra}
    print("=== RESULT_FOR_AGENT ===", flush=True)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return exit_code


# ============================================================
# Human-facing 日志
# ============================================================
def _setup_logger(log_path: Path) -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    logger.handlers.clear()
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(handler)


def log_event(event: str, **kwargs) -> None:
    logger.info(f"EVENT: {json.dumps({'event': event, **kwargs}, ensure_ascii=False)}")


# ============================================================
# 跨 exec 状态读取
# ============================================================
def resolve_session_dir(script_dir: Path) -> Optional[Path]:
    """读取 .current_session_dir,获取会话目录路径。失败返回 None。"""
    marker_file = script_dir / SESSION_MARKER_FILENAME
    if marker_file.exists():
        try:
            content = marker_file.read_text(encoding="utf-8").strip()
            if content:
                return Path(content)
        except Exception:
            pass

    # Fallback 到环境变量(向后兼容,允许调试场景)
    env_val = os.getenv("DR_SESSION_DIR", "").strip()
    if env_val:
        return Path(env_val)

    return None


# ============================================================
# 输入校验
# ============================================================
def parse_query() -> Tuple[bool, str, str]:
    """
    解析命令行 query 参数。
    返回 (是否合法, 处理后的 query, 警告信息)。
    """
    if len(sys.argv) < 2:
        return False, "", "缺少 query 命令行参数"

    query = sys.argv[1].strip()
    if not query:
        return False, "", "query 为空字符串"

    warning = ""
    if len(query) > MAX_QUERY_LENGTH:
        warning = f"query 长度 {len(query)} 超过 {MAX_QUERY_LENGTH},已截断"
        query = query[:MAX_QUERY_LENGTH]

    return True, query, warning


# ============================================================
# 请求体构造
# ============================================================
def build_request_body(template_path: Path, query: str, cfg: Config) -> dict:
    with open(template_path, encoding="utf-8") as f:
        data = json.load(f)

    data["query"] = query
    data["extraInfo"]["context"]["userInfo"]["uid"] = str(cfg.personal_uid)
    data["extraInfo"]["session"]["sessionId"] = str(cfg.sessionId)

    # 白名单方式注入环境上下文,避免泄露敏感变量
    data["claw_extra_info"] = {
        k: os.environ[k] for k in ALLOWED_EXTRA_ENV_KEYS if k in os.environ
    }
    return data


# ============================================================
# SSE 响应解析
# ============================================================
SUBMIT_PATH = "/celia-claw/v1/sse-api/skill/execute"
def extract_task_id_from_sse(response: requests.Response) -> Tuple[Optional[str], str]:
    """
    从 SSE 流中提取 task_id。
    返回 (task_id, 诊断信息)。task_id 为 None 表示提取失败。
    """
    lines_seen = 0
    parse_errors = 0
    events_seen = []

    for line in response.iter_lines():
        if not line:
            continue
        lines_seen += 1

        try:
            line_str = line.decode("utf-8", errors="replace")
        except Exception as e:
            parse_errors += 1
            log_event("sse_decode_error", error=str(e))
            continue

        if line_str.startswith("id"):
            continue

        # SSE 协议中,data 行以 "data:" 开头
        payload_str = line_str[len("data:"):] if line_str.startswith("data:") else line_str

        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError:
            parse_errors += 1
            continue

        event_type = payload.get("event")
        if event_type:
            events_seen.append(event_type)

        if event_type != "command":
            continue

        # 进入 command 事件深层解析
        try:
            content = json.loads(payload["content"])
            directives = content.get("directives", [])
            if not directives:
                log_event("sse_empty_directives")
                continue
            task_id = directives[0]["payload"]["cardParams"]["researchCacheKey"]
            if task_id:
                log_event("task_id_extracted", task_id=task_id,
                          lines_seen=lines_seen, parse_errors=parse_errors)
                return task_id, ""
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
            log_event("sse_command_parse_error", error=str(e),
                      payload_preview=payload_str[:200])
            continue

    diagnosis = (
        f"SSE 流处理完毕但未提取到 task_id。"
        f"共处理 {lines_seen} 行,解析错误 {parse_errors} 次,"
        f"出现的事件类型: {events_seen or '<无>'}。"
    )
    return None, diagnosis


# ============================================================
# 主流程
# ============================================================
def main() -> int:
    script_dir = Path(os.path.abspath(sys.argv[0])).parent

    # ---- 启动日志(如果会话目录可解析)----
    session_dir = resolve_session_dir(script_dir)
    if session_dir is not None:
        try:
            session_dir.mkdir(parents=True, exist_ok=True)
            _setup_logger(session_dir / "generate.log")
            log_event("submit_start", script_dir=str(script_dir),
                      session_dir=str(session_dir))
        except Exception as e:
            # 日志建不起来不致命,继续跑;agent-facing 输出仍可用
            print(f"[WARN] 日志初始化失败: {e}", file=sys.stderr)
            session_dir = None

    # ---- 输入校验 ----
    ok, query, warning = parse_query()
    if not ok:
        return emit_agent_result(
            EXIT_FAILED,
            phase="invalid_input",
            message=warning,
            diagnosis="调用 submit_research.py 时必须把 CONFIRMED_QUERY 作为第一个命令行参数,且不能为空。",
        )
    if warning:
        log_event("query_warning", warning=warning)

    # ---- 配置加载 ----
    try:
        cfg = Config.load()
    except ValueError as e:
        log_event("config_load_failed", error=str(e))
        return emit_agent_result(
            EXIT_FAILED,
            phase="config_load_failed",
            message=f"配置加载失败: {e}",
            diagnosis="检查 config 模块要求的环境变量或配置文件是否齐全。",
        )

    # ---- 构造请求体 ----
    template_path = script_dir / "req_template.json"
    if not template_path.exists():
        log_event("template_missing", path=str(template_path))
        return emit_agent_result(
            EXIT_FAILED,
            phase="template_missing",
            message="找不到 req_template.json",
            diagnosis=f"模板文件应位于 {template_path},检查 skill 部署是否完整。",
        )

    try:
        body = build_request_body(template_path, query, cfg)
    except (KeyError, json.JSONDecodeError) as e:
        log_event("template_invalid", error=str(e))
        return emit_agent_result(
            EXIT_FAILED,
            phase="template_invalid",
            message=f"请求模板解析失败: {e}",
            diagnosis="req_template.json 格式异常或缺少必需字段,检查模板结构。",
        )

    # ---- 发送请求(timestamp 在此处生成,确保新鲜)----
    headers = {
        "Content-Type": "application/json",
        "x-skill-id": "deep_research_create_task",
        "timestamp": str(int(time.time() * 1000)),
        "x-hag-trace-id": cfg.sn,
    }

    t_start = time.time()
    try:
        # 命名管道形态经主进程 SkillApiProxy 转发(np://claw-skill);
        # 旧沙箱形态 http(s) 直连由 config.skill_post 内部处理。
        response = cfg.skill_post(
            SUBMIT_PATH,
            body,
            headers=headers,
        )
        response.raise_for_status()
    except PipeHttpError as e:
        log_event("pipe_http_error", error=str(e))
        return emit_agent_result(
            EXIT_FAILED,
            phase="http_request_failed",
            message=f"命名管道请求异常: {e}",
            diagnosis="检查主进程 skill API 代理是否可用(CLAW_SKILL_TOKEN 是否注入)。",
        )
    except requests.exceptions.Timeout:
        log_event("http_timeout", timeout_s=HTTP_TIMEOUT_S)
        return emit_agent_result(
            EXIT_FAILED,
            phase="http_timeout",
            message=f"提交请求 {HTTP_TIMEOUT_S}s 内未完成",
            diagnosis="云端响应缓慢或网络不通,检查 service_url 与网络连通性。",
        )
    except requests.exceptions.HTTPError as e:
        log_event("http_error", status_code=response.status_code, error=str(e))
        return emit_agent_result(
            EXIT_FAILED,
            phase="http_error",
            message=f"云端返回 HTTP {response.status_code}: {e}",
            diagnosis="云端拒绝了提交请求。检查鉴权头、用户 ID、请求体格式。",
            status_code=response.status_code,
        )
    except requests.exceptions.RequestException as e:
        log_event("http_request_failed", error=str(e))
        return emit_agent_result(
            EXIT_FAILED,
            phase="http_request_failed",
            message=f"网络请求异常: {e}",
            diagnosis="检查网络连通性与云端服务可用性。",
        )

    # ---- SSE 解析 ----
    try:
        task_id, diagnosis = extract_task_id_from_sse(response)
    finally:
        response.close()
    if not task_id:
        return emit_agent_result(
            EXIT_FAILED,
            phase="task_id_missing",
            message="提交成功但未能从云端响应中提取 task_id",
            diagnosis=diagnosis or "云端 SSE 响应格式可能已变更,检查 extract_task_id_from_sse 解析逻辑。",
        )

    # ---- 持久化 task_id ----
    task_id_file = script_dir / "task_id.json"
    try:
        with open(task_id_file, "w", encoding="utf-8") as f:
            json.dump({"task_id": task_id}, f, ensure_ascii=False, indent=4)
    except IOError as e:
        log_event("task_id_persist_failed", error=str(e))
        return emit_agent_result(
            EXIT_FAILED,
            phase="task_id_persist_failed",
            message=f"task_id 写入文件失败: {e}",
            diagnosis=f"无法写入 {task_id_file},检查目录权限。",
            task_id=task_id,
        )

    consumed_s = round(time.time() - t_start, 1)
    log_event("submit_done", task_id=task_id, consumed_s=consumed_s)

    # 保留原有的人话提示行,兼容 skill 文档里的旧出口检查(查找"深度研究任务id是:"字符串)
    print(f"深度研究任务id是:{task_id}", flush=True)

    return emit_agent_result(
        EXIT_OK,
        phase="submitted",
        message="深度研究任务已提交",
        task_id=task_id,
        task_id_file=str(task_id_file),
        consumed_s=consumed_s,
    )


if __name__ == "__main__":
    sys.exit(main())