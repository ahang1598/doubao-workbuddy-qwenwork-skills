#!/usr/bin/env python3
"""Create and restore isolated PDF jobs across independent exec shells.

There is deliberately no global "current job" pointer.  Every caller must
carry the UUID returned by ``init`` and provide it again to ``load`` or
``make.sh run --session-id``.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import tempfile
import uuid
from pathlib import Path


def _state_root() -> Path:
    override = os.getenv("XIAOYI_PDF_SESSION_ROOT", "").strip()
    return Path(override).expanduser() if override else Path(tempfile.gettempdir()) / "xiaoyi_pdf"


def _normalise_session_id(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError) as exc:
        raise ValueError("PDF 任务 ID 必须是有效 UUID") from exc


def _state_file(session_id: str) -> Path:
    canonical_id = _normalise_session_id(session_id)
    return _state_root() / canonical_id / "session.json"


def _write_json_atomic(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def init_state() -> dict[str, str]:
    session_id = str(uuid.uuid4())
    session_dir = _state_root() / session_id
    session_dir.mkdir(parents=True, exist_ok=False)
    state = {
        "PDF_JOB_ID": session_id,
        "PDF_SESSION_DIR": str(session_dir.resolve()),
        "PDF_CONTENT_PATH": str((session_dir / "content.json").resolve()),
        "PDF_DELIVERY_DIR": str(Path.cwd().resolve()),
    }
    _write_json_atomic(_state_file(session_id), state)
    return state


def load_state(session_id: str) -> dict[str, str]:
    canonical_id = _normalise_session_id(session_id)
    state_file = _state_file(canonical_id)
    if not state_file.is_file():
        raise FileNotFoundError(
            f"PDF 任务状态不存在：{canonical_id}；请使用正确的任务 ID 初始化或恢复"
        )

    state = json.loads(state_file.read_text(encoding="utf-8"))
    required = ("PDF_JOB_ID", "PDF_SESSION_DIR", "PDF_CONTENT_PATH", "PDF_DELIVERY_DIR")
    if any(not isinstance(state.get(key), str) or not state[key].strip() for key in required):
        raise ValueError("PDF 任务状态不完整，请重新初始化")
    if state["PDF_JOB_ID"] != canonical_id:
        raise ValueError("PDF 任务状态与请求的任务 ID 不匹配，拒绝恢复")

    expected_dir = (_state_root() / canonical_id).resolve()
    if Path(state["PDF_SESSION_DIR"]).resolve() != expected_dir:
        raise ValueError("PDF 任务目录不合法，拒绝恢复")
    if Path(state["PDF_CONTENT_PATH"]).resolve() != expected_dir / "content.json":
        raise ValueError("PDF 内容路径不合法，拒绝恢复")
    return {key: state[key] for key in required}


def print_shell(state: dict[str, str]) -> None:
    for key, value in state.items():
        print(f"export {key}={shlex.quote(value)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("init", "load"))
    parser.add_argument("--session-id", help="恢复任务时必须提供的 UUID")
    args = parser.parse_args()

    if args.command == "init":
        if args.session_id:
            parser.error("init 会创建新任务，不能指定 --session-id")
        state = init_state()
    else:
        if not args.session_id:
            parser.error("load 必须指定 --session-id，禁止恢复不明确的任务")
        state = load_state(args.session_id)
    print_shell(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
