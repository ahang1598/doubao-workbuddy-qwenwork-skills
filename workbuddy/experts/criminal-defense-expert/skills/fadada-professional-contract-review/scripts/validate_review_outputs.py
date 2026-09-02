#!/usr/bin/env python3
"""Validate review DOCX deliverables and their separation rules.

交付前机检闸门（移植自 english-contract-review，去除 bilingual 检查）：
  - 通用：docx 包合法、无 emoji、A4 页面、表格总宽 ≤ 9026 DXA
  - redline（修订版/带批注修订版）：含 w:ins + w:del + comments.xml +
    修订说明汇总表 + 依据标签；不得含报告免责声明
  - clean：不残留修订/批注标记；不得含报告免责声明
  - report（评审报告/意见书）：开头 500 字符内含免责声明；标题为黑色
  - operations 覆盖：高/中风险必须落为 replace 类操作或带 comment_only_reason
"""

from __future__ import annotations

# 同目录模块（producer_evidence）在部分宿主环境下不会自动进入 sys.path，显式注入。
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

from lxml import etree

from producer_evidence import build_review_evidence, write_review_evidence


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿]", re.UNICODE)
DISCLAIMER_TEXT = "不构成正式法律意见"
# 裸占位符：章节被留空的信号。技能契约要求确不涉及的项写「经核实不涉及：<理由>」，
# 不得以裸「无」「本节不适用」「暂无」「/」占位。这些正是 build_review_report 对空内容
# 渲染出的字面（"无。" / "本节不适用。"），也是 LLM 写不完时最常塞的桩。
BARE_PLACEHOLDERS = {
    "无", "本节不适用", "暂无", "略", "待补充", "待完善", "待定",
    "/", "／", "n/a", "na", "todo", "tbd", "xx", "xxx",
}
# 子串级桩标记：出现即视为未完成，无论所在段落长短。「经核实不涉及」是允许形式，不在此列。
STUB_SUBSTRINGS = ("待补充", "待完善", "此处填写", "占位", "placeholder", "todo", "tbd")
# 红线批注标准模板字段（BLK-01 原因）：风险批注必须用这套字段，不得用非标准替代。
COMMENT_REQUIRED_FIELDS = ("【风险编号】", "【审查立场】", "【风险类型】", "【风险说明】", "【修改依据】")
# 非标准字段：观测到 drafting 手搓批注时用这些替代标准字段，出现即判错。
# 精确匹配这些方括号词，不会误伤标准复合字段（【修改依据】≠【依据】、【风险等级】≠【风险】）。
COMMENT_NONSTANDARD_FIELDS = ("【依据】", "【风险】", "【修改】")
BLACK_COLORS = {"000000", "0A0D12", "AUTO"}
REPORT_STYLE_SIZES = {
    "Normal": "24",
    "Title": "44",
    "Heading1": "36",
    "Heading2": "32",
    "Heading3": "28",
}
TABLE_FONT_SIZE = "21"


def read_docx(path: Path) -> tuple[set[str], object, object | None, str]:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        root = etree.fromstring(archive.read("word/document.xml"))
        styles = (
            etree.fromstring(archive.read("word/styles.xml"))
            if "word/styles.xml" in names
            else None
        )
    text = "".join(root.xpath(".//w:t/text()", namespaces=NS))
    return names, root, styles, text


def table_widths_of(root) -> list[int]:
    """各表格的栅格总宽（DXA），无栅格记 0。"""
    result = []
    for table in root.xpath(".//w:tbl", namespaces=NS):
        widths = [
            int(value)
            for value in table.xpath("./w:tblGrid/w:gridCol/@w:w", namespaces=NS)
        ]
        result.append(sum(widths) if widths else 0)
    return result


def page_size_of(root) -> tuple[int, int] | None:
    page = root.find(".//w:sectPr/w:pgSz", namespaces=NS)
    if page is None:
        return None
    return (int(page.get(f"{{{W_NS}}}w", "0")), int(page.get(f"{{{W_NS}}}h", "0")))


