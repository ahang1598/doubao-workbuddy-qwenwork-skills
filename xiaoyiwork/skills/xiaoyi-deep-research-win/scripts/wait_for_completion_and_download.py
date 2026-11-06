"""
wait_for_completion_and_download.py(版本 B + 120s yieldMs 上限适配)

变更点(相对于 _b 版本):
- 启动时在会话目录写入 start_time.txt(epoch 秒),供 check_status.py 判断累计耗时,
  替代 agent 自己计数循环次数(循环节奏不可靠时,时间判断更稳)。
- 其他逻辑保持 _b 版本。
"""

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Optional, Tuple

import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning

from claw_doc_gen import gen_code_file
from claw_pipe_http import PipeHttpError
from config import Config
from deliver_report import deliver_file
from local_report_docx import generate_local_docx, validate_docx
from session_state import load_state

urllib3.disable_warnings(InsecureRequestWarning)

logger = logging.getLogger("poll_dr")
logger.addHandler(logging.NullHandler())

EXIT_OK = 0
EXIT_DOWNLOAD_FAILED = 1
EXIT_FAILED = 2

CLOUD_STATUS_FAILED = 1
CLOUD_STATUS_COMPLETED = 100
CLOUD_STATUS_RESEARCHING_VALUES = {0, 2}

CHECK_PATH = "/celia-claw/v1/rest-api/skill/execute"

STATUS_FILENAME = "status.json"
START_TIME_FILENAME = "start_time.txt"  # 新增:记录任务实际开始时间

START_TIME = time.monotonic()
STATUS_FILE_PATH: Optional[Path] = None
CURRENT_SESSION_ID = ""


