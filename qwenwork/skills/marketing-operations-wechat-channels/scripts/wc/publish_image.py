"""微信视频号图文发布。"""

from __future__ import annotations

import json
import logging
import os
import time

from .cdp import Page
from .errors import PublishError, UploadTimeoutError
from .human import sleep_random
from .selectors import (
    IMAGE_DESC_INPUT,
    IMAGE_FILE_INPUT,
    IMAGE_TITLE_INPUT,
    PUBLISH_BUTTON,
    PUBLISH_BUTTON_DISABLED_CLASS,
    SCHEDULE_DATE_INPUT,
    SCHEDULE_DATE_PICKER,
    SCHEDULE_LABEL_TEXT,
    SCHEDULE_MONTH_LABEL,
    SCHEDULE_NEXT_MONTH,
    SCHEDULE_TIME_INPUT,
)
from .types import PublishImageContent
from .urls import IMAGE_POST_LIST_URL, PUBLISH_IMAGE_URL

logger = logging.getLogger(__name__)

MAX_IMAGE_COUNT = 18
MAX_IMAGE_SIZE_MB = 20


def publish_image_content(page: Page, content: PublishImageContent) -> None:
    """发布图文内容（填写表单 + 点击发布/草稿）。"""
    fill_publish_image_form(page, content)
    if content.is_draft:
        _click_save_draft(page)
    else:
        _click_publish_button(page)


def fill_publish_image_form(page: Page, content: PublishImageContent) -> None:
    """填写图文发布表单，不点击发布按钮。"""
    if not content.image_paths:
        raise PublishError("图片不能为空")

    _validate_images(content.image_paths)

    # 导航到图文发布页
    page.navigate(PUBLISH_IMAGE_URL)
    page.wait_for_load()
    sleep_random(2000, 3000)

    # 等待 iframe 内容加载完成
    _wait_for_iframe_ready(page)

    # 上传图片
    _upload_images(page, content.image_paths)

    # 填写标题
    if content.title:
        _fill_title(page, content.title)

    # 填写描述和话题
    _fill_description(page, content.description, content.tags)

    # 定时发布
    if content.publish_date:
        _set_schedule_time(page, content.publish_date)

    logger.info("图文表单填写完成，等待确认发布")


def _validate_images(image_paths: list[str]) -> None:
    """校验图片文件。"""
    if len(image_paths) > MAX_IMAGE_COUNT:
        raise PublishError(f"图片数量超过限制：最多 {MAX_IMAGE_COUNT} 张，当前 {len(image_paths)} 张")

    for path in image_paths:
        if not os.path.exists(path):
            raise PublishError(f"图片文件不存在: {path}")
        size_mb = os.path.getsize(path) / (1024 * 1024)
        if size_mb > MAX_IMAGE_SIZE_MB:
            raise PublishError(f"图片文件过大: {path} ({size_mb:.1f}MB > {MAX_IMAGE_SIZE_MB}MB)")