def source_layout(path: Path | None) -> dict | None:
    """抽取原合同的版式特征，供红线/清洁版做「继承豁免」判定。"""
    if path is None or not Path(path).exists():
        return None
    try:
        _, root, _, _ = read_docx(Path(path))
    except Exception:
        return None
    return {
        "table_widths": {w for w in table_widths_of(root) if w > 9026},
        "page": page_size_of(root),
    }


def common_checks(
    path: Path, errors: list[str], inherited: dict | None = None
) -> tuple[set[str], object, object | None, str]:
    """通用机检。

    `inherited` 传入原合同的版式特征（`source_layout()` 产出）时用于红线/清洁版：
    它们的页面尺寸与表格几何**继承自用户的原合同**，而技能契约要求「修订版保持
    合同外观、不重排版式」。对这类特征判技能不合格，调用方无论怎么改
    report-json / operations 都修不好——真机中原合同 7 个表格均宽 9155–9511 DXA，
    交付因此被永久阻断。

    豁免是**逐项比对**的，不是整体放行：只有确实与原合同一致的超宽表/页面尺寸才
    降级为 warning；技能自己新加的超宽表照样判错。
    """
    try:
        names, root, styles, text = read_docx(path)
    except Exception as exc:
        errors.append(f"{path.name}: invalid DOCX package: {exc}")
        return set(), None, None, ""
    if EMOJI_RE.search(text):
        errors.append(f"{path.name}: contains emoji")

    page = page_size_of(root)
    if page is None:
        errors.append(f"{path.name}: missing page size")
    elif not (11850 <= page[0] <= 11950 and 16750 <= page[1] <= 16900):
        if inherited is not None and page == inherited.get("page"):
            print(f"warning: {path.name}: page is not A4 "
                  "(inherited from source layout, preserved as-is)")
        else:
            errors.append(f"{path.name}: page is not A4")

    inherited_widths = (inherited or {}).get("table_widths") or set()
    for index, total in enumerate(table_widths_of(root), start=1):
        if total > 9026:
            if total in inherited_widths:
                print(f"warning: {path.name}: table {index} exceeds content width "
                      "(inherited from source layout, preserved as-is)")
            else:
                errors.append(f"{path.name}: table {index} exceeds content width")
    return names, root, styles, text


def check_black_heading_styles(styles, label: str, errors: list[str]) -> None:
    if styles is None:
        errors.append(f"{label}: missing styles.xml")
        return
    for style in styles.xpath(".//w:style[@w:type='paragraph']", namespaces=NS):
        style_id = style.get(f"{{{W_NS}}}styleId", "")
        if style_id.lower() != "title" and not style_id.lower().startswith("heading"):
            continue
        colors = style.xpath("./w:rPr/w:color/@w:val", namespaces=NS)
        if not colors or colors[0].upper() not in BLACK_COLORS:
            errors.append(f"{label}: {style_id} is not explicitly black")


