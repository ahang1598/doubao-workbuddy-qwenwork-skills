#!/usr/bin/env python3
"""商品发布服务 — 图片压缩、图片银行上传、AI 识图、发品链接拼接"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import base64
import json
import logging
from typing import Optional
from io import BytesIO

from PIL import Image

from _errors import ParamError, ServiceError
from _http import api_post_raw

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('product_publish')


def compress_image_to_base64(image_path: str, max_size_bytes: int = 1_000_000) -> "tuple[str, str]":
    """
    压缩图片到 max_size_bytes 以内，返回 (base64_str, image_name)。

    算法：
    1. 验证文件路径存在且可访问
    2. 用 Pillow 打开图片
    3. 获取文件名（不含路径）作为 image_name
    4. 如果原始文件大小 <= max_size_bytes，直接读取原始文件并 base64 编码返回
    5. 否则将图片转为 RGB 模式（处理 RGBA/P 等格式）
    6. 逐步降低 JPEG quality（从 95 开始，每次 -5，最低到 10）
    7. 如仍超限，缩小分辨率（每次 width/height 乘 0.8），再从 quality=85 开始降，最多缩5轮
    8. 最终返回 base64 编码字符串和文件名
    """
    if not os.path.exists(image_path):
        raise ParamError(f"图片文件不存在: {image_path}")
    if not os.path.isfile(image_path):
        raise ParamError(f"路径不是文件: {image_path}")

    image_name = os.path.basename(image_path)
    logger.debug("开始压缩图片: %s", image_name)

    original_size = os.path.getsize(image_path)
    if original_size <= max_size_bytes:
        logger.debug("图片原始大小 %d 字节，未超过限制 %d 字节，直接读取", original_size, max_size_bytes)
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8"), image_name

    try:
        img = Image.open(image_path)
    except Exception as e:
        raise ServiceError(f"无法打开图片文件: {e}")

    if img.mode in ("RGBA", "P", "LA", "L", "I", "F", "YCbCr", "CMYK", "HSV"):
        logger.debug("图片模式为 %s，转换为 RGB", img.mode)
        img = img.convert("RGB")

    def _try_compress(image: Image.Image, start_quality: int) -> "Optional[tuple]":
        for quality in range(start_quality, 9, -5):
            buffer = BytesIO()
            try:
                image.save(buffer, format="JPEG", quality=quality, optimize=True)
            except Exception:
                logger.debug("JPEG 保存失败 (quality=%d)", quality)
                continue
            size = buffer.tell()
            if size <= max_size_bytes:
                logger.debug("压缩成功: quality=%d, 大小=%d 字节", quality, size)
                return buffer.getvalue(), quality
            logger.debug("quality=%d 时大小=%d 字节，仍超过限制", quality, size)
        return None

    result = _try_compress(img, 95)
    if result:
        encoded = base64.b64encode(result[0]).decode("utf-8")
        return encoded, image_name

    width, height = img.size
    for round_idx in range(1, 6):
        width = int(width * 0.8)
        height = int(height * 0.8)
        if width < 10 or height < 10:
            logger.debug("图片分辨率已缩至极限 (%dx%d)，终止缩放", width, height)
            break
        logger.debug("第 %d 轮缩放分辨率至 %dx%d", round_idx, width, height)
        resized = img.resize((width, height), Image.Resampling.LANCZOS)
        result = _try_compress(resized, 85)
        if result:
            encoded = base64.b64encode(result[0]).decode("utf-8")
            return encoded, image_name

    raise ServiceError(f"图片压缩失败，无法将 {image_name} 压缩到 {max_size_bytes} 字节以内")


def upload_image_to_bank(image_path: str) -> str:
    """
    本地图片 -> 压缩 -> base64 -> 上传图片银行 -> 返回完整图片 URL。
    """
    base64_str, image_name = compress_image_to_base64(image_path)
    logger.debug("上传图片到图片银行")

    resp = api_post_raw(
        "/api/image_bank_upload_picture/1.0.0",
        {"imageName": image_name, "base64Str": base64_str},
    )

    if resp.get("success") is False:
        msg = resp.get("msgInfo") or resp.get("msgCode") or "未知错误"
        raise ServiceError(f"图片银行上传失败: {msg}")

    data = resp.get("data", {}) if isinstance(resp.get("data"), dict) else {}
    model = data.get("model", {}) if isinstance(data.get("model"), dict) else {}
    relative_url = model.get("relativeUrl")
    if not relative_url:
        raise ServiceError("图片银行上传失败，请稍后重试")

    full_url = f"https://cbu01.alicdn.com/{relative_url}"
    logger.debug("图片银行上传成功")
    return full_url


def ai_publish_by_image(pic_url: str) -> dict:
    """
    图片链接 -> AI 识别同款商品。
    返回包含 categoryId、categoryName、tkItemIds、effectiveItemIds 的字典。
    """
    logger.debug("AI 识图分析图片")
    resp = api_post_raw("/api/ai_publish_by_imageurl/1.0.0", {"picUrl": pic_url})

    data_json_str = resp.get("dataJson") or (resp.get("data", {}) or {}).get("dataJson")
    if not data_json_str:
        logger.debug("AI 识图未返回有效数据，返回默认跳转链接")
        return {"redirect": "https://offer-new.1688.com/select.htm"}

    try:
        data = json.loads(data_json_str)
    except json.JSONDecodeError:
        raise ServiceError("AI 识图返回数据解析失败，请稍后重试")

    effective_items = []
    raw_effective = data.get("effectiveItemIds", [])
    if isinstance(raw_effective, list):
        for item in raw_effective:
            if isinstance(item, dict):
                effective_items.append({
                    "sameItemId": item.get("sameItemId"),
                    "sameItemTitle": item.get("sameItemTitle"),
                    "sameItemPicUrl": item.get("sameItemPicUrl"),
                    "sameItemSellerPoint": item.get("sameItemSellerPoint"),
                })

    result = {
        "categoryId": int(data.get("categoryId", 0)),
        "categoryName": str(data.get("categoryName", "")),
        "tkItemIds": data.get("tkItemIds", []),
        "effectiveItemIds": effective_items,
    }
    logger.debug("AI 识图成功")
    return result


def ai_publish_save(
    pic_url: str,
    category_id: int,
    category_name: str,
    tk_item_ids: list,
    absolute_same_item_id: str,
    absolute_same_item_title: str,
) -> str:
    """
    保存用户选品数据，返回 aigcSelectCategoryTime。
    """
    logger.debug("保存 AI 选品数据")
    resp = api_post_raw(
        "/api/ai_publish_save_tair/1.0.0",
        {
            "picUrl": pic_url,
            "categoryId": category_id,
            "categoryName": category_name,
            "tkItemIds": tk_item_ids,
            "absoluteSameItemId": absolute_same_item_id,
            "absoluteSameItemTitle": absolute_same_item_title,
        },
    )

    data_json_str = resp.get("dataJson") or (resp.get("data", {}) or {}).get("dataJson")
    if not data_json_str:
        raise ServiceError("保存选品数据失败，请稍后重试")

    try:
        data = json.loads(data_json_str)
    except json.JSONDecodeError:
        raise ServiceError("保存选品数据失败，请稍后重试")

    aigc_time = data.get("aigcSelectCategoryTime")
    if not aigc_time:
        raise ServiceError("保存选品数据失败，请稍后重试")

    logger.debug("选品数据保存成功")
    return str(aigc_time)


def build_publish_url(aigc_time: str, cat_id: int) -> str:
    """
    拼接发品跳转链接。
    """
    url = (
        f"https://offer-new.1688.com/aigc/publish.htm"
        f"?operator=new&scene=effectiveType"
        f"&aigcSelectCategoryTime={aigc_time}&catId={cat_id}"
    )
    logger.debug("生成发品链接")
    return url

