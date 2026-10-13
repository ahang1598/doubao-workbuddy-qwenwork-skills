"""用户自定义 HTML 报告模板的持久化管理。

存储位置：与 config.json 同级目录（~/.store-inspection/），
不在技能文件内，防止技能版本更新时被覆盖丢失。

文件命名：
- 单店模板：custom_report_template_single.html
- 多店模板：custom_report_template_multi.html

每种类型（single / multi）最多持久化一份。
用户提供新模板时，若已有持久化模板，需返回旧模板内容供确认覆盖。

模板优先级（从高到低）：
1. 用户本次会话通过 --template 显式传入的 HTML 文件
2. 持久化目录中的用户自定义模板
3. 技能内置默认模板（single_store_template.html / report_template.html）

关于单店 vs 多店报告的判定规则（严格遵守）：
- 单店报告：用户明确指定了**一家且仅一家**门店生成报告时使用。
  例如："为西溪1店生成报告"、"看看朝阳店的情况"。
- 多店报告：涉及多家门店、筛选条件可能命中多家、或未指定具体门店，均使用多店报告：
  · "为 A 门店、B 门店生成报告"（多家门店 = 多店报告）
  · "为所有杭州的门店生成报告"（筛选条件 = 多店报告）
  · "生成今天巡店任务的报告"（未指定具体门店 = 多店报告）
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# 持久化目录：与 config.json 同级
_STORE_DIR_ENV = "STORE_TASK_DISPATCHER_CONFIG"
_AGENT_WORK_ROOT_ENV = "AGENT_WORK_ROOT"

_SINGLE_TEMPLATE_FILENAME = "custom_report_template_single.html"
_MULTI_TEMPLATE_FILENAME = "custom_report_template_multi.html"


def _resolve_storage_dir() -> Path:
    """解析模板持久化目录（与 config.json 同目录）。

    优先级：
    1. $STORE_TASK_DISPATCHER_CONFIG 所在目录
    2. $AGENT_WORK_ROOT/workspace/store-inspection/
    3. ~/.store-inspection/
    """
    env_config = os.environ.get(_STORE_DIR_ENV)
    if env_config:
        return Path(env_config).expanduser().resolve().parent

    agent_root = os.environ.get(_AGENT_WORK_ROOT_ENV)
    if agent_root:
        return (Path(agent_root) / "workspace" / "store-inspection").resolve()

    return Path("~/.store-inspection").expanduser().resolve()


def _template_path(report_type: str) -> Path:
    """获取指定类型模板的持久化文件路径。

    Args:
        report_type: "single" 或 "multi"。
    """
    filename = (
        _SINGLE_TEMPLATE_FILENAME if report_type == "single"
        else _MULTI_TEMPLATE_FILENAME
    )
    return _resolve_storage_dir() / filename


def has_custom_template(report_type: str) -> bool:
    """检查是否已有持久化的用户自定义模板。

    Args:
        report_type: "single" 或 "multi"。
    """
    return _template_path(report_type).exists()


def read_custom_template(report_type: str) -> Optional[str]:
    """读取持久化的用户自定义模板内容。

    Args:
        report_type: "single" 或 "multi"。

    Returns:
        模板 HTML 字符串，不存在时返回 None。
    """
    path = _template_path(report_type)
    if not path.exists():
        return None
    try:
        content = path.read_text(encoding="utf-8")
        logger.debug("读取用户自定义模板: %s", path)
        return content
    except OSError as exc:
        logger.warning("读取自定义模板失败 [%s]: %s", path, exc)
        return None


def save_custom_template(report_type: str, html_content: str) -> Path:
    """持久化用户自定义模板（覆盖写入）。

    Args:
        report_type: "single" 或 "multi"。
        html_content: 完整的 HTML 模板内容。

    Returns:
        持久化文件的绝对路径。
    """
    path = _template_path(report_type)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_content, encoding="utf-8")
    logger.info("用户自定义模板已持久化: %s", path)
    return path


def check_and_confirm_overwrite(report_type: str) -> Tuple[bool, Optional[str]]:
    """检查是否需要覆盖确认。

    Returns:
        (needs_confirm, existing_content):
        - needs_confirm=True 时，existing_content 为旧模板内容，
          调用方应展示给用户确认后再调用 save_custom_template 覆盖。
        - needs_confirm=False 时，可直接保存。
    """
    if not has_custom_template(report_type):
        return False, None
    existing = read_custom_template(report_type)
    return True, existing


def get_custom_template_path(report_type: str) -> Optional[Path]:
    """返回持久化模板文件路径（如果存在），否则 None。"""
    path = _template_path(report_type)
    return path if path.exists() else None


__all__ = [
    "has_custom_template",
    "read_custom_template",
    "save_custom_template",
    "check_and_confirm_overwrite",
    "get_custom_template_path",
]