def check_report_profile(root, styles, errors: list[str]) -> None:
    """Enforce the executable word-report subset of Output Standard 1.1.0."""
    if root is None or styles is None:
        return
    title_paragraphs = root.xpath(
        ".//w:body/w:p[w:pPr/w:pStyle/@w:val='Title']", namespaces=NS
    )
    if not title_paragraphs:
        errors.append("report: document title does not use semantic Title style")
    normal = styles.xpath(
        ".//w:style[@w:type='paragraph' and @w:styleId='Normal']", namespaces=NS
    )
    if not normal:
        errors.append("report: missing Normal paragraph style")
    else:
        spacing = normal[0].xpath("./w:pPr/w:spacing", namespaces=NS)
        line = spacing[0].get(f"{{{W_NS}}}line", "") if spacing else ""
        rule = spacing[0].get(f"{{{W_NS}}}lineRule", "") if spacing else ""
        if line != "360" or rule != "auto":
            errors.append("report: Normal style is not 1.5 line spacing")
    for style_id, expected_size in REPORT_STYLE_SIZES.items():
        matches = styles.xpath(
            ".//w:style[@w:type='paragraph' and @w:styleId=$style_id]",
            namespaces=NS,
            style_id=style_id,
        )
        if not matches:
            errors.append(f"report: missing {style_id} paragraph style")
            continue
        sizes = matches[0].xpath("./w:rPr/w:sz/@w:val", namespaces=NS)
        if not sizes or sizes[0] != expected_size:
            errors.append(
                f"report: {style_id} must use {int(expected_size) / 2:g} pt"
            )
    section = root.find(".//w:sectPr", namespaces=NS)
    if section is not None:
        page = section.find("w:pgSz", namespaces=NS)
        margins = section.find("w:pgMar", namespaces=NS)
        if page is not None and margins is not None:
            safe_width = (
                int(page.get(f"{{{W_NS}}}w", "0"))
                - int(margins.get(f"{{{W_NS}}}left", "0"))
                - int(margins.get(f"{{{W_NS}}}right", "0"))
                - 113
            )
            for index, table in enumerate(root.xpath(".//w:tbl", namespaces=NS), 1):
                widths = [
                    int(value)
                    for value in table.xpath(
                        "./w:tblGrid/w:gridCol/@w:w", namespaces=NS
                    )
                ]
                if widths and sum(widths) > safe_width:
                    errors.append(
                        f"report: table {index} does not keep the 2mm width safety margin"
                    )
    for index, table in enumerate(root.xpath(".//w:tbl", namespaces=NS), 1):
        first_row = table.xpath("./w:tr[1]", namespaces=NS)
        if not first_row:
            continue
        widths = [
            int(value)
            for value in table.xpath(
                "./w:tblGrid/w:gridCol/@w:w", namespaces=NS
            )
        ]
        headers = [
            normalize("".join(cell.xpath(".//w:t/text()", namespaces=NS)))
            for cell in first_row[0].xpath("./w:tc", namespaces=NS)
        ]
        COMPACT_EXACT = frozenset({
            "等级", "风险等级", "标识", "风险标识", "重要性", "优先级",
            "状态", "处理状态", "审查状态", "是否", "结果", "审查结果",
        })
        COMPACT_MARKERS = frozenset({
            "等级", "标识", "重要性", "优先级", "状态", "是否", "结果",
        })
        kinds = []
        for header in headers:
            compact_header = re.sub(r"[\s：:()\uff08\uff09【】\[\]]+", "", header).lower()
            if re.fullmatch(r"(?:序号|编号|no\.?|id)", compact_header, re.IGNORECASE):
                kinds.append("index")
            elif compact_header in COMPACT_EXACT or (
                len(compact_header) <= 8
                and any(m in compact_header for m in COMPACT_MARKERS)
            ):
                kinds.append("compact")
            else:
                kinds.append("narrative")
        total_width = sum(widths)
        if len(widths) == len(kinds) and "narrative" in kinds and total_width:
            for column, (kind, width) in enumerate(zip(kinds, widths), 1):
                limit = 0.09 if kind == "index" else 0.20
                if kind in {"index", "compact"} and width > round(total_width * limit) + 1:
                    errors.append(
                        f"report: table {index} compact column {column} exceeds {limit:.0%}"
                    )
        for cell in first_row[0].xpath("./w:tc", namespaces=NS):
            fills = cell.xpath("./w:tcPr/w:shd/@w:fill", namespaces=NS)
            if not fills or fills[0].upper() not in {"000000", "0A0D12"}:
                errors.append(f"report: table {index} header is not black-filled")
                break
        for run in table.xpath(".//w:r", namespaces=NS):
            sizes = run.xpath("./w:rPr/w:sz/@w:val", namespaces=NS)
            if not sizes or sizes[0] != TABLE_FONT_SIZE:
                errors.append(
                    f"report: table {index} text must use {int(TABLE_FONT_SIZE) / 2:g} pt"
                )
                break


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def check_report_completeness(root, errors: list[str]) -> None:
    """No chapter may be left as a bare placeholder.

    机械完整性闸门（本次新增）：逐段扫描报告正文，把每个正文段落归属到其最近的
    上级标题（章节）。若某章节的正文只有裸占位（「无。」「本节不适用。」「/」等）或
    含桩标记（待补充/占位/TODO），即判为该章节未填实。技能契约明确：确不涉及的项
    须写「经核实不涉及：<理由>」——该形式不含桩标记、也不等于裸占位，故不会误伤。

    这是 draft→verify 多轮返工的根因闸门：过去报告章节留空只能等下游核验用一次完整
    往返才暴露，现在在生成侧本地即判 FAIL，逼子代理在本轮补齐、且能定位到具体章节。
    """
    if root is None:
        return
    empty_sections: list[str] = []
    current_heading = "（报告开头）"
    for para in root.xpath(".//w:body/w:p", namespaces=NS):
        styles = para.xpath("./w:pPr/w:pStyle/@w:val", namespaces=NS)
        style_id = styles[0].lower() if styles else ""
        text = normalize("".join(para.xpath(".//w:t/text()", namespaces=NS)))
        if style_id == "title" or style_id.startswith("heading"):
            if text:
                current_heading = text
            continue
        if not text:
            continue
        compact = re.sub(r"[。.\s、，,；;：:]+$", "", text).strip().lower()
        low = text.lower()
        if compact in BARE_PLACEHOLDERS or any(s in low for s in STUB_SUBSTRINGS):
            empty_sections.append(f"「{current_heading}」→「{text[:30]}」")
    # 去重，保留出现顺序
    seen: set[str] = set()
    for item in empty_sections:
        if item in seen:
            continue
        seen.add(item)
        errors.append(
            f"report: 章节 {item} 为裸占位/桩内容——须补实质内容；确不涉及的章节"
            '在报告 JSON 中写 {"empty_reason": "经核实不涉及：<一句理由>"}，'
            "不得把该字段删成空值或空数组（空值会渲染成裸「无。」，反而触发本项）"
        )


