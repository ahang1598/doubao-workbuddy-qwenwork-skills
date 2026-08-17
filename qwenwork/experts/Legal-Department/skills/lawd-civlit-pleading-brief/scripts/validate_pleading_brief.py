#!/usr/bin/env python3
"""lawd-civlit-pleading-brief 代理词交付门禁（防幻觉 / 防缺漏 / 防模板空壳）。

用法
----
    # 材料齐备：Markdown 提纲 + Word 正式稿一并校验（主路径）
    python3 scripts/validate_pleading_brief.py \
        --outline 《XX案-代理词-提纲》.md \
        --brief   《XX案-代理词》.docx \
        --material-status complete

    # 材料齐备但上游只要结构化内容（SKILL.md「被整合调用模式」允许跳过 Word）
    python3 scripts/validate_pleading_brief.py \
        --outline 《XX案-代理词-提纲》.md --material-status complete --outline-only

    # 材料不足：只交付「空白提纲 + 材料缺口清单」
    python3 scripts/validate_pleading_brief.py \
        --outline 《XX案-代理词-提纲(空白)》.md --material-status incomplete

支持格式：.md / .markdown / .txt / .docx（--outline 与 --brief 均可）。
docx 用标准库 zipfile + ElementTree 解析，覆盖正文段落、表格、页眉页脚与文本框，
无需安装 python-docx。

`--material-status` 为必填：缺省时脚本直接以退出码 2 报错，不做静默放过——材料
是否齐备决定「该不该出 Word」「该不该有缺口清单」两条相反的判据，猜不得。
材料齐备且未加 `--outline-only` 时缺 `--brief` 同样退出 2。

检查项（材料齐备模式）
----------------------
1. 场景路由（SKILL.md:26/:36）：审理机构（法院/仲裁）、审级（一审/二审/再审/仲裁）、
   我方地位（原告/被告/上诉人/被上诉人/申请人/被申请人）三个维度须在提纲首部/正
   式稿首部可识别；并检查称谓混用（同一文书里同时出现「审判长」与「首席仲裁员/
   仲裁庭」这类相对方称谓即拦）。仅出现《仲裁法》《民事诉讼法》等法名不算混用。
2. 双输出规范（:143/:158/:197）：提纲须是代理词提纲；Word 正式稿须存在（或显式
   `--outline-only` 且未交付 Word）；Word 争点节数不得少于提纲争点数（防漏争点）；
   两份均含文首免责声明（:239）；正式稿提交格式项齐备（标题、法庭/仲裁庭称谓语、
   结尾请求、落款代理人/律所/日期）。**正式稿须为提纲之外的实质正文**（P0⑩）：
   正文长度达标、含称谓语与「事实与理由/法律依据/综上请求」等实质小节、且不得与
   提纲逐句相同——把提纲当正式稿二次提交即拦。`--outline-only` 仅在未交付 Word 时
   跳过对应关系校验；一旦传入 `--brief`，正式稿强制校验全量执行（P0⑪）。
3. 争点与主张矩阵（:131 + references/fact-evidence-law-matrix.md）：接受两种合规
   渲染形式之一——①三联表（表头含争点/主张/事实/证据/法律，数据行非占位）；
   ②提纲「争议焦点逐项」分节（每个争点一节）。两者皆无 → 拦。空壳拦截：所有争
   点节均无实质内容，或核心争点（★★★★★/★★★★☆，无星标时取首个争点）缺
   「证据要素」或「法律要素」。★★★☆☆ 及以下按 outline-template 只需「立场 +
   要点 2～3 条」，不强求法律要素，避免误拦。
4. 证据锚定（:92）：纯形式判据，不做语义推断——事实型章节（案件事实 / 事实陈述
   等）内的实质事实段落须带证据编号引用（`[证X-PX]`、「证5」「原告证据3」「被告
   证据一」「附件2」等均认）。豁免：「无争议/对方自认事实」小节，以及标注「待证
   事实/待证/待补充/待确认」的段落（:93 允许的写法）。拦截口径保守：①全文无任何
   证据编号引用；或②未锚定段落 >= 3 条且占比 > 50%。若文内含证据清单/证据目录表，
   额外交叉比对被引编号是否在清单内，但**只提示不拦截**（我方/对方证据分别编号时
   易误判）。
5. 法条引用格式（:95）：法条条号须带《法律名》。允许「《法名》（以下简称《简称》）
   第X条」「第X条第2款、第Y条」「该法第X条」等写法；「合同第三条」「公司章程第五
   条」等非法条条号不计入拦截。全文既无《法名》第X条、又无「待律师人工复核 / 检索
   结果不足」标注（:141）时拦截。
6. 材料不足模式（:72/:151/:207）：仅校验交付规范——必附结构化「材料缺口清单」
   （须单独成章，且有分级/表格等结构，一句话不算）；提纲须留「待补充」占位；
   **不得**交付 Word 正式稿（传了 --brief 即拦）。此模式下判据 3/4/5 降级为提示，
   避免空白骨架被误拦。

退出码：0=通过；1=拦截；2=输入错误（含缺 --material-status、缺 --brief）。
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
from xml.etree import ElementTree as ET

# ------------------------------------------------------------------ 常量/正则

NUM_CHARS = "零〇○一二两三四五六七八九十百千0123456789"
CN_ONLY = "零〇○一二两三四五六七八九十百千"

_N = "[" + NUM_CHARS + "]+"
_SUFFIX = r"(?:\s*第" + _N + r"[款项])*"

# 《法律名》[（以下简称《简称》）] 第X条[第X款/项][、第Y条第Y款…]
CITATION_RE = re.compile(
    r"《([^《》\n]{2,80}?)》"
    r"(?:\s*[（(][^）)\n]{0,60}[）)])?"
    r"\s*(?:之|的)?\s*"
    r"第(" + _N + r")条" + _SUFFIX +
    r"((?:\s*[、，,;；和与及]?\s*第" + _N + r"条" + _SUFFIX + r")*)"
)

ARTICLE_RE = re.compile(r"第(" + _N + r")条")

# 紧邻条号之前的「非法条载体」（合同/章程等），这类「第X条」不是法条引用
NON_STATUTE_PREFIX_RE = re.compile(
    r"(?:合同|协议|合约|契约|章程|规约|公约|条款|细则|规则|规程|议事规则|管理规约|"
    r"业主公约|标准|规范|附件|附则|备忘录|意向书|承诺书|授权书|决议|判决|裁定|裁决|"
    r"调解书|通知|保单|制度|手册|须知|说明|方案|纪要|清单|明细|订单|补充协议)"
    r"\s*(?:书|文本)?\s*(?:之|的|中|里)?\s*$"
)

# 可不带《》的「回指」表述（该法/本法第X条），需全文存在法律引用才放行
BACKREF_RE = re.compile(
    r"(?:该法|本法|上述法律|前述法律|同法|该司法解释|该解释|上述解释|该条例|"
    r"上述条例|该规定|上述规定|该批复|该意见|该纪要)\s*(?:之|的)?\s*$"
)

# 法律/法规/司法解释名称特征（用于区分《XX买卖合同》与《民法典》）
STATUTE_NAME_RE = re.compile(
    r"(?:法|法典|宪法|条例|规定|解释|办法|细则|规则|通知|意见|纪要|批复|决定|准则|"
    r"标准|规范)$"
)

# 编号小标题：（一） (1) 一、 1、 1. 第一项 焦点1
SUBHEAD_RE = re.compile(
    r"^(?:#{1,6}\s*)?(?:\*{1,2})?\s*(?:"
    r"[（(]\s*[" + NUM_CHARS + r"]{1,4}\s*[)）]"
    r"|[" + CN_ONLY + r"]{1,4}\s*[、.．]"
    r"|\d{1,3}(?:\.\d{1,3})?\s*[.、)）]"
    r"|第[" + NUM_CHARS + r"]{1,4}[项条点]"
    r")"
)

# 一级（章）标题：一、二、三…… 允许 markdown # 前缀
TOP_HEAD_RE = re.compile(
    r"^(?:#{1,4}\s*)?(?:\*{1,2})?\s*[" + CN_ONLY + r"]{1,3}\s*[、.．]"
)

# 争点/焦点条目标题：焦点1 / 争点二 / （一）关于XXX
FOCUS_ITEM_RE = re.compile(
    r"^(?:#{1,6}\s*)?(?:\*{1,2})?\s*(?:"
    r"(?:争议)?(?:焦点|争点)\s*[" + NUM_CHARS + r"]{1,3}"
    r"|[（(]\s*[" + NUM_CHARS + r"]{1,4}\s*[)）]"
    r"|F-?\d{1,3}"
    r")"
)

# 争点章节标题
FOCUS_CHAPTER_RE = re.compile(r"争议焦点|争点|焦点")

# 事实章节标题（案件事实 / 事实陈述 / 事实与理由 / 事实和理由）
FACT_CHAPTER_RE = re.compile(r"案件事实|事实陈述|事实经过|事实\s*[与和及]?\s*理由|事实认定")

# 事实章节内的豁免小节（无争议 / 对方自认）
FACT_EXEMPT_SECTION_RE = re.compile(r"无争议|对方自认|自认事实|双方无异议|不争议事实")

# 段落级豁免标注（:93 允许的「待证事实」写法）
FACT_EXEMPT_MARK_RE = re.compile(r"待证事实|待证|待补充|待确认|待核实|待律师")

# 证据编号引用：[证3-P2] / 证3 / 原告证据3 / 被告证据一 / 证据3 / 附件2 / 证据清单第3项
EVIDENCE_REF_RE = re.compile(
    r"\[\s*证[^\]]{0,30}\]"
    r"|(?:原告|被告|上诉人|被上诉人|申请人|被申请人|我方|对方|本方)?\s*"
    r"证据\s*(?:材料\s*)?[" + NUM_CHARS + r"]{1,4}"
    r"|证\s*[" + NUM_CHARS + r"]{1,4}\s*(?:[-—－]\s*P?[" + NUM_CHARS + r"-]{1,10})?\s*(?:号)?"
    r"|附件\s*[" + NUM_CHARS + r"]{1,4}"
)
# 用于抽取编号数字（交叉比对证据清单）
EVIDENCE_NO_RE = re.compile(r"证据?\s*[第]?\s*([" + NUM_CHARS + r"]{1,4})")

# 场景路由三维度
INSTITUTION_COURT_RE = re.compile(r"人民法院|海事法院|知识产权法院|金融法院|审判长|审判员")
INSTITUTION_ARBI_RE = re.compile(r"仲裁委员会|仲裁院|仲裁中心|仲裁庭|首席仲裁员|仲裁委")
STAGE_RE = re.compile(
    r"一审|二审|再审|初审|终审|上诉|仲裁"
    r"|first_instance|second_instance|retrial|arbitration"
)
ROLE_WORD = r"(?:原告|被告|上诉人|被上诉人|申请人|被申请人|再审申请人|第三人)"
ROLE_DECL_RE = re.compile(
    r"(?:我方|本方|本代理人|代理人|委托人|当事人)?\s*(?:诉讼|仲裁)?\s*(?:地位|身份)"
    r"\s*[：:是为]?\s*(?:一审|二审|再审|初审|终审|仲裁)?\s*" + ROLE_WORD
    + r"|(?:我方|本方|本代理人)\s*(?:作为|系|为|是|代理)\s*" + ROLE_WORD
    + r"|受\s*" + ROLE_WORD + r"[^。\n]{0,25}(?:之?委托)"
    + r"|" + ROLE_WORD + r"[^。\n]{0,20}(?:的)?(?:委托)?代理人"
    + r"|(?:担任|作为)\s*" + ROLE_WORD + r"[^。\n]{0,15}代理人"
    + r"|场景[^。\n]{0,60}" + ROLE_WORD
    + r"|role\s*[:：]\s*(?:plaintiff|defendant|appellant|appellee|applicant|respondent)"
)

# 称谓混用：法庭称谓 vs 仲裁称谓（相对方称谓同时出现即混用）
SALUTATION_COURT_RE = re.compile(r"审判长|审判员|合议庭")
SALUTATION_ARBI_RE = re.compile(r"仲裁庭|首席仲裁员|独任仲裁员")

# 免责声明（:239）
DISCLAIMER_A_RE = re.compile(r"辅助生成|AI\s*辅助|智能辅助")
DISCLAIMER_B_RE = re.compile(r"不构成正式法律意见|承办律师审核|律师审核|律师复核|审核修改")

# 提纲身份
OUTLINE_TITLE_RE = re.compile(r"提纲|大纲|outline")
BRIEF_TITLE_RE = re.compile(r"代理词|代理意见|辩论意见|出庭意见")

# 正式稿提交格式项
CLOSING_REQUEST_RE = re.compile(
    r"综上所述|综上，|综上,|恳请|请依法|请求(?:法庭|贵院|仲裁庭|合议庭)"
    r"|结尾请求|请求事项|判令|判如所请|驳回(?:原告|上诉|申请人)"
    r"|维持原判|撤销原判|依法改判|发回重审|支持(?:全部|部分)?(?:诉讼请求|仲裁请求)"
)
SIGN_AGENT_RE = re.compile(r"代理人|委托代理人|出庭代理人")
SIGN_FIRM_RE = re.compile(r"律师事务所|律所")
SIGN_DATE_RE = re.compile(r"\d{4}\s*年\s*\d{1,2}\s*月|年\s+月\s+日|年\s*月\s*日|\d{4}-\d{1,2}-\d{1,2}")
SALUTATION_ANY_RE = re.compile(r"尊敬的\s*(?:审判长|审判员|仲裁庭|首席仲裁员|合议庭)|审判长、审判员|仲裁庭、首席仲裁员")

# 检索不足时的合规标注（:141）
REVIEW_NOTE_RE = re.compile(r"待律师人工复核|需律师人工复核|待律师复核|检索结果不足|检索不足|人工复核")

# 材料缺口清单
GAP_TITLE_RE = re.compile(r"材料缺口清单|材料缺口|缺口清单")
GAP_LEVEL_RE = re.compile(r"必需|强烈建议|可选|最低启动条件")
PENDING_MARK_RE = re.compile(r"待补充|待确认|未齐备|待提供|待核实")

# 矩阵表头列组（三联表）
MATRIX_COL_GROUPS: List[Tuple[str, re.Pattern]] = [
    ("争点", re.compile(r"争点|争议焦点|焦点")),
    ("我方主张/立场", re.compile(r"主张|立场|意见|观点")),
    ("事实", re.compile(r"事实")),
    ("证据", re.compile(r"证据|证明|锚点")),
    ("法律", re.compile(r"法律|法条|法规|依据")),
]

PLACEHOLDER_WORDS = {
    "待补充", "待填", "待填写", "待定", "待确认", "待完善", "待写", "略", "无", "暂无",
    "na", "n/a", "tbd", "todo", "xx", "xxx", "示例", "同上", "见上", "略述",
}
PLACEHOLDER_PUNCT_RE = re.compile(r"^[\s\-—–_.。、,，;；:：…·*#/\\|]+$")
PLACEHOLDER_BRACKET_RE = re.compile(r"^[\[\(（<【]?[^\]\)）>】]{0,10}[\]\)）>】]?$")

CN_DIGITS = {
    "零": 0, "〇": 0, "○": 0,
    "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}
CN_UNITS = {"十": 10, "百": 100, "千": 1000}

TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".text"}
MIN_FACT_LEN = 20          # 一条「实质事实段落」的最少字数（去空白后）
MIN_FOCUS_LEN = 40         # 一个争点节「有实质内容」的最少字数
MIN_MATRIX_CELL = 2        # 矩阵单元格最少字数
LOOKBACK_FOR_LAW = 120     # 裸条号向前查找《法律名》的字符窗口
UNANCHORED_MIN = 3         # 未锚定事实段落的拦截门槛（条）
UNANCHORED_RATIO = 0.5     # 未锚定事实段落的拦截门槛（占比）

MIN_BRIEF_LEN = 400        # 正式稿正文最少字数（去空白后），低于此视为无实质正文（P0⑩）
MIN_BRIEF_NEW_LEN = 200    # 正式稿须比提纲多出的「新正文」字数（提纲之外实质内容）
MIN_BRIEF_SECTION_HIT = 2  # 必备实质小节（事实与理由/法律依据/综上请求）至少命中数

# 正式稿必备「事实类」小节（覆盖一审/二审/仲裁各场景模板：案件事实 / 事实与理由 /
# 一审裁判要点 / 认定事实错误 等）
BRIEF_FACT_SECTION_RE = re.compile(
    r"案件事实|事实陈述|事实经过|事实\s*[与和及]?\s*理由|事实认定|一审裁判|裁判要点|"
    r"认定事实|裁判事实|裁决事实"
)
# 正式稿必备「法律类」小节或引用
BRIEF_LAW_SECTION_RE = re.compile(r"法律依据|法律适用|法律论证|法律规定|法条")

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class InputError(Exception):
    """输入层错误，退出码 2。"""


# ------------------------------------------------------------------ 小工具


def cn_num_to_int(text: str) -> Optional[int]:
    s = text.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    total, current, valid = 0, 0, False
    for ch in s:
        if ch in CN_DIGITS:
            current = CN_DIGITS[ch]
            valid = True
        elif ch in CN_UNITS:
            unit = CN_UNITS[ch]
            if current == 0:
                current = 1
            total += current * unit
            current = 0
            valid = True
        else:
            return None
    return total + current if valid else None


def norm(text: str) -> str:
    return re.sub(r"\s+", "", text)


def strip_markup(line: str) -> str:
    """去掉 markdown 标记，便于判断是否像标题。"""
    s = line.strip()
    s = re.sub(r"^[#>\-*\s|]+", "", s)
    s = s.replace("**", "").replace("*", "").strip()
    return s.rstrip("|").strip()


def heading_like(line: str) -> bool:
    return len(strip_markup(line)) <= 40


def is_table_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.count("|") >= 3


def is_separator_row(line: str) -> bool:
    return bool(re.fullmatch(r"[|\s:：\-—–]+", line.strip()))


def table_cells(line: str) -> List[str]:
    body = line.strip().strip("|")
    return [c.strip() for c in body.split("|")]


def is_placeholder(cell: str) -> bool:
    """单元格是否为占位/空壳。

    「待证」「待律师复核」「[证3-P2]」是 SKILL.md 认可的合规写法，不算占位。
    """
    s = norm(cell)
    if not s:
        return True
    if re.search(r"证\s*[" + NUM_CHARS + r"]|待证|《|第[" + NUM_CHARS + r"]+条", s):
        return False
    if s.lower() in PLACEHOLDER_WORDS:
        return True
    if PLACEHOLDER_PUNCT_RE.fullmatch(s):
        return True
    inner = re.sub(r"[\[\]\(\)（）<>【】]", "", s)
    if inner.lower() in PLACEHOLDER_WORDS:
        return True
    if len(s) < MIN_MATRIX_CELL and PLACEHOLDER_BRACKET_RE.fullmatch(s):
        return True
    return False


# ------------------------------------------------------------------ docx 读取
# 只用标准库 zipfile + ElementTree，避免 python-docx 依赖。


def _tag(name: str) -> str:
    return W + name


def _textbox_t_ids(element) -> Set[int]:
    ids: Set[int] = set()
    for box in element.iter(_tag("txbxContent")):
        for node in box.iter(_tag("t")):
            ids.add(id(node))
    return ids


def _para_text(para, skip_ids: Optional[Set[int]] = None) -> str:
    skip_ids = skip_ids if skip_ids is not None else _textbox_t_ids(para)
    parts: List[str] = []
    for node in para.iter():
        tag = node.tag
        if tag == _tag("t"):
            if id(node) not in skip_ids:
                parts.append(node.text or "")
        elif tag in (_tag("tab"), _tag("br"), _tag("cr")):
            parts.append(" ")
    return "".join(parts).strip()


def _cell_text(cell) -> str:
    parts: List[str] = []
    for child in cell:
        if child.tag == _tag("p"):
            text = _para_text(child)
            if text:
                parts.append(text)
        elif child.tag == _tag("tbl"):
            parts.extend(_table_lines(child))
    return " ".join(parts).strip()


def _table_lines(table) -> List[str]:
    """把表格渲染成便于统计的文本行。

    单列表格在中文法律文书里常被当作排版容器（整篇正文塞进一列），此时按普通段落
    输出；多列表格保留 markdown 行形式，便于按行做矩阵校验。
    """
    lines: List[str] = []
    for row in table.findall(_tag("tr")):
        cells = [_cell_text(tc) for tc in row.findall(_tag("tc"))]
        if not any(c for c in cells):
            continue
        filled = {c for c in cells if c}
        if len(cells) == 1 or len(filled) == 1:
            lines.extend(part for part in cells[0].splitlines() if part.strip())
        else:
            lines.append("| " + " | ".join(re.sub(r"\s+", " ", c) for c in cells) + " |")
    return lines


def _walk_blocks(element):
    """按文档顺序产出 w:p / w:tbl，穿透 sdt / sdtContent 等容器。"""
    for child in element:
        tag = child.tag
        if tag == _tag("p"):
            yield ("p", child)
        elif tag == _tag("tbl"):
            yield ("tbl", child)
        elif tag in (_tag("sdt"), _tag("sdtContent"), _tag("customXml")):
            for item in _walk_blocks(child):
                yield item


def _textbox_texts(element) -> List[str]:
    out: List[str] = []
    for box in element.iter(_tag("txbxContent")):
        for para in box.iter(_tag("p")):
            text = "".join(node.text or "" for node in para.iter(_tag("t"))).strip()
            if text:
                out.append(text)
    seen: Set[str] = set()
    uniq: List[str] = []
    for item in out:
        key = norm(item)
        if key and key not in seen:
            seen.add(key)
            uniq.append(item)
    return uniq


def load_docx(path: Path) -> Tuple[List[str], List[str]]:
    """读取 docx，返回（正文块列表, 页眉/页脚/文本框附加块列表）。"""
    if not zipfile.is_zipfile(path):
        raise InputError(f"文件不是合法 DOCX ZIP 容器：{path.name}（.doc 请先转 .docx）")
    blocks: List[str] = []
    extras: List[str] = []
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            if "word/document.xml" not in names:
                raise InputError(f"DOCX 缺少 word/document.xml：{path.name}")
            root = ET.fromstring(zf.read("word/document.xml"))
            body = root.find(_tag("body"))
            if body is None:
                raise InputError(f"DOCX 正文为空：{path.name}")
            for kind, node in _walk_blocks(body):
                if kind == "p":
                    blocks.append(_para_text(node))
                else:
                    blocks.extend(_table_lines(node))
            extras.extend(_textbox_texts(body))
            for name in sorted(names):
                if not re.fullmatch(r"word/(?:header|footer)\d*\.xml", name):
                    continue
                part = ET.fromstring(zf.read(name))
                for kind, node in _walk_blocks(part):
                    if kind == "p":
                        text = _para_text(node)
                        if text:
                            extras.append(text)
                    else:
                        extras.extend(_table_lines(node))
                extras.extend(_textbox_texts(part))
    except InputError:
        raise
    except ET.ParseError as exc:
        raise InputError(f"DOCX XML 解析失败：{exc}")
    except Exception as exc:  # zip 损坏等
        raise InputError(f"无法读取 DOCX：{exc}")

    seen: Set[str] = set()
    uniq_extras: List[str] = []
    for item in extras:
        key = norm(item)
        if key and key not in seen:
            seen.add(key)
            uniq_extras.append(item)
    return blocks, uniq_extras


def load_document(path: Path) -> Tuple[List[str], List[str]]:
    """读取 md/txt/docx，返回（正文块列表, 附加块列表）。"""
    suffix = path.suffix.lower()
    if suffix not in TEXT_SUFFIXES and suffix != ".docx":
        raise InputError(
            f"不支持的文件类型：{path.name}"
            "（支持 .md/.markdown/.txt/.docx；.doc 请先转 .docx）"
        )
    if not path.exists():
        raise InputError(f"文件不存在：{path}")
    if path.stat().st_size == 0:
        raise InputError(f"文件为空：{path.name}")
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
        raise InputError(f"文件内容为空：{path.name}")
    return content.splitlines(), []


class Doc:
    """一份被校验的文书。"""

    def __init__(self, path: Path, label: str):
        self.path = path
        self.label = label
        self.blocks, self.extras = load_document(path)
        self.text = "\n".join(self.blocks + self.extras)
        self.lines = self.text.splitlines()
        self.head = [b for b in self.blocks if b.strip()][:15]

    @property
    def name(self) -> str:
        return self.path.name


# ------------------------------------------------------------------ 章节切分


def chapter_spans(lines: Sequence[str], keyword_re: re.Pattern) -> List[Tuple[int, int]]:
    """定位标题命中 keyword_re 的一级章节区间 [start, end)。

    章节以下一个「不含该关键词的一级标题」或文件结束为终点；找不到一级标题时退化
    为「命中关键词的任意标题行 → 下一个命中/结束」。
    """
    tops = [idx for idx, line in enumerate(lines)
            if TOP_HEAD_RE.match(line.strip()) and heading_like(line)
            and not is_table_row(line)]
    starts = [idx for idx in tops if keyword_re.search(strip_markup(lines[idx]))]
    spans: List[Tuple[int, int]] = []
    if starts:
        for start in starts:
            end = len(lines)
            for idx in tops:
                if idx > start and not keyword_re.search(strip_markup(lines[idx])):
                    end = idx
                    break
            spans.append((start, end))
        return spans
    # 退化路径：无一级标题体系（例如纯 markdown ### 分节）
    md_heads = [idx for idx, line in enumerate(lines)
                if re.match(r"^#{1,6}\s", line.strip()) and heading_like(line)]
    starts = [idx for idx in md_heads if keyword_re.search(strip_markup(lines[idx]))]
    for start in starts:
        level = len(re.match(r"^#+", lines[start].strip()).group(0))
        end = len(lines)
        for idx in md_heads:
            if idx <= start:
                continue
            lv = len(re.match(r"^#+", lines[idx].strip()).group(0))
            if lv <= level and not keyword_re.search(strip_markup(lines[idx])):
                end = idx
                break
        spans.append((start, end))
    return spans


def split_items(lines: Sequence[str], item_re: re.Pattern) -> List[Tuple[str, List[str]]]:
    """按 item_re 命中的小标题把区间切成条目：(标题, 内容行)。"""
    items: List[Tuple[str, List[str]]] = []
    title: Optional[str] = None
    buf: List[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and item_re.match(stripped) and heading_like(line) \
                and not is_table_row(line):
            if title is not None:
                items.append((title, buf))
            title, buf = stripped, []
            continue
        if title is not None:
            buf.append(line)
    if title is not None:
        items.append((title, buf))
    return items


def focus_items(doc: "Doc") -> List[Tuple[str, List[str]]]:
    """抽取争点条目（争点/焦点节）。"""
    spans = chapter_spans(doc.lines, FOCUS_CHAPTER_RE)
    items: List[Tuple[str, List[str]]] = []
    for start, end in spans:
        items.extend(split_items(doc.lines[start + 1:end], FOCUS_ITEM_RE))
    if items:
        return items
    # 无争点章节时，全局找「焦点N/争点N」标题
    return split_items(doc.lines, re.compile(
        r"^(?:#{1,6}\s*)?(?:\*{1,2})?\s*(?:争议)?(?:焦点|争点)\s*[" + NUM_CHARS + r"]{1,3}"
    ))


def read_tables(lines: Sequence[str]) -> List[List[List[str]]]:
    """抽取所有 markdown/docx 表格，返回 [表[行[单元格]]]。"""
    tables: List[List[List[str]]] = []
    current: List[List[str]] = []
    for line in lines:
        if is_table_row(line):
            if is_separator_row(line):
                continue
            current.append(table_cells(line))
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


# ------------------------------------------------------------------ 法条引用


def sentence_head(text: str, pos: int) -> str:
    start = max((text.rfind(ch, 0, pos) for ch in "。；;！!？?\n"), default=-1)
    return text[start + 1:pos]


def statute_citations(text: str) -> List[re.Match]:
    return [m for m in CITATION_RE.finditer(text)
            if STATUTE_NAME_RE.search(m.group(1))]


def law_name_nearby(text: str, pos: int) -> bool:
    window = text[max(0, pos - LOOKBACK_FOR_LAW):pos]
    return any(STATUTE_NAME_RE.search(name)
               for name in re.findall(r"《([^《》\n]{2,80}?)》", window))


def classify_bare_articles(
    text: str, citations: Sequence[re.Match]
) -> Tuple[List[re.Match], List[re.Match], List[re.Match]]:
    """把未被《法名》直接包裹的第X条分成：非法条条号 / 可归属 / 真裸条号。"""
    spans = [m.span() for m in citations]
    has_statute = bool(statute_citations(text))
    non_statute: List[re.Match] = []
    attributed: List[re.Match] = []
    bare: List[re.Match] = []
    for m in ARTICLE_RE.finditer(text):
        if any(s <= m.start() < e for s, e in spans):
            continue
        prefix = text[max(0, m.start() - 20):m.start()]
        if NON_STATUTE_PREFIX_RE.search(prefix):
            non_statute.append(m)
            continue
        if BACKREF_RE.search(prefix) and has_statute:
            attributed.append(m)
            continue
        head = sentence_head(text, m.start())
        if any(STATUTE_NAME_RE.search(name)
               for name in re.findall(r"《([^《》\n]{2,80}?)》", head)):
            attributed.append(m)
            continue
        if law_name_nearby(text, m.start()):
            attributed.append(m)
            continue
        bare.append(m)
    return non_statute, attributed, bare


# ------------------------------------------------------------------ 各项判据


def declared_institution(doc: "Doc") -> Optional[str]:
    """从首部场景标签（场景/机构/审理机构）判断声明的审理机构。

    只认显式声明，避免把正文里「仲裁协议效力」「《仲裁法》」这类正当提及误判。
    """
    for line in doc.head:
        flat = re.sub(r"[*#>`\s]", "", line)
        if not re.search(r"(?:场景|机构|审理机构|institution)[：:]", flat):
            continue
        value = re.split(r"[：:]", flat, maxsplit=1)[-1]
        court = bool(re.search(r"法院|court", value))
        arbi = bool(re.search(r"仲裁|arbitration", value))
        if court and not arbi:
            return "court"
        if arbi and not court:
            return "arbitration"
    return None


def check_routing(docs: Sequence["Doc"], strict: bool,
                  checks: List[str], warns: List[str], errors: List[str]) -> None:
    """判据 1：场景路由（机构 / 审级 / 我方地位）+ 称谓不混用。"""
    for doc in docs:
        text = doc.text
        court = bool(INSTITUTION_COURT_RE.search(text))
        arbi = bool(INSTITUTION_ARBI_RE.search(text))
        stage = STAGE_RE.search(text)
        role = ROLE_DECL_RE.search(text)
        missing: List[str] = []
        if not (court or arbi):
            missing.append("审理机构（人民法院/仲裁委员会）")
        if not stage:
            missing.append("审级（一审/二审/再审/仲裁）")
        if not role:
            missing.append("我方地位（原告/被告/上诉人/被上诉人/申请人/被申请人）")
        if missing:
            msg = ("场景路由（%s）：首部未体现 %s；SKILL.md:26/:36 要求三个维度写入"
                   "提纲首部与正式稿首部" % (doc.label, "、".join(missing)))
            (errors if strict else warns).append(msg)
        else:
            inst = "法院" if court and not arbi else ("仲裁" if arbi and not court else "法院+仲裁均出现")
            checks.append("场景路由（%s）：机构=%s、审级=「%s」、我方地位可识别"
                          % (doc.label, inst, norm(stage.group(0))))
        # 称谓混用①：法庭称谓与仲裁称谓同时出现（两者均为纯称谓词）
        m_court_sal = SALUTATION_COURT_RE.search(text)
        m_arbi_sal = SALUTATION_ARBI_RE.search(text)
        if m_court_sal and m_arbi_sal:
            errors.append(
                "称谓混用（%s）：同时出现「%s」与「%s」，违反 SKILL.md:47 称谓强制规则"
                % (doc.label, m_court_sal.group(0), m_arbi_sal.group(0)))
            continue
        # 称谓混用②：与首部声明的场景标签相反的称谓
        declared = declared_institution(doc)
        if declared == "court" and m_arbi_sal:
            errors.append(
                "称谓混用（%s）：首部场景标签声明为法院审理，正文却使用仲裁称谓「%s」，"
                "违反 SKILL.md:47 称谓强制规则" % (doc.label, m_arbi_sal.group(0)))
        elif declared == "arbitration" and m_court_sal:
            errors.append(
                "称谓混用（%s）：首部场景标签声明为仲裁，正文却使用法庭称谓「%s」，"
                "违反 SKILL.md:47 称谓强制规则" % (doc.label, m_court_sal.group(0)))
        elif court and arbi and declared is None:
            warns.append("称谓提示（%s）：正文同时出现法院与仲裁机构表述，且首部无场景"
                         "标签，请人工确认称谓一致（SKILL.md:47）" % doc.label)


def check_dual_output(outline: "Doc", brief: Optional["Doc"], outline_only: bool,
                      checks: List[str], warns: List[str], errors: List[str]) -> None:
    """判据 2：双输出规范与提纲—正式稿对应关系。"""
    head_text = norm("\n".join(outline.head))
    if OUTLINE_TITLE_RE.search(head_text) and BRIEF_TITLE_RE.search(head_text):
        checks.append("双输出-提纲身份：文首标题含「代理词」+「提纲」")
    elif OUTLINE_TITLE_RE.search(norm(outline.text)) and BRIEF_TITLE_RE.search(norm(outline.text)):
        warns.append("双输出-提纲身份：文首未见「代理词提纲」标题（仅在正文中出现），已按齐备计")
    else:
        errors.append("双输出-提纲身份：%s 文首缺少「《XX案》代理词提纲」类标题"
                      "（:143 要求先产出 Markdown 提纲版）" % outline.name)

    if brief is not None:
        # --outline-only 只豁免“未交付 Word”时的对应关系校验；一旦传入 --brief，
        # 正式稿标题等强制校验照常执行——实质内容/必备结构/引用格式不可跳过（P0⑪）。
        if BRIEF_TITLE_RE.search(norm("\n".join(brief.head))):
            checks.append("双输出-Word 正式稿：文首标题含「代理词/代理意见」")
        else:
            errors.append("双输出-Word 正式稿：%s 文首缺少「代理词/仲裁代理意见」标题"
                          % brief.name)
    elif outline_only:
        warns.append("双输出-Word 正式稿：未传 --brief（--outline-only：SKILL.md:116 "
                     "上游仅要结构化内容），跳过 Word 对应关系校验")

    # 免责声明（:239 Word 与 Markdown 均须包含）
    for doc in [d for d in (outline, brief) if d is not None]:
        if DISCLAIMER_A_RE.search(doc.text) and DISCLAIMER_B_RE.search(doc.text):
            checks.append("文首免责声明（%s）：齐备" % doc.label)
        else:
            errors.append("文首免责声明（%s）：缺失或不完整，SKILL.md:239 要求 Word 与"
                          " Markdown 均含「辅助生成 + 须经承办律师审核」表述" % doc.label)

    if brief is None:
        # 未交付 Word（--outline-only）：争点对应与正式稿格式项不适用可跳过；
        # 但提纲自身的结尾请求（SKILL.md:149 必备结构）仍强制校验，不可随开关免检（P0⑪）。
        if CLOSING_REQUEST_RE.search(outline.text):
            checks.append("结尾请求（提纲）：找到「综上所述/恳请…」类请求事项")
        else:
            errors.append("结尾请求（提纲）：缺少结尾请求事项（:149/:131 提纲亦须含与"
                          "诉请/上诉请求/仲裁请求对齐的结尾请求）")
        return

    # 争点对应关系（:205 Word 争点顺序与提纲一致）
    o_items = focus_items(outline)
    b_items = focus_items(brief)
    if not o_items:
        return  # 争点缺失由判据 3 统一拦截，避免重复报错
    if not b_items:
        errors.append("双输出-争点对应：正式稿未识别到争议焦点分节（提纲有 %d 个争点），"
                      "违反 :197/:205「Word 正文在提纲基础上扩写，争点顺序一致」"
                      % len(o_items))
    elif len(b_items) < len(o_items):
        errors.append("双输出-争点对应：正式稿争点节 %d 个 < 提纲争点 %d 个，疑漏写争点"
                      "（提纲争点：%s）"
                      % (len(b_items), len(o_items),
                         "；".join(strip_markup(t)[:20] for t, _ in o_items)))
    else:
        checks.append("双输出-争点对应：提纲 %d 个争点 / 正式稿 %d 个争点节，无漏项"
                      % (len(o_items), len(b_items)))
        if len(b_items) > len(o_items):
            warns.append("双输出-争点对应：正式稿争点节多于提纲，请确认是否为提纲未同步")

    # 结尾请求（:149 与诉请/上诉请求/仲裁请求对齐）
    for doc in (outline, brief):
        if CLOSING_REQUEST_RE.search(doc.text):
            checks.append("结尾请求（%s）：找到「综上所述/恳请…」类请求事项" % doc.label)
        else:
            errors.append("结尾请求（%s）：缺少结尾请求事项（:149/:131 结尾请求须与"
                          "诉请/上诉请求/仲裁请求对齐）" % doc.label)

    # 正式稿提交格式项
    format_items = (
        ("法庭/仲裁庭称谓语（尊敬的审判长…/尊敬的仲裁庭…）", bool(SALUTATION_ANY_RE.search(brief.text))),
        ("落款-代理人", bool(SIGN_AGENT_RE.search(brief.text))),
        ("落款-律师事务所", bool(SIGN_FIRM_RE.search(brief.text))),
        ("落款-日期", bool(SIGN_DATE_RE.search(brief.text))),
    )
    for name, ok in format_items:
        if ok:
            checks.append("正式稿提交格式项-%s：齐备" % name)
        else:
            errors.append("正式稿提交格式项-%s：缺失（见 references/"
                          "pleading-brief-template.md 通用首部与落款）" % name)


def _brief_novel_len(outline_norm: str, brief_norm: str) -> int:
    """提纲之外的「新正文」字数：difflib 求两份文本的匹配块，未匹配字符数即近似新增内容。

    用于拦截「把提纲当正式稿二次提交」：合法正式稿在提纲基础上扩写，新增内容通常占
    正文大部分；直接复制提纲（或仅改标题/换行）时新增内容趋近于 0。
    """
    if not outline_norm:
        return len(brief_norm)
    matched = 0
    for block in difflib.SequenceMatcher(
            None, outline_norm, brief_norm, autojunk=False).get_matching_blocks():
        matched += block.size
    return len(brief_norm) - matched


def check_brief_substance(outline: "Doc", brief: "Doc",
                          checks: List[str], warns: List[str],
                          errors: List[str]) -> None:
    """判据 2 补充：正式稿必须是提纲之外的实质正文（P0⑩：禁止提纲冒充正式稿）。

    三道防线，任一不过即拦：
    1. 正式稿与提纲同一文件或内容逐字相同 → 拦；
    2. 正文去空白后 < MIN_BRIEF_LEN，或提纲之外的新正文 < MIN_BRIEF_NEW_LEN → 拦；
    3. 缺法庭/仲裁庭称谓语，或「事实与理由/法律依据/综上请求」实质小节命中 < 2/3 → 拦。
    """
    o_norm = norm(outline.text)
    b_norm = norm(brief.text)
    if not b_norm:
        errors.append("双输出-正式稿为空：%s 未读到任何正文文字" % brief.name)
        return
    if brief.path == outline.path or b_norm == o_norm:
        errors.append("双输出-正式稿与提纲相同：--brief（%s）与 --outline（%s）为同一文件"
                      "或内容逐字相同，禁止把提纲当正式稿二次提交（SKILL.md:158/:197 "
                      "要求 Word 在提纲基础上扩写）" % (brief.name, outline.name))
        return
    problems: List[str] = []
    if len(b_norm) < MIN_BRIEF_LEN:
        problems.append("正文去空白后仅 %d 字 < 阈值 %d 字" % (len(b_norm), MIN_BRIEF_LEN))
    new_len = _brief_novel_len(o_norm, b_norm)
    if new_len < MIN_BRIEF_NEW_LEN:
        problems.append("提纲之外的新正文仅 %d 字 < 阈值 %d 字（与提纲重复 %d 字），"
                        "疑似复制提纲冒充正式稿"
                        % (new_len, MIN_BRIEF_NEW_LEN, len(b_norm) - new_len))
    if not SALUTATION_ANY_RE.search(brief.text):
        problems.append("缺法庭/仲裁庭称谓语（尊敬的审判长/审判员/仲裁庭…）")
    hits = 0
    if BRIEF_FACT_SECTION_RE.search(brief.text):
        hits += 1
    if BRIEF_LAW_SECTION_RE.search(brief.text) or statute_citations(brief.text):
        hits += 1
    if CLOSING_REQUEST_RE.search(brief.text):
        hits += 1
    if hits < MIN_BRIEF_SECTION_HIT:
        problems.append("实质小节不足（%d/3 命中：事实与理由/法律依据/综上请求）" % hits)
    if problems:
        errors.append("双输出-正式稿非实质正文（%s）：%s；正式稿须为提纲之外扩写的完整"
                      "代理词正文（SKILL.md:158/:197）" % (brief.name, "；".join(problems)))
    else:
        checks.append("双输出-正式稿实质正文（%s）：正文 %d 字、提纲之外新正文 %d 字、"
                      "称谓与实质小节齐备" % (brief.name, len(b_norm), new_len))


def match_matrix_table(table: Sequence[Sequence[str]]) -> Optional[Tuple[List[str], int]]:
    """判断表格是否为「事实-证据-法律三联表」；返回（命中列组, 表头行号）。"""
    for row_idx, row in enumerate(table[:2]):
        header = " ".join(row)
        hit = [name for name, pattern in MATRIX_COL_GROUPS if pattern.search(header)]
        need = {"争点", "证据", "法律"}
        if need.issubset(set(hit)) and len(hit) >= 4:
            return hit, row_idx
    return None


def check_focus_matrix(docs: Sequence["Doc"], strict: bool,
                       checks: List[str], warns: List[str], errors: List[str]) -> None:
    """判据 3：争点与主张矩阵缺失 / 空壳。

    合规渲染形式二选一：①三联表；②提纲「争议焦点逐项」分节。
    """
    matrix_hit: Optional[Tuple[str, List[str], int, int]] = None
    for doc in docs:
        for table in read_tables(doc.lines):
            matched = match_matrix_table(table)
            if not matched:
                continue
            hit, header_idx = matched
            header = table[header_idx]
            rows = [r for r in table[header_idx + 1:] if any(c.strip() for c in r)]
            solid = 0
            for row in rows:
                cells = {}
                for pos, title in enumerate(header):
                    for name, pattern in MATRIX_COL_GROUPS:
                        if pattern.search(title) and name not in cells:
                            cells[name] = row[pos] if pos < len(row) else ""
                needed = [cells.get(k, "") for k in ("证据", "法律")]
                if all(not is_placeholder(c) for c in needed) \
                        and not is_placeholder(cells.get("争点", "")):
                    solid += 1
            if matrix_hit is None or solid > matrix_hit[3]:
                matrix_hit = (doc.label, hit, len(rows), solid)
    if matrix_hit and matrix_hit[3] >= 1:
        checks.append("争点矩阵-三联表（%s）：列组命中 %s；有效数据行 %d/%d"
                      % (matrix_hit[0], "/".join(matrix_hit[1]),
                         matrix_hit[3], matrix_hit[2]))
    elif matrix_hit:
        warns.append("争点矩阵-三联表（%s）：表头齐备但数据行「证据锚点/法律依据」全为"
                     "占位，改按提纲争点分节校验" % matrix_hit[0])

    # 提纲争点分节
    section_ok = False
    for doc in docs:
        items = focus_items(doc)
        if not items:
            continue
        solid = [(t, b) for t, b in items
                 if len(norm("\n".join([t] + b))) >= MIN_FOCUS_LEN]
        if not solid:
            errors.append("争点矩阵-空壳（%s）：识别到 %d 个争点小标题，但全部无实质内容"
                          "（每节正文不足 %d 字），属模板空壳"
                          % (doc.label, len(items), MIN_FOCUS_LEN))
            continue
        # 核心争点（★★★★★ / ★★★★☆）须含证据要素与法律要素
        core = [(t, b) for t, b in solid if re.search(r"★{4,5}", t + "\n".join(b))]
        if not core:
            core = [solid[0]]
        bad: List[str] = []
        for title, body in core:
            block = "\n".join([title] + body)
            has_evi = bool(EVIDENCE_REF_RE.search(block)) or "证据" in block
            has_law = bool(CITATION_RE.search(block)) or bool(
                re.search(r"法律适用|法律依据|法条|司法解释|第[" + NUM_CHARS + r"]+条", block))
            lack = []
            if not has_evi:
                lack.append("证据要素")
            if not has_law:
                lack.append("法律要素")
            if lack:
                bad.append("「%s」缺 %s" % (strip_markup(title)[:24], "+".join(lack)))
        if bad:
            msg = ("争点矩阵-核心争点要素不全（%s）：%s；SKILL.md:135/:148 要求核心争点"
                   "填齐「立场/事实证据/法律适用/反驳」" % (doc.label, "；".join(bad)))
            (errors if strict else warns).append(msg)
        else:
            checks.append("争点矩阵-争点分节（%s）：%d 个争点，其中核心争点 %d 个证据与"
                          "法律要素齐备" % (doc.label, len(solid), len(core)))
        section_ok = True

    if not section_ok and not (matrix_hit and matrix_hit[3] >= 1):
        msg = ("争点矩阵缺失：既未找到「事实-证据-法律三联表」（表头需含争点/主张/事实/"
               "证据/法律），也未找到「争议焦点逐项」分节（焦点1/争点一/（一）关于…）；"
               "违反 SKILL.md:131 阶段二与 :104 争点驱动")
        (errors if strict else warns).append(msg)


def evidence_list_numbers(docs: Sequence["Doc"]) -> Set[Any]:
    """从「证据清单/证据目录」表格中抽取证据序号集合（仅用于提示性交叉比对）。"""
    numbers: Set[Any] = set()
    for doc in docs:
        for idx, line in enumerate(doc.lines):
            if not re.search(r"证据清单|证据目录|证据列表", strip_markup(line)):
                continue
            for probe in doc.lines[idx: idx + 80]:
                if not is_table_row(probe) or is_separator_row(probe):
                    continue
                first = table_cells(probe)[0]
                num = cn_num_to_int(norm(first))
                if num is not None:
                    numbers.add(num)
    return numbers


def check_evidence_anchor(docs: Sequence["Doc"], strict: bool,
                          checks: List[str], warns: List[str], errors: List[str]) -> None:
    """判据 4：证据锚定（纯形式判据，不做语义推断）。"""
    total_refs = 0
    total_facts = 0
    unanchored: List[Tuple[str, str]] = []
    scoped_docs = 0
    for doc in docs:
        total_refs += len(EVIDENCE_REF_RE.findall(doc.text))
        spans = chapter_spans(doc.lines, FACT_CHAPTER_RE)
        if not spans:
            continue
        scoped_docs += 1
        for start, end in spans:
            exempt = False
            for line in doc.lines[start + 1:end]:
                stripped = line.strip()
                if not stripped or is_separator_row(stripped):
                    continue
                bare = strip_markup(stripped)
                if heading_like(stripped) and not is_table_row(stripped) \
                        and (SUBHEAD_RE.match(stripped) or re.match(r"^#{1,6}\s", stripped)):
                    exempt = bool(FACT_EXEMPT_SECTION_RE.search(bare))
                    continue
                if exempt:
                    continue
                if is_table_row(stripped) and re.search(
                        r"对方主张|我方回应|证据|序号", stripped):
                    # 表头行跳过
                    if not re.search(r"[。；;]", stripped) and len(norm(stripped)) < 40:
                        continue
                if len(norm(bare)) < MIN_FACT_LEN:
                    continue
                if FACT_EXEMPT_MARK_RE.search(bare):
                    continue
                total_facts += 1
                if not EVIDENCE_REF_RE.search(stripped):
                    unanchored.append((doc.label, bare[:60]))

    if not scoped_docs:
        msg = ("证据锚定：未定位到事实型章节（案件事实/事实陈述/事实与理由），"
               "无法核验证据锚定")
        (errors if strict else warns).append(msg)
        return

    if total_refs == 0:
        msg = ("证据锚定：全文未出现任何证据编号引用（[证X-PX]/证3/原告证据3/附件2），"
               "违反 SKILL.md:92「所有事实陈述必须标注证据索引」")
        (errors if strict else warns).append(msg)
    elif total_facts and len(unanchored) >= UNANCHORED_MIN \
            and len(unanchored) / total_facts > UNANCHORED_RATIO:
        errors.append("证据锚定不足：事实段落 %d 条中 %d 条无证据编号引用（超过 %d%%），"
                      "违反 SKILL.md:92；无证据支撑的事实须标注「待证事实」"
                      % (total_facts, len(unanchored), int(UNANCHORED_RATIO * 100)))
        for label, snippet in unanchored[:5]:
            errors.append("  未锚定事实（%s）：%s…" % (label, snippet))
        if len(unanchored) > 5:
            errors.append("  共 %d 条未锚定事实，仅列出前 5 条" % len(unanchored))
    else:
        checks.append("证据锚定：事实段落 %d 条，未带证据编号 %d 条（阈值：>=%d 条且 >%d%%），"
                      "全文证据编号引用 %d 处"
                      % (total_facts, len(unanchored), UNANCHORED_MIN,
                         int(UNANCHORED_RATIO * 100), total_refs))

    # 交叉比对证据清单（提示性，不拦截）
    listed = evidence_list_numbers(docs)
    if listed:
        cited: Set[Any] = set()
        for doc in docs:
            for m in EVIDENCE_NO_RE.finditer(doc.text):
                num = cn_num_to_int(m.group(1))
                if num is not None:
                    cited.add(num)
        outside = sorted(n for n in cited if n not in listed)
        if outside:
            warns.append("证据清单交叉比对（仅提示）：被引证据编号 %s 未出现在证据清单"
                         "序号集合 %s 中，请人工确认是否引用了未列入清单的证据"
                         % (outside[:10], sorted(listed)[:10]))
        else:
            checks.append("证据清单交叉比对：被引证据编号均落在证据清单序号集合内")


def check_citation_format(docs: Sequence["Doc"], strict: bool,
                          checks: List[str], warns: List[str], errors: List[str]) -> None:
    """判据 5：法条引用格式（带《法律名》+ 条号；防误拦合同/章程条号）。"""
    all_bare: List[Tuple[str, str]] = []
    citations_n = 0
    statutes_n = 0
    attributed_n = 0
    non_statute_n = 0
    for doc in docs:
        citations = list(CITATION_RE.finditer(doc.text))
        citations_n += len(citations)
        statutes_n += len(statute_citations(doc.text))
        non_statute, attributed, bare = classify_bare_articles(doc.text, citations)
        attributed_n += len(attributed)
        non_statute_n += len(non_statute)
        for m in bare:
            ctx = doc.text[max(0, m.start() - 15): m.end() + 5].replace("\n", " ")
            all_bare.append((doc.label, ctx))

    if all_bare:
        for label, ctx in all_bare[:5]:
            errors.append("法条引用格式（%s）：条号缺少《法律名》 → …%s…" % (label, ctx))
        if len(all_bare) > 5:
            errors.append("法条引用格式：共 %d 处裸条号，仅列出前 5 处" % len(all_bare))
    if statutes_n == 0:
        note = any(REVIEW_NOTE_RE.search(doc.text) for doc in docs)
        if note:
            checks.append("法条引用：全文无《法律名》第X条，但已按 :141 标注"
                          "「检索结果不足/需律师人工复核」")
        else:
            msg = ("法条引用缺失：全文无《法律名》+条号的法律依据，且未按 SKILL.md:141"
                   "标注「检索结果不足，以下法律适用需律师人工复核」；违反 :95 法律意见"
                   "来源要求")
            (errors if strict else warns).append(msg)
    elif not all_bare:
        parts = ["%d 处《法律名》+条号引用" % citations_n]
        if attributed_n:
            parts.append("%d 处同句/近邻已归属法律名的条号" % attributed_n)
        if non_statute_n:
            parts.append("%d 处非法条条号（合同/章程等，不作要求）" % non_statute_n)
        checks.append("法条引用格式：" + "、".join(parts) + "，未见裸条号")


def check_incomplete_delivery(outline: "Doc", brief: Optional["Doc"], gap: Optional["Doc"],
                              checks: List[str], warns: List[str],
                              errors: List[str]) -> None:
    """判据 6：材料不足时的交付规范（:72/:151/:207）。"""
    if brief is not None:
        errors.append("材料不足却出正式稿：--material-status incomplete 时传入了 --brief"
                      "（%s）；SKILL.md:84/:207 禁止材料不足时生成 Word 正式代理词"
                      % brief.name)

    gap_docs = [d for d in (outline, gap) if d is not None]
    found_doc = None
    structured = False
    heading_ok = False
    for doc in gap_docs:
        for idx, line in enumerate(doc.lines):
            if not GAP_TITLE_RE.search(strip_markup(line)):
                continue
            found_doc = doc
            if re.match(r"^#{1,3}\s", line.strip()) or TOP_HEAD_RE.match(line.strip()) \
                    or heading_like(line):
                heading_ok = True
            tail = doc.lines[idx:]
            rows = sum(1 for l in tail if is_table_row(l) and not is_separator_row(l))
            levels = len(set(m.group(0) for l in tail for m in GAP_LEVEL_RE.finditer(l)))
            if rows >= 2 or levels >= 2:
                structured = True
            break
        if found_doc:
            break

    if found_doc is None:
        errors.append("材料缺口清单缺失：材料不足时必须在空白提纲之后附完整《材料缺口"
                      "清单》（SKILL.md:74/:151，references/material-gap-checklist.md）")
    elif not heading_ok:
        errors.append("材料缺口清单未单独成章：仅在正文中提及「材料缺口清单」，"
                      "违反 material-gap-checklist「禁止埋在提纲中间某一节」")
    elif not structured:
        errors.append("材料缺口清单非结构化：未见「必需/强烈建议/可选」分级或清单表格，"
                      "SKILL.md:83 禁止用一句话代替结构化缺口清单")
    else:
        checks.append("材料缺口清单（%s）：单独成章且含分级/表格结构" % found_doc.label)

    if PENDING_MARK_RE.search(outline.text):
        checks.append("空白提纲占位：已按 :78 用「待补充」等占位，未编造具体论证")
    else:
        errors.append("空白提纲占位缺失：材料不足时争点/事实/证据处须写「待补充」占位"
                      "（SKILL.md:78），未见任何占位标记，存在编造内容风险")

    if DISCLAIMER_A_RE.search(outline.text) and DISCLAIMER_B_RE.search(outline.text):
        checks.append("文首免责声明（提纲）：齐备")
    else:
        errors.append("文首免责声明（提纲）：缺失或不完整（SKILL.md:239）")


# ------------------------------------------------------------------ 主流程


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="代理词交付门禁：场景路由 / 双输出对应 / 争点矩阵（防空壳）/ "
                    "证据锚定 / 法条引用格式 / 材料不足交付规范。支持 md/txt/docx。",
        epilog=(
            "判据口径：①场景路由=机构+审级+我方地位三维可识别，且法庭称谓与仲裁称谓"
            "不混用；②双输出=提纲身份+正式稿存在（或 --outline-only 且未交付 Word）+"
            "正式稿须为提纲之外的实质正文（长度/称谓/实质小节/不得与提纲逐句相同）+"
            "正式稿争点节数不少于提纲争点数+两份均含免责声明+落款齐备；--outline-only"
            "仅在未传 --brief 时生效；③争点矩阵=三联表或提纲争点分节二者之一，核心争点"
            "（★★★★★/★★★★☆）须有证据与法律要素；"
            "④证据锚定=事实章节内实质段落须带证据编号（[证X-PX]/证3/原告证据3/附件2），"
            "「无争议·对方自认」小节与标注「待证事实」的段落豁免，仅当全文无任何证据"
            "编号、或未锚定段落>=3条且占比>50% 时拦截，不做语义推断；⑤法条须带《法名》"
            "+条号，「合同第三条」「章程第五条」不计；⑥材料不足=必附结构化缺口清单+"
            "留「待补充」占位+不得交付 Word。退出码：0 通过 / 1 拦截 / 2 输入错误。"
        ),
    )
    parser.add_argument("--outline", "--md", dest="outline", required=True, type=Path,
                        help="Markdown 提纲版路径（.md/.markdown/.txt/.docx）")
    parser.add_argument("--brief", "--docx", "--word", dest="brief", type=Path,
                        default=None,
                        help="Word 正式代理词路径（.docx，也接受 md 复核）；材料齐备时"
                             "必填，除非显式 --outline-only")
    parser.add_argument("--material-status", dest="status", default=None,
                        choices=["complete", "incomplete"],
                        help="【必填】材料是否达最低启动条件：complete=齐备（走完整判据）；"
                             "incomplete=不足（仅校验交付规范，禁止交付 Word）")
    parser.add_argument("--outline-only", action="store_true",
                        help="材料齐备但上游仅要结构化内容（SKILL.md:116），跳过 Word 校验")
    parser.add_argument("--gap-checklist", dest="gap", type=Path, default=None,
                        help="材料缺口清单单独成文时的路径（默认在 --outline 同文件内查找）")
    parser.add_argument("--matrix", dest="matrix", type=Path, default=None,
                        help="事实-证据-法律三联表单独成文时的路径（可选）")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.status is None:
        print(
            "输入错误：缺少 --material-status。\n"
            "  材料是否达最低启动条件决定两条相反判据（该不该出 Word、该不该有缺口清单），"
            "本门禁不做静默放过。\n"
            "  例（材料齐备）：python3 scripts/validate_pleading_brief.py "
            "--outline 提纲.md --brief 代理词.docx --material-status complete\n"
            "  例（材料不足）：python3 scripts/validate_pleading_brief.py "
            "--outline 空白提纲.md --material-status incomplete",
            file=sys.stderr,
        )
        return 2
    if args.status == "complete" and args.brief is None and not args.outline_only:
        print(
            "输入错误：--material-status complete 时缺少 --brief。\n"
            "  SKILL.md:158/:197 要求材料齐备时交付 Word 正式代理词；若确属 SKILL.md:116"
            "「上游仅要结构化内容」，请显式加 --outline-only。",
            file=sys.stderr,
        )
        return 2
    if args.status == "incomplete" and args.outline_only:
        print("输入错误：--material-status incomplete 与 --outline-only 冲突"
              "（材料不足本就只交付提纲 + 缺口清单）", file=sys.stderr)
        return 2

    try:
        outline = Doc(args.outline, "提纲")
        brief = Doc(args.brief, "正式稿") if args.brief is not None else None
        gap = Doc(args.gap, "缺口清单") if args.gap is not None else None
        matrix = Doc(args.matrix, "三联表") if args.matrix is not None else None
    except InputError as exc:
        print(f"输入错误：{exc}", file=sys.stderr)
        return 2

    checks: List[str] = []
    warns: List[str] = []
    errors: List[str] = []

    for doc in [d for d in (outline, brief, gap, matrix) if d is not None]:
        if doc.extras:
            warns.append("已额外读取 %s 的页眉/页脚/文本框 %d 段文字参与校验"
                         % (doc.name, len(doc.extras)))

    complete = args.status == "complete"
    docs = [d for d in (outline, brief, matrix) if d is not None]

    check_routing(docs if complete else [outline], complete, checks, warns, errors)

    if complete:
        check_dual_output(outline, brief, args.outline_only, checks, warns, errors)
        if brief is not None:
            check_brief_substance(outline, brief, checks, warns, errors)
        check_focus_matrix(docs, True, checks, warns, errors)
        check_evidence_anchor(docs, True, checks, warns, errors)
        check_citation_format(docs, True, checks, warns, errors)
    else:
        check_incomplete_delivery(outline, brief, gap, checks, warns, errors)
        check_focus_matrix([outline] + ([matrix] if matrix else []),
                           False, checks, warns, errors)
        check_evidence_anchor([outline], False, checks, warns, errors)
        check_citation_format([outline], False, checks, warns, errors)

    mode = "材料齐备" if complete else "材料不足"
    print("== 代理词交付门禁（%s模式）：%s%s（通过清单）=="
          % (mode, outline.name, " + " + brief.name if brief else ""))
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
        print(f"校验不通过：共拦截 {len(errors)} 项；未通过禁止交付", file=sys.stderr)
        return 1
    print("校验通过（%s模式）：场景路由、双输出对应、争点矩阵、证据锚定、法条引用"
          "%s 均合格" % (mode, "与交付规范" if not complete else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
