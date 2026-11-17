#!/usr/bin/env python3
"""Validate objective structure in a creative-video storyboard Markdown file."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


EXPECTED_HEADERS = [
    "节拍ID",
    "镜头ID",
    "生成段ID",
    "时间",
    "镜头职责",
    "新增信息",
    "画面层级",
    "主体与场景/素材",
    "画面动作",
    "镜头语言",
    "画面设计",
    "声音与文字",
    "转场/尾态",
    "风险/禁区",
]

CREATIVE_LABELS = [
    "核心主线",
    "表达意图与观看路径",
    "视觉记忆点与母题",
    "视听与文字策略",
    "素材使用与风险边界",
]

TIME_RE = re.compile(
    r"^\s*(?P<start>\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)"
    r"\s*(?:-|–|—|~|至)\s*"
    r"(?P<end>\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\s*$"
)
BEAT_RE = re.compile(r"^B\d{2}$")
SHOT_RE = re.compile(r"^SH\d{3}$")
SEGMENT_RE = re.compile(r"^SEG\d{2}$")
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")


def parse_time(value: str) -> float:
    parts = value.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        second_value = float(seconds)
        if not 0 <= second_value < 60:
            raise ValueError(f"秒字段必须小于 60：{value}")
        return int(minutes) * 60 + second_value
    if len(parts) == 3:
        hours, minutes, seconds = parts
        minute_value = int(minutes)
        second_value = float(seconds)
        if not 0 <= minute_value < 60:
            raise ValueError(f"分钟字段必须小于 60：{value}")
        if not 0 <= second_value < 60:
            raise ValueError(f"秒字段必须小于 60：{value}")
        return int(hours) * 3600 + minute_value * 60 + second_value
    raise ValueError(f"非法时间：{value}")


def split_markdown_row(line: str) -> list[str]:
    text = line.strip()
    if not text.startswith("|") or not text.endswith("|"):
        return []
    return [cell.strip() for cell in text[1:-1].split("|")]


def extract_spoken_segments(value: str) -> tuple[list[str], bool]:
    segments: list[str] = []
    start: int | None = None
    valid = True

    for index, char in enumerate(value):
        if char == "{":
            if start is not None:
                valid = False
            else:
                start = index + 1
        elif char == "}":
            if start is None:
                valid = False
            else:
                spoken = value[start:index]
                if not spoken.strip():
                    valid = False
                segments.append(spoken)
                start = None

    if start is not None:
        valid = False
    return segments, valid


def find_section(lines: list[str], heading: str) -> int | None:
    target = f"## {heading}"
    return next(
        (index for index, line in enumerate(lines) if line.strip() == target),
        None,
    )


def validate_creative_section(text: str, errors: list[str]) -> None:
    lines = text.splitlines()
    section_index = find_section(lines, "创意说明")
    if section_index is None:
        errors.append("缺少章节：## 创意说明")
        return

    next_heading = next(
        (
            index
            for index in range(section_index + 1, len(lines))
            if lines[index].startswith("## ")
        ),
        len(lines),
    )
    section = "\n".join(lines[section_index + 1 : next_heading])
    for label in CREATIVE_LABELS:
        match = re.search(
            rf"^\s*-\s*{re.escape(label)}：\s*(.+)$",
            section,
            re.MULTILINE,
        )
        if not match or not match.group(1).strip():
            errors.append(f"创意说明缺少有效内容：{label}")


def parse_storyboard_table(
    lines: list[str],
    errors: list[str],
) -> list[dict[str, str]]:
    section_index = find_section(lines, "完整分镜表")
    if section_index is None:
        errors.append("缺少章节：## 完整分镜表")
        return []

    table_lines: list[str] = []
    for line in lines[section_index + 1 :]:
        stripped = line.strip()
        if not stripped and not table_lines:
            continue
        if stripped.startswith("|"):
            table_lines.append(stripped)
        elif table_lines:
            break

    if len(table_lines) < 3:
        errors.append("完整分镜表缺少表头、分隔行或镜头数据")
        return []

    headers = split_markdown_row(table_lines[0])
    if headers != EXPECTED_HEADERS:
        errors.append(
            "完整分镜表表头不匹配，必须严格使用："
            + " | ".join(EXPECTED_HEADERS)
        )
        return []

    separator = split_markdown_row(table_lines[1])
    if len(separator) != len(EXPECTED_HEADERS) or not all(
        re.fullmatch(r":?-{3,}:?", cell) for cell in separator
    ):
        errors.append("完整分镜表第二行不是合法 Markdown 分隔行")
        return []

    rows: list[dict[str, str]] = []
    for row_number, line in enumerate(table_lines[2:], start=1):
        cells = split_markdown_row(line)
        if len(cells) != len(EXPECTED_HEADERS):
            errors.append(
                f"镜头数据第 {row_number} 行有 {len(cells)} 列，"
                f"应为 {len(EXPECTED_HEADERS)} 列"
            )
            continue
        rows.append(dict(zip(EXPECTED_HEADERS, cells)))
    return rows


def validate_grouping(values: list[str], label: str, errors: list[str]) -> None:
    closed: set[str] = set()
    current: str | None = None
    for value in values:
        if value == current:
            continue
        if current is not None:
            closed.add(current)
        if value in closed:
            errors.append(f"{label} {value} 非连续重复出现")
        current = value


def validate_group_sequence(
    values: list[str],
    label: str,
    prefix: str,
    width: int,
    errors: list[str],
) -> None:
    unique_values = list(dict.fromkeys(values))
    expected = [
        f"{prefix}{number:0{width}d}"
        for number in range(1, len(unique_values) + 1)
    ]
    if unique_values != expected:
        errors.append(
            f"{label} 必须从 {prefix}{1:0{width}d} 开始连续编号，"
            f"当前顺序：{', '.join(unique_values)}"
        )


def validate_storyboard(
    text: str,
    expected_duration: float | None,
    min_shots: int | None,
    max_chars_per_second: float,
    max_shots: int | None = None,
    require_opening_cut: bool = False,
    tail_duration: float | None = None,
    max_tail_duration: float = 1.0,
) -> list[str]:
    errors: list[str] = []
    lines = text.splitlines()
    creative_index = find_section(lines, "创意说明")
    storyboard_index = find_section(lines, "完整分镜表")
    continuity_index = find_section(lines, "片段执行与连续性说明")
    if (
        creative_index is not None
        and storyboard_index is not None
        and creative_index >= storyboard_index
    ):
        errors.append("章节顺序非法：创意说明必须位于完整分镜表之前")
    if (
        continuity_index is not None
        and storyboard_index is not None
        and continuity_index <= storyboard_index
    ):
        errors.append("章节顺序非法：片段执行与连续性说明必须位于完整分镜表之后")

    validate_creative_section(text, errors)
    rows = parse_storyboard_table(lines, errors)
    if not rows:
        return errors

    required_nonempty = [
        "镜头职责",
        "新增信息",
        "画面层级",
        "主体与场景/素材",
        "画面动作",
        "镜头语言",
        "画面设计",
        "声音与文字",
        "转场/尾态",
        "风险/禁区",
    ]
    seen_shots: set[str] = set()
    beats: list[str] = []
    segments: list[str] = []
    intervals: list[tuple[float, float, str]] = []
    for index, row in enumerate(rows, start=1):
        beat_id = row["节拍ID"]
        shot_id = row["镜头ID"]
        segment_id = row["生成段ID"]
        beats.append(beat_id)
        segments.append(segment_id)

        if not BEAT_RE.fullmatch(beat_id):
            errors.append(f"第 {index} 镜节拍ID非法：{beat_id}")
        shot_match = SHOT_RE.fullmatch(shot_id)
        if not shot_match:
            errors.append(f"第 {index} 镜镜头ID非法：{shot_id}")
        else:
            shot_number = int(shot_id[2:])
            if shot_number != index:
                errors.append(
                    f"第 {index} 镜镜头ID应为 SH{index:03d}，当前为 {shot_id}"
                )
        if not SEGMENT_RE.fullmatch(segment_id):
            errors.append(f"第 {index} 镜生成段ID非法：{segment_id}")
        if shot_id in seen_shots:
            errors.append(f"镜头ID重复：{shot_id}")
        seen_shots.add(shot_id)

        for field in required_nonempty:
            if not row[field].strip():
                errors.append(f"{shot_id or f'第 {index} 镜'} 缺少：{field}")

        time_match = TIME_RE.fullmatch(row["时间"])
        row_duration = 0.0
        if not time_match:
            errors.append(f"{shot_id} 时间格式非法：{row['时间']}")
        else:
            try:
                start = parse_time(time_match.group("start"))
                end = parse_time(time_match.group("end"))
                if end <= start:
                    errors.append(f"{shot_id} 结束时间必须晚于开始时间")
                else:
                    row_duration = end - start
                intervals.append((start, end, shot_id))
            except ValueError as exc:
                errors.append(f"{shot_id} {exc}")

        sound = row["声音与文字"]
        spoken_segments, valid_braces = extract_spoken_segments(sound)
        if not valid_braces:
            errors.append(f"{shot_id} 的台词花括号不配对")
        cjk_count = sum(
            len(CJK_RE.findall(spoken)) for spoken in spoken_segments
        )
        if (
            row_duration > 0
            and cjk_count / row_duration > max_chars_per_second + 1e-9
        ):
            errors.append(
                f"{shot_id} 台词密度 {cjk_count / row_duration:.2f} 字/秒，"
                f"超过上限 {max_chars_per_second:g}"
            )

    validate_grouping(beats, "节拍ID", errors)
    validate_grouping(segments, "生成段ID", errors)
    if all(BEAT_RE.fullmatch(value) for value in beats):
        validate_group_sequence(beats, "节拍ID", "B", 2, errors)
    if all(SEGMENT_RE.fullmatch(value) for value in segments):
        validate_group_sequence(segments, "生成段ID", "SEG", 2, errors)

    if intervals:
        if abs(intervals[0][0]) > 0.05:
            errors.append(
                f"时间轴必须从 0 秒开始，当前从 {intervals[0][0]:g} 秒开始"
            )
        for previous, current in zip(intervals, intervals[1:]):
            gap = current[0] - previous[1]
            if abs(gap) > 0.05:
                relation = "空档" if gap > 0 else "重叠"
                errors.append(
                    f"{previous[2]} 到 {current[2]} 存在 "
                    f"{abs(gap):.2f} 秒{relation}"
                )
        actual_duration = intervals[-1][1]
        if (
            expected_duration is not None
            and abs(actual_duration - expected_duration) > 0.05
        ):
            errors.append(
                f"分镜总时长 {actual_duration:g} 秒，"
                f"与预期 {expected_duration:g} 秒不一致"
            )
        required_shots = min_shots or 1
        if len(rows) < required_shots:
            errors.append(f"镜头数 {len(rows)} 少于下限 {required_shots}")
        if max_shots is not None and len(rows) > max_shots:
            errors.append(f"镜头数 {len(rows)} 超过上限 {max_shots}")

        if (
            require_opening_cut
            and 4.0 <= actual_duration <= 15.05
        ):
            opening_indexes = [
                index
                for index, (start, _, _) in enumerate(intervals)
                if start < 3.0
            ]
            opening_shots = len(opening_indexes)
            if opening_shots < 2:
                errors.append("前三秒至少需要一次切镜")

        if 4.0 <= actual_duration <= 15.05:
            if tail_duration is None:
                errors.append("缺少稳定尾帧时长：请传入 --tail-duration")
            elif 0 < tail_duration < 0.6:
                errors.append(
                    f"稳定尾帧 {tail_duration:g} 秒，低于 0.6 秒下限"
                )
            elif tail_duration > max_tail_duration:
                errors.append(
                    f"稳定尾帧 {tail_duration:g} 秒，"
                    f"超过 {max_tail_duration:g} 秒上限"
                )
            elif tail_duration > actual_duration:
                errors.append("稳定尾帧时长不能超过视频总时长")

    return errors


def self_test() -> int:
    valid = """# 测试完整分镜