def check_redline_comment_template(redline_path: Path, errors: list[str]) -> None:
    """红线批注必须使用标准模板字段（BLK-01 类缺陷的本地闸门）。

    机械可检：过去 drafting 手搓批注、用【依据】/【风险】/【修改】等非标准字段替代
    标准模板，只有下游 verification 才抓到，触发一次完整 draft→verify 往返。此检查把它
    前移到生成侧——逐条读取 comments.xml：①出现非标准字段即判错；②凡带【风险等级】的
    风险批注，必须含【风险编号】【审查立场】【风险类型】【风险说明】【修改依据】全集。
    """
    try:
        with zipfile.ZipFile(redline_path) as archive:
            if "word/comments.xml" not in archive.namelist():
                return  # 缺 comments.xml 由 main() 的 redline 分支另行报错
            comments_root = etree.fromstring(archive.read("word/comments.xml"))
    except Exception:
        return  # 包损坏由 common_checks 报告
    for comment in comments_root.xpath(".//w:comment", namespaces=NS):
        cid = comment.get(f"{{{W_NS}}}id", "?")
        text = "".join(comment.xpath(".//w:t/text()", namespaces=NS))
        used_nonstandard = [f for f in COMMENT_NONSTANDARD_FIELDS if f in text]
        if used_nonstandard:
            errors.append(
                f"redline: 批注#{cid} 使用非标准字段 {'/'.join(used_nonstandard)}"
                "，必须改用标准模板字段" + "".join(COMMENT_REQUIRED_FIELDS)
            )
        if "【风险等级】" in text:
            missing = [f for f in COMMENT_REQUIRED_FIELDS if f not in text]
            if missing:
                errors.append(
                    f"redline: 批注#{cid} 为风险批注但缺必填模板字段 {'/'.join(missing)}"
                )
        # 重复标签检测：同一批注内任一【标签】出现两次即判错（防多操作合并时裸拼接完整模板）
        for label in dict.fromkeys(re.findall(r"【[^】]+】", text)):
            count = text.count(label)
            if count > 1:
                errors.append(
                    f"redline: 批注#{cid} 模板标签 {label} 重复出现 {count} 次"
                    "——同段多操作应按字段归并，不得裸拼接完整模板"
                )


