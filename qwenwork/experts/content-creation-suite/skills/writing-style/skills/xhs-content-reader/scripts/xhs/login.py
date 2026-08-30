"""登录管理，对应 Go xiaohongshu/login.go。"""

from __future__ import annotations

import base64
import logging
import os
import tempfile
import time

from .cdp import Page
from .errors import RateLimitError
from .human import sleep_random
from .selectors import (
    AGREE_CHECKBOX,
    AGREE_CHECKBOX_CHECKED,
    CODE_INPUT,
    GET_CODE_BUTTON,
    LOGIN_CONTAINER,
    LOGIN_ERR_MSG,
    LOGIN_STATUS,
    LOGOUT_MENU_ITEM,
    LOGOUT_MORE_BUTTON,
    PHONE_INPUT,
    PHONE_LOGIN_SUBMIT,
    QRCODE_IMG,
)
from .urls import EXPLORE_URL

logger = logging.getLogger(__name__)


def check_login_status(page: Page) -> bool:
    """检查登录状态。

    Returns:
        True 已登录，False 未登录。
    """
    page.navigate(EXPLORE_URL)
    page.wait_for_load()
    sleep_random(800, 1500)

    return page.has_element(LOGIN_STATUS)


def fetch_qrcode(page: Page) -> tuple[str, bool]:
    """获取登录二维码。

    Returns:
        (qrcode_src, already_logged_in)
        - 如果已登录，返回 ("", True)
        - 如果未登录，返回 (qrcode_base64_or_url, False)
    """
    page.navigate(EXPLORE_URL)
    page.wait_for_load()
    sleep_random(1500, 2500)

    # 检查是否已登录
    if page.has_element(LOGIN_STATUS):
        return "", True

    # 获取二维码图片 src
    src = page.get_element_attribute(QRCODE_IMG, "src")
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
        img_data = base64.b64decode(src[len(prefix) :])
    elif src.startswith("data:image/"):
        # 处理其他 MIME 类型，如 data:image/jpeg;base64,...
        _, encoded = src.split(",", 1)
        img_data = base64.b64decode(encoded)
    else:
        # 不是 data URL，无法保存
        raise ValueError(f"不支持的二维码格式，需要 data URL: {src[:50]}...")

    qr_dir = os.path.join(tempfile.gettempdir(), "xhs")
    os.makedirs(qr_dir, exist_ok=True)
    filepath = os.path.join(qr_dir, "login_qrcode.png")

    with open(filepath, "wb") as f:
        f.write(img_data)

    logger.info("二维码已保存: %s", filepath)
    return filepath


def send_phone_code(page: Page, phone: str) -> bool:
    """填写手机号并发送短信验证码。

    适用于无界面服务器场景，全程通过 CDP 操作，无需扫码。

    Args:
        page: CDP 页面对象。
        phone: 手机号（不含国家码，如 13800138000）。

    Returns:
        True 验证码已发送，False 已登录（无需再登录）。

    Raises:
        RuntimeError: 找不到登录表单或手机号输入框。
    """
    page.navigate(EXPLORE_URL)
    page.wait_for_load()
    sleep_random(1500, 2500)

    if page.has_element(LOGIN_STATUS):
        return False

    # 等待登录弹窗出现
    page.wait_for_element(LOGIN_CONTAINER, timeout=15.0)
    sleep_random(500, 800)

    # 点击手机号输入框并逐字输入
    page.click_element(PHONE_INPUT)
    sleep_random(200, 400)
    page.type_text(phone, delay_ms=80)
    sleep_random(500, 800)

    # 先勾选用户协议，再点获取验证码
    if not page.has_element(AGREE_CHECKBOX_CHECKED):
        page.click_element(AGREE_CHECKBOX)
        sleep_random(300, 600)

    # 点击"获取验证码"
    page.click_element(GET_CODE_BUTTON)
    sleep_random(2000, 2500)

    # 检测按钮是否变为倒计时（成功发送后按钮文字会包含数字秒数）
    btn_text = page.get_element_text(GET_CODE_BUTTON) or ""
    if not any(ch.isdigit() for ch in btn_text):
        raise RateLimitError()

    logger.info("验证码已发送至 %s", phone[:3] + "****" + phone[-4:])
    return True


def submit_phone_code(page: Page, code: str) -> bool:
    """填写短信验证码并提交登录。

    Args:
        page: CDP 页面对象。
        code: 收到的短信验证码。

    Returns:
        True 登录成功，False 失败（超时或验证码错误）。
    """
    # 点击验证码输入框并逐字输入
    page.click_element(CODE_INPUT)
    sleep_random(300, 500)
    page.type_text(code, delay_ms=100)
    sleep_random(500, 800)

    # 点击登录按钮
    page.click_element(PHONE_LOGIN_SUBMIT)
    sleep_random(1000, 2000)

    # 检查是否有错误提示
    err = page.get_element_text(LOGIN_ERR_MSG)
    if err and err.strip():
        logger.warning("登录失败: %s", err.strip())
        return False

    return wait_for_login(page, timeout=30.0)


def logout(page: Page) -> bool:
    """通过页面 UI 退出登录（点击"更多"→"退出登录"）。

    Args:
        page: CDP 页面对象。

    Returns:
        True 退出成功，False 未登录或操作失败。
    """
    page.navigate(EXPLORE_URL)
    page.wait_for_load()
    sleep_random(800, 1500)

    if not page.has_element(LOGIN_STATUS):
        logger.info("当前未登录，无需退出")
        return False

    # 点击"更多"按钮展开菜单
    page.click_element(LOGOUT_MORE_BUTTON)
    sleep_random(500, 800)

    # 等待退出菜单项出现并点击
    page.wait_for_element(LOGOUT_MENU_ITEM, timeout=5.0)
    page.click_element(LOGOUT_MENU_ITEM)
    sleep_random(1000, 1500)

    logger.info("已退出登录")
    return True


def check_scan_status(page: Page) -> dict:
    """检查扫码后的页面状态。

    当用户告知已完成扫码后调用。若已登录则返回成功；若出现验证码输入框（部分场景），
    则返回 need_verify_code 提示用户执行 verify-code。

    Args:
        page: CDP 页面对象。

    Returns:
        dict: 已登录时 {"logged_in": True, "message": str}；
              需验证码时 {"need_verify_code": True, "message": str, "next_step": str}；
              仍在等待扫码时 {"waiting_scan": True, "message": str}。
    """
    sleep_random(500, 800)

    if page.has_element(LOGIN_STATUS):
        logger.info("登录成功")
        return {"logged_in": True, "message": "登录成功"}

    # 若已出现验证码输入框（扫码后触发二次验证）
    if page.has_element(CODE_INPUT):
        return {
            "need_verify_code": True,
            "message": "已扫码，需输入短信验证码完成验证",
            "next_step": "获取验证码后执行 verify-code --code <验证码>",
        }

    return {
        "waiting_scan": True,
        "message": "仍在等待扫码，请使用小红书 App 或微信扫描二维码后再次执行 check-scan-status",
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
        if page.has_element(LOGIN_STATUS):
            logger.info("登录成功")
            return True
        time.sleep(0.5)
    return False
