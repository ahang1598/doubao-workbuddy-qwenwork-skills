#!/usr/bin/env python3
"""lawd-company-info 企业尽调报告交付门禁（防模板当报告 / 防降级态假报告 / 防缺章 /
防空壳与必需维度缺失 / 防供应商回退 / 防形态自证）。

用法
----
    python3 scripts/validate_dd_report.py <报告文件.md>
    python3 scripts/validate_dd_report.py <报告文件.md> --registry-data available|missing
    python3 scripts/validate_dd_report.py <报告文件.docx>          # 对 Word 成稿复核
    python3 scripts/validate_dd_report.py --help

支持格式：.md / .markdown / .txt / .docx（docx 读取依赖 python-docx：pip3 install python-docx）。

输出形态判定（权威口径 SKILL.md §1.5/§1.6/§6.2）
-------------------------------------------------
- 摘要形态：文本含明确降级标记「⚠️ 公开信息摘要」声明（⚠️ + 本摘要 / 公开信息摘要 /
  未经工商数据核验）→ 只按 §1.6「公开信息摘要」规则校验（⚠️ 强制免责声明 + 实质内容 +
  无评级结论 + 无供应商名）。降级判定只认该明确标记，不依据「主要数据来源」行的长短，
  不依据是否提及 MCP。
- 完整报告形态：无摘要声明时，按「工商数据获取状态」声明行判定；未取得 → A 档降级门禁。

拦截判据
--------
1. **模板文件当报告**：文件名含 report-template 或内容含模板占位符/模板注释
   （references/report-template.md 或其副本）→ 拦截「模板文件，非报告」。
2. **降级态假装完整报告**：声明未取得 / 摘要形态下仍输出完整 13 章结构或风险评级结论 → 拦截。
3. **13 个必填章节缺一**（SKILL.md §6.2 口径 13 章；风险评估还须含司法/经营/周边/交叉分析四子块）。
4. **空壳与必需维度缺失**：
   - 全篇无任何章节含实质信息（剔除「数据缺失」等标注后）→ 拦截；
   - 必需维度（企业基本信息/股权结构/主要人员/知识产权/行业资质/风险评估）整体无实质内容
     时输出综合评级 → 拦截（综合评级不放行，须取得数据或改出公开信息摘要）。
5. **供应商名/工具名回退**（匹配前归一化：去 markdown 标记、空白、全半角差异）→ 拦截。
6. **缺失字段留空**：表格留空单元格、未填充模板占位符。
7. **形态不一致**：完整 13 章 ⇄ 头部「主要数据来源」声明连接器数据源（能力语义）；
   WebSearch-only ⇄ 必须走「⚠️ 公开信息摘要」形态；不一致 → 拦截。

退出码：0=通过（可交付）；1=拦截（按清单修复后重跑）；2=输入错误。
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

# ---------------------------------------------------------------- 章节清单

# 13 个必填章节：SKILL.md §6.2「必填章节」12 项 + 「建议章节」中须保留的招投标记录。
# 每章命中任一关键词即视为存在。
REQUIRED_SECTIONS: List[Tuple[str, Tuple[str, ...]]] = [
    ("一、执行摘要", ("执行摘要",)),
    ("二、企业基本信息", ("企业基本信息", "基本信息")),
    ("三、工商变更历史", ("工商变更历史", "变更历史")),
    ("四、股权结构", ("股权结构",)),
    ("五、关联企业图谱", ("关联企业图谱", "关联企业")),
    ("六、主要人员", ("主要人员",)),
    ("七、知识产权", ("知识产权",)),
    ("八、行业资质与许可证", ("行业资质", "资质与许可", "许可证")),
    ("九、风险评估", ("风险评估",)),
    ("十、招投标记录", ("招投标", "中标记录")),
    ("十一、法律评价与建议", ("法律评价", "法律评价与建议")),
    ("十二、待线下核实事项清单", ("待线下核实", "待核实事项")),
    ("十三、免责条款", ("免责条款", "免责声明")),
]

# 综合评级放行的必需维度（P0-2）：任一整体无实质内容 → 综合评级不放行（exit 1）。
# 口径：工商登记（章二）/ 股权结构（章四）/ 主要人员（章六）/ 知识产权（章七）/
# 行业资质（章八）/ 风险评估（章九）。缺章本身由 13 章必填检查拦截。
REQUIRED_DIMENSIONS: Tuple[str, ...] = (
    "二、企业基本信息",
    "四、股权结构",
    "六、主要人员",
    "七、知识产权",
    "八、行业资质与许可证",
    "九、风险评估",
)

# 风险评估章节的四个必备子块（SKILL.md §6.2 必填章节括注）
RISK_SUBBLOCKS: List[Tuple[str, Tuple[str, ...]]] = [
    ("司法风险", ("司法风险", "司法")),
    ("经营风险", ("经营风险", "行政处罚", "经营异常")),
    ("周边风险", ("周边风险", "关联方风险")),
    ("风险交叉分析", ("交叉分析", "风险交叉")),
]

# 降级/摘要形态禁止出现的结论标记
CONCLUSION_MARKERS = (
    "综合风险评级",
    "分维度风险评级",
    "风险评级说明",
    "法律评价与建议",
    "风险交叉分析",
    "建议后续调查重点",
    "专业建议",
)

# ---------------------------------------------------------------- 供应商黑名单
# 【黑名单词定义】以下是全库唯一允许出现供应商名的位置：报告正文出现即拦截（防改造回退哨兵）。
# 匹配前先对行做归一化（去 markdown 标记 / 去空白 / 全半角转换），防「天 眼 查」/「**企查查**」绕过。
VENDOR_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("天眼查", re.compile("天眼查")),
    ("企查查", re.compile("企查查")),
    ("tianyancha", re.compile(r"(?i)(?<![a-z0-9])tianyancha(?![a-z0-9])")),
    ("qichacha", re.compile(r"(?i)(?<![a-z0-9])qichacha(?![a-z0-9])")),
    ("tyc", re.compile(r"(?i)(?<![a-z0-9])tyc(?![a-z0-9])")),
    ("qcc", re.compile(r"(?i)(?<![a-z0-9])qcc(?![a-z0-9])")),
]

# ---------------------------------------------------------------- 模板黑名单（P0-3）
# 模板本身（references/report-template.md 或其副本）必须被显式识别并拦截。
TEMPLATE_NAME_RE = re.compile(r"report[-_ ]?template", re.IGNORECASE)
TEMPLATE_CONTENT_MARKERS = ("模板填写约束", "{actual_sources}", "{企业全称}")

# ---------------------------------------------------------------- 其他常量/正则

STATUS_RE = re.compile(r"工商数据获取状态[^\n]{0,20}?(已取得|未取得)")
MAIN_SOURCE_RE = re.compile(r"主要数据来源[^\n]*")
PUBLIC_SOURCE_RE = re.compile(r"公开网络检索|WebSearch|公开检索|网络检索|公开信息检索")
DIM_FAIL_RE = re.compile(r"该维度数据获取失败|该维度获取失败|未探测到对应能力")
MISSING_MARKER_RE = re.compile(r"数据缺失|该维度数据获取失败|未查询到|未探测到对应能力|无相关记录")
PLACEHOLDER_RE = re.compile(r"\{[^{}\n]{1,40}\}")
UNVERIFIED_RE = re.compile(r"未核验")
CONNECTOR_HINT_RE = re.compile(r"连接器")
WARN_MARK_RE = re.compile(r"⚠")

# 摘要形态唯一认定标记（P0-4/P0-5）：⚠️ + 本摘要 / 公开信息摘要 / 未经工商数据核验。
SUMMARY_MODE_RE = re.compile(r"⚠[^\n。]*?(?:公开信息摘要|本摘要|未经工商数据核验)")

# P0-7 形态一致性：WebSearch-only 自证声明（完整报告头部未声明连接器数据源时兜底判定）
WEBSEARCH_ONLY_SELF_CLAIM_RE = re.compile(
    r"(?:全部|所有|整份|整体)(?:报告)?数据(?:均|都)?已?通过WebSearch(?:取得|获取)"
)

# 章级标题：markdown 二级标题，或「一、xxx」～「十三、xxx」式短标题
CN_SECTION_RE = re.compile(r"^[#\s>*]*[一二三四五六七八九十]{1,3}\s*[、.．]")
MD_H2_RE = re.compile(r"^##(?!#)\s*\S")
MD_ANY_H_RE = re.compile(r"^#{1,6}\s*\S")

TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".text"}
MIN_SECTION_CHARS = 40      # 一个章节「有实质内容」的最低有效字数
MIN_DIM_CHARS = 20          # 必需维度「有实质数据」的最低字数（剔除缺失标注与表头/首列后）
FULL_REPORT_THRESHOLD = 8   # 命中 >= 8 章即视为「在输出完整报告」
MAX_DETAIL = 8              # 同类拦截明细最多打印条数


class InputError(Exception):
    """输入层错误，退出码 2。"""


# ---------------------------------------------------------------- 文档读取


def _docx_lines(path: Path) -> List[str]:
    if not zipfile.is_zipfile(path):
        raise InputError("文件不是合法 DOCX ZIP 容器")
    try:
        from docx import Document
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        from docx.oxml.table import CT_Tbl
        from docx.oxml.text.paragraph import CT_P
    except ImportError:
        raise InputError("当前环境未安装 python-docx，请先执行：pip3 install python-docx")
    try:
        document = Document(str(path))
    except Exception as exc:  # noqa: BLE001
        raise InputError(f"python-docx 无法打开文件：{exc}")

    lines: List[str] = []
    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            para = Paragraph(child, document)
            text = para.text.strip()
            if not text:
                continue
            style = (para.style.name or "") if para.style is not None else ""
            if "heading" in style.lower() and not text.startswith("#"):
                level_match = re.search(r"(\d+)", style)
                level = int(level_match.group(1)) if level_match else 2
                level = max(1, min(level, 6))
                lines.append("#" * level + " " + text)
            else:
                lines.append(text)
        elif isinstance(child, CT_Tbl):
            table = Table(child, document)
            for row in table.rows:
                cells = [re.sub(r"\s*\n\s*", " ", cell.text).strip() for cell in row.cells]
                if not cells:
                    continue
                lines.append("| " + " | ".join(cells) + " |")
    return lines


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
        return _docx_lines(path)
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            content = path.read_text(encoding="gbk")
        except Exception as exc:  # noqa: BLE001
            raise InputError(f"无法以 UTF-8/GBK 解码文本文件：{exc}")
    if not content.strip():
        raise InputError("文件内容为空")
    return content.splitlines()


# ---------------------------------------------------------------- 小工具


def norm(text: str) -> str:
    return re.sub(r"\s+", "", text)


def norm_vendor(text: str) -> str:
    """供应商名匹配前的归一化：全角→半角、去 markdown 标记、去全部空白。

    防「天 眼 查」「**企查查**」「ｔｉａｎｙａｎｃｈａ」等写法绕过哨兵。
    """
    s = "".join(chr(ord(c) - 0xFEE0) if 0xFF01 <= ord(c) <= 0xFF5E else c for c in text)
    s = re.sub(r"[*_`~#>\|]", "", s)
    return re.sub(r"\s+", "", s)


def strip_markup(line: str) -> str:
    s = line.strip()
    s = re.sub(r"^[#>\-*\s|]+", "", s)
    return s.replace("**", "").replace("*", "").rstrip("|").strip()


def is_table_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.count("|") >= 2


def is_separator_row(line: str) -> bool:
    return bool(re.fullmatch(r"[|\s:：\-—–]+", line.strip())) and "|" in line


def table_cells(line: str) -> List[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_comment_line(line: str) -> bool:
    s = line.strip()
    return s.startswith("<!--") or s.endswith("-->") or s.startswith("```")


def is_chapter_heading(line: str) -> bool:
    """章级标题：## 二级标题，或「一、/十三、」式中文序号短标题。"""
    if is_table_row(line):
        return False
    stripped = line.strip()
    if MD_H2_RE.match(stripped):
        return True
    if MD_ANY_H_RE.match(stripped):
        return False  # # / ### 及更深层级不作章级切分
    body = strip_markup(stripped)
    return bool(CN_SECTION_RE.match(stripped) and len(body) <= 40)


