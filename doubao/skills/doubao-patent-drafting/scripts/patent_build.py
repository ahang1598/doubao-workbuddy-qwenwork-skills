#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""专利申请文件审阅稿编译器（单文件、纯标准库、兼容 Python 3.8）。

用法：
    python3 scripts/patent_build.py build --draft draft.md --out output/
    python3 scripts/patent_build.py selftest        （或 --selftest）

draft.md 合同见 SKILL.md；机械检查为 C1-C20。stdout 最后一行固定为：
    PATENT_BUILD: PASS 输出=<docx路径> 检查=<n项通过>
    PATENT_BUILD: FAIL 报告=<report路径>

附图文件约定（draft.md 合同本身不含图片路径字段，属本脚本的补充约定，
非设计文档条款，如需变更请同步告知 SKILL.md 撰写方）：
    真实附图按图号存放在 <draft.md 同级目录>/figures/ 下，文件名为
    「N.png」「N.jpg」「N.jpeg」之一（N 为图号，从 1 开始），可用
    --figures-dir 覆盖该目录。找不到对应文件视为构建失败，不会假装已嵌入。

draft.md 编码约定（同为本脚本的补充约定）：
    draft.md 必须是 UTF-8 编码（可带或不带 BOM）。非 UTF-8 编码（如 GBK/ANSI）
    一律判定为构建失败并给出中文提示，不做静默的乱码替换。
    若 --out 指定的路径已存在但不是目录（与输出目录同名的普通文件），
    同样直接判定失败，不依赖文件系统异常的裸报错。

机械检查 C11 与散文 Markdown 规范化（同为本脚本的补充约定，非设计文档条款）：
    豆包撰写 draft.md 时偶尔会在"散文型"文本——审阅说明的撰写结论/待确认
    事项/边界与免责、说明书各节正文、说明书摘要——里混入行内 Markdown 标记
    （行首 #、成对 **/__、行首 -/*/+ 列表符、``` 代码围栏等），原样渲染进
    docx 会被专家视为格式缺陷。本脚本在"解析之后、写入 docx 之前"对上述散文
    区域自动清理这些标记（不改 draft.md 原文件），并新增 C11 检查：命中即判
    定为 WARN（不阻断构建，因为渲染层已自动清理），在 stdout 的「提示【C11】」
    中列出被清理的具体行与标记类别，便于下次直接产出干净稿。权利要求书区
    （「N. 」编号具语义）与案件头字段行不在清理与检测范围内。

权利要求书条目间空行（同为本脚本的补充约定，非设计文档条款）：
    权利要求书条目之间若留有空行（下一处非空行以「N. 」开头），解析层静默
    忽略该空行，解析结果与不留空行时完全一致，C2 只报一条 WARN 提示下次不要
    留空行，不阻断构建；但若空行出现在同一条权利要求文本中间、把它劈成两截
    （空行后一行不以「N. 」开头），仍判定为 C2 FAIL。

机械检查 C12：发明内容/实用新型内容与权利要求整句照抄检测（同为本脚本的补充
约定，非设计文档条款）：
    专家评测反复点名的失分模式——说明书"发明内容"/"实用新型内容"部分大段
    复制粘贴权利要求原文、不加任何连接语（references/writing-style.md 已有
    文字规则禁止此事，但过去一直没有脚本兜底）。本检查把每条权利要求按中文
    句号/分号切分为子句，过滤掉长度 <25 字的必然重复短子句（如"其特征在
    于"），发明内容/实用新型内容正文做同样切分后逐句比对；比对前分别剥离从
    权引用前缀「根据权利要求N所述的…，其特征在于，」（权利要求侧）与
    「进一步地」等引导词（发明内容侧），只有剥离后去除首尾空白逐字完全一致
    才算命中——像"为解决上述技术问题，本发明提供一种…"这种带连接语、只是
    复述独立权利要求技术方案的规范写法不会被误判。命中数量占权利要求候选
    子句总数比例 ≥60% 判 FAIL，30%~60% 判 WARN，<30% 不报（详见 check_c12）。

机械检查 C13：内部工具名泄漏检测（同为本脚本的补充约定，非设计文档条款）：
    法律文书正文不得出现本 skill 的内部工具、文件名或审计编码痕迹（脚本名 patent_build.py、
    draft.md、SKILL.md、sub-skills、writing-style.md、doubao-patent-drafting、
    stdout 契约字样 PATENT_BUILD:、selftest、修稿报告、P0/P1、A/B/C/D 级等）。扫描范围覆盖全部
    将渲染进 docx 的正文文本——审阅说明（撰写结论/待确认事项/边界与免责）、
    说明书摘要、权利要求书、说明书各节正文；案件头字段行不在扫描范围内（该
    字段的取值合法性另由 C1/C5 等检查覆盖，不与本检查重复）。命中词表任一
    子串即判定为 FAIL，不设 WARN 降级——这是文书事故，不是可以留到下次改进
    的机械噪音（详见 check_c13）。

机械检查 C16-C18：C16 统一公式符号并拦截未定义变量；C17 检查附图标记重名和
仅在标记表出现、正文未使用的编号；C18 在测试或性能状态仍待确认时，拦截
“明显优于”“从根本上解决”等证据强度过高的结论。三项均为 FAIL 级。

draft.md 历史快照（同为本脚本的补充约定，非设计文档条款）：
    构建整体 PASS 且 docx 成功生成后，脚本会把当次 draft.md 原样复制一份到
    <out_dir>/history/draft-<时间戳>.md（时间戳来自 time.strftime，同一秒内
    重复构建自动加序号后缀避免覆盖旧快照），便于事后追溯某次 docx 产出对应
    的源稿版本。快照写入用 try/except 包裹：目录不可写等原因导致快照失败时，
    只在 stdout 打印一行提示，不影响本次构建的 PASS 结论与返回码；stdout 最
    后一行仍固定为 PATENT_BUILD 结论行（详见 _snapshot_draft_history）。
