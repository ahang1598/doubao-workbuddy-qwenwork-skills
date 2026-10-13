"""
美团浏览器辅助工具。

封装 CDP 页面创建逻辑，统一应用移动设备配置（UA、屏幕尺寸等）。
"""

from services.browser.browser import launch_browser
from services.browser.cdp_client import CdpBrowser, CdpPage
from services.meituan.device_profiles import get_device_profile


def create_mobile_page(
    *,
    device_name: str = "iphone14",
    headless: bool = False,
) -> tuple[CdpBrowser, CdpPage]:
    """创建一个模拟移动设备的浏览器页面。

    通过 CDP 连接浏览器，并创建带有指定设备 UA、视口尺寸的新页面。

    Args:
        device_name: 设备名称，默认 "iphone14"
        headless: 是否无头模式

    Returns:
        (browser, page) 元组
    """
    profile = get_device_profile(device_name)
    browser = launch_browser(headless=headless)

    page = browser.new_page(
        user_agent=profile.user_agent,
        viewport={"width": profile.viewport_width, "height": profile.viewport_height},
        device_scale_factor=profile.device_scale_factor,
        is_mobile=profile.is_mobile,
        has_touch=profile.has_touch,
    )

    print(f"📱 已创建移动端页面 (设备: {profile.name})")
    print(f"   视口: {profile.viewport_width}x{profile.viewport_height}")
    return browser, page