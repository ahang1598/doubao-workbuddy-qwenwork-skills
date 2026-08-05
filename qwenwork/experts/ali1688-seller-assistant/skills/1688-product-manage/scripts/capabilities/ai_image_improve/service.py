#!/usr/bin/env python3
"""AI 主图优化服务 — 商品查询、图片解析、图片生成、URL 转换、修改商品主图"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import json
import time
import logging
from typing import Optional

from _errors import ParamError, ServiceError
from _http import api_post_raw

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ai_image_improve')

# 接口路径
OFFER_QUERY_PATH = "/api/cbu_offer_query_tool/1.0.0"
IMAGE_ANALYSE_PATH = "/api/cbu_image_analyse_tool/1.0.0"
IMAGE_GEN_PATH = "/api/cbu_image_generation_and_editing_tool/1.0.0"
IMAGE_BANK_CONVERT_PATH = "/api/image_bank_change_url_for_offer/1.0.0"
CHANGE_MAIN_IMAGE_PATH = "/api/cbu_skill_change_main_image/1.0.0"

# 图片解析任务类型（固定字段）
IMAGE_PARSE_TYPE = "ecommerce_content_parsing"
# 图片编辑类型（固定字段）
IMAGE_GEN_TYPE = "image_to_image"


def query_offer_info(offer_id: str) -> dict:
    """
    查询商品基础信息（标题 + 主图列表）。

    Returns:
        {"title": "...", "images": ["url1", "url2", ...]}
    """
    if not offer_id:
        raise ParamError("商品ID不能为空")

    logger.info("查询商品基础信息，offerId=%s", offer_id)
    resp = api_post_raw(OFFER_QUERY_PATH, {"offerId": offer_id})
    logger.info("商品信息响应: %s", json.dumps(resp, ensure_ascii=False, default=str)[:500])

    if resp.get("success") is False:
        raise ServiceError("商品信息查询失败")

    data = resp.get("data") if isinstance(resp.get("data"), dict) else {}
    title = resp.get("title") or data.get("title") or ""
    images = resp.get("images") or data.get("images") or []
    if not isinstance(images, list):
        images = []

    if not title and not images:
        raise ServiceError("未获取到商品标题与主图，请检查商品ID")

    return {"title": title, "images": images}


def submit_image_parse(image_url: str) -> str:
    """提交图片解析任务，返回 taskId。"""
    if not image_url:
        raise ParamError("图片 URL 不能为空")

    logger.info("提交图片解析任务，imageUrl=%s", image_url)
    resp = api_post_raw(IMAGE_ANALYSE_PATH, {
        "type": IMAGE_PARSE_TYPE,
        "imageUrlList": [image_url],
    })
    logger.info("图片解析任务响应: %s", json.dumps(resp, ensure_ascii=False, default=str)[:500])

    if resp.get("success") is False:
        raise ServiceError("图片解析任务提交失败")

    data = resp.get("data") if isinstance(resp.get("data"), dict) else {}
    task_id = resp.get("taskId") or data.get("taskId")
    if not task_id:
        raise ServiceError("未获取到图片解析 taskId")

    return str(task_id)


def poll_image_parse_result(task_id: str, timeout: int = 30, interval: int = 3) -> dict:
    """
    轮询图片解析结果。

    Returns:
        {"success": True, "text_region_summary": "...",
         "selling_points_visible": [...], "composition_summary": "..."}
        或 {"success": False, "message": "..."}
    """
    elapsed = 0
    attempt = 0

    while elapsed < timeout:
        time.sleep(interval)
        elapsed += interval
        attempt += 1
        logger.info("第 %d 次轮询图片解析结果（已等待 %d 秒），taskId=%s", attempt, elapsed, task_id)

        try:
            resp = api_post_raw(IMAGE_ANALYSE_PATH, {"taskId": task_id})
        except Exception as e:
            logger.warning("第 %d 次图片解析轮询异常: %s", attempt, e)
            continue

        if resp.get("success") is False:
            continue

        data = resp.get("data") if isinstance(resp.get("data"), dict) else {}
        text_summary = resp.get("text_region_summary") or data.get("text_region_summary")
        selling_points = resp.get("selling_points_visible") or data.get("selling_points_visible")
        composition = resp.get("composition_summary") or data.get("composition_summary")

        if text_summary or selling_points or composition:
            return {
                "success": True,
                "text_region_summary": text_summary or "",
                "selling_points_visible": selling_points or [],
                "composition_summary": composition or "",
            }

    return {"success": False, "message": f"图片解析未完成（已等待 {elapsed} 秒），请稍后重试"}


def submit_image_generation(image_id: str, image_url: str, prompt: str, size: str) -> str:
    """提交图片生成任务，返回 taskId。"""
    if not image_url:
        raise ParamError("图片 URL 不能为空")
    if not prompt:
        raise ParamError("prompt 不能为空")
    if size not in ("1:1", "3:4"):
        raise ParamError("size 仅支持 1:1 或 3:4")

    body = {
        "type": IMAGE_GEN_TYPE,
        "imageId": str(image_id),
        "imageUrlList": [image_url],
        "prompt": prompt,
        "size": size,
        "params": {},
    }
    logger.info("提交图片生成任务，imageId=%s, size=%s", image_id, size)
    resp = api_post_raw(IMAGE_GEN_PATH, body)
    logger.info("图片生成任务响应: %s", json.dumps(resp, ensure_ascii=False, default=str)[:500])

    if resp.get("success") is False:
        raise ServiceError("图片生成任务提交失败")

    data = resp.get("data") if isinstance(resp.get("data"), dict) else {}
    task_id = resp.get("taskId") or data.get("taskId")
    if not task_id:
        raise ServiceError("未获取到图片生成 taskId")

    return str(task_id)


def poll_image_generation_result(task_id: str, timeout: int = 120, interval: int = 4) -> dict:
    """
    轮询图片生成结果。

    Returns:
        {"success": True, "image_id": "1", "gen_image_urls": [url, ...]}
        或 {"success": False, "message": "..."}
    """
    elapsed = 0
    attempt = 0

    while elapsed < timeout:
        time.sleep(interval)
        elapsed += interval
        attempt += 1
        logger.info("第 %d 次轮询图片生成结果（已等待 %d 秒），taskId=%s", attempt, elapsed, task_id)

        try:
            resp = api_post_raw(IMAGE_GEN_PATH, {"taskId": task_id})
        except Exception as e:
            logger.warning("第 %d 次图片生成轮询异常: %s", attempt, e)
            continue

        if resp.get("success") is False:
            continue

        data = resp.get("data") if isinstance(resp.get("data"), dict) else {}
        gen_urls = resp.get("gen_image_urls") or data.get("gen_image_urls")
        image_id = resp.get("image_id") or data.get("image_id")

        if isinstance(gen_urls, list) and any(u for u in gen_urls if u):
            valid_urls = [u for u in gen_urls if u]
            return {
                "success": True,
                "image_id": str(image_id) if image_id is not None else "",
                "gen_image_urls": valid_urls,
            }

    return {"success": False, "message": f"图片生成未完成（已等待 {elapsed} 秒），请稍后重试"}


def convert_image_urls(pic_urls: list) -> dict:
    """
    将 AI 生成的图片 URL 转换为商品可接受的图片银行链接。

    Returns:
        {"success": True, "images": [转换后的URL列表]}
        或 {"success": False, "message": "..."}
    """
    if not pic_urls or not isinstance(pic_urls, list):
        raise ParamError("图片URL列表不能为空")

    logger.info("转换图片链接，picUrls=%s", pic_urls)
    try:
        resp = api_post_raw(IMAGE_BANK_CONVERT_PATH, {"picUrl": pic_urls})
    except Exception as e:
        return {"success": False, "message": f"图片链接转换失败：{e}"}

    success = resp.get("success")
    model = resp.get("model")
    if success is None or model is None:
        data = resp.get("data", {})
        if isinstance(data, dict):
            if success is None:
                success = data.get("success")
            if model is None:
                model = data.get("model")

    if not success:
        msg = resp.get("msgInfo") or resp.get("msgCode") or "未知错误"
        return {"success": False, "message": f"图片链接转换失败：{msg}"}

    if not isinstance(model, list):
        return {"success": False, "message": "图片链接转换失败：响应格式异常"}

    images = []
    for item in model:
        if isinstance(item, dict):
            relative_url = item.get("relativeUrl")
            if relative_url:
                images.append(f"https://cbu01.alicdn.com/{relative_url}")

    if not images:
        return {"success": False, "message": "图片链接转换失败：未获取到有效链接"}

    return {"success": True, "images": images}


def change_main_image(offer_id: str, images: list) -> dict:
    """修改商品主图。"""
    if not offer_id:
        raise ParamError("商品ID不能为空")
    if not images or not isinstance(images, list):
        raise ParamError("主图列表不能为空")

    logger.info("修改商品主图，offerId=%s，images=%s", offer_id, images)
    resp = api_post_raw(CHANGE_MAIN_IMAGE_PATH, {"offerId": offer_id, "images": images})

    success = resp.get("success")
    if success is None:
        data = resp.get("data", {})
        if isinstance(data, dict):
            success = data.get("success")

    if success:
        return {"success": True, "message": "主图修改成功"}
    return {"success": False, "message": "主图修改失败"}
