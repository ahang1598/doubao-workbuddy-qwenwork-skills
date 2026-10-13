"""微信视频号自动化异常体系。"""


class WCError(Exception):
    """微信视频号自动化基础异常。"""


class NotLoggedInError(WCError):
    """未登录。"""

    def __init__(self) -> None:
        super().__init__("未登录，请先微信扫码登录")


class CookieExpiredError(WCError):
    """Cookie 已过期。"""

    def __init__(self) -> None:
        super().__init__("Cookie 已过期，请重新扫码登录")


class UploadTimeoutError(WCError):
    """上传超时。"""


class PublishError(WCError):
    """发布失败。"""


class CDPError(WCError):
    """CDP 通信异常。"""


class ElementNotFoundError(WCError):
    """页面元素未找到。"""

    def __init__(self, selector: str) -> None:
        self.selector = selector
        super().__init__(f"未找到元素: {selector}")


class QRCodeTimeoutError(WCError):
    """二维码获取超时。"""

    def __init__(self) -> None:
        super().__init__("二维码获取超时，请重试")
