"""
移动设备配置。

定义浏览器模拟移动设备时所需的 UA、屏幕尺寸等参数。
支持扩展更多设备型号。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceProfile:
    """移动设备配置描述。"""
    name: str
    user_agent: str
    viewport_width: int
    viewport_height: int
    device_scale_factor: float
    is_mobile: bool
    has_touch: bool


IPHONE_14 = DeviceProfile(
    name="iPhone 14",
    user_agent=(
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/16.0 Mobile/15E148 Safari/604.1"
    ),
    viewport_width=390,
    viewport_height=844,
    device_scale_factor=3.0,
    is_mobile=True,
    has_touch=True,
)

# 可扩展更多设备
DEVICE_REGISTRY: dict[str, DeviceProfile] = {
    "iphone14": IPHONE_14,
}


def get_device_profile(device_name: str = "iphone14") -> DeviceProfile:
    """根据设备名称获取配置，默认 iPhone 14。"""
    profile = DEVICE_REGISTRY.get(device_name.lower())
    if not profile:
        available = ", ".join(DEVICE_REGISTRY.keys())
        raise ValueError(f"未知设备: {device_name}，可选: {available}")
    return profile
