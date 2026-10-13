#!/usr/bin/env python3
"""交付门禁：校验起诉状风险分析报告（模式A）/ 争议焦点分析报告（模式B）。

校验四项（对应体检清单必补项）：
  1. 争点编号连续、无重复
  2. 要件 <-> 争点映射完整（无悬空要件、无指向不存在的争点）
  3. 模式A：逐项诉请回应数 >= 原告诉请数（防漏项）
  4. 法条引用带法律名 + 条号（禁裸条号）

用法：
  python3 validate_analysis_report.py REPORT.md [--mode {a,b,auto}] [--claims N]

退出码：0 = 全部通过；1 = 存在拦截项（禁止交付）；2 = 参数/读取错误。
无第三方依赖，Python 3.8+。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

# --------------------------------------------------------------------------- #
# 中文数字
# --------------------------------------------------------------------------- #

_CN_DIGITS = {
    "零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}
_NUM_CHARS = "0-9０-９〇零一二两三四五六七八九十百"


def cn_to_int(token: str) -> Optional[int]:
    """把「三」「十二」「12」「１２」等转成 int；无法解析返回 None。"""
    token = token.strip()
    if not token:
        return None
    # 全角转半角
    token = token.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    if token.isdigit():
        return int(token)

    total = 0
    section = 0
    matched = False
    for ch in token:
        if ch in _CN_DIGITS:
            section = _CN_DIGITS[ch]
            matched = True
        elif ch == "十":
            section = (section or 1) * 10
            matched = True
        elif ch == "百":
            section = (section or 1) * 100
            matched = True
        else:
            return None
    if not matched:
        return None
    total += section
    return total or None


# --------------------------------------------------------------------------- #
# 结果收集
# --------------------------------------------------------------------------- #


class Result:
    def __init__(self) -> None:
        self.passes: List[str] = []
        self.fails: List[str] = []
        self.warns: List[str] = []

    def ok(self, msg: str) -> None:
        self.passes.append(msg)

    def fail(self, msg: str) -> None:
        self.fails.append(msg)

    def warn(self, msg: str) -> None:
        self.warns.append(msg)


# --------------------------------------------------------------------------- #
# 解析工具
# --------------------------------------------------------------------------- #

_HEAD_PREFIX = r"^[\s>*#\-•]*"
_TREE_CHARS = ("├", "└", "│", "┣", "┗")

# 争点声明的两种规范写法（分组独立校验，避免跨形式误判重复）
FOCUS_PATTERNS: Sequence[Tuple[str, "re.Pattern[str]"]] = (
    ("争议焦点X", re.compile(_HEAD_PREFIX + r"\**\s*争议焦点\s*([" + _NUM_CHARS + r"]+)\s*[：:、.\)）】]")),
    ("【焦点X】", re.compile(_HEAD_PREFIX + r"\**\s*【?\s*焦点\s*([" + _NUM_CHARS + r"]+)\s*】")),
)

CLAIM_PATTERN = re.compile(_HEAD_PREFIX + r"\**\s*诉请\s*([" + _NUM_CHARS + r"]+)\s*[：:、.\)）]")

EMPTY_MAPPING_TOKENS = {
    "", "-", "—", "――", "无", "无对应", "未归属", "待定", "待补充", "n/a", "na",
    "none", "null", "/", "暂无", "空", "?", "？", "无争点", "未识别",
}

LAW_ARTICLE_PATTERN = re.compile(
    r"第\s*[" + _NUM_CHARS + r"]+\s*(?:[、,，]\s*[" + _NUM_CHARS + r"]+\s*)*条"
)
LAW_NAME_HINTS = ("》", "同法", "该法", "本法", "上述法律", "前述法律", "该司法解释", "同解释")


def is_table_row(line: str) -> bool:
    return line.lstrip().startswith("|")


def mask_code_fences(lines: Sequence[str]) -> List[str]:
    """把围栏代码块内的行清空（保留行号），避免代码块中的示例表格/树线被误判为正文结构。"""
    masked = list(lines)
    in_fence = False
    for i, raw in enumerate(lines):
        stripped = raw.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            masked[i] = ""
            continue
        if in_fence:
            masked[i] = ""
    return masked


def is_tree_line(line: str) -> bool:
    stripped = line.lstrip()
    return any(stripped.startswith(ch) for ch in _TREE_CHARS) or any(
        ch in stripped[:6] for ch in _TREE_CHARS
    )


def collect_focus_numbers(lines: Sequence[str]) -> Dict[str, List[Tuple[int, int]]]:
    """返回 {形式名: [(争点编号, 行号), ...]}，仅取非表格、非体系图树线的声明行。"""
    found: Dict[str, List[Tuple[int, int]]] = {name: [] for name, _ in FOCUS_PATTERNS}
    for lineno, raw in enumerate(lines, start=1):
        if is_table_row(raw) or is_tree_line(raw):
            continue
        for name, pattern in FOCUS_PATTERNS:
            match = pattern.match(raw)
            if match:
                number = cn_to_int(match.group(1))
                if number:
                    found[name].append((number, lineno))
                break
    return found


def all_focus_numbers(found: Dict[str, List[Tuple[int, int]]]) -> Set[int]:
    numbers: Set[int] = set()
    for items in found.values():
        numbers.update(n for n, _ in items)
    return numbers


def split_table_row(line: str) -> List[str]:
    cells = line.strip().strip("|").split("|")
    return [cell.strip() for cell in cells]


def is_separator_row(cells: Sequence[str]) -> bool:
    return bool(cells) and all(set(cell) <= set("-: ") and cell for cell in cells)


def find_mapping_table(lines: Sequence[str]) -> Optional[Tuple[int, List[List[str]]]]:
    """定位「要件—争点映射表」：先找含要件+争点/焦点+映射的标题行，再取其后的第一张表。

    找不到标题时，退化为寻找表头同时含「要件」与「争点/焦点」的任意表格。
    返回 (表头行号, 行单元格列表) 或 None。
    """
    heading_idx: Optional[int] = None
    for idx, raw in enumerate(lines):
        if is_table_row(raw):
            continue
        text = raw.strip()
        if "要件" in text and ("争点" in text or "焦点" in text) and ("映射" in text or "对应" in text):
            heading_idx = idx
            break

    def read_table(start: int) -> Optional[Tuple[int, List[List[str]]]]:
        i = start
        while i < len(lines) and not is_table_row(lines[i]):
            # 标题后若出现新的一级/二级标题则放弃
            if lines[i].lstrip().startswith("#") and i != start:
                return None
            i += 1
        if i >= len(lines):
            return None
        rows: List[List[str]] = []
        header_line = i
        while i < len(lines) and is_table_row(lines[i]):
            cells = split_table_row(lines[i])
            if not is_separator_row(cells):
                rows.append(cells)
            i += 1
        return (header_line + 1, rows) if rows else None

    if heading_idx is not None:
        table = read_table(heading_idx + 1)
        if table:
            return table

    for idx, raw in enumerate(lines):
        if not is_table_row(raw):
            continue
        cells = split_table_row(raw)
        joined = " ".join(cells)
        if "要件" in joined and ("争点" in joined or "焦点" in joined):
            return read_table(idx)
    return None


EXEMPT_CLAIM_TOKENS = ("随主请求", "不单独评估", "不单独分析", "不单独列项", "随主诉处理")


def find_claim_total_from_table(lines: Sequence[str]) -> Optional[Tuple[int, int]]:
    """从「诉讼请求拆解与风险评级总表」推断 (原告诉请数, 显式豁免逐项分析的诉请数)。

    实务中诉讼费等附随请求常在总表内标注「随主请求，不单独评估」而不单独成章；
    这类**显式声明**的豁免不计入漏项，静默漏项仍会被拦截。
    """
    for idx, raw in enumerate(lines):
        if is_table_row(raw):
            continue
        text = raw.strip()
        if ("风险评级总表" in text) or ("诉讼请求拆解" in text) or ("诉请总表" in text):
            i = idx + 1
            while i < len(lines) and not is_table_row(lines[i]):
                if lines[i].lstrip().startswith("#") and i != idx + 1:
                    return None
                i += 1
            count = 0
            exempt = 0
            while i < len(lines) and is_table_row(lines[i]):
                cells = split_table_row(lines[i])
                if cells and not is_separator_row(cells):
                    first = cells[0]
                    if cn_to_int(first) is not None and "序号" not in first:
                        count += 1
                        row_text = " ".join(cells)
                        if any(token in row_text for token in EXEMPT_CLAIM_TOKENS):
                            exempt += 1
                i += 1
            return (count, exempt) if count else None
    return None


# --------------------------------------------------------------------------- #
# 各校验项
# --------------------------------------------------------------------------- #


def check_focus_numbering(lines: Sequence[str], result: Result, required: bool) -> Set[int]:
    found = collect_focus_numbers(lines)
    total_declared = sum(len(items) for items in found.values())
    if total_declared == 0:
        if required:
            result.fail("未识别到任何争议焦点声明（应写成「争议焦点一：…」或「【焦点一】」），无法校验争点编号")
        else:
            result.ok("争点编号：报告未声明争议焦点，跳过该项")
        return set()

    clean = True
    for form, items in found.items():
        if not items:
            continue
        numbers = [n for n, _ in items]
        seen: Dict[int, int] = {}
        for number, lineno in items:
            if number in seen:
                result.fail(
                    f"争点编号重复：{form} 形式的「{number}」在第 {seen[number]} 行与第 {lineno} 行各出现一次"
                )
                clean = False
            else:
                seen[number] = lineno
        distinct = sorted(set(numbers))
        expected = list(range(1, len(distinct) + 1))
        if distinct != expected:
            missing = sorted(set(expected) - set(distinct))
            result.fail(
                f"争点编号不连续：{form} 形式实际为 {distinct}，应为 {expected}"
                + (f"，缺 {missing}" if missing else "")
            )
            clean = False
    if clean:
        summary = "；".join(
            f"{form} {len(items)} 个" for form, items in found.items() if items
        )
        result.ok(f"争点编号连续且无重复（{summary}）")
    return all_focus_numbers(found)


def check_element_mapping(
    lines: Sequence[str], result: Result, focus_numbers: Set[int], required: bool
) -> None:
    table = find_mapping_table(lines)
    if table is None:
        if required:
            result.fail(
                "缺少「要件—争点映射表」：模式B / A+B 连做必须给出每个法律要件的争点归属"
                "（表头需含「法律要件」与「对应争议焦点」两列）"
            )
        else:
            result.ok("要件↔争点映射：报告无映射表，模式A 单独交付时不强制，跳过该项")
        return

    header_lineno, rows = table
    header = rows[0]
    element_col = next((i for i, c in enumerate(header) if "要件" in c), None)
    focus_col = next(
        (i for i, c in enumerate(header) if ("争点" in c or "焦点" in c) and "要件" not in c),
        None,
    )
    if element_col is None or focus_col is None:
        result.fail(
            f"要件—争点映射表（第 {header_lineno} 行）表头无法识别："
            "需同时包含「要件」列与「对应争议焦点」列"
        )
        return

    data_rows = rows[1:]
    if not data_rows:
        result.fail(f"要件—争点映射表（第 {header_lineno} 行）没有数据行，无法证明要件已全部归属")
        return

    dangling: List[str] = []
    unknown_refs: List[str] = []
    checked = 0
    for offset, cells in enumerate(data_rows, start=1):
        if max(element_col, focus_col) >= len(cells):
            result.fail(f"要件—争点映射表第 {offset} 个数据行列数不足，无法校验：{cells}")
            continue
        element = cells[element_col].strip()
        focus_cell = cells[focus_col].strip()
        if not element or element.lower() in EMPTY_MAPPING_TOKENS:
            continue
        checked += 1
        if focus_cell.lower() in EMPTY_MAPPING_TOKENS:
            dangling.append(f"{element}（争点列为「{focus_cell or '空'}」）")
            continue
        refs = [
            cn_to_int(m)
            for m in re.findall(r"(?:争议焦点|争点|焦点)\s*([" + _NUM_CHARS + r"]+)", focus_cell)
        ]
        refs = [r for r in refs if r]
        if not refs:
            plain = [cn_to_int(m) for m in re.findall(r"[" + _NUM_CHARS + r"]+", focus_cell)]
            refs = [r for r in plain if r]
        if not refs:
            dangling.append(f"{element}（争点列「{focus_cell}」未指明具体争点编号）")
            continue
        if focus_numbers:
            for ref in refs:
                if ref not in focus_numbers:
                    unknown_refs.append(f"{element} → 争议焦点{ref}（该争点不存在）")

    for item in dangling:
        result.fail(f"悬空要件（无争点归属）：{item}")
    for item in unknown_refs:
        result.fail(f"要件映射指向不存在的争点：{item}")
    if not dangling and not unknown_refs:
        result.ok(f"要件↔争点映射完整：{checked} 个要件全部有争点归属，且引用的争点编号均存在")


def check_claim_coverage(
    lines: Sequence[str], result: Result, declared_claims: Optional[int]
) -> None:
    responses = []
    for lineno, raw in enumerate(lines, start=1):
        if is_table_row(raw) or is_tree_line(raw):
            continue
        match = CLAIM_PATTERN.match(raw)
        if match:
            number = cn_to_int(match.group(1))
            if number:
                responses.append(number)
    response_count = len(set(responses))

    exempt = 0
    if declared_claims is not None:
        total: Optional[int] = declared_claims
        source = "--claims 参数"
    else:
        parsed = find_claim_total_from_table(lines)
        if parsed is None:
            total = None
            source = "风险评级总表"
        else:
            total, exempt = parsed
            source = "风险评级总表"

    if total is None:
        result.fail(
            "无法确定原告诉请数：报告缺少「诉讼请求拆解与风险评级总表」，"
            "请补齐总表或运行时加 --claims N"
        )
        return

    required = total - exempt
    detail = f"原告诉请 {total} 项（来源：{source}）" + (
        f"，其中 {exempt} 项已在总表显式标注「随主请求/不单独评估」" if exempt else ""
    )

    if response_count == 0 and required > 0:
        result.fail(f"未识别到任何逐项诉请分析章节（应写成「诉请 1：…」）；{detail}")
        return
    if response_count < required:
        result.fail(
            f"逐项回应漏项：{detail}，需逐项分析 {required} 项，实际仅 {response_count} 项"
        )
        return
    result.ok(f"逐项回应完整：{detail}，需逐项分析 {required} 项，实际 {response_count} 项")


def check_law_citations(lines: Sequence[str], result: Result) -> None:
    bare: List[str] = []
    total = 0
    for lineno, raw in enumerate(lines, start=1):
        for match in LAW_ARTICLE_PATTERN.finditer(raw):
            total += 1
            before = raw[: match.start()]
            context = before[-60:]
            if any(hint in context for hint in LAW_NAME_HINTS):
                continue
            # 允许法律名写在上一非空行末尾
            prev = ""
            for back in range(lineno - 2, max(-1, lineno - 5), -1):
                if back < 0:
                    break
                if lines[back].strip():
                    prev = lines[back].strip()[-60:]
                    break
            if any(hint in prev for hint in LAW_NAME_HINTS) and not before.strip():
                continue
            snippet = raw.strip()
            if len(snippet) > 70:
                snippet = snippet[:70] + "…"
            bare.append(f"第 {lineno} 行：{match.group(0)}（缺法律名）｜{snippet}")

    if total == 0:
        result.warn("报告未出现任何「第X条」法条引用：若属未取得检索结果的降级情形，须在正文标注；否则请核查是否漏写法律依据")
        result.ok("法条引用格式：未发现裸条号（报告无条号引用）")
        return
    if bare:
        for item in bare:
            result.fail(f"法条引用缺法律名（应为《法律名称》第X条[第X款]）：{item}")
        return
    result.ok(f"法条引用格式合规：{total} 处条号引用均带《法律名称》")


# --------------------------------------------------------------------------- #
# 模式判定与主流程
# --------------------------------------------------------------------------- #


def detect_mode(text: str, lines: Sequence[str]) -> str:
    """按结构性强信号判定模式；仅提及「争议焦点」字样不足以判为模式B。"""
    a_signals = [
        kw
        for kw in (
            "起诉状深度解析报告",
            "起诉状风险分析报告",
            "风险评级总表",
            "诉讼请求拆解",
            "风险评分卡",
            "防御行动清单",
            "证据脆弱性分析",
        )
        if kw in text
    ]
    b_signals = [
        kw
        for kw in ("焦点体系图", "法庭辩论推演", "焦点攻防路线图", "report_profile", "要件—争点映射", "要件-争点映射")
        if kw in text
    ]
    if all_focus_numbers(collect_focus_numbers(lines)):
        b_signals.append("争点声明行")

    if a_signals and b_signals:
        return "ab"
    if b_signals:
        return "b"
    if a_signals:
        return "a"
    return "unknown"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="validate_analysis_report.py",
        description=(
            "起诉状分析与攻防策略（lawd-complaint-analyzer）交付门禁脚本。"
            "校验：①争点编号连续无重复 ②要件↔争点映射完整（无悬空要件）"
            "③模式A 逐项回应数≥原告诉请数 ④法条引用带法律名+条号。"
            "交付前必须运行，未通过禁止交付。"
        ),
        epilog=(
            "示例：\n"
            "  python3 validate_analysis_report.py 起诉状风险分析报告.md --mode a --claims 3\n"
            "  python3 validate_analysis_report.py 争议焦点分析报告.md --mode b\n"
            "  python3 validate_analysis_report.py report.md            # 自动判定模式\n"
            "退出码：0 通过 / 1 有拦截项（禁止交付） / 2 参数或读取错误"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("report", type=Path, help="待校验的报告文件（Markdown 或纯文本）")
    parser.add_argument(
        "--mode",
        choices=("a", "b", "ab", "auto"),
        default="auto",
        help="a=起诉状风险分析报告；b=争议焦点分析报告；ab=连做产物；auto=按内容自动判定（默认）",
    )
    parser.add_argument(
        "--claims",
        type=int,
        default=None,
        help="模式A：原告诉请项数（不给则从「风险评级总表」推断）",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    path: Path = args.report
    if not path.exists():
        print(f"校验失败：报告文件不存在：{path}", file=sys.stderr)
        return 2
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"校验失败：无法读取报告：{exc}", file=sys.stderr)
        return 2
    if not text.strip():
        print(f"校验失败：报告为空：{path}", file=sys.stderr)
        return 2

    lines = mask_code_fences(text.splitlines())
    mode = args.mode
    if mode == "auto":
        mode = detect_mode(text, lines)
        if mode == "unknown":
            print(
                "校验失败：无法自动判定报告模式，请显式指定 --mode a|b|ab",
                file=sys.stderr,
            )
            return 2

    result = Result()
    check_a = mode in ("a", "ab")
    check_b = mode in ("b", "ab")

    focus_numbers = check_focus_numbering(lines, result, required=check_b)
    check_element_mapping(lines, result, focus_numbers, required=check_b)
    if check_a:
        check_claim_coverage(lines, result, args.claims)
    else:
        result.ok("逐项回应数校验：非模式A 报告，跳过该项")
    check_law_citations(lines, result)

    mode_label = {"a": "模式A 起诉状风险分析", "b": "模式B 争议焦点分析", "ab": "模式A+B 连做"}[mode]
    print(f"=== 交付门禁校验：{path} ===")
    print(f"判定模式：{mode_label}（--mode {args.mode}）")
    print()
    print(f"【通过清单】{len(result.passes)} 项")
    for item in result.passes:
        print(f"  [PASS] {item}")
    if result.warns:
        print()
        print(f"【提示】{len(result.warns)} 项")
        for item in result.warns:
            print(f"  [WARN] {item}")
    print()
    if result.fails:
        print(f"【拦截清单】{len(result.fails)} 项 —— 未通过，禁止交付", file=sys.stderr)
        for item in result.fails:
            print(f"  [FAIL] {item}", file=sys.stderr)
        print("\n请修正上述问题后重跑本脚本；禁止绕过门禁交付。", file=sys.stderr)
        return 1
    print("【拦截清单】0 项 —— 门禁通过，可进入交付环节。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