def section_spans(lines: Sequence[str]) -> List[Tuple[int, str, int, int]]:
    """返回 [(标题行号, 标题文本, 内容起, 内容止)]（行号从 0 起，内容止为开区间）。"""
    heads = [idx for idx, line in enumerate(lines) if is_chapter_heading(line)]
    spans: List[Tuple[int, str, int, int]] = []
    for pos, idx in enumerate(heads):
        end = heads[pos + 1] if pos + 1 < len(heads) else len(lines)
        spans.append((idx, strip_markup(lines[idx]), idx + 1, end))
    return spans


def effective_chars(lines: Sequence[str]) -> int:
    """章节有效字数：排除标题、表格分隔行、注释、未填充占位符。"""
    total = 0
    for line in lines:
        if not line.strip() or is_separator_row(line) or is_comment_line(line):
            continue
        if MD_ANY_H_RE.match(line.strip()):
            continue
        text = " ".join(table_cells(line)) if is_table_row(line) else strip_markup(line)
        text = PLACEHOLDER_RE.sub("", text)
        total += len(norm(text))
    return total


def dimension_substance_chars(lines: Sequence[str]) -> int:
    """必需维度「实质数据」字数：非表格正文 + 表格除首列外的数据单元格。

    剔除缺失标注与占位符；跳过表头行（其后紧跟分隔行）与表格首列（模板中多为
    「项目/序号」标签列），避免纯标签 + 「数据缺失」的空壳章节凑字数。
    """
    total = 0
    header_rows = set()
    for index, line in enumerate(lines):
        if is_separator_row(line) and index > 0 and is_table_row(lines[index - 1]):
            header_rows.add(index - 1)
    for idx, line in enumerate(lines):
        if not line.strip() or is_separator_row(line) or is_comment_line(line):
            continue
        if MD_ANY_H_RE.match(line.strip()):
            continue
        if is_table_row(line):
            if idx in header_rows:
                continue  # 表头行只含标签，不计数
            cells = table_cells(line)
            body = " ".join(cells[1:]) if len(cells) > 1 else ""
        else:
            body = strip_markup(line)
        body = MISSING_MARKER_RE.sub("", body)
        body = PLACEHOLDER_RE.sub("", body)
        total += len(norm(body))
    return total