"""

import argparse
import datetime
import re
import struct
import sys
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# =====================================================================
# 第一段：解析 draft.md
# =====================================================================

@dataclass(frozen=True)
class Line:
    no: int
    text: str


@dataclass(frozen=True)
class Claim:
    number: Optional[int]
    text: str
    line_no: int


@dataclass(frozen=True)
class PendingItem:
    level: str
    event: str
    impact: str
    line_no: int


@dataclass(frozen=True)
class SpecSection:
    title: str
    heading_line_no: int
    lines: List[Line]

    def text(self) -> str:
        return "".join(l.text.strip() for l in self.lines if l.text.strip())


REQUIRED_H1 = ["案件头", "审阅说明", "说明书摘要", "权利要求书", "说明书"]
REQUIRED_REVIEW_H2 = ["撰写结论", "待确认事项", "边界与免责"]
CONTENT_TITLE_BY_CASE_TYPE = {"发明": "发明内容", "实用新型": "实用新型内容"}

FIELD_LINE_RE = re.compile(r"^-\s*([^:：]+?)\s*[:：]\s*(.*)$")
DRAWING_STATUS_RE = re.compile(
    r"^真实附图(\d+)幅$|^规划图名(\d+)条$|^无$|^真实附图(\d+)幅[＋+]规划图名(\d+)条$")
MARKER_ENTRY_RE = re.compile(r"^(\d+)\s*[=＝]\s*(\S.*)$")
CLAIM_START_RE = re.compile(r"^(\d+)\.\s*(.*)$")
PENDING_ITEM_RE = re.compile(r"^-\s*\[(本次定稿前需要确认|正式提交前建议确认)\]\s*(.+)$")
PENDING_LEVEL_BY_LABEL = {
    "本次定稿前需要确认": "P0",
    "正式提交前建议确认": "P1",
}
PENDING_LABEL_BY_LEVEL = {level: label for label, level in PENDING_LEVEL_BY_LABEL.items()}


@dataclass
class Draft:
    source_path: str
    parse_notes: List[str] = field(default_factory=list)

    h1_order: List[str] = field(default_factory=list)

    case_header_fields: Dict[str, Tuple[str, int]] = field(default_factory=dict)
    unparsed_header_lines: List[Line] = field(default_factory=list)
    case_type: Optional[str] = None
    invention_name: Optional[str] = None
    subject_entity: Optional[str] = None  # 主题实体（阶段一按整机口径登记，C19 比对）
    drawing_status_raw: Optional[str] = None
    drawing_mode: Optional[str] = None  # "real" | "planned" | "mixed" | "none" | None(非法)
    drawing_count: int = 0  # 附图说明应列出的总图数（mixed = 真实+规划）
    real_figure_count: int = 0  # 需要嵌入 docx 的真实图数（图1..M，v7 实测：仅有部分外观图的案件必须能混合声明）
    marker_table_raw: Optional[str] = None
    marker_table: Dict[int, str] = field(default_factory=dict)
    marker_table_bad_entries: List[str] = field(default_factory=list)

    review_h2_order: List[str] = field(default_factory=list)
    conclusion_lines: List[Line] = field(default_factory=list)
    pending_items: List[PendingItem] = field(default_factory=list)
    boundary_lines: List[Line] = field(default_factory=list)

    abstract_lines: List[Line] = field(default_factory=list)

    claims_present: bool = False
    claims: List[Claim] = field(default_factory=list)
    claims_body_lines: List[Line] = field(default_factory=list)
    claims_leading_orphan: List[Line] = field(default_factory=list)
    claims_interior_blank_line_nos: List[int] = field(default_factory=list)
    claims_blank_separator_line_nos: List[int] = field(default_factory=list)

    spec_h2_order: List[str] = field(default_factory=list)
    spec_sections: Dict[str, SpecSection] = field(default_factory=dict)

    def abstract_text(self) -> str:
        return "".join(l.text.strip() for l in self.abstract_lines if l.text.strip())

    def all_spec_lines(self) -> List[Line]:
        result: List[Line] = []
        for title in self.spec_h2_order:
            section = self.spec_sections.get(title)
            if section:
                result.extend(section.lines)
        return result

    def spec_full_text(self) -> str:
        return "".join(l.text.strip() for l in self.all_spec_lines() if l.text.strip())


def _heading_level(line_text: str) -> Tuple[Optional[int], Optional[str]]:
    m = re.match(r"^(#{1,6})[ \t]+(.*\S)[ \t]*$", line_text)
    if not m:
        return None, None
    return len(m.group(1)), m.group(2).strip()


def _split_by_level(lines: List[Line], level: int) -> List[Tuple[str, int, List[Line]]]:
    """按标题层级切分为 [(标题, 标题所在行号, 内容行列表)]；内容行含更深层标题原文。"""
    sections: List[Tuple[str, int, List[Line]]] = []
    title: Optional[str] = None
    heading_no = 0
    body: List[Line] = []
    for line in lines:
        lvl, text = _heading_level(line.text)
        if lvl == level:
            if title is not None:
                sections.append((title, heading_no, body))
            title, heading_no, body = text, line.no, []
        else:
            if title is not None:
                body.append(line)
    if title is not None:
        sections.append((title, heading_no, body))
    return sections


def _parse_case_header(content: List[Line], draft: Draft) -> None:
    for line in content:
        if not line.text.strip():
            continue
        m = FIELD_LINE_RE.match(line.text.strip())
        if not m:
            draft.unparsed_header_lines.append(line)
            continue
        key, value = m.group(1).strip(), m.group(2).strip()
        draft.case_header_fields[key] = (value, line.no)

    if "案件类型" in draft.case_header_fields:
        draft.case_type = draft.case_header_fields["案件类型"][0]
    if "发明名称" in draft.case_header_fields:
        draft.invention_name = draft.case_header_fields["发明名称"][0]
    if "主题实体" in draft.case_header_fields:
        draft.subject_entity = draft.case_header_fields["主题实体"][0]
    if "附图状态" in draft.case_header_fields:
        raw = draft.case_header_fields["附图状态"][0]
        draft.drawing_status_raw = raw
        m = DRAWING_STATUS_RE.match(raw)
        if m:
            if raw == "无":
                draft.drawing_mode, draft.drawing_count = "none", 0
            elif m.group(1) is not None:
                draft.drawing_mode, draft.drawing_count = "real", int(m.group(1))
                draft.real_figure_count = int(m.group(1))
            elif m.group(2) is not None:
                draft.drawing_mode, draft.drawing_count = "planned", int(m.group(2))
            else:
                real, planned = int(m.group(3)), int(m.group(4))
                draft.drawing_mode = "mixed"
                draft.real_figure_count = real
                draft.drawing_count = real + planned
    if "附图标记表" in draft.case_header_fields:
        raw = draft.case_header_fields["附图标记表"][0]
        draft.marker_table_raw = raw
        if raw != "无":
            for piece in re.split(r"[,，、]", raw):
                piece = piece.strip()
                if not piece:
                    continue
                m = MARKER_ENTRY_RE.match(piece)
                if m:
                    draft.marker_table[int(m.group(1))] = m.group(2).strip()
                else:
                    draft.marker_table_bad_entries.append(piece)


def _parse_review_note(content: List[Line], draft: Draft) -> None:
    h2_sections = _split_by_level(content, 2)
    draft.review_h2_order = [t for t, _, _ in h2_sections]
    for title, _, body in h2_sections:
        if title == "撰写结论":
            draft.conclusion_lines = body
        elif title == "待确认事项":
            for line in body:
                stripped = line.text.strip()
                if not stripped:
                    continue
                m = PENDING_ITEM_RE.match(stripped)
                if not m:
                    draft.parse_notes.append(
                        "待确认事项 第{}行 无法识别：{}".format(line.no, stripped)
                    )
                    continue
                label, rest = m.group(1), m.group(2)
                level = PENDING_LEVEL_BY_LABEL[label]
                if "：" in rest:
                    event, impact = rest.split("：", 1)
                elif ":" in rest:
                    event, impact = rest.split(":", 1)
                else:
                    event, impact = rest, ""
                draft.pending_items.append(
                    PendingItem(level=level, event=event.strip(), impact=impact.strip(), line_no=line.no)
                )
        elif title == "边界与免责":
            draft.boundary_lines = body


def _parse_claims(content: List[Line], draft: Draft) -> None:
    """解析权利要求书正文。

    条目之间的空行（空行之后的下一处非空行以「N. 」开头，是新条目的起点）按
    补充约定静默吞掉：不计入任何权项文本，解析结果与不留空行时完全一致；只是
    把行号记入 claims_blank_separator_line_nos，供 check_c2 报一条 WARN 提示。
    若空行出现在同一条权项文本中间——空行之后的下一处非空行不是以「N. 」开头
    （即只是被空行打断的续行）——判定为真正的文本断裂，行号记入
    claims_interior_blank_line_nos，供 check_c2 报 FAIL。
    """
    draft.claims_present = True
    start, end = 0, len(content)
    while start < end and not content[start].text.strip():
        start += 1
    while end > start and not content[end - 1].text.strip():
        end -= 1
    body = content[start:end]
    draft.claims_body_lines = body

    number: Optional[int] = None
    text_parts: List[str] = []
    claim_line_no = 0
    saw_first_number = False

    def flush() -> None:
        if number is not None:
            draft.claims.append(Claim(number=number, text="".join(text_parts), line_no=claim_line_no))

    n = len(body)
    i = 0
    while i < n:
        line = body[i]
        stripped = line.text.strip()
        if not stripped:
            blank_run = [line.no]
            j = i + 1
            while j < n and not body[j].text.strip():
                blank_run.append(body[j].no)
                j += 1
            # body 的首尾空行已在上面裁掉，因此这里 j < n 恒成立：空行之后必有
            # 非空内容可供判断——要么是下一条「N. 」，要么是被打断的续行。
            next_stripped = body[j].text.strip()
            if saw_first_number and CLAIM_START_RE.match(next_stripped):
                draft.claims_blank_separator_line_nos.extend(blank_run)
            else:
                draft.claims_interior_blank_line_nos.extend(blank_run)
            i = j
            continue
        m = CLAIM_START_RE.match(stripped)
        if m:
            flush()
            saw_first_number = True
            number, claim_line_no = int(m.group(1)), line.no
            text_parts = [m.group(2)]
        elif not saw_first_number:
            draft.claims_leading_orphan.append(line)
        else:
            text_parts.append(stripped)
        i += 1
    flush()


def _parse_specification(content: List[Line], draft: Draft) -> None:
    h2_sections = _split_by_level(content, 2)
    draft.spec_h2_order = [t for t, _, _ in h2_sections]
    for title, no, body in h2_sections:
        draft.spec_sections[title] = SpecSection(title=title, heading_line_no=no, lines=body)


def parse_draft(text: str, source_path: str) -> Draft:
    draft = Draft(source_path=source_path)
    raw_lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines = [Line(i + 1, t) for i, t in enumerate(raw_lines)]

    h1_sections = _split_by_level(lines, 1)
    draft.h1_order = [t for t, _, _ in h1_sections]
    for title, _, body in h1_sections:
        if title == "案件头":
            _parse_case_header(body, draft)
        elif title == "审阅说明":
            _parse_review_note(body, draft)
        elif title == "说明书摘要":
            draft.abstract_lines = body
        elif title == "权利要求书":
            _parse_claims(body, draft)
        elif title == "说明书":
            _parse_specification(body, draft)
    return draft


# =====================================================================
# 第 1.5 段：散文文本 Markdown 规范化（渲染前清理 与 C11 检查共用同一实现）
# =====================================================================

_MD_FENCE_RE = re.compile(r"^[ \t]*```")
_MD_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(\S.*)$")
_MD_LIST_RE = re.compile(r"^([-*+])[ \t]+(\S.*)$")
_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")
_MD_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)|(?<!_)_([^_\n]+)_(?!_)")
_MD_CODE_RE = re.compile(r"`([^`\n]+)`")
_MD_NUM_LIST_SPACE_RE = re.compile(r"^(\d+)\.[ \t]{2,}(\S.*)$")

MD_HIT_LABELS = {
    "heading": "标题标记（行首 #）",
    "list": "列表标记（行首 -/*/+）",
    "bold": "加粗标记（**/__）",
    "italic": "斜体标记（*/_）",
    "code": "行内代码标记（`）",
    "fence": "代码围栏标记（```）",
}


def normalize_prose_markdown(text: str) -> Tuple[str, List[str]]:
    """清理散文型文本中残留的行内 Markdown 标记，返回（清理后文本, 命中类别列表）。

    调用方必须只传入"散文"区域文本（审阅说明撰写结论/待确认事项/边界与免责、
    说明书摘要、说明书各节正文）：权利要求书内「N. 」编号是语义编号，案件头
    字段行另有专门语法，两者都不得经过本函数处理。

    命中类别（用于 C11 提示与 MD_HIT_LABELS 对照）：
        heading 行首 #{1,6}（去标记，原文按普通段落保留）
        list    行首 -/*/+ 列表符（转换为「・」前缀，保留原缩进文字）
        bold    成对 **x**/__x__ （去标记保留 x）
        italic  成对 *x*/_x_ （去标记保留 x；不成对的孤立 */_ 不处理）
        code    成对反引号 `x`（去标记保留 x）
        fence   独占一行的 ``` 代码围栏（整行清空，不渲染空段落）
    行首「N. 」数字列表在非权利要求区仅做多余空格归一，不计入命中类别（不算
    Markdown 残留缺陷，属于纯粹的空白整理）。
    """
    hits: List[str] = []
    s = text

    if _MD_FENCE_RE.match(s):
        return "", ["fence"]

    m = _MD_HEADING_RE.match(s)
    if m:
        hits.append("heading")
        s = m.group(2)

    m = _MD_LIST_RE.match(s)
    if m:
        hits.append("list")
        s = "・" + m.group(2)

    if _MD_BOLD_RE.search(s):
        hits.append("bold")
        s = _MD_BOLD_RE.sub(lambda mo: mo.group(1) if mo.group(1) is not None else mo.group(2), s)

    italic_replaced = _MD_ITALIC_RE.sub(
        lambda mo: mo.group(1) if mo.group(1) is not None else mo.group(2), s)
    if italic_replaced != s:
        hits.append("italic")
    s = italic_replaced

    if _MD_CODE_RE.search(s):
        hits.append("code")
        s = _MD_CODE_RE.sub(r"\1", s)

    m = _MD_NUM_LIST_SPACE_RE.match(s)
    if m:
        s = "{}. {}".format(m.group(1), m.group(2))

    return s, hits


# =====================================================================
# 第二段：机械检查 C1-C12
# =====================================================================

@dataclass(frozen=True)
class Issue:
    check: str
    severity: str  # FAIL | WARN
    location: str
    problem: str
    fix: str


def check_c1(draft: Draft) -> List[Issue]:
    """结构：案件头字段齐全；必需章节存在且顺序正确；案件类型与内容标题匹配。"""
    issues: List[Issue] = []

    for note in draft.parse_notes:
        issues.append(Issue(
            "C1", "FAIL", "审阅说明/待确认事项", note,
            "待确认事项仅使用“本次定稿前需要确认”或“正式提交前建议确认”两类对外标签，"
            "不要使用 P0/P1 等内部代码。"))

    for line in draft.unparsed_header_lines:
        issues.append(Issue("C1", "FAIL", "案件头 第{}行".format(line.no),
                             "无法识别的案件头字段行：「{}」。".format(line.text.strip()),
                             "按「- 字段: 值」格式书写，字段名与冒号之间不要多余符号。"))

    required_fields = ["案件类型", "发明名称", "主题实体", "附图状态", "附图标记表"]
    for f in required_fields:
        if f not in draft.case_header_fields or not draft.case_header_fields[f][0].strip():
            issues.append(Issue("C1", "FAIL", "案件头",
                                 "缺少必填字段「{}」。".format(f),
                                 "在「# 案件头」下补充「- {}: <值>」一行。".format(f)))

    if draft.case_type is not None and draft.case_type not in ("发明", "实用新型"):
        issues.append(Issue("C1", "FAIL", "案件头/案件类型",
                             "案件类型取值「{}」不合法。".format(draft.case_type),
                             "案件类型只能是「发明」或「实用新型」二者之一。"))

    if draft.drawing_status_raw is not None and draft.drawing_mode is None:
        issues.append(Issue("C1", "FAIL", "案件头/附图状态",
                             "附图状态取值「{}」不合法。".format(draft.drawing_status_raw),
                             "附图状态写「真实附图N幅」「规划图名N条」「无」之一；既有真实图又有规划图时写"
                             "「真实附图M幅+规划图名N条」（真实图占图1..M，按图号存 figures/ 目录）。"))

    if draft.marker_table_bad_entries:
        issues.append(Issue("C1", "FAIL", "案件头/附图标记表",
                             "附图标记表中以下条目无法解析：{}。".format("、".join(draft.marker_table_bad_entries)),
                             "每条标记须写成「编号=名称」，多条之间用逗号或顿号分隔，例如「1=柜体, 7=玻璃门」。"))

    if draft.h1_order != REQUIRED_H1:
        issues.append(Issue("C1", "FAIL", "draft.md 章节结构",
                             "顶级章节应依次为 {}，实际为 {}。".format(REQUIRED_H1, draft.h1_order),
                             "按 draft.md 合同固定骨架调整章节的增删与顺序（不得缺项、多项或错序）。"))

    if draft.review_h2_order != REQUIRED_REVIEW_H2:
        issues.append(Issue("C1", "FAIL", "审阅说明 子章节",
                             "「审阅说明」下子章节应依次为 {}，实际为 {}。".format(REQUIRED_REVIEW_H2, draft.review_h2_order),
                             "补齐「## 撰写结论」「## 待确认事项」「## 边界与免责」三节且保持该顺序。"))

    if draft.case_type in CONTENT_TITLE_BY_CASE_TYPE and draft.drawing_mode is not None:
        expected = ["发明名称", "技术领域", "背景技术", CONTENT_TITLE_BY_CASE_TYPE[draft.case_type]]
        if draft.drawing_mode in ("real", "planned", "mixed"):
            expected.append("附图说明")
        expected.append("具体实施方式")
        if draft.spec_h2_order != expected:
            other_title = "实用新型内容" if draft.case_type == "发明" else "发明内容"
            hint = ""
            if other_title in draft.spec_h2_order:
                hint = "案件类型为「{}」，说明书标题应使用「{}」而非「{}」。".format(
                    draft.case_type, CONTENT_TITLE_BY_CASE_TYPE[draft.case_type], other_title)
            else:
                hint = "按案件类型与附图状态调整「说明书」下子标题的增删与顺序。"
            issues.append(Issue("C1", "FAIL", "说明书 子章节",
                                 "「说明书」下子章节应依次为 {}，实际为 {}。".format(expected, draft.spec_h2_order),
                                 hint))
    return issues


def check_c2(draft: Draft) -> List[Issue]:
    """权项格式：编号连续从1起；每项恰好一个句尾句号；无项目符号/链接。

    条目之间的空行不再判为 FAIL：解析层已静默忽略（结果与不留空行时完全一致），
    这里改报一条 WARN 提示下次不要留空行。但空行把同一条权项文本从中间劈成两截
    （空行后一行不以「N. 」开头）时，仍是真正的断裂，判 FAIL。
    """
    issues: List[Issue] = []
    if not draft.claims_present:
        return issues

    if draft.claims_leading_orphan:
        first = draft.claims_leading_orphan[0]
        issues.append(Issue("C2", "FAIL", "权利要求书 第{}行".format(first.no),
                             "权利要求书正文首行不是编号权利要求：「{}」。".format(first.text.strip()),
                             "删除编号之外的说明文字，权利要求书应直接以「1. 」开始逐条列出。"))

    for no in draft.claims_interior_blank_line_nos:
        issues.append(Issue("C2", "FAIL", "权利要求书 第{}行".format(no),
                             "权利要求书内部出现空行，把一条权利要求的正文打断成了两截"
                             "（空行后一行不是以「N. 」开头的新条目）。",
                             "删除该空行，把被打断的正文重新接续为同一条完整陈述。"))

    if draft.claims_blank_separator_line_nos:
        line_list = "、".join(str(no) for no in draft.claims_blank_separator_line_nos)
        issues.append(Issue("C2", "WARN", "权利要求书 第{}行".format(line_list),
                             "权利要求书条目间存在空行（第{}行），已自动忽略；解析结果与不留空行时完全一致。".format(line_list),
                             "下次书写时权项之间请不要留空行，各条应前后相接、连续排列。"))

    for line in draft.claims_body_lines:
        stripped = line.text.strip()
        if not stripped:
            continue
        if re.match(r"^[-*+•·]\s", stripped):
            issues.append(Issue("C2", "FAIL", "权利要求书 第{}行".format(line.no),
                                 "出现项目符号：「{}」。".format(stripped),
                                 "权利要求书只能用「N. 」阿拉伯数字编号，不得使用项目符号。"))
        if re.search(r"\[[^\]]*\]\([^)]*\)", stripped):
            issues.append(Issue("C2", "FAIL", "权利要求书 第{}行".format(line.no),
                                 "出现 Markdown 链接语法：「{}」。".format(stripped),
                                 "权利要求书为纯文本陈述，删除链接语法。"))

    numbers = [c.number for c in draft.claims]
    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        issues.append(Issue("C2", "FAIL", "权利要求书",
                             "权利要求编号应从 1 开始连续排列，实际序列为 {}。".format(numbers),
                             "重新核对权利要求编号，确保连续、不跳号、不重复。"))

    for claim in draft.claims:
        count = claim.text.count("。")
        ends_ok = claim.text.rstrip().endswith("。")
        if count != 1 or not ends_ok:
            issues.append(Issue("C2", "FAIL", "权利要求书 第{}行（第{}项）".format(claim.line_no, claim.number),
                                 "本条应恰好包含一个句尾中文句号，实际检测到 {} 个句号，且{}。".format(
                                     count, "末尾是句号" if ends_ok else "末尾不是句号"),
                                 "将本条改写为一段完整陈述，仅在结尾使用一个「。」，条内并列请用顿号、逗号或分号。"))
    return issues


DEP_REF_RE = re.compile(r"^根据权利要求([0-9、，,至或任一项中\s]+?)所述的([^，,。；;]+)[，,]")
INDEP_SUBJECT_RE = re.compile(r"^一种([^，,。；;]+)[，,]")


def _parse_ref_numbers(clause: str) -> List[int]:
    range_m = re.search(r"(\d+)\s*至\s*(\d+)", clause)
    if range_m:
        lo, hi = int(range_m.group(1)), int(range_m.group(2))
        if lo <= hi:
            return list(range(lo, hi + 1))
    return [int(n) for n in re.findall(r"\d+", clause)]


def _claim_profile(claim: Claim) -> Dict:
    m = DEP_REF_RE.match(claim.text)
    if m:
        return {"dependent": True, "refs": _parse_ref_numbers(m.group(1)), "subject": m.group(2).strip()}
    m2 = INDEP_SUBJECT_RE.match(claim.text)
    if m2:
        return {"dependent": False, "refs": [], "subject": m2.group(1).strip()}
    return {"dependent": False, "refs": [], "subject": None}


def _subject_consistent(a: Optional[str], b: Optional[str]) -> bool:
    if a is None or b is None:
        return True
    return a == b or a.endswith(b) or b.endswith(a)


def check_c3(draft: Draft) -> List[Issue]:
    """引用关系：从权引用编号<自身编号且存在；主题词一致；多引用从权不引用多引用从权。"""
    issues: List[Issue] = []
    if not draft.claims:
        return issues
    profiles = {c.number: _claim_profile(c) for c in draft.claims if c.number is not None}

    for claim in draft.claims:
        if claim.number is None:
            continue
        profile = profiles[claim.number]
        if not profile["dependent"]:
            continue
        loc = "权利要求书 第{}行（第{}项）".format(claim.line_no, claim.number)
        refs = profile["refs"]
        if not refs:
            issues.append(Issue("C3", "FAIL", loc,
                                 "本条以「根据权利要求…所述的」引用他项，但未能解析出被引用的编号。",
                                 "使用标准句式「根据权利要求N所述的<主题>」「…N或M所述的…」「…N至M中任一项所述的…」。"))
            continue
        for ref in refs:
            if ref >= claim.number:
                issues.append(Issue("C3", "FAIL", loc,
                                     "第{}项引用了第{}项，引用编号必须小于本项编号。".format(claim.number, ref),
                                     "改为引用编号更小的在先权利要求，或调整权利要求排列顺序。"))
                continue
            if ref not in profiles:
                issues.append(Issue("C3", "FAIL", loc,
                                     "第{}项引用的权利要求{}不存在。".format(claim.number, ref),
                                     "核对权利要求编号，删除或修正无效引用。"))
                continue
            ref_subject = profiles[ref]["subject"]
            if not _subject_consistent(profile["subject"], ref_subject):
                issues.append(Issue("C3", "FAIL", loc,
                                     "第{}项主题词「{}」与被引第{}项主题词「{}」不一致。".format(
                                         claim.number, profile["subject"], ref, ref_subject),
                                     "统一两处主题名称用词，同一保护对象在全文须用同一名称。"))
        if len(refs) > 1:
            for ref in refs:
                ref_profile = profiles.get(ref)
                if ref_profile and ref_profile["dependent"] and len(ref_profile["refs"]) > 1:
                    issues.append(Issue("C3", "FAIL", loc,
                                         "第{}项为多引用从权，其引用的第{}项本身也是多引用从权。".format(claim.number, ref),
                                         "多项引用的从属权利要求不得引用另一个多项引用的从属权利要求，请改为引用单一引用权项。"))

    # 星形引用告警：从权数量较多却全部引权1（零链式引用）通常意味着没有做
    # 「我限定的对象由哪条权项引入」的自问（sub-skills/claims 第4节），布局塌平。
    dependents = [profiles[c.number] for c in draft.claims
                  if c.number is not None and profiles[c.number]["dependent"]]
    if len(dependents) >= 5 and all(p["refs"] == [1] for p in dependents):
        issues.append(Issue("C3", "WARN", "权利要求书",
                             "共 {} 条从权全部引用权利要求1，无任何链式引用。".format(len(dependents)),
                             "逐条自问「这条限定的对象是哪条权项引入的」——细化特征（如导向杆之于螺杆、"
                             "触控屏之于玻璃门、数值下探之于上位阈值）应引用引入该对象的从权，形成阶梯。"))
    return issues


METHOD_KEYWORDS = ["步骤", "方法包括", "所述方法", "包括如下步骤", "包括以下步骤"]
METHOD_PATTERNS = [re.compile(r"当[^，。；]{0,30}时(执行|进行|启动|触发)"), re.compile(r"[Ss]\d+\s*[:：、\.]")]


def check_c4(draft: Draft) -> List[Issue]:
    """实用新型客体：权利要求内不得出现方法步骤特征。"""
    issues: List[Issue] = []
    if draft.case_type != "实用新型":
        return issues
    for claim in draft.claims:
        if claim.number is None:
            continue
        hits = [kw for kw in METHOD_KEYWORDS if kw in claim.text]
        hits += [p.pattern for p in METHOD_PATTERNS if p.search(claim.text)]
        if hits:
            issues.append(Issue("C4", "FAIL", "权利要求书 第{}行（第{}项）".format(claim.line_no, claim.number),
                                 "实用新型权利要求不得包含方法步骤特征，命中线索：{}。".format("、".join(hits)),
                                 "将方法性描述改写为结构/构造特征，或将该方案改以发明申请保护。"))
    return issues


def check_c5(draft: Draft) -> List[Issue]:
    """摘要不超过300字；发明名称不超过25字。"""
    issues: List[Issue] = []
    if draft.invention_name is not None and len(draft.invention_name) > 25:
        issues.append(Issue("C5", "FAIL", "案件头/发明名称",
                             "发明名称「{}」共 {} 字，超过 25 字上限。".format(draft.invention_name, len(draft.invention_name)),
                             "精简发明名称，只保留技术主题，去掉效果词、场景词与修饰语。"))
    abstract_text = draft.abstract_text()
    if len(abstract_text) > 300:
        issues.append(Issue("C5", "FAIL", "说明书摘要",
                             "摘要正文共 {} 字，超过 300 字上限。".format(len(abstract_text)),
                             "精简摘要，只保留技术领域、独立权利要求核心方案与主要效果。"))
    return issues


MARKER_CITE_RE = re.compile(r"[（(](\d+)[)）]")
FIGURE_REF_RE = re.compile(r"如\s*图\s*(\d+)\s*所示")
FIGURE_DECL_RE = re.compile(r"图\s*(\d+)\s*(?:是|为)")
# 图号引用可以是列表/区间形式（v7 实测：「如图2和图3所示」「如图1、图2、图3所示」
# 被旧的单图号正则漏计，导致误报"未引用"，豆包实测自行定位了该误报）。
FIGURE_REF_BLOCK_RE = re.compile(r"如\s*((?:图\s*\d+\s*(?:[、，,]|和|与|及|至)?\s*)+)所示")
FIGURE_RANGE_RE = re.compile(r"图\s*(\d+)\s*至\s*图?\s*(\d+)")
FIGURE_NUM_RE = re.compile(r"图\s*(\d+)")


def _extract_figure_refs(text: str) -> set:
    """提取一行文本中「如图…所示」引用到的全部图号（支持顿号/和/与/及列表与「至」区间）。"""
    refs = set()
    for m in FIGURE_REF_BLOCK_RE.finditer(text):
        block = m.group(1)
        for a, b in FIGURE_RANGE_RE.findall(block):
            refs.update(range(int(a), int(b) + 1))
        for n in FIGURE_NUM_RE.findall(block):
            refs.add(int(n))
    return refs


def check_c6(draft: Draft) -> List[Issue]:
    """附图一致性：无图不得引用如图N；标记须在表内；附图说明图号连续。"""
    issues: List[Issue] = []
    spec_lines = draft.all_spec_lines()

    if draft.drawing_mode == "none":
        for line in spec_lines:
            if FIGURE_REF_RE.search(line.text):
                issues.append(Issue("C6", "FAIL", "说明书 第{}行".format(line.no),
                                     "附图状态为「无」，但说明书正文出现附图引用：「{}」。".format(line.text.strip()),
                                     "删除该处「如图N所示」表述，或将附图状态改为「真实附图N幅」/「规划图名N条」并补充附图说明。"))

    if draft.marker_table:
        allowed = set(draft.marker_table.keys())
        for line in spec_lines + draft.claims_body_lines:
            for m in MARKER_CITE_RE.finditer(line.text):
                n = int(m.group(1))
                if n not in allowed:
                    issues.append(Issue("C6", "FAIL", "正文 第{}行".format(line.no),
                                         "正文引用了标记「{}」，但案件头「附图标记表」中未登记该编号。".format(n),
                                         "在案件头附图标记表中补充标记{}的含义，或改正正文中的编号。".format(n)))

    if "附图说明" in draft.spec_sections:
        section = draft.spec_sections["附图说明"]
        numbers = []
        for line in section.lines:
            # 同一图号可能在开头声明句（"图1为已提供的真实附图，图2至图4为规划
            # 图名"）和图名列表中各出现一次——按首次出现去重，只校验顺序与总数
            # （v8 实测：重复计数曾导致顺序/数量误判，豆包被迫改写声明句绕开）。
            for x in FIGURE_DECL_RE.findall(line.text):
                n = int(x)
                if n not in numbers:
                    numbers.append(n)
        # 声明句可能以区间/列表形式提前提及图号（"图2至图3为规划图名"），出现
        # 顺序不可靠——只校验去重后的图号集合从1起连续，不校验行文出现顺序。
        expected = list(range(1, len(numbers) + 1))
        if numbers and sorted(numbers) != expected:
            issues.append(Issue("C6", "FAIL", "说明书/附图说明",
                                 "附图说明中的图号应从图1起连续编号，实际检测到 {}。".format(sorted(numbers)),
                                 "按图1、图2……连续编号，不跳号、不重复。"))
        elif draft.drawing_count and len(numbers) != draft.drawing_count:
            issues.append(Issue("C6", "FAIL", "说明书/附图说明",
                                 "案件头声明附图数量为{}，附图说明中实际列出{}幅。".format(draft.drawing_count, len(numbers)),
                                 "核对案件头「附图状态」与附图说明中列出的图号数量，保持一致。"
                                 "混合状态「真实附图M幅+规划图名N条」的声明总数=M+N，"
                                 "附图说明应把真实图（图1..M）和规划图全部列出。"))

        # 图号引用贯穿检查：声明了附图（真实或规划）却未在实施方式中引用，
        # 会造成图文脱节。既然作者选择保留该图，就必须给出对应正文；不需要的
        # 图应从规划图名中删除，因此这里按 FAIL 阻断。
        if numbers and draft.drawing_mode != "none":
            impl_lines = []
            if "具体实施方式" in draft.spec_sections:
                impl_lines = draft.spec_sections["具体实施方式"].lines
            referenced = set()
            for line in impl_lines:
                referenced |= _extract_figure_refs(line.text)
            if not referenced:
                issues.append(Issue("C6", "FAIL", "说明书/具体实施方式",
                                     "附图说明列出了{}幅图，但具体实施方式中没有任何「如图N所示」引用，正文与附图脱节。".format(len(numbers)),
                                     "主要结构段落以「如图N所示」引出并使用标记表编号（规划附图同样适用，见 sub-skills/specification 第4节）。"))
            else:
                unused = [n for n in numbers if n not in referenced]
                if unused:
                    issues.append(Issue("C6", "FAIL", "说明书/具体实施方式",
                                         "图{}在附图说明中声明，但具体实施方式从未引用。".format("、".join(map(str, unused))),
                                         "为对应结构段落补「如图N所示」引用，或删去多余的规划图名。"))
    return issues


BANNED_EXACT_PHRASES = [
    "有鉴于此，提出本申请",
    "有鉴于此提出本申请",
    "这里将详细地对示例性实施例进行说明",
    "在本申请使用的术语",
    "为了更好地理解上述技术方案",
    "上面结合附图对本申请的实施例进行了描述",
]
REPEAT_PHRASE = "在具体实施过程中"
REPEAT_THRESHOLD = 3
EMPTY_OPENING_RE = re.compile(r"随着.{0,30}?(不断发展|快速发展|飞速发展|日益广泛应用|日益增长|日益普及|逐渐普及)")

# 黑名单第3/7条的同义变体：按句式模式匹配，只扫说明书正文。级别为 WARN 而非
# FAIL——基准标准答案（专家撰写）本身就使用一句式行规免责句（"以上所述仅为…
# 较佳实施例…""应当理解，以下实施方式仅用于说明…"），专家真正否定的是旧版
# skill 的整段模板前言/整段免责（精确短语表继续 FAIL）。告警引导更优写法：
# 点名本案核心特征的实质性范围说明。
# 收尾类免责段：二轮专家评测（2026-07）定性为套话（保护范围由权利要求书确定），
# v14 实测文本规则首轮仅 2/3 执行 → 按 C6 同款打法升 FAIL 硬门禁（生成端可控，删除零代价）。
BANNED_CLOSING_VARIANT_PATTERNS = [
    # 「实施方式」措辞词是 v16 实测逃逸样本（「以上实施方式仅用于说明…」）
    (re.compile(r"以上(所述|各?实施例|实施方式)[^。，]{0,8}仅(为|用[以于](解释|说明))"),
     "填充式结尾免责段（「以上所述/实施方式仅为…」式开头）"),
    (re.compile(r"凡在[^。]{0,15}(精神|原则)[^。]{0,40}(修改|等同替换|改进)"),
     "填充式结尾免责段（「凡在…精神/原则之内…修改/替换」式）"),
    (re.compile(r"(修改|等同替换)[^。]{0,30}不脱离[^。]{0,25}(精神|范围)"),
     "填充式结尾免责段（「修改/替换…不脱离…精神/范围」式）"),
]
# 开场式实施例免责句：一轮专家标准答案自身使用（「以下实施方式仅用于说明…」），
# 二轮专家未否定——保持 WARN 不阻断，两轮校准口径并存。
BANNED_OPENING_VARIANT_PATTERNS = [
    (re.compile(r"仅用[以于](解释|说明)[^。]{0,25}并?不用[以于]限定"),
     "实施例免责开场句（「仅用以解释/说明…并不用于限定」式）"),
]
BANNED_VARIANT_PATTERNS = BANNED_CLOSING_VARIANT_PATTERNS + BANNED_OPENING_VARIANT_PATTERNS


def check_c7(draft: Draft) -> List[Issue]:
    """套话黑名单：命中模板句直接判定失败；重复句式超阈值告警。"""
    issues: List[Issue] = []
    scan_lines = draft.abstract_lines + draft.conclusion_lines + draft.boundary_lines + draft.all_spec_lines()
    for line in scan_lines:
        for phrase in BANNED_EXACT_PHRASES:
            if phrase in line.text:
                issues.append(Issue("C7", "FAIL", "第{}行".format(line.no),
                                     "命中套话黑名单：「{}」。".format(phrase),
                                     "删除该模板化表述，改写为针对本申请技术内容的具体陈述。"))
    repeat_count = sum(line.text.count(REPEAT_PHRASE) for line in scan_lines)
    if repeat_count >= REPEAT_THRESHOLD:
        issues.append(Issue("C7", "WARN", "说明书",
                             "「{}」在全文中出现 {} 次，重复句式较多。".format(REPEAT_PHRASE, repeat_count),
                             "改写部分段落的引导句，避免逐段重复同一模板句式。"))
    for line in scan_lines:
        if EMPTY_OPENING_RE.search(line.text):
            issues.append(Issue("C7", "WARN", "第{}行".format(line.no),
                                 "空洞开篇句式：「随着……发展/普及」类时代背景铺垫。",
                                 "背景技术从具体的现有技术和技术问题写起，删除或改写这句时代背景铺垫。"))
            break
    for line in draft.all_spec_lines():
        matched = False
        for pattern, label in BANNED_CLOSING_VARIANT_PATTERNS:
            if pattern.search(line.text):
                issues.append(Issue("C7", "FAIL", "第{}行".format(line.no),
                                     "收尾免责段：{}。".format(label),
                                     "删除该收尾段——写完发明点即收笔；仅当申请人模板明确要求时，"
                                     "才写点名本案核心特征的实质性范围说明"
                                     "（如「只要采用（本案核心特征组合），均应落入本申请的保护范围」）。"))
                matched = True
                break
        if matched:
            continue
        for pattern, label in BANNED_OPENING_VARIANT_PATTERNS:
            if pattern.search(line.text):
                issues.append(Issue("C7", "WARN", "第{}行".format(line.no),
                                     "通用免责句式：{}（行业惯例，允许保留）。".format(label),
                                     "可保留；不主动新增同类句式。"))
                break
    return issues


ENUM_TRIGGERS = ("包括", "包含", "设有", "设置", "具有")
ENUM_SPLIT_RE = re.compile(r"、|，|,|以及|及|和|与")
ENUM_STOP_RE = re.compile(r"[，,。；;]")


def _build_claim_vocabulary(claims: List[Claim]) -> set:
    """从权利要求「包括/设有…」枚举句中收集可信术语，用于「所述X」定位。"""
    vocab = set()
    for claim in claims:
        text = claim.text
        for trigger in ENUM_TRIGGERS:
            search_from = 0
            while True:
                pos = text.find(trigger, search_from)
                if pos == -1:
                    break
                span_start = pos + len(trigger)
                stop = ENUM_STOP_RE.search(text, span_start)
                span_end = stop.start() if stop else len(text)
                for item in ENUM_SPLIT_RE.split(text[span_start:span_end]):
                    item = item.strip()
                    if "的" in item:
                        item = item.rsplit("的", 1)[-1].strip()
                    if 2 <= len(item) <= 12 and all("一" <= ch <= "鿿" for ch in item):
                        vocab.add(item)
                search_from = pos + len(trigger)
    return vocab


def _referenced_terms(text: str, vocab: set) -> List[str]:
    terms = []
    for m in re.finditer("所述", text):
        tail = text[m.end():]
        candidates = [term for term in vocab if tail.startswith(term)]
        if candidates:
            terms.append(max(candidates, key=len))
    return terms


def check_c8(draft: Draft) -> List[Issue]:
    """术语一致性：权利要求中「所述X」提取的名词短语必须在说明书中出现。"""
    issues: List[Issue] = []
    if not draft.claims:
        return issues
    vocab = _build_claim_vocabulary(draft.claims)
    if not vocab:
        return issues
    spec_text = draft.spec_full_text()
    first_seen: Dict[str, int] = {}
    for claim in draft.claims:
        for term in _referenced_terms(claim.text, vocab):
            if term not in first_seen:
                first_seen[term] = claim.line_no
    for term, line_no in sorted(first_seen.items(), key=lambda kv: kv[1]):
        if term not in spec_text:
            issues.append(Issue("C8", "FAIL", "权利要求书 第{}行起使用「{}」".format(line_no, term),
                                 "权利要求中的术语「{}」未在说明书正文中出现。".format(term),
                                 "在说明书（发明内容或具体实施方式）中补充对「{}」的描述，或统一为说明书中已使用的名称。".format(term)))
    return issues


PENDING_REF_RE = re.compile(r"待确认事项\s*(\d+)")


def check_c9(draft: Draft) -> List[Issue]:
    """待确认联动：正文引用「待确认事项N」时，审阅说明须存在对应条目。"""
    issues: List[Issue] = []
    total = len(draft.pending_items)
    for line in draft.abstract_lines + draft.all_spec_lines():
        for m in PENDING_REF_RE.finditer(line.text):
            n = int(m.group(1))
            if n < 1 or n > total:
                issues.append(Issue("C9", "FAIL", "第{}行".format(line.no),
                                     "正文引用「待确认事项{}」，但审阅说明的待确认事项列表共有{}条，不存在第{}条。".format(n, total, n),
                                     "在审阅说明「待确认事项」中补充对应条目，或修正正文中的编号。"))
    return issues


def _invention_subject(name: str) -> str:
    name = name.strip()
    if name.startswith("一种"):
        name = name[2:]
    if "及其" in name:
        name = name.split("及其")[0]
    return name.strip()


def check_c10(draft: Draft) -> List[Issue]:
    """摘要与权1主题词一致：发明名称主题须出现在摘要中。"""
    issues: List[Issue] = []
    if not draft.invention_name:
        return issues
    subject = _invention_subject(draft.invention_name)
    if subject and subject not in draft.abstract_text():
        issues.append(Issue("C10", "FAIL", "说明书摘要",
                             "摘要中未出现发明名称主题词「{}」。".format(subject),
                             "在摘要开头点明该主题词，例如「本申请公开一种{}，……」。".format(subject)))
    return issues


def check_c11(draft: Draft) -> List[Issue]:
    """散文区 Markdown 残留：命中裸标记判定 WARN（渲染层已自动清理，不阻断构建）。"""
    issues: List[Issue] = []

    def scan(location_prefix: str, lines: List[Line]) -> None:
        for line in lines:
            stripped = line.text.strip()
            if not stripped:
                continue
            _, hits = normalize_prose_markdown(stripped)
            if not hits:
                continue
            labels = "、".join(MD_HIT_LABELS[h] for h in hits)
            issues.append(Issue("C11", "WARN", "{} 第{}行".format(location_prefix, line.no),
                                 "散文文本残留裸 Markdown 标记：{}（原文：「{}」），"
                                 "已在生成 docx 时自动清理为纯文本。".format(labels, stripped),
                                 "下次直接撰写不含 Markdown 标记的纯文本陈述，删除{}等符号。".format(labels)))

    scan("审阅说明/撰写结论", draft.conclusion_lines)
    scan("审阅说明/边界与免责", draft.boundary_lines)
    scan("说明书摘要", draft.abstract_lines)
    for title in draft.spec_h2_order:
        section = draft.spec_sections.get(title)
        if section:
            scan("说明书/{}".format(title), section.lines)

    for idx, item in enumerate(draft.pending_items, 1):
        combined = "{}：{}".format(item.event, item.impact) if item.impact else item.event
        _, hits = normalize_prose_markdown(combined)
        if not hits:
            continue
        labels = "、".join(MD_HIT_LABELS[h] for h in hits)
        issues.append(Issue("C11", "WARN", "审阅说明/待确认事项 第{}行（第{}条）".format(item.line_no, idx),
                             "散文文本残留裸 Markdown 标记：{}（原文：「{}」），"
                             "已在生成 docx 时自动清理为纯文本。".format(labels, combined),
                             "下次直接撰写不含 Markdown 标记的纯文本陈述，删除{}等符号。".format(labels)))
    return issues


_CLAUSE_SPLIT_RE = re.compile(r"[。；]")
_DEP_CLAIM_PREFIX_STRIP_RE = re.compile(
    r"^根据权利要求[0-9、，,至或任一项中\s]+?所述的[^，,。；;]+[，,]\s*其特征在于[，,]\s*")
_SPEC_LEADIN_STRIP_RE = re.compile(r"^(?:进一步地|进一步|此外|另外|优选地|作为优选)[，,、]\s*")
C12_CLAUSE_MIN_LEN = 25
C12_FAIL_RATIO = 0.60
C12_WARN_RATIO = 0.30


def _split_clauses(text: str) -> List[str]:
    """按中文句号、分号把一段正文切分为子句（去除切分符本身，过滤空白子句）。"""
    return [c.strip() for c in _CLAUSE_SPLIT_RE.split(text) if c.strip()]


def _strip_dependent_claim_prefix(clause: str) -> str:
    """剥离从权引用前缀「根据权利要求N所述的…，其特征在于，」；独立权利要求
    的子句不含该前缀，原样返回（其中段的「其特征在于，」不属于可剥离的引用
    前缀，保留不动，属保守处理，宁可放过不误判）。"""
    return _DEP_CLAIM_PREFIX_STRIP_RE.sub("", clause, count=1).strip()


def _strip_spec_leadin(clause: str) -> str:
    """剥离发明内容/实用新型内容侧「进一步地/此外/另外」等引导词，使其与从权
    剥离前缀后的子句在同一基准上比较，避免结构相似（都是"追加一个特征"的
    引导句）但内容不同时被误判为照抄。"""
    return _SPEC_LEADIN_STRIP_RE.sub("", clause, count=1).strip()


def check_c12(draft: Draft) -> List[Issue]:
    """发明内容/实用新型内容整句照抄权利要求检测（详见模块头部补充约定说明）。

    命中判定要求剥离各自的引用前缀/引导词后逐字完全一致，结构相似但内容不同
    的子句不计入命中；命中比例 ≥60% 判 FAIL，30%~60% 判 WARN，<30% 不报。
    """
    issues: List[Issue] = []
    if draft.case_type not in CONTENT_TITLE_BY_CASE_TYPE or not draft.claims:
        return issues
    content_title = CONTENT_TITLE_BY_CASE_TYPE[draft.case_type]
    section = draft.spec_sections.get(content_title)
    if section is None:
        return issues

    spec_clauses = set()
    for raw in _split_clauses(section.text()):
        normed = _strip_spec_leadin(raw)
        if normed:
            spec_clauses.add(normed)
    if not spec_clauses:
        return issues

    total = 0
    hits: List[Tuple[int, str]] = []
    for claim in draft.claims:
        if claim.number is None:
            continue
        for raw in _split_clauses(claim.text):
            if len(raw) < C12_CLAUSE_MIN_LEN:
                continue
            total += 1
            normed = _strip_dependent_claim_prefix(raw)
            if normed and normed in spec_clauses:
                hits.append((claim.number, raw))
    if total == 0:
        return issues

    ratio = len(hits) / total
    if ratio < C12_WARN_RATIO:
        return issues
    severity = "FAIL" if ratio >= C12_FAIL_RATIO else "WARN"

    examples = "；".join(
        "第{}项「{}…」".format(number, raw[:40]) for number, raw in hits[:3])
    problem = (
        "「{}」正文与权利要求书存在整句照抄：命中 {}/{} 条权利要求子句（{:.0%}），"
        "示例：{}。".format(content_title, len(hits), total, ratio, examples))
    if severity == "FAIL":
        fix = "发明内容大段照抄权利要求原文，需以陈述句改写并加连接语。"
    else:
        fix = "「{}」中与权利要求高度重合的表述建议改写为陈述句并补充连接语，降低整句照抄比例。".format(
            content_title)
    issues.append(Issue("C12", severity, "说明书/{}".format(content_title), problem, fix))
    return issues


C13_BANNED_TOKENS = [
    "patent_build.py",
    "draft.md",
    "SKILL.md",
    "sub-skills",
    "writing-style.md",
    "doubao-patent-drafting",
    "PATENT_BUILD:",
    "selftest",
    "修稿报告",
    "本技能",
    "P0",
    "P1",
    "A级",
    "B级",
    "C级",
    "D级",
    "主链",
    "相邻业务",
    "门禁足迹",
]

# 裸词补充拦截：v5 实测 T1 审阅说明三次自称「本skill」——词表里只有带扩展名/
# 路径的文件名挡不住内部称谓。专利交付物里出现英文 skill / 「技能包」没有正当
# 场景（对外应自称「本次撰写服务 / 本文件」），大小写不敏感整词命中即 FAIL。
C13_EXTRA_RE = re.compile(r"skill|技能包", re.IGNORECASE)


def check_c13(draft: Draft) -> List[Issue]:
    """内部工具名泄漏：法律文书正文不得出现本 skill 的内部工具/文件名痕迹
    （详见模块头部补充约定说明）。

    扫描范围＝将渲染进 docx 的全部正文文本：审阅说明（撰写结论/待确认事项/
    边界与免责）、说明书摘要、权利要求书、说明书各节正文。案件头字段行不
    在扫描范围内——字段取值合法性另由 C1/C5 等检查覆盖，不与本检查重复。
    命中词表（C13_BANNED_TOKENS）任一子串即判定为 FAIL，不设 WARN 降级。
    """
    issues: List[Issue] = []

    def scan(location: str, text: str) -> None:
        hit_tokens = [token for token in C13_BANNED_TOKENS if token in text]
        for token in hit_tokens:
            issues.append(Issue(
                "C13", "FAIL", location,
                "正文出现内部工具/文件名「{}」，法律文书不得包含撰写工具痕迹，"
                "请改写为面向申请人的自然表述。".format(token),
                "删除或改写该处表述，不得提及撰写本文件所用的工具、脚本或内部文件名。"))
        if not any("skill" in token.lower() for token in hit_tokens):
            m = C13_EXTRA_RE.search(text)
            if m:
                issues.append(Issue(
                    "C13", "FAIL", location,
                    "正文出现内部称谓「{}」，交付物不得自称 skill / 技能包。".format(m.group(0)),
                    "改写为面向申请人的自然表述，如「本次撰写服务」「本文件」。"))

    for line in draft.conclusion_lines:
        stripped = line.text.strip()
        if stripped:
            scan("审阅说明/撰写结论 第{}行".format(line.no), stripped)
    for line in draft.boundary_lines:
        stripped = line.text.strip()
        if stripped:
            scan("审阅说明/边界与免责 第{}行".format(line.no), stripped)
    for idx, item in enumerate(draft.pending_items, 1):
        combined = "{}：{}".format(item.event, item.impact) if item.impact else item.event
        scan("审阅说明/待确认事项 第{}行（第{}条）".format(item.line_no, idx), combined)
    for line in draft.abstract_lines:
        stripped = line.text.strip()
        if stripped:
            scan("说明书摘要 第{}行".format(line.no), stripped)
    for title in draft.spec_h2_order:
        section = draft.spec_sections.get(title)
        if not section:
            continue
        for line in section.lines:
            stripped = line.text.strip()
            if stripped:
                scan("说明书/{} 第{}行".format(title, line.no), stripped)
    for claim in draft.claims:
        if claim.number is None:
            continue
        scan("权利要求书 第{}行（第{}项）".format(claim.line_no, claim.number), claim.text)

    return issues


C14_STRONG_WORDS = ["显著", "彻底", "大幅", "杜绝", "永久", "完全", "100%", "根本上解决", "最优"]
C14_TEST_CLAIM_RE = re.compile(r"经测试|实测|经验证|测试表明|数据显示")
C14_TEST_EVIDENCE_RE = re.compile(r"测试|实测|检测|试验")


def check_c14(draft: Draft) -> List[Issue]:
    """摘要越级词比对：摘要是发明内容的派生压缩，不得出现正文没有的强效果词
    （本脚本的补充约定，非设计文档条款）。

    比对基准＝发明内容/实用新型内容一节；该节缺失时退回全部说明书正文（宁可
    少报不误报）。词表与 references/writing-style.md 措辞分寸表的 A 级/禁用词
    同源。注意本检查只守「摘要单方面升格」：正文和摘要一起用错级别属于语义级
    越级，机器判不了，由派生式写作流程与交付前找茬负责。
    """
    issues: List[Issue] = []
    abstract = "".join(l.text for l in draft.abstract_lines)
    if not abstract.strip():
        return issues
    body_section = None
    if draft.case_type in CONTENT_TITLE_BY_CASE_TYPE:
        body_section = draft.spec_sections.get(CONTENT_TITLE_BY_CASE_TYPE[draft.case_type])
    body = body_section.text() if body_section is not None else "".join(
        l.text for l in draft.all_spec_lines())
    for word in C14_STRONG_WORDS:
        if word in abstract and word not in body:
            issues.append(Issue(
                "C14", "FAIL", "说明书摘要",
                "摘要出现强效果词「{}」，但发明内容/实用新型内容正文未出现同词——"
                "摘要是正文的压缩，不得单方面升格措辞。".format(word),
                "删除该词或降级为与正文同级的表述（能够/有利于）；如确有实测依据，"
                "先把该表述连同依据写入发明内容的有益效果段，再回到摘要引用。"))
    if C14_TEST_CLAIM_RE.search(abstract) and not C14_TEST_EVIDENCE_RE.search(body):
        issues.append(Issue(
            "C14", "FAIL", "说明书摘要",
            "摘要声称「经测试/实测/经验证」，但发明内容正文没有任何测试相关表述。",
            "删除测试断言，或先在发明内容的有益效果段写明测试依据。"))
    return issues


C15_CONNECTOR_STRIP_RE = re.compile(r"^(如|和|与|及|或|至|所述|该|上述|每层|各|其|另|即)+")
C15_PREFIX_BLACKLIST_RE = re.compile(r"(图|表|式|第|权利要求|实施例|对比例|样机|附件|阈值|步骤)$")
C15_NAME_WINDOW_RE = re.compile(r"([一-龥]{1,10})(\d{1,4})(?![\d\.．%~～\-—a-zA-Z℃°])")


def check_c15(draft: Draft) -> List[Issue]:
    """标记对位检查：正文「部件名+标记号」与案件头附图标记表双向核对
    （v7 实测事故：正文「水泵410」而标记表 410=水箱、411=水泵——名称与编号张冠李戴，
    C6 只查编号是否登记、查不出对应关系漂移）。

    保守分级：全部 WARN 不阻断——中文前缀切分存在歧义，误报 FAIL 会卡死构建；
    豆包已实证会逐条处理告警（v7 T2 两轮告警循环）。仅当编号在标记表中登记时才判定。
    """
    issues: List[Issue] = []
    if not draft.marker_table:
        return issues
    name_by_num = {n: str(name) for n, name in draft.marker_table.items()}
    nums_by_name = {}
    for n, name in name_by_num.items():
        nums_by_name.setdefault(name, set()).add(n)

    scan_lines = draft.all_spec_lines() + draft.claims_body_lines
    reported = set()
    for line in scan_lines:
        for m in C15_NAME_WINDOW_RE.finditer(line.text):
            window, num_s = m.group(1), m.group(2)
            if m.start() > 0 and line.text[m.start() - 1].isdigit():
                continue
            num = int(num_s)
            if num not in name_by_num:
                continue
            token = C15_CONNECTOR_STRIP_RE.sub("", window)
            if not token or C15_PREFIX_BLACKLIST_RE.search(window):
                continue
            registered = name_by_num[num]
            if registered in token or token in registered:
                continue
            key = ("num", num, token[-6:])
            if key in reported:
                continue
            reported.add(key)
            issues.append(Issue(
                "C15", "WARN", "正文 第{}行".format(line.no),
                "标记{}在标记表中登记为「{}」，正文此处写作「{}{}」——名称与编号可能张冠李戴。".format(
                    num, registered, token[-6:], num),
                "核对该处：改用正确编号（如「{}」对应的编号），或修正标记表。".format(token[-6:])))
        for name, nums in nums_by_name.items():
            # 前置负查找：防止短名称在长名称内部误匹配（v8 实测误报：「主出水管406」
            # 命中了登记名「出水管」——名称前一个字是汉字说明它只是长名的一部分）。
            for m in re.finditer(r"(?<![一-龥])" + re.escape(name) + r"(\d{1,4})(?![\d\.．%~～\-—a-zA-Z℃°])", line.text):
                num = int(m.group(1))
                if num in nums or num not in name_by_num:
                    continue
                key = ("name", name, num)
                if key in reported:
                    continue
                reported.add(key)
                issues.append(Issue(
                    "C15", "WARN", "正文 第{}行".format(line.no),
                    "「{}」在标记表中登记为{}，正文此处却写作「{}{}」（{}登记为「{}」）。".format(
                        name, "、".join(map(str, sorted(nums))), name, num, num, name_by_num[num]),
                    "核对该处编号是否笔误，与标记表保持一致。"))
    return issues


FORMULA_SYMBOL_RE = re.compile(r"(?<![A-Za-z0-9_])((?:Δ)?[A-Za-z][A-Za-z0-9_]*)(?![A-Za-z0-9_])")
SYMBOL_DEFINITION_RE = re.compile(
    r"(?<![A-Za-z0-9_])((?:Δ)?[A-Za-z][A-Za-z0-9_]*)\s*(?:为|：|:)")
FORMULA_LINE_RE = re.compile(r"[=＝×÷]|[|｜][^|｜]+[|｜]|[≤≥]")
# 未定义符号只在真公式行（含等号或绝对值围栏）追查——v16 实测「×」尺寸行、
# 「≤」规格行把 Cortex/Flash/型号字母卷进误报，导致 13 轮修稿缠斗
FORMULA_EQUATION_LINE_RE = re.compile(r"[=＝]|[|｜][^|｜]+[|｜]")
FORMULA_UNIT_TOKENS = {"mm", "cm", "m", "km", "ms", "s", "min", "h", "MPa", "Pa", "kPa", "dB"}


def _canonical_symbol(symbol: str) -> str:
    return symbol.replace("_", "")


# 形状/规格代号后缀：「L型支架」「S形水道」「M8号」是机械案标准行文，字母不是公式变量。
# v11 实测误报：尺寸「100×200mm」的 × 使整行被判为公式行，同行的 L/S 被当成未定义符号。
SHAPE_SUFFIX_CHARS = "型形号级系"


def _looks_like_formula_symbol(symbol: str) -> bool:
    if symbol in FORMULA_UNIT_TOKENS:
        return False
    if len(symbol) > 1 and symbol.isupper():
        return False
    return "_" in symbol or symbol.startswith("Δ") or len(symbol) == 1 or any(ch.islower() for ch in symbol)


CJK_RE = re.compile(r"[一-鿿]")


def _iter_formula_symbols(text: str):
    """产出正文里疑似公式变量的符号。两类误报排除（v12 实测校准）：
    ①形状/规格代号：字母后紧跟型/形/号等（「L型支架」「S形水道」）；
    ②编号代称：汉字紧跟的单个大写字母（「样机A」「方案B」）——真正的公式
    变量前面是运算符/标点/空白，不会直接嵌在词语里。"""
    for match in FORMULA_SYMBOL_RE.finditer(text):
        symbol = match.group(1)
        nxt = text[match.end():match.end() + 1]
        if nxt and nxt in SHAPE_SUFFIX_CHARS:
            continue
        prev = text[match.start() - 1:match.start()] if match.start() > 0 else ""
        if len(symbol) == 1 and symbol.isupper() and prev and CJK_RE.match(prev):
            continue
        if _looks_like_formula_symbol(symbol):
            yield symbol


def check_c16(draft: Draft) -> List[Issue]:
    """公式符号一致性：同一符号只允许一种写法，运算式中的变量必须有定义。"""
    issues: List[Issue] = []
    lines = draft.claims_body_lines + draft.all_spec_lines()
    definitions: Dict[str, set] = {}
    usages: Dict[str, set] = {}

    # 第一遍：先收齐全部符号定义（「X为…」），供第二遍的长词过滤参照
    for line in lines:
        for match in SYMBOL_DEFINITION_RE.finditer(line.text):
            symbol = match.group(1)
            if _looks_like_formula_symbol(symbol):
                definitions.setdefault(_canonical_symbol(symbol), set()).add(symbol)

    equation_usages: Dict[str, set] = {}
    for line in lines:
        if not FORMULA_LINE_RE.search(line.text):
            continue
        is_equation = bool(FORMULA_EQUATION_LINE_RE.search(line.text))
        for symbol in _iter_formula_symbols(line.text):
            canonical = _canonical_symbol(symbol)
            # 型号/器件名（Cortex、Flash 等 ≥5 位纯英文词）不是公式变量——
            # v16 实测误报致 13 轮修稿缠斗。例外：与某个已定义符号同规范形的
            # 长词（Tliquid vs T_liquid）正是变体检测的目标，必须保留。
            if (len(symbol) >= 5 and "_" not in symbol and not symbol.startswith("Δ")
                    and canonical not in definitions):
                continue
            usages.setdefault(canonical, set()).add(symbol)
            if is_equation:
                equation_usages.setdefault(canonical, set()).add(symbol)

    for canonical in sorted(set(definitions) | set(usages)):
        variants = definitions.get(canonical, set()) | usages.get(canonical, set())
        if len(variants) > 1:
            issues.append(Issue(
                "C16", "FAIL", "说明书/公式与符号",
                "同一符号存在多种写法，写法不一致：{}。".format("、".join(sorted(variants))),
                "选择一种写法，并同步修改符号表、公式、权利要求和实施例中的全部出现位置。"))

    # 未定义追查只看真公式行（=/绝对值围栏）：×尺寸行、≤规格行里的字母
    # 多为型号代称，v16 实测按全部公式标记行追查造成大量误报
    undefined = []
    for canonical, variants in equation_usages.items():
        if canonical not in definitions:
            undefined.extend(sorted(variants))
    if undefined:
        issues.append(Issue(
            "C16", "FAIL", "说明书/公式与符号",
            "公式或运算表达式使用了未定义符号：{}。".format("、".join(sorted(set(undefined)))),
            "在第一个公式之前的符号说明中补充同形定义，或删除未使用的符号。"))
    return issues


def check_c17(draft: Draft) -> List[Issue]:
    """附图标记完整性：名称不重复占用多个编号，每个编号都在技术正文中使用。"""
    issues: List[Issue] = []
    if not draft.marker_table:
        return issues

    nums_by_name: Dict[str, List[int]] = {}
    for number, name in draft.marker_table.items():
        nums_by_name.setdefault(name, []).append(number)
    for name, numbers in sorted(nums_by_name.items()):
        if len(numbers) > 1:
            issues.append(Issue(
                "C17", "FAIL", "案件头/附图标记表",
                "部件名称「{}」被多个编号重复使用：{}。".format(
                    name, "、".join(map(str, sorted(numbers)))),
                "同一部件统一使用一个编号；若实际为不同部件，分别使用能区分的准确名称。"))

    body_lines = list(draft.claims_body_lines)
    for title in draft.spec_h2_order:
        if title == "附图说明":
            continue
        section = draft.spec_sections.get(title)
        if section:
            body_lines.extend(section.lines)
    body = "\n".join(line.text for line in body_lines)

    for number, name in sorted(draft.marker_table.items()):
        exact = re.compile(re.escape(name) + r"\s*" + str(number) + r"(?!\d)")
        parenthesized = re.compile(r"[（(]" + str(number) + r"[)）]")
        if not exact.search(body) and not parenthesized.search(body):
            issues.append(Issue(
                "C17", "FAIL", "案件头/附图标记表",
                "标记{}（{}）只在标记表或附图说明中出现，技术正文未使用。".format(number, name),
                "在具体实施方式中以“部件名称+编号”说明其结构和关系，或删除多余标记。"))
    return issues


# v11 实测漏洞修复：触发词表原来只认「待确认/尚未…」等被动措辞，执行者把待确认事项
# 写成「请逐项确认实测状态」（v10-T2 豆包原话）就静默绕过——把「请/需…确认…实测」
# 这类主动句式一并纳入触发。
C18_PENDING_EVIDENCE_RE = re.compile(
    r"(?:实测|测试|试验|验证|性能|指标|效果|数据).{0,30}(?:待确认|未确认|尚未|缺失|待补|待提供|待验证)"
    r"|(?:待确认|未确认|尚未|缺失|待补|待提供).{0,30}(?:实测|测试|试验|验证|性能|指标|效果|数据)"
    r"|(?:请|需要?)[^。；\n]{0,12}确认[^。；\n]{0,24}(?:实测|测试|试验|验证|性能|指标|数据|效果)"
    r"|确认[^。；\n]{0,10}(?:实测|测试|试验)状态"
    # v12 实测逃逸（T2）：「未明确说明是否已完成样机测试验证」「按设计目标口径撰写」
    r"|是否已?(?:完成|进行|开展)[^。；\n]{0,10}(?:实测|测试|试验|验证)"
    r"|(?:实测|测试|试验|验证)[^。；\n]{0,10}(?:状态|情况)[^。；\n]{0,14}(?:未明确|未说明|不明确|待明确)"
    r"|按设计目标口径")
C18_STRONG_CLAIMS = ["明显优于", "优于传统", "从根本上解决", "有效解决", "彻底解决", "显著优于"]
# 同行证据豁免：v11 实测 T2 用「测试表明，…偏差不超过1摄氏度」引 A 级数据，
# 原豁免表不含「测试表明」会误拦——补齐常见引据句式。
C18_SAME_LINE_EVIDENCE_RE = re.compile(
    r"(?:经测试|经实测|测试表明|实测表明|试验表明|实测数据|测试数据|数据显示|试验结果|检测结果|实测结果).{0,100}\d")


def check_c18(draft: Draft) -> List[Issue]:
    """证据闭环：测试或性能状态尚未确认时，不得在申请人可见文本中下强结论。"""
    pending_text = "\n".join(
        "{}：{}".format(item.event, item.impact) for item in draft.pending_items)
    if not C18_PENDING_EVIDENCE_RE.search(pending_text):
        return []

    scan: List[Tuple[str, Line]] = []
    scan.extend(("审阅说明/撰写结论", line) for line in draft.conclusion_lines)
    scan.extend(("说明书摘要", line) for line in draft.abstract_lines)
    for title in ("发明内容", "实用新型内容", "具体实施方式"):
        section = draft.spec_sections.get(title)
        if section:
            scan.extend(("说明书/{}".format(title), line) for line in section.lines)

    issues: List[Issue] = []
    for location, line in scan:
        if C18_SAME_LINE_EVIDENCE_RE.search(line.text):
            continue
        for phrase in C18_STRONG_CLAIMS:
            if phrase in line.text:
                issues.append(Issue(
                    "C18", "FAIL", "{} 第{}行".format(location, line.no),
                    "测试或性能状态仍待确认，但本处使用强结论「{}」。".format(phrase),
                    "改为“能够/有利于/设计目标为/尚待验证”等与证据状态相符的表达；"
                    "如已有测试依据，先补充测试条件和数据并移除对应待确认事项。"))
    return issues


SUBJECT_PHRASE_RE = re.compile(r"^一种(.{1,40}?)(?:，|,|其特征|包括)")


def check_c19(draft: Draft) -> List[Issue]:
    """主题实体一致性（v15 实测回摆蒸馏）：主题被构思措辞带偏成「…结构/装置」
    是 v7 与 v15 两次实测的同款事故，文本重申无效——改为构造式：阶段一按
    整机口径登记「主题实体」，发明名称与权利要求1主题必须以登记值结尾。"""
    issues: List[Issue] = []
    entity = (draft.subject_entity or "").strip()
    if not entity:
        return issues  # 字段缺失由 C1 报
    name = (draft.invention_name or "").strip()
    if name:
        name_base = re.sub(r"及其.{0,14}$", "", name)  # 「…及其控制方法」双主题合法
        if not name_base.endswith(entity):
            issues.append(Issue(
                "C19", "FAIL", "案件头/发明名称",
                "发明名称「{}」未以主题实体「{}」结尾。".format(name, entity),
                "发明名称=修饰语+主题实体（可后接「及其…方法」）；"
                "确需变更主题时先改案件头「主题实体」登记值，再同步名称与权利要求。"))
    if draft.claims:
        first = draft.claims[0].text.strip()
        m = SUBJECT_PHRASE_RE.match(first)
        if m and not m.group(1).strip().endswith(entity):
            issues.append(Issue(
                "C19", "FAIL", "权利要求书/权利要求1",
                "权利要求1主题「一种{}」未以主题实体「{}」结尾——主题被限定语或构思措辞"
                "带偏（如以「…结构/装置」替代了整机）。".format(m.group(1).strip(), entity),
                "权利要求1主题名称照抄主题实体（前可加修饰语）；"
                "确需变更主题时先改案件头登记值并复核整机口径。"))
    return issues


C20_DEP_REF_RE = re.compile(r"^根据权利要求(\d+)所述")
SIMPLE_ALT_FEATURE_RE = re.compile(r"其特征在于[，,]?\s*所述([^，。]{1,12}?)(?:为|包括)([^。]+)。?\s*$")


def check_c20(draft: Draft) -> List[Issue]:
    """对偶实现拆条提示（v15 实测回摆蒸馏）：同一被引权项下、同一主语的多条
    单句从权（「所述X为/包括…」）应考虑合并为择一从权——专家标准答案通行
    写法，条数省一半、保护范围相同。WARN 不阻断（各自挂有下级细化从权时拆开合法）。"""
    groups: Dict[Tuple[str, str], List[Claim]] = {}
    for c in draft.claims:
        mref = C20_DEP_REF_RE.match(c.text.strip())
        if not mref:
            continue
        mfeat = SIMPLE_ALT_FEATURE_RE.search(c.text)
        if not mfeat:
            continue
        groups.setdefault((mref.group(1), mfeat.group(1)), []).append(c)
    issues: List[Issue] = []
    for (ref, subj), cs in sorted(groups.items()):
        if len(cs) >= 2:
            nums = "、".join(str(c.number) for c in cs)
            issues.append(Issue(
                "C20", "WARN", "权利要求书",
                "权利要求{}都在限定「所述{}」的实现形式（均引用权利要求{}），"
                "属对偶实现拆条。".format(nums, subj, ref),
                "合并为一条择一从权（如「所述{}包括A和B中的至少一种」），"
                "除非各自还挂有下级细化从权需要独立引用锚点。".format(subj)))
    return issues


ALL_CHECKS = [
    ("C1", check_c1), ("C2", check_c2), ("C3", check_c3), ("C4", check_c4), ("C5", check_c5),
    ("C6", check_c6), ("C7", check_c7), ("C8", check_c8), ("C9", check_c9), ("C10", check_c10),
    ("C11", check_c11), ("C12", check_c12), ("C13", check_c13), ("C14", check_c14), ("C15", check_c15),
    ("C16", check_c16), ("C17", check_c17), ("C18", check_c18), ("C19", check_c19), ("C20", check_c20),
]


def run_all_checks(draft: Draft) -> List[Issue]:
    issues: List[Issue] = []
    for _, fn in ALL_CHECKS:
        issues.extend(fn(draft))
    return issues


# =====================================================================
# 第三段：docx 生成（原生 OOXML，无第三方依赖）
# =====================================================================

FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"


class FigureResourceError(ValueError):
    pass


def _xml_text(value: str) -> str:
    return (value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _xml_attr(value: str) -> str:
    return _xml_text(value).replace('"', "&quot;")


def _sniff_image(payload: bytes) -> Optional[Tuple[str, int, int]]:
    """最小 PNG/JPEG 尺寸探测，仅用于确认格式并计算嵌入版式，不做完整校验。"""
    if payload[:8] == b"\x89PNG\r\n\x1a\n":
        if len(payload) >= 24 and payload[12:16] == b"IHDR":
            w, h = struct.unpack(">II", payload[16:24])
            return "png", w, h
        return None
    if payload[:2] == b"\xff\xd8":
        i, n = 2, len(payload)
        while i + 4 <= n:
            if payload[i] != 0xFF:
                i += 1
                continue
            marker = payload[i + 1]
            i += 2
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                continue
            if marker == 0xD9:
                break
            if i + 2 > n:
                break
            length = struct.unpack(">H", payload[i:i + 2])[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                if i + 7 <= n:
                    h, w = struct.unpack(">HH", payload[i + 3:i + 7])
                    return "jpeg", w, h
                break
            i += length
        return None
    return None


def _find_figure_file(figures_dir: Path, n: int) -> Optional[Path]:
    for ext in ("png", "jpg", "jpeg", "PNG", "JPG", "JPEG"):
        candidate = figures_dir / "{}.{}".format(n, ext)
        if candidate.is_file():
            return candidate
    if figures_dir.is_dir():
        for candidate in sorted(figures_dir.iterdir()):
            stem = candidate.stem
            if stem in ("图{}".format(n), "fig{}".format(n), "figure{}".format(n)):
                return candidate
    return None


def check_figure_resources(draft: Draft, figures_dir: Path) -> List[Issue]:
    """附图资源检查：声明真实附图（含混合状态的真实部分）时，图片文件必须存在且可识别。"""
    issues: List[Issue] = []
    if draft.real_figure_count <= 0:
        return issues
    if not figures_dir.is_dir():
        issues.append(Issue("资源", "FAIL", "附图文件",
                             "案件头声明真实附图{}幅，但未找到附图目录：{}。".format(draft.real_figure_count, figures_dir),
                             "在 draft.md 同级创建 figures/ 目录，将附图另存为 1.png、2.png……（或 .jpg），数量与案件头声明一致后重新构建。"))
        return issues
    for n in range(1, draft.real_figure_count + 1):
        path = _find_figure_file(figures_dir, n)
        if path is None:
            issues.append(Issue("资源", "FAIL", "附图文件",
                                 "未在 {} 找到图{}对应的图片文件。".format(figures_dir, n),
                                 "将图{n}另存为 {dir}/{n}.png 或 {dir}/{n}.jpg。".format(n=n, dir=figures_dir)))
            continue
        payload = path.read_bytes()
        if _sniff_image(payload) is None:
            issues.append(Issue("资源", "FAIL", "附图文件",
                                 "文件 {} 不是可识别的 PNG/JPEG 图片。".format(path),
                                 "确认该文件是未损坏的 PNG 或 JPEG 格式。"))
    return issues


def _paragraph(text: str, style: str, bold: bool = False, page_break: bool = False,
               drawing_xml: str = "") -> str:
    props = '<w:pPr><w:pStyle w:val="{}"/>'.format(_xml_attr(style))
    if page_break:
        props += "<w:pageBreakBefore/>"
    props += "</w:pPr>"
    run_props = "<w:rPr><w:b/></w:rPr>" if bold else ""
    runs = drawing_xml
    if text:
        preserve = ' xml:space="preserve"' if text[:1].isspace() or text[-1:].isspace() else ""
        runs += "<w:r>{}<w:t{}>{}</w:t></w:r>".format(run_props, preserve, _xml_text(text))
    return "<w:p>{}{}</w:p>".format(props, runs)


def _page_number_footer_xml() -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:ftr xmlns:w="{w}"><w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
        '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        '<w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        '<w:r><w:t>1</w:t></w:r>'
        '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
        '</w:p></w:ftr>'
    ).format(w=W_NS).encode("utf-8")


def _inline_drawing(rel_id: str, docpr_id: int, width_px: int, height_px: int, caption: str) -> str:
    max_width, max_height = 6 * 914400, 8 * 914400
    width_px, height_px = max(width_px, 1), max(height_px, 1)
    width_emu, height_emu = width_px * 9525, height_px * 9525  # 像素 -> EMU，按 96dpi 近似
    scale = min(max_width / float(width_emu), max_height / float(height_emu), 1.0)
    cx, cy = int(width_emu * scale), int(height_emu * scale)
    if cx <= 0 or cy <= 0:
        cx, cy = max_width, max_height
    return (
        '<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
        '<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{docpr}" name="Drawing{docpr}" descr="{caption}"/>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic><pic:nvPicPr><pic:cNvPr id="0" name="Drawing{docpr}"/><pic:cNvPicPr/></pic:nvPicPr>'
        '<pic:blipFill><a:blip r:embed="{rel}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>'
        '</a:graphicData></a:graphic></wp:inline></w:drawing></w:r>'
    ).format(cx=cx, cy=cy, docpr=docpr_id, caption=_xml_attr(caption), rel=_xml_attr(rel_id))


def _styles_xml() -> bytes:
    body_rpr = ('<w:rPr><w:rFonts w:ascii="SimSun" w:hAnsi="SimSun" w:eastAsia="宋体" w:hint="eastAsia"/>'
                '<w:sz w:val="24"/><w:szCs w:val="24"/><w:color w:val="000000"/></w:rPr>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:styles xmlns:w="{w}">'
        '<w:docDefaults><w:rPrDefault>{rpr}</w:rPrDefault>'
        '<w:pPrDefault><w:pPr><w:spacing w:line="360" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/>'
        '<w:pPr><w:spacing w:line="360" w:lineRule="auto"/></w:pPr>{rpr}</w:style>'
        '<w:style w:type="paragraph" w:styleId="PatentBody"><w:name w:val="Patent Body"/><w:basedOn w:val="Normal"/>'
        '<w:pPr><w:jc w:val="both"/><w:spacing w:after="120" w:line="360" w:lineRule="auto"/><w:ind w:firstLine="480"/></w:pPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="PatentClaim"><w:name w:val="Patent Claim"/><w:basedOn w:val="Normal"/>'
        '<w:pPr><w:jc w:val="both"/><w:spacing w:after="160" w:line="360" w:lineRule="auto"/>'
        '<w:ind w:left="420" w:hanging="420"/></w:pPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="PatentReviewItem"><w:name w:val="Patent Review Item"/><w:basedOn w:val="Normal"/>'
        '<w:pPr><w:jc w:val="both"/><w:spacing w:after="120" w:line="360" w:lineRule="auto"/>'
        '<w:ind w:left="420" w:hanging="420"/></w:pPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="PatentPartTitle"><w:name w:val="Patent Part Title"/><w:basedOn w:val="Normal"/>'
        '<w:pPr><w:jc w:val="center"/><w:keepNext/><w:spacing w:after="360"/></w:pPr>'
        '<w:rPr><w:rFonts w:ascii="SimSun" w:hAnsi="SimSun" w:eastAsia="宋体" w:hint="eastAsia"/><w:b/><w:sz w:val="32"/></w:rPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="PatentSectionTitle"><w:name w:val="Patent Section Title"/><w:basedOn w:val="Normal"/>'
        '<w:pPr><w:jc w:val="center"/><w:keepNext/><w:spacing w:before="240" w:after="180"/></w:pPr>'
        '<w:rPr><w:rFonts w:ascii="SimSun" w:hAnsi="SimSun" w:eastAsia="宋体" w:hint="eastAsia"/><w:b/><w:sz w:val="28"/></w:rPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="PatentDrawing"><w:name w:val="Patent Drawing"/><w:basedOn w:val="Normal"/>'
        '<w:pPr><w:jc w:val="center"/><w:spacing w:after="240"/></w:pPr></w:style>'
        '</w:styles>'
    ).format(w=W_NS, rpr=body_rpr).encode("utf-8")


def _settings_xml() -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:settings xmlns:w="{w}"><w:zoom w:percent="100"/><w:defaultTabStop w:val="420"/>'
        '</w:settings>'
    ).format(w=W_NS).encode("utf-8")


def _content_types(has_footer: bool, image_extensions: List[str]) -> bytes:
    defaults = ['<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
                '<Default Extension="xml" ContentType="application/xml"/>']
    seen = set()
    for ext in image_extensions:
        if ext in seen:
            continue
        seen.add(ext)
        media_type = "image/png" if ext == "png" else "image/jpeg"
        defaults.append('<Default Extension="{}" ContentType="{}"/>'.format(ext, media_type))
    overrides = [
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>',
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>',
        '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>',
    ]
    if has_footer:
        overrides.append('<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        + "".join(defaults) + "".join(overrides) + "</Types>"
    ).encode("utf-8")


def _root_relationships() -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '</Relationships>'
    ).encode("utf-8")


def _document_relationships(media: List[Tuple[str, str]], has_footer: bool) -> bytes:
    records = [
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>',
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>',
    ]
    if has_footer:
        records.append('<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>')
    for rel_id, member in media:
        records.append('<Relationship Id="{}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="{}"/>'.format(
            _xml_attr(rel_id), _xml_attr(member[len("word/"):])))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(records) + "</Relationships>"
    ).encode("utf-8")


def _write_docx(path: Path, members: List[Tuple[str, bytes]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(str(path), "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members:
            info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payload)


def _build_document_paragraphs(draft: Draft, figures_dir: Path) -> Tuple[List[str], List[Tuple[str, str, bytes]]]:
    paragraphs: List[str] = []
    media: List[Tuple[str, str, bytes]] = []
    docpr_id = 1
    next_rel_id = 4  # rId1=styles, rId2=settings, rId3=footer（见 build_docx）

    # 1. 卷首「审阅说明」
    paragraphs.append(_paragraph("审阅说明", "PatentPartTitle"))
    paragraphs.append(_paragraph("本页为审阅说明，非申请文件组成部分，提交前删除。", "PatentBody", bold=True))
    paragraphs.append(_paragraph("撰写结论", "PatentSectionTitle"))
    for line in draft.conclusion_lines:
        stripped = line.text.strip()
        if not stripped:
            continue
        cleaned = normalize_prose_markdown(stripped)[0]
        if cleaned.strip():
            paragraphs.append(_paragraph(cleaned, "PatentBody"))
    paragraphs.append(_paragraph("待确认事项", "PatentSectionTitle"))
    for idx, item in enumerate(draft.pending_items, 1):
        event = normalize_prose_markdown(item.event)[0]
        impact = normalize_prose_markdown(item.impact)[0] if item.impact else ""
        label = PENDING_LABEL_BY_LEVEL[item.level]
        text = "{}. {}：{}。{}。".format(idx, label, event.rstrip("。"), impact.rstrip("。")) if impact else \
               "{}. {}：{}".format(idx, label, event)
        paragraphs.append(_paragraph(text, "PatentReviewItem"))
    paragraphs.append(_paragraph("提交前说明", "PatentSectionTitle"))
    for line in draft.boundary_lines:
        stripped = line.text.strip()
        if not stripped:
            continue
        cleaned = normalize_prose_markdown(stripped)[0]
        if cleaned.strip():
            paragraphs.append(_paragraph(cleaned, "PatentBody"))

    # 2. 说明书摘要
    paragraphs.append(_paragraph("说明书摘要", "PatentPartTitle", page_break=True))
    for line in draft.abstract_lines:
        stripped = line.text.strip()
        if not stripped:
            continue
        cleaned = normalize_prose_markdown(stripped)[0]
        if cleaned.strip():
            paragraphs.append(_paragraph(cleaned, "PatentBody"))

    # 3. 权利要求书
    paragraphs.append(_paragraph("权利要求书", "PatentPartTitle", page_break=True))
    for claim in draft.claims:
        paragraphs.append(_paragraph("{}. {}".format(claim.number, claim.text), "PatentClaim"))

    # 4. 说明书
    paragraphs.append(_paragraph("说明书", "PatentPartTitle", page_break=True))
    if draft.invention_name:
        paragraphs.append(_paragraph(draft.invention_name, "PatentPartTitle"))
    for title in draft.spec_h2_order:
        section = draft.spec_sections.get(title)
        if not section:
            continue
        # draft.md 骨架统一用「发明名称」作内部键；实用新型案渲染时按法定
        # 标签输出「实用新型名称」（专家标准答案用法，v6 实测曾原样漏出）。
        display_title = title
        if title == "发明名称" and draft.case_type == "实用新型":
            display_title = "实用新型名称"
        paragraphs.append(_paragraph(display_title, "PatentSectionTitle"))
        for line in section.lines:
            stripped = line.text.strip()
            if not stripped:
                continue
            cleaned = normalize_prose_markdown(stripped)[0]
            if cleaned.strip():
                paragraphs.append(_paragraph(cleaned, "PatentBody"))

    # 5. 说明书附图（真实附图部分；mixed 状态嵌入图1..M，规划图无实体不嵌）
    if draft.real_figure_count:
        paragraphs.append(_paragraph("说明书附图", "PatentPartTitle", page_break=True))
        for n in range(1, draft.real_figure_count + 1):
            path = _find_figure_file(figures_dir, n)
            if path is None:
                raise FigureResourceError("图{}对应的图片文件缺失，无法嵌入。".format(n))
            payload = path.read_bytes()
            sniffed = _sniff_image(payload)
            if sniffed is None:
                raise FigureResourceError("图{}文件不是可识别的 PNG/JPEG。".format(n))
            fmt, width, height = sniffed
            ext = "png" if fmt == "png" else "jpg"
            member = "word/media/image{}.{}".format(n, ext)
            rel_id = "rId{}".format(next_rel_id)
            next_rel_id += 1
            media.append((rel_id, member, payload))
            caption = "图{}".format(n)
            drawing_xml = _inline_drawing(rel_id, docpr_id, width, height, caption)
            docpr_id += 1
            paragraphs.append(_paragraph("", "PatentDrawing", drawing_xml=drawing_xml))
            paragraphs.append(_paragraph(caption, "PatentDrawing"))

    return paragraphs, media


def _document_xml(paragraphs: List[str], has_footer: bool) -> bytes:
    footer_ref = '<w:footerReference w:type="default" r:id="rId3"/>' if has_footer else ""
    sect_pr = (
        '<w:sectPr>{footer}<w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>'
        '<w:cols w:space="720"/><w:docGrid w:linePitch="360"/></w:sectPr>'
    ).format(footer=footer_ref)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="{w}" xmlns:r="{r}" xmlns:wp="{wp}" xmlns:a="{a}" xmlns:pic="{pic}">'
        '<w:body>{paragraphs}{sect}</w:body></w:document>'
    ).format(w=W_NS, r=R_NS, wp=WP_NS, a=A_NS, pic=PIC_NS, paragraphs="".join(paragraphs), sect=sect_pr).encode("utf-8")


def _sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip() or "未命名"


def build_docx(draft: Draft, out_dir: Path, figures_dir: Path) -> Path:
    paragraphs, media = _build_document_paragraphs(draft, figures_dir)
    has_footer = True
    members: List[Tuple[str, bytes]] = [
        ("[Content_Types].xml", _content_types(has_footer, [m[1].rsplit(".", 1)[-1] for m in media])),
        ("_rels/.rels", _root_relationships()),
        ("word/document.xml", _document_xml(paragraphs, has_footer)),
        ("word/styles.xml", _styles_xml()),
        ("word/settings.xml", _settings_xml()),
        ("word/footer1.xml", _page_number_footer_xml()),
        ("word/_rels/document.xml.rels", _document_relationships([(r, m) for r, m, _ in media], has_footer)),
    ]
    members.extend((member, payload) for _, member, payload in media)
    filename = "{}-专利申请文件（审阅稿）.docx".format(_sanitize_filename(draft.invention_name or "专利申请"))
    output_path = out_dir / filename
    _write_docx(output_path, members)
    return output_path


# =====================================================================
# 第四段：报告生成 + 构建主流程 + CLI
# =====================================================================

# 官方依据静态映射（一次性表，渲染报告时只做字典查找，零运行时开销）：
# 按检查编号给出默认依据；C5 下摘要字数与发明名称字数依据不同条款，用
# (check, location) 精确覆盖默认值。未登记条款号的检查（C1 结构/C7 套话/
# C8 术语/C9 联动/C10 主题/C11 markdown/C12 照抄/C13 工具名泄漏，以及构建流程
# 中的临时性「资源」问题）一律标注为本 skill 撰写规范，不编造不存在的法条。
CHECK_BASIS: Dict[str, str] = {
    "C1": "本 skill 撰写规范",
    "C2": "《专利审查指南》第二部分第二章 3.3；《专利法实施细则》第22条",
    "C3": "《专利法实施细则》第23条",
    "C4": "《专利法》第2条第3款",
    "C5": "《专利法实施细则》第26条",
    "C6": "《专利法实施细则》第21条",
    "C7": "本 skill 撰写规范",
    "C8": "本 skill 撰写规范",
    "C9": "本 skill 撰写规范",
    "C10": "本 skill 撰写规范",
    "C11": "本 skill 撰写规范",
    "C12": "本 skill 撰写规范",
    "C13": "本 skill 撰写规范",
    "C14": "本 skill 撰写规范",
    "C15": "本 skill 撰写规范",
}
CHECK_BASIS_OVERRIDES: Dict[Tuple[str, str], str] = {
    ("C5", "案件头/发明名称"): "《专利审查指南》第二部分第二章 2.4",
}
CHECK_BASIS_DEFAULT = "本 skill 撰写规范"


def issue_basis(issue: Issue) -> str:
    """返回一条 Issue 的官方依据标注：先查 (check, location) 精确覆盖，未命中
    则按检查编号取默认依据；未登记的检查编号统一退回本 skill 撰写规范。"""
    override = CHECK_BASIS_OVERRIDES.get((issue.check, issue.location))
    if override:
        return override
    return CHECK_BASIS.get(issue.check, CHECK_BASIS_DEFAULT)


def render_report(issues: List[Issue], draft: Draft, generated_at: str) -> str:
    fail_issues = [i for i in issues if i.severity == "FAIL"]
    warn_issues = [i for i in issues if i.severity == "WARN"]
    lines = ["# 专利申请文件修稿报告", "",
             "生成时间：{}".format(generated_at),
             "草稿文件：{}".format(draft.source_path),
             "检查结论：FAIL（共 {} 处必须修改{}）".format(
                 len(fail_issues), "，另有 {} 条提示".format(len(warn_issues)) if warn_issues else ""),
             "", "## 必须修改的问题", ""]
    for idx, issue in enumerate(fail_issues, 1):
        lines.append("{}. 【{}】位置：{}".format(idx, issue.check, issue.location))
        lines.append("   问题：{}".format(issue.problem))
        lines.append("   怎么改：{}".format(issue.fix))
        lines.append("   依据：{}".format(issue_basis(issue)))
        lines.append("")
    if warn_issues:
        lines.append("## 提示（不阻塞生成，建议一并处理）")
        lines.append("")
        for issue in warn_issues:
            lines.append("- 【{}】{}：{}（建议：{}；依据：{}）".format(
                issue.check, issue.location, issue.problem, issue.fix, issue_basis(issue)))
        lines.append("")
    lines.append("## 下一步")
    lines.append("按上述问题修改 draft.md 后，重新运行：")
    lines.append("```")
    lines.append("python3 scripts/patent_build.py build --draft draft.md --out output/")
    lines.append("```")
    return "\n".join(lines) + "\n"


