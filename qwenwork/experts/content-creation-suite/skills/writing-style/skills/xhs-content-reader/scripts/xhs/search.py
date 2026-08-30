"""搜索 Feeds，对应 Go xiaohongshu/search.go。"""

from __future__ import annotations

import json
import logging
import time

from .cdp import Page
from .errors import NoFeedsError
from .human import sleep_random
from .selectors import FILTER_BUTTON, FILTER_PANEL
from .types import Feed, FilterOption
from .urls import make_search_url

logger = logging.getLogger(__name__)

# 筛选选项映射表：{筛选组索引: [(标签索引, 文本), ...]}
_FILTER_OPTIONS: dict[int, list[tuple[int, str]]] = {
    1: [(1, "综合"), (2, "最新"), (3, "最多点赞"), (4, "最多评论"), (5, "最多收藏")],
    2: [(1, "不限"), (2, "视频"), (3, "图文")],
    3: [(1, "不限"), (2, "一天内"), (3, "一周内"), (4, "半年内")],
    4: [(1, "不限"), (2, "已看过"), (3, "未看过"), (4, "已关注")],
    5: [(1, "不限"), (2, "同城"), (3, "附近")],
}

# 从 __INITIAL_STATE__ 提取搜索结果的 JS
_EXTRACT_SEARCH_JS = """
(() => {
    if (window.__INITIAL_STATE__ &&
        window.__INITIAL_STATE__.search &&
        window.__INITIAL_STATE__.search.feeds) {
        const feeds = window.__INITIAL_STATE__.search.feeds;
        const feedsData = feeds.value !== undefined ? feeds.value : feeds._value;
        if (feedsData) {
            return JSON.stringify(feedsData);
        }
    }
    return "";
})()
"""


def _find_internal_option(group_index: int, text: str) -> tuple[int, int]:
    """查找内部筛选选项索引。

    Returns:
        (filters_index, tags_index)

    Raises:
        ValueError: 未找到匹配的选项。
    """
    options = _FILTER_OPTIONS.get(group_index)
    if not options:
        raise ValueError(f"筛选组 {group_index} 不存在")

    for tags_index, option_text in options:
        if option_text == text:
            return group_index, tags_index

    valid = [t for _, t in options]
    raise ValueError(f"在筛选组 {group_index} 中未找到 '{text}'，有效值: {valid}")


def _convert_filters(filter_opt: FilterOption) -> list[tuple[int, int]]:
    """将 FilterOption 转换为内部 (filters_index, tags_index) 列表。"""
    result: list[tuple[int, int]] = []

    if filter_opt.sort_by:
        result.append(_find_internal_option(1, filter_opt.sort_by))
    if filter_opt.note_type:
        result.append(_find_internal_option(2, filter_opt.note_type))
    if filter_opt.publish_time:
        result.append(_find_internal_option(3, filter_opt.publish_time))
    if filter_opt.search_scope:
        result.append(_find_internal_option(4, filter_opt.search_scope))
    if filter_opt.location:
        result.append(_find_internal_option(5, filter_opt.location))

    return result


def search_feeds(
    page: Page,
    keyword: str,
    filter_option: FilterOption | None = None,
) -> list[Feed]:
    """搜索 Feeds。

    Args:
        page: CDP 页面对象。
        keyword: 搜索关键词。
        filter_option: 可选筛选条件。

    Raises:
        NoFeedsError: 没有捕获到搜索结果。
        ValueError: 筛选选项无效。
    """
    search_url = make_search_url(keyword)
    page.navigate(search_url)
    page.wait_for_load()
    page.wait_dom_stable()

    # 等待 __INITIAL_STATE__ 初始化
    _wait_for_initial_state(page)

    # 应用筛选条件
    if filter_option:
        internal_filters = _convert_filters(filter_option)
        if internal_filters:
            _apply_filters(page, internal_filters)

    # 提取搜索结果
    result = page.evaluate(_EXTRACT_SEARCH_JS)
    if not result:
        raise NoFeedsError()

    feeds_data = json.loads(result)
    return [Feed.from_dict(f) for f in feeds_data]


