"""
check_status.py(版本 B + 120s yieldMs 上限适配)

变更点:
- 读取 start_time.txt(若存在),计算"自最初提交起总秒数"作为 total_elapsed_s 返回。
  agent 用 total_elapsed_s 而不是循环计数来判断超时,即使中间重启 wait 脚本也准确。
"""

import argparse
import json
import sys
import time
from pathlib import Path

from session_state import load_state


STATUS_FILENAME = "status.json"
START_TIME_FILENAME = "start_time.txt"

EXIT_TERMINAL = 0
EXIT_RUNNING = 1
EXIT_NO_STATUS = 2


def emit(exit_code: int, phase: str, message: str, **extra) -> int:
    # 注意:进程退出码与 JSON 里的 exit_code 字段是两回事。
    # - JSON 里的 "exit_code" 是给 agent 用的状态信号(0=终态 / 1=运行中 / 2=状态异常),
    #   agent 通过读取 ===RESULT_FOR_AGENT=== 下一行 JSON 的 exit_code 分支(见 step_generate_monitor.md)。
    # - 进程退出码则是 bash 工具用来判 success 的:非 0 会被判定为"命令失败",
    #   导致客户端把"仍在运行"误显示为"失败"。
    # 这里固定返回 0(进程层面始终成功),仅把状态放在 JSON 的 exit_code 字段里,
    # 从而既不影响 agent 逻辑,又避免运行中被标记为失败。
    payload = {"exit_code": exit_code, "phase": phase, "message": message, **extra}
    print("=== RESULT_FOR_AGENT ===", flush=True)
    print(json.dumps(payload, ensure_ascii=False), flush=True)
    return 0


def read_total_elapsed(session_dir: Path) -> int:
    """从 start_time.txt 计算自最初任务起的总秒数。失败返回 -1。"""
    start_file = session_dir / START_TIME_FILENAME
    if not start_file.exists():
        return -1
    try:
        start_epoch = int(start_file.read_text(encoding="utf-8").strip())
        return int(time.time()) - start_epoch
    except Exception:
        return -1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-id", required=True, help="本次深度研究作业 UUID")
    args = parser.parse_args()

    try:
        state = load_state(args.session_id)
        session_id = state["DR_SESSION_ID"]
        session_dir = Path(state["DR_SESSION_DIR"])
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
        return emit(
            EXIT_NO_STATUS,
            phase="no_session",
            message=f"无法恢复指定深度研究会话: {e}",
            diagnosis="必须传入 session_state.py init 创建的准确会话 ID。",
        )

    total_elapsed_s = read_total_elapsed(session_dir)

    status_file = session_dir / STATUS_FILENAME
    if not status_file.exists():
        return emit(
            EXIT_NO_STATUS,
            phase="no_status_file",
            message=f"找不到 {status_file}",
            diagnosis=(
                "wait 脚本可能尚未启动或被强杀。可读 generate.log 排查;"
                "若需要继续任务可重新启动 wait 脚本(start_time.txt 会保留)。"
            ),
            session_id=session_id,
            session_dir=str(session_dir),
            total_elapsed_s=total_elapsed_s,
        )

    try:
        with open(status_file, encoding="utf-8") as f:
            status = json.load(f)
    except json.JSONDecodeError as e:
        return emit(
            EXIT_NO_STATUS,
            phase="status_corrupted",
            message=f"status.json 解析失败: {e}",
            diagnosis="文件可能在写入中途被读取,稍候 1-2 秒后重试。",
            session_id=session_id,
            total_elapsed_s=total_elapsed_s,
        )

    phase = status.get("phase", "unknown")
    is_terminal = bool(status.get("is_terminal", False))
    message = status.get("message", "")

    # status.json 里由 wait 脚本写入的 exit_code 会与下方 emit() 的位置参数
    # exit_code 冲突(导致 "got multiple values for argument 'exit_code'")。
    # 这里在构造 extra 时排除掉,统一覆盖所有终态 phase(terminated/completed/cloud_failed 等)。
    extra = {k: v for k, v in status.items()
             if k not in {"phase", "is_terminal", "message", "exit_code"}}
    extra["session_id"] = session_id
    extra["total_elapsed_s"] = total_elapsed_s  # 总耗时附在返回里供 agent 判断超时

    if is_terminal:
        return emit(EXIT_TERMINAL, phase=phase, message=message, is_terminal=True, **extra)
    else:
        return emit(EXIT_RUNNING, phase=phase, message=message, is_terminal=False, **extra)


if __name__ == "__main__":
    sys.exit(main())
