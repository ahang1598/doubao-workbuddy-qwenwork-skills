from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from report_pipeline_common import DEFAULT_OUTPUT_PATH, ValidationError, read_utf8, require


DEFAULT_URL_REGEX = r"https?://[^\s\"']+"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="把完整 Markdown 报告导入为飞书在线文档。")
    parser.add_argument("--file", type=Path, default=DEFAULT_OUTPUT_PATH, help=f"待导入 Markdown 文件，默认: {DEFAULT_OUTPUT_PATH}")
    parser.add_argument("--title", help="导入后的文档标题；默认从 Markdown 首个 H1 提取。")
    parser.add_argument("--folder-token", default="", help="可选的目标云空间文件夹 token；默认导入根目录。")
    parser.add_argument("--as-identity", choices=("user", "bot"), default="user", help="导入身份，默认 user。")
    parser.add_argument("--url-regex", default=DEFAULT_URL_REGEX, help="从命令输出中提取飞书链接的正则。")
    parser.add_argument("--max-polls", type=int, default=6, help="导入返回异步 ticket 时的后续查询次数。")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="异步查询间隔秒数。")
    parser.add_argument("--command-timeout", type=float, default=60.0, help="单次命令超时秒数。")
    parser.add_argument("--total-timeout", type=float, default=180.0, help="导入与查询的总时限秒数。")
    parser.add_argument("--skip-validate", action="store_true", help="此参数不影响上传行为；上传前不执行报告内容校验。")
    parser.add_argument("--dry-run", action="store_true", help="只打印最终命令，不实际执行导入。")
    return parser


def extract_title(markdown_path: Path) -> str:
    for line in read_utf8(markdown_path).splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return markdown_path.stem


def relative_to_cwd(path: Path) -> str:
    resolved = path.resolve()
    cwd = Path.cwd().resolve()
    try:
        return str(resolved.relative_to(cwd))
    except ValueError as exc:
        raise ValidationError(f"导入文件必须位于当前工作目录下，当前为: {resolved}") from exc


def build_import_command(file_arg: str, title: str, folder_token: str, identity: str) -> list[str]:
    command = [
        "lark-cli",
        "drive",
        "+import",
        "--as",
        identity,
        "--file",
        file_arg,
        "--type",
        "docx",
        "--name",
        title,
        "--format",
        "json",
    ]
    if folder_token:
        command.extend(["--folder-token", folder_token])
    return command


def run_command(command: list[str], timeout: float = 60.0) -> tuple[str, str]:
    require(timeout > 0, "上传总时限已到，保留本地报告并停止上传")
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise ValidationError(f"上传命令超过 {timeout:g} 秒，保留本地报告并停止上传") from exc
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    require(result.returncode == 0, f"命令失败，退出码 {result.returncode}")
    return stdout, stderr


def parse_json_blob(text: str) -> Any | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def walk_values(value: Any) -> list[Any]:
    values = [value]
    if isinstance(value, dict):
        for item in value.values():
            values.extend(walk_values(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(walk_values(item))
    return values


def extract_first_url(text: str, data: Any | None, pattern: str) -> str:
    if data is not None:
        for value in walk_values(data):
            if isinstance(value, str):
                match = re.search(pattern, value)
                if match:
                    return match.group(0)
    match = re.search(pattern, text)
    require(match is not None, "导入成功，但未能从输出中解析文档链接")
    return match.group(0)


def extract_ticket(data: Any | None) -> str:
    if data is None:
        return ""
    if isinstance(data, dict):
        candidates = []

        def collect(obj: Any) -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in {"ticket", "import_ticket", "task_ticket"} and isinstance(value, str):
                        candidates.append(value)
                    collect(value)
            elif isinstance(obj, list):
                for item in obj:
                    collect(item)

        collect(data)
        if candidates:
            return candidates[0]
    return ""


def is_ready(data: Any | None) -> bool:
    if not isinstance(data, dict):
        return True
    ready_values: list[bool] = []
    timed_out_values: list[bool] = []

    def collect(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "ready" and isinstance(value, bool):
                    ready_values.append(value)
                elif key == "timed_out" and isinstance(value, bool):
                    timed_out_values.append(value)
                collect(value)
        elif isinstance(obj, list):
            for item in obj:
                collect(item)

    collect(data)
    if any(value is False for value in ready_values):
        return False
    if any(value is True for value in timed_out_values):
        return False
    return True


def poll_import_task(
    ticket: str, max_polls: int, poll_interval: float,
    *, deadline: float | None = None, command_timeout: float = 60.0,
) -> tuple[str, str, Any | None]:
    if deadline is None:
        deadline = time.monotonic() + 180.0
    command = [
        "lark-cli",
        "drive",
        "+task_result",
        "--scenario",
        "import",
        "--ticket",
        ticket,
        "--format",
        "json",
    ]
    stdout = stderr = ""
    data = None
    for index in range(max_polls):
        if index:
            require(deadline - time.monotonic() > poll_interval, "上传总时限已到，保留本地报告并停止查询")
            time.sleep(poll_interval)
        stdout, stderr = run_command(command, timeout=min(command_timeout, deadline - time.monotonic()))
        data = parse_json_blob(stdout)
        if is_ready(data):
            break
    return stdout, stderr, data


def upload(args: argparse.Namespace) -> str:
    require(args.command_timeout > 0 and args.total_timeout > 0, "上传超时秒数必须大于0")
    markdown_path = args.file.resolve()
    require(markdown_path.exists(), f"待导入文件不存在: {markdown_path}")

    title = args.title or extract_title(markdown_path)
    file_arg = relative_to_cwd(markdown_path)
    command = build_import_command(file_arg, title, args.folder_token, args.as_identity)

    print("[upload_report] command:", " ".join(command))
    if args.dry_run:
        return ""

    deadline = time.monotonic() + args.total_timeout
    stdout, stderr = run_command(command, timeout=min(args.command_timeout, args.total_timeout))
    data = parse_json_blob(stdout)
    ticket = extract_ticket(data)
    if ticket and not is_ready(data):
        stdout, stderr, data = poll_import_task(
            ticket, args.max_polls, args.poll_interval,
            deadline=deadline, command_timeout=args.command_timeout,
        )

    return extract_first_url("\n".join(filter(None, [stdout, stderr])), data, args.url_regex)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        url = upload(args)
    except ValidationError as exc:
        print(f"[upload_report] 失败: {exc}", file=sys.stderr)
        return 1

    if url:
        print(f"[upload_report] 文档链接: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
