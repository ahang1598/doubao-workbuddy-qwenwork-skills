"""微信视频号登录管理。"""

from __future__ import annotations

import base64
import logging
import os
import tempfile
import time

from .cdp import Page
from .human import sleep_random
from .selectors import (
    LOGGED_IN_INDICATOR,
    LOGIN_PAGE_INDICATOR,
    QRCODE_IMG,
)
from .urls import HOME_URL, PUBLISH_URL

logger = logging.getLogger(__name__)


def check_login_status(page: Page) -> bool:
    """检查登录状态。

    导航到创作者中心发布页面，检测是否已登录。
    页面内容在 iframe 内，CSS 选择器无法直接查到，改用以下策略：
    1. URL 判断：被重定向到 login/passport 说明未登录
    2. 页面文本判断：已登录页面包含导航菜单关键词（内容管理、数据中心等）

    Returns:
        True 已登录，False 未登录。
    """
    page.navigate(PUBLISH_URL)
    page.wait_for_load()
    sleep_random(2000, 3000)

    # 检查是否被重定向到登录页面
    current_url = page.evaluate("window.location.href") or ""
    if "login" in current_url or "passport" in current_url:
        logger.info("未登录：URL 包含 login/passport")
        return False

    # 通过页面可见文本判断：已登录的创作者中心包含导航菜单
    body_text = page.evaluate("document.body.innerText") or ""
    logged_in_keywords = ["内容管理", "数据中心", "互动管理"]
    if any(kw in body_text for kw in logged_in_keywords):
        logger.info("已登录：页面包含创作者中心导航菜单")
        return True

    # 兜底：检查是否出现登录页面特征文字
    login_keywords = ["微信小店", "扫码登录", "手机号登录"]
    if any(kw in body_text for kw in login_keywords):
        logger.info("未登录：页面包含登录页特征文字")
        return False

    logger.warning("无法判断登录状态，body_text 前200字: %s", body_text[:200])
    return False


def fetch_qrcode(page: Page) -> tuple[str, bool]:
    """获取登录二维码。

    Returns:
        (qrcode_src, already_logged_in)
        - 如果已登录，返回 ("", True)
        - 如果未登录，返回 (qrcode_src, False)
    """
    page.navigate(HOME_URL)
    page.wait_for_load()
    sleep_random(2000, 3500)

    # 检查是否已登录
    if page.has_element(LOGGED_IN_INDICATOR):
        return "", True

    # 等待二维码出现
    page.wait_for_element(QRCODE_IMG, timeout=15.0)
    sleep_random(500, 1000)

    # 获取二维码图片 src
    src = page.get_element_attribute(QRCODE_IMG, "src")
    if not src:
        # 尝试备用选择器
        src = page.evaluate(
            """
            (() => {
                const imgs = document.querySelectorAll('img');
                for (const img of imgs) {
                    if (img.src && (img.src.includes('qrcode') || img.src.startsWith('data:image'))) {
                        return img.src;
                    }
                }
                return null;
            })()
            """
        )
    if not src:
        raise RuntimeError("二维码图片 src 为空")

    return src, False


def save_qrcode_to_file(src: str) -> str:
    """将二维码 data URL 保存为临时 PNG 文件。

    Args:
        src: 二维码图片的 data URL（data:image/png;base64,...）或普通 URL。

    Returns:
        保存的文件绝对路径。
    """
    prefix = "data:image/png;base64,"
    if src.startswith(prefix):
        img_data = base64.b64decode(src[len(prefix):])
    elif src.startswith("data:image/"):
        _, encoded = src.split(",", 1)
        img_data = base64.b64decode(encoded)
    else:
        raise ValueError(f"不支持的二维码格式，需要 data URL: {src[:50]}...")

    qr_dir = os.path.join(tempfile.gettempdir(), "wechat-channels")
    os.makedirs(qr_dir, exist_ok=True)
    filepath = os.path.join(qr_dir, "login_qrcode.png")

    with open(filepath, "wb") as f:
        f.write(img_data)

    logger.info("二维码已保存: %s", filepath)
    return filepath


def check_scan_status(page: Page) -> dict:
    """检查扫码后的页面状态。

    当用户告知已完成扫码后调用。

    Returns:
        dict: 已登录时 {"logged_in": True, "message": str}；
              仍在等待扫码时 {"waiting_scan": True, "message": str}。
    """
    sleep_random(1000, 2000)

    # 检查是否已登录（页面跳转到创作者中心）
    current_url = page.evaluate("window.location.href") or ""
    if "platform" in current_url:
        logger.info("登录成功")
        return {"logged_in": True, "message": "登录成功"}

    if page.has_element(LOGGED_IN_INDICATOR):
        logger.info("登录成功")
        return {"logged_in": True, "message": "登录成功"}

    return {
        "waiting_scan": True,
        "message": "仍在等待扫码，请使用微信扫描二维码后再次执行 check-scan-status",
    }


def wait_for_login(page: Page, timeout: float = 120.0) -> bool:
    """等待扫码登录完成。

    Args:
        page: CDP 页面对象。
        timeout: 超时时间（秒）。

    Returns:
        True 登录成功，False 超时。
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current_url = page.evaluate("window.location.href") or ""
        if "platform" in current_url:
            logger.info("登录成功")
            return True
        if page.has_element(LOGGED_IN_INDICATOR):
            logger.info("登录成功")
            return True
        time.sleep(1)
    return False
