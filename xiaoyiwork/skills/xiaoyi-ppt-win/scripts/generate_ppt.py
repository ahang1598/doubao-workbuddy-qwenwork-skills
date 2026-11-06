"""
generate_ppt.py - 通过 {SERVICE_URL}/celia-claw/v1/sse-api/skill/execute SSE 接口生成 PPT

桌面形态 SERVICE_URL=np://claw-skill（默认）：经主进程 skill API 代理转发，
businessCredential 鉴权由主进程注入，本进程零业务凭证。

用法：
  python generate_ppt.py <query>
"""

import argparse
import io
import json
import logging
import os
import sys
import tempfile
import threading
import time
import uuid
import zipfile
from pathlib import Path
from posixpath import basename as url_basename
from typing import Optional
from typing import Tuple

import requests
import urllib3

try:  # Package import for tests and reusable callers.
    from .claw_pipe_http import PipeHttpError
    from .config import Config, ppt_session_dir
except ImportError:  # Direct ``python scripts/generate_ppt.py`` execution.
    from claw_pipe_http import PipeHttpError
    from config import Config, ppt_session_dir

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SKILL_EXECUTE_PATH = "/celia-claw/v1/sse-api/skill/execute"
SKILL_ID = "xiaoyi_office"

OFFICE_EXTENSIONS = {
    ".pptx", ".ppt", ".docx", ".doc", ".xlsx", ".xls",
    ".pdf", ".pptm", ".docm", ".xlsm",
}
RESULT_FILE_NAME = "generation_result.json"
DOWNLOAD_ATTEMPTS = 3
MAX_EXTRACTED_PPTX_BYTES = 200 * 1024 * 1024

logger = logging.getLogger("generate_ppt")
logger.addHandler(logging.NullHandler())


def _setup_logger(log_path: Path) -> None:
    """初始化 logger，输出到指定文件。"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    logger.handlers.clear()
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(handler)


# ============================================================
# Event Handlers
# ============================================================

def handle_step_info(data: dict):
    content = data.get("content", "").rstrip("\n")
    if content:
        logger.info("[进度] %s", content)


def handle_data(data: dict) -> str:
    reasoning = data.get("reasoning_content", "")
    if reasoning:
        logger.debug("[思考] %s", reasoning)
    content = data.get("content", "")
    if content:
        logger.debug("[data] %s", content)
    return content


OFFICE_EXTENSIONS = {
    ".pptx", ".ppt", ".docx", ".doc", ".xlsx", ".xls",
    ".pdf", ".pptm", ".docm", ".xlsm",
}


def _write_bytes_atomically(target: Path, content: bytes) -> None:
    """Write a downloaded artifact without exposing a partially written file."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        temp_path = Path(temp_file.name)
        temp_file.write(content)
        temp_file.flush()
        os.fsync(temp_file.fileno())
    try:
        os.replace(temp_path, target)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _download_bytes(url: str, display_name: str) -> bytes:
    """Retry only an idempotent artifact download, never the PPT generation request."""
    last_error: Exception | None = None
    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        try:
            response = requests.get(url, timeout=300, verify=False)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as exc:
            last_error = exc
            if attempt == DOWNLOAD_ATTEMPTS:
                break
            delay = 2 ** (attempt - 1)
            logger.warning("[下载重试] %s，第 %d/%d 次失败：%s；%ds 后重试", display_name, attempt, DOWNLOAD_ATTEMPTS, exc, delay)
            time.sleep(delay)
    raise RuntimeError(f"下载失败（已重试 {DOWNLOAD_ATTEMPTS} 次）：{display_name}") from last_error


