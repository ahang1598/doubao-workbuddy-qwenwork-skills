"""Feed 详情 + 评论加载，对应 Go xiaohongshu/feed_detail.go（867 行）。"""

from __future__ import annotations

import json
import logging
import random
import re
import time

from .cdp import Page
from .errors import NoFeedDetailError, PageNotAccessibleError
from .human import (
    BUTTON_CLICK_INTERVAL,
    DEFAULT_MAX_ATTEMPTS,
    FINAL_SPRINT_PUSH_COUNT,
    HUMAN_DELAY,
    LARGE_SCROLL_TRIGGER,
    MAX_CLICK_PER_ROUND,
    MIN_SCROLL_DELTA,
    POST_SCROLL,
    REACTION_TIME,
    READ_TIME,
    SCROLL_WAIT,
    SHORT_READ,
    STAGNANT_LIMIT,
    calculate_scroll_delta,
    get_scroll_interval,
    get_scroll_ratio,
    sleep_random,
)
from .selectors import (
    ACCESS_ERROR_WRAPPER,
    END_CONTAINER,
    NO_COMMENTS_TEXT,
    PARENT_COMMENT,
    SHOW_MORE_BUTTON,
)
from .types import (
    CommentList,
    CommentLoadConfig,
    FeedDetail,
    FeedDetailResponse,
)
from .urls import make_feed_detail_url

logger = logging.getLogger(__name__)

# 页面不可访问关键词
_INACCESSIBLE_KEYWORDS = [
    "当前笔记暂时无法浏览",
    "该内容因违规已被删除",
    "该笔记已被删除",
    "内容不存在",
    "笔记不存在",
    "已失效",
    "私密笔记",
    "仅作者可见",
    "因用户设置，你无法查看",
    "因违规无法查看",
    "Isn't Available",
    "isn't available",
]

# 扫码验证关键词（触发反爬机制）
_SCAN_QRCODE_KEYWORDS = [
    "扫码查看",
    "打开小红书App扫码",
    "请使用小红书App扫码",
]

_REPLY_COUNT_RE = re.compile(r"展开\s*(\d+)\s*条回复")
_TOTAL_COMMENT_RE = re.compile(r"共(\d+)条评论")

# 默认评论加载数量（不传 --load-all-comments 时）
DEFAULT_COMMENT_COUNT = 30
# 每次滚动预估加载的评论数（小红书每次滚动约加载 5~10 条）
_ESTIMATED_COMMENTS_PER_SCROLL = 5
# 动态计算滚动上限时的安全系数（防止网络慢等情况多滚几次）
_SCROLL_SAFETY_FACTOR = 2
# "没有更多"终止关键词
_NO_MORE_COMMENTS_KEYWORDS = ["没有更多", "暂无评论", "还没有评论"]

