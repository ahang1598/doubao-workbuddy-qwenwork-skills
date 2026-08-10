#!/usr/bin/env python3
"""Lightweight quality checks for generated fitness-guide drafts.

XML mode is auto-detected: a file ending in .xml, or containing <title>/<callout/
<bookmark, is treated as Feishu XML-rich even without --xml. This keeps weak
models from skipping all structural checks by forgetting the --xml flag.

Usage:
  python3 check_fitness_quality.py path/to/output.txt
  python3 check_fitness_quality.py --xml path/to/doc.xml
  python3 check_fitness_quality.py path/to/doc.xml   # auto-detected as XML
  python3 check_fitness_quality.py --final fetched_doc.xml
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


def count(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text, flags=re.I | re.M))


def has(pattern: str, text: str) -> bool:
    return re.search(pattern, text, flags=re.I | re.M) is not None


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


def unknown_xml_tags(text: str) -> list[str]:
    tags: list[str] = []
    for match in re.finditer(r"</?\s*([A-Za-z][A-Za-z0-9_-]*)\b[^>]*>", text):
        tag = match.group(1).lower()
        if tag not in ALLOWED_FEISHU_TAGS:
            tags.append(match.group(0)[:120])
    return tags


INTERNAL_TOOL_STATUS_PATTERNS = [
    r"发现当前版本.*lark-?cli",
    r"当前版本.*lark-?cli.*(?:没有|无).*(?:auth|skills|命令|子命令)",
    r"lark-?cli.*(?:没有|无).*(?:auth|skills)\s*(?:命令|子命令)?",
    r"(?:没有|无)\s*(?:auth|skills)\s*(?:命令|子命令)",
    r"lark-?cli.*(?:权限|认证|登录|scope|token|fallback|降级|工具不可用|命令不可用)",
    r"后续需考虑替代方案|确认是否为预期情况|当前环境已暴露|飞书工具不可用",
    r"这可能会影响相关操作",
]

DELIVERY_LEAK_PATTERNS = [
    r"未找到.*(?:可稳定下载|稳定下载|可下载|权威).*图",
    r"没找到.*(?:可稳定下载|稳定下载|可下载|权威).*图",
    r"无法.*(?:可稳定下载|稳定下载|下载).*图",
    r"正文用.*(?:视频链接|动作卡).*(?:补足|替代)",
    r"(?:视频链接|动作卡).*补足.*不影响执行",
    r"不影响执行",
    r"需要(?:你)?补充(?:的)?信息",
    r"(?:请|需要|还需要)(?:你)?(?:提供|补充).{0,30}(?:信息|情况|基础|时间|伤病|疼痛|旧伤|不适)",
    r"(?:补充|提供).{0,20}后(?:可以|可|能).{0,30}(?:细化|调整|选择|优化)",
    r"文末(?:附了|有|设置了)?.*(?:待补充|需要你补充|补充问题)",
    r"(?:待补充|需要你补充).*(?:问题|信息)",
    r"补充后可.*(?:细化|进一步细化|调整)",
    r"后续可.*(?:细化|进一步细化|调整)",
    r"必要追问|待确认信息|补充确认的信息",
    r"no_reliable_image|image-plan\.tsv|media-insert",
]

HTML_FORM_LEAK_PATTERNS = [
    r"<input\b[^>]*>",
    r"&lt;input\b[^&]*(?:&gt;|>)?",
    r"</?(?:button|select|textarea|label|form)\b[^>]*>",
    r"&lt;/?(?:button|select|textarea|label|form)\b[^&]*(?:&gt;|>)?",
]

INTERNAL_ANCHOR_LEAK_PATTERNS = [
    r"【[^】]{0,50}(?:锚点|anchor|插图|图片位置|动作锚点|封面锚点)[^】]{0,50}】",
    r"\[[^\]]{0,50}(?:锚点|anchor|插图|图片位置|动作锚点|封面锚点)[^\]]{0,50}\]",
    r"(?:封面|动作|图片|插图|Day\s*\d+|第\s*\d+\s*天)[^\n<]{0,12}锚点",
]

BAD_IMAGE_PLAN_ANCHOR_PATTERN = re.compile(
    r"(?:锚点|anchor|插图位置|图片位置|动作锚点|封面锚点|^【.*】$|^\[.*\]$)",
    re.IGNORECASE,
)


def strip_tags(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def line_ratio(pattern: str, lines: list[str]) -> float:
    if not lines:
        return 0.0
    matched = sum(1 for line in lines if re.match(pattern, line.strip()))
    return matched / max(len(lines), 1)


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
        or data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    )


def load_image_plan(plan_path: Path) -> tuple[list[dict[str, str]], list[str]]:
    """Load a sidecar image plan. The plan is internal metadata, never doc body."""
    errors: list[str] = []
    if not plan_path.is_file():
        return [], [f"Image plan file does not exist: {plan_path}"]

    try:
        if plan_path.suffix.lower() == ".json":
            raw = json.loads(plan_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                raw = raw.get("images") or raw.get("items") or raw.get("plan") or []
            if not isinstance(raw, list):
                return [], [f"Image plan JSON must be a list or contain images/items/plan: {plan_path}"]
            rows = []
            for item in raw:
                if not isinstance(item, dict):
                    errors.append(f"Image plan JSON row is not an object: {item!r}")
                    continue
                rows.append({str(k).strip(): str(v).strip() for k, v in item.items() if v is not None})
            return rows, errors

        with plan_path.open(encoding="utf-8", newline="") as f:
            sample = f.read(4096)
            f.seek(0)
            delimiter = "\t" if "\t" in sample else ","
            reader = csv.DictReader(f, delimiter=delimiter)
            if not reader.fieldnames:
                return [], [f"Image plan TSV/CSV has no header: {plan_path}"]
            rows = []
            for row in reader:
                rows.append({str(k).strip(): str(v).strip() for k, v in row.items() if k and v is not None})
            return rows, errors
    except Exception as exc:  # pragma: no cover - defensive CLI guard
        return [], [f"Could not read image plan {plan_path}: {exc}"]


def auto_image_plan_path(xml_file: Path, explicit: Path | None) -> Path | None:
    if explicit:
        return explicit
    base_dir = xml_file.resolve().parent
    candidates = [
        base_dir / "image-plan.tsv",
        base_dir / "image-plan.json",
        base_dir / "visuals" / "image-plan.tsv",
        base_dir / "visuals" / "image-plan.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("--xml", action="store_true", help="Expect Feishu XML-ish rich text")
    parser.add_argument(
        "--stage",
        choices=("draft", "final"),
        default="draft",
        help="draft validates a sidecar image-plan file and local image files; final forbids internal markers and expects inserted Feishu images",
    )
    parser.add_argument("--final", action="store_true", help="Alias for --stage final")
    parser.add_argument(
        "--image-plan",
        type=Path,
        help="Sidecar TSV/JSON image plan for draft validation. Never put image markers in the XML body.",
    )
    args = parser.parse_args()
    stage = "final" if args.final else args.stage

    text = args.file.read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line.strip()]
    failures: list[str] = []
    warnings: list[str] = []

    training_hits = count(r"训练|动作|组|次数|RIR|RPE|力量|增肌|塑形|深蹲|俯卧撑|划船|硬拉|卧推|跑步", text)
    diet_hits = count(r"饮食|减脂|热量|食堂|外卖|蛋白|主食|蔬菜|奶茶|零食|夜宵|早餐|午餐|晚餐", text)
    plan_hits = count(r"计划|周期|每周|打卡|复盘|模板|日志|记录|进阶", text)
    technique_hits = count(r"起始姿势|执行路径|发力|常见错误|修正|降阶|进阶|停止条件|疼痛|自检", text)
    media_promises = count(r"视频|图片|图解|链接|资源|演示", text)
    url_hits = count(r"https?://|<bookmark|href=", text)
    image_hits = count(r"<img\b|!\[[^\]]*\]\([^)]+\)|\bimage\b|图片|图解|示意图|动作图|餐盘图|视觉图", text)
    generated_image_hits = count(r"image_gen|生成图|AI\s*生成图|生图|generated", text)
    img_href_external = count(r'<img\b[^>]*href\s*=\s*["\']https?://', text)
    img_src_token_count = count(r'<img\b[^>]*src\s*=\s*["\'][A-Za-z0-9_-]{8,}', text)
    base_dir = args.file.resolve().parent
    image_plan_path = auto_image_plan_path(args.file, args.image_plan)
    image_plan_entries: list[dict[str, str]] = []
    image_plan_errors: list[str] = []
    if stage == "draft" and image_plan_path is not None:
        image_plan_entries, image_plan_errors = load_image_plan(image_plan_path)

    def resolve_local(rel: str) -> Path | None:
        p = Path(rel)
        candidates = [p, base_dir / p, base_dir / p.name]
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

    local_image_paths: dict[str, Path] = {}
    missing_local_images: list[str] = []
    invalid_local_images: list[str] = []
    incomplete_image_plan_rows: list[str] = []
    bad_image_plan_anchors: list[str] = []
    for index, entry in enumerate(image_plan_entries, start=1):
        status = (entry.get("status") or "").strip().lower()
        if status in {"no_reliable_image", "not_found", "skipped", "omit"}:
            if not (entry.get("source") or entry.get("reason") or entry.get("purpose")):
                incomplete_image_plan_rows.append(
                    f"row {index} marked {status} but missing source/reason/purpose: {entry}"
                )
            continue
        file_value = entry.get("file") or entry.get("path") or entry.get("image") or entry.get("filename")
        anchor = entry.get("anchor") or entry.get("selection") or entry.get("selection_with_ellipsis")
        caption = entry.get("caption")
        if not file_value or not anchor or not caption:
            incomplete_image_plan_rows.append(
                f"row {index} missing file/anchor/caption: {entry}"
            )
            continue
        if BAD_IMAGE_PLAN_ANCHOR_PATTERN.search(anchor):
            bad_image_plan_anchors.append(f"row {index}: {anchor}")
        local_path = resolve_local(file_value)
        if local_path is None and image_plan_path is not None:
            plan_relative = image_plan_path.resolve().parent / file_value
            if plan_relative.is_file() and plan_relative.stat().st_size > 0:
                local_path = plan_relative
        if local_path is None:
            missing_local_images.append(file_value)
        elif is_real_image(local_path):
            local_image_paths[file_value] = local_path
        else:
            invalid_local_images.append(f"{file_value} -> {local_path}")
    real_image_count = img_src_token_count + len(local_image_paths)
    real_bookmark_hits = count(r'<bookmark\b[^>]*href\s*=\s*["\']https?://(?!example\.com|placeholder\.)', text)
    placeholder_url_hits = count(r'https?://(?:example\.com|placeholder\.)', text)
    stale_media_markers = count(r'<!--\s*(media:|插图位置)', text)
    text_without_comments = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text_without_img_tags = re.sub(r"<img\b[^>]*>", "", text_without_comments, flags=re.S | re.I)
    leaked_xml_fields = len(
        re.findall(
            r'anchor\s*=\s*"|caption\s*=\s*"|source_type\s*=|来源：生成图|来源：搜图',
            text_without_img_tags,
            re.IGNORECASE,
        )
    )
    real_visual_assets = real_image_count + real_bookmark_hits
    is_xml = args.xml or args.file.suffix.lower() == ".xml" or has(r"<title>|<callout|<bookmark", text)
    domestic_hits = count(r"bilibili|b23\.tv|哔哩哔哩|B站|小红书|xiaohongshu|xhslink|中国居民膳食指南|中国营养学会|疾控", text)
    core_action_hits = count(r"核心动作|动作库|动作要点|起始姿势|执行路径|常见错误|目标肌群", text)
    adherence_hits = count(r"漏练|低动力|坚持|没动力|吃超|补救|最低完成|常见问题|Q&A|FAQ|酸痛|器械被占|平台期|忘记打卡|连续漏|应酬|出差", text)
    explanation_hits = count(r"为什么|因为|目的|作用|优先|不建议|避免|为了|核心抓手|关键|服务|取舍|更适合|不适合", text)
    execution_detail_hits = count(
        r"\d+\s*[x×]\s*\d+|\d+\s*组|\d+\s*次|\d+\s*分钟|\d+\s*秒|每周|休息|强度|余力|热身|收操|早餐|午餐|晚餐|样例餐|点餐|蛋白|主食|蔬菜|步数|心率",
        text,
    )
    adjustment_hits = count(r"替代|换成|降阶|进阶|加重|加次数|加组|降载|调整|减少|保留|删掉|回到计划|下一餐|下一次|停止|停练|改成", text)
    review_hits = count(r"复盘|记录|日志|完成率|围度|照片|7\s*日均重|体重趋势|PR|训练容量|睡眠|疲劳|疼痛\s*0-10|主观疲劳|根据.*调整", text)
    internal_tool_status_hits = sum(count(pattern, text) for pattern in INTERNAL_TOOL_STATUS_PATTERNS)
    delivery_leak_hits = sum(count(pattern, text) for pattern in DELIVERY_LEAK_PATTERNS)
    html_form_leak_hits = sum(count(pattern, text) for pattern in HTML_FORM_LEAK_PATTERNS)
    internal_anchor_leak_hits = sum(count(pattern, text) for pattern in INTERNAL_ANCHOR_LEAK_PATTERNS)
    unknown_tag_hits = unknown_xml_tags(text)
    generic_heading_pattern = (
        r"核心训练原则|安全注意事项|训练安排|训练路线|当下训练|动作要点|"
        r"饮食建议|饮食恢复|恢复与睡眠|学习资源|打卡复盘|常见问题|"
        r"写在最后|装备清单|健身基础知识"
    )

    if internal_tool_status_hits:
        failures.append(
            "Document exposes internal lark-cli/tool compatibility status; remove auth/skills/version/permission/fallback notes from the user-facing guide"
        )
    if delivery_leak_hits:
        failures.append(
            "Document or delivery text exposes internal process notes, media-search shortcomings, completion excuses, or user-facing supplement-question blocks. Remove these from the Feishu body and keep any non-blocking refinement note outside the document."
        )
    if html_form_leak_hits:
        failures.append(
            "Document exposes raw HTML form tag(s), commonly <input type=\"checkbox\" />. Feishu XML checklists must use <checkbox done=\"false\">item text</checkbox>; Markdown fallback uses '- [ ] item text'. Remove all HTML input/button/select/textarea/label/form tags from the visible body."
        )
    if internal_anchor_leak_hits:
        failures.append(
            "Document exposes internal image anchor placeholder(s), such as 【动作锚点-...】 or 【封面锚点-...】. Delete these markers from the visible body. Image-plan anchors must point to a normal sentence already present in the guide, not to a fake placeholder label."
        )
    if unknown_tag_hits:
        failures.append(
            f"Document contains unsupported/self-invented XML or HTML tag(s): {unknown_tag_hits[:8]}. Use only Feishu XML whitelist tags (title/h1/h2/h3/p/b/i/br/callout/grid/column/table/thead/tbody/tr/th/td/checkbox/bookmark/blockquote/hr/img). For card-like layouts, use callout + grid + table instead of <card> or custom tags."
        )
    if generated_image_hits:
        failures.append(
            "Generated fitness images are forbidden. Do not use image_gen/generated/生成图/生图 for fitness actions or diagrams; if no reliable real image is available, omit the image and use video/bookmark + action cards."
        )

    if is_xml:
        for tag in ("<title>", "<table", "<bookmark", "<checkbox"):
            if tag not in text:
                failures.append(f"XML output missing required rich block: {tag}")
        rich_blocks = sum(text.count(tag) for tag in ("<callout", "<table", "<grid", "<bookmark", "<checkbox", "<img", "<hr", "<blockquote"))
        if rich_blocks < 6:
            failures.append("XML output has too few rich blocks for a Feishu guide")
        title_match = re.search(r"<title>(.*?)</title>\s*<h1>\s*\1\s*</h1>", text, flags=re.S)
        if title_match:
            failures.append("Body repeats the exact document title as the first H1")
        title = strip_tags(re.search(r"<title>(.*?)</title>", text, flags=re.S).group(1)) if re.search(r"<title>(.*?)</title>", text, flags=re.S) else ""
        if title:
            if re.search(r"(攻略|计划|方案)\s*$", title) and not re.search(r"手册|路线|系统|训练卡|面板|清单|吃法|避痛|复盘|纠错", title):
                warnings.append("Title ends with generic 攻略/计划/方案; prefer a more scenario-specific document form")
            if len(title) <= 10 and re.search(r"攻略|计划|方案", title):
                failures.append("Title is too generic; make it scenario-specific")
        h2_titles = [strip_tags(item) for item in re.findall(r"<h2[^>]*>(.*?)</h2>", text, flags=re.S | re.I)]
        generic_h2 = [heading for heading in h2_titles if re.search(generic_heading_pattern, heading, flags=re.I)]
        if len(generic_h2) >= 4:
            failures.append("Too many generic H2 headings (more than 3); rewrite some around the user's specific scenario")
        if len(h2_titles) >= 5:
            specific_terms = re.findall(
                r"食堂|外卖|热量|点餐|马甲线|肩背|塑形|偏瘦|增肌|居家|无器械|健身房|跑步|跑走|TFCC|小臂|25\s*分钟|上班族|打卡|复盘|新手|零基础|器械|动作|疼痛|奶茶|便利店|腰围|步数",
                " ".join(h2_titles),
                flags=re.I,
            )
            if len(set(specific_terms)) < 2 and len(generic_h2) >= 3:
                failures.append("H2 headings carry almost no user-specific scenario words; add the user's goal/situation to headings")
        if h2_titles and re.search(r"导览|默认假设|核心训练原则|健身基础知识", h2_titles[0]):
            failures.append("First H2 is generic; first screen should answer the user's core scenario")

        full_guide_like = len(text) >= 2500 or len(h2_titles) >= 4 or (training_hits + diet_hits + plan_hits >= 18)
        if full_guide_like:
            if explanation_hits < 3:
                failures.append(
                    "clarity-floor: Full guide lacks enough 'why this works' explanation. Add brief rationale/取舍 for the main training, diet, or recovery modules instead of only listing items."
                )
            if execution_detail_hits < 8:
                failures.append(
                    "clarity-floor: Full guide lacks concrete execution details. Add sets/reps/time/intensity/rest, meal-ordering details, weekly frequency, or check-in fields so the user can follow it."
                )
            if adjustment_hits < 4:
                failures.append(
                    "clarity-floor: Full guide lacks adjustment logic. Add how to progress, deload, substitute equipment, reduce volume, handle discomfort, or return to the plan after disruption."
                )
            if review_hits < 3:
                failures.append(
                    "richness-floor: Full guide lacks review metrics. Add what to record and how 2-4 weeks of weight, waist, completion rate, reps/loads, fatigue, or pain should change the plan."
                )
            if adherence_hits < 2:
                failures.append(
                    "richness-floor: Full guide lacks execution support. Add concrete handling for at least two likely blockers such as missed workouts, eating over plan, low motivation, equipment occupied, soreness, travel, or overtime."
                )
        if stale_media_markers:
            failures.append(
                f"Found {stale_media_markers} internal planning comment(s) in the XML body. Do NOT put image markers such as <!-- 插图位置 --> or <!-- media: --> in Feishu XML; Feishu may render them as visible text. Use a sidecar image-plan.tsv/json instead."
            )
        if image_plan_errors:
            failures.extend(image_plan_errors)
        non_image_plan_rows = [
            entry for entry in image_plan_entries
            if (entry.get("status") or "").strip().lower() in {"no_reliable_image", "not_found", "skipped", "omit"}
        ]
        if incomplete_image_plan_rows:
            failures.append(
                f"Image plan rows missing required fields file/anchor/caption: {incomplete_image_plan_rows}"
            )
        if bad_image_plan_anchors:
            failures.append(
                f"Image plan anchor values look like internal placeholder labels instead of natural body text: {bad_image_plan_anchors}. Use an exact normal sentence from the guide as the anchor; do not use words like 锚点/anchor/插图位置."
            )
        if full_guide_like and real_image_count == 0:
            if real_bookmark_hits < 3:
                failures.append(
                    "Full Feishu fitness guide has no reliable real image inserted. This is allowed only when the guide includes enough real video/diagram bookmarks (at least 3) and action cards. Add real bookmarks or insert a verified real image; do not generate images."
                )
            elif stage == "draft" and image_plan_path is None:
                warnings.append(
                    "No image-plan.tsv found. If image search was attempted and no reliable image was available, record status=no_reliable_image in image-plan.tsv for traceability."
                )
        if img_href_external:
            failures.append(
                f"Found {img_href_external} <img href=\"external-URL\"> — Feishu server-side fetch returns 403 for many sources (anti-hotlink). Download the image locally with curl -A \"Mozilla/5.0\" and use +media-insert --file <local> instead. See SKILL.md '图片怎么进飞书'."
            )
        if missing_local_images:
            failures.append(
                f"Image plan references local image files that do not exist: {missing_local_images}. Download each via curl -A 'Mozilla/5.0' <URL> to that path and verify with `file` before creating the doc."
            )
        if invalid_local_images:
            failures.append(
                f"Image plan references files that exist but are not real PNG/JPEG/GIF/WebP images: {invalid_local_images}. You may have downloaded an HTML error page or placeholder text; replace them with real image files."
            )
        if stage == "draft" and image_plan_path is None and img_src_token_count == 0 and full_guide_like and real_bookmark_hits < 3:
            failures.append(
                "Draft XML has no sidecar image plan and not enough real bookmarks. Either create image-plan.tsv with ready/no_reliable_image rows, or add enough verified video/diagram bookmarks. Do not generate images."
            )
        if leaked_xml_fields:
            failures.append(
                f"Found {leaked_xml_fields} leaked internal field(s) (anchor=\"/caption=\"/source_type/来源：生成图/来源：搜图) in the body. These are for the tool/script, not the user. Delete them from visible body text."
            )
        if placeholder_url_hits:
            failures.append(
                "Document contains placeholder/example URLs (example.com). Replace with real, verified source links or remove the bookmark"
            )
        if full_guide_like and real_image_count == 0 and real_bookmark_hits > 0:
            warnings.append(
                "Guide has bookmarks but no inserted image. Keep the user-facing delivery focused on content highlights; do not mention media-search process."
            )
        # 通用信号:训练型攻略列了多个核心动作但图明显偏少 → 列多配少
        if full_guide_like and training_hits >= 8 and real_image_count < 2 and real_bookmark_hits < 3:
            failures.append(
                f"content-media-mismatch: Training guide lists multiple core movements (training_signal={training_hits}) but has only {real_image_count} image(s) and too few real bookmarks ({real_bookmark_hits}). Add verified video/diagram bookmarks for core actions or insert verified real images. Do not generate images."
            )
        if full_guide_like and real_image_count == 1:
            warnings.append(
                "single-image: Full guide has only 1 image. If the guide lists multiple photo-worthy objects (movements/dishes), add one photo per key object and show side-by-side via <grid>."
            )


    if training_hits + diet_hits + plan_hits >= 4 and len(text.strip()) < 240:
        failures.append("Fitness guide is too short to be actionable")

    if is_xml:
        headings = re.findall(r"<h2[^>]*>(.*?)</h2>(.*?)(?=<h2|</?title|$)", text, flags=re.S | re.I)
        thin_sections = 0
        thin_major_sections = 0
        for _, body in headings:
            body_text = re.sub(r"<[^>]+>", " ", body)
            body_text = re.sub(r"\s+", "", body_text)
            rich = sum(body.count(tag) for tag in ("<table", "<grid", "<callout", "<checkbox", "<bookmark", "<blockquote", "<img"))
            if len(body_text) < 80 and rich == 0:
                thin_sections += 1
            if len(body_text) < 140 and rich <= 1:
                thin_major_sections += 1
        if thin_sections >= 2:
            failures.append("Multiple major sections are too thin; expand or merge one-line H2 sections")
        if len(headings) >= 4 and thin_major_sections >= 3:
            failures.append(
                "Many H2 sections are shallow. Major modules need more than a one-line note or one thin component; add explanation, execution detail, and adjustment logic, or merge the section."
            )

    if not is_xml:
        md_headings = [line.strip("# ").strip() for line in lines if re.match(r"^#{1,3}\s+", line.strip())]
        if md_headings:
            generic_md = [heading for heading in md_headings if re.search(generic_heading_pattern, heading, flags=re.I)]
            if len(generic_md) >= 4:
                failures.append("Too many generic Markdown headings; rewrite headings around the user's specific scenario")
            if re.search(r"(攻略|计划|方案)\s*$", md_headings[0]) and len(md_headings[0]) <= 14:
                warnings.append("Markdown title appears generic; prefer a scenario-specific document form")

    if plan_hits >= 1 and not has(r"\d+\s*[x×]\s*\d+|\d+\s*组|\d+\s*次|\d+\s*分钟|\d+\s*天|每周|早餐|午餐|晚餐|样例餐|记录|复盘", text):
        failures.append("Plan-like content lacks concrete schedule, dose, meal, or review details")

    if training_hits >= 8:
        if not has(r"\d+\s*[x×]\s*\d+|\d+\s*组|\d+\s*次|\d+\s*分钟|\d+\s*秒", text):
            failures.append("Training content lacks concrete sets/reps/duration")
        if not has(r"RIR|RPE|余力|强度|心率|还能做", text):
            failures.append("Training content lacks intensity guidance")
        plain_intensity = has(r"还能做|还能再做|余力|不变形|吃力|轻松|喘|能说短句|呼吸可控|有挑战", text)
        if has(r"RPE|RIR", text) and not plain_intensity:
            warnings.append("Intensity uses RPE/RIR but no plain-language explanation. Add a plain explanation for users (e.g. '有挑战还能做2-3次 (RPE 7-8)'), don't just throw 'RPE 7-8' at the user.")
        if not has(r"休息|间歇|组间", text):
            failures.append("Training content lacks rest guidance")
        if technique_hits < 5:
            failures.append("Training content lacks enough technique details")
        if not has(r"替代|换成|降阶|器械被占|不适|太难|时间不够", text):
            failures.append("Training content lacks substitutions or adjustment logic")

    if plan_hits >= 5 and training_hits >= 5 and training_hits >= diet_hits:
        if not has(r"日志|记录|打卡|实际|RIR|RPE|疼痛\s*0-10|完成率|PR|训练容量|复盘", text):
            failures.append("Plan lacks training log or review metrics")
        if not has(r"进阶|加重|加次数|加组|降载|调整", text):
            failures.append("Plan lacks progression or deload rules")
        if adherence_hits < 2:
            failures.append("Longer plan has little adherence support; add scenario-specific FAQ, missed-workout rescue, low-motivation fallback, or eating-over-plan repair logic")

    # 荒谬场景拼凑：强度/疼痛描述套到不合适场景（独立于 training_hits，任何文档都查）
    if has(r"游泳|水中|泳", text) and has(r"说话|能说|说短句|聊天|说话测试", text):
        failures.append("Absurd scene mismatch: swimming/underwater + 'talking/saying sentences' for intensity. You can't talk underwater to gauge intensity — use pace/heart-rate. Delete the 'talking test' wording from swimming context.")

    if diet_hits >= 8:
        if not has(r"早餐|午餐|晚餐|样例餐|食堂|外卖|便利店|点餐|少油|少酱", text):
            failures.append("Diet content lacks concrete meal or ordering guidance")
        if not has(r"蛋白|蔬菜|主食|饮料|零食|夜宵", text):
            failures.append("Diet content lacks practical food-category rules")
        if has(r"\d{3,4}\s*kcal", text) and not has(r"粗略|区间|估算|不必精确", text):
            warnings.append("Calorie numbers appear precise; consider framing as estimates")
        if has(r"食堂|外卖|上班族|奶茶|夜宵", text) and adherence_hits < 2:
            warnings.append("External-eating diet guide should include eat-over/milk-tea/night-snack/social-meal rescue logic")

    if media_promises >= 1 and url_hits == 0 and real_image_count == 0:
        failures.append("Mentions video/image/resources but provides no real local/inserted image or bookmark link")

    if training_hits >= 8 and media_promises >= 1 and url_hits < max(1, min(4, core_action_hits)):
        failures.append("Learning resources appear fewer than the covered core actions")

    if (training_hits >= 8 or diet_hits >= 8) and media_promises >= 1 and domestic_hits == 0:
        warnings.append("No domestic Chinese learning/resource source detected; prefer Bilibili/Xiaohongshu or Chinese authoritative sources when available")

    if is_xml and (training_hits >= 8 or diet_hits >= 8 or plan_hits >= 5):
        if real_image_count == 0 and real_bookmark_hits < 3:
            failures.append(
                "Guide has substantial training/diet content but lacks both verified images and enough real bookmarks. Add real video/diagram/resource bookmarks or insert verified real images. Do not generate images."
            )

    bullet_ratio = line_ratio(r"^(\d+\.|[-*]\s+)", lines)
    if bullet_ratio > 0.55 and len(lines) > 25:
        failures.append("Output is too list-heavy; use tables/cards/callouts/grids/logs")

    if failures:
        print("FAILED")
        for failure in failures:
            print(f"- {failure}")
        for warning in warnings:
            print(f"warning: {warning}")
        return 1

    print("PASSED")
    for warning in warnings:
        print(f"warning: {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
