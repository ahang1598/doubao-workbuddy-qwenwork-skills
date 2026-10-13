"""微信视频号数据类型定义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PublishVideoContent:
    """视频发布内容。"""

    title: str = ""
    video_path: str = ""
    tags: list[str] = field(default_factory=list)
    publish_date: datetime | None = None  # None 表示立即发布
    category: str | None = None  # 原创类型（如：生活、科技）
    is_original: bool = False
    is_draft: bool = False


@dataclass
class PublishImageContent:
    """图文发布内容。"""

    title: str = ""  # 图文标题，22 字符内
    description: str = ""  # 图文描述，1000 字符内
    image_paths: list[str] = field(default_factory=list)  # 图片路径列表，最多 18 张
    tags: list[str] = field(default_factory=list)
    publish_date: datetime | None = None  # None 表示立即发布
    is_draft: bool = False


@dataclass
class ActionResult:
    """通用动作响应。"""

    success: bool = False
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "message": self.message,
        }
