"""微信视频号视频发布。"""

from __future__ import annotations

import json
import logging
import os
import time

from .cdp import Page
from .errors import PublishError, UploadTimeoutError
from .human import sleep_random
from .selectors import (
    COLLECTION_LABEL,
    COLLECTION_OPTIONS,
    DELETE_CONFIRM_BUTTON,
    DRAFT_BUTTON,
    FILE_INPUT,
    ORIGINAL_AGREEMENT,
    ORIGINAL_CHECKBOX,
    ORIGINAL_CHECKBOX_NEW,
    ORIGINAL_DECLARE_BUTTON,
    ORIGINAL_DECLARE_BUTTON_NEW,
    ORIGINAL_DIALOG_CHECKBOX,
    ORIGINAL_LABEL_NEW,
    ORIGINAL_TYPE_DROPDOWN,
    ORIGINAL_TYPE_FORM,
    ORIGINAL_TYPE_OPTION,
    PUBLISH_BUTTON,
    PUBLISH_BUTTON_DISABLED_CLASS,
    SCHEDULE_DATE_INPUT,
    SCHEDULE_DATE_PICKER,
    SCHEDULE_LABEL_TEXT,
    SCHEDULE_MONTH_LABEL,
    SCHEDULE_NEXT_MONTH,
    SCHEDULE_TIME_INPUT,
    SHORT_TITLE_INPUT,
    SHORT_TITLE_LABEL,
    TITLE_INPUT,
    UPLOAD_DELETE_TAG,
    UPLOAD_ERROR,
)
from .types import PublishVideoContent
from .urls import POST_LIST_URL, PUBLISH_URL

logger = logging.getLogger(__name__)


def format_short_title(origin_title: str) -> str:
    """从标题生成 6-16 字的短标题。"""
    allowed_special_chars = "《》"":+?%°"
    filtered_chars = [
        char if char.isalnum() or char in allowed_special_chars
        else ' ' if char == ','
        else ''
        for char in origin_title
    ]
    formatted = ''.join(filtered_chars)

    if len(formatted) > 16:
        formatted = formatted[:16]
    elif len(formatted) < 6:
        formatted += ' ' * (6 - len(formatted))

    return formatted


def publish_video_content(page: Page, content: PublishVideoContent) -> None:
    """发布视频内容（填写表单 + 点击发布/草稿）。"""
    fill_publish_video_form(page, content)
    if content.is_draft:
        click_save_draft(page)
    else:
        click_publish_button(page)


def fill_publish_video_form(page: Page, content: PublishVideoContent) -> None:
    """填写视频发布表单，不点击发布按钮。"""
    if not content.video_path:
        raise PublishError("视频不能为空")

    # 导航到发布页（重复导航到同一页面是安全的）
    page.navigate(PUBLISH_URL)
    page.wait_for_load()
    sleep_random(2000, 3000)

    # 上传视频
    _upload_video(page, content.video_path)

    # 填写标题和话题
    _add_title_tags(page, content.title, content.tags)

    # 合集
    _add_collection(page)

    # 原创声明
    if content.is_original:
        _add_original(page, content.category)

    # 等待视频处理完成
    _detect_upload_status(page)

    # 定时发布
    if content.publish_date:
        _set_schedule_time(page, content.publish_date)

    # 短标题
    _add_short_title(page, content.title)

    logger.info("视频表单填写完成，等待确认发布")


def click_publish_button(page: Page) -> None:
    """点击发表按钮。"""
    _wait_for_publish_button_clickable(page)

    page.click_element(PUBLISH_BUTTON)
    sleep_random(2000, 3000)

    # 等待跳转到发布列表页面
    _wait_for_publish_complete(page)
    logger.info("视频发布完成")


def click_save_draft(page: Page) -> None:
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
        logger.info("视频草稿保存成功")
    else:
        raise PublishError("未找到保存草稿按钮")


