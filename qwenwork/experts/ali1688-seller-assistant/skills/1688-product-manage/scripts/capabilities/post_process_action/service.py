#!/usr/bin/env python3
"""Post-process MCP results for 1688 product management workflows."""

from __future__ import annotations

import base64
import json
import os
import time
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image


TITLE_MAX_LENGTH = 30
DEFAULT_SIZE = "1:1"
ALLOWED_SIZES = {"1:1", "3:4"}
ALLOWED_CUSTOMIZE_KEYS = {"size", "background", "text_selling_points"}

BASE_DIR = Path(__file__).resolve().parents[2]
PUBLISH_STATE_FILE = BASE_DIR / ".publish_state.json"
BATCH_PUBLISH_STATE_FILE = BASE_DIR / ".batch_publish_state.json"
TITLE_STATE_FILE = BASE_DIR / ".title_state.json"
BATCH_TITLE_STATE_FILE = BASE_DIR / ".batch_title_state.json"
IMAGE_STATE_FILE = BASE_DIR / ".image_state.json"


def handle_action(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("输入必须是 JSON 对象")
    action = payload.get("action")
    if not action:
        raise ValueError("缺少 action")

    handlers = {
        "compress_image": _compress_image_action,
        "publish_candidates": _publish_candidates_action,
        "publish_save_result": _publish_save_result_action,
        "title_context": _title_context_action,
        "title_suggest": _title_suggest_action,
        "title_apply_result": _title_apply_result_action,
        "batch_title_suggest": _batch_title_suggest_action,
        "batch_title_apply_result": _batch_title_apply_result_action,
        "image_prepare": _image_prepare_action,
        "image_customize": _image_customize_action,
        "image_generate_result": _image_generate_result_action,
        "image_apply_plan": _image_apply_plan_action,
        "image_apply_result": _image_apply_result_action,
        "offer_operation_result": _offer_operation_result_action,
    }
    handler = handlers.get(action)
    if not handler:
        raise ValueError(f"未知 action: {action}")
    return handler(payload)


def _compress_image_action(payload: dict[str, Any]) -> dict[str, Any]:
    image_path = payload.get("image_path") or payload.get("image")
    if not image_path:
        raise ValueError("缺少 image_path")
    base64_str, image_name = compress_image_to_base64(str(image_path))
    return {
        "markdown": f"图片 `{image_name}` 已完成压缩编码，可调用 MCP 工具 `image_bank_upload_picture`。",
        "data": {"imageName": image_name, "base64Str": base64_str},
    }


def _publish_candidates_action(payload: dict[str, Any]) -> dict[str, Any]:
    pic_url = payload.get("picUrl") or payload.get("pic_url")
    mcp_result = _unwrap(payload.get("mcp_result") or payload.get("result"))
    parsed = parse_ai_publish_result(mcp_result)
    if parsed.get("redirect"):
        return {
            "markdown": "未识别到可用同款，建议进入手动发品页继续发布。",
            "data": {"redirect": parsed["redirect"], "picUrl": pic_url},
        }

    candidates = parsed.get("effectiveItemIds") or []
    state = {"picUrl": pic_url, "publishData": parsed, "saved_at": time.time()}
    _write_json(PUBLISH_STATE_FILE, state)

    lines = ["## AI 识图同款候选已生成", ""]
    lines.append(f"**类目**: {parsed.get('categoryName') or '未识别'}")
    lines.append("")
    lines.append("| 序号 | 同款标题 | 主图 | 卖点 |")
    lines.append("|---|---|---|---|")
    for idx, item in enumerate(candidates, 1):
        title = _safe_cell(item.get("sameItemTitle") or "")
        image = _safe_cell(item.get("sameItemPicUrl") or "")
        point = _safe_cell(_format_seller_point(item.get("sameItemSellerPoint")))
        lines.append(f"| {idx} | {title} | {image} | {point} |")
    lines.append("")
    lines.append("")
    lines.append("⛔ **Agent 必须在此停下，等待商家明确选择序号后才能继续。严禁自动选品或跳过此步骤。**")
    lines.append("")
    lines.append("商家选定序号后，再调用 MCP `ai_publish_save_tair`，并将保存结果交给 `publish_save_result` 后处理。")

    return {
        "markdown": "\n".join(lines),
        "data": {"picUrl": pic_url, "publishData": parsed, "candidateCount": len(candidates)},
    }


def _publish_save_result_action(payload: dict[str, Any]) -> dict[str, Any]:
    mcp_result = _unwrap(payload.get("mcp_result") or payload.get("result"))
    category_id = payload.get("categoryId") or payload.get("category_id")
    if not category_id:
        state = _read_json(PUBLISH_STATE_FILE) or {}
        category_id = (state.get("publishData") or {}).get("categoryId")
    aigc_time = extract_aigc_time(mcp_result)
    url = build_publish_url(str(aigc_time), int(category_id or 0))
    return {
        "markdown": f"## 发品链接已生成\n\n[点击进入发品页面]({url})",
        "data": {"publishUrl": url, "aigcSelectCategoryTime": str(aigc_time), "categoryId": int(category_id or 0)},
    }


def _title_context_action(payload: dict[str, Any]) -> dict[str, Any]:
    offer_id = str(payload.get("offerId") or payload.get("offer_id") or "")
    if not offer_id:
        raise ValueError("缺少 offerId")
    offer_info = parse_offer_info(_unwrap(payload.get("offer_query_result") or payload.get("offer")))
    parse_result = normalize_image_parse_result(payload.get("image_parse_result"))
    state = {
        "offer_id": offer_id,
        "original_title": offer_info["title"],
        "images": offer_info["images"],
        "parse_result": parse_result,
        "saved_at": time.time(),
    }
    _write_json(TITLE_STATE_FILE, state)
    return {
        "markdown": format_title_context_markdown(offer_id, offer_info["title"], offer_info["images"], parse_result),
        "data": {"offerId": offer_id, "originalTitle": offer_info["title"], "images": offer_info["images"], "parseResult": parse_result},
    }


def _title_suggest_action(payload: dict[str, Any]) -> dict[str, Any]:
    offer_id = str(payload.get("offerId") or payload.get("offer_id") or "")
    title = str(payload.get("title") or payload.get("ai_title") or "").strip()
    _validate_title(offer_id, title)
    state = _read_json(TITLE_STATE_FILE) or {"offer_id": offer_id}
    state["offer_id"] = offer_id
    state["ai_title"] = title
    state["saved_at"] = time.time()
    _write_json(TITLE_STATE_FILE, state)
    original = state.get("original_title") or ""
    md = ["## AI 标题优化建议", "", f"**商品ID**: {offer_id}"]
    if original:
        md.append(f"**原标题**: {original}")
    md.append(f"**AI 推荐标题**: {title}")
    md.append("")
    md.append("请用户确认后调用 MCP `cbu_skill_change_subject`，再将返回结果交给 `title_apply_result`。")
    return {"markdown": "\n".join(md), "data": {"offerId": offer_id, "aiTitle": title, "length": calc_title_length(title)}}


def _title_apply_result_action(payload: dict[str, Any]) -> dict[str, Any]:
    offer_id = str(payload.get("offerId") or payload.get("offer_id") or "")
    title = str(payload.get("title") or payload.get("subject") or "")
    if not title:
        state = _read_json(TITLE_STATE_FILE) or {}
        title = state.get("ai_title") or ""
    result = parse_success_result(_unwrap(payload.get("mcp_result") or payload.get("result")))
    if result["success"]:
        return {"markdown": f"## 标题修改成功\n\n**商品ID**: {offer_id}\n\n**新标题**: {title}", "data": {"offerId": offer_id, "newTitle": title, "applied": True}}
    return {"success": False, "markdown": f"## 标题修改失败\n\n**商品ID**: {offer_id}\n\n错误：{result['message']}", "data": {"offerId": offer_id, "message": result["message"]}}


def _batch_title_suggest_action(payload: dict[str, Any]) -> dict[str, Any]:
    suggestions = payload.get("suggestions")
    if not isinstance(suggestions, dict) or not suggestions:
        raise ValueError("suggestions 必须为非空 JSON 对象")
    state = _read_json(BATCH_TITLE_STATE_FILE) or {"items": {}}
    items = state.get("items") or {}
    skipped = []
    rows = ["## 批量 AI 标题优化建议", "", "| # | 商品ID | 原标题 | AI 推荐标题 | 状态 |", "|---|---|---|---|---|"]
    for idx, (offer_id, title) in enumerate(suggestions.items(), 1):
        title = str(title or "").strip()
        try:
            _validate_title(str(offer_id), title)
        except ValueError as exc:
            skipped.append({"offerId": str(offer_id), "title": title, "error": str(exc)})
            rows.append(f"| {idx} | {offer_id} | — | {_safe_cell(title)} | {str(exc)} |")
            continue
        item = items.get(str(offer_id)) or {"offer_id": str(offer_id)}
        item["ai_title"] = title
        items[str(offer_id)] = item
        rows.append(f"| {idx} | {offer_id} | {_safe_cell(item.get('original_title') or '—')} | {_safe_cell(title)} | 已暂存 |")
    state["items"] = items
    _write_json(BATCH_TITLE_STATE_FILE, state)
    return {"success": not skipped, "markdown": "\n".join(rows), "data": {"items": items, "skipped": skipped}}


def _batch_title_apply_result_action(payload: dict[str, Any]) -> dict[str, Any]:
    results = payload.get("results")
    if not isinstance(results, list):
        raise ValueError("results 必须为数组")
    lines = ["## 批量标题应用结果", "", "| # | 商品ID | 状态 | 新标题 | 备注 |", "|---|---|---|---|---|"]
    success_cnt = fail_cnt = 0
    normalized = []
    for idx, item in enumerate(results, 1):
        offer_id = str(item.get("offerId") or item.get("offer_id") or "")
        title = str(item.get("title") or item.get("subject") or "")
        parsed = parse_success_result(_unwrap(item.get("mcp_result") or item.get("result")))
        if parsed["success"]:
            success_cnt += 1
            status = "成功"
            note = ""
        else:
            fail_cnt += 1
            status = "失败"
            note = parsed["message"]
        lines.append(f"| {idx} | {offer_id} | {status} | {_safe_cell(title)} | {_safe_cell(note)} |")
        normalized.append({"offerId": offer_id, "success": parsed["success"], "newTitle": title, "message": note})
    lines.append("")
    lines.append(f"合计：成功 **{success_cnt}** 个，失败 **{fail_cnt}** 个。")
    return {"success": fail_cnt == 0, "markdown": "\n".join(lines), "data": {"results": normalized, "successCount": success_cnt, "failCount": fail_cnt}}


def _image_prepare_action(payload: dict[str, Any]) -> dict[str, Any]:
    offer_id = str(payload.get("offerId") or payload.get("offer_id") or "")
    offer_info = parse_offer_info(_unwrap(payload.get("offer_query_result") or payload.get("offer")))
    parse_results = payload.get("image_parse_results")
    if not isinstance(parse_results, list):
        parse_results = [payload.get("image_parse_result")] if payload.get("image_parse_result") is not None else []

    specs = []
    for idx, image_url in enumerate(offer_info["images"], 1):
        parse_result = normalize_image_parse_result(parse_results[idx - 1] if idx - 1 < len(parse_results) else None)
        specs.append({
            "index": idx,
            "original_url": image_url,
            "parse_result": parse_result,
            "size": DEFAULT_SIZE,
            "text_selling_points": "",
            "scene": "",
            "prompt": build_prompt(DEFAULT_SIZE),
        })
    state = {"offer_id": offer_id, "title": offer_info["title"], "images": offer_info["images"], "image_specs": specs, "stage": "prepare", "saved_at": time.time()}
    _write_json(IMAGE_STATE_FILE, state)

    lines = ["## 主图优化上下文已就绪", "", f"**商品ID**: {offer_id}", f"**商品标题**: {offer_info['title'] or '（无）'}", ""]
    lines.append("| 序号 | 原图 | 默认比例 | 默认 prompt |")
    lines.append("|---|---|---|---|")
    for spec in specs:
        lines.append(f"| {spec['index']} | {spec['original_url']} | {spec['size']} | {_safe_cell(spec['prompt'])} |")
    lines.append("")
    lines.append("如需调整比例、背景或文字卖点，调用 `image_customize`；确认后由 Agent 调用 MCP 图生图工具。")
    return {"markdown": "\n".join(lines), "data": {"offerId": offer_id, "imageSpecs": specs}}


def _image_customize_action(payload: dict[str, Any]) -> dict[str, Any]:
    offer_id = str(payload.get("offerId") or payload.get("offer_id") or "")
    customize = payload.get("customize")
    if not isinstance(customize, dict) or not customize:
        raise ValueError("customize 必须为非空 JSON 对象")
    state = _read_json(IMAGE_STATE_FILE)
    if not state or state.get("offer_id") != offer_id:
        raise ValueError("未找到主图优化上下文，请先执行 image_prepare")
    specs = state.get("image_specs") or []
    if _is_per_image_payload(customize):
        apply_per_image_customize(specs, customize)
    else:
        apply_unified_customize(specs, customize)
    state["image_specs"] = specs
    state["stage"] = "customize"
    _write_json(IMAGE_STATE_FILE, state)
    return {"markdown": format_prompt_table(offer_id, specs), "data": {"offerId": offer_id, "imageSpecs": specs}}


def _image_generate_result_action(payload: dict[str, Any]) -> dict[str, Any]:
    offer_id = str(payload.get("offerId") or payload.get("offer_id") or "")
    state = _read_json(IMAGE_STATE_FILE) or {}
    specs = state.get("image_specs") or payload.get("imageSpecs") or []
    results = payload.get("results")
    if not isinstance(results, list):
        raise ValueError("results 必须为数组")
    generated = []
    spec_by_index = {int(s["index"]): s for s in specs if isinstance(s, dict) and s.get("index") is not None}
    for item in results:
        idx = int(item.get("index") or item.get("image_id") or item.get("imageId") or 0)
        parsed = parse_generated_image_result(_unwrap(item.get("mcp_result") or item.get("result") or item))
        spec = spec_by_index.get(idx, {})
        generated.append({"index": idx, "success": parsed["success"], "generated_url": parsed.get("generated_url", ""), "message": parsed.get("message", ""), "original_url": spec.get("original_url", "")})
    generated.sort(key=lambda x: x["index"])
    state["generated"] = generated
    state["stage"] = "generate"
    _write_json(IMAGE_STATE_FILE, state)
    return {"markdown": format_generated_markdown(offer_id, generated), "data": {"offerId": offer_id, "generated": generated}}


def _image_apply_plan_action(payload: dict[str, Any]) -> dict[str, Any]:
    offer_id = str(payload.get("offerId") or payload.get("offer_id") or "")
    select = payload.get("select") or ""
    state = _read_json(IMAGE_STATE_FILE) or {}
    generated = state.get("generated") or payload.get("generated") or []
    selected, ignored = select_generated_indexes(generated, str(select))
    if not selected:
        raise ValueError("无可应用的优化图片，所选序号均未成功生成")
    pic_urls = [g["generated_url"] for g in generated if g.get("index") in selected]
    return {"markdown": "已生成图片链接转换计划，请调用 MCP `image_bank_change_url_for_offer`。", "data": {"offerId": offer_id, "selected": selected, "ignored": ignored, "picUrl": pic_urls}}


def _image_apply_result_action(payload: dict[str, Any]) -> dict[str, Any]:
    offer_id = str(payload.get("offerId") or payload.get("offer_id") or "")
    selected = [int(x) for x in payload.get("selected", [])]
    state = _read_json(IMAGE_STATE_FILE) or {}
    specs = state.get("image_specs") or []
    generated = state.get("generated") or []
    conversion = parse_conversion_result(_unwrap(payload.get("conversion_result") or payload.get("convert_result")))
    final_images = merge_final_images(specs, generated, selected, conversion["images"])

    change_result_payload = payload.get("change_result")
    if change_result_payload is None:
        return {
            "markdown": "图片链接已转换，请调用 MCP `cbu_skill_change_main_image` 应用最终主图列表。",
            "data": {"offerId": offer_id, "images": final_images, "selected": selected},
        }

    parsed = parse_success_result(_unwrap(change_result_payload))
    if parsed["success"]:
        return {"markdown": f"## 主图修改成功\n\n**商品ID**: {offer_id}\n\n已应用 {len(selected)} 张优化主图。", "data": {"offerId": offer_id, "images": final_images, "applied": True}}
    return {"success": False, "markdown": f"## 主图修改失败\n\n**商品ID**: {offer_id}\n\n错误：{parsed['message']}", "data": {"offerId": offer_id, "images": final_images, "message": parsed["message"]}}


def _offer_operation_result_action(payload: dict[str, Any]) -> dict[str, Any]:
    operation = payload.get("operation")
    if operation not in {"cancel", "repost"}:
        raise ValueError("operation 必须为 cancel 或 repost")
    offer_ids = payload.get("offerIds") or payload.get("offer_ids") or []
    if isinstance(offer_ids, str):
        offer_ids = [offer_ids]
    offer_ids = [str(x).strip() for x in offer_ids if str(x).strip()]
    parsed = parse_success_result(_unwrap(payload.get("mcp_result") or payload.get("result")))
    verb = "下架" if operation == "cancel" else "上架"
    if parsed["success"]:
        if len(offer_ids) == 1:
            markdown = f"商品 `{offer_ids[0]}` {verb}成功"
        else:
            markdown = f"{len(offer_ids)} 个商品{verb}成功：{', '.join(f'`{oid}`' for oid in offer_ids)}"
        return {"markdown": markdown, "data": {"success": True, "message": f"{verb}成功", "offerIds": offer_ids}}
    if len(offer_ids) == 1:
        markdown = f"商品 `{offer_ids[0]}` {verb}失败：{parsed['message']}"
    else:
        markdown = f"商品{verb}失败：{parsed['message']}"
    return {"success": False, "markdown": markdown, "data": {"success": False, "message": parsed["message"], "offerIds": offer_ids}}


def compress_image_to_base64(image_path: str, max_size_bytes: int = 1_000_000) -> tuple[str, str]:
    if not os.path.exists(image_path):
        raise ValueError(f"图片文件不存在: {image_path}")
    if not os.path.isfile(image_path):
        raise ValueError(f"路径不是文件: {image_path}")
    image_name = os.path.basename(image_path)
    if os.path.getsize(image_path) <= max_size_bytes:
        with open(image_path, "rb") as file:
            return base64.b64encode(file.read()).decode("utf-8"), image_name

    img = Image.open(image_path)
    if img.mode in ("RGBA", "P", "LA", "L", "I", "F", "YCbCr", "CMYK", "HSV"):
        img = img.convert("RGB")

    def try_compress(image: Image.Image, start_quality: int):
        for quality in range(start_quality, 9, -5):
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=quality, optimize=True)
            if buffer.tell() <= max_size_bytes:
                return buffer.getvalue()
        return None

    raw = try_compress(img, 95)
    if raw:
        return base64.b64encode(raw).decode("utf-8"), image_name

    width, height = img.size
    for _ in range(5):
        width, height = int(width * 0.8), int(height * 0.8)
        if width < 10 or height < 10:
            break
        raw = try_compress(img.resize((width, height), Image.Resampling.LANCZOS), 85)
        if raw:
            return base64.b64encode(raw).decode("utf-8"), image_name
    raise ValueError(f"图片压缩失败，无法将 {image_name} 压缩到 {max_size_bytes} 字节以内")


