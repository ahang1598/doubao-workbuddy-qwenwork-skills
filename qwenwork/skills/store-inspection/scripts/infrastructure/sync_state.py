"""sync_state.json 读写。

记录上一次轮询同步的时间戳，下一次从该时间点继续增量扫描。
文件路径默认与 config.json 同目录，文件名 ``sync_state.json``。

字段::

    {
      "last_sync_time": "2026-04-24T10:00:00+08:00"
    }

容错：文件损坏或丢失时返回"今日 0 点"作为兜底起点（详见需求文档 §5）。
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Optional

from scripts.infrastructure.config import _resolve_config_path

logger = logging.getLogger(__name__)


SYNC_STATE_FILENAME = "sync_state.json"
DEFAULT_TZ = timezone(timedelta(hours=8))  # 北京时间


def _resolve_sync_state_path(path: Optional[Path] = None) -> Path:
    if path is not None:
        return Path(path).expanduser().resolve()
    env = os.environ.get("STORE_TASK_DISPATCHER_SYNC_STATE")
    if env:
        return Path(env).expanduser().resolve()
    cfg_path = _resolve_config_path()
    return cfg_path.parent / SYNC_STATE_FILENAME


def _today_start(now: Optional[datetime] = None) -> datetime:
    """北京时间今日 0 点。"""
    now = now or datetime.now(DEFAULT_TZ)
    if now.tzinfo is None:
        now = now.replace(tzinfo=DEFAULT_TZ)
    return datetime.combine(now.date(), time.min, tzinfo=DEFAULT_TZ)


def load_last_sync_time(
    path: Optional[Path] = None, *, fallback_now: Optional[datetime] = None
) -> datetime:
    """读取上一次同步时间。

    Returns:
        ``datetime`` 对象（带时区）。文件不存在或损坏时返回"今日 0 点"。
    """
    p = _resolve_sync_state_path(path)
    if not p.exists():
        return _today_start(fallback_now)
    try:
        text = p.read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.warning("读取 sync_state.json 失败: %s, 使用今日 0 点兜底", exc)
        return _today_start(fallback_now)
    if not text:
        return _today_start(fallback_now)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning(
            "sync_state.json JSON 损坏: %s, 使用今日 0 点兜底", exc.msg
        )
        return _today_start(fallback_now)
    raw = data.get("last_sync_time") if isinstance(data, dict) else None
    if not raw:
        return _today_start(fallback_now)
    try:
        return _parse_iso(raw)
    except ValueError:
        logger.warning(
            "sync_state.json 中 last_sync_time 解析失败 %r, 使用今日 0 点兜底",
            raw,
        )
        return _today_start(fallback_now)


def save_last_sync_time(
    ts: datetime, path: Optional[Path] = None
) -> Path:
    """保存上一次同步时间，返回文件路径。"""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=DEFAULT_TZ)
    p = _resolve_sync_state_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {"last_sync_time": ts.isoformat()}
    p.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return p


def reset(path: Optional[Path] = None) -> None:
    p = _resolve_sync_state_path(path)
    if p.exists():
        p.unlink()


def _parse_iso(text: str) -> datetime:
    """兼容多种 ISO8601 写法，确保返回带时区的 datetime。"""
    text = text.strip()
    # Python 3.11+ 的 fromisoformat 已支持 'Z' 与多种偏移；3.9/3.10 需手动处理 Z
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=DEFAULT_TZ)
    return dt


__all__ = [
    "DEFAULT_TZ",
    "SYNC_STATE_FILENAME",
    "load_last_sync_time",
    "save_last_sync_time",
    "reset",
]
