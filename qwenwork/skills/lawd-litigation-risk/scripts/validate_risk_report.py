#!/usr/bin/env python3
"""交付门禁：校验「诉讼风险与清偿评估」单元的报告是否可交付。

校验三件事：
  1. 胜诉概率 / 清偿率 / 回收率若出现，必须是区间或带明确依据（禁止无依据的单一精确数值）；
  2. 工商数据未取得时，禁止出现完整评估结论章节（A 档降级硬门禁）；
  3. 报告必备章节齐备（按模式校验 9 章）。

未通过时打印拦截清单并以非零退出码阻断交付。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# --- 章节要求（章节名 -> 命中任一关键词即视为存在） -------------------------------

REQUIRED_SECTIONS: dict[str, list[tuple[str, tuple[str, ...]]]] = {
    "litigation": [
        ("一、执行摘要 · Decision Pack", ("执行摘要", "Decision Pack")),
        ("二、数据来源与说明", ("数据来源",)),
        ("三、主体工商基本信息", ("主体工商", "工商基本信息", "企业身份核实")),
        ("四、企业当前诉讼地位", ("当前诉讼地位", "五维司法")),
        ("五、企业历史诉讼轨迹", ("历史诉讼轨迹", "年度诉讼趋势")),
        ("六、关键案件文书摘要", ("关键案件",)),
        ("七、诉讼类型风险模式分析", ("风险模式", "执行风险矩阵")),
        ("八、立案建议", ("立案建议",)),
        ("九、置信度分布", ("置信度",)),
    ],
    "recovery": [
        ("一、执行摘要 · Decision Pack", ("执行摘要", "Decision Pack")),
        ("二、数据来源与互证方法", ("数据来源",)),
        ("三、基本信息 × 财务底盘", ("财务底盘",)),
        ("四、可执行资产清单", ("可执行资产",)),
        ("五、当前债务压力扫描", ("债务压力",)),
        ("六、历史偿债模式识别", ("偿债模式",)),
        ("七、法代 / 实控人个人兜底评估", ("兜底",)),
        ("八、综合追偿评级 × 保全标的", ("追偿评级",)),
        ("九、免责声明", ("免责",)),
    ],
}

MODE_LABEL = {"litigation": "模式A 诉讼风险评估", "recovery": "模式B 债务清偿能力评估"}

# --- 结论章节（工商数据未取得时禁止出现） ---------------------------------------

CONCLUSION_MARKERS = (
    "执行风险评级",
    "立案建议",
    "胜诉概率推演",
    "追偿评级",
    "清偿率测算",
    "预期回收率",
    "保全标的清单",
    "五维度得分",
)

# --- 概率 / 清偿率表述 ----------------------------------------------------------

RATE_KEYWORDS = (
    "胜诉概率",
    "败诉概率",
    "胜诉率",
    "免责率",
    "清偿率",
    "回收率",
    "追偿率",
    "受偿率",
)
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?\s*%|(?<![\d.])0\.\d+(?![\d])")
RANGE_RE = re.compile(
    r"\d+(?:\.\d+)?\s*%?\s*(?:-|－|–|—|~|～|至|到)\s*\d+(?:\.\d+)?\s*%"
)
EVIDENCE_KEYWORDS = (
    "依据",
    "推演",
    "测算",
    "参见",
    "见 §",
    "见§",
    "区间",
    "样本",
    "保守",
    "中性",
    "激进",
    "公式",
)
SOURCE_CODE_RE = re.compile(r"\[[A-Z][A-Z\-]{1,}\]")
STATUS_RE = re.compile(r"工商数据获取状态[^\n]*?(已取得|未取得)")
INSTALL_HINT_KEYWORDS = ("连接器",)
UNVERIFIED_MARKER = "未核验"


def detect_mode(text: str) -> str | None:
    recovery_hits = sum(
        text.count(key) for key in ("债务清偿能力评估", "追偿评级", "清偿率", "保全标的")
    )
    litigation_hits = sum(
        text.count(key) for key in ("诉讼风险评估", "立案建议", "五维司法", "执行风险评级")
    )
    if recovery_hits == litigation_hits == 0:
        return None
    return "recovery" if recovery_hits > litigation_hits else "litigation"


def is_skippable(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if "{" in stripped and "}" in stripped:  # 模板占位行
        return True
    if set(stripped) <= set("|-: "):  # 表格分隔行
        return True
    return False


def check_rates(lines: list[str]) -> tuple[list[str], int]:
    """校验概率 / 清偿率表述。返回（拦截项, 命中的表述行数）。"""
    errors: list[str] = []
    checked = 0
    for index, line in enumerate(lines, start=1):
        if is_skippable(line):
            continue
        if not any(keyword in line for keyword in RATE_KEYWORDS):
            continue
        numbers = NUMBER_RE.findall(line)
        if not numbers:
            continue  # 纯定性表述，不校验
        checked += 1
        if RANGE_RE.search(line):
            continue
        if len(numbers) >= 2:  # 保守/中性/激进多档并列，等同区间
            continue
        if any(keyword in line for keyword in EVIDENCE_KEYWORDS):
            continue
        if SOURCE_CODE_RE.search(line):
            continue
        errors.append(
            f"第 {index} 行：概率/清偿率出现无依据的单一精确数值 → {line.strip()}\n"
            f"    修正：改为区间表述（如 55%-70%）或补明确依据；纯定性表述（行内无数值）不会被拦截，"
            f"请检查同行是否混入了其他百分比/比例数值；概率推演统一放在立案建议章节。"
        )
    return errors, checked


def check_registry_gate(text: str, lines: list[str], forced: str) -> tuple[list[str], str]:
    """校验工商数据状态声明与 A 档降级硬门禁。返回（拦截项, 生效状态）。"""
    errors: list[str] = []
    match = STATUS_RE.search(text)
    declared = match.group(1) if match else None

    if declared is None:
        errors.append(
            "缺少必填声明行「**工商数据获取状态：** 已取得 / 未取得」，"
            "无法判定是否允许输出完整评估结论"
        )
    status = declared or ""
    if forced != "auto":
        expected = "已取得" if forced == "available" else "未取得"
        if declared and declared != expected:
            errors.append(
                f"--registry-data={forced} 与报告声明「{declared}」不一致，请先核对数据获取状态"
            )
        status = expected

    if status != "未取得":
        return errors, status or "已取得"

    # 降级分支：禁止完整评估结论（含行内概率/清偿率表述，防"胜诉率：65%"措辞绕过章节黑名单）
    for index, line in enumerate(lines, start=1):
        if is_skippable(line):
            continue
        for marker in CONCLUSION_MARKERS:
            if marker in line:
                errors.append(
                    f"第 {index} 行：工商数据未取得，禁止出现完整评估结论「{marker}」→ {line.strip()}"
                )
                break
        else:
            if any(keyword in line for keyword in RATE_KEYWORDS) and NUMBER_RE.search(line):
                errors.append(
                    f"第 {index} 行：工商数据未取得，禁止出现概率/清偿率数值 → {line.strip()}"
                )
    if UNVERIFIED_MARKER not in text:
        errors.append("工商数据未取得，报告全文必须标注「未核验」，当前一处也没有")
    if not any(keyword in text for keyword in INSTALL_HINT_KEYWORDS):
        errors.append(
            "工商数据未取得，报告必须提示用户前往「设置 → 连接器」安装企业信息类连接器"
        )
    return errors, status


def check_sections(text: str, mode: str, status: str) -> tuple[list[str], list[str]]:
    """校验必备章节。降级模式下不要求结论类章节。"""
    if status == "未取得":
        return [], ["降级模式：跳过 9 章必备校验（仅允许待核验事项清单 + 初步方向）"]
    errors: list[str] = []
    found: list[str] = []
    for name, keywords in REQUIRED_SECTIONS[mode]:
        if any(keyword in text for keyword in keywords):
            found.append(name)
        else:
            errors.append(f"缺少必备章节：{name}（关键词任一：{' / '.join(keywords)}）")
    return errors, found


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="validate_risk_report.py",
        description=(
            "校验「诉讼风险与清偿评估」报告：①概率/清偿率必须区间或带依据 "
            "②工商数据未取得时禁止完整评估结论 ③必备章节齐备。未通过以非零退出码阻断交付。"
        ),
        epilog=(
            "示例：\n"
            "  python3 scripts/validate_risk_report.py report.md\n"
            "  python3 scripts/validate_risk_report.py report.md --mode recovery\n"
            "  python3 scripts/validate_risk_report.py report.md --registry-data missing\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("report", type=Path, help="报告文件路径（Markdown）")
    parser.add_argument(
        "--mode",
        choices=("auto", "litigation", "recovery"),
        default="auto",
        help="报告模式：litigation=模式A 诉讼风险；recovery=模式B 清偿能力；auto=按正文自动判定（默认）",
    )
    parser.add_argument(
        "--registry-data",
        choices=("auto", "available", "missing"),
        default="auto",
        help="工商数据获取状态：auto=读报告声明行（默认）；available/missing=显式指定并与声明行交叉校验",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        text = args.report.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"校验失败：无法读取报告文件：{exc}", file=sys.stderr)
        return 2
    if not text.strip():
        print("校验失败：报告文件为空", file=sys.stderr)
        return 2

    lines = text.splitlines()

    mode = args.mode
    if mode == "auto":
        detected = detect_mode(text)
        if detected is None:
            print(
                "校验失败：无法自动判定报告模式，请用 --mode litigation|recovery 显式指定",
                file=sys.stderr,
            )
            return 2
        mode = detected

    errors: list[str] = []
    passes: list[str] = []

    gate_errors, status = check_registry_gate(text, lines, args.registry_data)
    errors.extend(gate_errors)
    if not gate_errors:
        passes.append(f"工商数据获取状态声明 = {status}；A 档降级门禁通过")

    rate_errors, rate_checked = check_rates(lines)
    errors.extend(rate_errors)
    if not rate_errors:
        passes.append(f"概率/清偿率表述校验通过（含数字的相关表述 {rate_checked} 处，均为区间或带依据）")

    section_errors, section_info = check_sections(text, mode, status)
    errors.extend(section_errors)
    if not section_errors:
        if status == "未取得":
            passes.extend(section_info)
        else:
            passes.append(f"必备章节齐备（{len(section_info)}/{len(REQUIRED_SECTIONS[mode])} 章）")

    header = f"报告：{args.report}｜模式：{MODE_LABEL[mode]}"
    if errors:
        print(f"❌ 门禁未通过 — {header}", file=sys.stderr)
        print(f"拦截 {len(errors)} 项：", file=sys.stderr)
        for item in errors:
            print(f"- {item}", file=sys.stderr)
        if passes:
            print("已通过项：", file=sys.stderr)
            for item in passes:
                print(f"- {item}", file=sys.stderr)
        print("未通过禁止交付：请修复后重新运行本脚本。", file=sys.stderr)
        return 1

    print(f"✅ 门禁通过 — {header}")
    for item in passes:
        print(f"- {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