def check_operations_coverage(
    operations_path: Path, red_root, red_text: str, errors: list[str]
) -> None:
    """Every high/medium-risk recommendation must land as a real text edit.

    Replace-type operations are verified by the presence of their new_text in
    the redline body (w:t stream = unchanged + inserted runs). Comment-only
    operations at high/medium risk require an explicit comment_only_reason.
    """
    try:
        operations = json.loads(operations_path.read_text(encoding="utf-8"))[
            "operations"
        ]
    except Exception as exc:
        errors.append(f"operations: cannot load {operations_path.name}: {exc}")
        return
    # insert（物理插入新条款）与 replace 同为真实文本编辑，计入覆盖
    replace_ops = [
        op for op in operations
        if op.get("action") in {"replace", "replace_text", "insert"}
    ]
    if not replace_ops:
        errors.append(
            "operations: no replace/insert operations — redline carries no clause-text edits"
        )
    normalized_red = normalize(red_text)
    high_medium = {"high", "medium", "高", "中"}
    for op in operations:
        target = op.get("target", "?")
        risk = str(op.get("risk", "")).lower()
        action = op.get("action")
        if risk in high_medium and action == "comment" and not op.get(
            "comment_only_reason"
        ):
            errors.append(
                f"operations: {target} ({risk}) is comment-only without "
                "comment_only_reason — recommendation not applied to clause text"
            )
        if action in {"replace", "replace_text", "insert"}:
            new_text = normalize(op.get("new_text", ""))
            if new_text and new_text not in normalized_red:
                errors.append(
                    f"operations: {target} new_text not found in redline body: "
                    f"{new_text[:60]}…"
                )
    if red_root is not None:
        del_count = len(red_root.xpath(".//w:del", namespaces=NS))
        ins_count = len(red_root.xpath(".//w:ins", namespaces=NS))
        if replace_ops and (del_count + ins_count) < len(replace_ops):
            errors.append(
                f"operations: {len(replace_ops)} replace ops but only "
                f"{ins_count} w:ins / {del_count} w:del in redline"
            )