def _wait_for_iframe_ready(page: Page, timeout: float = 15.0) -> None:
    """等待 iframe 内容加载完成。

    图文发布页面的内容在 iframe 内，导航后需要等待 iframe 加载完成。
    通过检查 iframe 内是否存在图片 file input 来判断加载状态。
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        element_object_id = page._find_element_in_iframes(IMAGE_FILE_INPUT)
        if element_object_id:
            logger.info("iframe 内容已加载完成")
            return
        time.sleep(1.0)
    logger.warning("等待 iframe 加载超时 (%.0fs)", timeout)


def _upload_images(page: Page, image_paths: list[str]) -> None:
    """上传图片文件。

    通过 CDP DOM.setFileInputFiles 一次性设置多个文件。
    """
    page.set_file_input(IMAGE_FILE_INPUT, image_paths)
    logger.info("已选择 %d 张图片", len(image_paths))
    sleep_random(2000, 3000)

    # 等待图片上传完成（图片上传比视频快得多，但仍需等待）
    _wait_for_images_uploaded(page, len(image_paths))


def _wait_for_images_uploaded(page: Page, expected_count: int) -> None:
    """等待图片上传完成。

    通过检查发表按钮是否可点击来判断上传状态。
    图片上传比视频处理快得多，通常几秒内完成。
    """
    max_wait = 120.0
    start = time.monotonic()

    logger.info("等待图片上传完成...")

    while time.monotonic() - start < max_wait:
        clickable = page.evaluate_in_iframe(
            f"""
            (() => {{
                const btn = document.querySelector({json.dumps(PUBLISH_BUTTON)});
                if (!btn) {{
                    const buttons = document.querySelectorAll('button');
                    for (const b of buttons) {{
                        if (b.textContent && b.textContent.includes('发表')) {{
                            return !b.disabled
                                && !b.className.includes(
                                    {json.dumps(PUBLISH_BUTTON_DISABLED_CLASS)}
                                );
                        }}
                    }}
                    return false;
                }}
                return !btn.disabled
                    && !btn.className.includes({json.dumps(PUBLISH_BUTTON_DISABLED_CLASS)});
            }})()
            """
        )
        if clickable:
            logger.info("图片上传完成")
            return

        sleep_random(1000, 2000)

    raise UploadTimeoutError("等待图片上传超时(2分钟)")


def _fill_title(page: Page, title: str) -> None:
    """填写图文标题。

    图文标题是普通 <input> 元素，需要通过 nativeInputValueSetter 设置值。
    """
    truncated_title = title[:22]

    fill_title_js = f"""
    (() => {{
        const input = document.querySelector({json.dumps(IMAGE_TITLE_INPUT)});
        if (!input) return false;
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value'
        ).set;
        nativeInputValueSetter.call(input, {json.dumps(truncated_title)});
        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
        return true;
    }})()
    """
    result = page.evaluate_in_iframe(fill_title_js)
    if result:
        logger.info("图文标题已填充: %s", truncated_title)
    else:
        logger.warning("未找到图文标题输入框")


def _fill_description(page: Page, description: str, tags: list[str]) -> None:
    """填写图文描述和话题标签。"""
    page.click_element(IMAGE_DESC_INPUT)
    sleep_random(300, 500)

    if description:
        page.type_text(description)

    if tags:
        if description:
            page.press_key("Enter")
        for tag in tags:
            page.type_text("#" + tag)
            sleep_random(300, 500)
            page.press_key("Space")
            sleep_random(200, 400)
        logger.info("成功添加 %d 个话题标签", len(tags))


def _set_schedule_time(page: Page, publish_date) -> None:
    """设置定时发布时间。"""
    from datetime import datetime

    if not isinstance(publish_date, datetime):
        return

    # 点击"定时"标签
    schedule_js = f"""
    (() => {{
        const labels = document.querySelectorAll('label');
        for (const label of labels) {{
            if (label.textContent && label.textContent.includes(
                {json.dumps(SCHEDULE_LABEL_TEXT)}
            )) {{
                label.click();
                return true;
            }}
        }}
        return false;
    }})()
    """
    page.evaluate_in_iframe(schedule_js)
    sleep_random(500, 800)

    # 点击日期选择器
    page.click_element(SCHEDULE_DATE_INPUT)
    sleep_random(500, 800)

    # 检查月份是否需要切换
    str_month = f"{publish_date.month:02d}月"
    page_month = page.get_element_text(SCHEDULE_MONTH_LABEL) or ""

    if str_month not in page_month:
        page.click_element(SCHEDULE_NEXT_MONTH)
        sleep_random(300, 500)

    # 选择日期
    select_date_js = f"""
    (() => {{
        const cells = document.querySelectorAll({json.dumps(SCHEDULE_DATE_PICKER)});
        for (const cell of cells) {{
            if (cell.className && cell.className.includes('disabled')) continue;
            if (cell.textContent && cell.textContent.trim() === {json.dumps(str(publish_date.day))}) {{
                cell.click();
                return true;
            }}
        }}
        return false;
    }})()
    """
    page.evaluate_in_iframe(select_date_js)
    sleep_random(500, 800)

    # 设置时间
    page.click_element(SCHEDULE_TIME_INPUT)
    sleep_random(200, 400)

    select_all_js = """
    (() => {
        const input = document.activeElement;
        if (input && input.select) input.select();
    })()
    """
    page.evaluate_in_iframe(select_all_js)
    page.type_text(str(publish_date.hour))
    sleep_random(300, 500)

    # 回点描述框使定时生效
    page.click_element(IMAGE_DESC_INPUT)
    sleep_random(300, 500)

    logger.info("定时发布已设置: %s", publish_date)


def _click_publish_button(page: Page) -> None:
    """点击发表按钮。"""
    _wait_for_publish_button_clickable(page)

    page.click_element(PUBLISH_BUTTON)
    sleep_random(2000, 3000)

    # 等待跳转到图文列表页面
    _wait_for_publish_complete(page)
    logger.info("图文发布完成")


def _click_save_draft(page: Page) -> None:
    """点击保存草稿按钮。"""
    clicked = page.evaluate_in_iframe(
        """
        (() => {
            const buttons = document.querySelectorAll('div.form-btns button');
            for (const btn of buttons) {
                if (btn.textContent && btn.textContent.trim() === '保存草稿') {
                    btn.click();
                    return true;
                }
            }
            return false;
        })()
        """
    )
    if clicked:
        sleep_random(2000, 3000)
        logger.info("图文草稿保存成功")
    else:
        raise PublishError("未找到保存草稿按钮")


def _wait_for_publish_button_clickable(page: Page) -> None:
    """等待发布按钮可点击。"""
    max_wait = 120.0
    start = time.monotonic()

    while time.monotonic() - start < max_wait:
        clickable = page.evaluate_in_iframe(
            f"""
            (() => {{
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {{
                    if (btn.textContent && btn.textContent.includes('发表')) {{
                        return !btn.disabled
                            && !btn.className.includes(
                                {json.dumps(PUBLISH_BUTTON_DISABLED_CLASS)}
                            );
                    }}
                }}
                return false;
            }})()
            """
        )
        if clickable:
            return
        sleep_random(1000, 2000)

    raise UploadTimeoutError("等待发布按钮可点击超时")


def _wait_for_publish_complete(page: Page) -> None:
    """等待发布完成（页面跳转到图文列表）。"""
    max_wait = 30.0
    start = time.monotonic()

    while time.monotonic() - start < max_wait:
        current_url = page.evaluate("window.location.href") or ""
        if IMAGE_POST_LIST_URL in current_url or "finderNewLifePostList" in current_url:
            logger.info("图文发布成功")
            return
        sleep_random(500, 1000)

    logger.warning("发布后未检测到页面跳转，可能已发布成功")