def _wait_for_iframe_ready(page: Page, timeout: float = 15.0) -> None:
    """等待 iframe 内容加载完成。

    视频号发布页面的内容在 iframe 内，导航后需要等待 iframe 加载完成。
    通过检查 iframe 内是否存在 file input 来判断加载状态。
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        el_obj_id = page._find_element_in_iframes(FILE_INPUT)
        if el_obj_id:
            logger.info("iframe 内容已加载完成")
            return
        time.sleep(1.0)
    logger.warning("等待 iframe 加载超时 (%.0fs)", timeout)


def _upload_video(page: Page, video_path: str) -> None:
    """上传视频文件。"""
    if not os.path.exists(video_path):
        raise PublishError(f"视频文件不存在: {video_path}")

    # 等待 iframe 内容加载完成（file input 在 iframe 内）
    _wait_for_iframe_ready(page)

    page.set_file_input(FILE_INPUT, [video_path])
    logger.info("视频文件已选择: %s", video_path)
    sleep_random(2000, 3000)


def _add_title_tags(page: Page, title: str, tags: list[str]) -> None:
    """填充标题和话题标签。"""
    page.click_element(TITLE_INPUT)
    sleep_random(300, 500)
    page.type_text(title)

    if tags:
        page.press_key("Enter")
        for tag in tags:
            page.type_text("#" + tag)
            sleep_random(300, 500)
            page.press_key("Space")
            sleep_random(200, 400)
        logger.info("成功添加 %d 个话题标签", len(tags))


def _add_short_title(page: Page, title: str) -> None:
    """自动生成并填充短标题。"""
    # 查找短标题输入框
    short_title_js = f"""
    (() => {{
        const labels = document.querySelectorAll('*');
        for (const el of labels) {{
            if (el.textContent && el.textContent.trim() === {json.dumps(SHORT_TITLE_LABEL)}) {{
                const parent = el.closest('div') || el.parentElement;
                if (parent) {{
                    const input = parent.querySelector('input[type="text"]')
                        || parent.nextElementSibling?.querySelector('input[type="text"]');
                    if (input) return true;
                }}
            }}
        }}
        return false;
    }})()
    """
    has_short_title = page.evaluate_in_iframe(short_title_js)
    if has_short_title:
        short_title = format_short_title(title)
        # 通过 JS 找到并填充短标题
        fill_js = f"""
        (() => {{
            const labels = document.querySelectorAll('*');
            for (const el of labels) {{
                if (el.textContent && el.textContent.trim() === {json.dumps(SHORT_TITLE_LABEL)}) {{
                    const parent = el.closest('div') || el.parentElement;
                    if (parent) {{
                        const input = parent.querySelector('input[type="text"]')
                            || parent.nextElementSibling?.querySelector('input[type="text"]');
                        if (input) {{
                            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                                window.HTMLInputElement.prototype, 'value'
                            ).set;
                            nativeInputValueSetter.call(input, {json.dumps(short_title)});
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            return true;
                        }}
                    }}
                }}
            }}
            return false;
        }})()
        """
        page.evaluate_in_iframe(fill_js)
        logger.info("短标题已填充: %s", short_title)


def _add_collection(page: Page) -> None:
    """自动添加到合集（如果有合集可选）。"""
    # 通过文本查找"添加到合集"
    has_collection_js = f"""
    (() => {{
        const els = document.querySelectorAll('*');
        for (const el of els) {{
            if (el.textContent && el.textContent.trim() === {json.dumps(COLLECTION_LABEL)}) {{
                const sibling = el.nextElementSibling;
                if (sibling) {{
                    const options = sibling.querySelectorAll({json.dumps(COLLECTION_OPTIONS)});
                    return options.length > 1;
                }}
            }}
        }}
        return false;
    }})()
    """
    has_collection = page.evaluate_in_iframe(has_collection_js)
    if has_collection:
        # 点击合集区域展开选项
        click_collection_js = f"""
        (() => {{
            const els = document.querySelectorAll('*');
            for (const el of els) {{
                if (el.textContent && el.textContent.trim() === {json.dumps(COLLECTION_LABEL)}) {{
                    const sibling = el.nextElementSibling;
                    if (sibling) {{
                        sibling.click();
                        const options = sibling.querySelectorAll({json.dumps(COLLECTION_OPTIONS)});
                        if (options.length > 0) options[0].click();
                        return true;
                    }}
                }}
            }}
            return false;
        }})()
        """
        page.evaluate_in_iframe(click_collection_js)
        sleep_random(500, 800)
        logger.info("已添加到合集")


def _add_original(page: Page, category: str | None) -> None:
    """勾选原创声明。"""
    # 方式1：通过 label 文本查找"视频为原创"复选框
    original_js = f"""
    (() => {{
        // 尝试 getByLabel 方式
        const labels = document.querySelectorAll('label');
        for (const label of labels) {{
            if (label.textContent && label.textContent.includes({json.dumps(ORIGINAL_CHECKBOX)})) {{
                const input = label.querySelector('input') || label;
                input.click();
                return 'v1';
            }}
        }}
        return null;
    }})()
    """
    result = page.evaluate_in_iframe(original_js)
    sleep_random(500, 800)

    if result == 'v1':
        # 检查是否需要同意条款
        agree_js = f"""
        (() => {{
            const labels = document.querySelectorAll('label');
            for (const label of labels) {{
                if (label.textContent && label.textContent.includes(
                    {json.dumps(ORIGINAL_AGREEMENT)}
                )) {{
                    const input = label.querySelector('input') || label;
                    input.click();
                    return true;
                }}
            }}
            return false;
        }})()
        """
        agreed = page.evaluate_in_iframe(agree_js)
        if agreed:
            sleep_random(500, 800)
            # 点击"声明原创"按钮
            declare_js = f"""
            (() => {{
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {{
                    if (btn.textContent && btn.textContent.includes(
                        {json.dumps(ORIGINAL_DECLARE_BUTTON)}
                    )) {{
                        btn.click();
                        return true;
                    }}
                }}
                return false;
            }})()
            """
            page.evaluate_in_iframe(declare_js)
            sleep_random(500, 800)
    else:
        # 方式2：新版原创声明（2023年11月后）
        new_original_js = f"""
        (() => {{
            const labels = document.querySelectorAll({json.dumps(ORIGINAL_LABEL_NEW)});
            for (const label of labels) {{
                if (label.textContent && label.textContent.includes('声明原创')) {{
                    const checkbox = document.querySelector(
                        {json.dumps(ORIGINAL_CHECKBOX_NEW)}
                    );
                    if (checkbox && !checkbox.disabled) {{
                        checkbox.click();
                        return true;
                    }}
                }}
            }}
            return false;
        }})()
        """
        clicked = page.evaluate_in_iframe(new_original_js)
        if clicked:
            sleep_random(500, 800)
            # 勾选对话框中的协议
            dialog_js = f"""
            (() => {{
                const checked = document.querySelector(
                    'div.declare-original-dialog label.ant-checkbox-wrapper-checked:visible'
                );
                if (!checked) {{
                    const input = document.querySelector(
                        {json.dumps(ORIGINAL_DIALOG_CHECKBOX)}
                    );
                    if (input) input.click();
                }}
                return true;
            }})()
            """
            page.evaluate_in_iframe(dialog_js)
            sleep_random(500, 800)

            # 选择原创类型（如果需要）
            if category:
                type_js = f"""
                (() => {{
                    const formLabel = document.querySelector(
                        {json.dumps(ORIGINAL_TYPE_FORM)}
                    );
                    if (formLabel && formLabel.textContent.includes('原创类型')) {{
                        const dropdown = document.querySelector(
                            {json.dumps(ORIGINAL_TYPE_DROPDOWN)}
                        );
                        if (dropdown) dropdown.click();
                        return true;
                    }}
                    return false;
                }})()
                """
                has_type = page.evaluate_in_iframe(type_js)
                if has_type:
                    sleep_random(500, 800)
                    select_type_js = f"""
                    (() => {{
                        const options = document.querySelectorAll(
                            {json.dumps(ORIGINAL_TYPE_OPTION)}
                        );
                        for (const opt of options) {{
                            if (opt.textContent && opt.textContent.includes(
                                {json.dumps(category)}
                            )) {{
                                opt.click();
                                return true;
                            }}
                        }}
                        return false;
                    }})()
                    """
                    page.evaluate_in_iframe(select_type_js)
                    sleep_random(800, 1200)

            # 点击"声明原创"按钮
            declare_new_js = f"""
            (() => {{
                const btn = document.querySelector({json.dumps(ORIGINAL_DECLARE_BUTTON_NEW)});
                if (btn) {{ btn.click(); return true; }}
                return false;
            }})()
            """
            page.evaluate_in_iframe(declare_new_js)
            sleep_random(500, 800)

    logger.info("原创声明已设置")


def _set_schedule_time(page: Page, publish_date) -> None:
    """设置定时发布时间。"""
    from datetime import datetime

    if not isinstance(publish_date, datetime):
        return

    # 点击"定时"标签
    schedule_js = f"""
    (() => {{
        const labels = document.querySelectorAll({json.dumps("label")});
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
    # 需要点击第二个"定时"标签（第一个可能是其他选项）
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

    # 选中并替换时间
    select_all_js = """
    (() => {
        const input = document.activeElement;
        if (input && input.select) input.select();
    })()
    """
    page.evaluate_in_iframe(select_all_js)
    page.type_text(str(publish_date.hour))
    sleep_random(300, 500)

    # 回点标题使定时生效
    page.click_element(TITLE_INPUT)
    sleep_random(300, 500)

    logger.info("定时发布已设置: %s", publish_date)


def _detect_upload_status(page: Page) -> None:
    """等待视频上传/处理完成。"""
    max_wait = 600.0  # 10 分钟
    start = time.monotonic()

    logger.info("等待视频上传/处理完成...")

    while time.monotonic() - start < max_wait:
        # 检查发布按钮是否可点击（按钮在 iframe 内）
        clickable = page.evaluate_in_iframe(
            f"""
            (() => {{
                const btn = document.querySelector({json.dumps(PUBLISH_BUTTON)});
                if (!btn) {{
                    // 尝试通过文本查找
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
            logger.info("视频上传/处理完成")
            return

        # 检查是否出错
        if page.has_element(UPLOAD_ERROR) and page.has_element(UPLOAD_DELETE_TAG):
            logger.error("视频上传出错，尝试重新上传")
            _handle_upload_error(page)

        sleep_random(2000, 3000)

    raise UploadTimeoutError("等待视频上传/处理超时(10分钟)")


def _handle_upload_error(page: Page) -> None:
    """处理上传出错，删除并重新上传。"""
    logger.info("视频出错了，重新上传中")
    # 点击包含"删除"文本的标签
    page.evaluate_in_iframe(
        """
        (() => {
            const tags = document.querySelectorAll('div.media-status-content div.tag-inner');
            for (const tag of tags) {
                if (tag.textContent && tag.textContent.trim() === '删除') {
                    tag.click();
                    return true;
                }
            }
            return false;
        })()
        """
    )
    sleep_random(500, 800)

    # 点击确认删除按钮
    page.evaluate_in_iframe(
        """
        (() => {
            const buttons = document.querySelectorAll('button');
            for (const btn of buttons) {
                if (btn.textContent && btn.textContent.trim() === '删除') {
                    btn.click();
                    return true;
                }
            }
            return false;
        })()
        """
    )
    sleep_random(1000, 1500)


def _wait_for_publish_button_clickable(page: Page) -> None:
    """等待发布按钮可点击。"""
    max_wait = 600.0
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
    """等待发布完成（页面跳转到发布列表）。"""
    max_wait = 30.0
    start = time.monotonic()

    while time.monotonic() - start < max_wait:
        current_url = page.evaluate("window.location.href") or ""
        if POST_LIST_URL in current_url or "post/list" in current_url:
            logger.info("视频发布成功")
            return
        sleep_random(500, 1000)

    logger.warning("发布后未检测到页面跳转，可能已发布成功")
