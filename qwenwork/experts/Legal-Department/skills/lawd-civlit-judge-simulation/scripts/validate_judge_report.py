#!/usr/bin/env python3
"""lawd-civlit-judge-simulation 模拟裁判报告交付门禁（防缺编 / 防空壳 / 防幻觉 / 防漏项）。

用法
----
    python3 validate_judge_report.py --file 模拟裁判报告.md   --claims N
    python3 validate_judge_report.py --file 模拟裁判报告.docx --claims N

支持格式：.md / .markdown / .txt / .docx。
（--file 亦可写作 --doc / --docx / --md，等价。）
docx 用标准库 zipfile + ElementTree 解析 word/document.xml，按文档顺序覆盖
**正文段落与表格**（表格渲染为 `| 单元格 | 单元格 |` 行），无第三方依赖。

--claims（原告诉讼请求条数）为必填：第五编「诉请支持度逐项评估」的防漏项检查
依赖该条数，缺省时脚本直接以退出码 2 报错，**不做静默放过**——否则这道门禁
等于自愿检查。取值口径见下方 --claims 说明。

检查项（判据锚定 SKILL.md 十编分析体系的真实编号与标题措辞）
--------------------------------------------------------------
1. **十编齐备**：第一编 案件事实法庭认定模拟 / 第二编 争议焦点法庭归纳模拟 /
   第三编 法律法规检索与适用分析 / 第四编 类案检索与裁判规则分析 /
   第五编 诉讼请求支持度法庭评估 / 第六编 模拟裁判文书 /
   第七编 案件弱点识别与补强建议 / 第八编 庭审发问与辩论模拟推演 /
   第九编 裁判结果预判与后续策略 / 第十编 庭前准备检查清单。
   识别口径：标题行含「第X编」序号**或**含该编标题特征词（报告实际落笔常写成
   【案件事实法庭认定模拟】而不带「第一编」，两种写法都认）。缺一即拦截，并
   打印缺哪几编。
2. **各编非空壳**：有标题无实质内容即拦。实质字数 = 去空白/控制字符后的字符数，
   逐编统计「本编标题行 → 下一编标题行」之间的正文。第一至第九编阈值
   --min-chars（默认 350）；**第十编是勾选式检查清单，天然短**，单独按
   120 字或「清单条目 ≥ --checklist-min-items（默认 8）条」二者任一达标即通过，
   不会被长编阈值误拦。
   **各编防整句凑数**：同一句/同一行出现 ≥ 3 次（实质字数 ≥ 8 字的句/行才算）
   判「重复内容」；存在重复时按「去重后实质字数」重判空壳，两者任一命中即拦截。
   短标记（「☑ 已核对」、表头分隔行等）不进入统计，避免误拦清单类短行。
3. **法条引用格式（全文）**：每个「第X条」必须在**同一上下文**（同一小节或同段
   邻近范围）找到法律名称归属（《某某法》或「某某法 第X条」两种写法都认）；
   无归属的裸条号即拦，法律名出现在别的编/别的小节不能洗白本处条号。
   第三编另有强制项：须出现《法律名》+ 第X条（防整编不引用法条）。
   防误拦：「合同第三条」「章程第五条」等非法条载体的条号不计入；「该法第X条」
   等回指须在本小节内有法律名才视为已归属。
4. **第四编类案引用**：须出现真实案号（如「（2023）沪01民终1234号」）。
   防误拦：「指导案例23号」「案例1」这类编号不算案号，但**不因此单独拦截**，
   仅在无任何案号时拦截。
5. **第五编诉请逐项评估**：本编内「有实质内容的诉请评估条目」数 >= --claims N。
   统计口径：抓取本编内「诉讼请求N / 诉请N / 第N项诉讼请求 / 请求N」序数，
   每个序数对应的评估块实质字数须 >= 40 字（防「请求1、请求2…」列名式凑数），
   并与 1..N 比对，拦截时打印漏评的具体序号。
6. **第零条输入信息强制收集程序被跳过**：全文「材料未提供 / 未提交 / 待补充」
   等占位标记 >= --max-missing（默认 8）处，却仍输出完整裁判预判（第六编模拟
   裁判文书 + 第九编胜诉概率），即拦截。防误拦：SKILL.md 异常处理许可的
   「因材料不完整，分析深度受限」声明句本身不计入占位数。

防误拦的两处额外设计
--------------------
- **检索不足豁免**：本编注明「检索结果不足 / 检索服务暂时不可用 / 未经检索验证」
  时（SKILL.md 约束四点五许可的写法），第三编法条、第四编案号由拦截降级为提示。
- **模板/示例文件拒收**：入参指向 references/output-format-template.md 之类模板
  （文件名或标题区含 模板/template/示例/输出格式 等）时，以退出码 2 报输入错误，
  不假装校验——模板里的「第 X 条」「（年份）最高法民终 X 号」是占位符，不是幻觉。

退出码：0=通过；1=拦截；2=输入错误（含缺 --claims、模板文件、格式不支持）。
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

# ------------------------------------------------------------------ 常量/正则

NUM_CHARS = "零〇○一二两三四五六七八九十百千0123456789"
CN_ONLY = "零〇○一二两三四五六七八九十百千"

_N = "[" + NUM_CHARS + "]+"
_SUFFIX = r"(?:\s*第" + _N + r"[款项])*"

# 《法律名》[（以下简称《简称》）] 第X条[第X款/项][、第Y条…]
CITATION_RE = re.compile(
    r"《([^《》\n]{2,80}?)》"
    r"(?:\s*[（(][^）)\n]{0,60}[）)])?"
    r"\s*(?:之|的)?\s*"
    r"第\s*(" + _N + r")\s*条" + _SUFFIX +
    r"((?:\s*[、，,;；和与及]?\s*第\s*" + _N + r"\s*条" + _SUFFIX + r")*)"
)

ARTICLE_RE = re.compile(r"第\s*(" + _N + r")\s*条")

# 法律/法规/司法解释名称特征（区分《民法典》与《XX买卖合同》）
STATUTE_NAME_RE = re.compile(
    r"(?:法|法典|宪法|条例|规定|解释|办法|细则|规则|通知|意见|纪要|批复|决定|准则|"
    r"标准|规范)$"
)

# 紧邻条号之前的「非法条载体」：合同/章程等，这类「第X条」不是法条引用
NON_STATUTE_PREFIX_RE = re.compile(
    r"(?:合同|协议|合约|契约|章程|规约|公约|条款|细则|规则|规程|议事规则|管理规约|"
    r"业主公约|标准|规范|附件|附则|备忘录|意向书|承诺书|授权书|决议|判决|裁定|裁决|"
    r"调解书|通知|保单|制度|手册|须知|说明|方案|纪要|清单|明细)"
    r"\s*(?:书|文本)?\s*(?:之|的|中|里)?\s*$"
)

# 可不带《》的回指表述（该法/本法第X条），须本小节存在法律引用才放行
BACKREF_RE = re.compile(
    r"(?:该法|本法|上述法律|前述法律|同法|该司法解释|该解释|上述解释|该条例|"
    r"上述条例|该规定|上述规定|前引法条|上引法条)\s*(?:之|的)?\s*$"
)

# 不带《》的「法律名 + 第X条」写法（如「民法典第五百七十七条」「公司法第X条」），
# 与《某某法》第X条同样视为条号的法律名称归属（P0⑬ 口径）
NON_BRACKET_CITATION_RE = re.compile(
    r"([\u4e00-\u9fa5]{2,24}?"
    r"(?:法|法典|宪法|条例|规定|解释|办法|细则|规则|通知|意见|纪要|批复|决定|准则|"
    r"标准|规范))"
    r"\s*(?:之|的)?\s*第\s*[" + NUM_CHARS + r"]+\s*条"
)

# 通称/泛指表述，不是具体法律名称，不得作为条号归属（如「法律规定第X条」）
GENERIC_LAW_EXACT = {
    "该法", "本法", "同法", "该条例", "该解释", "该司法解释", "上述规定",
}
GENERIC_LAW_SUFFIX = (
    "法律规定", "行政法规", "地方性法规", "部门规章", "司法解释",
    "相关规定", "有关规定", "该规定", "该项规定", "本条规定", "前款规定",
    "上述法律", "前述法律", "合同规定", "公司规定", "单位规定",
)

# 案号：（2023）沪01民终1234号 / (2021)最高法民终123号
CASE_NO_RE = re.compile(
    r"[（(]\s*(?:19|20)\d{2}\s*[）)]\s*[^\n，,。；;：:、]{2,24}?\d+\s*号"
)

# 诉请序数
CLAIM_ORD_A_RE = re.compile(r"第\s*(" + _N + r")\s*项\s*(?:之)?\s*(?:诉讼请求|诉请|请求|主张)")
CLAIM_ORD_B_RE = re.compile(
    r"(?:诉讼请求|诉请|请求)\s*[（(]?\s*(" + _N + r")\s*[）)]?(?![" + NUM_CHARS + r"])"
)

# 输入不足的占位标记（第零条强制收集程序被跳过的迹象）
MISSING_MARKER_RE = re.compile(
    r"材料未提供|未提供材料|材料缺失|证据未提供|未提交证据|尚未提供|暂未提供|"
    r"待用户补充|待补充材料|待当事人补充|材料待提供|（未提供）|\(未提供\)|"
    r"【未提供】|无法获取材料|材料不详|未见材料"
)
# SKILL.md 异常处理许可的受限声明（不计入占位数，防误拦）
LIMITED_DISCLAIMER_RE = re.compile(
    r"因材料不完整[，,]\s*分析深度受限|分析深度受限|检索结果不足|"
    r"检索服务暂时不可用|未经检索验证"
)
# 检索不足豁免（SKILL.md 约束四点五）
RETRIEVAL_SHORT_RE = re.compile(r"检索结果不足|检索服务暂时不可用|未经检索验证|检索结果为空")

# 模板/示例文件特征（拒收，防把模板当成交付物校验）
TEMPLATE_NAME_PATTERNS = (
    "template", "example", "sample", "knowledge-base", "knowledge_base",
    "readme", "changelog", "skill.md", "模板", "示例", "样例", "知识库", "规范",
)
TEMPLATE_TITLE_PATTERNS = (
    "输出格式模板", "格式模板", "模板", "template", "示例", "样例", "知识库",
    "格式规范", "填写说明",
)

CHECKLIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]\s*)?\[\s*[xX ]?\s*\]|^\s*[-*+•·]\s+\S|^\s*□|^\s*☐")

# 清单条目 / 项目符号行：除含「第X编」外，一律不作编次标题
# （防「- [ ] 类案检索报告（含…）」命中第四编特征词，把第十编清单腰斩成空壳）
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+•·]\s|\[\s*[xX ]?\s*\]|□|☐|\d{1,2}[.)、]\s)")

# 小节序号前缀：一、／（一）／1.／1）／第一节
LEADING_ORDINAL_RE = re.compile(
    r"^(?:第?[" + CN_ONLY + r"]{1,3}[、.．)）]|[（(]\s*[" + NUM_CHARS + r"]{1,3}\s*[）)]|"
    r"\d{1,2}[.、)）])\s*"
)

MARKER_COVERAGE = 0.5         # 标题特征词须覆盖该行（去序号后）过半，才认作编次标题

TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".text"}
HEADING_MAX_LEN = 60          # 标题行最长字数（超长视为正文引述，不作编次标题）
TITLE_ZONE_LINES = 12         # 前 12 个非空行视为标题区
DEFAULT_MIN_CHARS = 350       # 第一至第九编的实质字数阈值
CHECKLIST_MIN_CHARS = 120     # 第十编（勾选清单）的实质字数阈值
DEFAULT_CHECKLIST_ITEMS = 8   # 第十编清单条目数替代阈值
DEFAULT_MAX_MISSING = 8       # 占位标记容忍上限
MIN_CLAIM_SUBSTANCE = 40      # 单条诉请评估的最少实质字数
MIN_DUP_CHARS = 8             # 计入重复统计的句/行最少实质字数（防清单短标记误判）
MIN_DUP_COUNT = 3             # 相同句/相同行出现 >= 3 次判重复
SUB_HEADING_MAX = 20          # 小节标题最大长度（超长视为正文，不作小节边界）

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# ------------------------------------------------------------------ 十编定义

PARTS: Tuple[Dict[str, object], ...] = (
    {"idx": 1, "ordinal": "第一编", "label": "案件事实法庭认定模拟",
     "markers": ("案件事实法庭认定模拟", "事实法庭认定模拟", "案件事实法庭认定",
                 "事实法庭认定", "法庭认定模拟", "事实认定模拟")},
    {"idx": 2, "ordinal": "第二编", "label": "争议焦点法庭归纳模拟",
     "markers": ("争议焦点法庭归纳模拟", "争议焦点法庭归纳", "焦点法庭归纳",
                 "争议焦点归纳模拟", "争议焦点归纳")},
    {"idx": 3, "ordinal": "第三编", "label": "法律法规检索与适用分析",
     "markers": ("法律法规检索与适用分析", "法律法规检索与适用", "法律法规检索",
                 "法规检索与适用", "法律适用分析")},
    {"idx": 4, "ordinal": "第四编", "label": "类案检索与裁判规则分析",
     "markers": ("类案检索与裁判规则分析", "类案检索与裁判规则", "类案检索",
                 "裁判规则分析")},
    {"idx": 5, "ordinal": "第五编", "label": "诉讼请求支持度法庭评估",
     "markers": ("诉讼请求支持度法庭评估", "诉讼请求支持度", "诉请支持度评估",
                 "诉请支持度")},
    {"idx": 6, "ordinal": "第六编", "label": "模拟裁判文书",
     "markers": ("模拟裁判文书", "模拟判决书", "模拟裁决书")},
    {"idx": 7, "ordinal": "第七编", "label": "案件弱点识别与补强建议",
     "markers": ("案件弱点识别与补强建议", "案件弱点识别", "弱点识别与补强",
                 "弱点识别")},
    {"idx": 8, "ordinal": "第八编", "label": "庭审发问与辩论模拟推演",
     "markers": ("庭审发问与辩论模拟推演", "庭审发问与辩论", "发问与辩论模拟推演",
                 "发问与辩论推演", "辩论模拟推演")},
    {"idx": 9, "ordinal": "第九编", "label": "裁判结果预判与后续策略",
     "markers": ("裁判结果预判与后续策略", "裁判结果预判", "结果预判与后续策略",
                 "裁判结果综合预判")},
    {"idx": 10, "ordinal": "第十编", "label": "庭前准备检查清单",
     "markers": ("庭前准备检查清单", "庭前检查清单", "庭前准备清单",
                 "庭前准备检查表")},
)


class InputError(Exception):
    """输入层错误，退出码 2。"""


# ------------------------------------------------------------------ 小工具


def norm(text: str) -> str:
    return re.sub(r"\s+", "", text)


def substantive_length(text: str) -> int:
    """实质字符数：去空白、控制字符与解码替换符。"""
    count = 0
    for ch in text:
        if ch.isspace() or ch == "\ufffd":
            continue
        if unicodedata.category(ch) in {"Cc", "Cf", "Cs", "Co", "Cn"}:
            continue
        count += 1
    return count


def strip_markup(line: str) -> str:
    """去掉 markdown / 装饰线 / 【】，便于判断是否像编次标题。"""
    s = line.strip()
    s = re.sub(r"^[#>\-*\s|=]+", "", s)
    s = s.replace("**", "").replace("*", "").strip()
    s = s.strip("━─—–═＝=~・·|").strip()
    s = s.strip("【】〖〗[]《》<>").strip()
    return s.strip("：:、.。 ").strip()


def is_table_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.count("|") >= 3


def is_separator_row(line: str) -> bool:
    return bool(re.fullmatch(r"[|\s:：\-—–]+", line.strip()))


def is_decoration(line: str) -> bool:
    return bool(re.fullmatch(r"[\s━─—–═＝=*#~_·・]+", line.strip()))


# ------------------------------------------------------------------ 文档读取


def _docx_lines(path: Path) -> List[str]:
    """zipfile + ElementTree 解析 docx：按文档顺序输出段落与表格行。"""
    if not zipfile.is_zipfile(path):
        raise InputError("文件不是合法 DOCX ZIP 容器（.doc 请先转 .docx）")
    try:
        with zipfile.ZipFile(path) as zf:
            names = [n for n in zf.namelist() if n == "word/document.xml"]
            if not names:
                raise InputError("DOCX 内缺少 word/document.xml，文件可能损坏")
            raw = zf.read("word/document.xml")
    except zipfile.BadZipFile as exc:
        raise InputError(f"DOCX 解压失败：{exc}")
    # 安全加固：正常 docx 的 document.xml 不含 DTD / 实体声明，出现即拒收，
    # 避免实体扩展（billion laughs）与外部实体引用。
    head = raw[:4096].upper()
    if b"<!DOCTYPE" in head or b"<!ENTITY" in raw.upper():
        raise InputError("DOCX 内 document.xml 含 DTD/实体声明，出于安全拒绝解析")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise InputError(f"DOCX XML 解析失败：{exc}")

    def para_text(node: ET.Element) -> str:
        """段落取文：含 w:t、制表符、换行；文本框内的 w:t 也在子树内，一并取到。"""
        parts: List[str] = []
        for el in node.iter():
            tag = el.tag
            if tag == W_NS + "t":
                parts.append(el.text or "")
            elif tag == W_NS + "tab":
                parts.append("\t")
            elif tag in (W_NS + "br", W_NS + "cr"):
                parts.append("\n")
        return "".join(parts)

    body = root.find(W_NS + "body")
    if body is None:
        raise InputError("DOCX 缺少 w:body 节点")

    lines: List[str] = []
    for child in list(body):
        if child.tag == W_NS + "p":
            text = para_text(child)
            lines.extend(text.split("\n") if "\n" in text else [text])
        elif child.tag == W_NS + "tbl":
            for row in child.findall(W_NS + "tr"):
                cells: List[str] = []
                for cell in row.findall(W_NS + "tc"):
                    cell_parts = [para_text(p) for p in cell.findall(W_NS + "p")]
                    cells.append(re.sub(r"\s*\n\s*", " ", " ".join(cell_parts)).strip())
                if not any(cells):
                    continue
                filled = {c for c in cells if c}
                if len(cells) == 1 or len(filled) == 1:
                    # 单列/合并单元格常被当排版容器，按普通段落输出
                    lines.extend(p for p in cells[0].splitlines() if p.strip())
                else:
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
    if not path.is_file():
        raise InputError(f"路径不是文件：{path}")
    if path.stat().st_size == 0:
        raise InputError("文件为空")
    if suffix == ".docx":
        return _docx_lines(path)
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


def reject_template(path: Path, lines: Sequence[str]) -> None:
    """模板/示例文件不是交付物，直接以输入错误拒收（避免占位符被当幻觉拦截）。"""
    name = path.name.lower()
    hit_name = next((p for p in TEMPLATE_NAME_PATTERNS if p in name), None)
    title_zone = [strip_markup(ln) for ln in lines if ln.strip()][:TITLE_ZONE_LINES]
    hit_title = next(
        (p for ln in title_zone for p in TEMPLATE_TITLE_PATTERNS if p in ln.lower()),
        None,
    )
    if hit_name or hit_title:
        why = f"文件名含「{hit_name}」" if hit_name else f"标题区含「{hit_title}」"
        raise InputError(
            f"{path.name} 看起来是模板/示例/知识库文件（{why}），不是待交付的模拟裁判"
            "报告。模板中的「第 X 条」「（年份）最高法民终 X 号」是占位符，本门禁"
            "不对模板做交付校验。请传入本案实际生成的报告文件。"
        )


# ------------------------------------------------------------------ 编次切分


def heading_like(line: str) -> bool:
    if is_table_row(line) or is_separator_row(line) or is_decoration(line):
        return False
    return 0 < len(strip_markup(line)) <= HEADING_MAX_LEN


def part_hits(lines: Sequence[str]) -> Dict[int, List[int]]:
    """定位各编的候选标题行号。

    两条口径（均为防误判）：
    1. 含「第X编」序号即认（无论写成「第三编 法律法规检索与适用分析」还是
       「第三编：…」）；清单条目行只走这一条路。
    2. 不含编序号时（报告实际落笔常写成【案件事实法庭认定模拟】），要求标题
       特征词覆盖该行去掉小节序号后长度的过半——即该行基本就是标题本身。
       这样「- [ ] 类案检索报告（含（2021）最高法民终123号…）」这类清单条目、
       以及正文中提到编次名称的长句，都不会被当成编次标题去截断正文。
    """
    hits: Dict[int, List[int]] = {int(p["idx"]): [] for p in PARTS}
    for i, line in enumerate(lines):
        if not heading_like(line):
            continue
        flat = norm(strip_markup(line))
        if not flat:
            continue
        is_list = bool(LIST_ITEM_RE.match(line))
        core = norm(LEADING_ORDINAL_RE.sub("", strip_markup(line)))
        for p in PARTS:
            idx = int(p["idx"])
            ordinal = str(p["ordinal"])
            markers = tuple(p["markers"])  # type: ignore[arg-type]
            if ordinal in flat:
                hits[idx].append(i)
                continue
            if is_list or not core:
                continue
            best = max((len(m) for m in markers if m in core), default=0)
            if best and best / len(core) >= MARKER_COVERAGE:
                hits[idx].append(i)
    return hits


def choose_sections(
    lines: Sequence[str], hits: Dict[int, List[int]]
) -> Dict[int, Tuple[int, int]]:
    """为每编挑一个正文段最长的标题位置，返回 {编号: (标题行, 段末行)}。

    两处防误判设计：
    1. 段末边界只取**其他编**的候选标题行。同编内的下级小节标题往往也含本编
       特征词（如第五编内「三、各诉讼请求支持度汇总」、第九编内「一、裁判结果
       综合预判」），若把它当边界会腰斩本编正文，导致实质字数被低估而误报空壳。
    2. 同一编有多个候选时取正文最长者，可排除报告开头的「目录 / 大纲」行——
       目录行彼此相邻，正文实质字数极小，不会被选中。
    """
    all_hits = [(pos, idx) for idx, positions in hits.items() for pos in positions]
    chosen: Dict[int, Tuple[int, int]] = {}
    for idx, positions in hits.items():
        others = sorted({pos for pos, j in all_hits if j != idx})
        best: Optional[Tuple[int, int, int]] = None      # (实质字数, start, end)
        for start in positions:
            nxt = [b for b in others if b > start]
            end = nxt[0] if nxt else len(lines)
            body = "\n".join(lines[start + 1:end])
            score = substantive_length(body)
            if best is None or score > best[0]:
                best = (score, start, end)
        if best is not None:
            chosen[idx] = (best[1], best[2])
    return chosen


def section_body(lines: Sequence[str], span: Tuple[int, int]) -> str:
    start, end = span
    return "\n".join(lines[start + 1:end])


def count_checklist_items(text: str) -> int:
    return sum(1 for ln in text.splitlines() if CHECKLIST_ITEM_RE.match(ln))


def analyze_repetition(text: str) -> Tuple[List[Tuple[str, str, int]], int]:
    """检测编内重复并给出去重后实质字数（P0⑫ 防整句复制凑数）。

    口径：相同句/相同行出现 >= MIN_DUP_COUNT（3）次即判重复；只统计实质字数
    >= MIN_DUP_CHARS 的句/行，避免「☑ 已核对」、表头分隔行等短标记被误判。
    返回 (重复条目[(类型, 内容, 次数), ...], 去重后实质字数)。
    """
    dups: List[Tuple[str, str, int]] = []
    seen_keys: Set[str] = set()
    # 行级重复（逐行精确匹配）
    line_counter: Counter = Counter(
        norm(ln) for ln in text.splitlines()
        if substantive_length(norm(ln)) >= MIN_DUP_CHARS
    )
    for key, n in line_counter.items():
        if n >= MIN_DUP_COUNT:
            sample = next(ln.strip() for ln in text.splitlines() if norm(ln) == key)
            dups.append(("行", sample, n))
            seen_keys.add(key)
    # 句级重复（按句读切分，可跨行）
    sent_counter: Counter = Counter(
        norm(chunk) for chunk in re.split(r"[。；;！!？?\n]+", text)
        if substantive_length(norm(chunk)) >= MIN_DUP_CHARS
    )
    for key, n in sent_counter.items():
        if n >= MIN_DUP_COUNT and key not in seen_keys:
            dups.append(("句", key, n))
    # 去重后实质字数：每个唯一句只计一次
    deduped = sum(substantive_length(k) for k in sent_counter)
    return dups, deduped


def build_regions(
    lines: Sequence[str], chosen: Dict[int, Tuple[int, int]]
) -> List[Tuple[int, str]]:
    """把全文切成区域：每编正文一个区域（label=编编号），标题区/编间为 0。

    每编正文自成区域后，第三编的法律名再也不能「洗白」第六编里的裸条号。"""
    region_of: Dict[int, int] = {}
    for idx, (start, end) in chosen.items():
        for i in range(start + 1, end):
            region_of[i] = idx
    regions: List[Tuple[int, str]] = []
    cur_label: Optional[int] = None
    cur: List[str] = []
    for i, line in enumerate(lines):
        label = region_of.get(i, 0)
        if cur_label is not None and label != cur_label:
            regions.append((cur_label, "\n".join(cur)))
            cur = []
        cur_label = label
        cur.append(line)
    if cur_label is not None:
        regions.append((cur_label, "\n".join(cur)))
    return regions


# ------------------------------------------------------------------ 引用核验


def sentence_head(text: str, pos: int) -> str:
    start = max((text.rfind(ch, 0, pos) for ch in "。；;！!？?\n"), default=-1)
    return text[start + 1:pos]


def statute_citations(text: str) -> List[re.Match]:
    return [m for m in CITATION_RE.finditer(text)
            if STATUTE_NAME_RE.search(m.group(1))]


def is_generic_law_name(name: str) -> bool:
    """通称/泛指表述（法律规定、行政法规、该法…）不算具体法律名称。"""
    return name in GENERIC_LAW_EXACT or any(
        name.endswith(sfx) for sfx in GENERIC_LAW_SUFFIX
    )


def collect_law_name_matches(text: str) -> List[Tuple[int, int, str]]:
    """收集文本内的法律名称出现位置，返回 [(起始, 结束, 名称)]。

    两种写法都认：《某某法》括号式（须以法/条例/规定等收尾），以及
    「某某法 第X条」不带括号式（如「民法典第五百七十七条」）。"""
    out: List[Tuple[int, int, str]] = []
    for m in re.finditer(r"《([^《》\n]{2,80}?)》", text):
        if STATUTE_NAME_RE.search(m.group(1)):
            out.append((m.start(), m.end(), m.group(1)))
    for m in NON_BRACKET_CITATION_RE.finditer(text):
        name = m.group(1)
        if is_generic_law_name(name):
            continue
        out.append((m.start(), m.end(), name))
    return out


def is_sub_heading(line: str) -> bool:
    """小节边界：markdown 标题 / 独立【…】短行 / 「一、」「（一）」「1.」序数短行。

    仅认短行（<= SUB_HEADING_MAX 字），且排除表格行、装饰线与分隔行，
    防止正文长句被误切成小节——误切只会让条号失去法律名归属而误拦合规稿。"""
    if is_table_row(line) or is_separator_row(line) or is_decoration(line):
        return False
    s = line.strip()
    if not s:
        return False
    flat = norm(strip_markup(s))
    if not flat:
        return False
    if len(flat) > SUB_HEADING_MAX:
        return False
    if re.match(r"^#{1,6}\s", s):
        return True
    if s.startswith("【") and s.endswith("】"):
        return True
    return bool(LEADING_ORDINAL_RE.match(s))


def sub_block_ranges(text: str) -> List[Tuple[int, int, str]]:
    """把文本切成小节区间 [(起始, 结束, 小节文本)]，小节边界为 is_sub_heading。

    小节标题行归入其后的正文块；区间连续覆盖全文，保证每个条号都能定位到
    自己的小节。"""
    starts: List[int] = [0]
    offset = 0
    for ln in text.splitlines(keepends=True):
        if offset > 0 and is_sub_heading(ln):
            starts.append(offset)
        offset += len(ln)
    starts.append(len(text))
    return [(starts[i], starts[i + 1], text[starts[i]:starts[i + 1]])
            for i in range(len(starts) - 1)]


def classify_bare_articles(
    text: str, citations: Sequence[re.Match]
) -> Tuple[List[re.Match], List[re.Match], List[re.Match]]:
    """把未被《法名》直接包裹的「第X条」分成：非法条条号 / 可归属 / 真裸条号。

    归属口径（P0⑬：法律名出现在别处不能洗白本处裸条号）：
    1. 条号所在同一小节内、且位于条号之前的《法律名》/「某某法 第X条」；
    2. 「该法第X条」等回指：本小节内有法律名才放行；
    3. 同一行（同一段）内条号之前已有法律名。
    以上均不满足的即为裸条号。"""
    spans = [m.span() for m in citations]
    ranges = sub_block_ranges(text)
    block_matches = [collect_law_name_matches(t) for _, _, t in ranges]
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
        pos = m.start()
        block_idx = next(i for i, (s, e, _) in enumerate(ranges) if s <= pos < e)
        names_before = any(ns < pos for ns, _, _ in block_matches[block_idx])
        if BACKREF_RE.search(prefix) and names_before:
            attributed.append(m)
            continue
        line_start = text.rfind("\n", 0, pos) + 1
        if any(ns >= line_start and ns < pos
               for ns, _, _ in block_matches[block_idx]):
            attributed.append(m)
            continue
        if names_before:
            attributed.append(m)
            continue
        bare.append(m)
    return non_statute, attributed, bare


# ------------------------------------------------------------------ 诉请逐项


def cn_num_to_int(text: str) -> Optional[int]:
    digits = {"零": 0, "〇": 0, "○": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
              "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    units = {"十": 10, "百": 100, "千": 1000}
    s = text.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    total, current, valid = 0, 0, False
    for ch in s:
        if ch in digits:
            current = digits[ch]
            valid = True
        elif ch in units:
            unit = units[ch]
            if current == 0:
                current = 1
            total += current * unit
            current = 0
            valid = True
        else:
            return None
    return total + current if valid else None


def claim_evaluations(section: str) -> Tuple[Dict[int, int], Set[str], int]:
    """统计第五编内各诉请序数对应评估块的实质字数。

    返回 (｛序号: 该序号最长评估块字数｝, 非数字序数集合, 命中序数总处数)。
    """
    marks: List[Tuple[int, str]] = []
    for regex in (CLAIM_ORD_A_RE, CLAIM_ORD_B_RE):
        for m in regex.finditer(section):
            marks.append((m.start(), m.group(1)))
    marks.sort(key=lambda x: x[0])

    sizes: Dict[int, int] = {}
    other: Set[str] = set()
    positions = [p for p, _ in marks]
    for i, (pos, raw) in enumerate(marks):
        end = positions[i + 1] if i + 1 < len(positions) else len(section)
        block = section[pos:end]
        size = substantive_length(block)
        num = cn_num_to_int(raw)
        if num is None:
            other.add(raw)
            continue
        sizes[num] = max(sizes.get(num, 0), size)
    return sizes, other, len(marks)


# ------------------------------------------------------------------ 主流程


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="模拟裁判报告交付门禁：十编齐备 / 各编非空壳 / 第三编法条引用 "
                    "/ 第四编类案案号 / 第五编诉请逐项评估 / 第零条信息收集未被跳过。"
                    "支持 md/txt/docx（docx 用 zipfile 解析段落与表格）。",
        epilog=(
            "--claims 取值口径：原告起诉状（或仲裁申请书）「诉讼请求」部分的实体诉请"
            "条数，不计「诉讼费用由被告负担」这类程序性请求；反诉另行单独校验。"
            " 判据锚定 SKILL.md「十编分析体系」的真实编号与标题措辞。"
            " 退出码：0=通过 / 1=拦截 / 2=输入错误。"
        ),
    )
    parser.add_argument("--file", "--doc", "--docx", "--md", dest="path",
                        required=True, type=Path,
                        help="模拟裁判报告文件路径（.md/.markdown/.txt/.docx）")
    parser.add_argument("--claims", type=int, default=None,
                        help="【必填】原告诉讼请求条数，用于核对第五编逐项评估不漏项")
    parser.add_argument("--min-chars", type=int, default=DEFAULT_MIN_CHARS,
                        metavar="N",
                        help=f"第一至第九编各编最小实质字数（默认 {DEFAULT_MIN_CHARS}）；"
                             f"第十编为勾选清单，另按 {CHECKLIST_MIN_CHARS} 字或清单"
                             f"条目数判定")
    parser.add_argument("--checklist-min-items", type=int,
                        default=DEFAULT_CHECKLIST_ITEMS, metavar="N",
                        help=f"第十编清单条目数达标线（默认 {DEFAULT_CHECKLIST_ITEMS}）")
    parser.add_argument("--max-missing", type=int, default=DEFAULT_MAX_MISSING,
                        metavar="N",
                        help=f"「材料未提供」类占位标记容忍上限（默认 {DEFAULT_MAX_MISSING}）；"
                             f"超限且仍出完整裁判预判即拦截")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.claims is None:
        print(
            "输入错误：缺少 --claims。\n"
            "  第五编「诉请支持度逐项评估」的防漏项检查依赖原告诉请条数，缺省时"
            "无法校验，本门禁不做静默放过。\n"
            "  请按 SKILL.md 流程传入：--claims <原告起诉状「诉讼请求」部分的实体诉请条数>\n"
            "  例：python3 scripts/validate_judge_report.py --file 《XX案-模拟裁判报告》.docx --claims 4",
            file=sys.stderr,
        )
        return 2
    if args.claims < 1:
        print("输入错误：--claims 必须 >= 1", file=sys.stderr)
        return 2
    if args.min_chars < 0 or args.checklist_min_items < 0 or args.max_missing < 0:
        print("输入错误：--min-chars / --checklist-min-items / --max-missing 不能为负数",
              file=sys.stderr)
        return 2

    try:
        lines = load_document(args.path)
        reject_template(args.path, lines)
    except InputError as exc:
        print(f"输入错误：{exc}", file=sys.stderr)
        return 2

    body = "\n".join(lines)
    checks: List[str] = []
    warns: List[str] = []
    errors: List[str] = []

    hits = part_hits(lines)
    chosen = choose_sections(lines, hits)

    # --- ① 十编齐备 ---
    missing_parts = [p for p in PARTS if int(p["idx"]) not in chosen]
    if missing_parts:
        names = "、".join(f"{p['ordinal']} {p['label']}" for p in missing_parts)
        errors.append(
            f"十编缺编：缺 {len(missing_parts)} 编 → {names}；"
            "识别口径为标题行含「第X编」序号或该编标题特征词，"
            "请补齐缺失编次（勿只留标题）"
        )
    else:
        checks.append("十编齐备：第一编至第十编标题全部命中")

    # --- ② 各编非空壳 + 各编防整句复制凑数（P0⑫）---
    hollow: List[str] = []
    substance_note: List[str] = []
    for p in PARTS:
        idx = int(p["idx"])
        if idx not in chosen:
            continue
        text = section_body(lines, chosen[idx])
        size = substantive_length(text)
        dups, deduped = analyze_repetition(text)
        if dups:
            samples = "、".join(
                f"「{content[:18]}」×{n}" for _, content, n in dups[:3]
            )
            errors.append(
                f"{p['ordinal']} {p['label']}：同一句/同一行出现 ≥ {MIN_DUP_COUNT} 次"
                f"（{samples}），属整句复制凑数，请改写为实质分析内容"
                + (f"（去重后仅 {deduped} 字）" if deduped < args.min_chars else "")
            )
        # 存在重复时按「去重后实质字数」判空壳，防止复制凑数绕过字数阈值
        eff_size = deduped if dups else size
        if idx == 10:
            items = count_checklist_items(text)
            ok = eff_size >= CHECKLIST_MIN_CHARS or items >= args.checklist_min_items
            substance_note.append(f"{p['ordinal']} {size} 字/{items} 条清单")
            if not ok:
                hollow.append(
                    f"{p['ordinal']} {p['label']}：实质内容仅 {size} 字"
                    + (f"（重复句/行去重后仅 {deduped} 字）" if dups else "")
                    + f"、清单 {items} 条"
                    f"（清单型编次口径：>= {CHECKLIST_MIN_CHARS} 字 或 >= "
                    f"{args.checklist_min_items} 条，二者任一即可）"
                )
        else:
            substance_note.append(f"{p['ordinal']} {size} 字")
            if eff_size < args.min_chars:
                hollow.append(
                    f"{p['ordinal']} {p['label']}：实质内容仅 {size} 字"
                    + (f"（重复句/行去重后仅 {deduped} 字）" if dups else "")
                    + f"（阈值 {args.min_chars} 字），有标题无实质内容，属空壳"
                )
    if hollow:
        for item in hollow:
            errors.append("各编空壳：" + item)
    elif chosen:
        checks.append("各编非空壳：" + "、".join(substance_note))

    # --- ③ 第三编法条引用格式（本编须出现《法律名》+第X条）---
    if 3 in chosen:
        sec3 = section_body(lines, chosen[3])
        exempt3 = bool(RETRIEVAL_SHORT_RE.search(sec3))
        statutes = statute_citations(sec3)
        if not statutes:
            msg = ("第三编法条引用：本编未见「《法律名》+第X条」格式的法条引用"
                   "（严禁编造，须经 lawd-regulation-retrieval 检索后按格式标注）")
            if exempt3:
                warns.append(msg + "；本编已注明检索结果不足，按 SKILL.md 约束四点五降级为提示")
            else:
                errors.append(msg)
        else:
            checks.append(f"第三编法条引用：命中 {len(statutes)} 处《法律名》+条号引用")

    # --- ③b 全文条号归属（P0⑬：每个「第X条」须在同一上下文找到法律名归属）---
    part_label = {int(p["idx"]): p["ordinal"] for p in PARTS}
    all_bare: List[Tuple[str, str, re.Match]] = []
    total_article = 0
    total_non_statute = 0
    for label, region_text in build_regions(lines, chosen):
        cites = list(CITATION_RE.finditer(region_text))
        non_statute, _attributed, bare = classify_bare_articles(region_text, cites)
        total_article += len(non_statute) + len(_attributed) + len(bare)
        total_non_statute += len(non_statute)
        for m in bare:
            where = part_label.get(label, "标题区/编间")
            all_bare.append((where, region_text, m))
    if all_bare:
        for where, region_text, m in all_bare[:5]:
            ctx = region_text[max(0, m.start() - 15): m.end() + 5].replace("\n", " ")
            errors.append(
                f"法条引用格式：裸条号缺少法律名称归属（第X条所在小节/同段未见"
                f"《法律名》或「某某法 第X条」）→ {where}…{ctx}…"
            )
        if len(all_bare) > 5:
            errors.append(f"法条引用格式：共 {len(all_bare)} 处无归属裸条号，仅列前 5 处")
    elif total_article:
        checks.append(f"法条引用归属：全文 {total_article} 处条号均有法律名称归属"
                      f"（另 {total_non_statute} 处合同/章程等非法条条号不作要求）")

    # --- ④ 第四编类案案号 ---
    if 4 in chosen:
        sec4 = section_body(lines, chosen[4])
        exempt4 = bool(RETRIEVAL_SHORT_RE.search(sec4))
        uniq_nos = {norm(m.group(0)) for m in CASE_NO_RE.finditer(sec4)}
        if uniq_nos:
            checks.append(f"第四编类案引用：命中 {len(uniq_nos)} 个案号"
                          f"（示例：{sorted(uniq_nos)[0]}）")
        else:
            msg = ("第四编类案引用：本编未见任何案号（格式如「（2023）沪01民终1234号」）；"
                   "「指导案例X号」「案例1」不是案号，严禁无案号的类案表述")
            if exempt4:
                warns.append(msg + "；本编已注明检索结果不足，按 SKILL.md 约束四点五降级为提示")
            else:
                errors.append(msg)

    # --- ⑤ 第五编诉请逐项评估（防漏项 + 防列名式凑数）---
    if 5 in chosen:
        sec5 = section_body(lines, chosen[5])
        sizes, other, total_marks = claim_evaluations(sec5)
        solid = sorted(n for n, size in sizes.items() if size >= MIN_CLAIM_SUBSTANCE)
        thin = sorted(n for n, size in sizes.items() if size < MIN_CLAIM_SUBSTANCE)
        expected = set(range(1, args.claims + 1))
        missing_claims = sorted(expected - set(solid))
        detail = (f"本编命中诉请序数 {total_marks} 处，实质评估 {len(solid)} 项"
                  f"（序号 {solid or '无'}）")
        if thin:
            detail += f"，另有 {len(thin)} 项仅列名不足 {MIN_CLAIM_SUBSTANCE} 字（序号 {thin}）"
        if other:
            detail += f"，无法解析的序数 {sorted(other)}"
        if len(solid) >= args.claims and not missing_claims:
            checks.append(f"第五编诉请逐项评估：{len(solid)} 项 >= 原告诉请 "
                          f"{args.claims} 项（{detail}）")
        else:
            errors.append(
                f"第五编诉请漏项：实质评估 {len(solid)} 项 < 原告诉请 {args.claims} 项"
                + (f"，漏评第 {missing_claims} 项诉讼请求" if missing_claims else "")
                + f"（{detail}）；每项须逐条评估请求权基础、构成要件、证据支撑与支持度，"
                  f"仅列「请求N」名称不计数"
            )

    # --- ⑥ 第零条输入信息强制收集程序是否被跳过 ---
    disclaimer_spans = [m.span() for m in LIMITED_DISCLAIMER_RE.finditer(body)]
    placeholders = [m for m in MISSING_MARKER_RE.finditer(body)
                    if not any(s <= m.start() < e for s, e in disclaimer_spans)]
    has_verdict = 6 in chosen
    has_probability = bool(
        re.search(r"胜诉概率|裁判结果综合预判|完全胜诉|概率\s*[:：]?\s*\d", body)
    ) and 9 in chosen
    if len(placeholders) >= args.max_missing and has_verdict and has_probability:
        samples = "、".join(sorted({m.group(0) for m in placeholders})[:5])
        errors.append(
            f"第零条信息收集被跳过：全文 {len(placeholders)} 处「材料未提供」类占位"
            f"（>= {args.max_missing}，示例：{samples}），却仍输出完整模拟裁判文书与"
            f"胜诉概率预判。信息不充分时不得出完整裁判预判，应先按第零条标准发问"
            f"模板补充材料（references/info-collection-template.md）"
        )
    else:
        checks.append(f"第零条信息收集：占位标记 {len(placeholders)} 处"
                      f"（容忍上限 {args.max_missing}），未见「材料严重缺失仍强行"
                      f"出完整预判」")

    # --- 输出 ---
    print(f"== 模拟裁判报告交付门禁：{args.path.name}（通过清单）==")
    for item in checks:
        print(f"- {item}")
    if not checks:
        print("-（无）")
    if warns:
        print("== 提示 ==")
        for item in warns:
            print(f"- {item}")
    if errors:
        print("== 拦截清单 ==", file=sys.stderr)
        for item in errors:
            print(f"- {item}", file=sys.stderr)
        print(f"校验不通过：共拦截 {len(errors)} 项", file=sys.stderr)
        return 1
    print(f"校验通过：{args.path.name} 十编齐备且无空壳、无整句复制凑数；全文条号均有"
          f"法律名称归属，第三编法条、第四编案号引用合规；第五编逐项评估 >= 原告诉请 "
          f"{args.claims} 项；第零条信息收集程序未被跳过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