def parse_ai_publish_result(resp: dict[str, Any]) -> dict[str, Any]:
    data_json_str = resp.get("dataJson") or (resp.get("data") or {}).get("dataJson")
    if not data_json_str:
        return {"redirect": "https://offer-new.1688.com/select.htm"}
    try:
        data = json.loads(data_json_str) if isinstance(data_json_str, str) else data_json_str
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI 识图返回数据解析失败: {exc}")
    effective = []
    for item in data.get("effectiveItemIds", []) if isinstance(data, dict) else []:
        if isinstance(item, dict):
            effective.append({
                "sameItemId": item.get("sameItemId"),
                "sameItemTitle": item.get("sameItemTitle"),
                "sameItemPicUrl": item.get("sameItemPicUrl"),
                "sameItemSellerPoint": item.get("sameItemSellerPoint"),
            })
    return {"categoryId": int(data.get("categoryId", 0)), "categoryName": str(data.get("categoryName", "")), "tkItemIds": data.get("tkItemIds", []), "effectiveItemIds": effective}


def extract_aigc_time(resp: dict[str, Any]) -> str:
    data_json_str = resp.get("dataJson") or (resp.get("data") or {}).get("dataJson")
    if not data_json_str:
        raise ValueError("保存选品数据失败，未返回 dataJson")
    data = json.loads(data_json_str) if isinstance(data_json_str, str) else data_json_str
    aigc_time = data.get("aigcSelectCategoryTime") if isinstance(data, dict) else None
    if not aigc_time:
        raise ValueError("保存选品数据失败，未返回 aigcSelectCategoryTime")
    return str(aigc_time)


