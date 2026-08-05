#!/usr/bin/env python3
"""AI 标题修改命令 — CLI 入口"""

from __future__ import annotations

COMMAND_NAME = "ai_title_modify"
COMMAND_DESC = "AI 智能优化商品标题（基于商品图片解析）"

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import argparse
import json
import time
from typing import Optional
from _output import make_output, print_output, print_error
from capabilities.ai_title_modify.service import (
    query_offer_info,
    submit_image_parse,
    poll_image_parse_result,
    change_subject,
    calc_title_length,
    TITLE_MAX_LENGTH,
)

# 状态文件：保存解析上下文与 Agent 暂存的 AI 标题，供 --apply 直接复用
STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "..", ".title_state.json")
# 批量状态文件：保存批量场景下每个商品的解析上下文与暂存的 AI 标题
BATCH_STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "..", ".batch_title_state.json")


def _save_state(state: dict) -> None:
    state["saved_at"] = time.time()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


def _load_state() -> Optional[dict]:
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_batch_state(state: dict) -> None:
    state["saved_at"] = time.time()
    with open(BATCH_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


def _load_batch_state() -> Optional[dict]:
    if not os.path.exists(BATCH_STATE_FILE):
        return None
    try:
        with open(BATCH_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _format_context_markdown(offer_id: str, original_title: str, images: list, parse_result: Optional[dict]) -> str:
    """格式化解析上下文 markdown，供 Agent 据此生成优化标题。"""
    lines = [f"## 商品标题优化上下文已就绪\n"]
    lines.append(f"**商品ID**: {offer_id}\n")
    lines.append(f"**原标题**: {original_title or '（无）'}\n")

    if images:
        lines.append(f"**主图（首图）**: {images[0]}\n")

    if parse_result and parse_result.get("success"):
        lines.append("### 图片解析结果\n")
        text_summary = parse_result.get("text_region_summary") or ""
        selling_points = parse_result.get("selling_points_visible") or []
        composition = parse_result.get("composition_summary") or ""
        if text_summary:
            lines.append(f"- **文字区域**：{text_summary}")
        if selling_points:
            lines.append(f"- **可见卖点**：{', '.join(selling_points)}")
        if composition:
            lines.append(f"- **构图摘要**：{composition}")
        lines.append("")
    elif parse_result and not parse_result.get("success"):
        lines.append(f"\n> ⚠️ 图片解析未完成：{parse_result.get('message', '')}\n")
    else:
        lines.append("\n> ⚠️ 商品无主图，跳过图片解析\n")

    lines.append("---")
    lines.append("**Agent 后续动作**：请基于上述图片解析结果与原标题，生成更优秀的商品标题。")
    lines.append("- 若原标题与图片偏差过大，请彻底抛弃原标题，以图片解析内容为准")
    lines.append("- 生成的标题应尽可能写满 30 个字符，但不得包含重复词语")
    lines.append(f"- 生成后调用：`ai_title_modify --offer_id {offer_id} --suggest \"<新标题>\"` 暂存并展示给商家")
    return "\n".join(lines)


def _mode_fetch_context(offer_id: str) -> None:
    """模式 1：拉取商品信息 + 解析主图 + 保存上下文。"""
    # 1. 查询商品基础信息
    offer_info = query_offer_info(offer_id)
    original_title = offer_info["title"]
    images = offer_info["images"]

    # 2. 提交图片解析任务（仅使用首图）
    parse_result: Optional[dict] = None
    if images:
        try:
            task_id = submit_image_parse(images[0])
            parse_result = poll_image_parse_result(task_id)
        except Exception as e:
            parse_result = {"success": False, "message": str(e)}

    # 3. 保存状态
    _save_state({
        "offer_id": offer_id,
        "original_title": original_title,
        "images": images,
        "parse_result": parse_result,
    })

    print_output(make_output(
        success=True,
        markdown=_format_context_markdown(offer_id, original_title, images, parse_result),
        data={
            "offerId": offer_id,
            "originalTitle": original_title,
            "images": images,
            "parseResult": parse_result,
        },
    ))


def _check_title_length(title: str) -> Optional[str]:
    """校验标题长度，超限返回错误提示，否则返回 None。"""
    length = calc_title_length(title)
    if length > TITLE_MAX_LENGTH:
        return f"标题长度超出限制：当前 {length:g} 字符（限制 {TITLE_MAX_LENGTH} 字符），请缩短标题后重试。"
    return None


def _mode_suggest(offer_id: str, ai_title: str) -> None:
    """模式 2：Agent 生成 AI 标题后调用，暂存并展示给商家确认。"""
    err = _check_title_length(ai_title)
    if err:
        print_output(make_output(
            success=False,
            error_code="TITLE_TOO_LONG",
            markdown=f"## 标题长度超限\n\n**商品ID**: {offer_id}\n\n{err}",
            data={"offerId": offer_id, "title": ai_title, "length": calc_title_length(ai_title), "limit": TITLE_MAX_LENGTH},
        ))
        return

    state = _load_state() or {}
    if state.get("offer_id") != offer_id:
        # 状态不一致也允许暂存（agent 可能直接调用），但提示
        state = {"offer_id": offer_id}

    state["ai_title"] = ai_title
    _save_state(state)

    original_title = state.get("original_title") or ""
    md_lines = ["## AI 标题优化建议\n"]
    md_lines.append(f"**商品ID**: {offer_id}\n")
    if original_title:
        md_lines.append(f"**原标题**: {original_title}")
    md_lines.append(f"**AI 推荐标题**: {ai_title}\n")
    md_lines.append("---")
    md_lines.append("请确认下一步操作：")
    md_lines.append(f"1. **直接应用 AI 推荐标题** → `ai_title_modify --offer_id {offer_id} --apply`")
    md_lines.append(f"2. **使用自定义标题** → `ai_title_modify --offer_id {offer_id} --subject \"<您的标题>\"`")

    print_output(make_output(
        success=True,
        markdown="\n".join(md_lines),
        data={"offerId": offer_id, "aiTitle": ai_title, "originalTitle": original_title},
    ))


def _mode_apply(offer_id: str) -> None:
    """模式 3：应用已暂存的 AI 标题。"""
    state = _load_state()
    if not state or state.get("offer_id") != offer_id or not state.get("ai_title"):
        print_output(make_output(
            success=False,
            error_code="NO_AI_TITLE",
            markdown=f"## 未找到 AI 标题\n\n**商品ID**: {offer_id}\n\n请先执行 `ai_title_modify --offer_id {offer_id}` 获取上下文，再生成 AI 标题。",
            data={"offerId": offer_id},
        ))
        return

    ai_title = state["ai_title"]
    result = change_subject(offer_id, ai_title)

    if result["success"]:
        print_output(make_output(
            success=True,
            markdown=f"## 标题修改成功\n\n**商品ID**: {offer_id}\n\n**新标题**: {ai_title}",
            data={"offerId": offer_id, "newTitle": ai_title, "applied": True},
        ))
    else:
        print_output(make_output(
            success=False,
            markdown=f"## 标题修改失败\n\n**商品ID**: {offer_id}\n\nAI 标题：{ai_title}\n\n错误：{result.get('message', '未知错误')}",
            data={"offerId": offer_id, "aiTitle": ai_title},
        ))


def _mode_apply_custom(offer_id: str, subject: str) -> None:
    """模式 4：应用自定义标题。"""
    err = _check_title_length(subject)
    if err:
        print_output(make_output(
            success=False,
            error_code="TITLE_TOO_LONG",
            markdown=f"## 标题长度超限\n\n**商品ID**: {offer_id}\n\n{err}",
            data={"offerId": offer_id, "title": subject, "length": calc_title_length(subject), "limit": TITLE_MAX_LENGTH},
        ))
        return

    result = change_subject(offer_id, subject)
    if result["success"]:
        print_output(make_output(
            success=True,
            markdown=f"## 标题修改成功\n\n**商品ID**: {offer_id}\n\n**新标题**: {subject}",
            data={"offerId": offer_id, "newTitle": subject, "applied": True},
        ))
    else:
        print_output(make_output(
            success=False,
            markdown=f"## 标题修改失败\n\n**商品ID**: {offer_id}\n\n{result.get('message', '未知错误')}",
            data={"offerId": offer_id},
        ))


def _fetch_single_context(offer_id: str) -> dict:
    """拉取单个商品的上下文（商品信息 + 首图解析）。失败不抛，记在 error 字段。"""
    item: dict = {"offer_id": offer_id}
    try:
        offer_info = query_offer_info(offer_id)
        item["original_title"] = offer_info["title"]
        item["images"] = offer_info["images"]
    except Exception as e:
        item["error"] = f"商品信息查询失败：{e}"
        item.setdefault("original_title", "")
        item.setdefault("images", [])
        return item

    parse_result: Optional[dict] = None
    if item["images"]:
        try:
            task_id = submit_image_parse(item["images"][0])
            parse_result = poll_image_parse_result(task_id)
        except Exception as e:
            parse_result = {"success": False, "message": str(e)}
    item["parse_result"] = parse_result
    return item


def _format_batch_context_markdown(items: list) -> str:
    """格式化批量上下文 markdown，供 Agent 依据生成优化标题。"""
    lines = [f"## 批量标题优化上下文已就绪\n"]
    lines.append(f"共 **{len(items)}** 个商品。\n")
    for idx, item in enumerate(items, 1):
        offer_id = item.get("offer_id", "")
        lines.append(f"### {idx}. 商品ID: {offer_id}")
        if item.get("error"):
            lines.append(f"> ⚠️ {item['error']}")
            lines.append("")
            continue
        original_title = item.get("original_title") or "（无）"
        lines.append(f"- **原标题**：{original_title}")
        images = item.get("images") or []
        if images:
            lines.append(f"- **主图（首图）**：{images[0]}")
        parse_result = item.get("parse_result")
        if parse_result and parse_result.get("success"):
            text_summary = parse_result.get("text_region_summary") or ""
            selling_points = parse_result.get("selling_points_visible") or []
            composition = parse_result.get("composition_summary") or ""
            if text_summary:
                lines.append(f"- **文字区域**：{text_summary}")
            if selling_points:
                lines.append(f"- **可见卖点**：{', '.join(selling_points)}")
            if composition:
                lines.append(f"- **构图摘要**：{composition}")
        elif parse_result and not parse_result.get("success"):
            lines.append(f"- ⚠️ 图片解析未完成：{parse_result.get('message', '')}")
        else:
            lines.append("- ⚠️ 商品无主图，跳过图片解析")
        lines.append("")

    lines.append("---")
    lines.append("**Agent 后续动作**：请为每个商品生成优化后的新标题，然后调用以下命令暂存并展示给商家：")
    lines.append("")
    lines.append("```")
    lines.append("python3 cli.py ai_title_modify --batch-suggest '{\"商品ID1\":\"新标题1\",\"商品ID2\":\"新标题2\"}'")
    lines.append("```")
    lines.append("- 若原标题与图片偏差过大，请彻底抛弃原标题，以图片解析内容为准")
    lines.append("- 生成的标题应尽可能写满 30 个字符，但不得包含重复词语")
    lines.append("- 存在查询/解析失败的商品可跳过，不需在 --batch-suggest 中传入")
    return "\n".join(lines)


def _mode_fetch_batch_context(offer_ids: list) -> None:
    """批量模式 1：拉取多个商品上下文 + 主图解析。"""
    # 去重且保持顺序
    seen = set()
    unique_ids: list = []
    for oid in offer_ids:
        if oid and oid not in seen:
            seen.add(oid)
            unique_ids.append(oid)

    items: list = [_fetch_single_context(oid) for oid in unique_ids]

    # 保存批量状态（以 offer_id 为键）
    state = {"items": {item["offer_id"]: item for item in items}}
    _save_batch_state(state)

    print_output(make_output(
        success=True,
        markdown=_format_batch_context_markdown(items),
        data={
            "count": len(items),
            "items": [
                {
                    "offerId": item.get("offer_id"),
                    "originalTitle": item.get("original_title", ""),
                    "images": item.get("images", []),
                    "parseResult": item.get("parse_result"),
                    "error": item.get("error"),
                }
                for item in items
            ],
        },
    ))


def _mode_batch_suggest(suggest_json: str) -> None:
    """批量模式 2：Agent 批量提交 AI 标题（JSON 映射）。"""
    try:
        suggestions = json.loads(suggest_json)
        if not isinstance(suggestions, dict) or not suggestions:
            raise ValueError("必须为非空 JSON 对象")
    except Exception as e:
        print_output(make_output(
            success=False,
            error_code="INVALID_PARAM",
            markdown=f"## --batch-suggest 参数解析失败\n\n错误：{e}\n\n期望格式：`{{\"商品ID1\":\"新标题1\",\"商品ID2\":\"新标题2\"}}`",
        ))
        return

    state = _load_batch_state() or {"items": {}}
    items: dict = state.get("items") or {}
    md_lines = ["## 批量 AI 标题优化建议\n"]
    md_lines.append("| # | 商品ID | 原标题 | AI 推荐标题 | 状态 |")
    md_lines.append("|---|---------|----------|---------------|------|")
    data_list: list = []
    skipped: list = []
    for idx, (oid, ai_title) in enumerate(suggestions.items(), 1):
        ai_title = (ai_title or "").strip()
        if not ai_title:
            continue
        # 校验标题长度
        length_err = _check_title_length(ai_title)
        if length_err:
            original_title = (items.get(oid) or {}).get("original_title") or "—"
            safe_orig = (original_title or "").replace("|", "\\|").replace("\n", " ")
            safe_ai = ai_title.replace("|", "\\|").replace("\n", " ")
            md_lines.append(f"| {idx} | {oid} | {safe_orig} | {safe_ai} | ⚠️ {length_err} |")
            skipped.append({"offerId": oid, "aiTitle": ai_title, "error": length_err})
            continue
        item = items.get(oid) or {"offer_id": oid}
        item["ai_title"] = ai_title
        items[oid] = item
        original_title = item.get("original_title") or "—"
        # 表格中换行可能破坏格式，简单转义
        safe_orig = (original_title or "").replace("|", "\\|").replace("\n", " ")
        safe_ai = ai_title.replace("|", "\\|").replace("\n", " ")
        md_lines.append(f"| {idx} | {oid} | {safe_orig} | {safe_ai} | ✅ 已暂存 |")
        data_list.append({"offerId": oid, "originalTitle": original_title, "aiTitle": ai_title})

    state["items"] = items
    _save_batch_state(state)

    md_lines.append("")
    if skipped:
        md_lines.append(f"\n> ⚠️ 共 {len(skipped)} 个标题因长度超限未暂存，请缩短后重新提交。\n")
    md_lines.append("---")
    md_lines.append("请确认下一步操作：")
    md_lines.append("1. **全部应用 AI 推荐标题** → `python3 cli.py ai_title_modify --batch-apply`")
    md_lines.append("2. **某个商品使用自定义标题** → `python3 cli.py ai_title_modify --offer_id <商品ID> --subject \"<您的标题>\"`")
    md_lines.append("3. **重新生成**：调整后重新调用 `--batch-suggest`")

    print_output(make_output(
        success=len(skipped) == 0,
        markdown="\n".join(md_lines),
        data={"count": len(data_list), "items": data_list, "skipped": skipped},
    ))


def _mode_batch_apply(apply_arg: str = '__ALL__') -> None:
    """批量模式 3：应用标题。支持两种方式：
    1. 传入 JSON 直接指定 {offerId: title} → 逐个应用
    2. 无参数（'__ALL__'）→ 应用批量状态中全部已暂存的 AI 标题
    """
    if apply_arg == '__ALL__':
        # 原有逻辑：从状态文件读取所有已暂存标题
        state = _load_batch_state()
        if not state or not state.get("items"):
            print_output(make_output(
                success=False,
                error_code="NO_BATCH_STATE",
                markdown="## 未找到批量 AI 标题\n\n请先执行 `ai_title_modify --offer_ids <id1> <id2> ...` 拉取上下文，再通过 `--batch-suggest` 暂存标题。",
            ))
            return
        items: dict = state.get("items") or {}
        pending = [(oid, it.get("ai_title")) for oid, it in items.items() if it.get("ai_title")]
        if not pending:
            print_output(make_output(
                success=False,
                error_code="NO_AI_TITLE",
                markdown="## 未找到可应用的 AI 标题\n\n请先调用 `--batch-suggest` 提交 AI 推荐标题。",
            ))
            return
    else:
        # 新逻辑：解析 JSON 参数，直接指定商品ID和标题
        try:
            title_map = json.loads(apply_arg)
        except (json.JSONDecodeError, TypeError) as e:
            print_output(make_output(
                success=False,
                error_code="INVALID_JSON",
                markdown=f"## JSON 解析失败\n\n`--batch-apply` 参数 JSON 格式错误：{e}\n\n正确格式：`'\"商品ID\":\"标题\",\"商品ID2\":\"标题2\"'`",
            ))
            return
        if not isinstance(title_map, dict) or not title_map:
            print_output(make_output(
                success=False,
                error_code="INVALID_JSON",
                markdown="## 参数格式错误\n\n`--batch-apply` 需要非空 JSON 对象，格式：`'{\"商品ID\":\"标题\",...}'`",
            ))
            return
        # 校验标题长度
        length_errors = []
        for oid, title in title_map.items():
            tlen = calc_title_length(title)
            if tlen > TITLE_MAX_LENGTH:
                length_errors.append(f"- 商品 {oid}：标题长度 {tlen} 字符，超出限制 {TITLE_MAX_LENGTH} 字符")
        if length_errors:
            print_output(make_output(
                success=False,
                error_code="TITLE_TOO_LONG",
                markdown="## 标题长度超限\n\n以下商品标题超出 30 字符限制：\n\n" + "\n".join(length_errors) + "\n\n请缩短标题后重试。",
            ))
            return
        pending = [(str(oid), str(title)) for oid, title in title_map.items()]

    md_lines = ["## 批量标题应用结果\n"]
    md_lines.append("| # | 商品ID | 状态 | 新标题 | 备注 |")
    md_lines.append("|---|---------|------|--------|------|")
    success_cnt = 0
    fail_cnt = 0
    results: list = []
    for idx, (oid, ai_title) in enumerate(pending, 1):
        try:
            r = change_subject(oid, ai_title)
        except Exception as e:
            r = {"success": False, "message": str(e)}
        ok = bool(r.get("success"))
        if ok:
            success_cnt += 1
            status = "✅ 成功"
            note = ""
        else:
            fail_cnt += 1
            status = "❌ 失败"
            note = (r.get("message") or "未知错误").replace("|", "\\|").replace("\n", " ")
        safe_title = (ai_title or "").replace("|", "\\|").replace("\n", " ")
        md_lines.append(f"| {idx} | {oid} | {status} | {safe_title} | {note} |")
        results.append({"offerId": oid, "success": ok, "newTitle": ai_title, "message": r.get("message", "")})

    md_lines.append("")
    md_lines.append(f"合计：成功 **{success_cnt}** 个，失败 **{fail_cnt}** 个。")
    if fail_cnt:
        md_lines.append("失败项可使用 `ai_title_modify --offer_id <商品ID> --subject \"<标题>\"` 重试或调整。")

    print_output(make_output(
        success=fail_cnt == 0,
        markdown="\n".join(md_lines),
        data={"successCount": success_cnt, "failCount": fail_cnt, "results": results},
    ))


def main(args=None):
    """
    AI 标题修改命令入口。

    Args:
        args: 命令参数列表。为 None 时从 sys.argv[1:] 读取。
              通过 cli.py 路由时传入 sys.argv[2:]。
    """
    parser = argparse.ArgumentParser(
        prog="ai_title_modify",
        description=COMMAND_DESC,
    )
    parser.add_argument("--offer_id", type=str, default="", help="商品ID")
    parser.add_argument("--offer_ids", type=str, nargs="+", default=[], help="批量商品ID列表（拉取多个商品上下文）")
    parser.add_argument("--subject", type=str, default="", help="自定义标题（直接应用此标题）")
    parser.add_argument("--suggest", type=str, default="", help="Agent 生成的 AI 推荐标题（暂存到状态文件，供 --apply 使用）")
    parser.add_argument("--apply", action="store_true", help="应用已暂存的 AI 推荐标题")
    parser.add_argument("--batch-suggest", dest="batch_suggest", type=str, default="", help="批量提交 AI 推荐标题（JSON：{\"商品ID\":\"新标题\"}）")
    parser.add_argument("--batch-apply", dest="batch_apply", type=str, nargs='?', const='__ALL__', default=None, help="批量应用标题。无参数时应用全部已暂存标题；传入JSON时应用指定商品ID和标题，格式：'{\"商品ID\":\"标题\",...}'")

    if args is None:
        args = sys.argv[1:]
    parsed = parser.parse_args(args)

    try:
        # 批量模式优先判断（与单商品路径完全解耦）
        # 批量模式 3：应用全部已暂存的 AI 标题
        if parsed.batch_apply is not None:
            _mode_batch_apply(parsed.batch_apply)
            return

        # 批量模式 2：Agent 提交批量 AI 标题
        if parsed.batch_suggest:
            _mode_batch_suggest(parsed.batch_suggest)
            return

        # 批量模式 1：拉取批量上下文
        if parsed.offer_ids:
            _mode_fetch_batch_context(list(parsed.offer_ids))
            return

        if not parsed.offer_id:
            print_output(make_output(
                success=False,
                error_code="MISSING_PARAM",
                markdown="""## 参数错误

请按以下方式使用：

1. **获取上下文（拉取商品信息 + 解析主图）**：
   ```
   python3 cli.py ai_title_modify --offer_id 123456
   ```

2. **暂存 Agent 生成的 AI 推荐标题**：
   ```
   python3 cli.py ai_title_modify --offer_id 123456 --suggest "AI 生成的新标题"
   ```

3. **应用 AI 标题**：
   ```
   python3 cli.py ai_title_modify --offer_id 123456 --apply
   ```

4. **应用自定义标题**：
   ```
   python3 cli.py ai_title_modify --offer_id 123456 --subject "自定义标题"
   ```

5. **批量拉取多个商品上下文**：
   ```
   python3 cli.py ai_title_modify --offer_ids 1001 1002 1003
   ```

6. **批量提交 AI 推荐标题**：
   ```
   python3 cli.py ai_title_modify --batch-suggest '{"1001":"新标题1","1002":"新标题2"}'
   ```

7. **应用批量 AI 标题**：
   ```
   python3 cli.py ai_title_modify --batch-apply
   ```
""",
            ))
            return

        # 模式 4：应用自定义标题（--offer_id + --subject）
        if parsed.subject:
            _mode_apply_custom(parsed.offer_id, parsed.subject)
            return

        # 模式 2：Agent 暂存 AI 标题（--offer_id + --suggest）
        if parsed.suggest:
            _mode_suggest(parsed.offer_id, parsed.suggest)
            return

        # 模式 3：应用已暂存的 AI 标题（--offer_id + --apply）
        if parsed.apply:
            _mode_apply(parsed.offer_id)
            return

        # 模式 1：拉取上下文（仅 --offer_id）
        _mode_fetch_context(parsed.offer_id)

    except Exception as e:
        print_error(e)


if __name__ == "__main__":
    main()
