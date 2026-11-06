"""
wait_for_completion_and_download.py(版本 B + 120s yieldMs 上限适配)

变更点(相对于 _b 版本):
- 启动时在会话目录写入 start_time.txt(epoch 秒),供 check_status.py 判断累计耗时,
  替代 agent 自己计数循环次数(循环节奏不可靠时,时间判断更稳)。
- 其他逻辑保持 _b 版本。
"""

import json
import logging
import os
import signal
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

SESSION_MARKER_FILENAME = ".current_session_dir"
STATUS_FILENAME = "status.json"
START_TIME_FILENAME = "start_time.txt"  # 新增:记录任务实际开始时间

START_TIME = time.monotonic()
STATUS_FILE_PATH: Optional[Path] = None


def write_status(phase: str, **fields) -> None:
    if STATUS_FILE_PATH is None:
        return

    terminal_phases = {
        "completed", "download_failed", "cloud_failed", "doc_gen_failed",
        "polling_timeout", "network_unstable", "poll_crashed",
        "unknown_status", "preflight_failed", "terminated",
    }

    payload = {
        "phase": phase,
        "is_terminal": phase in terminal_phases,
        "timestamp": int(time.time()),
        "elapsed_s": round(time.monotonic() - START_TIME, 1),
        **fields,
    }

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


def resolve_session_dir(script_dir: Path) -> Optional[Path]:
    marker_file = script_dir / SESSION_MARKER_FILENAME
    if marker_file.exists():
        try:
            content = marker_file.read_text(encoding="utf-8").strip()
            if content:
                return Path(content)
        except Exception:
            pass
    env_val = os.getenv("DR_SESSION_DIR", "").strip()
    if env_val:
        return Path(env_val)
    return None


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


def preflight() -> Tuple[Config, Path, str]:
    global STATUS_FILE_PATH

    script_dir = Path(os.path.abspath(sys.argv[0])).parent

    session_dir = resolve_session_dir(script_dir)
    if session_dir is None:
        print("=== RESULT_FOR_AGENT ===", flush=True)
        print(json.dumps({
            "exit_code": EXIT_FAILED,
            "phase": "preflight_failed",
            "message": "无法解析会话目录",
            "diagnosis": "找不到 .current_session_dir 文件且 DR_SESSION_DIR 未设置。",
        }, ensure_ascii=False), flush=True)
        sys.exit(EXIT_FAILED)

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

    task_id_file = script_dir / "task_id.json"
    if not task_id_file.exists():
        emit_final_result(EXIT_FAILED, phase="preflight_failed",
                          message="找不到 task_id.json",
                          diagnosis="submit_research.py 可能未成功执行。")
        sys.exit(EXIT_FAILED)

    try:
        with open(task_id_file, encoding="utf-8") as f:
            task_id = json.load(f)["task_id"]
    except (json.JSONDecodeError, KeyError) as e:
        emit_final_result(EXIT_FAILED, phase="preflight_failed",
                          message=f"task_id.json 解析失败: {e}")
        sys.exit(EXIT_FAILED)

    log_event("preflight_ok", task_id=task_id)
    return cfg, session_dir, task_id


def get_detail_and_trans_to_doc(res, cfg):
    res_dict = res["data"]["results"][0]
    return gen_code_file(
        str(uuid.uuid4()),
        res_dict["content"]["answer_content"],
        "docx",
        {},
        res_dict["content"]["ref_list"],
        cfg=cfg,
    )


def download_file(url, filename, output_dir):
    try:
        response = requests.get(url, stream=True, timeout=30, verify=False)
        response.raise_for_status()
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        local_path = output_dir / filename
        with open(local_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True, str(local_path), ""
    except requests.exceptions.Timeout:
        return False, "", "下载超时"
    except requests.exceptions.RequestException as e:
        return False, "", f"下载失败: {str(e)}"
    except IOError as e:
        return False, "", f"文件写入失败: {str(e)}"


def main() -> int:
    signal.signal(signal.SIGTERM, on_terminate)
    signal.signal(signal.SIGINT, on_terminate)

    cfg, output_dir, task_id = preflight()

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

                try:
                    file_name, paper_url = get_detail_and_trans_to_doc(res, cfg)
                except Exception as e:
                    log_event("doc_gen_failed", error=str(e))
                    return emit_final_result(
                        EXIT_FAILED, phase="doc_gen_failed",
                        message=f"文档生成失败: {e}",
                        task_id=task_id,
                    )

                success, local_path, error = download_file(paper_url, file_name, output_dir)

                if success:
                    result_info = {
                        "status": "completed", "file_name": file_name,
                        "local_path": local_path, "task_id": task_id,
                    }
                    with open(output_dir / "result.json", "w", encoding="utf-8") as f:
                        json.dump(result_info, f, ensure_ascii=False, indent=4)
                    return emit_final_result(
                        EXIT_OK, phase="completed",
                        message="研究完成,报告已下载",
                        file_name=file_name, local_path=local_path,
                        result_file=str(output_dir / "result.json"),
                    )

                if paper_url:
                    result_info = {
                        "status": "download_failed", "file_name": file_name,
                        "paper_url": paper_url, "task_id": task_id,
                    }
                    with open(output_dir / "result.json", "w", encoding="utf-8") as f:
                        json.dump(result_info, f, ensure_ascii=False, indent=4)
                    return emit_final_result(
                        EXIT_DOWNLOAD_FAILED, phase="download_failed",
                        message=f"报告下载失败但有云端链接: {error}",
                        file_name=file_name, paper_url=paper_url,
                        result_file=str(output_dir / "result.json"),
                    )

                return emit_final_result(
                    EXIT_FAILED, phase="doc_gen_failed",
                    message=f"下载失败且无云端链接: {error}",
                    task_id=task_id,
                )

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


if __name__ == "__main__":
    sys.exit(main())