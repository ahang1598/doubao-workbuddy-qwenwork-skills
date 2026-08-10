#!/usr/bin/env python3
"""Check travel guide image promises, title duplication, and Feishu visual richness."""

from __future__ import annotations

import re
import sys
import csv
import argparse
from pathlib import Path


IMAGE_PATTERNS = [
    re.compile(r"!\[[^\]]*\]\([^)]+\)"),
    re.compile(r"<img\b", re.IGNORECASE),
    re.compile(r"<image\b", re.IGNORECASE),
    re.compile(r"<bookmark\b[^>]*(?:图片|地图|image|photo|map)", re.IGNORECASE),
]

TABLE_PATTERN = re.compile(r"^\s*\|.+\|\s*$", re.MULTILINE)
XML_TABLE_PATTERN = re.compile(r"<table\b", re.IGNORECASE)
BULLET_PATTERN = re.compile(r"^\s*(?:[-*+]|[0-9]+[.)]|[•·])\s+", re.MULTILINE)
CALLOUT_PATTERN = re.compile(r"<callout\b", re.IGNORECASE)
GRID_PATTERN = re.compile(r"<grid\b", re.IGNORECASE)
CHECKBOX_PATTERN = re.compile(r"(?:<checkbox\b|^\s*[-*]?\s*\[[ xX]\])", re.IGNORECASE | re.MULTILINE)
BOOKMARK_PATTERN = re.compile(r"<bookmark\b", re.IGNORECASE)
BLOCKQUOTE_PATTERN = re.compile(r"(?:<blockquote\b|^\s*>\s+)", re.IGNORECASE | re.MULTILINE)
HR_PATTERN = re.compile(r"<hr\s*/?>", re.IGNORECASE)
CALLOUTISH_PATTERN = re.compile(r"(?:<callout\b|<grid\b|<checkbox\b|<blockquote\b|>\s|\[ \]|\[x\])", re.IGNORECASE)
SEMANTIC_COLOR_PATTERN = re.compile(r'(?:background-color|border-color)\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
SEMANTIC_COLOR_FAMILY_PATTERN = re.compile(r"(blue|green|yellow|gray|grey|red|orange|purple)", re.IGNORECASE)
DATE_PATTERN = re.compile(r"(?:20\d{2}[-/年.]\d{1,2}[-/月.]\d{1,2}|(?:\d{1,2}月\d{1,2}日)|周[一二三四五六日天]|星期[一二三四五六日天])")
BOOKING_ACTION_PATTERN = re.compile(r"(?:预订路径|从哪里订|何时订|先确认|失败替代|退改|取消政策|库存|票务|预约|官方|OTA|售票|购票)")
WEATHER_STRATEGY_PATTERN = re.compile(
    r"(?:天气|气温|温度|降雨|下雨|雨天|晴天|高温|低温|大风|风力|台风|雨季|雪季|降雪|花期|季节|避暑|防晒|保暖|48\s*小时|出发前\s*48)"
)
DAY_EXECUTION_PATTERN = re.compile(
    r"(?:上午|中午|下午|傍晚|晚上|夜间|时段|先去|再去|然后|交通|步行|打车|地铁|公交|换乘|耗时|用餐|午餐|晚餐|早餐|预约|排队|停止入场|可删减|删掉|撤退点|备选|替代|雨天|疲劳|太热|太冷)"
)
BOOKING_ENTRY_PATTERN = re.compile(
    r"(?:<bookmark\b[^>]*href\s*=\s*[\"']https?://|官网|官方网站|官方小程序|官方公众号|票务入口|购票入口|预约入口|地图搜索|小程序搜索|OTA|携程|美团|大众点评|12306|航空公司官网)",
    re.IGNORECASE,
)
GENERIC_TITLE_PATTERN = re.compile(r"(?:旅游攻略|旅行攻略|旅行计划|行程规划)\s*$")
GENERIC_HEADING_PATTERN = re.compile(r"^(?:#+\s*)?(?:先给结论|路线总览|分日安排|住哪里|吃什么|交通|预算|风险与备选|出发前准备|信息来源|常见问题|写在最后)\s*$", re.MULTILINE)
SOURCE_END_HEADING_PATTERN = re.compile(
    r"(?:^\s*#{1,4}\s*(?:图片与信息来源|信息来源与出发前复查|信息来源|参考资料|来源|图片来源|资料来源)\s*$|"
    r"<h[1-4][^>]*>\s*(?:图片与信息来源|信息来源与出发前复查|信息来源|参考资料|来源|图片来源|资料来源)\s*</h[1-4]>)",
    re.IGNORECASE | re.MULTILINE,
)
DAY_PATTERN = re.compile(r"(?:Day\s*\d+|第\s*\d+\s*天|D\d+)", re.IGNORECASE)
RICHNESS_PATTERN = re.compile(r"(?:为什么|取舍|不建议|删掉|可删减|撤退点|备选|下雨|雨天|疲劳|排队|没票|预约失败|闭馆|Q&A|FAQ|常见问题|怎么改|替代)")
VISUAL_SYSTEM_PATTERN = re.compile(r"(?:封面|路线图|地图|Day\s*图|时间轴|美食图鉴|点单卡|预算卡|避坑卡|视觉卡|图片尺寸|同尺寸|同规格|图注)")
GENERATED_VISUAL_PATTERN = re.compile(
    r"(?:生成图|AI\s*生成|根据本文行程生成|手绘路线卡|路线方向卡|美食图鉴|点单卡|住宿区域卡|预算卡|避坑卡|交通衔接卡|晴雨两案卡|中转时间账|时间轴卡)",
    re.IGNORECASE,
)
SCENE_CARD_PATTERN = re.compile(
    r"(?:路线结论|最顺路线|推荐保留|优先保留|今日主线|高光|可删减|撤退点|雨天替代|疲劳|排队|预约失败|预算卡|预订清单|风险卡|避坑|点单|Q&A|现场怎么改|保守版|进取版)"
)
XML_TITLE_PATTERN = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
XML_HEADING_PATTERN = re.compile(r"<h[12][^>]*>(.*?)</h[12]>", re.IGNORECASE | re.DOTALL)
XML_SECTION_HEADING_PATTERN = re.compile(r"<h[2-4]\b", re.IGNORECASE)
IMG_TAG_PATTERN = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
VISUAL_TAG_PATTERN = re.compile(r"<(?:img|bookmark)\b[^>]*>", re.IGNORECASE)
MARKDOWN_HEADING_PATTERN = re.compile(r"^\s*(#{1,2})\s+(.+?)\s*$", re.MULTILINE)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
ALLOWED_FEISHU_TAGS = {
    "title",
    "h1",
    "h2",
    "h3",
    "p",
    "b",
    "i",
    "br",
    "callout",
    "grid",
    "column",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "checkbox",
    "bookmark",
    "blockquote",
    "hr",
    "img",
    "image",
}

PROMISE_PATTERNS = [
    re.compile(r"图片与信息来源"),
    re.compile(r"图片说明"),
    re.compile(r"图片来自"),
    re.compile(r"景点及美食图片"),
    re.compile(r"目的地图片"),
    re.compile(r"美食图片"),
]

INTERNAL_PLANNING_PATTERNS = [
    re.compile(r"图片与视觉规划"),
    re.compile(r"图片需求清单"),
    re.compile(r"交付状态"),
    re.compile(r"必须插入"),
]

INTERNAL_TOOL_STATUS_PATTERNS = [
    re.compile(r"发现当前版本.*lark-?cli", re.IGNORECASE),
    re.compile(r"当前版本.*lark-?cli.*(?:没有|无).*(?:auth|skills|命令|子命令)", re.IGNORECASE),
    re.compile(r"lark-?cli.*(?:没有|无).*(?:auth|skills)\s*(?:命令|子命令)?", re.IGNORECASE),
    re.compile(r"(?:没有|无)\s*(?:auth|skills)\s*(?:命令|子命令)", re.IGNORECASE),
    re.compile(r"lark-?cli.*(?:权限|认证|登录|scope|token|fallback|降级|工具不可用|命令不可用)", re.IGNORECASE),
    re.compile(r"后续需考虑替代方案|确认是否为预期情况|当前环境已暴露|飞书工具不可用"),
    re.compile(r"这可能会影响相关操作"),
]

SELF_DISCLOSURE_PATTERNS = [
    re.compile(r"部分内容由.*生成"),
    re.compile(r"本攻略由.*生成"),
    re.compile(r"由(?:豆包|AI|大模型|模型|智能体|工具|skill|Skill).*生成"),
    re.compile(r"关于本攻略|生成方式|欢迎分享|祝你旅途愉快|祝.*旅行愉快"),
]

HTML_FORM_LEAK_PATTERNS = [
    re.compile(r"<input\b[^>]*>", re.IGNORECASE),
    re.compile(r"&lt;input\b[^&]*(?:&gt;|>)?", re.IGNORECASE),
    re.compile(r"</?(?:button|select|textarea|label|form)\b[^>]*>", re.IGNORECASE),
    re.compile(r"&lt;/?(?:button|select|textarea|label|form)\b[^&]*(?:&gt;|>)?", re.IGNORECASE),
]

INTERNAL_ANCHOR_LEAK_PATTERNS = [
    re.compile(r"【[^】]{0,50}(?:锚点|anchor|插图|图片位置|封面锚点)[^】]{0,50}】", re.IGNORECASE),
    re.compile(r"\[[^\]]{0,50}(?:锚点|anchor|插图|图片位置|封面锚点)[^\]]{0,50}\]", re.IGNORECASE),
    re.compile(r"(?:封面|Day\s*\d+|第\s*\d+\s*天|图片|插图)[^\n<]{0,12}锚点", re.IGNORECASE),
]

BAD_IMAGE_PLAN_ANCHOR_PATTERN = re.compile(
    r"(?:锚点|anchor|插图位置|图片位置|封面锚点|^【.*】$|^\[.*\]$)",
    re.IGNORECASE,
)

WEEKEND_PATTERNS = [
    re.compile(r"本周末|下周末|周末|近期|未来一个月|演出|演唱会|展览|集市|市集|球赛|city\s*walk", re.IGNORECASE),
]

BOOKING_PATTERNS = [
    re.compile(r"机票|酒店|门票|预算|积分|里程|现金|优惠|穷游|省钱|比价|预订", re.IGNORECASE),
]

FOOD_SIGNAL_PATTERN = re.compile(r"美食|小吃|夜市|点单|餐饮|早餐|午餐|晚餐|正餐|烧烤|火锅|手抓饭|舂鸡脚|泡鲁达|包烧|咖啡|茶|甜品|人均")
ATTRACTION_SIGNAL_PATTERN = re.compile(r"景点|公园|博物馆|古城|寺|总佛寺|植物园|野象谷|森林公园|夜市|街区|地标|风景|山|海|湖|草原|入口|拍照|打卡")
ROUTE_SIGNAL_PATTERN = re.compile(r"路线|路书|Day\s*\d+|第\s*\d+\s*天|交通|转场|住宿|酒店|民宿|区域|地铁|打车|自驾|步行|机场|高铁|车站")
ROUTE_VISUAL_PATTERN = re.compile(r"路线|地图|手绘|交通|方向|时间轴|Day\s*\d+|区域|住宿|中转|衔接|地铁|高铁|机场|车站|出口|路书|转场|换乘|线路", re.IGNORECASE)
FOOD_VISUAL_PATTERN = re.compile(r"美食|图鉴|点单|菜|夜市|餐|小吃|烧烤|火锅|饮品", re.IGNORECASE)
ATTRACTION_VISUAL_PATTERN = re.compile(r"景点|风景|地标|街区|古城|公园|寺|博物馆|植物园|夜市|酒店|入口|实景|照片|博物院|美术馆|科技馆|纪念馆|故居|遗址|景区|广场|陵|塔|楼|阁|宫|庙|湖|钟楼|城墙|古镇", re.IGNORECASE)
BUDGET_ONLY_VISUAL_PATTERN = re.compile(r"预算|budget|饼图|成本|花.*钱|省钱|价格|费用", re.IGNORECASE)


def count_matches(patterns: list[re.Pattern[str]], text: str) -> int:
    return sum(len(pattern.findall(text)) for pattern in patterns)


def normalize_heading(value: str) -> str:
    value = HTML_TAG_PATTERN.sub("", value)
    value = re.sub(r"[*_`~#>\s]+", "", value)
    value = re.sub(r"[|｜:：,，。.!！?？、\-—_（）()\[\]【】《》\"“”'‘’]", "", value)
    return value.lower()


def unknown_xml_tags(text: str) -> list[str]:
    tags: list[str] = []
    for match in re.finditer(r"</?\s*([A-Za-z][A-Za-z0-9_-]*)\b[^>]*>", text):
        tag = match.group(1).lower()
        if tag not in ALLOWED_FEISHU_TAGS:
            tags.append(match.group(0)[:120])
    return tags


def repeated_title_issue(text: str) -> str | None:
    xml_title_match = XML_TITLE_PATTERN.search(text)
    if xml_title_match:
        title = normalize_heading(xml_title_match.group(1))
        if title:
            after_title = text[xml_title_match.end() : xml_title_match.end() + 1200]
            first_heading = XML_HEADING_PATTERN.search(after_title)
            if first_heading and normalize_heading(first_heading.group(1)) == title:
                return "Feishu/XML title is repeated immediately as body H1/H2. Keep the title only in the Feishu title area and start body with conclusion/route/risk content."

    headings = [(match.group(1), match.group(2).strip()) for match in MARKDOWN_HEADING_PATTERN.finditer(text)]
    if len(headings) >= 2:
        first = normalize_heading(headings[0][1])
        second = normalize_heading(headings[1][1])
        if first and second and first == second:
            return "First two Markdown headings are identical. Do not repeat the document title as the first body heading."

    if headings:
        first_heading = normalize_heading(headings[0][1])
        leading_text = text[: text.find(headings[0][1])]
        title_like_lines = [
            normalize_heading(line)
            for line in leading_text.splitlines()
            if line.strip() and not line.strip().startswith((">", "-", "*", "|"))
        ]
        if first_heading and title_like_lines and title_like_lines[-1] == first_heading:
            return "Body appears to repeat a title already shown above it. Remove the duplicate body title and start with useful trip content."

    return None


def is_real_image(path: Path) -> bool:
    try:
        data = path.read_bytes()[:16]
    except OSError:
        return False
    return (
        data.startswith(b"\x89PNG\r\n\x1a\n")
        or data.startswith(b"\xff\xd8\xff")
        or data.startswith(b"GIF87a")
        or data.startswith(b"GIF89a")
        or (data.startswith(b"RIFF") and data[8:12] == b"WEBP")
    )


def load_image_plan(plan_path: Path) -> tuple[list[dict[str, str]], list[str]]:
    errors: list[str] = []
    if not plan_path.is_file():
        return [], [f"Image plan file does not exist: {plan_path}"]
    try:
        with plan_path.open(encoding="utf-8", newline="") as f:
            sample = f.read(4096)
            f.seek(0)
            delimiter = "\t" if "\t" in sample else ","
            reader = csv.DictReader(f, delimiter=delimiter)
            if not reader.fieldnames:
                return [], [f"Image plan has no header: {plan_path}"]
            rows = [{str(k).strip(): str(v).strip() for k, v in row.items() if k and v is not None} for row in reader]
            return rows, errors
    except Exception as exc:
        return [], [f"Could not read image plan {plan_path}: {exc}"]


def auto_image_plan_path(xml_file: Path, explicit: Path | None) -> Path | None:
    if explicit:
        return explicit
    base_dir = xml_file.resolve().parent
    for candidate in (base_dir / "image-plan.tsv", base_dir / "image-plan.csv"):
        if candidate.is_file():
            return candidate
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Check travel guide image promises and Feishu visual quality.")
    parser.add_argument("file", type=Path, help="guide xml/md/html/text file")
    parser.add_argument("--image-plan", type=Path, help="Sidecar TSV/CSV with file, anchor, caption, role, width, source, status, reason")
    args = parser.parse_args()

    path = args.file
    text = path.read_text(encoding="utf-8")
    image_count = count_matches(IMAGE_PATTERNS, text)
    img_tags = IMG_TAG_PATTERN.findall(text)
    visual_tags = VISUAL_TAG_PATTERN.findall(text)
    visual_tag_text = " ".join(visual_tags)
    budget_image_count = sum(1 for tag in img_tags if BUDGET_ONLY_VISUAL_PATTERN.search(tag))
    route_visual_count = len(ROUTE_VISUAL_PATTERN.findall(visual_tag_text)) + len(
        ROUTE_VISUAL_PATTERN.findall(" ".join(GENERATED_VISUAL_PATTERN.findall(text)))
    )
    food_visual_count = len(FOOD_VISUAL_PATTERN.findall(visual_tag_text))
    attraction_visual_count = len(ATTRACTION_VISUAL_PATTERN.findall(visual_tag_text))
    promise_count = count_matches(PROMISE_PATTERNS, text)
    internal_count = count_matches(INTERNAL_PLANNING_PATTERNS, text)
    internal_tool_status_count = count_matches(INTERNAL_TOOL_STATUS_PATTERNS, text)
    self_disclosure_count = count_matches(SELF_DISCLOSURE_PATTERNS, text)
    html_form_leak_count = count_matches(HTML_FORM_LEAK_PATTERNS, text)
    internal_anchor_leak_count = count_matches(INTERNAL_ANCHOR_LEAK_PATTERNS, text)
    unknown_tag_hits = unknown_xml_tags(text)
    bullet_count = len(BULLET_PATTERN.findall(text))
    markdown_table_count = len(TABLE_PATTERN.findall(text))
    xml_table_count = len(XML_TABLE_PATTERN.findall(text))
    table_count = markdown_table_count + xml_table_count
    callout_count = len(CALLOUT_PATTERN.findall(text))
    grid_count = len(GRID_PATTERN.findall(text))
    checkbox_count = len(CHECKBOX_PATTERN.findall(text))
    bookmark_count = len(BOOKMARK_PATTERN.findall(text))
    blockquote_count = len(BLOCKQUOTE_PATTERN.findall(text))
    hr_count = len(HR_PATTERN.findall(text))
    semantic_color_values = SEMANTIC_COLOR_PATTERN.findall(text)
    semantic_color_families = {
        match.group(1).lower().replace("grey", "gray")
        for value in semantic_color_values
        for match in [SEMANTIC_COLOR_FAMILY_PATTERN.search(value)]
        if match
    }
    semantic_color_count = len(semantic_color_families)
    scene_card_count = len(SCENE_CARD_PATTERN.findall(text))
    rich_count = image_count + table_count + len(CALLOUTISH_PATTERN.findall(text))
    weekend_signal_count = count_matches(WEEKEND_PATTERNS, text)
    booking_signal_count = count_matches(BOOKING_PATTERNS, text)
    date_count = len(DATE_PATTERN.findall(text))
    booking_action_count = len(BOOKING_ACTION_PATTERN.findall(text))
    weather_strategy_count = len(WEATHER_STRATEGY_PATTERN.findall(text))
    day_execution_count = len(DAY_EXECUTION_PATTERN.findall(text))
    booking_entry_count = len(BOOKING_ENTRY_PATTERN.findall(text))
    generic_heading_count = len(GENERIC_HEADING_PATTERN.findall(text))
    day_count = len(DAY_PATTERN.findall(text))
    food_signal_count = len(FOOD_SIGNAL_PATTERN.findall(text))
    attraction_signal_count = len(ATTRACTION_SIGNAL_PATTERN.findall(text))
    route_signal_count = len(ROUTE_SIGNAL_PATTERN.findall(text))
    richness_count = len(RICHNESS_PATTERN.findall(text))
    visual_system_count = len(VISUAL_SYSTEM_PATTERN.findall(text))
    generated_visual_count = len(GENERATED_VISUAL_PATTERN.findall(text))
    visual_anchor_count = image_count + bookmark_count + generated_visual_count
    real_bookmark_count = count_matches(
        [re.compile(r'<bookmark\b[^>]*href\s*=\s*["\']https?://(?!example\.com|placeholder\.)', re.IGNORECASE)], text
    )
    placeholder_url_count = count_matches(
        [re.compile(r"https?://(?:example\.com|placeholder\.)", re.IGNORECASE)], text
    )
    img_href_external = count_matches([re.compile(r'<img\b[^>]*href\s*=\s*["\']https?://', re.IGNORECASE)], text)
    img_src_token_count = count_matches([re.compile(r'<img\b[^>]*src\s*=\s*["\'][A-Za-z0-9_-]{8,}', re.IGNORECASE)], text)
    base_dir = path.resolve().parent
    image_plan_path = auto_image_plan_path(path, args.image_plan)
    image_plan_entries: list[dict[str, str]] = []
    image_plan_errors: list[str] = []
    if image_plan_path is not None:
        image_plan_entries, image_plan_errors = load_image_plan(image_plan_path)

    def resolve_local(rel: str) -> Path | None:
        p = Path(rel)
        candidates = [p, base_dir / p, base_dir / p.name]
        if image_plan_path is not None:
            plan_dir = image_plan_path.resolve().parent
            candidates.extend([plan_dir / p, plan_dir / p.name])
        anc = base_dir
        for _ in range(5):
            candidates.append(anc / p)
            if anc.parent == anc:
                break
            anc = anc.parent
        # also search one level down (visuals/) since markers often use just the filename
        for sub in ("visuals", "visuals/normalized"):
            candidates.append(base_dir / sub / p)
            candidates.append(base_dir / sub / p.name)
        for candidate in candidates:
            if candidate.is_file() and candidate.stat().st_size > 0:
                return candidate
        return None

    existing_local_images: list[str] = []
    missing_local_images: list[str] = []
    invalid_local_images: list[str] = []
    incomplete_image_plan_rows: list[str] = []
    bad_image_plan_anchors: list[str] = []
    long_captions: list[str] = []
    bad_widths: list[str] = []
    unnormalized_files: list[str] = []
    for index, entry in enumerate(image_plan_entries, start=1):
        status = (entry.get("status") or "").strip().lower()
        if status and status not in {"ready", "insert", "ok"}:
            continue
        file_value = entry.get("file") or entry.get("path") or entry.get("image") or entry.get("filename")
        anchor = entry.get("anchor") or entry.get("selection") or entry.get("selection_with_ellipsis")
        caption = entry.get("caption") or ""
        width_raw = entry.get("width") or ""
        if not file_value or not anchor or not caption or not width_raw:
            incomplete_image_plan_rows.append(f"row {index} missing file/anchor/caption/width: {entry}")
            continue
        if BAD_IMAGE_PLAN_ANCHOR_PATTERN.search(anchor):
            bad_image_plan_anchors.append(f"row {index}: {anchor}")
        if "normalized" not in file_value.replace("\\", "/"):
            unnormalized_files.append(file_value)
        caption_text = re.sub(r"\s+", "", caption)
        if len(caption_text) > 18 or "\n" in caption or "来源" in caption:
            long_captions.append(f"row {index}: {caption}")
        try:
            width = int(re.sub(r"[^0-9]", "", width_raw))
        except ValueError:
            width = 0
        if width < 260 or width > 680:
            bad_widths.append(f"row {index}: {width_raw}")
        local_path = resolve_local(file_value)
        if local_path is None:
            missing_local_images.append(file_value)
        elif not is_real_image(local_path):
            invalid_local_images.append(f"{file_value} -> {local_path}")
        else:
            existing_local_images.append(file_value)
    real_image_count = img_src_token_count + len(existing_local_images)
    stale_media_marker_count = count_matches([re.compile(r'<!--\s*(media:|插图位置)', re.IGNORECASE)], text)
    leaked_xml_fields = len(re.findall(r'caption\s*=\s*"|anchor\s*=\s*"|来源：生成图|来源：搜图', text, re.IGNORECASE))
    real_visual_anchor_count = real_image_count + real_bookmark_count
    xml_section_heading_count = len(XML_SECTION_HEADING_PATTERN.findall(text))
    first_heading = next((line.strip().lstrip("#").strip() for line in text.splitlines() if line.strip().startswith("#")), "")
    substantial_doc = len(text) >= 2500 or day_count >= 2 or table_count >= 6 or xml_section_heading_count >= 2

    errors: list[str] = []
    warnings: list[str] = []
    duplicate_title_error = repeated_title_issue(text)
    if duplicate_title_error:
        errors.append(duplicate_title_error)
    if self_disclosure_count:
        errors.append(
            "Document exposes AI/tool self-disclosure or marketing tail. Remove 部分内容由...生成/本攻略由...生成/欢迎分享/祝旅途愉快 from the guide body."
        )
    if html_form_leak_count:
        errors.append(
            "Document exposes raw HTML form tag(s), commonly <input type=\"checkbox\" />. Feishu XML checklists must use <checkbox done=\"false\">item text</checkbox>; Markdown fallback uses '- [ ] item text'. Remove all HTML input/button/select/textarea/label/form tags from the visible body."
        )
    if internal_anchor_leak_count:
        errors.append(
            "Document exposes internal image anchor placeholder(s), such as 【封面锚点-...】 or 【Day2...锚点】. Delete these markers from the visible body. Image-plan anchors must point to a normal sentence already present in the guide, not to a fake placeholder label."
        )
    if first_heading and GENERIC_TITLE_PATTERN.search(first_heading) and len(first_heading) <= 18:
        warnings.append(
            "Title appears generic. Prefer a scenario-specific form such as 路线/路书/地图/雷达/时间账/决策表/手册."
        )
    if generic_heading_count >= 6:
        errors.append(
            "Too many generic headings (more than 5). Rewrite some around the destination, dates, traveler type, budget, route, or theme."
        )
    if SOURCE_END_HEADING_PATTERN.search(text):
        errors.append(
            "Do not add a final source/reference section. Remove 来源/信息来源/图片与信息来源/信息来源与出发前复查/参考资料 headings; place necessary sources beside the relevant fact, image caption, bookmark, or paragraph instead."
        )
    if promise_count and image_count == 0:
        errors.append(
            "Document promises images but contains no embedded image, visual card, or image/map link card. "
            "Remove image promises or insert real visuals near the relevant section. Do not add a final source section as a workaround."
        )
    if internal_count:
        errors.append(
            "Document appears to expose internal image planning fields. Remove 图片与视觉规划/图片需求清单/交付状态/必须插入 from final content."
        )
    if unknown_tag_hits:
        errors.append(
            f"Document contains unsupported/self-invented XML or HTML tag(s): {unknown_tag_hits[:8]}. Use only Feishu XML whitelist tags (title/h1/h2/h3/p/b/i/br/callout/grid/column/table/thead/tbody/tr/th/td/checkbox/bookmark/blockquote/hr/img). For card-like layouts, use callout + grid + table instead of <card> or custom tags."
        )
    if internal_tool_status_count:
        errors.append(
            "Document exposes internal lark-cli/tool compatibility status. Remove lark-cli auth/skills/version/permission/fallback notes from the user-facing guide."
        )
    if image_plan_errors:
        errors.extend(image_plan_errors)
    if incomplete_image_plan_rows:
        errors.append(
            f"image-plan rows are incomplete; each ready row must include file/anchor/caption/width: {incomplete_image_plan_rows}"
        )
    if bad_image_plan_anchors:
        errors.append(
            f"image-plan anchor values look like internal placeholder labels instead of natural body text: {bad_image_plan_anchors}. Use an exact normal sentence from the guide as the anchor; do not use words like 锚点/anchor/插图位置."
        )
    if unnormalized_files:
        errors.append(
            f"image-plan must use standardized files under visuals/normalized, not raw images: {unnormalized_files}"
        )
    if long_captions:
        errors.append(
            f"image captions are too long or include source/newlines, which causes caption wrapping like the screenshot. Keep captions <=18 Chinese chars, e.g. 图：青岛栈桥. Bad captions: {long_captions}"
        )
    if bad_widths:
        errors.append(
            f"image-plan width must be explicit and between 260 and 680. Use 560 for body photos, 360-420 for 2-column gallery, 260-320 for 3-column gallery, 640 for cover/route. Bad widths: {bad_widths}"
        )
    if invalid_local_images:
        errors.append(
            f"image-plan references files that exist but are not real PNG/JPEG/GIF/WebP images: {invalid_local_images}"
        )
    if bullet_count >= 35 and rich_count < 12:
        errors.append(
            "Document is likely too list-heavy. Add richer structure: route tables, Day cards, callouts, grids, checkboxes, visual/link cards, and explanatory paragraphs."
        )
    if substantial_doc:
        guide_like_doc = day_count >= 1 or route_signal_count >= 6 or attraction_signal_count >= 4
        if guide_like_doc and weather_strategy_count < 2:
            errors.append(
                "clarity-floor: Full travel guide lacks a weather/season strategy. Add current forecast when dates are known, or seasonal climate/rain/heat/cold risks when dates are unknown, plus a 48-hour recheck action and route adjustments."
            )
        if day_count >= 2 and day_execution_count < 12:
            errors.append(
                "clarity-floor: Multi-day guide does not explain 'how to play' at action level. Each Day needs time bands, transport/walking, meal landing, booking/queue notes, removable items, retreat point, and weather/fatigue alternatives."
            )
        if (day_count >= 2 or attraction_signal_count >= 5 or booking_signal_count >= 4) and booking_entry_count < 2:
            errors.append(
                "booking-floor: Guide mentions itinerary/attractions/booking but lacks enough concrete booking or reservation entrances. Add nearby real <bookmark> links or official app/map/search paths for core attractions, transport, hotels, shows, museums, or restaurants; do not only say '提前预约'."
            )
        if real_image_count == 0:
            errors.append(
                "image-floor: Full Feishu travel guide has NO real image. Search/generate an image, curl it to outputs/.../visuals/raw/, normalize it to visuals/normalized/, record it in image-plan.tsv, then insert with +media-insert --file <local> --selection-with-ellipsis <anchor> --width <width>. A bookmark does NOT count."
            )
        if img_href_external:
            errors.append(
                f"Found {img_href_external} <img href=\"external-URL\"> — Feishu server-side fetch returns 403 for many sources (anti-hotlink). Download the image locally with curl -A \"Mozilla/5.0\" and use +media-insert --file <local> instead. See SKILL.md '图片怎么进飞书'."
            )
        if missing_local_images:
            errors.append(
                f"image-plan references local image files that do not exist: {missing_local_images}. Download raw images, normalize to visuals/normalized, and point image-plan file values at normalized files before creating the doc."
            )
        if stale_media_marker_count:
            errors.append(
                f"Found {stale_media_marker_count} planning marker(s) (<!-- 插图位置 --> or <!-- media: -->) in the XML body. Do not put image markers in Feishu XML; use sidecar image-plan.tsv instead. Markers can leak into the document and cause broken spacing."
            )
        if leaked_xml_fields:
            errors.append(
                f"Found {leaked_xml_fields} leaked internal field(s) (caption=\"/anchor=\"/来源：生成图/来源：搜图) in the body. These are for the tool/script, not the user. Delete them; the image caption is passed via +media-insert --caption, not written in the body."
            )
        if placeholder_url_count:
            errors.append(
                "placeholder-url: Document contains example.com/placeholder URLs. Replace with real verified source links or remove the bookmark."
            )
        if callout_count < 3 or grid_count < 1 or checkbox_count < 1 or (bookmark_count + blockquote_count) < 1:
            errors.append(
                "visual-floor: Full Feishu travel documents need a non-image visual floor in addition to the required image/generated visual: at least 3 callouts, 1 grid, 1 checkbox group, and 1 bookmark/blockquote."
            )
        if semantic_color_count < 3:
            errors.append(
                "visual-floor: Feishu document lacks semantic color variety. Use at least 3 color families among blue/green/yellow/gray for conclusion, recommendation, risk, and source/boundary blocks."
            )
        if scene_card_count < 2:
            errors.append(
                "visual-floor: Feishu document lacks scenario cards. Add at least 2 route/Day/budget/risk/food/Q&A cards with concrete travel decisions."
            )
        if real_bookmark_count == 0 and (day_count >= 2 or booking_signal_count >= 6 or attraction_signal_count >= 6 or food_signal_count >= 5):
            errors.append(
                "source/action-floor: Full travel documents need at least one relevant bookmark/link card (non-example.com) near a dynamic fact, official ticket page, map entrance, attraction, hotel area, food reference, or transport source. A blockquote is not enough."
            )
        if day_count >= 3 and real_visual_anchor_count < 2:
            errors.append(
                "multi-day-visual-floor: A complex multi-day guide has too few real visual anchors (real images or real bookmarks). Add a route/area map or generated route card plus a food/attraction/hotel/booking visual or bookmark near the relevant section."
            )
        if day_count >= 3 and image_count > 0 and image_count == budget_image_count and (route_signal_count >= 8 or food_signal_count >= 6 or attraction_signal_count >= 6):
            errors.append(
                "visual-mismatch: The only embedded image appears to be a budget/cost visual while the guide contains route, attraction, and food decisions. Add a route/area visual and at least one real-object/food/attraction/map visual or bookmark."
            )
        if day_count >= 3 and (route_visual_count + food_visual_count + attraction_visual_count) == 0 and (route_signal_count >= 8 or food_signal_count >= 6 or attraction_signal_count >= 6):
            errors.append(
                "visual-coverage: Multi-day guides must visually support at least one core route, food, attraction, street, hotel-area, or map decision. A generic/budget-only image does not satisfy the travel-guide visual requirement."
            )
        if table_count >= 6 and (callout_count < 3 or grid_count < 1):
            errors.append(
                "table-heavy: Document uses many tables but too few colorful Feishu components. Tables plus hr/checkbox are not enough visual design; add callouts and grid cards."
            )
        dish_rows = len(re.findall(r"<tr>\s*<td>[^<]+</td>", text, re.IGNORECASE))
        # 通用信号:文档列了多个"值得配图的对象"(景点/美食/街区/天)但图明显偏少 → 列多配少
        object_signal = attraction_signal_count + food_signal_count + route_signal_count + dish_rows
        if day_count >= 3 and real_image_count < 2:
            errors.append(
                f"content-image-mismatch: Multi-day guide lists many objects (attractions/food/days, signal={object_signal}) but only {real_image_count} image(s). Images should follow content: list several attractions/dishes → add a photo for each and show them side-by-side via <grid>. Don't list many objects with 1 photo."
            )
        elif object_signal >= 12 and real_image_count < 3:
            warnings.append(
                f"Guide lists many photo-worthy objects (signal={object_signal}) but only {real_image_count} image(s). Consider adding one photo per key attraction/dish, shown side-by-side via <grid>."
            )
        elif (food_signal_count >= 4 or dish_rows >= 3) and real_image_count < 2:
            errors.append(
                f"food-image-floor: Guide lists multiple dishes (food_signal={food_signal_count}, dish_rows={dish_rows}) but only {real_image_count} image(s). Add a photo per key dish (or a multi-dish collage) and show them side-by-side via <grid>."
            )
    if substantial_doc and real_image_count == 0 and real_bookmark_count > 0:
        warnings.append(
            "Guide uses bookmarks but no inserted image. Bookmarks are link cards, not images. Add a normalized local image through image-plan.tsv and +media-insert --width."
        )
    if substantial_doc and real_image_count == 1:
        warnings.append(
            "single-image: Full guide has only 1 image. If the guide lists multiple photo-worthy objects (attractions/dishes), add one photo per key object and show side-by-side via <grid>."
        )
    if weekend_signal_count >= 3 and date_count < 2:
        errors.append(
            "Document appears to cover weekend/recent activities but lacks concrete dates. Lock relative time to absolute dates and verify event windows."
        )
    if booking_signal_count >= 6 and booking_action_count < 3:
        errors.append(
            "Document appears to discuss budget/booking but lacks booking path details. Add where/when to book, what to confirm, cancellation/stock risk, and fallback."
        )
    if day_count >= 2 and not re.search(r"撤退点|可删减|下雨|雨天|疲劳|排队|预约失败|闭馆|没票|备选", text):
        errors.append(
            "Multi-day itinerary lacks deletion/retreat/fallback logic. Add per-day removable items and weather/fatigue/queue alternatives."
        )
    if day_count >= 2 and richness_count < 6:
        warnings.append(
            "Guide may be thin on decision value. Add why-this-route, what to skip, food ordering, fallback, and scenario-specific Q&A."
        )
    if promise_count and image_count > 0 and visual_system_count < 3:
        warnings.append(
            "Images are present/promised but visual system is under-specified. Ensure cover/route/Day/food/budget cards use consistent sizes and captions."
        )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        for warning in warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
        print(
            f"image_count={image_count} promise_count={promise_count} internal_count={internal_count} "
            f"internal_tool_status_count={internal_tool_status_count} "
            f"html_form_leak_count={html_form_leak_count} "
            f"internal_anchor_leak_count={internal_anchor_leak_count} "
            f"unknown_tag_count={len(unknown_tag_hits)} "
            f"self_disclosure_count={self_disclosure_count} visual_anchor_count={visual_anchor_count} "
            f"budget_image_count={budget_image_count} route_visual_count={route_visual_count} "
            f"food_visual_count={food_visual_count} attraction_visual_count={attraction_visual_count} "
            f"bullet_count={bullet_count} table_count={table_count} rich_count={rich_count} "
            f"callout_count={callout_count} grid_count={grid_count} checkbox_count={checkbox_count} "
            f"bookmark_count={bookmark_count} blockquote_count={blockquote_count} hr_count={hr_count} "
            f"semantic_color_count={semantic_color_count} scene_card_count={scene_card_count} "
            f"weekend_signal_count={weekend_signal_count} date_count={date_count} "
            f"booking_signal_count={booking_signal_count} booking_action_count={booking_action_count} "
            f"food_signal_count={food_signal_count} attraction_signal_count={attraction_signal_count} "
            f"route_signal_count={route_signal_count} "
            f"generic_heading_count={generic_heading_count} day_count={day_count} "
            f"weather_strategy_count={weather_strategy_count} day_execution_count={day_execution_count} "
            f"booking_entry_count={booking_entry_count} "
            f"richness_count={richness_count} visual_system_count={visual_system_count} "
            f"generated_visual_count={generated_visual_count} xml_section_heading_count={xml_section_heading_count}",
            file=sys.stderr,
        )
        return 1

    for warning in warnings:
        print(f"WARNING: {warning}")
    print(
        f"OK image_count={image_count} promise_count={promise_count} internal_count={internal_count} "
        f"internal_tool_status_count={internal_tool_status_count} "
        f"html_form_leak_count={html_form_leak_count} "
        f"internal_anchor_leak_count={internal_anchor_leak_count} "
        f"unknown_tag_count={len(unknown_tag_hits)} "
        f"self_disclosure_count={self_disclosure_count} visual_anchor_count={visual_anchor_count} "
        f"budget_image_count={budget_image_count} route_visual_count={route_visual_count} "
        f"food_visual_count={food_visual_count} attraction_visual_count={attraction_visual_count} "
        f"bullet_count={bullet_count} table_count={table_count} rich_count={rich_count} "
        f"callout_count={callout_count} grid_count={grid_count} checkbox_count={checkbox_count} "
        f"bookmark_count={bookmark_count} blockquote_count={blockquote_count} hr_count={hr_count} "
        f"semantic_color_count={semantic_color_count} scene_card_count={scene_card_count} "
        f"weekend_signal_count={weekend_signal_count} date_count={date_count} "
        f"booking_signal_count={booking_signal_count} booking_action_count={booking_action_count} "
        f"food_signal_count={food_signal_count} attraction_signal_count={attraction_signal_count} "
        f"route_signal_count={route_signal_count} "
        f"generic_heading_count={generic_heading_count} day_count={day_count} "
        f"weather_strategy_count={weather_strategy_count} day_execution_count={day_execution_count} "
        f"booking_entry_count={booking_entry_count} "
        f"richness_count={richness_count} visual_system_count={visual_system_count} "
        f"generated_visual_count={generated_visual_count} xml_section_heading_count={xml_section_heading_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