def _extract_pptx_from_zip(content: bytes, output_dir: Path, archive_name: str) -> Optional[str]:
    """Safely recover a PPTX when the service returns only an output ZIP."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            candidates = [
                member for member in archive.infolist()
                if not member.is_dir() and Path(member.filename).suffix.lower() == ".pptx"
            ]
            if not candidates:
                logger.error("[下载失败] %s 中没有 PPTX 文件", archive_name)
                return None
            member = max(candidates, key=lambda item: item.file_size)
            if member.file_size > MAX_EXTRACTED_PPTX_BYTES:
                logger.error("[下载失败] %s 中的 PPTX 超过 %d MB 限制", archive_name, MAX_EXTRACTED_PPTX_BYTES // 1024 // 1024)
                return None
            pptx_content = archive.read(member)
    except (OSError, zipfile.BadZipFile) as exc:
        logger.error("[下载失败] 无法读取 %s：%s", archive_name, exc)
        return None

    if not zipfile.is_zipfile(io.BytesIO(pptx_content)):
        logger.error("[下载失败] %s 中的 %s 不是有效 PPTX", archive_name, member.filename)
        return None
    local_path = output_dir / Path(member.filename).name
    try:
        _write_bytes_atomically(local_path, pptx_content)
    except OSError as exc:
        logger.error("[下载失败] 保存 %s 失败：%s", member.filename, exc)
        return None
    abs_path = str(local_path.resolve())
    logger.info("[文件已保存] %s!%s -> %s", archive_name, member.filename, abs_path)
    return abs_path


def handle_generate_doc(
    data: dict,
    output_dir: Path,
    deferred_zip_files: list[tuple[bytes, str]],
) -> Optional[str]:
    doc = data.get("doc", {})
    name = doc.get("name") or doc.get("path", "")
    url = doc.get("url", "")
    if not url:
        return None
    logger.info("[生成文件] %s: %s", name, url)

    # Usually the service returns a direct Office file. Some runs return only
    # output.zip. Keep ZIP bytes as a fallback until the SSE stream finishes:
    # extracting immediately would leave two local PPTX files when the service
    # later sends its normal direct-PPTX artifact.
    suffix = Path(name).suffix.lower() if name else ""
    if suffix and suffix not in OFFICE_EXTENSIONS and suffix != ".zip":
        logger.info("[跳过下载] %s (非Office格式: %s)", name, suffix)
        return None

    try:
        content = _download_bytes(url, name or "output")
        if suffix == ".zip":
            deferred_zip_files.append((content, name or "output.zip"))
            logger.info("[ZIP候选] 已缓存 %s，等待独立 PPTX 结果", name or "output.zip")
            return None
        local_path = output_dir / (Path(name).name or "output")
        _write_bytes_atomically(local_path, content)
        abs_path = str(local_path.resolve())
        logger.info("[文件已保存] %s -> %s", name, abs_path)
        return abs_path
    except Exception as e:
        logger.error("[下载失败] %s: %s", name, e)
        return None


def handle_tool(data: dict):
    tool_name = data.get("tool_name", "")
    if tool_name:
        logger.info("[调用工具] %s", tool_name)


def handle_tool_result(data: dict):
    tool_name = data.get("tool_name", "")
    result = str(data.get("tool_result", ""))
    if len(result) > 200:
        result = result[:200] + "..."
    if tool_name:
        logger.info("[%s 结果] %s", tool_name, result)


def handle_command(data: dict):
    content_str = data.get("content", "")
    try:
        content = json.loads(content_str) if isinstance(content_str, str) else content_str
    except json.JSONDecodeError:
        return
    steps = content.get("payload", {}).get("cardParams", {}).get("taskStepInfo", [])
    running = [s["stepName"] for s in steps if s.get("stepStatus") == "running"]
    if running:
        logger.info("[进行中] %s", ", ".join(running))


def handle_finish(data: dict):
    finish_type = data.get("type", "normal")
    # logger.info("[完成] type=%s", finish_type)


def _heartbeat_worker(stop_event: threading.Event, interval: int = 15) -> None:
    start = time.monotonic()
    tick = 0
    while not stop_event.wait(interval):
        tick += 1
        elapsed = int(time.monotonic() - start)
        logger.info("[等待中] 已耗时 %dm%02ds，云端仍在处理…", elapsed // 60, elapsed % 60)


# ============================================================
# SSE parsing
# ============================================================

def process_event(
    event_data: str,
    response_text: list[str],
    output_dir: Path,
    downloaded_files: list[str],
    deferred_zip_files: list[tuple[bytes, str]],
) -> bool:
    """处理一个 SSE 事件的 data 内容。返回 True 表示收到 finish 应终止。"""
    try:
        data = json.loads(event_data)
    except json.JSONDecodeError:
        logger.warning("无法解析: %s", event_data[:200])
        return False

    event_type = data.get("event", "")

    if event_type == "stepInfo":
        handle_step_info(data)
    elif event_type == "data":
        text = handle_data(data)
        if text:
            response_text.append(text)
    elif event_type == "generateDoc":
        local_path = handle_generate_doc(data, output_dir, deferred_zip_files)
        if local_path:
            downloaded_files.append(local_path)
    elif event_type == "tool":
        handle_tool(data)
    elif event_type == "tool_result":
        handle_tool_result(data)
    elif event_type == "command":
        handle_command(data)
    elif event_type == "heartbeat":
        pass
    elif event_type == "finish":
        handle_finish(data)
        return True

    return False


def resolve_pptx_files(
    downloaded_files: list[str],
    deferred_zip_files: list[tuple[bytes, str]],
    output_dir: Path,
) -> list[Path]:
    """Prefer independently returned PPTX files; use cached ZIP only as fallback."""
    direct_pptx_files = [
        Path(path) for path in downloaded_files
        if Path(path).is_file() and Path(path).suffix.lower() == ".pptx"
    ]
    if direct_pptx_files:
        return direct_pptx_files

    for content, archive_name in reversed(deferred_zip_files):
        fallback_path = _extract_pptx_from_zip(content, output_dir, archive_name)
        if fallback_path:
            return [Path(fallback_path)]
    return []


def _write_generation_result(output_dir: Path, pptx_files: list[Path]) -> Path:
    """Atomically persist the verified local deliverable for later workflow steps."""
    primary_pptx = pptx_files[-1].resolve()
    result = {
        "status": "done",
        "primary_pptx": str(primary_pptx),
        "files": [str(path.resolve()) for path in pptx_files],
    }
    result_path = output_dir / RESULT_FILE_NAME
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output_dir,
        prefix=f".{RESULT_FILE_NAME}.",
        suffix=".tmp",
        delete=False,
    ) as result_file:
        temp_path = Path(result_file.name)
        json.dump(result, result_file, ensure_ascii=False, indent=2)
        result_file.write("\n")
        result_file.flush()
        os.fsync(result_file.fileno())
    try:
        os.replace(temp_path, result_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    return result_path


# ============================================================
# Core: build request + streaming SSE response
# ============================================================

def build_request(
    cfg: Config,
    session_id: str,
    interaction_id: str,
    query: str,
    attachments: list[dict] = None,
) -> dict:
    timestamp = str(int(time.time() * 1000)) # 获取毫秒级时间戳
    sn = f"{session_id}_{interaction_id}_{timestamp}"
    req = {
        "sn": sn,
        "sessionid": sn,
        "interactionid": interaction_id,
        "query": query,
        "from": cfg.request_from,
        "device": cfg.device.to_dict(trace_id=sn),
        "client_context": {"appExtraInfo": {"customAgent": {"name": "acp_ppt_with_outline"}}},
    }

    if attachments:
        req["attachment"] = attachments

    if cfg.personal_uid:
        req["user"] = {"uid": cfg.personal_uid}

    if cfg.request_from:
        req["agentInfo"] = {"agentId": cfg.request_from}

    return req


def get_session_info(file_path: str = None) -> Tuple[str, str]:
    """
    获取 Session ID 和 Interaction ID。
    优先从文件读取，如果读取失败或字段缺失，则使用默认值生成逻辑。

    参数:
        file_path: 配置文件路径，默认为 ~/.openclaw/.xiaoyiruntime

    返回:
        Tuple[str, str]: (session_id, interaction_id)
    """

    # 1. 确定文件路径
    if file_path is None:
        file_path = os.path.expanduser("~/.openclaw/.xiaoyiruntime")

    session_id = ""
    interaction_id = ""

    # 2. 尝试从文件读取
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("TASK_ID="):
                        # 截取等号后面的内容
                        raw_task_id = line.split("=", 1)[1]

                        # 根据 & 符号切分
                        parts = raw_task_id.split("&")

                        # 获取第一部分 (Session ID)
                        if len(parts) > 0:
                            session_id = parts[0]

                        # 获取第二部分 (Interaction ID)
                        if len(parts) > 1:
                            interaction_id = parts[1]
                        break
        except Exception:
            # 读取出错则忽略，走下面的默认逻辑
            pass

    # 3. 处理默认值和回退逻辑

    # 处理 SESSION_ID: 如果为空，生成 UUID
    if not session_id:
        session_id = str(uuid.uuid4())

    # 处理 INTERACTION_ID: 如果为空，默认1
    if not interaction_id:
        interaction_id = "1"

    return session_id, interaction_id


def prompt(cfg: Config, query: str, ppt_session_id: str, attachments: list[dict] = None) -> str:
    """
    发送 prompt 到 skill/execute SSE 接口（经主进程管道代理），返回完整的响应文本。

    Args:
        cfg: 配置
        query: 用户查询文本
        attachments: 可选的附件列表

    Returns:
        完整的响应文本
    """
    session_id, interaction_id = get_session_info()
    output_dir = ppt_session_dir(ppt_session_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    _setup_logger(output_dir / "generate.log")
    req_body = build_request(cfg, session_id, interaction_id, query, attachments)

    headers = {
        "x-skill-id": SKILL_ID,
        "x-hag-trace-id": req_body["sn"],
        # 旧沙箱形态由 skill_post 内部合并 auth_headers()；管道形态业务鉴权主进程注入
        **cfg.auth_headers(),
    }

    response_text = []
    downloaded_files: list[str] = []
    deferred_zip_files: list[tuple[bytes, str]] = []

    logger.info("发送请求 path=%s sn=%s", SKILL_EXECUTE_PATH, req_body["sn"])

    _stop_heartbeat = threading.Event()
    _heartbeat = threading.Thread(
        target=_heartbeat_worker, args=(_stop_heartbeat, 15), daemon=True
    )
    _heartbeat.start()

    try:
        with cfg.skill_post(SKILL_EXECUTE_PATH, req_body, headers=headers, stream=True) as resp:
            if resp.status_code != 200:
                error_body = resp.text
                logger.error("HTTP %d: %s", resp.status_code, error_body)
                raise RuntimeError(f"HTTP {resp.status_code}: {error_body}")

            pending_data = ""
            has_pending = False

            for raw_line in resp.iter_lines(decode_unicode=True):
                if raw_line is None:
                    continue
                line = raw_line.strip()

                if not line:
                    if has_pending and pending_data:
                        if process_event(
                            pending_data,
                            response_text,
                            output_dir,
                            downloaded_files,
                            deferred_zip_files,
                        ):
                            break
                    pending_data = ""
                    has_pending = False
                    continue

                if line.startswith("data:"):
                    data_part = line[5:].strip()
                    if has_pending:
                        pending_data += "\n" + data_part
                    else:
                        pending_data = data_part
                        has_pending = True

            if has_pending and pending_data:
                process_event(
                    pending_data,
                    response_text,
                    output_dir,
                    downloaded_files,
                    deferred_zip_files,
                )

    except (requests.exceptions.RequestException, PipeHttpError) as e:
        logger.error("[ERROR] 请求失败: %s", e)
        raise
    finally:
        _stop_heartbeat.set()
        _heartbeat.join(timeout=1)

    pptx_files = resolve_pptx_files(downloaded_files, deferred_zip_files, output_dir)
    if not pptx_files:
        logger.error("[ERROR] 云端流程结束但未下载到本地 PPTX，拒绝标记完成")
        raise RuntimeError("云端未返回可交付的本地 PPTX 文件")

    result_path = _write_generation_result(output_dir, pptx_files)
    logger.info("[RESULT] %s", result_path)
    logger.info("[DONE] output_dir=%s", output_dir)
    return "".join(response_text)


# ============================================================
# CLI 入口
# ============================================================

def parse_files_to_attachments(files_json: str) -> list[dict]:
    """将 --files JSON 数组转换为 attachment 列表"""
    urls = json.loads(files_json)
    attachments = []
    for url in urls:
        file_name = url_basename(url.split("?")[0]) or "file"
        attachments.append({
            "fileId": str(uuid.uuid4()),
            "fileName": file_name,
            "fileDownloadUrl": url,
        })
    return attachments


def parse_image_urls_to_attachments(image_urls_json_path: str) -> list[dict]:
    """从 --image-urls-file 指定的 JSON 文件中读取图片 URL 列表，转换为 attachment 列表"""
    path = Path(image_urls_json_path)
    if not path.is_file():
        return []
    urls = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(urls, list):
        return []
    attachments = []
    for info in urls:
        if not info or 'url' not in info or 'file_name' not in info:
            continue
        file_name = info['file_name']
        attachments.append({
            "fileId": str(uuid.uuid4()),
            "fileName": file_name,
            "fileDownloadUrl": info['url'],
        })
    return attachments


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="用户查询文本")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--files", default=None, help='附件 URL JSON 数组，如 \'["http://host/a.md"]\'')
    group.add_argument("--outline-file", default=None, metavar="PATH",
                       help="大纲本地文件路径，脚本内部自动上传并获取 URL")
    parser.add_argument("--image-urls-file", default=None, metavar="PATH",
                        help="图片 URL 列表 JSON 文件路径，图片将作为 attachment 传入")
    args = parser.parse_args()

    try:
        cfg = Config.load()
    except ValueError as e:
        logger.error("配置错误: %s", e)
        sys.exit(1)

    attachments = []
    ppt_session_id = os.getenv("PPT_SESSION_ID", "") or str(uuid.uuid4())
    if args.outline_file:
        # outline 位于 <会话目录>/outline.md，其父目录名即会话 id（跨平台，不依赖路径分隔符）
        ppt_session_id = Path(args.outline_file).parent.name
        try:
            from upload_file import upload_file as do_upload
            outline_url = do_upload(cfg, args.outline_file)
            attachments.extend(parse_files_to_attachments(json.dumps([outline_url])))
        except Exception as e:
            logger.error("大纲文件上传失败: %s", e)
            sys.exit(1)
    elif args.files:
        try:
            attachments.extend(parse_files_to_attachments(args.files))
        except (json.JSONDecodeError, TypeError) as e:
            logger.error("--files 参数解析失败: %s", e)
            sys.exit(1)

    if args.image_urls_file:
        try:
            image_attachments = parse_image_urls_to_attachments(args.image_urls_file)
            attachments.extend(image_attachments)
            logger.info("已添加 %d 张图片到 attachment", len(image_attachments))
        except Exception as e:
            logger.error("--image-urls-file 解析失败: %s", e)

    try:
        prompt(cfg, args.query, ppt_session_id, attachments if attachments else None)
    except Exception as e:
        logger.error("[ERROR] %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