# ---------------------------------------------------------------- 各项检查


def match_sections(spans: Sequence[Tuple[int, str, int, int]]):
    """把 13 个必填章节匹配到实际标题上。返回 (命中 dict, 缺失清单)。"""
    found = {}
    missing: List[str] = []
    for name, keywords in REQUIRED_SECTIONS:
        hit = None
        for span in spans:
            title = norm(span[1])
            if any(keyword in title for keyword in keywords):
                hit = span
                break
        if hit is None:
            missing.append(f"缺少必填章节：{name}（标题须含：{' / '.join(keywords)}）")
        else:
            found[name] = hit
    return found, missing


def check_vendor(lines: Sequence[str]) -> List[str]:
    """供应商名哨兵（P0-6）：匹配前对每行做归一化，防空格/加粗/全半角绕过。"""
    errors: List[str] = []
    hits: List[str] = []
    for index, line in enumerate(lines, start=1):
        if is_comment_line(line):
            continue
        nline = norm_vendor(line)
        for label, pattern in VENDOR_PATTERNS:
            if pattern.search(nline):
                hits.append(f"第 {index} 行出现供应商/工具名「{label}」→ {line.strip()[:80]}")
                break
    for item in hits[:MAX_DETAIL]:
        errors.append(
            "供应商名回退：" + item + "（报告只允许写能力语义，如「企业工商信息查询连接器（运行时探测）」）"
        )
    if len(hits) > MAX_DETAIL:
        errors.append(f"供应商名回退：共 {len(hits)} 处，仅列出前 {MAX_DETAIL} 处")
    return errors


