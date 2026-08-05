"""
OAuth 2.1 授权入口脚本（作为子进程运行）

触发模式（正常调用）：
    python3 scripts/authorize.py --mode AK [--timeout 300]
    python3 scripts/authorize.py --scope "read:order" [--client-id xxx] [--timeout 300]

服务进程模式（内部自调用，不直接使用）：
    python3 scripts/authorize.py --server-only --mode AK [--timeout 300]
    python3 scripts/authorize.py --server-only --client-id xxx [--timeout 300]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import secrets
import signal
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlencode

# Windows 默认 GBK 编码，强制 stdout/stderr 使用 UTF-8 避免中文输出报错
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# 确保 scripts/ 目录在 sys.path 中
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _const import (
    CLIENT_ID,
    AUTHORIZE_ENDPOINT,
    AUTHORIZATION_TIMEOUT,
    CALLBACK_HOST,
    ENV_FILE,
    ENV_CLIENT_ID,
    AUTH_MODE_OAUTH,
    AUTH_MODE_AK,
    DATA_DIR,
    LOG_FILE,
)
from pkce import generate_pair
from callback_server import CallbackServer
from token_manager import load_token, has_scope
from secure_store import load_metadata
from _output import print_browser_use_action

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    """仅在作为独立脚本运行时初始化日志（避免作为模块导入时覆盖调用方的日志配置）。"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8")],
        force=True,
    )


def _setup_server_signals() -> None:
    """注册退出信号处理，确保 finally 块正常执行。仅在非 Windows 上注册 SIGTERM。
    Windows 的 taskkill /F 走 TerminateProcess，无法被 Python 信号机制捕获。"""
    def _handle(signum, frame):
        raise SystemExit(0)

    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, _handle)
        logger.debug("已注册 SIGTERM 处理器（Windows 不支持，跳过）")


def _open_browser(url: str, timeout: int = AUTHORIZATION_TIMEOUT) -> None:
    """输出 browser_use 提示，告知 Agent 使用 browser_use 工具打开授权链接。"""
    print_browser_use_action(
        url,
        (
            f"授权链接已生成！请使用 browser_use 工具打开以下链接完成授权：\n\n{url}\n\n"
            f"打开后请立即执行 list_tabs 查找真实授权页 targetId，再用该 targetId 执行 focus_tab 置顶授权页。\n\n"
            f"browser_use 完成后请调用 `configure --status` 确认授权结果。"
        ),
    )


def _open_browser_AK(url: str) -> None:
    """输出 browser_use 提示：打开 AK 授权页，登录后从 localStorage 读取 userAk 并 configure。"""
    markdown = (
        f"授权链接已生成！请使用 browser_use 工具打开以下链接，打开后立即将授权页置顶，完成授权后关闭浏览器窗口：\n\n{url}\n\n"
        "用户登录成功后按照如下顺序执行：\n\n"
        "1. 使用 **browser_use** 打开链接后，**立即**执行 `list_tabs`，从 URL 含 `login.1688.com` 或 `air.1688.com` 的授权页条目中获取真实 `targetId`，再执行 `focus_tab` 置顶授权页（见 `after_open` 字段）\n\n"
        "2. 使用 **browser_use** 在当前页面上下文中读取 **localStorage** 中键 **`userAk`** 的值 （与 `localStorage.getItem('userAk')` 等价）\n\n"
        "3. 如果 userAk 的值为空，则在当前页稍等后再用 browser_use 读一次（最多重复执行两次）\n\n"
        "4. 如果 userAk 的值不为空，**必须**再次执行 `list_tabs` 定位授权页真实 `targetId`，再执行 `close_tab` 关闭授权页；关闭失败时重试一次，仍失败则明确告知用户授权页未关闭\n\n"
        "5. 使用技能**set_ak**，指令格式为 `python3 cli.py set_ak YOUR_NEW_AK`，将 `YOUR_NEW_AK` 替换为步骤 2 读到的userAk的值（注意勿将 AK 泄露到无关日志或聊天中）\n\n"
        "6. 执行 `python3 cli.py configure --status` 确认 AK 是否已就绪。\n\n"
    )
    print_browser_use_action(
        url,
        markdown,
        local_storage_key="userAk",
        read_local_storage_via="browser_use",
        configure_hint="python3 cli.py configure <AK>",
    )