## 创意说明
- 核心主线：测试主线
- 表达意图与观看路径：问题到结果
- 视觉记忆点与母题：一条光线
- 视听与文字策略：默剧与动作拟音
- 素材使用与风险边界：不虚构

## 完整分镜表
| 节拍ID | 镜头ID | 生成段ID | 时间 | 镜头职责 | 新增信息 | 画面层级 | 主体与场景/素材 | 画面动作 | 镜头语言 | 画面设计 | 声音与文字 | 转场/尾态 | 风险/禁区 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B01 | SH001 | SEG01 | 00:00.0-00:01.5 | 钩子 | 问题出现 | A-roll | 人物在桌边 | 抬头看向屏幕 | 中近景固定 | 冷色侧光 | <提示音> | 视线切出 | 不虚构界面 |
| B02 | SH002 | SEG01 | 00:01.5-00:03.0 | 结果 | 产品解决问题 | 产品特写 | 产品位于桌面 | 按键后屏幕完成 | 近景推入 | 暖色正光 | <完成音> | 产品停稳 | 产品不变形 |
"""
    errors = validate_storyboard(valid, 3.0, None, 5.0)
    if errors:
        print("self-test valid case failed:", *errors, sep="\n", file=sys.stderr)
        return 1

    invalid = valid.replace("00:01.5-00:03.0", "00:02.0-00:03.0")
    errors = validate_storyboard(invalid, 3.0, None, 5.0)
    if not errors:
        print("self-test invalid case unexpectedly passed", file=sys.stderr)
        return 1

    dense_dialogue = valid.replace(
        "<提示音>",
        "旁白：{甲乙丙丁戊}{己庚辛壬癸}",
    )
    errors = validate_storyboard(dense_dialogue, 3.0, None, 5.0)
    if not any("台词密度" in error for error in errors):
        print("self-test dialogue aggregation failed", file=sys.stderr)
        return 1

    malformed_dialogue = valid.replace("<提示音>", "旁白：}甲乙{")
    errors = validate_storyboard(malformed_dialogue, 3.0, None, 5.0)
    if not any("花括号不配对" in error for error in errors):
        print("self-test dialogue brace validation failed", file=sys.stderr)
        return 1

    reversed_shots = valid.replace("SH001", "SH999").replace("SH002", "SH001")
    errors = validate_storyboard(reversed_shots, 3.0, None, 5.0)
    if not any("镜头ID应为" in error for error in errors):
        print("self-test shot sequence validation failed", file=sys.stderr)
        return 1

    invalid_beat_start = valid.replace("B01", "B02").replace("B02", "B03")
    errors = validate_storyboard(invalid_beat_start, 3.0, None, 5.0)
    if not any("节拍ID 必须从 B01" in error for error in errors):
        print("self-test beat sequence validation failed", file=sys.stderr)
        return 1

    invalid_segment_width = valid.replace("SEG01", "SEG001")
    errors = validate_storyboard(invalid_segment_width, 3.0, None, 5.0)
    if not any("生成段ID非法" in error for error in errors):
        print("self-test segment width validation failed", file=sys.stderr)
        return 1

    invalid_segment_start = valid.replace("SEG01", "SEG02")
    errors = validate_storyboard(invalid_segment_start, 3.0, None, 5.0)
    if not any("生成段ID 必须从 SEG01" in error for error in errors):
        print("self-test segment sequence validation failed", file=sys.stderr)
        return 1

    invalid_seconds = valid.replace("00:01.5", "00:61.5", 1)
    errors = validate_storyboard(invalid_seconds, 3.0, None, 5.0)
    if not any("秒字段必须小于 60" in error for error in errors):
        print("self-test time field validation failed", file=sys.stderr)
        return 1

    reversed_sections = valid.replace("## 创意说明", "## 临时说明") + (
        "\n## 创意说明\n"
        "- 核心主线：测试主线\n"
        "- 表达意图与观看路径：问题到结果\n"
        "- 视觉记忆点与母题：一条光线\n"
        "- 视听与文字策略：默剧与动作拟音\n"
        "- 素材使用与风险边界：不虚构\n"
    )
    errors = validate_storyboard(reversed_sections, 3.0, None, 5.0)
    if not any("章节顺序非法" in error for error in errors):
        print("self-test section order validation failed", file=sys.stderr)
        return 1

    errors = validate_storyboard(valid, 3.0, 3, 5.0)
    if not any("少于下限" in error for error in errors):
        print("self-test explicit shot minimum failed", file=sys.stderr)
        return 1

    sparse_but_continuous = valid.replace(
        "00:00.0-00:01.5",
        "00:00.0-00:07.5",
    ).replace(
        "00:01.5-00:03.0",
        "00:07.5-00:15.0",
    ).replace(
        "抬头看向屏幕",
        "抬头发现屏幕 -> 伸手点按 -> 屏幕给出反馈",
    ).replace(
        "按键后屏幕完成",
        "接住完成状态 -> 手离开按钮 -> 结果稳定可读",
    )
    errors = validate_storyboard(
        sparse_but_continuous,
        15.0,
        8,
        5.0,
        tail_duration=7.5,
    )
    if not any("镜头数 2 少于下限 8" in error for error in errors):
        print("self-test 15-second shot minimum failed", file=sys.stderr)
        return 1
    if not any("稳定尾帧 7.5 秒" in error for error in errors):
        print("self-test tail-duration validation failed", file=sys.stderr)
        return 1
    tail_only_errors = validate_storyboard(
        sparse_but_continuous,
        15.0,
        8,
        5.0,
        tail_duration=7.5,
        max_tail_duration=8.0,
    )
    if any("尾帧" in error for error in tail_only_errors):
        print("self-test explicit tail duration failed", file=sys.stderr)
        return 1

    valid_15_rows = [
        ("00:00.0-00:00.8", "异常入场", "异常首次出现"),
        ("00:00.8-00:01.8", "主体揭示", "主体身份明确"),
        ("00:01.8-00:03.0", "任务启动", "核心动作开始"),
        ("00:03.0-00:05.2", "动作桥", "运动路径完整"),
        ("00:05.2-00:07.0", "核心证明", "第一结果出现"),
        ("00:07.0-00:09.3", "反馈升级", "人物反馈变化"),
        ("00:09.3-00:14.2", "结果回收", "结果与品牌关联"),
        ("00:14.2-00:15.0", "尾帧稳定", "品牌与行动明确"),
    ]
    valid_15_table = "\n".join(
        (
            f"| B{index:02d} | SH{index:03d} | SEG01 | {time_range} | "
            f"{duty} | {info} | A-roll | 主体{index} | "
            f"触发{index} -> 变化{index} -> 反馈{index} | "
            f"机位{index} | 设计{index} | <声音{index}> | "
            f"状态{index}承接下一镜 | 禁区{index} |"
        )
        for index, (time_range, duty, info) in enumerate(valid_15_rows, start=1)
    )
    valid_15 = valid[: valid.rfind("| B01")] + valid_15_table + "\n"
    errors = validate_storyboard(
        valid_15,
        15.0,
        8,
        5.0,
        require_opening_cut=True,
        tail_duration=0.8,
    )
    if errors:
        print(
            "self-test valid 15-second structure failed:",
            *errors,
            sep="\n",
            file=sys.stderr,
        )
        return 1

    short_tail_errors = validate_storyboard(
        valid_15,
        15.0,
        8,
        5.0,
        require_opening_cut=True,
        tail_duration=0.3,
    )
    if not any("低于 0.6 秒下限" in error for error in short_tail_errors):
        print("self-test tail-duration lower bound failed", file=sys.stderr)
        return 1

    short_rows = [
        ("00:00.0-00:02.0", "异常入场", "异常与主体连续升级"),
        ("00:02.0-00:03.0", "首次反馈", "第一结果出现"),
        ("00:03.0-00:05.0", "核心证明", "证明过程完成"),
        ("00:05.0-00:06.0", "结果收束", "主题与结果关联"),
    ]
    short_table = "\n".join(
        (
            f"| B{index:02d} | SH{index:03d} | SEG01 | {time_range} | "
            f"{duty} | {info} | A-roll | 主体{index} | "
            f"触发{index} -> 变化{index} -> 反馈{index} | "
            f"机位{index} | 设计{index} | <声音{index}> | "
            f"状态{index}承接下一镜 | 禁区{index} |"
        )
        for index, (time_range, duty, info) in enumerate(short_rows, start=1)
    )
    valid_short = valid[: valid.rfind("| B01")] + short_table + "\n"
    errors = validate_storyboard(
        valid_short,
        6.0,
        4,
        5.0,
        require_opening_cut=True,
        tail_duration=0.8,
    )
    if errors:
        print(
            "self-test valid short structure failed:",
            *errors,
            sep="\n",
            file=sys.stderr,
        )
        return 1

    invalid_short_opening = valid_short.replace(
        "00:00.0-00:02.0",
        "00:00.0-00:03.1",
    ).replace(
        "00:02.0-00:03.0",
        "00:03.1-00:04.0",
    ).replace(
        "00:03.0-00:05.0",
        "00:04.0-00:05.0",
    )
    errors = validate_storyboard(
        invalid_short_opening,
        6.0,
        4,
        5.0,
        require_opening_cut=True,
        tail_duration=0.8,
    )
    if not any("前三秒至少需要一次切镜" in error for error in errors):
        print("self-test short opening validation failed", file=sys.stderr)
        return 1

    one_shot_table = (
        "| B01 | SH001 | SEG01 | 00:00.0-00:05.0 | 连续运动 | "
        "主体完成一次状态变化 | A-roll | 单图主体 | "
        "启动 -> 发展 -> 反馈 -> 回环 | 连续轻跟随 | 设计 | "
        "<环境声> | 回到起始状态 | 不改变主体身份 |"
    )
    one_shot = valid[: valid.rfind("| B01")] + one_shot_table + "\n"
    errors = validate_storyboard(
        one_shot,
        5.0,
        1,
        5.0,
        max_shots=1,
        tail_duration=0.0,
    )
    if errors:
        print(
            "self-test photo animation failed:",
            *errors,
            sep="\n",
            file=sys.stderr,
        )
        return 1

    wrong_photo_duration = one_shot.replace(
        "00:00.0-00:05.0",
        "00:00.0-00:06.0",
    )
    errors = validate_storyboard(
        wrong_photo_duration,
        5.0,
        1,
        5.0,
        max_shots=1,
        tail_duration=0.0,
    )
    if not any("与预期 5 秒不一致" in error for error in errors):
        print("self-test photo animation duration failed", file=sys.stderr)
        return 1

    errors = validate_storyboard(
        one_shot,
        5.0,
        1,
        5.0,
        max_shots=3,
        tail_duration=0.0,
    )
    if errors:
        print(
            "self-test simple motion failed:",
            *errors,
            sep="\n",
            file=sys.stderr,
        )
        return 1

    errors = validate_storyboard(
        valid_short,
        6.0,
        1,
        5.0,
        max_shots=1,
        tail_duration=0.0,
    )
    if not any("镜头数 4 超过上限 1" in error for error in errors):
        print("self-test one-take shot count failed", file=sys.stderr)
        return 1

    print("self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="客观校验完整分镜 Markdown，不评价创意质量。"
    )
    parser.add_argument("storyboard", nargs="?", type=Path)
    parser.add_argument("--expected-duration", type=float)
    parser.add_argument("--min-shots", type=int)
    parser.add_argument("--max-shots", type=int)
    parser.add_argument("--require-opening-cut", action="store_true")
    parser.add_argument("--max-chars-per-second", type=float, default=5.0)
    parser.add_argument("--tail-duration", type=float)
    parser.add_argument("--max-tail-duration", type=float, default=1.0)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if args.storyboard is None:
        parser.error("缺少完整分镜 Markdown 路径")
    if args.expected_duration is None:
        parser.error("缺少必填参数 --expected-duration")
    if args.min_shots is None:
        parser.error("缺少必填参数 --min-shots")
    if args.min_shots is not None and args.min_shots <= 0:
        parser.error("--min-shots 必须是正整数")
    if args.max_shots is not None and args.max_shots <= 0:
        parser.error("--max-shots 必须是正整数")
    if args.max_shots is not None and args.max_shots < args.min_shots:
        parser.error("--max-shots 不能小于 --min-shots")
    if args.max_chars_per_second <= 0:
        parser.error("--max-chars-per-second 必须大于 0")
    if args.tail_duration is not None and args.tail_duration < 0:
        parser.error("--tail-duration 必须大于或等于 0")
    if args.max_tail_duration <= 0:
        parser.error("--max-tail-duration 必须大于 0")

    errors = validate_storyboard(
        args.storyboard.read_text(encoding="utf-8"),
        args.expected_duration,
        args.min_shots,
        args.max_chars_per_second,
        args.max_shots,
        args.require_opening_cut,
        args.tail_duration,
        args.max_tail_duration,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"OK: {args.storyboard}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