def _snapshot_draft_history(draft_path: Path, out_dir: Path) -> Path:
    """把当次 draft.md 原样（字节级）复制一份到 <out_dir>/history/draft-<时间
    戳>.md（详见模块头部「draft.md 历史快照」补充约定）。调用方须自行用
    try/except 包裹：本函数在目录不可写等情况下会照常抛出异常，快照失败不
    得影响整体构建结论，由调用方决定如何降级处理。"""
    history_dir = out_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    candidate = history_dir / "draft-{}.md".format(stamp)
    suffix = 2
    while candidate.exists():
        candidate = history_dir / "draft-{}-{}.md".format(stamp, suffix)
        suffix += 1
    candidate.write_bytes(draft_path.read_bytes())
    return candidate


def run_build(draft_path: Path, out_dir: Path, figures_dir: Optional[Path] = None) -> int:
    generated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if out_dir.exists() and not out_dir.is_dir():
        # 不依赖 mkdir 的异常语义：--out 与既有普通文件同名时，mkdir 会抛
        # FileExistsError，若放任其向上抛出，main() 里兜底 except 的恢复逻辑会
        # 重复执行同一句必然失败的 mkdir，导致裸 Traceback（无 PATENT_BUILD 行）。
        print("PATENT_BUILD: FAIL 报告=<未生成：--out 指定的路径「{}」已存在但不是目录，"
              "无法在其中写入修稿报告或 docx；请更换为其他输出目录，或删除/重命名该同名文件后重试。>".format(out_dir))
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)

    if not draft_path.is_file():
        report_path = out_dir / "修稿报告.md"
        report_path.write_text(
            render_report(
                [Issue("C1", "FAIL", "draft.md", "找不到草稿文件：{}。".format(draft_path),
                       "确认 --draft 参数指向的路径存在。")],
                Draft(source_path=str(draft_path)), generated_at),
            encoding="utf-8")
        print("PATENT_BUILD: FAIL 报告={}".format(report_path))
        return 1

    try:
        # utf-8-sig 对不含 BOM 的正常 UTF-8 文本行为与 utf-8 完全一致，同时能
        # 正确剥离 BOM（纯 utf-8 编解码器不会因 BOM 抛异常，BOM 会被解码为
        # U+FEFF 留在文本最前面，导致「# 案件头」标题正则匹配不上、整节被
        # 静默吞掉）。仍抛出 UnicodeDecodeError 说明确实不是 UTF-8 系编码
        # （如 GBK/ANSI），此时不得用 errors="replace" 静默生成乱码喂给后续
        # 解析与报告渲染，直接给出明确的中文 FAIL。
        text = draft_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        report_path = out_dir / "修稿报告.md"
        report_path.write_text(
            render_report(
                [Issue("C1", "FAIL", "draft.md",
                       "draft.md 不是 UTF-8 编码（可能是 GBK/ANSI 等）。",
                       "请用文本编辑器将 draft.md 另存为 UTF-8 编码后重试。")],
                Draft(source_path=str(draft_path)), generated_at),
            encoding="utf-8")
        print("PATENT_BUILD: FAIL 报告={}".format(report_path))
        return 1

    draft = parse_draft(text, str(draft_path))
    if figures_dir is None:
        figures_dir = draft_path.resolve().parent / "figures"

    issues = run_all_checks(draft)
    issues.extend(check_figure_resources(draft, figures_dir))

    overall_pass = not any(i.severity == "FAIL" for i in issues)
    official_checks = [cid for cid, _ in ALL_CHECKS]
    passed_count = sum(
        1 for cid in official_checks
        if not any(i.severity == "FAIL" and i.check == cid for i in issues)
    )

    if not overall_pass:
        report_path = out_dir / "修稿报告.md"
        report_path.write_text(render_report(issues, draft, generated_at), encoding="utf-8")
        print("PATENT_BUILD: FAIL 报告={}".format(report_path))
        return 1

    try:
        docx_path = build_docx(draft, out_dir, figures_dir)
    except FigureResourceError as exc:
        issues.append(Issue("资源", "FAIL", "附图文件", str(exc), "补齐附图文件后重新构建。"))
        report_path = out_dir / "修稿报告.md"
        report_path.write_text(render_report(issues, draft, generated_at), encoding="utf-8")
        print("PATENT_BUILD: FAIL 报告={}".format(report_path))
        return 1

    try:
        _snapshot_draft_history(draft_path, out_dir)
    except Exception as exc:  # noqa: BLE001 - 快照失败不得影响构建结果，仅提示不阻断
        print("提示【draft快照】写入历史快照失败，不影响本次构建结果：{}: {}。".format(
            type(exc).__name__, exc))

    for issue in issues:
        if issue.severity == "WARN":
            print("提示【{}】{}：{}".format(issue.check, issue.location, issue.problem))
    print("PATENT_BUILD: PASS 输出={} 检查={}项通过".format(docx_path, passed_count))
    return 0