def write_status(phase: str, **fields) -> None:
    if STATUS_FILE_PATH is None:
        return

    terminal_phases = {
        "completed", "completed_fallback", "download_failed", "cloud_failed", "doc_gen_failed",
        "polling_timeout", "network_unstable", "poll_crashed",
        "unknown_status", "preflight_failed", "result_mismatch", "terminated",
    }

    payload = {
        "phase": phase,
        "is_terminal": phase in terminal_phases,
        "timestamp": int(time.time()),
        "elapsed_s": round(time.monotonic() - START_TIME, 1),
    }
    if CURRENT_SESSION_ID:
        payload["session_id"] = CURRENT_SESSION_ID
    payload.update(fields)

    try:
        tmp_path = STATUS_FILE_PATH.with_suffix(".json.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        tmp_path.replace(STATUS_FILE_PATH)
    except Exception as e:
        print(f"[WARN] status.json 写入失败: {e}", file=sys.stderr)


def emit_final_result(exit_code: int, phase: str, message: str, **extra) -> int:
    write_status(phase, exit_code=exit_code, message=message, **extra)
    result = {"exit_code": exit_code, "phase": phase, "message": message, **extra}
    print("=== RESULT_FOR_AGENT ===", flush=True)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return exit_code


def _setup_logger(log_path: Path) -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    for existing in logger.handlers:
        existing.close()
    logger.handlers.clear()
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(handler)


def log_event(event: str, **kwargs) -> None:
    logger.info(f"EVENT: {json.dumps({'event': event, **kwargs}, ensure_ascii=False)}")


def on_terminate(signum, frame):
    elapsed = time.monotonic() - START_TIME
    try:
        sig_name = signal.Signals(signum).name
    except Exception:
        sig_name = str(signum)
    log_event("terminated", signal=sig_name, elapsed_s=round(elapsed, 1))
    emit_final_result(
        EXIT_FAILED,
        phase="terminated",
        message=f"脚本被信号 {sig_name} 中断",
        signal=sig_name,
    )
    sys.exit(EXIT_FAILED)


def write_start_time_if_first(session_dir: Path) -> None:
    """
    第一次启动时写入 start_time.txt;重启时保留原始时间,
    供 check_status.py 计算"自最初提交起经过多久"。
    """
    start_file = session_dir / START_TIME_FILENAME
    if not start_file.exists():
        try:
            start_file.write_text(str(int(time.time())), encoding="utf-8")
        except Exception as e:
            print(f"[WARN] start_time.txt 写入失败: {e}", file=sys.stderr)


def load_task(session_id: str, session_dir: Path) -> dict:
    task_file = session_dir / "task.json"
    if not task_file.is_file():
        raise FileNotFoundError("找不到本会话的 task.json；submit_research.py 可能未成功执行")
    task = json.loads(task_file.read_text(encoding="utf-8"))
    if task.get("session_id") != session_id:
        raise ValueError("task.json 与当前会话 ID 不匹配，拒绝轮询")
    if not isinstance(task.get("task_id"), str) or not task["task_id"].strip():
        raise ValueError("task.json 缺少有效 task_id")
    return task


def preflight(session_id: str) -> Tuple[Config, Path, Path, dict]:
    global CURRENT_SESSION_ID, STATUS_FILE_PATH

    try:
        state = load_state(session_id)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
        print("=== RESULT_FOR_AGENT ===", flush=True)
        print(json.dumps({
            "exit_code": EXIT_FAILED,
            "phase": "preflight_failed",
            "message": f"无法恢复深度研究会话: {e}",
            "diagnosis": "必须传入 session_state.py init 创建的准确会话 ID。",
        }, ensure_ascii=False), flush=True)
        sys.exit(EXIT_FAILED)

    CURRENT_SESSION_ID = state["DR_SESSION_ID"]
    session_dir = Path(state["DR_SESSION_DIR"])
    delivery_dir = Path(state["DR_DELIVERY_DIR"])
    delivery_dir.mkdir(parents=True, exist_ok=True)

    try:
        session_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print("=== RESULT_FOR_AGENT ===", flush=True)
        print(json.dumps({
            "exit_code": EXIT_FAILED,
            "phase": "preflight_failed",
            "message": f"会话目录无法创建: {e}",
        }, ensure_ascii=False), flush=True)
        sys.exit(EXIT_FAILED)

    STATUS_FILE_PATH = session_dir / STATUS_FILENAME
    write_status("starting", message="脚本启动,正在做初始化")
    write_start_time_if_first(session_dir)

    _setup_logger(session_dir / "generate.log")
    log_event("preflight_start", session_dir=str(session_dir))

    try:
        cfg = Config.load()
    except ValueError as e:
        log_event("config_load_failed", error=str(e))
        emit_final_result(EXIT_FAILED, phase="preflight_failed",
                          message=f"配置加载失败: {e}")
        sys.exit(EXIT_FAILED)

    try:
        task = load_task(CURRENT_SESSION_ID, session_dir)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        emit_final_result(EXIT_FAILED, phase="preflight_failed",
                          message=f"本会话任务状态无效: {e}")
        sys.exit(EXIT_FAILED)

    log_event("preflight_ok", session_id=CURRENT_SESSION_ID, task_id=task["task_id"])
    return cfg, session_dir, delivery_dir, task


def write_json_atomic(path: Path, payload: dict) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def response_task_id(response_body: dict) -> Optional[str]:
    """Return a cloud correlation id when the response exposes one."""
    candidates = [response_body]
    data = response_body.get("data")
    if isinstance(data, dict):
        candidates.append(data)
        results = data.get("results")
        if isinstance(results, list) and results and isinstance(results[0], dict):
            candidates.append(results[0])
    for item in candidates:
        for key in ("researchCacheKey", "chatId"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def get_detail_and_trans_to_doc(res, cfg):
    res_dict = res["data"]["results"][0]
    return gen_code_file(
        str(uuid.uuid4()),
        res_dict["content"]["answer_content"],
        "docx",
        {},
        res_dict["content"].get("ref_list", ""),
        cfg=cfg,
    )


def download_file(url, filename, output_dir):
    temporary = Path(output_dir) / ("cloud-report." + uuid.uuid4().hex + ".part")
    try:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        # A cloud filename must never overwrite task.json / source or escape the session.
        local_path = output_dir / "cloud-report.docx"
        with requests.get(url, stream=True, timeout=30, verify=False) as response:
            response.raise_for_status()
            with open(temporary, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        validate_docx(temporary)
        os.replace(temporary, local_path)
        return True, str(local_path), ""
    except requests.exceptions.Timeout:
        return False, "", "下载超时"
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else "未知"
        return False, "", f"下载被拒绝或失败（HTTP {code}）"
    except requests.exceptions.RequestException as e:
        return False, "", f"下载网络异常: {type(e).__name__}"
    except ValueError as e:
        return False, "", str(e)
    except IOError as e:
        return False, "", f"文件写入失败: {str(e)}"
    finally:
        if temporary.exists():
            temporary.unlink()


def complete_report(res, cfg, output_dir, delivery_dir, task):
    """Try the cloud DOCX once, then render the completed report offline once."""
    content = res["data"]["results"][0].get("content", {})
    source = {
        "session_id": CURRENT_SESSION_ID, "task_id": task["task_id"],
        "query_sha256": task.get("query_sha256", ""), "content": content,
    }
    # Save the exact cloud content before conversion / downloads can fail.
    source_file = output_dir / "report_source.json"
    write_json_atomic(source_file, source)
    file_name, paper_url, error = "深度研究报告.docx", "", ""
    try:
        file_name, paper_url = get_detail_and_trans_to_doc(res, cfg)
        if not isinstance(file_name, str) or not file_name.strip():
            file_name = "深度研究报告.docx"
        success, local_path, error = download_file(paper_url, file_name, output_dir)
    except Exception as exc:
        success, local_path = False, ""
        error = f"云端文档生成异常: {type(exc).__name__}"

    fallback = not success
    if fallback:
        log_event("local_docx_fallback_start", reason=error)
        write_status("generating_local_report", task_id=task["task_id"],
                     message="云端文档获取失败，正在用已完成的研究结果生成本地 DOCX")
        try:
            if not isinstance(content, dict):
                raise ValueError("云端报告正文格式错误")
            local_path = str(generate_local_docx(content.get("answer_content"), content.get("ref_list", ""),
                                                 output_dir / "local-report.docx"))
            # Always deliver a DOCX extension, regardless of a malformed cloud name.
            file_name = Path(file_name.replace("\\", "/")).stem + ".docx"
        except Exception as exc:
            fallback_error = f"本地 DOCX 生成失败: {type(exc).__name__}: {exc}"
            log_event("local_docx_fallback_failed", error=fallback_error)
            phase = "download_failed" if paper_url else "doc_gen_failed"
            info = {"status": phase, "file_name": file_name, **source,
                    "source_file": str(source_file), "download_error": error,
                    "fallback_error": fallback_error}
            info.pop("content")
            if paper_url:
                info["paper_url"] = paper_url
            write_json_atomic(output_dir / "result.json", info)
            return emit_final_result(
                EXIT_DOWNLOAD_FAILED if paper_url else EXIT_FAILED, phase=phase,
                message=f"{error}；{fallback_error}", file_name=file_name,
                **({"paper_url": paper_url} if paper_url else {}),
                result_file=str(output_dir / "result.json"),
            )

    delivered = deliver_file(Path(local_path), delivery_dir, file_name)
    phase = "completed_fallback" if fallback else "completed"
    info = {
        "status": phase, "file_name": delivered.name, "local_path": str(delivered),
        "session_id": CURRENT_SESSION_ID, "task_id": task["task_id"],
        "query_sha256": task.get("query_sha256", ""), "source_file": str(source_file),
        "report_origin": "local_fallback" if fallback else "cloud_download",
    }
    if fallback:
        info["fallback_reason"] = error
        if paper_url:
            info["paper_url"] = paper_url
    write_json_atomic(output_dir / "result.json", info)
    return emit_final_result(
        EXIT_OK, phase=phase,
        message="研究完成，已生成本地 DOCX 兜底报告" if fallback else "研究完成,报告已下载",
        file_name=delivered.name, local_path=str(delivered), report_origin=info["report_origin"],
        result_file=str(output_dir / "result.json"),
    )


def _run_polling(session_id: str) -> int:
    signal.signal(signal.SIGTERM, on_terminate)
    signal.signal(signal.SIGINT, on_terminate)

    cfg, output_dir, delivery_dir, task = preflight(session_id)
    task_id = task["task_id"]

    headers = {
        "Content-Type": "application/json",
        "x-skill-id": "deep_research_check_task",
        "x-hag-trace-id": cfg.sn,
        **cfg.auth_headers(),  # 管道形态返回空;旧沙箱 http 直连需要
    }
    data = {"userId": str(cfg.personal_uid), "chatId": task_id, "researchType": 0}

    start = time.time()
    poll_count = 0
    consecutive_errors = 0

    write_status("polling", task_id=task_id, poll_count=0,
                 message="开始轮询云端任务状态")

    while time.time() < start + 3600:
        poll_count += 1

        try:
            # 命名管道形态经主进程 SkillApiProxy 转发(np://claw-skill);
            # 旧沙箱形态 http(s) 直连由 config.skill_post 内部处理。
            response = cfg.skill_post(CHECK_PATH, data, headers=headers)
            res = json.loads(response.text)
            cloud_task_id = response_task_id(res)
            if cloud_task_id is not None and cloud_task_id != task_id:
                return emit_final_result(
                    EXIT_FAILED, phase="result_mismatch",
                    message="云端返回的任务标识与本会话不一致，已停止交付",
                    expected_task_id=task_id,
                    actual_task_id=cloud_task_id,
                )
            status = res["data"]["results"][0].get("status", "")
            consecutive_errors = 0

            if not status:
                log_event("researching", poll_count=poll_count)
                write_status("polling", task_id=task_id, poll_count=poll_count,
                             message="云端研究进行中")
                time.sleep(15)
                continue

            if status == CLOUD_STATUS_FAILED:
                log_event("cloud_failed")
                return emit_final_result(
                    EXIT_FAILED, phase="cloud_failed",
                    message="云端研究任务失败",
                    diagnosis="云端任务进入失败状态。可建议用户调整 query 后重新提交。",
                    task_id=task_id,
                )

            if status == CLOUD_STATUS_COMPLETED:
                log_event("research_completed", poll_count=poll_count)
                write_status("downloading", task_id=task_id,
                             message="云端完成,正在生成并下载文档")

                return complete_report(res, cfg, output_dir, delivery_dir, task)

            if status in CLOUD_STATUS_RESEARCHING_VALUES:
                log_event("researching", poll_count=poll_count)
                write_status("polling", task_id=task_id, poll_count=poll_count,
                             message="云端研究进行中")
                time.sleep(15)
                continue

            return emit_final_result(
                EXIT_FAILED, phase="unknown_status",
                message=f"云端返回未知状态: {status}",
                task_id=task_id,
            )

        except requests.exceptions.Timeout:
            consecutive_errors += 1
            log_event("poll_timeout", consecutive_errors=consecutive_errors)
            write_status("polling", task_id=task_id, poll_count=poll_count,
                         consecutive_errors=consecutive_errors,
                         message="云端响应超时,稍后重试")
        except PipeHttpError as e:
            consecutive_errors += 1
            log_event("poll_pipe_error", error=str(e))
            write_status("polling", task_id=task_id, poll_count=poll_count,
                         consecutive_errors=consecutive_errors,
                         message=f"命名管道异常: {e}")
        except requests.exceptions.RequestException as e:
            consecutive_errors += 1
            log_event("poll_request_error", error=str(e))
            write_status("polling", task_id=task_id, poll_count=poll_count,
                         consecutive_errors=consecutive_errors,
                         message=f"网络异常: {e}")
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            return emit_final_result(
                EXIT_FAILED, phase="poll_crashed",
                message=f"云端响应解析失败: {e}", task_id=task_id,
            )
        except Exception as e:
            return emit_final_result(
                EXIT_FAILED, phase="poll_crashed",
                message=f"轮询循环异常: {e}", task_id=task_id,
            )

        if consecutive_errors >= 10:
            return emit_final_result(
                EXIT_FAILED, phase="network_unstable",
                message=f"连续 {consecutive_errors} 次轮询网络失败",
                task_id=task_id,
            )

        time.sleep(15)

    return emit_final_result(
        EXIT_FAILED, phase="polling_timeout",
        message="轮询 1 小时仍未拿到终态",
        task_id=task_id, poll_count=poll_count,
    )


DAEMON_CHILD_ENV = "DR_DAEMON_CHILD"


def _daemonize(session_id: str) -> int:
    """
    把真正的轮询循环 fork 到后台子进程,父进程立即返回。

    背景:exec 前台执行有 timeout 上限(本次环境约 120s),wait 脚本是常驻
    轮询进程,若直接跑在前台会被超时杀,导致后台无进程 → 任务卡死、永远
    拿不到报告。这里用 subprocess 再拉起一个自身进程并在后台运行,父进程
    立刻打印 RESULT_FOR_AGENT 返回(退出码 0),不触发前台超时。

    子进程通过环境变量 DAEMON_CHILD_ENV 标记,避免再次 fork。
    """
    script = Path(os.path.abspath(sys.argv[0])).resolve()

    # 父进程先验证作业状态，避免后台子进程启动后才静默失败。
    try:
        state = load_state(session_id)
        session_id = state["DR_SESSION_ID"]
        load_task(state["DR_SESSION_ID"], Path(state["DR_SESSION_DIR"]))
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
        print("=== RESULT_FOR_AGENT ===", flush=True)
        print(json.dumps({
            "exit_code": EXIT_FAILED,
            "phase": "preflight_failed",
            "message": f"本会话任务状态无效: {e}",
        }, ensure_ascii=False), flush=True)
        return EXIT_FAILED

    env = dict(os.environ)
    env[DAEMON_CHILD_ENV] = "1"

    # 无窗口解释器:同目录的 pythonw.exe(pythonw 是 GUI 子系统进程,
    # 永远不会创建控制台窗口,从根上消除深度研究触发时的终端弹窗)。
    def _windowless_python() -> str:
        if os.name != "nt":
            return sys.executable
        base = os.path.normpath(sys.executable)
        if not base.lower().endswith(".exe"):
            return sys.executable
        stem = base[:-4]
        # 优先 pythonX.exe -> pythonXw.exe; python.exe -> pythonw.exe
        for candidate in (stem + "w.exe",
                          os.path.join(os.path.dirname(base), "pythonw.exe")):
            if os.path.isfile(candidate):
                return candidate
        # 找不到 windows 时回退原解释器,并改用安全的创建标志
        return sys.executable

    try:
        with open(os.devnull, "w") as devnull:
            if os.name == "nt":
                # Windows:脱离控制台/进程组,前台超时杀不到它。
                # 关键:用 pythonw.exe 作为解释器(GUI 子系统,无控制台窗口),
                # pythonw 使用 DETACHED_PROCESS；缺少 pythonw 时使用 CREATE_NO_WINDOW，
                # 两个标志不能组合，否则 CREATE_NO_WINDOW 被忽略。
                interpreter = _windowless_python()
                is_windowless = os.path.basename(interpreter).lower().endswith("w.exe")
                if is_windowless:
                    creationflags = (
                        subprocess.CREATE_NEW_PROCESS_GROUP
                        | subprocess.DETACHED_PROCESS
                    )
                else:
                    creationflags = (
                        subprocess.CREATE_NEW_PROCESS_GROUP
                        | getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    )
                proc = subprocess.Popen(
                    [interpreter, str(script), "--session-id", session_id],
                    env=env,
                    stdout=devnull,
                    stderr=devnull,
                    stdin=subprocess.DEVNULL,
                    creationflags=creationflags,
                    close_fds=True,
                )
            else:
                proc = subprocess.Popen(
                    [sys.executable, str(script), "--session-id", session_id],
                    env=env,
                    stdout=devnull,
                    stderr=devnull,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                    close_fds=True,
                )
    except Exception as e:
        print("=== RESULT_FOR_AGENT ===", flush=True)
        print(json.dumps({
            "exit_code": EXIT_FAILED,
            "phase": "daemonize_failed",
            "message": f"后台守护启动失败: {e}",
        }, ensure_ascii=False), flush=True)
        return EXIT_FAILED

    # 子进程 preflight 需要一点时间写 status.json;
    # 父进程稍作等待,让 check_status 首次读到的是新会话而不是旧状态。
    time.sleep(1.5)

    print("=== RESULT_FOR_AGENT ===", flush=True)
    print(json.dumps({
        "exit_code": EXIT_OK,
        "phase": "daemonized",
        "message": "wait 脚本已在后台启动,开始轮询云端任务",
        "session_id": session_id,
    }, ensure_ascii=False), flush=True)
    return EXIT_OK


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-id", required=True, help="本次深度研究作业 UUID")
    args = parser.parse_args()

    # 若已由守护拉起(子进程),直接进入轮询循环;
    # 否则先把自己转入后台,父进程返回,子进程再进来跑轮询。
    if os.environ.get(DAEMON_CHILD_ENV) != "1":
        return _daemonize(args.session_id)
    return _run_polling(args.session_id)


if __name__ == "__main__":
    sys.exit(main())