def check_blank_fields(lines: Sequence[str]) -> List[str]:
    """表格留空单元格 + 未填充模板占位符。"""
    errors: List[str] = []
    blanks: List[str] = []
    holders: List[str] = []
    header_rows = set()
    for index, line in enumerate(lines):
        if is_separator_row(line) and index > 0 and is_table_row(lines[index - 1]):
            header_rows.add(index - 1)
    for index, line in enumerate(lines, start=1):
        if is_comment_line(line):
            continue
        if is_table_row(line) and not is_separator_row(line) and (index - 1) not in header_rows:
            cells = table_cells(line)
            if len(cells) >= 2 and any(not cell for cell in cells):
                blanks.append(f"第 {index} 行表格有留空单元格 → {line.strip()[:80]}")
        for match in PLACEHOLDER_RE.finditer(line):
            holders.append(f"第 {index} 行占位符未填充 → {match.group(0)}")
    for item in blanks[:MAX_DETAIL]:
        errors.append("缺失字段留空：" + item + "（须统一写 `数据缺失`，禁止留空或删节）")
    if len(blanks) > MAX_DETAIL:
        errors.append(f"缺失字段留空：共 {len(blanks)} 处留空单元格，仅列出前 {MAX_DETAIL} 处")
    for item in holders[:MAX_DETAIL]:
        errors.append("模板占位符未填充：" + item + "（交付稿不得保留 {} 占位符）")
    if len(holders) > MAX_DETAIL:
        errors.append(f"模板占位符未填充：共 {len(holders)} 处，仅列出前 {MAX_DETAIL} 处")
    return errors