# ---------------------------------------------------------------------
# selftest：内嵌最小用例，无外部依赖即可自测
# ---------------------------------------------------------------------

_SELFTEST_DRAFT_OK = """# 案件头
- 案件类型: 实用新型
- 发明名称: 螺纹紧固垫片
- 主题实体: 螺纹紧固垫片
- 附图状态: 无
- 附图标记表: 无

# 审阅说明
## 撰写结论
本次任务为根据交底材料撰写实用新型专利申请文件（自测样例）。
## 待确认事项
- [正式提交前建议确认] 垫片材质未记载具体牌号：影响实施例细节完整性。
## 边界与免责
本文件为内部自测样例，本次未包含检索和侵权分析。

# 说明书摘要
本实用新型公开一种螺纹紧固垫片，属于紧固件技术领域。该垫片包括垫片本体，所述垫片本体上设有防松齿纹，能够提高螺纹连接的防松效果。

# 权利要求书
1. 一种螺纹紧固垫片，包括垫片本体，其特征在于，所述垫片本体的表面设有防松齿纹。
2. 根据权利要求1所述的螺纹紧固垫片，其特征在于，所述防松齿纹沿所述垫片本体周向均匀分布。

# 说明书
## 发明名称
螺纹紧固垫片
## 技术领域
本实用新型涉及紧固件技术领域，具体涉及一种螺纹紧固垫片。
## 背景技术
现有螺纹连接在振动环境下容易松动，普通平垫片缺乏防松结构。
## 实用新型内容
本实用新型的技术问题是提高螺纹连接的防松效果。为此提供一种螺纹紧固垫片，包括垫片本体，所述垫片本体的表面设有防松齿纹，能够提高螺纹连接的防松效果。
## 具体实施方式
本实用新型提供的螺纹紧固垫片，包括垫片本体，所述垫片本体的表面设有防松齿纹，所述防松齿纹沿所述垫片本体周向均匀分布，装配时齿纹咬合被连接件表面，从而提高防松效果。
在一个实施例中，垫片本体为L型结构，外缘尺寸为100×200mm，防松齿纹呈S形延伸。
"""

