#!/usr/bin/env python3
"""Deterministically render the agent-task-hub 「通知文案」(richText markdown).

通知文案是自动化通知卡片的正文，样式已实机验证：加粗标签 + 引用块让接手/认领
prompt 独立成段。本脚本是模板唯一事实源——agent 必须把输出原样嵌入 cells，
禁止自由组装（历史上自由发挥曾产出无结构口语正文与硬规则禁用措辞）。

sanitize 也在此收敛（实机验证 2026-08：richText 渲染器在 markdown 解析之后跑
linkify autolink，会把 SKILL.md / run_all.py 这类裸域名形态 token——.md/.py 恰为
国家码顶级域——加超链接；只有行内代码能抑制，转义点无效）：
1. 显式 markdown 链接 [text](url) 折叠为 text；
2. 裸域名/文件名词元与裸 URL 包反引号成行内代码。
任务标题不做 sanitize（接手/认领 prompt 需原标题定位记录），标题含会被 autolink
的 token 时向 stderr 告警。

本脚本只做本地渲染：不调用 dws，不读写表格。

Usage:
    python3 scripts/render-notice.py handoff --title "<任务标题>" --summary "<一句话摘要>"
    python3 scripts/render-notice.py claim   --title "<任务标题>" --summary "<一句话摘要>"

输出 richText cell 值 JSON {"markdown": "..."}，原样嵌入 operations.md 里
<通知文案fieldId> 的 cell 值。--title 必须与交接子记录「任务标题」一致，
接手/认领 prompt 靠它定位记录。
"""

from __future__ import annotations

import argparse
import json
import re
import sys

# 渲染器 linkify 把「单词字符/连字符/斜杠 + . + 2-6 字母后缀」当裸域名（.md/.py 等恰为
# 国家码 TLD）。lookbehind/lookahead 防止从路径/URL 中间截出子 token。
_BARE_PATTERN = r"(?<![\w./-])([\w./-]+\.[A-Za-z]{2,6})(?![A-Za-z])"
_BARE_DOMAIN = re.compile(_BARE_PATTERN)
_RAW_URL = re.compile(r"https?://[^\s`。，；！？）」]+")
# 单遍从左到右：URL 先整体消费，避免 URL 内域名被二次命中
_COMBINED = re.compile(r"(https?://[^\s`。，；！？）」]+)|" + _BARE_PATTERN)
_CODE_SPAN = re.compile(r"(`[^`]+`)")
_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def sanitize_text(text: str) -> str:
    """中和通知文案里会被渲染器 autolink 的 token；已在反引号内的内容原样保留。"""

    def wrap(m: re.Match) -> str:
        return f"`{m.group(1) or m.group(2)}`"

    def fix(segment: str) -> str:
        segment = _MD_LINK.sub(r"\1", segment)
        return _COMBINED.sub(wrap, segment)

    parts = _CODE_SPAN.split(text)
    parts[0::2] = [fix(s) for s in parts[0::2]]
    return "".join(parts)


def render_notice(kind: str, title: str, summary: str) -> dict:
    title = title.strip()
    summary = sanitize_text(summary.strip())
    if not title:
        raise SystemExit("title must not be empty")
    if not summary:
        raise SystemExit("summary must not be empty")

    if _BARE_DOMAIN.search(title) or _RAW_URL.search(title):
        # 标题原样进接手/认领 prompt，不能 sanitize（否则定位记录失配），只告警。
        print(
            "warn: title contains filename/domain-like token that the renderer will autolink; "
            "avoid bare .md/.py-style filenames in title",
            file=sys.stderr,
        )

    if kind == "handoff":
        desc_label, action, verb = "交接说明", "接手方式", "接手"
    else:
        desc_label, action, verb = "待认领", "认领方式", "认领"
    markdown = (
        f"**任务**：{title}\n\n"
        f"**{desc_label}**：{summary}\n\n"
        f"**{action}**：新开会话，对 agent 说：\n"
        f"> 使用 agent-task-hub {verb}「{title}」"
    )
    return {"markdown": markdown}


def main() -> None:
    parser = argparse.ArgumentParser(description="Render 通知文案 richText markdown deterministically")
    sub = parser.add_subparsers(dest="kind", required=True)

    handoff = sub.add_parser("handoff", help="Render designated-assignee handoff notice")
    handoff.add_argument("--title", required=True)
    handoff.add_argument("--summary", required=True)

    claim = sub.add_parser("claim", help="Render pending-claim group notice")
    claim.add_argument("--title", required=True)
    claim.add_argument("--summary", required=True)

    args = parser.parse_args()
    print(json.dumps(render_notice(args.kind, args.title, args.summary), ensure_ascii=False))


if __name__ == "__main__":
    main()