def check_shells(lines: Sequence[str], found: dict) -> List[str]:
    errors: List[str] = []
    for name, span in found.items():
        body = lines[span[2]:span[3]]
        chars = effective_chars(body)
        if chars >= MIN_SECTION_CHARS:
            continue
        if MISSING_MARKER_RE.search("\n".join(body)):
            continue  # 显式标注了数据缺失 / 该维度数据获取失败，属合规写法
        errors.append(
            f"章节空壳：「{name}」有标题但无实质内容（有效字数 {chars} < {MIN_SECTION_CHARS}），"
            "须补实质内容，或按规范写 `数据缺失` / `该维度数据获取失败` + 原因"
        )
    return errors


def check_risk_subblocks(lines: Sequence[str], found: dict) -> List[str]:
    span = found.get("九、风险评估")
    if span is None:
        return []
    body = norm("\n".join(lines[span[2]:span[3]]))
    errors: List[str] = []
    for name, keywords in RISK_SUBBLOCKS:
        if not any(keyword in body for keyword in keywords):
            errors.append(f"风险评估章缺子块：{name}（须含 司法/经营/周边/交叉分析 四类）")
    return errors


def check_required_dimensions(lines: Sequence[str], found: dict) -> List[str]:
    """必需维度实质内容门禁（P0-2）：任一必需维度整体无实质数据 → 综合评级不放行。"""
    errors: List[str] = []
    for name in REQUIRED_DIMENSIONS:
        span = found.get(name)
        if span is None:
            continue  # 缺章已由 13 章必填检查拦截
        chars = dimension_substance_chars(lines[span[2]:span[3]])
        if chars < MIN_DIM_CHARS:
            errors.append(
                f"必需维度「{name}」无实质内容（有效数据字数 {chars} < {MIN_DIM_CHARS}，"
                "全为「数据缺失」/「该维度数据获取失败」）时不得输出完整报告与综合评级："
                "须取得该维度数据并填实质内容；若必需能力（企业主体定位/工商登记/司法涉诉与强制执行/"
                "经营异常与合规负面）缺失，须按 SKILL.md §1.6 改出「公开信息摘要」，禁止带评级的完整报告"
            )
    return errors


def check_report_shell(lines: Sequence[str], found: dict) -> List[str]:
    """全篇空壳门禁（P0-1）：无任何章节含非「数据缺失」的实质信息 → 拦截。"""
    if not found:
        return []
    if any(dimension_substance_chars(lines[span[2]:span[3]]) >= MIN_SECTION_CHARS
           for span in found.values()):
        return []
    return [
        f"空壳报告：全篇 {len(found)}/13 章均无实质信息（剔除「数据缺失/该维度数据获取失败」"
        "标注与表格标签后无任何章节达到实质内容线），禁止交付：至少一个章节须含非缺失的实质信息"
    ]