_SELFTEST_DRAFT_BAD = _SELFTEST_DRAFT_OK.replace("- 附图状态: 无\n", "")

# 事故回归样例：实测真实逃逸样本逐字蒸馏。第5轮（v5 包）：①审阅说明自称
# 「本skill」→C13 ②说明书结尾免责段变体→C7（现为 WARN 级）③摘要单方面升格
# 「显著」→C14。第7轮（v7 包）：④正文「防松齿纹5」与标记表 5=垫片本体 张冠
# 李戴→C15。维护纪律：以后每轮实测发现逃逸，先把样本加进本 fixture 再改
# 词表/正则，selftest 不过不发版。
_SELFTEST_DRAFT_INCIDENTS = _SELFTEST_DRAFT_OK.replace(
    "- 附图标记表: 无",
    "- 附图标记表: 5=垫片本体, 6=防松齿纹",
).replace(
    "本次任务为根据交底材料撰写实用新型专利申请文件（自测样例）。",
    "本次任务为根据交底材料撰写实用新型专利申请文件（自测样例）。\n"
    "现有技术检索：本skill职责范围不包含专利检索业务。",
).replace(
    "能够提高螺纹连接的防松效果。\n\n# 权利要求书",
    "能够显著提高螺纹连接的防松效果。\n\n# 权利要求书",
).replace(
    "从而提高防松效果。",
    "从而提高防松效果。防松齿纹5均匀分布于垫片本体6的表面。\n"
    "以上所述仅为本实用新型的较佳实施例，凡在本实用新型的精神和原则之内"
    "所作的任何修改、等同替换、改进等，均应包含在本实用新型的保护范围之内。",
)