def build_publish_url(aigc_time: str, cat_id: int) -> str:
    return f"https://offer-new.1688.com/aigc/publish.htm?operator=new&scene=effectiveType&aigcSelectCategoryTime={aigc_time}&catId={cat_id}"


def calc_title_length(title: str) -> float:
    return sum(1.0 if ord(ch) > 127 else 0.5 for ch in title)


def parse_offer_info(resp: dict[str, Any]) -> dict[str, Any]:
    data = resp.get("data") if isinstance(resp.get("data"), dict) else {}
    title = resp.get("title") or data.get("title") or resp.get("subject") or data.get("subject") or ""
    images = resp.get("images") or data.get("images") or resp.get("image") or data.get("image") or []
    if isinstance(images, str):
        images = [images]
    if not isinstance(images, list):
        images = []
    if not title and not images:
        raise ValueError("未获取到商品标题与主图，请检查商品ID")
    return {"title": title, "images": images}


def normalize_image_parse_result(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    resp = _unwrap(value)
    if resp.get("success") is False:
        return {"success": False, "message": resp.get("message") or "图片解析未完成"}
    data = resp.get("data") if isinstance(resp.get("data"), dict) else {}
    text_summary = resp.get("text_region_summary") or data.get("text_region_summary")
    selling_points = resp.get("selling_points_visible") or data.get("selling_points_visible")
    composition = resp.get("composition_summary") or data.get("composition_summary")
    if text_summary or selling_points or composition:
        return {"success": True, "text_region_summary": text_summary or "", "selling_points_visible": selling_points or [], "composition_summary": composition or ""}
    return {"success": False, "message": resp.get("message") or "图片解析未完成"}


def format_title_context_markdown(offer_id: str, original_title: str, images: list, parse_result: dict | None) -> str:
    lines = ["## 商品标题优化上下文已就绪", "", f"**商品ID**: {offer_id}", f"**原标题**: {original_title or '（无）'}"]
    if images:
        lines.append(f"**主图（首图）**: {images[0]}")
    lines.append("")
    if parse_result and parse_result.get("success"):
        lines.append("### 图片解析结果")
        if parse_result.get("text_region_summary"):
            lines.append(f"- **文字区域**：{parse_result['text_region_summary']}")
        if parse_result.get("selling_points_visible"):
            lines.append(f"- **可见卖点**：{', '.join(parse_result['selling_points_visible'])}")
        if parse_result.get("composition_summary"):
            lines.append(f"- **构图摘要**：{parse_result['composition_summary']}")
    elif parse_result:
        lines.append(f"> 图片解析未完成：{parse_result.get('message', '')}")
    else:
        lines.append("> 商品无主图，跳过图片解析")
    lines.append("")
    lines.append("请基于上述上下文生成标题，再调用 `title_suggest` 暂存并由用户确认。")
    return "\n".join(lines)


def build_prompt(size: str, text_selling_points: str | None = None, background: str | None = None) -> str:
    if size not in ALLOWED_SIZES:
        size = DEFAULT_SIZE
    tsp = text_selling_points.strip() if text_selling_points and text_selling_points.strip() else None
    bg = background.strip() if background and background.strip() else None
    out = f"做一张1688商品电商的主图,{size}比例"
    if tsp:
        out += f"，突出{tsp}的文字卖点"
    if bg:
        out += f"{',' if tsp else '，'}背景换成{bg}"
    return out


def apply_unified_customize(specs: list[dict[str, Any]], payload: dict[str, Any]) -> None:
    validate_customize_keys(payload, "统一型 payload ")
    size = normalize_size(payload.get("size") or DEFAULT_SIZE)
    for spec in specs:
        spec["size"] = size
        if "background" in payload:
            spec["scene"] = payload.get("background") or ""
        if "text_selling_points" in payload:
            spec["text_selling_points"] = payload.get("text_selling_points") or ""
        spec["prompt"] = build_prompt(size, spec.get("text_selling_points"), spec.get("scene"))


def apply_per_image_customize(specs: list[dict[str, Any]], payload: dict[str, Any]) -> None:
    for key, value in payload.items():
        if not isinstance(value, dict):
            raise ValueError(f"序号 {key} 的配置必须是对象")
        idx = int(key)
        target = next((s for s in specs if int(s["index"]) == idx), None)
        if not target:
            raise ValueError(f"序号 {idx} 不存在（共 {len(specs)} 张图）")
        validate_customize_keys(value, f"序号 {idx} 的 payload ")
        target["size"] = normalize_size(value.get("size") or target.get("size") or DEFAULT_SIZE)
        if "background" in value:
            target["scene"] = value.get("background") or ""
        if "text_selling_points" in value:
            target["text_selling_points"] = value.get("text_selling_points") or ""
        target["prompt"] = build_prompt(target["size"], target.get("text_selling_points"), target.get("scene"))


def format_prompt_table(offer_id: str, specs: list[dict[str, Any]]) -> str:
    lines = ["## 主图优化 prompt 已更新", "", f"**商品ID**: {offer_id}", "", "| 序号 | 图片 | 图片比例 | 文字卖点 | 场景 | 最终 prompt |", "|---|---|---|---|---|---|"]
    for spec in specs:
        lines.append(f"| {spec['index']} | {spec['original_url']} | {spec['size']} | {_safe_cell(spec.get('text_selling_points') or '—')} | {_safe_cell(spec.get('scene') or '—')} | {_safe_cell(spec.get('prompt') or '')} |")
    lines.append("")
    lines.append("请按表格中的 prompt 调用 MCP `cbu_image_generation_and_editing_tool`。")
    return "\n".join(lines)


def parse_generated_image_result(resp: dict[str, Any]) -> dict[str, Any]:
    if resp.get("success") is False:
        return {"success": False, "message": resp.get("message") or resp.get("msgInfo") or "生成失败"}
    data = resp.get("data") if isinstance(resp.get("data"), dict) else {}
    urls = resp.get("gen_image_urls") or data.get("gen_image_urls") or resp.get("imageUrls") or data.get("imageUrls") or []
    if isinstance(urls, str):
        urls = [urls]
    urls = [url for url in urls if url]
    if urls:
        return {"success": True, "generated_url": urls[0]}
    return {"success": False, "message": resp.get("message") or "生成失败"}


def format_generated_markdown(offer_id: str, generated: list[dict[str, Any]]) -> str:
    success_cnt = sum(1 for item in generated if item.get("success"))
    fail_cnt = len(generated) - success_cnt
    lines = ["## AI 主图生成完成", "", f"**商品ID**: {offer_id}", f"**成功**: {success_cnt} 张  **失败**: {fail_cnt} 张", "", "| 序号 | 原图 | 优化后图片 |", "|---|---|---|"]
    for item in generated:
        cell = item.get("generated_url") if item.get("success") else f"生成失败，已保留原图（{item.get('message') or '生成失败'}）"
        lines.append(f"| {item['index']} | {item.get('original_url') or ''} | {_safe_cell(cell)} |")
    lines.append("")
    lines.append("如需应用，先调用 `image_apply_plan` 生成待转换图片列表。")
    return "\n".join(lines)


def select_generated_indexes(generated: list[dict[str, Any]], select_str: str) -> tuple[list[int], list[int]]:
    success_set = {int(g["index"]) for g in generated if g.get("success")}
    if select_str:
        requested = [int(token.strip()) for token in select_str.split(",") if token.strip()]
        return [idx for idx in requested if idx in success_set], [idx for idx in requested if idx not in success_set]
    return sorted(success_set), []


def parse_conversion_result(resp: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_success_result(resp)
    if not parsed["success"]:
        raise ValueError(f"图片链接转换失败：{parsed['message']}")
    data = resp.get("data") if isinstance(resp.get("data"), dict) else {}
    model = resp.get("model") or data.get("model")
    if not isinstance(model, list):
        raise ValueError("图片链接转换失败：响应格式异常")
    images = []
    for item in model:
        if isinstance(item, dict) and item.get("relativeUrl"):
            images.append(f"https://cbu01.alicdn.com/{item['relativeUrl']}")
        elif isinstance(item, str):
            images.append(item)
    if not images:
        raise ValueError("图片链接转换失败：未获取到有效链接")
    return {"images": images}


def merge_final_images(specs: list[dict[str, Any]], generated: list[dict[str, Any]], selected: list[int], converted_urls: list[str]) -> list[str]:
    converted_by_index = {idx: converted_urls[pos] for pos, idx in enumerate(selected) if pos < len(converted_urls)}
    final = []
    for spec in sorted(specs, key=lambda item: int(item["index"])):
        idx = int(spec["index"])
        final.append(converted_by_index.get(idx) or spec.get("original_url") or "")
    return final


def parse_success_result(resp: dict[str, Any]) -> dict[str, Any]:
    data = resp.get("data") if isinstance(resp.get("data"), dict) else {}
    success = data.get("success") if data.get("success") is not None else data.get("successs")
    if success is None:
        success = resp.get("success")
    message = data.get("message") or resp.get("message") or resp.get("msgInfo") or resp.get("msgCode") or "API 返回失败，请检查参数后重试"
    for eng, chn in {"user doesn't have these offer": "当前账号下没有该商品", "operate failed": "操作失败，请检查商品状态"}.items():
        if eng in str(message).lower():
            message = chn
    return {"success": bool(success), "message": str(message)}


def normalize_size(size: str) -> str:
    if size in ALLOWED_SIZES:
        return size
    raise ValueError(f"size 仅支持 1:1 / 3:4，收到：{size}")


def validate_customize_keys(payload: dict[str, Any], where: str) -> None:
    extra = sorted(set(payload.keys()) - ALLOWED_CUSTOMIZE_KEYS)
    if extra:
        raise ValueError(f"{where}出现不允许的字段：{extra}。仅支持 size、background、text_selling_points，不允许提交 prompt / selling_points。")


def _is_per_image_payload(payload: dict[str, Any]) -> bool:
    if not payload:
        return False
    try:
        for key in payload.keys():
            int(key)
        return True
    except (TypeError, ValueError):
        return False


def _validate_title(offer_id: str, title: str) -> None:
    if not offer_id:
        raise ValueError("商品ID不能为空")
    if not title:
        raise ValueError("标题不能为空")
    length = calc_title_length(title)
    if length > TITLE_MAX_LENGTH:
        raise ValueError(f"标题长度超出限制：当前 {length:g} 字符（限制 {TITLE_MAX_LENGTH} 字符），请缩短标题后重试。")


def _unwrap(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("MCP 返回必须是 JSON 对象")
    if value.get("success") is False or value.get("__success__") is False:
        return value
    data = value.get("data")
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        return data["data"]
    return value


def _format_seller_point(value: Any) -> str:
    if not value or not isinstance(value, dict):
        return "无"
    return ", ".join(f"{key}: {val}" for key, val in value.items())


def _safe_cell(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
