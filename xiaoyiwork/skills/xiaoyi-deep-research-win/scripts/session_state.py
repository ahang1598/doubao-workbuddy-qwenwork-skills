#!/usr/bin/env python3
"""Create and restore isolated deep-research job state across exec shells.

There is deliberately no global "current session" file. Each research job owns
one UUID-named directory under the system temp directory. Callers must provide
that UUID when restoring or operating on a job so concurrent conversations
cannot resume or overwrite one another.
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
    override = os.getenv("XIAOYI_DR_SESSION_ROOT", "").strip()
    return Path(override).expanduser() if override else Path(tempfile.gettempdir()) / "xiaoyi_dr"


def _normalise_session_id(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError) as exc:
        raise ValueError("深度研究会话 ID 必须是有效 UUID") from exc


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
        "DR_SESSION_ID": session_id,
        "DR_SESSION_DIR": str(session_dir.resolve()),
        "DR_DELIVERY_DIR": str(Path.cwd().resolve()),
    }
    _write_json_atomic(_state_file(session_id), state)
    return state


def load_state(session_id: str) -> dict[str, str]:
    canonical_id = _normalise_session_id(session_id)
    state_file = _state_file(canonical_id)
    if not state_file.is_file():
        raise FileNotFoundError(
            f"深度研究会话状态不存在：{canonical_id}；请使用正确的会话 ID 初始化或恢复"
        )

    state = json.loads(state_file.read_text(encoding="utf-8"))
    required = ("DR_SESSION_ID", "DR_SESSION_DIR", "DR_DELIVERY_DIR")
    if any(not isinstance(state.get(key), str) or not state[key].strip() for key in required):
        raise ValueError("深度研究会话状态不完整，请重新执行会话初始化")
    if state["DR_SESSION_ID"] != canonical_id:
        raise ValueError("深度研究会话状态与请求的会话 ID 不匹配，拒绝恢复")

    expected_dir = (_state_root() / canonical_id).resolve()
    if Path(state["DR_SESSION_DIR"]).resolve() != expected_dir:
        raise ValueError("深度研究会话目录不合法，拒绝恢复")
    return {key: state[key] for key in required}


def print_shell(state: dict[str, str]) -> None:
    for key, value in state.items():
        print(f"export {key}={shlex.quote(value)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("init", "load"))
    parser.add_argument(
        "--session-id",
        help="恢复指定深度研究作业时必须提供的 UUID；init 不接受该参数",
    )
    args = parser.parse_args()

    if args.command == "init":
        if args.session_id:
            parser.error("init 会创建新会话，不能指定 --session-id")
        state = init_state()
    else:
        if not args.session_id:
            parser.error("load 必须指定 --session-id，禁止恢复不明确的会话")
        state = load_state(args.session_id)
    print_shell(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