def check_form_consistency(text: str) -> List[str]:
    """形态一致性门禁（P0-7）：完整 13 章 ⇄ 头部声明连接器数据源；WebSearch-only ⇄ 摘要形态。"""
    errors: List[str] = []
    m = MAIN_SOURCE_RE.search(text)
    main_line = m.group(0) if m else ""
    declares_connector = ("连接器" in main_line) or ("工商信息查询" in main_line)
    if main_line and not declares_connector and PUBLIC_SOURCE_RE.search(main_line):
        errors.append(
            "数据形态不一致：头部「主要数据来源」仅声明公开网络检索（WebSearch），却输出完整 13 章报告。"
            "WebSearch-only 只能走「⚠️ 公开信息摘要」形态（SKILL.md §1.6），不得输出完整报告与综合评级；"
            "完整报告头部须声明「企业工商信息查询连接器（运行时探测）」等能力语义数据源"
        )
    elif not declares_connector and WEBSEARCH_ONLY_SELF_CLAIM_RE.search(text):
        errors.append(
            "数据形态不一致：报告自证全部数据仅通过 WebSearch 取得，却输出完整 13 章报告。"
            "WebSearch-only 只能走「⚠️ 公开信息摘要」形态（SKILL.md §1.6），不得输出完整报告与综合评级"
        )
    return errors


def detect_summary_mode(text: str) -> bool:
    """摘要形态唯一认定（P0-4/P0-5）：只认「⚠️ 公开信息摘要」类明确降级标记。"""
    return bool(SUMMARY_MODE_RE.search(text))


def check_summary_gate(text: str, lines: Sequence[str], found: dict) -> List[str]:
    """公开信息摘要校验（P0-4）：⚠️ 强制免责声明 + 实质内容 + 无评级结论 + 不套 13 章结构。

    报错信息不指导把摘要补成完整报告——摘要就是最终交付物之一。
    """
    errors: List[str] = []
    if len(found) >= FULL_REPORT_THRESHOLD:
        errors.append(
            f"公开信息摘要不得套用完整 13 章报告结构：识别到 {len(found)}/13 章。"
            "摘要形态只输出「已知公开信息 + 待核实事项清单」，不套用 report-template.md"
        )
    disclaimer_ok = any(k in text for k in (
        "未经工商数据核验", "不得作为立案或合作决策依据", "不能替代正式尽调", "不能替代", "不构成正式"
    ))
    if not disclaimer_ok:
        errors.append(
            "公开信息摘要缺少强制免责声明：头部必须标注「⚠️ 本摘要基于公开网络检索整理，未经工商数据核验，"
            "可能滞后或不完整，不能替代正式尽调，不得作为立案或合作决策依据」（SKILL.md §1.6），"
            "并提示前往「千问办公 设置 → 连接器」安装企业信息类连接器"
        )
    body_lines = [line for line in lines if "⚠" not in line]
    substance = effective_chars(body_lines)
    if substance < MIN_SECTION_CHARS:
        errors.append(
            f"公开信息摘要无实质内容（剔除 ⚠️ 强制声明后有效字数 {substance} < {MIN_SECTION_CHARS}）："
            "须输出已知公开信息与待核实事项清单，禁止只有声明没有内容"
        )
    hit_conclusions = [marker for marker in CONCLUSION_MARKERS if marker in text]
    for marker in hit_conclusions[:MAX_DETAIL]:
        errors.append(f"公开信息摘要禁止输出评级/结论内容：命中「{marker}」")
    return errors


def is_template_report(name: str, text: str) -> bool:
    """模板识别（P0-3）：文件名含 report-template，或内容含模板占位符/模板注释。"""
    if TEMPLATE_NAME_RE.search(name):
        return True
    return any(marker in text for marker in TEMPLATE_CONTENT_MARKERS)


