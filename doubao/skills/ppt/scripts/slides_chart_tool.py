#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_DIR = SKILL_ROOT / "references"
DEFAULT_DEMO_PATH = REFERENCES_DIR / "xml" / "slides_chart_demo.xml"
DEFAULT_LIMIT = 8

# 11 slides in slides_chart_demo.xml. Each slide is one chart-type showcase.
# The `chineseName · englishName` string appears as a sub-headline inside the
# slide body, and is used to associate a slide block with a chart id.
CHART_TYPES: list[dict[str, Any]] = [
    {
        "id": "minimal",
        "chineseName": "极简图表",
        "englishName": "Minimal",
        "description": "无图例/无标题/无数据标签的最小组合（含柱状 / 折线 / 饼 / 环形）",
        "aliases": [
            "minimal",
            "minimal chart",
            "simple chart",
            "basic chart",
            "clean chart",
            "no legend",
            "no title",
            "no labels",
            "极简",
            "极简图表",
            "极简版",
            "简洁图表",
            "基础图表",
            "最小图表",
            "无图例",
            "无标题",
            "无标签",
            "无数据标签",
        ],
    },
    {
        "id": "column",
        "chineseName": "柱状图",
        "englishName": "Column Chart",
        "description": "分组柱状 · 堆叠柱状 · 百分比堆叠",
        "aliases": [
            "column",
            "column chart",
            "vertical bar",
            "vertical bar chart",
            "clustered column",
            "grouped column",
            "stacked column",
            "100% stacked column",
            "percent stacked column",
            "柱状",
            "柱状图",
            "柱形图",
            "柱图",
            "垂直柱状",
            "竖向柱状",
            "纵向柱状",
            "分组柱状",
            "堆叠柱状",
            "百分比堆叠柱状",
            "百分比柱状",
            "100%堆叠柱状",
        ],
    },
    {
        "id": "line",
        "chineseName": "折线图",
        "englishName": "Line Chart",
        "description": "直线折线 · 平滑折线 · 阶梯折线",
        "aliases": [
            "line",
            "line chart",
            "line graph",
            "trend line",
            "smooth line",
            "step line",
            "stepped line",
            "折线",
            "折线图",
            "线图",
            "趋势图",
            "趋势线",
            "平滑折线",
            "阶梯折线",
        ],
    },
    {
        "id": "pie",
        "chineseName": "饼图",
        "englishName": "Pie Chart",
        "description": "饼图 · 环形图（Donut）",
        "aliases": [
            "pie",
            "pie chart",
            "donut",
            "donut chart",
            "doughnut",
            "doughnut chart",
            "ring chart",
            "饼",
            "饼图",
            "饼状图",
            "扇形图",
            "占比图",
            "结构占比",
            "环形图",
            "环图",
            "圆环图",
            "甜甜圈图",
            "甜甜圈",
        ],
    },
    {
        "id": "bar",
        "chineseName": "条形图",
        "englishName": "Bar Chart",
        "description": "分组条形 · 堆叠条形 · 百分比堆叠",
        "aliases": [
            "bar",
            "bar chart",
            "horizontal bar",
            "horizontal bar chart",
            "grouped bar",
            "stacked bar",
            "100% stacked bar",
            "percent stacked bar",
            "ranking bar",
            "rank chart",
            "条形",
            "条形图",
            "横向条形",
            "水平条形",
            "横向柱状",
            "水平柱状",
            "分组条形",
            "堆叠条形",
            "百分比堆叠条形",
            "百分比条形",
            "100%堆叠条形",
            "排名图",
            "排行图",
            "横向排名",
        ],
    },
    {
        "id": "area",
        "chineseName": "面积图",
        "englishName": "Area Chart",
        "description": "重叠面积 · 堆叠面积 · 百分比堆叠",
        "aliases": [
            "area",
            "area chart",
            "filled line",
            "filled line chart",
            "overlay area",
            "stacked area",
            "100% stacked area",
            "percent stacked area",
            "面积",
            "面积图",
            "区域图",
            "填充折线",
            "重叠面积",
            "堆叠面积",
            "百分比堆叠面积",
            "百分比面积",
            "100%堆叠面积",
        ],
    },
    {
        "id": "combo",
        "chineseName": "组合图",
        "englishName": "Combo Chart",
        "description": "柱线组合，含次坐标轴",
        "aliases": [
            "combo",
            "combo chart",
            "combination chart",
            "mixed chart",
            "column line",
            "column line chart",
            "bar line",
            "dual axis",
            "dual axis chart",
            "secondary axis",
            "组合",
            "组合图",
            "复合图",
            "混合图",
            "柱线组合",
            "柱折组合",
            "柱线图",
            "柱状折线图",
            "双轴图",
            "双坐标轴",
            "次坐标轴",
        ],
    },
    {
        "id": "radar",
        "chineseName": "雷达图",
        "englishName": "Radar Chart",
        "description": "多边形雷达 · 圆形雷达 · 无填充雷达",
        "aliases": [
            "radar",
            "radar chart",
            "spider chart",
            "web chart",
            "polar chart",
            "雷达",
            "雷达图",
            "蜘蛛图",
            "网状图",
            "能力雷达",
            "多维雷达",
            "圆形雷达",
            "多边形雷达",
            "无填充雷达",
        ],
    },
    {
        "id": "bubble",
        "chineseName": "气泡图",
        "englishName": "Bubble Chart",
        "description": "三维气泡（X / Y / 气泡大小）",
        "aliases": [
            "bubble",
            "bubble chart",
            "bubble plot",
            "scatter",
            "scatter chart",
            "scatter plot",
            "xy scatter",
            "x y size",
            "x/y/size",
            "气泡",
            "气泡图",
            "气泡散点",
            "散点",
            "散点图",
            "三维气泡",
            "二维气泡",
            "x y 气泡",
            "x/y/气泡",
        ],
    },
    {
        "id": "waterfall",
        "chineseName": "瀑布图",
        "englishName": "Waterfall Chart",
        "description": "增量 / 减量 / 总计三色语义配色",
        "aliases": [
            "waterfall",
            "waterfall chart",
            "bridge chart",
            "cascade chart",
            "variance chart",
            "increase decrease",
            "瀑布",
            "瀑布图",
            "桥图",
            "阶梯图",
            "增减图",
            "增减变化",
            "差异分析",
            "变动分析",
            "累计影响",
            "财务桥",
        ],
    },
    {
        "id": "pareto",
        "chineseName": "帕累托图",
        "englishName": "Pareto Chart",
        "description": "柱状 + 累计百分比双轴",
        "aliases": [
            "pareto",
            "pareto chart",
            "pareto analysis",
            "80/20",
            "80-20",
            "8020",
            "abc",
            "abc analysis",
            "sorted bar cumulative line",
            "cumulative percentage",
            "帕累托",
            "帕累托图",
            "帕累托分析",
            "二八法则",
            "80/20法则",
            "80-20法则",
            "ABC分析",
            "重点因素分析",
            "累计百分比",
            "累计占比",
        ],
    },
]