def get_feed_detail(
    page: Page,
    feed_id: str,
    xsec_token: str,
    load_all_comments: bool = False,
    config: CommentLoadConfig | None = None,
) -> FeedDetailResponse:
    """获取 Feed 详情（含评论）。

    默认加载 top 30 条评论（通过滚动评论区）。
    传入 load_all_comments=True 时加载全部评论（无数量限制）。

    Args:
        page: CDP 页面对象。
        feed_id: Feed ID。
        xsec_token: xsec_token。
        load_all_comments: 是否加载全部评论（默认 False，仅加载 top 30）。
        config: 评论加载配置。

    Raises:
        PageNotAccessibleError: 页面不可访问。
        NoFeedDetailError: 未获取到详情数据。
    """
    if config is None:
        config = CommentLoadConfig()

    url = make_feed_detail_url(feed_id, xsec_token)
    logger.info("打开 feed 详情页: %s", url)

    # 导航 + 页面可访问性检查（含防爬重试）
    anti_crawl_delays = [
        random.randint(7, 10),
        random.randint(15, 18),
    ]
    last_error: Exception | None = None

    for nav_round in range(1 + len(anti_crawl_delays)):
        # 如果是防爬重试轮次，先等待
        if nav_round > 0:
            delay = anti_crawl_delays[nav_round - 1]
            print(f"遇到了重定向或防爬验证，将在 {delay} 秒后重试（第 {nav_round}/{len(anti_crawl_delays)} 次重试）")
            logger.info("遇到重定向或防爬验证，等待 %d 秒后重试（第 %d/%d 次）...", delay, nav_round, len(anti_crawl_delays))
            time.sleep(delay)

        # 导航（含网络重试）
        for attempt in range(3):
            try:
                page.navigate(url)
                page.wait_for_load()
                page.wait_dom_stable()
                break
            except Exception as e:
                logger.debug("页面导航重试 #%d: %s", attempt, e)
                time.sleep(0.5 + random.random())
        else:
            raise RuntimeError("页面导航失败")

        sleep_random(800, 1500)

        # 检查页面可访问性
        try:
            _check_page_accessible(page, url, feed_id)
            last_error = None
            break
        except PageNotAccessibleError as e:
            last_error = e
            # 如果是内容本身不可用（非防爬），直接抛出不重试
            error_msg = str(e)
            is_anti_crawl = "重定向" in error_msg or "验证" in error_msg or "反爬" in error_msg
            if not is_anti_crawl:
                raise
            logger.warning("防爬检测失败: %s", e)

    if last_error is not None:
        raise last_error

    # 加载评论
    if load_all_comments:
        # 全量模式：无数量限制，使用原有的大滚动上限
        logger.info("全量评论模式: 加载全部评论")
        try:
            _load_comments(page, config, max_comments=0, max_scroll_rounds=DEFAULT_MAX_ATTEMPTS)
        except Exception as e:
            logger.warning("加载全部评论失败: %s", e)
    else:
        # 默认模式：加载 top N 条评论
        target_count = config.max_comment_items if config.max_comment_items > 0 else DEFAULT_COMMENT_COUNT
        # 根据目标评论数动态计算滚动上限：目标数 / 每次滚动预估加载数 * 安全系数
        dynamic_scroll_rounds = max(
            10,
            (target_count // _ESTIMATED_COMMENTS_PER_SCROLL + 1) * _SCROLL_SAFETY_FACTOR,
        )
        logger.info("默认评论模式: 加载 top %d 条评论, 滚动上限 %d 次", target_count, dynamic_scroll_rounds)
        try:
            _load_comments(page, config, max_comments=target_count, max_scroll_rounds=dynamic_scroll_rounds)
        except Exception as e:
            logger.warning("加载评论失败: %s", e)

    return _extract_feed_detail(page, feed_id)
# ========== 页面检查 ==========

def _check_page_accessible(page: Page, url: str = "", feed_id: str = "") -> None:
    """检查页面是否可访问。

    检测顺序：
    1. URL 重定向检测：如果页面被重定向到非详情页（如首页 /explore），
       说明触发了反爬机制，等待后重试。
    2. DOM 元素检测：检查页面上的错误提示文本（扫码验证、内容不可用等）。
    """
    time.sleep(0.5)

    # 第一步：检测 URL 是否被重定向（反爬最常见的表现）
    if feed_id:
        current_url = page.evaluate("window.location.href") or ""
        if f"/explore/{feed_id}" not in current_url:
            raise PageNotAccessibleError(
                f"页面被重定向，可能触发了反爬限制。"
                f"预期: /explore/{feed_id}，实际: {current_url}"
            )

    # 第二步：检测 DOM 元素中的错误提示
    text = page.get_element_text(ACCESS_ERROR_WRAPPER)
    if not text:
        return

    text = text.strip()

    # 检测扫码验证（反爬机制触发）→ 抛出异常，由外层 get_feed_detail 统一重试
    if _is_scan_qrcode_verification(text):
        raise PageNotAccessibleError(
            f"触发了小红书扫码验证（反爬机制），需要等待后重试。"
        )

    for kw in _INACCESSIBLE_KEYWORDS:
        if kw in text:
            raise PageNotAccessibleError(kw)

    if text:
        raise PageNotAccessibleError(text)

def _is_scan_qrcode_verification(text: str) -> bool:
    """判断页面文本是否为扫码验证。"""
    return any(kw in text for kw in _SCAN_QRCODE_KEYWORDS)


# ========== 数据提取 ==========


_EXTRACT_DETAIL_JS = """
(() => {
    if (window.__INITIAL_STATE__ &&
        window.__INITIAL_STATE__.note &&
        window.__INITIAL_STATE__.note.noteDetailMap) {
        return JSON.stringify(window.__INITIAL_STATE__.note.noteDetailMap);
    }
    return "";
})()
"""


def _extract_feed_detail(page: Page, feed_id: str) -> FeedDetailResponse:
    """从 __INITIAL_STATE__ 提取 Feed 详情。

    视频类帖子或网络较慢时，__INITIAL_STATE__ 可能需要更长时间初始化，
    因此使用递增等待策略，最多等待约 10 秒。
    """
    result = None
    max_retries = 10
    for attempt in range(max_retries):
        result = page.evaluate(_EXTRACT_DETAIL_JS)
        if result:
            break
        wait_sec = min(0.5 + attempt * 0.3, 2.0)
        logger.debug("等待 __INITIAL_STATE__ 就绪（第 %d 次，等待 %.1fs）", attempt + 1, wait_sec)
        time.sleep(wait_sec)

    if not result:
        raise NoFeedDetailError()

    note_detail_map = json.loads(result)
    note_data = note_detail_map.get(feed_id)
    if not note_data:
        # 某些帖子（尤其是视频类）noteDetailMap 的 key 可能是 "undefined" 而非 feed_id，
        # 这是小红书前端的已知行为，尝试用 fallback key 获取数据
        available_keys = list(note_detail_map.keys())
        logger.debug("noteDetailMap 中未找到 feed_id=%s，尝试 fallback，可用 keys: %s", feed_id, available_keys[:5])

        # 优先尝试 "undefined" key（最常见的 fallback 场景）
        if "undefined" in note_detail_map:
            note_data = note_detail_map["undefined"]
            logger.info("使用 fallback key 'undefined' 获取到详情数据")
        else:
            # 如果只有一个 key 且不是 feed_id，直接使用该 key 的数据
            if len(available_keys) == 1:
                note_data = note_detail_map[available_keys[0]]
                logger.info("使用唯一可用 key '%s' 获取到详情数据", available_keys[0])

    if not note_data:
        logger.warning("noteDetailMap 中未找到 feed_id=%s 的数据，可用 keys: %s", feed_id, available_keys[:5])
        raise NoFeedDetailError()

    comments_raw = note_data.get("comments")
    if comments_raw is None:
        comments_raw = {}
    return FeedDetailResponse(
        note=FeedDetail.from_dict(note_data.get("note", {})),
        comments=CommentList.from_dict(comments_raw),
    )


# ========== 评论加载状态机 ==========

def _check_no_more_comments(page: Page) -> bool:
    """检查页面是否显示"没有更多评论"等终止文本。"""
    body_text = page.evaluate(
        "document.querySelector('.comments-container') "
        "? document.querySelector('.comments-container').innerText.slice(-100) : ''"
    ) or ""
    for keyword in _NO_MORE_COMMENTS_KEYWORDS:
        if keyword in body_text:
            return True
    return False

def _load_comments(
    page: Page,
    config: CommentLoadConfig,
    max_comments: int,
    max_scroll_rounds: int,
) -> None:
    """加载评论的状态机。

    Args:
        page: CDP 页面对象。
        config: 评论加载配置。
        max_comments: 目标评论数上限（0 = 不限）。
        max_scroll_rounds: 最大滚动次数上限。
    """
    scroll_interval = get_scroll_interval(config.scroll_speed)

    logger.info(
        "开始加载评论（目标: %s, 滚动上限: %d）...",
        f"{max_comments} 条" if max_comments > 0 else "全部",
        max_scroll_rounds,
    )
    _scroll_to_comments_area(page)
    sleep_random(*HUMAN_DELAY)

    # 检查是否无评论
    if _check_no_comments(page):
        logger.info("检测到无评论区域，跳过加载")
        return

    # 状态
    last_count = 0
    last_scroll_top = 0
    stagnant_checks = 0
    total_clicked = 0
    total_skipped = 0

    for round_num in range(max_scroll_rounds):
        logger.debug("=== 滚动轮次 %d/%d ===", round_num + 1, max_scroll_rounds)

        # 终止条件 1: 检查是否到达底部（THE END）
        if _check_end_container(page):
            count = _get_comment_count(page)
            logger.info(
                "检测到 THE END，加载完成: %d 条评论, 点击: %d, 跳过: %d",
                count, total_clicked, total_skipped,
            )
            return

        # 终止条件 2: 检查"没有更多评论"文本
        if _check_no_more_comments(page):
            count = _get_comment_count(page)
            logger.info(
                "检测到没有更多评论，加载完成: %d 条评论, 点击: %d, 跳过: %d",
                count, total_clicked, total_skipped,
            )
            return

        # 定期点击展开按钮
        if config.click_more_replies and round_num % BUTTON_CLICK_INTERVAL == 0:
            clicked, skipped = _click_show_more_buttons(page, config.max_replies_threshold)
            total_clicked += clicked
            total_skipped += skipped
            if clicked > 0 or skipped > 0:
                sleep_random(*READ_TIME)
                second_clicked, second_skipped = _click_show_more_buttons(
                    page, config.max_replies_threshold
                )
                total_clicked += second_clicked
                total_skipped += second_skipped
                if second_clicked > 0 or second_skipped > 0:
                    sleep_random(*SHORT_READ)

        # 获取当前评论数
        current_count = _get_comment_count(page)
        if current_count != last_count:
            logger.info("评论增加: %d -> %d", last_count, current_count)
            last_count = current_count
            stagnant_checks = 0
        else:
            stagnant_checks += 1

        # 终止条件 3: 检查是否达到目标评论数
        if max_comments > 0 and current_count >= max_comments:
            logger.info("已达到目标评论数: %d/%d", current_count, max_comments)
            return

        # 滚动
        if current_count > 0:
            _scroll_to_last_comment(page)
            sleep_random(*POST_SCROLL)

        large_mode = stagnant_checks >= LARGE_SCROLL_TRIGGER
        push_count = 1
        if large_mode:
            push_count = 3 + random.randint(0, 2)

        scroll_delta, current_scroll_top = _human_scroll(
            page, config.scroll_speed, large_mode, push_count
        )

        if scroll_delta < MIN_SCROLL_DELTA or current_scroll_top == last_scroll_top:
            stagnant_checks += 1
        else:
            stagnant_checks = 0
            last_scroll_top = current_scroll_top

        # 终止条件 4: 滚动停滞过多
        if stagnant_checks >= STAGNANT_LIMIT:
            # 全量模式下尝试大冲刺，默认模式下直接结束
            if max_comments == 0:
                logger.info("停滞过多，尝试大冲刺...")
                _human_scroll(page, config.scroll_speed, True, 10)
                stagnant_checks = 0
            else:
                count = _get_comment_count(page)
                logger.info(
                    "滚动停滞，评论不再增加，结束加载: %d 条评论", count
                )
                return

        time.sleep(scroll_interval)

    # 达到滚动上限
    count = _get_comment_count(page)
    if max_comments == 0:
        # 全量模式：最终冲刺
        logger.info("达到最大滚动次数，最后冲刺...")
        _human_scroll(page, config.scroll_speed, True, FINAL_SPRINT_PUSH_COUNT)
        count = _get_comment_count(page)
    logger.info(
        "加载结束: %d 条评论, 点击: %d, 跳过: %d",
        count, total_clicked, total_skipped,
    )

# ========== 滚动 ==========


def _human_scroll(
    page: Page,
    speed: str,
    large_mode: bool,
    push_count: int,
) -> tuple[int, int]:
    """人类化滚动。

    Returns:
        (actual_delta, current_scroll_top)
    """
    before_top = page.get_scroll_top()
    viewport_height = page.get_viewport_height()

    base_ratio = get_scroll_ratio(speed)
    if large_mode:
        base_ratio *= 2.0

    actual_delta = 0
    current_scroll_top = before_top

    for i in range(max(1, push_count)):
        scroll_delta = calculate_scroll_delta(viewport_height, base_ratio)
        page.scroll_by(0, int(scroll_delta))
        sleep_random(*SCROLL_WAIT)

        current_scroll_top = page.get_scroll_top()
        delta_this = current_scroll_top - before_top
        actual_delta += delta_this
        before_top = current_scroll_top

        if i < push_count - 1:
            sleep_random(*HUMAN_DELAY)

    # 如果没有滚动，强制到底部
    if actual_delta < MIN_SCROLL_DELTA and push_count > 0:
        page.scroll_to_bottom()
        sleep_random(*POST_SCROLL)
        current_scroll_top = page.get_scroll_top()
        actual_delta = current_scroll_top - (before_top - actual_delta)

    return actual_delta, current_scroll_top


def _scroll_to_comments_area(page: Page) -> None:
    """滚动到评论区。"""
    logger.info("滚动到评论区...")
    page.scroll_element_into_view(".comments-container")
    time.sleep(0.5)
    # 触发懒加载
    page.dispatch_wheel_event(100)


def _scroll_to_last_comment(page: Page) -> None:
    """滚动到最后一条评论。"""
    count = page.get_elements_count(PARENT_COMMENT)
    if count > 0:
        page.scroll_nth_element_into_view(PARENT_COMMENT, count - 1)


# ========== DOM 查询 ==========


def _get_comment_count(page: Page) -> int:
    """获取当前评论数量。"""
    return page.get_elements_count(PARENT_COMMENT)


def _get_total_comment_count(page: Page) -> int:
    """获取总评论数（从 "共N条评论" 提取）。"""
    text = page.get_element_text(".comments-container .total")
    if not text:
        return 0
    match = _TOTAL_COMMENT_RE.search(text)
    if match:
        return int(match.group(1))
    return 0


def _check_no_comments(page: Page) -> bool:
    """检查是否无评论区域。"""
    text = page.get_element_text(NO_COMMENTS_TEXT)
    if not text:
        return False
    return "这是一片荒地" in text.strip()


def _check_end_container(page: Page) -> bool:
    """检查是否到达底部 THE END。"""
    text = page.get_element_text(END_CONTAINER)
    if not text:
        return False
    upper = text.strip().upper()
    return "THE END" in upper or "THEEND" in upper


# ========== 按钮点击 ==========


def _click_show_more_buttons(page: Page, max_threshold: int) -> tuple[int, int]:
    """点击"展开N条回复"按钮。

    Returns:
        (clicked, skipped)
    """
    count = page.get_elements_count(SHOW_MORE_BUTTON)
    if count == 0:
        return 0, 0

    max_click = MAX_CLICK_PER_ROUND + random.randint(0, MAX_CLICK_PER_ROUND - 1)
    clicked = 0
    skipped = 0

    for i in range(count):
        if clicked >= max_click:
            break

        # 获取按钮文本
        text = page.evaluate(
            f"document.querySelectorAll({json.dumps(SHOW_MORE_BUTTON)})[{i}]?.textContent || ''"
        )
        if not text:
            continue

        # 检查是否应该跳过
        if max_threshold > 0:
            match = _REPLY_COUNT_RE.search(text)
            if match:
                reply_count = int(match.group(1))
                if reply_count > max_threshold:
                    logger.debug(
                        "跳过 '%s'（回复数 %d > 阈值 %d）", text, reply_count, max_threshold
                    )
                    skipped += 1
                    continue

        # 滚动到按钮并点击
        page.scroll_nth_element_into_view(SHOW_MORE_BUTTON, i)
        sleep_random(*REACTION_TIME)
        page.evaluate(f"document.querySelectorAll({json.dumps(SHOW_MORE_BUTTON)})[{i}]?.click()")
        sleep_random(*READ_TIME)
        clicked += 1

    return clicked, skipped