def detect_registry_status(text: str, forced: str) -> Tuple[str, List[str], List[str]]:
    """判定工商数据获取状态。返回 (状态, 降级证据, 拦截项)。

    降级判定只认声明行「工商数据获取状态：未取得」；不依据「主要数据来源」行内容
    （P0-5：来源行简短/未提及 MCP 不得误判为降级；WebSearch 只作补充来源）。
    """
    errors: List[str] = []
    signals: List[str] = []

    match = STATUS_RE.search(text)
    declared: Optional[str] = match.group(1) if match else None
    if declared is None:
        errors.append(
            "缺少必填声明行「**工商数据获取状态：** 已取得 / 未取得」"
            "（SKILL.md §6.1，门禁据此判定是否允许输出完整报告）"
        )
    elif declared == "未取得":
        signals.append("报告声明「工商数据获取状态：未取得」")

    status = "未取得" if signals else (declared or "已取得")
    if forced != "auto":
        expected = "已取得" if forced == "available" else "未取得"
        if declared and declared != expected:
            errors.append(
                f"--registry-data={forced} 与报告声明「{declared}」不一致，请先核对工商数据获取状态"
            )
        if expected == "已取得" and signals:
            errors.append(
                "--registry-data=available 与报告实际降级证据冲突：" + "；".join(signals)
            )
        status = expected
    return status, signals, errors


def check_downgrade_gate(
    text: str, lines: Sequence[str], found: dict, signals: Sequence[str]
) -> List[str]:
    """降级态（声明工商数据未取得、非摘要形态）下的 A 档硬门禁。"""
    errors: List[str] = []
    evidence = "；".join(signals) if signals else "显式声明工商数据未取得"

    if len(found) >= FULL_REPORT_THRESHOLD:
        errors.append(
            f"降级态假装完整报告：工商数据未取得（{evidence}），却输出了 {len(found)}/13 章"
            "完整尽调报告结构。A 档禁止硬跑：只允许出「公开信息摘要」，"
            "并提示用户前往「千问办公 设置 → 连接器」安装企业信息类连接器"
        )
    hit_conclusions = [marker for marker in CONCLUSION_MARKERS if marker in text]
    for marker in hit_conclusions[:MAX_DETAIL]:
        errors.append(f"降级态禁止输出结论/评级内容：命中「{marker}」")
    if not UNVERIFIED_RE.search(text):
        errors.append("降级态全文必须标注「未核验」，当前一处也没有")
    if not WARN_MARK_RE.search(text):
        errors.append("降级态头部必须有 ⚠️ 声明（未经工商数据核验，不得作为立案/合作决策依据）")
    if not CONNECTOR_HINT_RE.search(text):
        errors.append("降级态必须提示用户前往「千问办公 设置 → 连接器」安装企业信息类连接器")
    return errors