# v11 事故回归：图2仅声明未引用、公式符号写法漂移且 Tset 未定义、同名标记
# 重复占号并有未使用编号、测试状态未确认却下“从根本上解决”的强结论。
# 待确认措辞用「请逐项确认…实测状态」——v12 修复前这种主动句式会绕过 C18 触发。
_SELFTEST_DRAFT_V11_INCIDENTS = _SELFTEST_DRAFT_OK.replace(
    "- 附图状态: 无", "- 附图状态: 规划图名2条"
).replace(
    "- 附图标记表: 无", "- 附图标记表: 5=垫片本体, 6=防松齿纹, 7=垫片本体"
).replace(
    "- [正式提交前建议确认] 垫片材质未记载具体牌号：影响实施例细节完整性。",
    "- [本次定稿前需要确认] 请逐项确认交底材料中各项性能指标的实测状态：影响效果措辞定级。\n"
    # v12 实测逃逸样本（T2 原话句式）：修复前该措辞绕过 C18 触发
    "- [本次定稿前需要确认] 性能参数的验证状态：交底书记载的指标未明确说明是否已完成样机测试验证，目前按设计目标口径撰写。",
).replace(
    "## 具体实施方式\n",
    "## 附图说明\n图1是垫片结构示意图；\n图2是齿纹局部放大图。\n"
    "## 具体实施方式\n如图1所示，",
).replace(
    "垫片本体，", "垫片本体5，"
).replace(
    "防松齿纹，", "防松齿纹6，"
).replace(
    "从而提高防松效果。",
    "从根本上解决了松动问题。计算公式为：Tliquid = T_surface + P × R。"
    "控制误差为|Tset-Tliquid|。其中，T_liquid为估算温度，"
    "T_surface为表面温度，P为功率，R为热阻。",
)