def search_feeds_with_count(
    page: Page,
    keyword: str,
    count: int,
    filter_option: FilterOption | None = None,
    max_scroll_rounds: int = 20,
) -> list[Feed]:
    """搜索 Feeds，通过滚动加载尽量获取指定数量的帖子。

    当 count > 页面初始加载数量时，自动触发滚动加载更多内容，
    直到累计数量达到 count 或页面无更多数据为止。

    每次滚动后随机等待 3~6 秒，模拟人工浏览节奏，避免触发反爬机制。

    Args:
        page: CDP 页面对象。
        keyword: 搜索关键词。
        count: 期望获取的帖子数量上限。
        filter_option: 可选筛选条件。
        max_scroll_rounds: 最大滚动轮次，防止无限循环（默认 20）。

    Raises:
        NoFeedsError: 没有捕获到任何搜索结果。
        ValueError: 筛选选项无效。
    """
    search_url = make_search_url(keyword)
    page.navigate(search_url)
    page.wait_for_load()
    page.wait_dom_stable()

    _wait_for_initial_state(page)

    # 应用筛选条件
    if filter_option:
        internal_filters = _convert_filters(filter_option)
        if internal_filters:
            _apply_filters(page, internal_filters)

    # 首次提取（应用筛选器后页面可能需要额外时间重新渲染数据）
    result = page.evaluate(_EXTRACT_SEARCH_JS)

    seen_ids: set[str] = set()
    all_feeds: list[Feed] = []

    def _collect_new_feeds(raw_json: str) -> int:
        """解析并去重追加到 all_feeds，返回本轮新增数量。"""
        new_count = 0
        for item in json.loads(raw_json):
            feed = Feed.from_dict(item)
            if feed.id and feed.id not in seen_ids:
                seen_ids.add(feed.id)
                all_feeds.append(feed)
                new_count += 1
        return new_count

    if result:
        _collect_new_feeds(result)
    logger.info("首次加载获取 %d 条，目标 %d 条", len(all_feeds), count)

    # 滚动加载更多
    scroll_round = 0
    while len(all_feeds) < count and scroll_round < max_scroll_rounds:
        scroll_round += 1

        # 滚动到页面底部触发加载，随机等待 3~6 秒模拟人工浏览节奏
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        sleep_random(3000, 6000)
        page.wait_dom_stable()

        new_result = page.evaluate(_EXTRACT_SEARCH_JS)
        if not new_result:
            logger.info("第 %d 轮滚动后无数据，停止", scroll_round)
            break

        newly_added = _collect_new_feeds(new_result)
        logger.info(
            "第 %d 轮滚动后新增 %d 条，累计 %d 条",
            scroll_round,
            newly_added,
            len(all_feeds),
        )

        if newly_added == 0:
            # 连续无新增说明已到底
            logger.info("无新增数据，页面已加载完毕，停止滚动")
            break

    logger.info("滚动加载完成，共获取 %d 条（目标 %d 条）", len(all_feeds), count)
    return all_feeds[:count]


def _wait_for_initial_state(page: Page, timeout: float = 10.0) -> None:
    """等待 __INITIAL_STATE__ 就绪。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ready = page.evaluate("window.__INITIAL_STATE__ !== undefined")
        if ready:
            return
        time.sleep(0.5)
    logger.warning("等待 __INITIAL_STATE__ 超时")


def _apply_filters(page: Page, filters: list[tuple[int, int]]) -> None:
    """应用筛选条件。

    修复说明：
    小红书搜索页面为每个筛选项生成了两个 div.tags 元素：
    - 一个隐藏的（aria-hidden="true", style="opacity: 1e-05"）
    - 一个可见的（正常显示）

    原选择器 `nth-child(N)` 可能选中隐藏元素导致点击无效。
    修复方案：通过 JavaScript 查找可见的 tags 元素进行点击。

    Args:
        page: CDP 页面对象。
        filters: [(filters_index, tags_index), ...] 筛选条件列表。
    """
    # 悬停筛选按钮
    page.hover_element(FILTER_BUTTON)

    # 等待筛选面板出现
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if page.has_element(FILTER_PANEL):
            break
        sleep_random(300, 600)

    # 检查面板是否出现
    if not page.has_element(FILTER_PANEL):
        logger.warning("筛选面板未出现，跳过筛选")
        return

    # 点击各筛选项
    for filters_index, tags_index in filters:
        # 获取该筛选组的选项文本
        options = _FILTER_OPTIONS.get(filters_index, [])
        if tags_index < 1 or tags_index > len(options):
            logger.warning(
                "无效的 tags_index: %d，筛选组 %d 有效范围 1-%d",
                tags_index, filters_index, len(options)
            )
            continue

        target_text = options[tags_index - 1][1]  # tags_index 从 1 开始

        # 使用 JavaScript 查找并点击可见的 tags 元素
        click_js = f"""
        (() => {{
            const filters = document.querySelectorAll('div.filter-panel div.filters');
            if (!filters[{filters_index - 1}]) {{
                return {{ success: false, reason: '筛选组 {filters_index} 不存在' }};
            }}
            
            const tags = filters[{filters_index - 1}].querySelectorAll('div.tags');
            // 找到文本匹配且可见的元素
            const visibleTag = Array.from(tags).find(tag => {{
                const text = tag.textContent?.trim();
                const isHidden = tag.hasAttribute('aria-hidden') || 
                                  tag.style.opacity === '1e-05' ||
                                  tag.offsetParent === null;
                return text === '{target_text}' && !isHidden;
            }});
            
            if (visibleTag) {{
                visibleTag.click();
                return {{ success: true, text: visibleTag.textContent?.trim() }};
            }}
            return {{ success: false, reason: '未找到可见的 {target_text} 元素' }};
        }})()
        """

        result = page.evaluate(click_js)
        logger.info("点击筛选 [组%d] %s: %s", filters_index, target_text, result)

        if not result or not result.get("success"):
            logger.warning("筛选点击失败: %s", result)
            # 失败时尝试备用方案：直接用原选择器点击
            selector = (
                f"div.filter-panel div.filters:nth-child({filters_index}) "
                f"div.tags:nth-child({tags_index * 2})"  # 可见元素通常是奇数位置
            )
            try:
                page.click_element(selector)
                logger.info("备用方案点击成功: %s", selector)
            except Exception as e:
                logger.warning("备用方案点击也失败: %s", e)

        sleep_random(300, 600)

    # 等待页面更新
    page.wait_dom_stable()
    _wait_for_initial_state(page)