def output_json(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False), flush=True)


# ── PID 文件管理：跟踪后台服务进程 ──
_PID_FILE = DATA_DIR / ".authorize.pid"


def _kill_stale_process() -> None:
    """检测并终止上一次遗留的后台回调服务进程"""
    if not _PID_FILE.exists():
        return
    try:
        old_pid = int(_PID_FILE.read_text().strip())
        if old_pid == os.getpid():
            return
        if sys.platform == "win32":
            logger.debug("Windows: 使用 taskkill 终止遗留进程 PID=%d", old_pid)
            subprocess.run(["taskkill", "/PID", str(old_pid), "/F"],
                           capture_output=True, check=False)
        else:
            logger.debug("Unix: 使用 SIGTERM 终止遗留进程 PID=%d", old_pid)
            os.kill(old_pid, signal.SIGTERM)
        logger.info("已终止上一次遗留的回调服务进程 (PID=%d)", old_pid)
    except (ValueError, ProcessLookupError, PermissionError):
        pass
    finally:
        _PID_FILE.unlink(missing_ok=True)


def _write_pid() -> None:
    """写入当前进程 PID（由服务进程调用）"""
    _PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PID_FILE.write_text(str(os.getpid()))


def _cleanup_pid() -> None:
    """只在 PID 文件记录的仍是当前进程时才删除，避免误删新进程的 PID 文件。"""
    try:
        if _PID_FILE.exists() and _PID_FILE.read_text().strip() == str(os.getpid()):
            _PID_FILE.unlink(missing_ok=True)
    except OSError:
        pass


# ═══════════════════════════════════════════════════════
# 服务进程模式（--server-only）
# 由触发模式以守护子进程启动，独立存活直到回调完成或超时
# ═══════════════════════════════════════════════════════

