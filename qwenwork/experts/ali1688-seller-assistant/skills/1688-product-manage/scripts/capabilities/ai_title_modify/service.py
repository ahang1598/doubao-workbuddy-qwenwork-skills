#!/usr/bin/env python3
"""AI 标题修改服务 — 商品信息查询、图片解析、修改商品标题"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import json, time, logging
from typing import Optional
from _errors import ParamError, ServiceError
from _http import api_post_raw

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ai_title_modify')

# 商品查询接口
OFFER_QUERY_PATH = "/api/cbu_offer_query_tool/1.0.0"
# 图片解析接口（提交任务与轮询结果共用）
IMAGE_ANALYSE_PATH = "/api/cbu_image_analyse_tool/1.0.0"
# 商品标题修改接口
CHANGE_SUBJECT_PATH = "/api/cbu_skill_change_subject/1.0.0"
# 图片解析任务类型（固定字段）
IMAGE_PARSE_TYPE = "ecommerce_content_parsing"
# 标题长度上限（中文=1字符，英文/数字/半角符号=0.5字符）
TITLE_MAX_LENGTH = 30


def calc_title_length(title: str) -> float:
    """计算标题长度：中文=1字符，英文/数字/半角符号=0.5字符"""
    length = 0.0
    for ch in title:
        if ord(ch) > 127:  # 非 ASCII 字符（中文、全角符号等）
            length += 1.0
        else:  # ASCII 字符（英文、数字、半角符号）
            length += 0.5
    return length


def query_offer_info(offer_id: str) -> dict:
    """
    查询商品基础信息（标题 + 主图列表）。

    Args:
        offer_id: 商品ID

    Returns:
        {"title": "...", "images": ["url1", "url2", ...]}

    Raises:
        ParamError / ServiceError
    """
    if not offer_id:
        raise ParamError("商品ID不能为空")

    logger.info("查询商品基础信息，offerId=%s", offer_id)
    resp = api_post_raw(OFFER_QUERY_PATH, {"offerId": offer_id})
    logger.info("商品信息响应: %s", json.dumps(resp, ensure_ascii=False, default=str)[:500])

    if resp.get("success") is False:
        raise ServiceError("商品信息查询失败")

    # 允许字段位于顶层或嵌套在 data 中
    data = resp.get("data") if isinstance(resp.get("data"), dict) else {}
    title = resp.get("title") or data.get("title") or ""
    images = resp.get("images") or data.get("images") or []
    if not isinstance(images, list):
        images = []

    if not title and not images:
        raise ServiceError("未获取到商品标题与主图，请检查商品ID")

    return {"title": title, "images": images}


def submit_image_parse(image_url: str) -> str:
    """
    提交图片解析任务。

    Args:
        image_url: 主图 URL（仅传第一张主图）

    Returns:
        taskId 字符串

    Raises:
        ParamError / ServiceError
    """
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

    logger.info("获取到图片解析 taskId=%s", task_id)
    return str(task_id)


def poll_image_parse_result(task_id: str, timeout: int = 30, interval: int = 3) -> dict:
    """
    轮询图片解析结果。

    Args:
        task_id: 图片解析任务 ID
        timeout: 最大等待秒数（默认 30 秒）
        interval: 轮询间隔秒数（默认 3 秒）

    Returns:
        {
            "success": True,
            "text_region_summary": "...",
            "selling_points_visible": [...],
            "composition_summary": "..."
        }
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
            logger.info("图片解析结果响应: %s", json.dumps(resp, ensure_ascii=False, default=str)[:500])
        except Exception as e:
            logger.warning("第 %d 次图片解析轮询异常: %s", attempt, e)
            continue

        if resp.get("success") is False:
            continue

        # 允许字段位于顶层或嵌套在 data 中
        data = resp.get("data") if isinstance(resp.get("data"), dict) else {}
        # 关键字段：text_region_summary / selling_points_visible / composition_summary
        text_summary = resp.get("text_region_summary") or data.get("text_region_summary")
        selling_points = resp.get("selling_points_visible") or data.get("selling_points_visible")
        composition = resp.get("composition_summary") or data.get("composition_summary")

        if text_summary or selling_points or composition:
            logger.info("图片解析完成（耗时 %d 秒）", elapsed)
            return {
                "success": True,
                "text_region_summary": text_summary or "",
                "selling_points_visible": selling_points or [],
                "composition_summary": composition or "",
            }

    logger.warning("图片解析轮询超时（共等待 %d 秒）", elapsed)
    return {"success": False, "message": f"图片解析未完成（已等待 {elapsed} 秒），请稍后重试"}


def change_subject(offer_id: str, subject: str) -> dict:
    """
    修改商品标题。

    Args:
        offer_id: 商品ID
        subject: 新标题

    Returns:
        {"success": True/False, "message": "..."}
    """
    if not offer_id:
        raise ParamError("商品ID不能为空")
    if not subject:
        raise ParamError("标题不能为空")

    logger.info("修改商品标题，offerId=%s，subject=%s", offer_id, subject)
    resp = api_post_raw(CHANGE_SUBJECT_PATH, {"offerId": offer_id, "subject": subject})

    success = resp.get("success")
    if success is None:
        data = resp.get("data", {})
        if isinstance(data, dict):
            success = data.get("success")

    if success:
        logger.info("标题修改成功")
        return {"success": True, "message": "标题修改成功"}
    else:
        logger.warning("标题修改失败，响应: %s", resp)
        return {"success": False, "message": "标题修改失败"}