class SlidesChartToolError(Exception):
    pass


def fail(message: str) -> None:
    raise SlidesChartToolError(message)


def normalize_token(value: str) -> str:
    normalized = value.lower().replace("_", " ")
    normalized = re.sub(r"[-/]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def load_demo_text(path: str | Path = DEFAULT_DEMO_PATH) -> str:
    demo_path = Path(path)
    if not demo_path.exists():
        fail(f"chart demo xml not found: {demo_path}")
    return demo_path.read_text(encoding="utf-8")


def split_slides(text: str) -> list[dict[str, Any]]:
    """Split the demo XML into individual slide blocks.

    Returns a list of dicts with startLine / endLine (1-based inclusive) and
    the raw xml text for each slide. Uses line-anchored matching on
    `<slide>` / `</slide>` to keep parsing dependency-free.
    """
    lines = text.splitlines(keepends=True)
    slides: list[dict[str, Any]] = []
    start_index: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "<slide>":
            start_index = index
        elif stripped == "</slide>" and start_index is not None:
            block = "".join(lines[start_index : index + 1])
            slides.append(
                {
                    "startLine": start_index + 1,
                    "endLine": index + 1,
                    "xml": block,
                }
            )
            start_index = None
    return slides


def detect_chart_id(slide_xml: str) -> str | None:
    """Detect chart id by scanning sub-headline text inside a slide block."""
    for entry in CHART_TYPES:
        pattern = rf"<p>\s*{re.escape(entry['chineseName'])}\s*·\s*{re.escape(entry['englishName'])}\s*</p>"
        if re.search(pattern, slide_xml):
            return entry["id"]
    return None


def load_slides(path: str | Path = DEFAULT_DEMO_PATH) -> list[dict[str, Any]]:
    text = load_demo_text(path)
    slides = split_slides(text)
    for slide in slides:
        slide["id"] = detect_chart_id(slide["xml"])
    return slides


def public_type(entry: dict[str, Any], slide: dict[str, Any] | None = None) -> dict[str, Any]:
    result = {
        "id": entry["id"],
        "chineseName": entry["chineseName"],
        "englishName": entry["englishName"],
        "description": entry["description"],
        "aliases": list(entry.get("aliases") or []),
    }
    if slide is not None:
        result["startLine"] = slide["startLine"]
        result["endLine"] = slide["endLine"]
    return result


def list_chart_types(slides: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    slide_by_id = {slide["id"]: slide for slide in slides or [] if slide.get("id")}
    return [public_type(entry, slide_by_id.get(entry["id"])) for entry in CHART_TYPES]


def resolve_type(query: str) -> dict[str, Any]:
    if not query or not query.strip():
        fail("empty chart type value")
    normalized = normalize_token(query)
    for entry in CHART_TYPES:
        candidates = {
            normalize_token(entry["id"]),
            normalize_token(entry["chineseName"]),
            normalize_token(entry["englishName"]),
        }
        for alias in entry.get("aliases") or []:
            candidates.add(normalize_token(alias))
        if normalized in candidates:
            return entry
    # fallback: chineseName substring (allows "帕累托" to match "帕累托图")
    for entry in CHART_TYPES:
        if entry["chineseName"] in query or query in entry["chineseName"]:
            return entry
    fail(f"unknown chart type: {query}")


def parse_limit(value: Any) -> int:
    if value is None or value is False:
        return DEFAULT_LIMIT
    if value is True:
        fail("limit requires an integer value")
    try:
        return int(value)
    except (TypeError, ValueError):
        fail(f"limit must be an integer: {value}")


def search_chart_types(query: str, limit: int = DEFAULT_LIMIT) -> list[dict[str, Any]]:
    if not query or not query.strip():
        fail("query is required")
    normalized = normalize_token(query)
    ranked: list[tuple[int, dict[str, Any]]] = []
    for entry in CHART_TYPES:
        score = 0
        haystacks = [
            (entry["id"], 60),
            (entry["chineseName"], 100),
            (entry["englishName"], 80),
        ]
        for alias in entry.get("aliases") or []:
            haystacks.append((alias, 40))
        for value, weight in haystacks:
            norm_value = normalize_token(value)
            if not norm_value:
                continue
            if normalized == norm_value:
                score += weight * 2
            elif normalized in norm_value or norm_value in normalized:
                score += weight
        # substring on Chinese name without normalization (Chinese has no case)
        if entry["chineseName"] in query or query in entry["chineseName"]:
            score += 30
        if score > 0:
            ranked.append((score, public_type(entry)))
    ranked.sort(key=lambda item: (-item[0], item[1]["id"]))
    return [entry for _, entry in ranked[: max(limit, 0)]]


def extract_chart_demos(entries: list[dict[str, Any]], path: str | Path = DEFAULT_DEMO_PATH) -> list[dict[str, Any]]:
    slides = load_slides(path)
    slides_by_id = {slide["id"]: slide for slide in slides if slide.get("id")}

    demos: list[dict[str, Any]] = []
    for entry in entries:
        slide = slides_by_id.get(entry["id"])
        if slide is None:
            fail(f"chart type not found in demo xml: {entry['id']}")
        demo = public_type(entry, slide)
        demo["xml"] = slide["xml"]
        demos.append(demo)
    return demos


def render_xml(demos: list[dict[str, Any]]) -> str:
    return "\n".join(demo["xml"] for demo in demos)


def get_chart_entries(queries: list[str], limit: int = DEFAULT_LIMIT) -> list[dict[str, Any]]:
    if not queries:
        fail("at least one chart id or keyword is required")
    entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for query in queries:
        if not query or not query.strip():
            fail("chart id or keyword cannot be empty")
        try:
            matches = [resolve_type(query)]
        except SlidesChartToolError:
            matches = [resolve_type(match["id"]) for match in search_chart_types(query, limit)]
            if not matches:
                fail(f"chart type not found: {query}")
        for entry in matches:
            if entry["id"] not in seen_ids:
                seen_ids.add(entry["id"])
                entries.append(entry)
    return entries


def parse_cli_args(argv: list[str]) -> tuple[str | None, dict[str, Any]]:
    if not argv:
        return None, {}
    command, *rest = argv
    options: dict[str, Any] = {}
    queries: list[str] = []
    index = 0
    while index < len(rest):
        token = rest[index]
        if not token.startswith("--"):
            queries.append(token)
            index += 1
            continue
        key = token[2:]
        next_token = rest[index + 1] if index + 1 < len(rest) else None
        if next_token is None or next_token.startswith("--"):
            if key == "query":
                fail("query requires a value; pass chart ids or keywords after get")
            options[key] = True
            index += 1
            continue
        if key == "query":
            queries.append(next_token)
        else:
            options[key] = next_token
        index += 2
    options["_queries"] = queries
    return command, options


def print_usage() -> None:
    usage = [
        "Usage:",
        "  python3 slides_chart_tool.py list",
        "  python3 slides_chart_tool.py get <id-or-keyword>... [--limit 8]",
        "",
        "Chart types: " + ", ".join(entry["chineseName"] for entry in CHART_TYPES),
    ]
    print("\n".join(usage), file=sys.stderr)


def write_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def run_cli(argv: list[str] | None = None) -> None:
    command, options = parse_cli_args(argv or sys.argv[1:])
    if not command or command in {"--help", "help"}:
        print_usage()
        raise SystemExit(0)

    if command == "list":
        write_json([entry["id"] for entry in CHART_TYPES])
        return

    if command == "get":
        limit = parse_limit(options.get("limit"))
        xml = render_xml(extract_chart_demos(get_chart_entries(options["_queries"], limit)))
        sys.stdout.write(xml)
        if not xml.endswith("\n"):
            sys.stdout.write("\n")
        return

    print_usage()
    fail(f"unknown command: {command}")


if __name__ == "__main__":
    try:
        run_cli()
    except SlidesChartToolError as error:
        print(f"slides-chart-tool error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