# ---------------------------------------------------------------- 主流程


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="validate_dd_report.py",
        description=(
            "企业尽调报告交付门禁：① 模板文件拦截 ② 摘要/降级态防假装完整报告 "
            "③ 13 章必填齐备 ④ 空壳与必需维度缺失不放行综合评级 ⑤ 供应商名哨兵（归一化匹配） "
            "⑥ 缺失字段须写 `数据缺失` ⑦ 完整 13 章 ⇄ 头部声明连接器数据源（形态一致性）。"
            "未通过以非零退出码阻断交付。"
        ),
        epilog=(
            "示例：\n"
            "  python3 scripts/validate_dd_report.py outputs/某公司_企业尽调报告.md\n"
            "  python3 scripts/validate_dd_report.py outputs/某公司_企业尽调报告.md --registry-data missing\n"
            "  python3 scripts/validate_dd_report.py outputs/某公司_企业尽调报告.docx\n"
            "\n退出码：0=通过；1=拦截；2=输入错误。\n"
            "报告头部须有必填声明行：**工商数据获取状态：** 已取得 / 未取得（SKILL.md §6.1）。\n"
            "含「⚠️ 公开信息摘要」强制声明的文件按 §1.6 摘要规则校验（本参数对其不生效）。\n"
            "模板文件（references/report-template.md 或其副本）会被识别并拦截（exit 1）。\n"
            "docx 复核依赖 python-docx（pip3 install python-docx）。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("report", type=Path,
                       help="尽调报告文件路径（.md/.markdown/.txt/.docx）")
    parser.add_argument(
        "--registry-data",
        choices=("auto", "available", "missing"),
        default="auto",
        help="工商数据获取状态：auto=按报告声明行自动判定（默认）；"
             "available/missing=显式指定并与报告交叉校验（公开信息摘要形态下自动忽略）",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        lines = load_document(args.report)
    except InputError as exc:
        print(f"输入错误：{exc}", file=sys.stderr)
        return 2

    text = "\n".join(lines)
    if not text.strip():
        print("输入错误：报告内容为空", file=sys.stderr)
        return 2

    # --- ⓪ 模板黑名单（P0-3）：两种形态都拦，先于一切判定 ---
    if is_template_report(args.report.name, text):
        print(f"❌ 门禁未通过 — 报告：{args.report.name}｜模板文件，非报告", file=sys.stderr)
        print("- 拦截：该文件是报告模板（references/report-template.md 或其副本），不是实际尽调报告。"
              "请按 SKILL.md 流程基于真实查询数据填写后另存为正式报告文件"
              "（文件名不得含 report-template），再运行门禁；禁止交付模板本身。", file=sys.stderr)
        return 1

    spans = section_spans(lines)
    found, missing = match_sections(spans)

    errors: List[str] = []
    passes: List[str] = []

    summary_mode = detect_summary_mode(text)

    if summary_mode:
        # --- 摘要形态（P0-4/P0-5）：按 §1.6 公开信息摘要规则校验 ---
        mode_label = "公开信息摘要"
        sum_errors = check_summary_gate(text, lines, found)
        errors.extend(sum_errors)
        if not sum_errors:
            passes.append("公开信息摘要形态合规：含 ⚠️ 强制免责声明 + 实质内容，无评级结论，未套用 13 章结构")
    else:
        status, signals, status_errors = detect_registry_status(text, args.registry_data)
        errors.extend(status_errors)
        mode_label = "降级态（未取得）" if status == "未取得" else "完整报告（已取得）"

        if status == "未取得":
            # --- ① 降级态（声明未取得、无摘要标记）：A 档硬门禁 ---
            gate_errors = check_downgrade_gate(text, lines, found, signals)
            errors.extend(gate_errors)
            if not gate_errors:
                passes.append(f"降级态（工商数据未取得）合规：{len(found)}/13 章未成完整报告结构，"
                              "含 ⚠️ 声明 + 未核验标注 + 连接器安装提示，无评级结论")
        else:
            # --- ②③④⑥⑦ 完整报告结构校验 ---
            if not status_errors:
                passes.append("工商数据获取状态 = 已取得，允许输出完整尽调报告")
            errors.extend(missing)
            if not missing:
                passes.append(f"13 个必填章节齐备（{len(found)}/13）")
            risk_errors = check_risk_subblocks(lines, found)
            errors.extend(risk_errors)
            if not risk_errors and "九、风险评估" in found:
                passes.append("风险评估章四子块齐备（司法 / 经营 / 周边 / 交叉分析）")
            shell_errors = check_shells(lines, found)
            errors.extend(shell_errors)
            if not shell_errors and found:
                passes.append(f"章节实质内容校验通过（{len(found)} 章均有实质内容或显式缺失标注）")
            dim_errors = check_required_dimensions(lines, found)
            errors.extend(dim_errors)
            if not dim_errors:
                passes.append("必需维度实质内容校验通过（企业基本信息/股权结构/主要人员/知识产权/行业资质/风险评估）")
            whole_errors = check_report_shell(lines, found)
            errors.extend(whole_errors)
            if not whole_errors:
                passes.append("全篇空壳校验通过（至少一个章节含非缺失的实质信息）")
            blank_errors = check_blank_fields(lines)
            errors.extend(blank_errors)
            if not blank_errors:
                passes.append("缺失字段校验通过（无留空单元格、无未填充占位符）")
            form_errors = check_form_consistency(text)
            errors.extend(form_errors)
            if not form_errors:
                passes.append("数据形态一致性校验通过（完整 13 章 ⇄ 头部声明连接器数据源）")

    # --- ⑤ 供应商名哨兵（两种形态都查，归一化匹配）---
    vendor_errors = check_vendor(lines)
    errors.extend(vendor_errors)
    if not vendor_errors:
        passes.append("供应商名哨兵通过（报告内无任何供应商 / 工具名）")

    mode_label = "公开信息摘要" if summary_mode else mode_label
    header = f"报告：{args.report.name}｜形态：{mode_label}｜识别到章节 {len(found)}/13"
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
