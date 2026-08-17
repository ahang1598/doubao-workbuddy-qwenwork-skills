#!/usr/bin/env python3
"""lawd-evidence-list-generator 证据清单交付门禁（防缺列 / 防空证明对象 / 防页码断档 / 防模板空壳）。

用法
----
    python3 scripts/validate_evidence_list.py --file 证据清单.md            # 主路径：先出 Markdown 过门禁
    python3 scripts/validate_evidence_list.py --file 证据清单.docx           # 复核路径：对最终 Word 成稿复核
    python3 scripts/validate_evidence_list.py --file 证据清单.md --evidence-count 6   # 加防漏项核对
    python3 scripts/validate_evidence_list.py --file 证据清单.md --original-pages     # 单份材料/沿用原始页码

支持格式：.md / .markdown / .txt / .docx。
（--file 亦可写作 --doc / --docx / --md，等价，便于旧命令兼容。）
.docx 用标准库 zipfile + xml.etree 直接解析 word/document.xml（不依赖 python-docx），
按文档顺序读取段落与**表格单元格文字**——证据清单主体就是表格，读不到表格等于没校验。

检查项（判据口径锚定 SKILL.md）
------------------------------
1. 必备列齐备（SKILL.md「标准证据清单表格」五列）：序号 / 证据名称 / 页码 / 原-复印件 /
   证明对象。表头别名均认（如「原件/复印件」「原件或复印件」「证明目的」「待证事实」）；
   多出的列（来源、证据类型、份数、备注等）一律不拦，只提示。
2. 证明对象非空且非占位符。证明对象是证据清单的灵魂，空着等于没做，因此
   `-` `—` `待补充` `待确认` `XX` `略` `N/A` 之类一律拦截；正文过短（去空白后 < 6 字）
   也按空壳拦。**注意**：这里不强制出现「证明」二字，措辞如「用以佐证……」只提示不拦，
   避免把合规写法误判为缺项。
3. 页码列逐行必填 + 页码连续性（SKILL.md「页码重排规则」）：
   - **逐行必填（P0⑧）**：每一行页码必须可解析（数字 / 数字-数字）或为 SKILL.md
     允许的「待确认/待核实」缺信息标注；空单元格与「-」「—」「略」「?」等占位符
     一律拦截——整列留空/画杠等于没标页码，禁止以此绕过页码校验。
   - 连续性：≥2 份证据时，第 1 份须从第 1 页开始，第 N 份起始页 = 第 N-1 份结束页 + 1。
   - 用户未提供页码时 SKILL.md 允许写「待确认/待核实」，这类标注只提示补充，不按断档拦；
   - 单份材料（仅 1 行数据）沿用原始页码，天然不做重排校验；
   - 多份材料确需沿用原始卷宗页码时，加 `--original-pages`，此时只拦「倒序/重叠」，
     不拦「不从 1 开始」与「不紧接」。
4. 序号：从 1 开始连续、不重复、不跳号（SKILL.md「序号：从 1 开始的连续编号」）。
5. 原/复印件：不得为空（SKILL.md 允许「复印件（待核实）」，故该写法不拦）。取值既非
   原件也非复印件时只提示，不拦——避免「原件（已核对）」等合规变体被误杀。
6. 表格下方落款（SKILL.md「表格下方信息」）：标题含「证据清单」+「提交人（代理律师）」行
   +「提交日期」行。**落款位置（P0⑨）**：落款必须是表格之外（表格下方、文档末尾）的
   结构化落款，表格单元格内的「日期：…」「提交人」等文字不得计入落款；无表格外落款 → 拦。
   **防误拦**：SKILL.md 明确允许提交人留空白下划线供手写，故
   「提交人（代理律师）：_______」判为齐备；但提交日期若仍是模板占位
   `YYYY年MM月DD日` / `年 月 日`，则按模板空壳拦截。提供者标识（原告/被告/第三人提供）
   缺失时只提示（SKILL.md 异常处理允许通用标题「证据清单」）。
   `:279` 未把「份数」列为落款项，故本门禁不查份数，只在提示区提醒备份份数。
7. 空壳拦截：有表头无数据行；或全部数据行为占位符；或全部证明对象为占位符。
8. 防漏项（可选）：给出 `--evidence-count N` 时，核对清单行数 == N（SKILL.md
   「用户提供多少份证据材料，就提取并列出多少项证据」）。不传则只提示不校验。

退出码：0=通过；1=拦截；2=输入错误。
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# ------------------------------------------------------------------ 常量 / 正则

TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".text"}

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

MIN_PROOF_LEN = 6  # 一条“有实质内容的证明对象”的最少字数（去空白与编号后）

# 占位符 / 空壳标记（整格等于其中之一，或去掉标点后等于其中之一时判为占位）
PLACEHOLDER_TOKENS = {
    "", "-", "--", "—", "——", "–", "/", "\\", "、", "。", "无", "空", "略",
    "暂无", "未填", "未填写", "未提供", "未知", "不详", "待补充", "待填写", "待完善",
    "待定", "待核实", "待确认", "待补", "省略", "同上", "略述",
    "xx", "xxx", "xxxx", "××", "×××", "x", "n/a", "na", "tbd", "todo",
    "???", "?", "占位", "示例", "样例", "待补充内容",
}
PLACEHOLDER_PATTERN = re.compile(
    r"^(?:待[补填核确][充写实认][内容]?|[xX×]{1,6}|[?？]{1,6}|[-–—_]{1,8}|"
    r"（?待[^）]{0,6}）?|请填写[^。]{0,10}|此处填写[^。]{0,10})$"
)

# 页码占位（SKILL.md 允许“待确认/待核实”，只提示不拦）
PAGE_PENDING_RE = re.compile(r"待\s*(?:确认|核实|补充|定|填)")

# 页码区间：1-3 / 1–3 / 1~3 / 第1至3页 / P1-3 / 单页 5
PAGE_RANGE_RE = re.compile(r"(\d{1,5})\s*(?:[-–—~～]|至|to|TO)\s*(\d{1,5})")
PAGE_SINGLE_RE = re.compile(r"(?<![\d-])(\d{1,5})(?![\d\s]*[-–—~～至])")

# 模板日期占位
DATE_TEMPLATE_RE = re.compile(
    r"(?:YYYY|yyyy|XXXX|××××)\s*年|^\s*年\s*月\s*日\s*$|_{2,}\s*年|年\s*_{2,}\s*月"
)
DATE_REAL_RE = re.compile(r"(\d{4})\s*[年./-]\s*(\d{1,2})\s*[月./-]\s*(\d{1,2})\s*日?")

FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")

# 表头列别名（按语义匹配，命中即算该列）
COLUMN_ALIASES: Dict[str, Tuple[str, ...]] = {
    "序号": ("序号", "编号", "证据序号", "序列", "No", "NO", "no"),
    "证据名称": ("证据名称", "证据名", "名称", "证据内容", "材料名称", "证据材料"),
    "页码": ("页码", "页次", "页码范围", "证据页码", "所在页码", "页号"),
    "原/复印件": ("原/复印件", "原复印件", "原件/复印件", "原件复印件", "原件或复印件",
               "原件、复印件", "复印件/原件", "原件与复印件", "件别", "原件情况"),
    "证明对象": ("证明对象", "证明目的", "证明内容", "证明事项", "待证事实", "证明的事实",
              "证明事实"),
}
REQUIRED_COLUMNS = ("序号", "证据名称", "页码", "原/复印件", "证明对象")

COPY_TYPE_RE = re.compile(r"原件|复印件|复制件|影印件|扫描件|电子件|原物|原始载体")

PROVIDER_RE = re.compile(r"(原告|被告|第三人|上诉人|被上诉人|申请人|被申请人|反诉[原被]告)"
                         r"\s*(?:方)?\s*提供")

SUBMITTER_RE = re.compile(r"提交人|举证人|提供人|具状人|提交单位")
SUBMIT_DATE_RE = re.compile(r"提交日期|提交时间|举证日期|出具日期|日\s*期")


class InputError(Exception):
    """输入层错误，退出码 2。"""


# ------------------------------------------------------------------ 小工具


def norm(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def normalize_header(text: str) -> str:
    """表头归一：去空白、去分隔与装饰符号，便于别名匹配。"""
    s = norm(text)
    s = s.replace("**", "").replace("*", "")
    s = re.sub(r"[（）()\[\]【】<>《》:：,，.。、\-—/\\|]", "", s)
    return s


def strip_cell(text: str) -> str:
    """单元格文本清洗：去 markdown 强调、去 <br>、统一空白。"""
    s = (text or "").replace("<br/>", "\n").replace("<br>", "\n").replace("<br />", "\n")
    s = s.replace("**", "").replace("__", "")
    s = s.translate(FULLWIDTH_DIGITS)
    s = re.sub(r"[ \t\u3000]+", " ", s)
    return s.strip()


def is_placeholder(text: str) -> bool:
    s = strip_cell(text)
    key = norm(s).lower()
    if key in PLACEHOLDER_TOKENS:
        return True
    return bool(PLACEHOLDER_PATTERN.match(norm(s)))


def proof_body(text: str) -> str:
    """去掉证明对象里的分条编号（1. / （一） / 1、），留下实质文字用于字数判断。"""
    parts = []
    for line in strip_cell(text).splitlines():
        line = re.sub(r"^\s*(?:[（(]\s*[0-9一二三四五六七八九十]{1,3}\s*[)）]|"
                      r"[0-9]{1,3}\s*[.、)）]|[一二三四五六七八九十]{1,3}\s*[、.])\s*", "", line)
        parts.append(line)
    return norm(" ".join(parts))


def count_proof_items(text: str) -> int:
    body = strip_cell(text)
    marks = re.findall(r"(?:^|\n|\s)(?:[（(]\s*[0-9一二三四五六七八九十]{1,3}\s*[)）]|"
                       r"[0-9]{1,3}\s*[.、)）])", body)
    return max(1, len(marks))


def is_table_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.count("|") >= 3


def is_separator_row(line: str) -> bool:
    return bool(re.fullmatch(r"[|\s:：\-—–]+", line.strip())) and "|" in line


def is_table_line(line: str) -> bool:
    """行是否属于表格渲染行（md/docx 统一渲染为 |…| 形式，含单列表格）。

    用于「落款必须在表格之外」判据：docx 单单元格行渲染为「| 文字 |」，
    is_table_row 要求 >=3 个竖线会漏判，这里放宽为首尾竖线即视为表格行。
    """
    s = line.strip()
    return (s.startswith("|") and s.endswith("|")) or is_table_row(s)


def split_md_row(line: str) -> List[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [strip_cell(cell) for cell in s.split("|")]


# ------------------------------------------------------------------ 文档读取


def _docx_cell_text(cell: ET.Element) -> str:
    """单元格内所有段落文字，段落之间用换行连接（保留分条结构）。"""
    lines: List[str] = []
    for para in cell.iter(W_NS + "p"):
        text = "".join(node.text or "" for node in para.iter(W_NS + "t"))
        # 手动换行 <w:br/> 视为分隔
        if text.strip():
            lines.append(text.strip())
    return "\n".join(lines)


def _docx_row_cells(row: ET.Element) -> List[str]:
    return [_docx_cell_text(tc) for tc in row.findall(W_NS + "tc")]


def load_docx(path: Path) -> List[str]:
    """用 zipfile 直接解析 docx，按文档顺序输出行；表格行渲染为 markdown 形式。"""
    if not zipfile.is_zipfile(path):
        raise InputError("文件不是合法 DOCX ZIP 容器（.doc 请先转存为 .docx）")
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
            if "word/document.xml" not in names:
                raise InputError("DOCX 内缺少 word/document.xml，文件可能损坏")
            payloads = [zf.read("word/document.xml")]
            for name in sorted(names):
                if re.fullmatch(r"word/(?:header|footer)\d*\.xml", name):
                    payloads.append(zf.read(name))
    except zipfile.BadZipFile as exc:
        raise InputError(f"DOCX 解压失败：{exc}")

    lines: List[str] = []
    for payload in payloads:
        try:
            root = ET.fromstring(payload)
        except ET.ParseError as exc:
            raise InputError(f"DOCX XML 解析失败：{exc}")
        body = root.find(W_NS + "body")
        _walk_docx_container(body if body is not None else root, lines)
    if not lines:
        raise InputError("DOCX 中未读到任何文字（段落与表格均为空）")
    return lines


def _walk_docx_container(container: ET.Element, lines: List[str]) -> None:
    """按文档顺序遍历正文层：w:p 出段落、w:tbl 出表格行，容器元素（w:sdt 等）递归下钻。

    不用 iter() 全量遍历，避免把表格单元格内的段落再当正文段落输出一遍。
    """
    for child in container:
        if child.tag == W_NS + "tbl":
            for row in child.findall(W_NS + "tr"):
                cells = _docx_row_cells(row)
                if not any(c.strip() for c in cells):
                    continue
                flat = [re.sub(r"\s*\n\s*", "<br>", c).strip() for c in cells]
                lines.append("| " + " | ".join(flat) + " |")
        elif child.tag == W_NS + "p":
            text = "".join(node.text or "" for node in child.iter(W_NS + "t")).strip()
            if text:
                lines.append(text)
        elif child.tag in (W_NS + "sdt", W_NS + "sdtContent", W_NS + "txbxContent"):
            _walk_docx_container(child, lines)
        elif child.tag == W_NS + "sectPr":
            continue
        else:
            # 其他包装元素（如 mc:AlternateContent、w:customXml）继续下钻找 p/tbl
            if any(sub.tag in (W_NS + "p", W_NS + "tbl") for sub in child.iter()):
                _walk_docx_container(child, lines)


def load_document(path: Path) -> List[str]:
    suffix = path.suffix.lower()
    if suffix not in TEXT_SUFFIXES and suffix != ".docx":
        raise InputError(
            f"不支持的文件类型：{path.name}"
            "（支持 .md/.markdown/.txt/.docx；.doc 请先转 .docx）"
        )
    if not path.exists():
        raise InputError(f"文件不存在：{path}")
    if path.stat().st_size == 0:
        raise InputError("文件为空")
    if suffix == ".docx":
        return load_docx(path)
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            content = path.read_text(encoding="gbk")
        except Exception as exc:
            raise InputError(f"无法以 UTF-8/GBK 解码文本文件：{exc}")
    if not content.strip():
        raise InputError("文件内容为空")
    return content.splitlines()


# ------------------------------------------------------------------ 表格定位


def match_column(header_cell: str) -> Optional[str]:
    key = normalize_header(header_cell)
    if not key:
        return None
    if key in ("页数", "总页数"):        # 页数≠页码，别当页码列认
        return None
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            akey = normalize_header(alias)
            if key == akey:
                return canonical
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            akey = normalize_header(alias)
            if len(akey) >= 2 and akey in key:
                return canonical
    return None


def map_header(cells: Sequence[str]) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    for idx, cell in enumerate(cells):
        canonical = match_column(cell)
        if canonical and canonical not in mapping:
            mapping[canonical] = idx
    return mapping


def locate_table(lines: Sequence[str]) -> Tuple[Optional[int], Dict[str, int],
                                                List[Tuple[int, List[str]]],
                                                List[str]]:
    """定位证据清单表格。

    返回 (表头行号, 列映射, [(行号, 单元格列表)], 表头原始单元格)。
    多个表格时取“必备列命中最多”的那个，命中数相同取数据行更多的那个。
    """
    candidates: List[Tuple[int, Dict[str, int], List[Tuple[int, List[str]]], List[str]]] = []
    idx = 0
    total = len(lines)
    while idx < total:
        line = lines[idx]
        if is_table_row(line) and not is_separator_row(line):
            header_cells = split_md_row(line)
            mapping = map_header(header_cells)
            rows: List[Tuple[int, List[str]]] = []
            cursor = idx + 1
            while cursor < total and is_table_row(lines[cursor]):
                if not is_separator_row(lines[cursor]):
                    rows.append((cursor + 1, split_md_row(lines[cursor])))
                cursor += 1
            if mapping:
                candidates.append((idx + 1, mapping, rows, header_cells))
            idx = cursor
            continue
        idx += 1
    if not candidates:
        return None, {}, [], []
    candidates.sort(
        key=lambda item: (
            len([c for c in REQUIRED_COLUMNS if c in item[1]]),
            len(item[2]),
        ),
        reverse=True,
    )
    return candidates[0]


# ------------------------------------------------------------------ 页码解析


def parse_pages(text: str) -> Optional[Tuple[int, int, bool]]:
    """解析页码单元格 → (起始页, 结束页, 是否多段)。无法解析返回 None。"""
    s = strip_cell(text)
    if not s:
        return None
    segments: List[Tuple[int, int]] = []
    consumed = s
    for m in PAGE_RANGE_RE.finditer(s):
        segments.append((int(m.group(1)), int(m.group(2))))
        consumed = consumed.replace(m.group(0), " ")
    for m in PAGE_SINGLE_RE.finditer(consumed):
        num = int(m.group(1))
        segments.append((num, num))
    if not segments:
        return None
    segments.sort()
    return segments[0][0], segments[-1][1], len(segments) > 1


# ------------------------------------------------------------------ 主流程


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="证据清单交付门禁：必备列齐备 / 证明对象非空非占位 / 页码连续性与重排"
                    "规则 / 序号连续 / 落款齐备 / 防模板空壳。支持 md/txt/docx"
                    "（docx 用 zipfile 直接解析，含表格文字，无需 python-docx）。",
        epilog=(
            "判据口径见 SKILL.md：「标准证据清单表格」五列、「页码重排规则」、"
            "「表格下方信息」。防误拦说明：页码写「待确认/待核实」按 SKILL.md 允许的"
            "缺信息标注处理，只提示不拦；但页码空单元格与「-」「—」等占位符一律拦截；"
            "落款必须位于表格之外（表格下方），表格单元格内的日期/提交人文字不计入落款；"
            "提交人保留空白下划线视为齐备；「原件（已核对）」等变体不拦；"
            "「份数」不属 SKILL.md 落款必备项，不查。"
            "退出码：0=通过，1=拦截，2=输入错误。"
        ),
    )
    parser.add_argument("--file", "--doc", "--docx", "--md", dest="path",
                        required=True, type=Path,
                        help="证据清单文件路径（.md/.markdown/.txt/.docx）")
    parser.add_argument("--evidence-count", type=int, default=None,
                        help="用户提供的证据材料份数，用于防漏项核对（清单行数须等于该值）；"
                             "不传则跳过该项并提示")
    parser.add_argument("--original-pages", action="store_true",
                        help="页码沿用原始材料页码（单份材料或法院要求保留卷宗页码）："
                             "跳过“从第1页起 + 紧接上一份”的重排校验，仅拦倒序/重叠")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.evidence_count is not None and args.evidence_count < 1:
        print("输入错误：--evidence-count 必须 >= 1", file=sys.stderr)
        return 2

    try:
        lines = load_document(args.path)
    except InputError as exc:
        print(f"输入错误：{exc}", file=sys.stderr)
        return 2

    body = "\n".join(lines)
    checks: List[str] = []
    warns: List[str] = []
    errors: List[str] = []

    header_lineno, mapping, raw_rows, header_cells = locate_table(lines)

    # --- ① 必备列齐备 ---
    if header_lineno is None:
        errors.append("表格结构：全文未找到证据清单表格（未识别到任何含表头的表格行）")
        mapping, raw_rows = {}, []
    else:
        missing = [c for c in REQUIRED_COLUMNS if c not in mapping]
        if missing:
            errors.append(
                "必备列缺失：缺 %s（表头第 %d 行实际为：%s）"
                % ("、".join(missing), header_lineno, " / ".join(header_cells) or "空")
            )
        else:
            checks.append("必备列齐备：序号 / 证据名称 / 页码 / 原-复印件 / 证明对象"
                          "（表头第 %d 行）" % header_lineno)
        extra = [header_cells[i] for i in range(len(header_cells))
                 if i not in set(mapping.values()) and header_cells[i].strip()]
        if extra:
            warns.append("表头存在额外列（不影响门禁）：%s" % "、".join(extra))

    # --- 数据行提取（过滤掉整行占位/整行空的伪行）---
    def cell_of(cells: Sequence[str], col: str) -> str:
        pos = mapping.get(col)
        if pos is None or pos >= len(cells):
            return ""
        return cells[pos]

    data_rows: List[Tuple[int, List[str]]] = []
    empty_rows: List[int] = []
    for lineno, cells in raw_rows:
        if not any(strip_cell(c) for c in cells):
            continue
        meaningful = [cell_of(cells, c) for c in ("证据名称", "页码", "证明对象")]
        if all(is_placeholder(c) for c in meaningful):
            empty_rows.append(lineno)
            continue
        data_rows.append((lineno, cells))

    # --- ② 空壳拦截 ---
    if header_lineno is not None and not data_rows:
        if empty_rows:
            errors.append("空壳拦截：表格 %d 行数据全部为占位符（行号 %s），无任何实质证据"
                          % (len(empty_rows), "、".join(str(n) for n in empty_rows)))
        else:
            errors.append("空壳拦截：只有表头（第 %d 行）没有任何数据行，属模板空壳"
                          % header_lineno)
    elif empty_rows:
        errors.append("占位数据行：第 %s 行的证据名称/页码/证明对象全为占位符，须删除或补实"
                      % "、".join(str(n) for n in empty_rows))

    if data_rows:
        checks.append("清单规模：识别到 %d 份证据（数据行第 %d-%d 行）"
                      % (len(data_rows), data_rows[0][0], data_rows[-1][0]))

    # --- ③ 逐份证据字段校验 ---
    def label(lineno: int, cells: Sequence[str]) -> str:
        seq = strip_cell(cell_of(cells, "序号")) or "?"
        name = strip_cell(cell_of(cells, "证据名称")).replace("\n", " ")
        short = (name[:18] + "…") if len(name) > 18 else (name or "（名称为空）")
        return "第 %d 行（序号 %s：%s）" % (lineno, seq, short)

    proof_ok = 0
    for lineno, cells in data_rows:
        name = cell_of(cells, "证据名称")
        if is_placeholder(name):
            errors.append("%s 证据名称为空或占位符" % label(lineno, cells))
        elif len(norm(name)) > 60:
            warns.append("%s 证据名称 %d 字，超出 SKILL.md 建议的 50 字上限"
                         % (label(lineno, cells), len(norm(name))))

        proof = cell_of(cells, "证明对象")
        if is_placeholder(proof):
            errors.append("%s 证明对象为空或占位符（实际内容：「%s」）——证明对象是证据"
                          "清单的灵魂，禁止留空/占位交付"
                          % (label(lineno, cells), strip_cell(proof) or "空"))
        elif len(proof_body(proof)) < MIN_PROOF_LEN:
            errors.append("%s 证明对象过短（去编号后仅 %d 字：「%s」），不构成实质证明对象"
                          % (label(lineno, cells), len(proof_body(proof)),
                             strip_cell(proof)))
        else:
            proof_ok += 1
            if "证明" not in norm(proof):
                warns.append("%s 证明对象未使用「证明……的事实」标准表述，建议按 SKILL.md"
                             "统一措辞（不拦截）" % label(lineno, cells))

        copy_type = cell_of(cells, "原/复印件")
        if is_placeholder(copy_type):
            errors.append("%s 原/复印件未标注（SKILL.md：未核实时应写「复印件（待核实）」）"
                          % label(lineno, cells))
        elif not COPY_TYPE_RE.search(norm(copy_type)):
            warns.append("%s 原/复印件取值为「%s」，非「原件/复印件」常规写法，请人工确认"
                         % (label(lineno, cells), strip_cell(copy_type)))

    if data_rows and proof_ok == len(data_rows):
        checks.append("证明对象：%d 份证据全部有实质证明对象（非空、非占位、达标字数）"
                      % proof_ok)

    # --- ④ 序号连续性 ---
    seq_values: List[Tuple[int, Optional[int], str]] = []
    for lineno, cells in data_rows:
        raw = strip_cell(cell_of(cells, "序号")).translate(FULLWIDTH_DIGITS)
        m = re.search(r"\d+", raw)
        seq_values.append((lineno, int(m.group(0)) if m else None, raw))
    bad_seq = [(ln, raw) for ln, val, raw in seq_values if val is None]
    for ln, raw in bad_seq:
        errors.append("第 %d 行 序号无法识别为数字（实际：「%s」）" % (ln, raw or "空"))
    nums = [(ln, val) for ln, val, _ in seq_values if val is not None]
    seq_bad = False
    for pos, (ln, val) in enumerate(nums, start=1):
        if val != pos:
            errors.append("序号不连续：第 %d 行应为 %d，实际为 %d（SKILL.md 要求从 1 开始"
                          "连续编号）" % (ln, pos, val))
            seq_bad = True
    if nums and not seq_bad and not bad_seq:
        checks.append("序号连续：1-%d 无跳号无重复" % len(nums))

    # --- ⑤ 页码逐行必填 + 连续性与重排规则 ---
    parsed: List[Tuple[int, List[str], Optional[Tuple[int, int, bool]], str]] = []
    pending_pages: List[int] = []            # SKILL.md 允许的「待确认/待核实」缺信息标注（只提示）
    missing_pages: List[Tuple[int, str]] = []  # 空单元格 / 「-」「—」等占位符（拦截）
    for lineno, cells in data_rows:
        raw = strip_cell(cell_of(cells, "页码"))
        if PAGE_PENDING_RE.search(norm(raw)):
            pending_pages.append(lineno)
            parsed.append((lineno, cells, None, raw))
            continue
        if is_placeholder(raw):
            missing_pages.append((lineno, raw))
            parsed.append((lineno, cells, None, raw))
            continue
        info = parse_pages(raw)
        if info is None:
            errors.append("%s 页码无法解析（实际：「%s」），须写为「1-3」或单页「5」"
                          % (label(lineno, cells), raw or "空"))
        parsed.append((lineno, cells, info, raw))

    if missing_pages:
        errors.append("页码缺失/占位：第 %s 行页码为空或为「-」「—」等占位符（实际："
                      "「%s」）；SKILL.md 要求逐份标注页码范围（如「1-3」「5」），确实"
                      "没有页码时应写「待确认」而非留空/画杠——整列留空或画杠等于未标页码"
                      % ("、".join(str(n) for n, _ in missing_pages),
                         " / ".join(r or "空" for _, r in missing_pages)))

    if pending_pages:
        warns.append("页码待补：第 %s 行页码为「待确认/待核实」类标注，SKILL.md 允许该"
                     "缺信息写法，交付前请提示用户补齐后重跑本门禁"
                     % "、".join(str(n) for n in pending_pages))

    ranged = [(ln, cells, info, raw) for ln, cells, info, raw in parsed if info]
    page_errors_before = len(errors)
    for ln, cells, info, raw in ranged:
        start, end, multi = info
        if start > end:
            errors.append("%s 页码区间倒序（%s）" % (label(ln, cells), raw))
        if multi:
            warns.append("%s 页码含多个区间（%s），已按最小起始页与最大结束页参与连续性"
                         "校验" % (label(ln, cells), raw))

    if len(ranged) >= 2 and not args.original_pages:
        first_ln, first_cells, first_info, first_raw = ranged[0]
        if first_info[0] != 1:
            errors.append("页码重排违规：%s 起始页为 %d，SKILL.md「页码重排规则」要求"
                          "第 1 份证据从第 1 页开始（如确需沿用原始卷宗页码，"
                          "请加 --original-pages 复跑）"
                          % (label(first_ln, first_cells), first_info[0]))
        prev_end = first_info[1]
        prev_label = label(first_ln, first_cells)
        for ln, cells, info, raw in ranged[1:]:
            expect = prev_end + 1
            if info[0] != expect:
                gap = "断档" if info[0] > expect else "重叠"
                errors.append("页码%s：%s 起始页应为 %d（紧接%s的第 %d 页），实际为 %d"
                              "（页码「%s」）"
                              % (gap, label(ln, cells), expect, prev_label,
                                 prev_end, info[0], raw))
            prev_end = max(prev_end, info[1])
            prev_label = label(ln, cells)
    elif len(ranged) >= 2 and args.original_pages:
        prev_end = ranged[0][2][1]
        for ln, cells, info, raw in ranged[1:]:
            if info[0] <= prev_end:
                errors.append("页码重叠/倒序：%s 起始页 %d 未晚于上一份结束页 %d"
                              "（--original-pages 模式仅放行“不连续”，不放行重叠）"
                              % (label(ln, cells), info[0], prev_end))
            prev_end = max(prev_end, info[1])

    if ranged and len(errors) == page_errors_before:
        if len(ranged) < 2:
            checks.append("页码：单份材料（%d 份可解析页码），按 SKILL.md 沿用原始页码，"
                          "不做重排校验" % len(ranged))
        elif args.original_pages:
            checks.append("页码：%d 份沿用原始页码（--original-pages），无重叠无倒序"
                          % len(ranged))
        else:
            checks.append("页码重排合规：%d 份证据自第 1 页起连续无断层（%s → %s）"
                          % (len(ranged), ranged[0][3], ranged[-1][3]))

    # --- ⑥ 标题与落款 ---
    if re.search(r"证\s*据\s*清\s*单", body):
        checks.append("标题：全文含「证据清单」标题")
    else:
        errors.append("标题缺失：全文未找到「证据清单」标题")

    if PROVIDER_RE.search(norm(body)):
        checks.append("提供者标识：标题/正文含「%s」"
                      % PROVIDER_RE.search(norm(body)).group(0))
    else:
        warns.append("未见「XX提供」提供者标识；SKILL.md 异常处理允许无法确定时用通用"
                     "标题「证据清单」，此处仅提示")

    # 落款必须是表格之外（表格下方、文档末尾）的结构化落款：表格单元格内的
    # 「日期：…」「提交人」等文字不得计入落款（P0⑨：防止表格内文字冒充落款）。
    table_line_idx = [i for i, ln in enumerate(lines) if is_table_line(ln)]
    last_table_idx = max(table_line_idx) if table_line_idx else -1
    outside_lines = [ln for i, ln in enumerate(lines) if i > last_table_idx and ln.strip()]

    submitter_line = next((ln for ln in outside_lines if SUBMITTER_RE.search(ln)), None)
    if submitter_line:
        checks.append("落款-提交人：表格外找到「%s」（SKILL.md 允许留空白下划线供手写）"
                      % strip_cell(submitter_line)[:40])
    else:
        errors.append("落款缺项：表格外（表格下方/文档末尾）缺「提交人（代理律师）：」行"
                      "（依据 SKILL.md「表格下方信息」；表格单元格内文字不计入落款）")

    date_lines = [ln for ln in outside_lines if SUBMIT_DATE_RE.search(ln)]
    if not date_lines:
        errors.append("落款缺项：表格外（表格下方/文档末尾）缺「提交日期：」行"
                      "（依据 SKILL.md「表格下方信息」；表格单元格内文字不计入落款）")
    else:
        real = next((ln for ln in date_lines if DATE_REAL_RE.search(strip_cell(ln))), None)
        if real:
            m = DATE_REAL_RE.search(strip_cell(real))
            month, day = int(m.group(2)), int(m.group(3))
            if not (1 <= month <= 12 and 1 <= day <= 31):
                errors.append("落款-提交日期非法：「%s」月份或日期越界" % strip_cell(real)[:40])
            else:
                checks.append("落款-提交日期：%s年%s月%s日" % (m.group(1), m.group(2), m.group(3)))
        else:
            errors.append("落款-提交日期为模板占位（实际：「%s」），须填实际提交日期"
                          "（YYYY年MM月DD日）" % strip_cell(date_lines[0])[:40])

    # --- ⑦ 防漏项 ---
    if args.evidence_count is None:
        warns.append("未传 --evidence-count：本次未核对「用户提供多少份就列多少份」"
                     "（SKILL.md 完整性要求），建议按材料份数复跑一次")
    elif len(data_rows) != args.evidence_count:
        errors.append("完整性门禁：清单 %d 份 ≠ 用户材料 %d 份（SKILL.md 禁止自行筛选、"
                      "遗漏或合并证据项）" % (len(data_rows), args.evidence_count))
    else:
        checks.append("完整性：清单 %d 份 = 用户材料 %d 份"
                      % (len(data_rows), args.evidence_count))

    warns.append("提醒：交付前请按「对方当事人数量 + 1 份给法院」准备证据副本份数"
                 "（SKILL.md 阶段六，不属本门禁拦截项）")

    # --- 输出 ---
    print(f"== 证据清单交付门禁：{args.path.name}（通过清单）==")
    for item in checks:
        print(f"- {item}")
    if warns:
        print("== 提示 ==")
        for item in warns:
            print(f"- {item}")
    if errors:
        print("== 拦截清单 ==", file=sys.stderr)
        for item in errors:
            print(f"- {item}", file=sys.stderr)
        print(f"校验不通过：共拦截 {len(errors)} 项，禁止交付", file=sys.stderr)
        return 1
    print("校验通过：%s 必备列齐备；%d 份证据的证明对象均有实质内容；页码与序号合规；"
          "落款齐备" % (args.path.name, len(data_rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