def run_selftest() -> int:
    import shutil
    import tempfile

    workdir = Path(tempfile.mkdtemp(prefix="patent_build_selftest_"))
    ok = True
    try:
        draft_path = workdir / "draft_ok.md"
        draft_path.write_text(_SELFTEST_DRAFT_OK, encoding="utf-8")
        out_dir = workdir / "out_ok"
        rc = run_build(draft_path, out_dir)
        if rc != 0:
            print("SELFTEST: FAIL 合规样例未通过构建")
            ok = False
        else:
            docx_files = list(out_dir.glob("*.docx"))
            if len(docx_files) != 1:
                print("SELFTEST: FAIL 未生成唯一 docx 文件")
                ok = False
            else:
                with zipfile.ZipFile(docx_files[0]) as z:
                    doc = z.read("word/document.xml").decode("utf-8")
                headings = ("审阅说明", "说明书摘要", "权利要求书", "说明书")
                order = [doc.find("<w:t>{}</w:t>".format(t)) for t in headings]
                if any(pos == -1 for pos in order) or order != sorted(order):
                    print("SELFTEST: FAIL docx 章节顺序不正确")
                    ok = False

        bad_path = workdir / "draft_bad.md"
        bad_path.write_text(_SELFTEST_DRAFT_BAD, encoding="utf-8")
        out_dir_bad = workdir / "out_bad"
        rc_bad = run_build(bad_path, out_dir_bad)
        if rc_bad == 0:
            print("SELFTEST: FAIL 缺失附图状态字段的样例本应构建失败")
            ok = False
        elif not (out_dir_bad / "修稿报告.md").is_file():
            print("SELFTEST: FAIL 未生成修稿报告")
            ok = False

        inc_path = workdir / "draft_incidents.md"
        inc_path.write_text(_SELFTEST_DRAFT_INCIDENTS, encoding="utf-8")
        out_dir_inc = workdir / "out_incidents"
        rc_inc = run_build(inc_path, out_dir_inc)
        inc_report = out_dir_inc / "修稿报告.md"
        if rc_inc == 0 or not inc_report.is_file():
            print("SELFTEST: FAIL 事故回归样例本应构建失败并生成修稿报告")
            ok = False
        else:
            inc_text = inc_report.read_text(encoding="utf-8")
            for check_id in ("C7", "C13", "C14", "C15"):
                if "【{}】".format(check_id) not in inc_text:
                    print("SELFTEST: FAIL 事故回归样例未命中 {}".format(check_id))
                    ok = False

        v11_inc_path = workdir / "draft_v11_incidents.md"
        v11_inc_path.write_text(_SELFTEST_DRAFT_V11_INCIDENTS, encoding="utf-8")
        out_dir_v11_inc = workdir / "out_v11_incidents"
        rc_v11_inc = run_build(v11_inc_path, out_dir_v11_inc)
        v11_inc_report = out_dir_v11_inc / "修稿报告.md"
        if rc_v11_inc == 0 or not v11_inc_report.is_file():
            print("SELFTEST: FAIL v11 事故回归样例本应构建失败并生成修稿报告")
            ok = False
        else:
            v11_inc_text = v11_inc_report.read_text(encoding="utf-8")
            for check_id in ("C6", "C16", "C17", "C18"):
                if "【{}】".format(check_id) not in v11_inc_text:
                    print("SELFTEST: FAIL v11 事故回归样例未命中 {}".format(check_id))
                    ok = False
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    print("SELFTEST: {}".format("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="patent_build.py")
    parser.add_argument("--selftest", action="store_true")
    sub = parser.add_subparsers(dest="command")

    build_parser = sub.add_parser("build")
    build_parser.add_argument("--draft", required=True)
    build_parser.add_argument("--out", required=True)
    build_parser.add_argument("--figures-dir", default=None)

    sub.add_parser("selftest")

    args = parser.parse_args(argv)

    if args.selftest or args.command == "selftest":
        return run_selftest()
    if args.command == "build":
        figures_dir = Path(args.figures_dir) if args.figures_dir else None
        try:
            return run_build(Path(args.draft), Path(args.out), figures_dir)
        except Exception as exc:  # noqa: BLE001 - 兜底，确保始终有 PATENT_BUILD 结论行
            generated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            issue = Issue("C1", "FAIL", "脚本执行",
                          "脚本内部出现未预期异常：{}: {}。".format(type(exc).__name__, exc),
                          "检查 draft.md 是否为 UTF-8 编码的合法 Markdown 文本，修正后重试；如持续失败请保留本报告与原始报错反馈。")
            # 恢复动作本身（建目录/写报告）也必须异常安全：例如 --out 恰好与一个
            # 既有普通文件同名时，这里的 mkdir 会再次抛出与 run_build 内部相同的
            # FileExistsError；若不包一层 try/except，第二个异常会裸奔到最顶层，
            # 使 stdout 完全没有任何 PATENT_BUILD 行。任何恢复失败都退化为直接
            # print 一行结论，不再尝试写文件。
            try:
                out_dir = Path(args.out)
                out_dir.mkdir(parents=True, exist_ok=True)
                report_path = out_dir / "修稿报告.md"
                report_path.write_text(
                    render_report([issue], Draft(source_path=args.draft), generated_at), encoding="utf-8")
                print("PATENT_BUILD: FAIL 报告={}".format(report_path))
            except Exception as exc2:  # noqa: BLE001 - 恢复动作也要兜底，不能让第二个异常裸奔
                print("PATENT_BUILD: FAIL 报告=<写入失败：原始异常 {}: {}；恢复动作异常 {}: {}。"
                      "请检查 --out 路径是否可写、是否与既有文件同名后重试。>".format(
                          type(exc).__name__, exc, type(exc2).__name__, exc2))
            return 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