def _run_server_only_ak(timeout: int) -> int:
    """AK 服务进程：写 PID，启动回调服务器，向父进程报告端口，阻塞等待回调。"""
    # SIGTERM → SystemExit，确保 finally 块正常执行（PID 清理、server.stop）
    _setup_server_signals()

    _write_pid()

    state = secrets.token_urlsafe(32)
    server = CallbackServer(
        client_id="", redirect_uri="", code_verifier="",
        state=state, mode=AUTH_MODE_AK,
    )
    server.start()
    server.redirect_uri = f"http://{CALLBACK_HOST}:{server.port}/callback"

    # 向父进程（通过 stdout pipe）报告端口和 state
    try:
        sys.stdout.write(json.dumps({"port": server.port, "state": state}, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    except Exception:
        pass
    # 重定向到 /dev/null：安全隔断父进程管道，避免关闭 fd 导致后续写入异常
    try:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        pass

    # 独立阻塞等待，父进程已退出
    try:
        server.wait(timeout=timeout)
    finally:
        server.stop()
        _cleanup_pid()
    return 0


def _run_server_only_oauth(client_id: str, env_file: Path, timeout: int) -> int:
    """OAuth 服务进程：写 PID，启动回调服务器，向父进程报告端口和 PKCE 参数，阻塞等待回调。"""
    _setup_server_signals()

    _write_pid()

    code_verifier, code_challenge = generate_pair()
    state = secrets.token_urlsafe(32)

    server = CallbackServer(
        client_id=client_id,
        redirect_uri="",
        code_verifier=code_verifier,
        state=state,
        env_file=env_file,
    )
    server.start()
    server.redirect_uri = f"http://{CALLBACK_HOST}:{server.port}/callback"

    info = {
        "port": server.port,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    try:
        sys.stdout.write(json.dumps(info, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    except Exception:
        pass
    try:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        pass

    try:
        server.wait(timeout=timeout)
    finally:
        server.stop()
        _cleanup_pid()
    return 0


# ═══════════════════════════════════════════════════════
# 触发模式：启动后台回调服务器，输出 browser_use 提示后立即退出
# 服务器在后台独立运行，接收授权页回调后自动保存 AK
# ═══════════════════════════════════════════════════════

def _spawn_server(mode: str, extra_args: list[str], timeout: int) -> dict:
    """
    以独立守护进程启动 --server-only 子进程。
    子进程通过 stdout 第一行 JSON 报告端口和密钥参数，之后父进程关闭管道。
    返回服务器信息 dict（port, state, 以及 OAuth 模式下的 code_challenge 等）。
    """
    script = str(Path(__file__).resolve())
    cmd = [
        sys.executable, script,
        "--server-only",
        "--mode", mode,
        "--timeout", str(timeout),
    ] + extra_args

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    stderr_sink = open(LOG_FILE, "a", encoding="utf-8")

    kwargs: dict = {
        "stdout": subprocess.PIPE,
        "stderr": stderr_sink,
        "text": True,
        "encoding": "utf-8",
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True

    proc = subprocess.Popen(cmd, **kwargs)
    stderr_sink.close()
    line = proc.stdout.readline().strip()
    proc.stdout.close()

    try:
        return json.loads(line)
    except (json.JSONDecodeError, ValueError):
        proc.terminate()
        raise RuntimeError(f"回调服务器启动失败（输出: {line!r}）")


def run_ak_mode(timeout: int, env_file: Path) -> int:
    try:
        _kill_stale_process()
        params = {
            "response_type": "code",
            "mode": AUTH_MODE_AK,
        }
        _open_browser_AK(f"{AUTHORIZE_ENDPOINT}?{urlencode(params)}")
        return 0
    except Exception as e:
        output_json({"success": False, "error_code": "AK_MODE_ERROR",
                     "markdown": f"获取 AK 失败：{e}"})
        return 1


def run_oauth_mode(requested_scope: str, client_id: str, timeout: int, env_file: Path) -> int:
    # 检查已有有效 Token
    token = load_token(env_file)
    if token and not token["expired"] and has_scope(token["scope"], requested_scope):
        output_json({"success": True, "scope": token["scope"],
                     "expires_in": token["expires_in"],
                     "message": "已有有效授权，无需重新授权"})
        return 0

    # 增量授权：合并已有 scope
    if token and token["scope"]:
        existing = set(token["scope"].split())
        merged_scope = " ".join(sorted(existing | set(requested_scope.split())))
    else:
        merged_scope = requested_scope

    try:
        _kill_stale_process()
        params = {
            "response_type": "code",
            "client_id": client_id,
            "scope": merged_scope,
        }
        _open_browser(f"{AUTHORIZE_ENDPOINT}?{urlencode(params)}", timeout)
        return 0
    except Exception as e:
        output_json({"success": False, "error_code": "OAUTH_MODE_ERROR",
                     "markdown": f"发起授权失败：{e}"})
        return 1


def main() -> int:
    _setup_logging()
    parser = argparse.ArgumentParser(description="1688 OAuth 2.1 授权")
    parser.add_argument("--scope", default=None)
    parser.add_argument("--client-id", default=None)
    parser.add_argument("--mode", default=AUTH_MODE_OAUTH, choices=[AUTH_MODE_OAUTH, AUTH_MODE_AK])
    parser.add_argument("--timeout", type=int, default=AUTHORIZATION_TIMEOUT)
    parser.add_argument("--env-file", type=Path, default=ENV_FILE)
    parser.add_argument("--server-only", action="store_true",
                        help="内部参数：以后台回调服务进程模式运行，不直接调用")
    args = parser.parse_args()

    env_file: Path = args.env_file
    timeout: int = args.timeout
    mode: str = args.mode

    # ── 服务进程模式（内部调用） ──
    if args.server_only:
        if mode == AUTH_MODE_AK:
            return _run_server_only_ak(timeout)
        client_id = args.client_id or load_metadata(ENV_CLIENT_ID, env_file) or CLIENT_ID
        return _run_server_only_oauth(client_id, env_file, timeout)

    # ── 触发模式 ──
    if mode == AUTH_MODE_AK:
        return run_ak_mode(timeout, env_file)

    requested_scope = (args.scope or "").strip()
    if not requested_scope:
        output_json({"success": False, "error": "MISSING_SCOPE",
                     "message": "必须指定 --scope 参数"})
        return 1

    client_id = args.client_id or load_metadata(ENV_CLIENT_ID, env_file) or CLIENT_ID
    return run_oauth_mode(requested_scope, client_id, timeout, env_file)


if __name__ == "__main__":
    sys.exit(main())