def check_review_subject(intake: Path | None, contract: Path | None,
                         errors: list[str]) -> None:
    """审查对象一致性：交付所依据的合同必须就是准备阶段抽取的那一份。

    真机诊断 rpt_20260806T065933Z 中，模型拿不到原文件路径，改把读到的正文
    重打成一份**节选**当审查对象，报告却按整份合同口径出具。此处以 intake 记录的
    sha256 为准做机检，堵住「用节选冒充全文」。两个参数缺一则跳过（向后兼容）。
    """
    if intake is None or contract is None:
        return
    if not intake.exists():
        errors.append(f"review subject: intake bundle not found: {intake}")
        return
    if not contract.exists():
        errors.append(f"review subject: contract not found: {contract}")
        return
    try:
        bundle = json.loads(intake.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append(f"review subject: intake bundle unreadable: {exc}")
        return
    expected = bundle.get("sourceSha256")
    if not expected:
        errors.append(
            "review subject: intake bundle 缺少 sourceSha256，无法核对审查对象；"
            "请用当前版本的 review_intake.py 重新生成上下文包")
        return
    digest = hashlib.sha256()
    with contract.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != expected:
        errors.append(
            "review subject: 交付所用合同与准备阶段抽取的合同不一致"
            f"（intake sha256={expected[:12]}…，实际={actual[:12]}…）。"
            "禁止用重打的正文或节选替代原文件——请以 review_intake.py "
            "返回的 contractPath 作为审查对象重新构建。")


def main() -> None:
    parser = argparse.ArgumentParser()
    # --redline 允许缺省，仅用于「降级交付」：红线在重试预算内仍生成不出来时，
    # 报告先行交付并显式声明缺件（见 failure_policy / review_build 的 partial 路径）。
    # 正常交付必须两件套齐全，调用方不得为了绕过红线检查而故意省略本参数。
    parser.add_argument("--redline", type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--clean", type=Path)
    parser.add_argument(
        "--operations",
        type=Path,
        help="operations.json used by apply; verifies that high/medium-risk "
        "recommendations landed as real clause-text edits",
    )
    parser.add_argument(
        "--result-json",
        type=Path,
        help="write machine-readable producer self-check evidence; this is not "
        "trusted platform validation",
    )
    parser.add_argument(
        "--intake",
        type=Path,
        help="review_intake.py 产出的上下文包；用于核对交付所依据的合同"
        "与准备阶段实际抽取的合同是同一份文件",
    )
    parser.add_argument(
        "--contract",
        type=Path,
        help="本次构建实际使用的合同文件。两个用途：与 --intake 配合做审查对象"
        "一致性核对；以及为红线/清洁版提供「原合同版式特征」，使继承自原件的"
        "超宽表与非 A4 页面降级为 warning（技能自己新增的超宽表仍判错）",
    )
    args = parser.parse_args()
    errors: list[str] = []

    check_review_subject(args.intake, args.contract, errors)

    # 原合同版式特征：红线/清洁版继承自它的超宽表与页面尺寸只 warning，不判错
    inherited = source_layout(args.contract)

    if args.redline is None:
        # 降级交付：跳过全部红线检查，并在证据中留痕（不得静默当作通过）
        red_names, red_root, red_text = set(), None, ""
    else:
        red_names, red_root, _, red_text = common_checks(
            args.redline, errors, inherited)
    if red_root is not None:
        if not red_root.xpath(".//w:ins", namespaces=NS):
            errors.append("redline: missing w:ins")
        if not red_root.xpath(".//w:del", namespaces=NS):
            errors.append("redline: missing w:del")
        if "word/comments.xml" not in red_names:
            errors.append("redline: missing comments.xml")
        if "修订说明汇总" not in red_text:
            errors.append("redline: missing revision summary")
        if not any(tag in red_text for tag in ("[用规]", "[要点]", "[法规]", "[惯例]")):
            errors.append("redline: missing basis label")
        if DISCLAIMER_TEXT in red_text:
            errors.append("redline: contains report disclaimer")

    if red_root is not None:
        check_redline_comment_template(args.redline, errors)

    # operations 覆盖率检查依赖红线实体，降级交付时无从校验
    if args.operations and args.redline is not None:
        check_operations_coverage(args.operations, red_root, red_text, errors)

    clean_names, clean_root, _, clean_text = (
        common_checks(args.clean, errors, inherited)
        if args.clean
        else (set(), None, None, "")
    )
    if clean_root is not None:
        if clean_root.xpath(
            ".//w:ins | .//w:del | .//w:commentRangeStart | "
            ".//w:commentRangeEnd | .//w:commentReference",
            namespaces=NS,
        ):
            errors.append("clean: revisions or comment markers remain")
        if "word/comments.xml" in clean_names:
            errors.append("clean: comments.xml remains")
        if DISCLAIMER_TEXT in clean_text:
            errors.append("clean: contains report disclaimer")

    _, report_root, report_styles, report_text = common_checks(args.report, errors)
    if report_root is not None and DISCLAIMER_TEXT not in report_text[:500]:
        errors.append("report: disclaimer missing from opening text")
    if report_root is not None:
        check_black_heading_styles(report_styles, "report", errors)
        check_report_profile(report_root, report_styles, errors)
        check_report_completeness(report_root, errors)

    artifacts = [(args.report, "review_report")]
    if args.redline is not None:
        artifacts.append((args.redline, "redline"))
    if args.clean:
        artifacts.append((args.clean, "clean_contract"))
    evidence = build_review_evidence(
        producer_skill_id="fadada-professional-contract-review",
        artifacts=artifacts,
        errors=errors,
    )
    if args.result_json:
        write_review_evidence(args.result_json, evidence)

    if errors:
        raise SystemExit("\n".join(errors))
    if args.redline is None:
        print("review output validation passed (report only, redline absent)")
    else:
        print("review output validation passed")


if __name__ == "__main__":
    main()
