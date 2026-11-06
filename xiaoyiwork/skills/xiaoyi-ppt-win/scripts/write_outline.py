#!/usr/bin/env python3
"""
write_outline.py - 大纲写入脚本（验证 + 写入）

模型不再直接使用 Write 工具写入 outline_pre.md，而是通过本脚本完成：
  1. 从 stdin 读取大纲内容
  2. 验证格式合规性（不自动清洗，仅诊断）
  3. 合规则写入目标文件，不合规则拒绝写入并给出错误提示

用法：
    cat << 'EOF' | python write_outline.py "$PPT_SESSION_DIR/outline_pre.md"
    <style>CreamInk</style>

    ---

    # 标题
    ...
    EOF

退出码：
    0 - 验证通过，文件已写入
    1 - 验证失败，文件未写入（需模型自行修正后重试）
"""

import sys
import re
import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger("write_outline")

VALID_STYLES = {"CreamInk", "PlatinumExecutive", "WarmPaper"}
IMAGE_QUERY_TAGS = [("<image_gen_queries>", "</image_gen_queries>"),
                    ("<image_search_queries>", "</image_search_queries>"),
                    ("<image_user_provided>", "</image_user_provided>")]


def _setup_logger(log_path: Path) -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    for old_handler in logger.handlers[:]:
        old_handler.close()
        logger.removeHandler(old_handler)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(handler)


def _log_and_print(level: int, msg: str, *args) -> None:
    """同时写入日志和 stdout。"""
    formatted = msg % args if args else msg
    try:
        print(formatted)
    except UnicodeEncodeError:
        # A plain Windows console can still use GBK even when the desktop
        # runtime normally injects UTF-8.  Logging must not turn a successful
        # atomic write into a failed command merely because it contains emoji.
        encoding = sys.stdout.encoding or "utf-8"
        print(formatted.encode(encoding, errors="replace").decode(encoding))
    logger.log(level, msg, *args)


def write_outline(content: str, output_path: str) -> bool:
    """验证并写入大纲。不自动清洗，仅诊断。返回 True 表示成功写入，False 表示失败。"""
    text = content.strip()

    if not text:
        _log_and_print(logging.ERROR, "❌ 大纲内容为空，未写入文件")
        return False

    # ---- 诊断：检测 JSON 格式（不清洗，仅报错） ----
    if text.startswith('[') and text.endswith(']'):
        try:
            json.loads(text)
            _log_and_print(logging.ERROR, "❌ 大纲格式错误：检测到 JSON 数组格式，应为纯 Markdown 文本")
            _log_and_print(logging.ERROR, "❌ 文件未写入，请重新生成纯 Markdown 格式的大纲")
            return False
        except json.JSONDecodeError:
            pass

    if text.startswith('{') and text.endswith('}'):
        try:
            json.loads(text)
            _log_and_print(logging.ERROR, "❌ 大纲格式错误：检测到 JSON 对象格式，应为纯 Markdown 文本")
            _log_and_print(logging.ERROR, "❌ 文件未写入，请重新生成纯 Markdown 格式的大纲")
            return False
        except json.JSONDecodeError:
            pass

    if text.startswith('"') and text.endswith('"'):
        try:
            unquoted = json.loads(text)
            if isinstance(unquoted, str):
                _log_and_print(logging.ERROR, "❌ 大纲格式错误：检测到 JSON 字符串包裹，应为纯 Markdown 文本")
                _log_and_print(logging.ERROR, "❌ 文件未写入，请重新生成纯 Markdown 格式的大纲")
                return False
        except json.JSONDecodeError:
            pass

    # ---- 验证 ----
    if not text.startswith('<style>'):
        _log_and_print(logging.ERROR, "❌ 大纲必须以 <style>xxx</style> 开头，当前开头: '%s'", text[:80])
        _log_and_print(logging.ERROR, "❌ 文件未写入，请重新生成纯 Markdown 格式的大纲")
        return False

    style_match = re.search(r'<style>(.*?)</style>', text)
    if not style_match:
        _log_and_print(logging.ERROR, "❌ <style> 标签格式不正确，缺少 </style>")
        _log_and_print(logging.ERROR, "❌ 文件未写入，请重新生成纯 Markdown 格式的大纲")
        return False

    style_value = style_match.group(1).strip()
    if not style_value:
        _log_and_print(logging.ERROR, "❌ <style> 标签值不能为空")
        _log_and_print(logging.ERROR, "❌ 文件未写入，请重新生成纯 Markdown 格式的大纲")
        return False

    if style_value not in VALID_STYLES:
        _log_and_print(logging.WARNING, "⚠️ 风格值 '%s' 不在已知列表 %s 中", style_value, VALID_STYLES)

    if not re.search(r"(?m)^---\s*$", text):
        _log_and_print(logging.ERROR, "❌ 未检测到独立页面分隔线 '---'，文件未写入")
        return False

    if not re.search(r"(?m)^#{1,3}\s+\S", text):
        _log_and_print(logging.ERROR, "❌ 未检测到任何页面标题（#、## 或 ###），文件未写入")
        return False

    for tag_start, tag_end in IMAGE_QUERY_TAGS:
        if text.count(tag_start) != text.count(tag_end):
            _log_and_print(
                logging.ERROR,
                "❌ %s 标签未闭合（开始 %d 个，结束 %d 个），文件未写入",
                tag_start,
                text.count(tag_start),
                text.count(tag_end),
            )
            return False

    # ---- 原子写入 ----
    # Never truncate a previously valid outline.  A failed or interrupted write
    # leaves the destination untouched until the complete temporary file is
    # fsynced and atomically replaced.
    p = Path(output_path).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=p.parent,
            prefix=f".{p.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(text + "\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, p)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()

    _log_and_print(logging.INFO, "✅ 大纲验证通过并写入 %s（风格: %s）", p, style_value)
    return True


def main():
    if len(sys.argv) != 2:
        print("用法: python write_outline.py <outline_pre.md 路径>", file=sys.stderr)
        print("  从 stdin 读取大纲内容，验证后写入目标文件", file=sys.stderr)
        sys.exit(1)

    output_path = Path(sys.argv[1]).resolve()
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    _setup_logger(output_dir / "write_outline.log")

    content = sys.stdin.read()

    if not write_outline(content, str(output_path)):
        print("❌ 大纲格式验证失败，文件未写入，请修正格式后重新生成大纲")
        sys.exit(1)

    print("大纲写入完成，继续下一步。")
    sys.exit(0)


if __name__ == "__main__":
    main()
