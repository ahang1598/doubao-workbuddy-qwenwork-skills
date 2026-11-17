#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合同审查批注引擎 — apply_review.py

使用 python-docx + lxml 实现 Track Changes 和 Comments 写入。
兼容主流大模型的输出格式。

变更:
  - P0: 修复 ensure_comments_xml() lxml C扩展兼容问题
  - P0: 修复 ensure_content_types() 重复创建 Override 元素
  - P1: 新增段落索引定位机制 (paragraph_index)
  - P1: 新增 JSON 预校验与自动修复
  - P2: 增强模糊匹配 (关键词覆盖 + 滑动窗口)
  - P2: 标点符号归一化函数
  - P3: 新增 --extract-paragraphs 导出模式

用法:
    # 正常审查
    python3 apply_review.py \\
        --input contract.docx \\
        --output contract_reviewed.docx \\
        --json modifications.json

    # 导出段落索引 (辅助 LLM 精确定位)
    python3 apply_review.py \\
        --input contract.docx \\
        --extract-paragraphs paragraphs.txt

JSON 格式见 modification-engine.md
"""

import argparse
import copy
import json

# 统一批注/修订作者名 —— Word 按 author 名字分配颜色,
# 之前给不同风险等级加 [P0🔴]/[P1🟡]/[P2🔵] 前缀导致同一份文档里批注红蓝混杂。
# 现在所有批注/修订统一使用同一作者名,颜色一致;风险等级的红黄蓝图标改为放进
# 批注正文(见 decorate_comment_with_risk),既保持批注底纹同色,又保留风险等级可视化。
def get_author(risk_level: str, base_author: str = "合同审查助手") -> str:
    """Return a single unified author name so all comments/track-changes share one color.

    Word colors comments and revisions by the author string. Prefixing the author with a
    per-risk badge previously produced mixed red/blue comments. Risk level is conveyed by a
    colored icon inside the comment body (decorate_comment_with_risk), so the author name
    stays uniform and comment shading color is consistent.
    """
    return base_author


# 风险等级红黄蓝图标 —— 放进批注正文,不再污染 author 名(避免整体变色)。
_RISK_ICON = {"P0": "🔴", "P1": "🟡", "P2": "🔵"}


def decorate_comment_with_risk(comment_text: str, risk_level: str) -> str:
    """在批注正文中为风险等级加上红黄蓝图标。

    - 若正文含"【风险等级】P1"这类标签,则在等级值前插入对应图标 → "【风险等级】🟡 P1"。
    - 若无该标签,则在正文最前面加一个"🟡 "徽标。
    颜色图标仅出现在批注文字里,不影响 Word 依 author 分配的批注底纹颜色。
    """
    rl = (risk_level or "").strip().upper()
    icon = _RISK_ICON.get(rl, "")
    if not icon or not comment_text:
        return comment_text
    # 已有图标则不重复添加
    if icon in comment_text:
        return comment_text
    m = re.search(r"(【风险等级】)\s*(P[012])", comment_text)
    if m:
        return comment_text[:m.start()] + f"{m.group(1)}{icon} {m.group(2)}" + comment_text[m.end():]
    return f"{icon} {comment_text}"

import os
import re
import shutil
import sys
import traceback
import unicodedata
import zipfile
from datetime import datetime
from difflib import SequenceMatcher

try:
    from lxml import etree
except ImportError:
    print("[WARN] lxml not found, falling back to xml.etree.ElementTree")
    import xml.etree.ElementTree as etree

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WPML = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
COMMENTS_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
)
COMMENTS_CT = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"
)

W = f"{{{WPML}}}"
DEFAULT_AUTHOR = "合同审查助手"
DEFAULT_INITIALS = "CA"

# 标点归一化映射表 (P2)
_PUNCT_MAP = str.maketrans({
    "\u201c": '"',  # "
    "\u201d": '"',  # "
    "\u2018": "'",  # '
    "\u2019": "'",  # '
    "\u3001": ",",  # 、
    "\u3002": ".",  # 。
    "\uff0c": ",",  # ，
    "\uff1b": ";",  # ；
    "\uff1a": ":",  # ：
    "\uff08": "(",  # （
    "\uff09": ")",  # ）
    "\uff01": "!",  # ！
    "\uff1f": "?",  # ？
    "\u2014": "-",  # —
    "\u2013": "-",  # –
    "\u3010": "[",  # 【
    "\u3011": "]",  # 】
})


def _qn(tag: str) -> str:
    """Quick namespace helper: 'w:p' -> '{http://...}p'"""
    if tag.startswith("w:"):
        return f"{W}{tag[2:]}"
    return tag


# ---------------------------------------------------------------------------
# P2: 标点符号归一化
# ---------------------------------------------------------------------------

def normalize_punctuation(text: str) -> str:
    """
    将中文标点统一映射为 ASCII 标点，便于文本比对。
    同时压缩连续空白为单个空格。
    """
    text = text.translate(_PUNCT_MAP)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------------------------------------------------------------------
# Paragraph text extraction helpers
# ---------------------------------------------------------------------------

def get_paragraph_text(para_elem) -> str:
    """
    Extract text from a w:p element, returning the "accepted-revisions view".

    为什么:合同可能处于修订模式(含 w:ins/w:del 等)。审查阶段的 search_text 基于
    "接受全部修订后"的语义撰写,匹配时也必须用同一视图,否则 w:del 残留文本会污染
    paragraph text,导致 search_text 永远找不到。本函数跳过 w:del/w:delText/w:moveFrom
    子树(等价于接受删除),保留 w:ins/w:moveTo 子树内容(等价于接受插入)。

    对无修订的文档,行为等价于"遍历所有 w:t"——完全向后兼容。
    """
    SKIP_SUBTREES = {
        _qn("w:del"), _qn("w:moveFrom"), _qn("w:delText"),
        _qn("w:rPrChange"), _qn("w:pPrChange"), _qn("w:sectPrChange"),
        _qn("w:tblPrChange"), _qn("w:tcPrChange"), _qn("w:trPrChange"),
    }
    t_tag = _qn("w:t")

    parts = []

    def _walk(node):
        if node.tag in SKIP_SUBTREES:
            return  # 跳过整个子树(包括其下的 w:t)
        if node.tag == t_tag and node.text:
            parts.append(node.text)
            return  # w:t 是叶节点
        for child in node:
            _walk(child)

    _walk(para_elem)
    return "".join(parts)


def get_all_paragraphs(body_elem):
    """Return list of (index, paragraph_element, text) for all w:p in body."""
    result = []
    for i, para in enumerate(body_elem.iter(_qn("w:p"))):
        text = get_paragraph_text(para)
        result.append((i, para, text))
    return result


# ---------------------------------------------------------------------------
# P3: --extract-paragraphs 导出段落索引
# ---------------------------------------------------------------------------

def extract_paragraphs(input_path: str, output_path: str):
    """从 docx 中提取所有段落的索引和文本，输出为文本文件供 LLM 参考。"""
    work_dir = input_path + "_extract_tmp"
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)

    try:
        with zipfile.ZipFile(input_path, "r") as z:
            z.extractall(work_dir)
    except zipfile.BadZipFile:
        print("[ERROR] Invalid docx file")
        sys.exit(1)

    doc_xml_path = os.path.join(work_dir, "word", "document.xml")
    doc_tree = etree.parse(doc_xml_path)
    doc_root = doc_tree.getroot()

    body = doc_root.find(_qn("w:body"))
    if body is None:
        for child in doc_root:
            if "body" in child.tag.lower():
                body = child
                break

    if body is None:
        print("[ERROR] w:body not found")
        shutil.rmtree(work_dir, ignore_errors=True)
        sys.exit(1)

    paragraphs = get_all_paragraphs(body)

    lines = []
    for idx, para, text in paragraphs:
        text_display = text.strip() if text.strip() else "(empty)"
        lines.append(f"P{idx:04d} | {text_display}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    shutil.rmtree(work_dir, ignore_errors=True)
    print(f"[OK] Extracted {len(paragraphs)} paragraphs -> {output_path}")


# ---------------------------------------------------------------------------
# P2: 增强模糊匹配
# ---------------------------------------------------------------------------

def _keyword_coverage(search_text: str, para_text: str) -> float:
    """
    计算 search_text 中关键词在 para_text 中的覆盖率。
    关键词 = 连续的中文字符 / 英文单词 (>= 2 字符)。
    """
    # 提取关键词: 连续中文 >= 2字 或 英文单词 >= 2字
    keywords = re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z0-9]{2,}", search_text)
    if not keywords:
        return 0.0
    hits = sum(1 for kw in keywords if kw in para_text)
    return hits / len(keywords)


def _sliding_window_score(search_text: str, para_text: str) -> float:
    """
    在 para_text 上按 search_text 长度做滑动窗口，
    返回最高 SequenceMatcher ratio。
    """
    s_len = len(search_text)
    p_len = len(para_text)
    if s_len == 0 or p_len == 0:
        return 0.0
    if p_len <= s_len:
        return SequenceMatcher(None, search_text, para_text).ratio()

    best = 0.0
    step = max(1, s_len // 4)
    for start in range(0, p_len - s_len + 1, step):
        window = para_text[start : start + s_len]
        score = SequenceMatcher(None, search_text, window).ratio()
        if score > best:
            best = score
            if best > 0.95:
                break
    return best


def find_paragraph(paragraphs, search_text: str, paragraph_index: int = -1,
                   threshold: float = 0.4):
    """
    Find the best matching paragraph for search_text.

    优先级:
      0. paragraph_index 直接定位 (P1)
      1. 精确子串匹配
      2. 空白归一化子串匹配
      3. 标点归一化子串匹配 (P2)
      4. 关键词覆盖 + 滑动窗口综合评分 (P2)
      5. 全段 SequenceMatcher (原有 fallback)

    Returns (index, para_elem, para_text) or None.
    """
    if not search_text or not search_text.strip():
        return None

    search_clean = search_text.strip()

    # Pass 0: paragraph_index 直接定位 (P1)
    if paragraph_index >= 0:
        for idx, para, text in paragraphs:
            if idx == paragraph_index:
                # 验证: 索引处的段落至少包含 search_text 中的部分关键词
                if _keyword_coverage(search_clean, text) >= 0.3 or search_clean[:10] in text:
                    return (idx, para, text)
                # 索引不匹配内容，打印警告，回退到文本搜索
                print(f"  [WARN] paragraph_index={paragraph_index} 内容不匹配, 回退到文本搜索")
                break

    # Pass 1: exact substring match
    for idx, para, text in paragraphs:
        if search_clean in text:
            return (idx, para, text)

    # Pass 2: normalized match (remove whitespace)
    search_norm = re.sub(r"\s+", "", search_clean)
    for idx, para, text in paragraphs:
        text_norm = re.sub(r"\s+", "", text)
        if search_norm in text_norm:
            return (idx, para, text)

    # Pass 3: 标点归一化匹配 (P2)
    search_pnorm = normalize_punctuation(search_clean)
    for idx, para, text in paragraphs:
        text_pnorm = normalize_punctuation(text)
        if search_pnorm in text_pnorm:
            return (idx, para, text)

    # Pass 4: 综合评分 — 关键词覆盖 × 0.4 + 滑动窗口 × 0.6 (P2)
    best_score = 0.0
    best_match = None
    for idx, para, text in paragraphs:
        if not text.strip():
            continue
        kw_score = _keyword_coverage(search_clean, text)
        sw_score = _sliding_window_score(search_clean, text)
        combined = kw_score * 0.4 + sw_score * 0.6
        if combined > best_score:
            best_score = combined
            best_match = (idx, para, text)

    if best_match and best_score >= threshold:
        return best_match

    # Pass 5: 全段 SequenceMatcher (fallback)
    best_ratio = 0.0
    best_fallback = None
    for idx, para, text in paragraphs:
        if not text.strip():
            continue
        ratio = SequenceMatcher(None, search_clean, text).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_fallback = (idx, para, text)

    if best_fallback and best_ratio >= threshold:
        return best_fallback

    return None


# ---------------------------------------------------------------------------
# ID allocation
# ---------------------------------------------------------------------------

def get_max_id(tree_root) -> int:
    """Find the maximum w:id / w14:paraId etc. used in the document."""
    max_id = 0
    for elem in tree_root.iter():
        for attr_name in [_qn("w:id"), "w:id", f"{W}id"]:
            val = elem.get(attr_name)
            if val:
                try:
                    max_id = max(max_id, int(val))
                except ValueError:
                    pass
    return max_id


# ---------------------------------------------------------------------------
# Track Changes: apply deletion + insertion
# ---------------------------------------------------------------------------

def _make_run(text: str, rpr_elem=None) -> "etree.Element":
    """Create a w:r element with optional formatting."""
    r = etree.SubElement(etree.Element("dummy"), _qn("w:r"))
    r = copy.deepcopy(r)
    if rpr_elem is not None:
        r.insert(0, copy.deepcopy(rpr_elem))
    t = etree.SubElement(r, _qn("w:t"))
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    return r


def _minimal_diff(old_clean: str, new_text: str):
    """
    计算 old/new 的公共前缀与公共后缀,返回真正发生变化的最小核心片段。

    为什么:模型经常把整句话放进 old_text/new_text,导致脚本删掉整句再重插整句,
    人工看到的是"整段被删+整段新增",无法逐字修订。本函数剥离两端未变化的文本,
    只对真正 diff 的核心做 w:del / w:ins,未变部分保留为普通文本。

    返回 (common_prefix, core_old, core_new, common_suffix)。
    """
    if new_text is None:
        new_text = ""
    n_old, n_new = len(old_clean), len(new_text)
    # 公共前缀
    p = 0
    while p < n_old and p < n_new and old_clean[p] == new_text[p]:
        p += 1
    # 公共后缀(不与前缀重叠)
    s = 0
    while (s < n_old - p) and (s < n_new - p) and old_clean[n_old - 1 - s] == new_text[n_new - 1 - s]:
        s += 1
    common_prefix = old_clean[:p]
    common_suffix = old_clean[n_old - s:] if s > 0 else ""
    core_old = old_clean[p: n_old - s]
    core_new = new_text[p: n_new - s]
    return common_prefix, core_old, core_new, common_suffix


def _diff_segments(old_clean: str, new_text: str):
    """
    基于 SequenceMatcher 的多块 diff,识别句子中间夹着的公共子串。

    为什么:单纯剥两端公共前后缀(_minimal_diff)无法处理"被告所在地有管辖权的法院"→
    "客户所在地有管辖权的人民法院"这类——中间的"有管辖权的"是公共块,却被前后不同的字
    夹住,逐字符算法只能整块删改。SequenceMatcher.get_opcodes() 能把公共块识别出来,
    实现真正的逐词修订。

    返回 opcode 列表,每项为:
      ('equal',  text)        未变文本,保留为普通 run
      ('delete', old_seg)     仅删除
      ('insert', new_seg)     仅插入
      ('replace', old_seg, new_seg)  就地替换(先删后插)
    """
    if new_text is None:
        new_text = ""
    sm = SequenceMatcher(None, old_clean, new_text, autojunk=False)
    ops = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            ops.append(("equal", old_clean[i1:i2]))
        elif tag == "delete":
            ops.append(("delete", old_clean[i1:i2]))
        elif tag == "insert":
            ops.append(("insert", new_text[j1:j2]))
        elif tag == "replace":
            ops.append(("replace", old_clean[i1:i2], new_text[j1:j2]))
    return ops


def _mk_del(seg, rpr_copy, change_id, author, date_str):
    del_elem = etree.Element(_qn("w:del"))
    del_elem.set(_qn("w:id"), str(change_id))
    del_elem.set(_qn("w:author"), author)
    del_elem.set(_qn("w:date"), date_str)
    del_run = etree.SubElement(del_elem, _qn("w:r"))
    if rpr_copy is not None:
        del_run.insert(0, copy.deepcopy(rpr_copy))
    del_t = etree.SubElement(del_run, _qn("w:delText"))
    del_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    del_t.text = seg
    return del_elem


def _mk_ins(seg, rpr_copy, change_id, author, date_str):
    ins_elem = etree.Element(_qn("w:ins"))
    ins_elem.set(_qn("w:id"), str(change_id))
    ins_elem.set(_qn("w:author"), author)
    ins_elem.set(_qn("w:date"), date_str)
    ins_run = etree.SubElement(ins_elem, _qn("w:r"))
    if rpr_copy is not None:
        ins_run.insert(0, copy.deepcopy(rpr_copy))
    ins_t = etree.SubElement(ins_run, _qn("w:t"))
    ins_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    ins_t.text = seg
    return ins_elem


def _emit_diff_nodes(parent, insert_idx, before_text, after_text, old_clean, new_text,
                     rpr_copy, change_id, author, date_str, created_elems):
    """
    按多块 diff 在 parent 的 insert_idx 处顺序插入:
      before_text(普通) → [equal/del/ins 交替] → after_text(普通)
    只把 del/ins 元素记入 created_elems(供批注锚定改动片段)。
    返回下一个可用 change_id。
    """
    if before_text:
        parent.insert(insert_idx, _make_run(before_text, rpr_copy))
        insert_idx += 1

    for op in _diff_segments(old_clean, new_text or ""):
        kind = op[0]
        if kind == "equal":
            if op[1]:
                parent.insert(insert_idx, _make_run(op[1], rpr_copy))
                insert_idx += 1
        elif kind == "delete":
            el = _mk_del(op[1], rpr_copy, change_id, author, date_str)
            parent.insert(insert_idx, el); insert_idx += 1; change_id += 1
            if created_elems is not None:
                created_elems.append(el)
        elif kind == "insert":
            el = _mk_ins(op[1], rpr_copy, change_id, author, date_str)
            parent.insert(insert_idx, el); insert_idx += 1; change_id += 1
            if created_elems is not None:
                created_elems.append(el)
        elif kind == "replace":
            eld = _mk_del(op[1], rpr_copy, change_id, author, date_str)
            parent.insert(insert_idx, eld); insert_idx += 1; change_id += 1
            eli = _mk_ins(op[2], rpr_copy, change_id, author, date_str)
            parent.insert(insert_idx, eli); insert_idx += 1; change_id += 1
            if created_elems is not None:
                created_elems.append(eld)
                created_elems.append(eli)

    if after_text:
        parent.insert(insert_idx, _make_run(after_text, rpr_copy))
        insert_idx += 1
    return change_id





def apply_track_change_to_paragraph(
    para_elem, old_text: str, new_text: str, change_id: int, author: str, date_str: str,
    created_elems: list = None,
):
    """
    Apply Track Change (delete old_text + insert new_text) in a paragraph.

    采用 SequenceMatcher 多块 diff(_emit_diff_nodes),识别句子中间夹着的公共
    子串(如"有管辖权的"),实现真正的逐词修订,不再把公共块整块删改。

    定位仍用完整 old_text(保证唯一命中),但实际 w:del/w:ins 只作用于真正变化的片段。
    若传入 created_elems(list),会把本次创建的 w:del / w:ins 元素追加进去,
    供调用方把批注精确锚定到"仅改动片段"而非整段。

    返回值:
      本次消耗的修订 id 数量(int, >=0) 表示成功;
      False 表示未能定位 old_text(定位失败)。
    调用方应据返回值推进 next_id。
    """
    # Collect runs and their texts
    runs = list(para_elem.iter(_qn("w:r")))

    # Build full text from runs with mapping
    run_texts = []
    for run in runs:
        parts = []
        for t_elem in run.findall(_qn("w:t")):
            if t_elem.text:
                parts.append(t_elem.text)
        run_texts.append("".join(parts))

    full_text = "".join(run_texts)

    # Normalize for matching
    old_clean = old_text.strip()
    if old_clean not in full_text:
        # Try normalized
        old_norm = re.sub(r"\s+", "", old_clean)
        full_norm = re.sub(r"\s+", "", full_text)
        if old_norm not in full_norm:
            return False

    # Find which run contains old_text (or spans multiple runs)
    pos = full_text.find(old_clean)
    if pos == -1:
        return False

    # Map position to run index
    char_count = 0
    target_run_idx = -1
    for i, rt in enumerate(run_texts):
        if char_count + len(rt) > pos:
            target_run_idx = i
            break
        char_count += len(rt)

    if target_run_idx == -1:
        return False

    # Simple case: old_text is within a single run
    target_run = runs[target_run_idx]
    target_text = run_texts[target_run_idx]

    if old_clean in target_text:
        # Get run properties
        rpr = target_run.find(_qn("w:rPr"))
        rpr_copy = copy.deepcopy(rpr) if rpr is not None else None

        # Find parent of this run
        parent = para_elem
        children = list(parent)
        run_pos = None
        for ci, child in enumerate(children):
            if child is target_run:
                run_pos = ci
                break

        # Also check nested elements
        if run_pos is None:
            for child in children:
                sub_children = list(child)
                for sci, sc in enumerate(sub_children):
                    if sc is target_run:
                        parent = child
                        children = sub_children
                        run_pos = sci
                        break
                if run_pos is not None:
                    break

        if run_pos is None:
            return False

        # Split text
        local_pos = target_text.index(old_clean)
        before_text = target_text[:local_pos]
        after_text = target_text[local_pos + len(old_clean):]

        # Remove original run
        parent.remove(target_run)
        insert_idx = run_pos

        # 多块 diff —— before/after 为原 run 中未涉及的文本,
        # 中间由 _emit_diff_nodes 按 equal/del/ins 逐词展开,保留公共子串。
        next_change_id = _emit_diff_nodes(
            parent, insert_idx, before_text, after_text,
            old_clean, new_text or "", rpr_copy,
            change_id, author, date_str, created_elems,
        )
        return next_change_id - change_id

    # Multi-run case: old_text spans multiple runs
    accumulated = ""
    start_run_idx = target_run_idx
    end_run_idx = target_run_idx
    offset_in_start = pos - char_count

    temp_count = char_count
    for i in range(target_run_idx, len(runs)):
        accumulated = full_text[pos : pos + len(old_clean)]
        temp_end = temp_count + len(run_texts[i])
        if temp_end >= pos + len(old_clean):
            end_run_idx = i
            break
        temp_count = temp_end
        end_run_idx = i

    first_run = runs[start_run_idx]
    rpr = first_run.find(_qn("w:rPr"))
    rpr_copy = copy.deepcopy(rpr) if rpr is not None else None

    # Find position of first run in parent
    parent_elem = para_elem
    children = list(parent_elem)
    first_pos = None
    for ci, child in enumerate(children):
        if child is first_run:
            first_pos = ci
            break

    if first_pos is None:
        return False

    # Remove involved runs
    for i in range(start_run_idx, end_run_idx + 1):
        try:
            parent_elem.remove(runs[i])
        except ValueError:
            pass

    insert_idx = first_pos

    # before/after 为首尾 run 中未涉及部分,中间用多块 diff 逐词展开
    first_text = run_texts[start_run_idx]
    before_text = first_text[:offset_in_start]

    last_text = run_texts[end_run_idx]
    end_offset = (pos + len(old_clean)) - sum(len(run_texts[j]) for j in range(end_run_idx))
    if end_offset < 0:
        end_offset = 0
    after_text = (last_text[end_offset:] if end_offset < len(last_text) else "")

    next_change_id = _emit_diff_nodes(
        parent_elem, insert_idx, before_text, after_text,
        old_clean, new_text or "", rpr_copy,
        change_id, author, date_str, created_elems,
    )
    return next_change_id - change_id


# ---------------------------------------------------------------------------
# Comments handling
# ---------------------------------------------------------------------------

def ensure_comments_xml(work_dir: str):
    """
    Ensure comments.xml exists; create if missing.

    P0 Fix: 移除 lxml C 扩展 __code__ 内省，改用 try/except。
    """
    comments_path = os.path.join(work_dir, "word", "comments.xml")
    if not os.path.exists(comments_path):
        # 直接用 try/except 创建，兼容 lxml 和 stdlib
        try:
            root = etree.Element(f"{{{WPML}}}comments", nsmap={"w": WPML})
        except TypeError:
            root = etree.Element(f"{{{WPML}}}comments")
            root.set("xmlns:w", WPML)

        tree = etree.ElementTree(root)
        tree.write(comments_path, xml_declaration=True, encoding="UTF-8")
    return comments_path


def add_comment_to_xml(
    comments_path: str,
    doc_tree,
    para_elem,
    comment_text: str,
    comment_id: int,
    author: str,
    initials: str,
    date_str: str,
    anchor_elems: list = None,
):
    """Add a comment to comments.xml and insert range markers in the paragraph.

    若提供 anchor_elems(本次修订创建的 w:del/w:ins 元素列表),批注范围只包裹
    这些元素(即"仅改动的字"),而非整段。这样 Word 中只有被改动的文字带批注底纹,
    不会整段变色。未提供 anchor_elems 时回退到旧行为(包裹整段)。
    """
    # Parse comments.xml
    comments_tree = etree.parse(comments_path)
    comments_root = comments_tree.getroot()

    # Create comment element
    comment_elem = etree.SubElement(comments_root, _qn("w:comment"))
    comment_elem.set(_qn("w:id"), str(comment_id))
    comment_elem.set(_qn("w:author"), author)
    comment_elem.set(_qn("w:date"), date_str)
    comment_elem.set(_qn("w:initials"), initials)

    # Add comment paragraphs — 批注排版标准（用户确认版）
    # 目标：让法务能"扫读"批注。三段式各部分独立成段、加大字号与段后间距，标签加粗。
    #   1. 【风险等级】🔴/🟡/🔵 Px —— 标签与等级值同一行、整行加粗（风险等级要一眼看到，
    #      拆两行反而割裂，所以特意保持同行）。
    #   2. 【风险分析】/【修改建议】等其它标签 —— 标签独占一行并加粗，其后正文另起一行、常规体，
    #      这样每段"标题在上、内容在下"，长句不会和标签挤成一团。
    #   3. 字号 13pt（sz=26，默认批注约 10pt），段后间距 8pt（after=160），三段之间留出呼吸感。
    # 引擎在此自行完成"标签/正文分行"，因此 TOML 里的 comment 只需用 \n 分隔三段即可，
    # 无需手动为每个标签再插入换行。
    _XMLSPACE = "{http://www.w3.org/XML/1998/namespace}space"
    _FONT_SZ = "26"       # 半磅值：26 = 13pt
    _SPACE_AFTER = "160"  # 段后间距，二十分之一磅：160 = 8pt

    def _mk_para(bold_head, head_text, body_text=None):
        """新建一个批注段落；head 部分按 bold_head 决定是否加粗，body 常规体。"""
        p = etree.SubElement(comment_elem, _qn("w:p"))
        ppr = etree.SubElement(p, _qn("w:pPr"))
        spc = etree.SubElement(ppr, _qn("w:spacing"))
        spc.set(_qn("w:after"), _SPACE_AFTER)

        def _run(text, bold):
            r = etree.SubElement(p, _qn("w:r"))
            rpr = etree.SubElement(r, _qn("w:rPr"))
            if bold:
                etree.SubElement(rpr, _qn("w:b"))
            sz = etree.SubElement(rpr, _qn("w:sz"))
            sz.set(_qn("w:val"), _FONT_SZ)
            szcs = etree.SubElement(rpr, _qn("w:szCs"))
            szcs.set(_qn("w:val"), _FONT_SZ)
            t = etree.SubElement(r, _qn("w:t"))
            t.set(_XMLSPACE, "preserve")
            t.text = text if text else " "

        _run(head_text, bold_head)
        if body_text:
            _run(body_text, False)
        return p

    # 风险等级行：标签后紧跟 (可选图标)+P0/P1/P2，识别后整行加粗、不拆分。
    _risk_re = re.compile(r"^(【风险等级】)\s*([🔴🟡🔵]?\s*P[012].*)$", re.S)
    # 其它标签行：【xxx】+正文，标签独占一行、正文另起一行。
    _label_re = re.compile(r"^(【[^】]*】)\s*(.*)$", re.S)
    for line in comment_text.split("\n"):
        rm = _risk_re.match(line) if line else None
        if rm:
            # 【风险等级】🟡 P1 —— 同一行、整行加粗
            _mk_para(True, f"{rm.group(1)}{rm.group(2)}")
            continue
        lm = _label_re.match(line) if line else None
        if lm and lm.group(1):
            body = lm.group(2).strip()
            if body:
                # 标签独占一行（加粗）+ 正文另起一行（常规）→ 拆成两个段落
                _mk_para(True, lm.group(1))
                _mk_para(False, body)
            else:
                _mk_para(True, lm.group(1))
        else:
            _mk_para(False, line)

    # Save comments.xml
    comments_tree.write(comments_path, xml_declaration=True, encoding="UTF-8")

    range_start = etree.Element(_qn("w:commentRangeStart"))
    range_start.set(_qn("w:id"), str(comment_id))
    range_end = etree.Element(_qn("w:commentRangeEnd"))
    range_end.set(_qn("w:id"), str(comment_id))
    ref_run = etree.Element(_qn("w:r"))
    ref = etree.SubElement(ref_run, _qn("w:commentReference"))
    ref.set(_qn("w:id"), str(comment_id))

    # 精确锚定到改动片段
    valid_anchors = [e for e in (anchor_elems or []) if e is not None and e.getparent() is not None]
    if valid_anchors:
        first = valid_anchors[0]
        last = valid_anchors[-1]
        fparent = first.getparent()
        fidx = list(fparent).index(first)
        fparent.insert(fidx, range_start)
        lparent = last.getparent()
        lidx = list(lparent).index(last)
        lparent.insert(lidx + 1, range_end)
        lparent.insert(lidx + 2, ref_run)
        return

    # Fallback: wrap whole paragraph (旧行为)
    para_elem.insert(0, range_start)
    para_elem.append(range_end)
    para_elem.append(ref_run)


# ---------------------------------------------------------------------------
# Content_Types and Relationships
# ---------------------------------------------------------------------------

def ensure_content_types(work_dir: str):
    """
    Ensure [Content_Types].xml declares comments.xml.

    P0 Fix: 修复重复创建 Override 元素的 bug — 原代码先 SubElement 再判断
    命名空间重新 SubElement，导致写入两个 Override。
    """
    ct_path = os.path.join(work_dir, "[Content_Types].xml")
    if not os.path.exists(ct_path):
        return

    tree = etree.parse(ct_path)
    root = tree.getroot()

    # Check if comments override already exists
    for child in root:
        part_name = child.get("PartName", "")
        if part_name == "/word/comments.xml":
            return  # 已存在，无需操作

    # 从 root.tag 推导实际命名空间
    if "{" in root.tag:
        actual_ns = root.tag.split("}")[0] + "}"
        override = etree.SubElement(root, f"{actual_ns}Override")
    else:
        override = etree.SubElement(root, "Override")

    override.set("PartName", "/word/comments.xml")
    override.set("ContentType", COMMENTS_CT)

    tree.write(ct_path, xml_declaration=True, encoding="UTF-8")


def ensure_relationships(work_dir: str):
    """Ensure document.xml.rels has comments relationship."""
    rels_dir = os.path.join(work_dir, "word", "_rels")
    rels_path = os.path.join(rels_dir, "document.xml.rels")

    if not os.path.exists(rels_path):
        os.makedirs(rels_dir, exist_ok=True)
        root = etree.Element("Relationships", xmlns=RELS_NS)
        tree = etree.ElementTree(root)
        tree.write(rels_path, xml_declaration=True, encoding="UTF-8")

    tree = etree.parse(rels_path)
    root = tree.getroot()

    # Determine namespace from root
    root_ns = ""
    if "{" in root.tag:
        root_ns = root.tag.split("}")[0] + "}"

    # Check existing relationships
    max_id = 0
    has_comments = False
    for rel in root:
        rid = rel.get("Id", "")
        if rid.startswith("rId"):
            try:
                max_id = max(max_id, int(rid[3:]))
            except ValueError:
                pass
        if rel.get("Type") == COMMENTS_TYPE:
            has_comments = True

    if not has_comments:
        new_rel = etree.SubElement(root, f"{root_ns}Relationship" if root_ns else "Relationship")
        new_rel.set("Id", f"rId{max_id + 1}")
        new_rel.set("Type", COMMENTS_TYPE)
        new_rel.set("Target", "comments.xml")

    tree.write(rels_path, xml_declaration=True, encoding="UTF-8")


# ---------------------------------------------------------------------------
# P1: JSON 预校验与自动修复
# ---------------------------------------------------------------------------

def validate_and_fix_json(data: dict) -> tuple:
    """
    校验 modifications JSON 结构，自动修复常见问题。
    返回 (fixed_data, warnings_list)。
    """
    warnings = []
    modifications = data.get("modifications", [])

    if not isinstance(modifications, list):
        warnings.append("'modifications' 不是数组，尝试转换")
        modifications = [modifications] if modifications else []
        data["modifications"] = modifications

    valid_types = {"track_change", "comment_only", "delete", "insert_after"}

    for i, mod in enumerate(modifications):
        # 类型修复
        mod_type = mod.get("type", "").strip().lower()
        if mod_type not in valid_types:
            # 尝试模糊匹配
            type_map = {
                "trackchange": "track_change",
                "track-change": "track_change",
                "modify": "track_change",
                "replace": "track_change",
                "comment": "comment_only",
                "add_comment": "comment_only",
                "add": "insert_after",
                "insert": "insert_after",
                "remove": "delete",
            }
            fixed_type = type_map.get(mod_type, "")
            if fixed_type:
                warnings.append(f"[{i}] type '{mod_type}' -> '{fixed_type}'")
                mod["type"] = fixed_type
            else:
                warnings.append(f"[{i}] 未知 type: '{mod_type}'")

        # search_text 必填校验
        if not mod.get("search_text", "").strip():
            warnings.append(f"[{i}] search_text 为空")

        # track_change 需要 old_text
        if mod.get("type") == "track_change" and not mod.get("old_text", "").strip():
            warnings.append(f"[{i}] track_change 缺少 old_text")

        # paragraph_index 类型修复
        pi = mod.get("paragraph_index")
        if pi is not None:
            if isinstance(pi, str):
                try:
                    mod["paragraph_index"] = int(pi)
                except ValueError:
                    warnings.append(f"[{i}] paragraph_index '{pi}' 无法转为 int，已忽略")
                    del mod["paragraph_index"]

        # 自动裁剪首尾空白
        for key in ("search_text", "old_text", "new_text", "comment"):
            if key in mod and isinstance(mod[key], str):
                mod[key] = mod[key].strip()

        # ===== 模型输出容错逻辑 =====

        # 容错1: risk_level 别名映射（模型可能输出中文或小写）
        rl = mod.get("risk_level", "")
        if rl:
            rl_norm = rl.strip().lower()
            rl_map = {
                "高": "P0", "严重": "P0", "high": "P0", "critical": "P0",
                "中": "P1", "重要": "P1", "medium": "P1", "important": "P1",
                "低": "P2", "一般": "P2", "low": "P2", "minor": "P2",
                "轻微": "P2", "提示": "P2", "info": "P2",
                "p0": "P0", "p1": "P1", "p2": "P2", "p3": "P2",
            }
            if rl_norm in rl_map:
                fixed_rl = rl_map[rl_norm]
                if fixed_rl != rl:
                    warnings.append(f"[{i}] risk_level '{rl}' -> '{fixed_rl}'")
                mod["risk_level"] = fixed_rl
            elif rl not in ("P0", "P1", "P2"):
                warnings.append(f"[{i}] risk_level '{rl}' 未知，已置为 P2")
                mod["risk_level"] = "P2"

        # 容错2: comment 格式标签自动补充（模型可能省略格式标签）
        comment = mod.get("comment", "")
        if comment and "【修改意见】" not in comment and "【修改原因】" not in comment and "【风险等级】" not in comment and "【风险分析】" not in comment:
            # 尝试检测是否有"建议"/"原因"等关键词来拆分
            if "原因" in comment or "因为" in comment or "风险" in comment:
                # comment 中有原因相关文本，尝试拆分
                parts = re.split(r"[。；;]", comment, maxsplit=1)
                if len(parts) == 2 and parts[1].strip():
                    mod["comment"] = f"【修改意见】{parts[0].strip()}\n【修改原因】{parts[1].strip()}"
                else:
                    mod["comment"] = f"【修改意见】{comment}"
            else:
                mod["comment"] = f"【修改意见】{comment}"
            warnings.append(f"[{i}] comment 缺少格式标签，已自动补充【修改意见】")

        # 容错3: track_change 缺少 new_text 时自动降级为 comment_only
        if mod.get("type") == "track_change" and not mod.get("new_text", "").strip():
            mod["type"] = "comment_only"
            warnings.append(f"[{i}] track_change 缺少 new_text，已降级为 comment_only")

        # 容错4: comment_only 缺少 comment 时用 old_text/new_text 构造
        if mod.get("type") == "comment_only" and not mod.get("comment", "").strip():
            auto_comment = ""
            if mod.get("old_text") and mod.get("new_text"):
                auto_comment = f"【修改意见】建议将「{mod['old_text']}」修改为「{mod['new_text']}」"
            elif mod.get("new_text"):
                auto_comment = f"【修改意见】{mod['new_text']}"
            if auto_comment:
                mod["comment"] = auto_comment
                warnings.append(f"[{i}] comment_only 缺少 comment，已从 old_text/new_text 自动构造")

    return data, warnings


# ---------------------------------------------------------------------------
# Main batch processing
# ---------------------------------------------------------------------------

def process_modifications(input_path: str, output_path: str, mods_json_path: str):
    """Main entry: apply all modifications from JSON to docx."""
    # Load JSON
    with open(mods_json_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    # P1: JSON 解析容错 — 去除可能的 BOM、控制字符
    raw_text = raw_text.lstrip("\ufeff")
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 解析失败: {e}")
        # 尝试自动修复常见问题: 中文引号替换
        fixed_text = raw_text.replace("\u201c", '"').replace("\u201d", '"')
        fixed_text = fixed_text.replace("\u2018", "'").replace("\u2019", "'")
        try:
            data = json.loads(fixed_text)
            print("[INFO] 自动修复中文引号后重新解析成功")
        except json.JSONDecodeError:
            print("[ERROR] 自动修复后仍无法解析 JSON")
            return {"success": 0, "failed": 0, "skipped": 0,
                    "total": 0, "error": f"JSON parse error: {e}"}

    # P1: JSON 预校验
    data, json_warnings = validate_and_fix_json(data)
    if json_warnings:
        print("[WARN] JSON 预校验发现问题:")
        for w in json_warnings:
            print(f"  - {w}")

    author = data.get("author", DEFAULT_AUTHOR)
    initials = data.get("initials", DEFAULT_INITIALS)
    modifications = data.get("modifications", [])

    if not modifications:
        print("[INFO] No modifications to apply")
        shutil.copy2(input_path, output_path)
        return {"success": 0, "failed": 0, "skipped": 0, "total": 0}

    date_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Backup original
    backup_path = input_path + ".backup"
    shutil.copy2(input_path, backup_path)

    # Extract docx
    work_dir = output_path + "_work"
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)

    try:
        with zipfile.ZipFile(input_path, "r") as z:
            z.extractall(work_dir)
    except zipfile.BadZipFile:
        print("[ERROR] Invalid docx file")
        return {"success": 0, "failed": 0, "skipped": 0, "total": len(modifications),
                "error": "Invalid docx file"}

    # Parse document.xml
    doc_xml_path = os.path.join(work_dir, "word", "document.xml")
    if not os.path.exists(doc_xml_path):
        print("[ERROR] document.xml not found")
        shutil.rmtree(work_dir)
        return {"success": 0, "failed": 0, "skipped": 0, "total": len(modifications),
                "error": "document.xml not found"}

    doc_tree = etree.parse(doc_xml_path)
    doc_root = doc_tree.getroot()

    # Find body
    body = doc_root.find(_qn("w:body"))
    if body is None:
        for child in doc_root:
            if "body" in child.tag.lower():
                body = child
                break

    if body is None:
        print("[ERROR] w:body not found in document.xml")
        shutil.rmtree(work_dir)
        return {"success": 0, "failed": 0, "skipped": 0, "total": len(modifications),
                "error": "w:body not found"}

    # Get all paragraphs
    paragraphs = get_all_paragraphs(body)

    # Ensure comments infrastructure
    comments_path = ensure_comments_xml(work_dir)
    ensure_content_types(work_dir)
    ensure_relationships(work_dir)

    # Get next available ID
    next_id = get_max_id(doc_root) + 1
    try:
        comments_tree = etree.parse(comments_path)
        next_id = max(next_id, get_max_id(comments_tree.getroot()) + 1)
    except Exception:
        pass

    # Process modifications
    stats = {"success": 0, "failed": 0, "skipped": 0, "total": len(modifications), "details": []}

    for i, mod in enumerate(modifications):
        mod_type = mod.get("type", "").strip().lower()
        search_text = mod.get("search_text", "").strip()
        old_text = mod.get("old_text", "").strip()
        new_text = mod.get("new_text", "")
        comment_text = mod.get("comment", "").strip()
        risk_level = mod.get("risk_level", "medium")
        # 风险等级红黄蓝图标放进批注正文(作者名保持统一,批注底纹不再混色)
        comment_text = decorate_comment_with_risk(comment_text, risk_level)
        paragraph_index = mod.get("paragraph_index", -1)  # P1: 段落索引
        mod_author = get_author(risk_level.upper(), author)  # v20: per-modification risk prefix

        detail = {"index": i, "type": mod_type, "status": "unknown", "message": ""}

        try:
            if not search_text:
                detail["status"] = "skipped"
                detail["message"] = "Empty search_text"
                stats["skipped"] += 1
                stats["details"].append(detail)
                continue

            # Find target paragraph (P1: 支持 paragraph_index)
            match = find_paragraph(paragraphs, search_text,
                                   paragraph_index=paragraph_index)
            if match is None:
                detail["status"] = "failed"
                detail["message"] = f"Paragraph not found for: {search_text[:50]}..."
                stats["failed"] += 1
                stats["details"].append(detail)
                continue

            _, para_elem, para_text = match

            if mod_type == "track_change":
                if not old_text:
                    detail["status"] = "failed"
                    detail["message"] = "old_text is required for track_change"
                    stats["failed"] += 1
                    stats["details"].append(detail)
                    continue

                created = []
                consumed = apply_track_change_to_paragraph(
                    para_elem, old_text, new_text or "", next_id, mod_author, date_str,
                    created_elems=created,
                )
                if consumed is not False:
                    next_id += consumed
                    if comment_text:
                        add_comment_to_xml(
                            comments_path, doc_tree, para_elem,
                            comment_text, next_id, mod_author, initials, date_str,
                            anchor_elems=created,
                        )
                        next_id += 1
                    detail["status"] = "success"
                    stats["success"] += 1
                else:
                    # Retry with normalized text
                    old_norm = re.sub(r"\s+", " ", old_text).strip()
                    created2 = []
                    consumed2 = apply_track_change_to_paragraph(
                        para_elem, old_norm, new_text or "", next_id, mod_author, date_str,
                        created_elems=created2,
                    )
                    if consumed2 is not False:
                        next_id += consumed2
                        if comment_text:
                            add_comment_to_xml(
                                comments_path, doc_tree, para_elem,
                                comment_text, next_id, mod_author, initials, date_str,
                                anchor_elems=created2,
                            )
                            next_id += 1
                        detail["status"] = "success"
                        detail["message"] = "Matched after normalization"
                        stats["success"] += 1
                    else:
                        # P2: 再尝试标点归一化 old_text
                        old_pnorm = normalize_punctuation(old_text)
                        para_full = get_paragraph_text(para_elem)
                        para_pnorm = normalize_punctuation(para_full)
                        # 如果归一化后能匹配，把原文中对应片段找出来
                        pnorm_pos = para_pnorm.find(old_pnorm)
                        if pnorm_pos != -1:
                            # 通过字符映射还原原文位置（近似）
                            created3 = []
                            consumed3 = apply_track_change_to_paragraph(
                                para_elem, old_text, new_text or "",
                                next_id, mod_author, date_str,
                                created_elems=created3,
                            )
                            if consumed3 is not False:
                                next_id += consumed3
                                if comment_text:
                                    add_comment_to_xml(
                                        comments_path, doc_tree, para_elem,
                                        comment_text, next_id, mod_author, initials, date_str,
                                        anchor_elems=created3,
                                    )
                                    next_id += 1
                                detail["status"] = "success"
                                detail["message"] = "Matched after punctuation normalization"
                                stats["success"] += 1
                                stats["details"].append(detail)
                                continue

                        # Fallback: add as comment only
                        fallback_comment = comment_text or f"[建议修改] 将「{old_text[:30]}」改为「{(new_text or '')[:30]}」"
                        add_comment_to_xml(
                            comments_path, doc_tree, para_elem,
                            fallback_comment, next_id, mod_author, initials, date_str
                        )
                        next_id += 1
                        detail["status"] = "partial"
                        detail["message"] = "Track change failed, added as comment. old_text not found in paragraph."
                        stats["success"] += 1  # Count as partial success

            elif mod_type == "comment_only":
                if not comment_text:
                    comment_text = f"[审查意见] {search_text[:50]}"
                add_comment_to_xml(
                    comments_path, doc_tree, para_elem,
                    comment_text, next_id, mod_author, initials, date_str
                )
                next_id += 1
                detail["status"] = "success"
                stats["success"] += 1

            elif mod_type == "delete":
                if not old_text:
                    old_text = search_text
                created_d = []
                consumed_d = apply_track_change_to_paragraph(
                    para_elem, old_text, "", next_id, mod_author, date_str,
                    created_elems=created_d,
                )
                if consumed_d is not False:
                    next_id += consumed_d
                    if comment_text:
                        add_comment_to_xml(
                            comments_path, doc_tree, para_elem,
                            comment_text, next_id, mod_author, initials, date_str,
                            anchor_elems=created_d,
                        )
                        next_id += 1
                    detail["status"] = "success"
                    stats["success"] += 1
                else:
                    if comment_text:
                        add_comment_to_xml(
                            comments_path, doc_tree, para_elem,
                            comment_text, next_id, mod_author, initials, date_str
                        )
                        next_id += 1
                    detail["status"] = "partial"
                    detail["message"] = "Delete failed, added as comment"
                    stats["success"] += 1

            elif mod_type == "insert_after":
                if not new_text:
                    detail["status"] = "failed"
                    detail["message"] = "new_text is required for insert_after"
                    stats["failed"] += 1
                    stats["details"].append(detail)
                    continue

                # Create insertion element
                ins_elem = etree.Element(_qn("w:ins"))
                ins_elem.set(_qn("w:id"), str(next_id))
                ins_elem.set(_qn("w:author"), mod_author)
                ins_elem.set(_qn("w:date"), date_str)
                ins_run = etree.SubElement(ins_elem, _qn("w:r"))
                ins_t = etree.SubElement(ins_run, _qn("w:t"))
                ins_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                ins_t.text = new_text
                next_id += 1

                # Find paragraph's parent and insert new paragraph after it
                parent = body
                para_idx = None
                for ci, child in enumerate(parent):
                    if child is para_elem:
                        para_idx = ci
                        break

                if para_idx is not None:
                    new_para = etree.Element(_qn("w:p"))
                    new_para.append(ins_elem)
                    parent.insert(para_idx + 1, new_para)

                    if comment_text:
                        add_comment_to_xml(
                            comments_path, doc_tree, new_para,
                            comment_text, next_id, mod_author, initials, date_str
                        )
                        next_id += 1

                    # Refresh paragraphs list
                    paragraphs = get_all_paragraphs(body)

                    detail["status"] = "success"
                    stats["success"] += 1
                else:
                    detail["status"] = "failed"
                    detail["message"] = "Could not find paragraph in body"
                    stats["failed"] += 1

            else:
                detail["status"] = "skipped"
                detail["message"] = f"Unknown type: {mod_type}"
                stats["skipped"] += 1

        except Exception as e:
            detail["status"] = "failed"
            detail["message"] = f"Exception: {str(e)}"
            stats["failed"] += 1
            traceback.print_exc()

        stats["details"].append(detail)

    # Save document.xml
    doc_tree.write(doc_xml_path, xml_declaration=True, encoding="UTF-8")

    # Re-pack to docx
    try:
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for dirpath, dirnames, filenames in os.walk(work_dir):
                for fname in filenames:
                    full_path = os.path.join(dirpath, fname)
                    arcname = os.path.relpath(full_path, work_dir)
                    zout.write(full_path, arcname)
    except Exception as e:
        print(f"[ERROR] Failed to create output docx: {e}")
        shutil.copy2(backup_path, output_path)
        stats["error"] = f"Pack failed: {e}"

    # Cleanup
    shutil.rmtree(work_dir, ignore_errors=True)

    # Validate output
    validation = validate_output(output_path)
    stats["validation"] = validation

    # Print summary
    print(f"\n{'='*50}")
    print(f"修改执行报告")
    print(f"{'='*50}")
    print(f"总计: {stats['total']} 条修改")
    print(f"成功: {stats['success']}")
    print(f"失败: {stats['failed']}")
    print(f"跳过: {stats['skipped']}")
    print(f"文件: {output_path}")
    print(f"验证: {'通过' if validation.get('valid') else '有问题'}")

    if validation.get("issues"):
        for issue in validation["issues"]:
            print(f"  - {issue}")

    failed_details = [d for d in stats["details"] if d["status"] == "failed"]
    if failed_details:
        print(f"\n失败详情:")
        for d in failed_details:
            print(f"  [{d['index']}] {d['message']}")

    return stats


# ---------------------------------------------------------------------------
# Output validation
# ---------------------------------------------------------------------------

def validate_output(docx_path: str) -> dict:
    """Validate the output docx file."""
    result = {"valid": True, "issues": []}

    try:
        with zipfile.ZipFile(docx_path, "r") as z:
            names = z.namelist()

            required = ["word/document.xml", "[Content_Types].xml"]
            for req in required:
                if req not in names:
                    result["issues"].append(f"缺少必要文件: {req}")
                    result["valid"] = False

            if "word/comments.xml" not in names:
                result["issues"].append("comments.xml 不存在，批注可能丢失")

            if "word/document.xml" in names:
                with z.open("word/document.xml") as doc_f:
                    content = doc_f.read().decode("utf-8")
                    ins_count = content.count("<w:ins ") + content.count("<w:ins>")
                    del_count = content.count("<w:del ") + content.count("<w:del>")
                    result["track_changes"] = ins_count + del_count

            if "word/comments.xml" in names:
                with z.open("word/comments.xml") as c_f:
                    content = c_f.read().decode("utf-8")
                    comment_count = content.count("<w:comment ")
                    result["comments"] = comment_count

    except zipfile.BadZipFile:
        result["valid"] = False
        result["issues"].append("文件不是有效的 docx")
    except Exception as e:
        result["issues"].append(f"验证异常: {str(e)}")

    return result


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

def dry_run_match(input_path: str, mods_json_path: str, report_path: str):
    """
    试匹配模式 — 不修改文档，仅报告每条 search_text 是否命中段落。
    让 LLM 在真正 apply 之前一轮修完错误 search_text，避免 apply 失败后的重改循环。
    """
    # 复用 process_modifications 的前置逻辑，但不执行任何写入
    with open(mods_json_path, "r", encoding="utf-8") as f:
        raw = f.read().lstrip("\ufeff")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        fixed = raw.replace("\u201c", '"').replace("\u201d", '"')
        fixed = fixed.replace("\u2018", "'").replace("\u2019", "'")
        data = json.loads(fixed)

    data, _ = validate_and_fix_json(data)
    mods = data.get("modifications", [])

    # 解出段落列表（复用解包逻辑）
    work_dir = input_path + "_dryrun_tmp"
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    with zipfile.ZipFile(input_path, "r") as z:
        z.extractall(work_dir)

    doc_xml_path = os.path.join(work_dir, "word", "document.xml")
    doc_tree = etree.parse(doc_xml_path)
    body = doc_tree.getroot().find(f"{W}body")
    paragraphs = get_all_paragraphs(body)

    report = {"total": len(mods), "matched": 0, "unmatched": 0, "details": []}
    for i, mod in enumerate(mods):
        search_text = mod.get("search_text", "")
        old_text = mod.get("old_text", "")
        para_idx = mod.get("paragraph_index", -1)
        match = find_paragraph(paragraphs, search_text, paragraph_index=para_idx)

        entry = {
            "index": i,
            "type": mod.get("type"),
            "risk_level": mod.get("risk_level"),
            "search_text_preview": search_text[:60] + ("..." if len(search_text) > 60 else ""),
        }
        if match is None:
            entry["status"] = "unmatched"
            entry["reason"] = "search_text 在文档中找不到匹配段落"
            # 提供前 3 段文本让 LLM 定位
            entry["hint_paragraphs"] = [
                {"idx": idx, "text_preview": text[:100]}
                for idx, _, text in paragraphs[:3] if text.strip()
            ]
            report["unmatched"] += 1
        else:
            idx, _, text = match
            # 对 track_change/delete 进一步验证 old_text 是否在段落内
            if old_text and old_text.strip() and old_text.strip() not in text:
                # 检查标点归一化后是否能找到
                if normalize_punctuation(old_text.strip()) not in normalize_punctuation(text):
                    entry["status"] = "old_text_missing"
                    entry["reason"] = f"search_text 命中段落 idx={idx}, 但 old_text 不在该段落内"
                    entry["matched_paragraph_idx"] = idx
                    entry["matched_paragraph_preview"] = text[:120]
                    report["unmatched"] += 1
                    report["details"].append(entry)
                    continue
            entry["status"] = "matched"
            entry["matched_paragraph_idx"] = idx
            report["matched"] += 1
        report["details"].append(entry)

    # 清理
    try:
        shutil.rmtree(work_dir)
    except Exception:
        pass

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"[dry-run] total={report['total']} matched={report['matched']} unmatched={report['unmatched']}")
    print(f"[dry-run] report: {report_path}")
    # 返回码:全部命中返回 0,有未命中返回 2(与真正的 apply 失败 1 区分)
    return 0 if report["unmatched"] == 0 else 2


def main():
    parser = argparse.ArgumentParser(description="合同审查批注引擎")
    parser.add_argument("--input", "-i", required=True, help="输入 docx 文件路径")
    parser.add_argument("--output", "-o", help="输出 docx 文件路径")
    parser.add_argument("--json", "-j", help="修改列表 JSON 文件路径")
    parser.add_argument("--extract-paragraphs", "-e", metavar="OUTPUT_TXT",
                        help="导出段落索引到文本文件 (P3)")
    parser.add_argument("--dry-run", metavar="REPORT_JSON",
                        help="试匹配模式:不修改文档,仅输出每条 search_text 的匹配报告")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"[ERROR] Input file not found: {args.input}")
        sys.exit(1)

    # P3: --extract-paragraphs 模式
    if args.extract_paragraphs:
        extract_paragraphs(args.input, args.extract_paragraphs)
        sys.exit(0)

    # --dry-run 模式
    if args.dry_run:
        if not args.json:
            print("[ERROR] --json is required in dry-run mode")
            sys.exit(1)
        if not os.path.exists(args.json):
            print(f"[ERROR] JSON file not found: {args.json}")
            sys.exit(1)
        rc = dry_run_match(args.input, args.json, args.dry_run)
        sys.exit(rc)

    # 正常审查模式
    if not args.output:
        print("[ERROR] --output is required in review mode")
        sys.exit(1)

    if not args.json:
        print("[ERROR] --json is required in review mode")
        sys.exit(1)

    if not os.path.exists(args.json):
        print(f"[ERROR] JSON file not found: {args.json}")
        sys.exit(1)

    stats = process_modifications(args.input, args.output, args.json)

    # Write stats to JSON for downstream consumption
    stats_path = args.output + ".stats.json"
    serializable_stats = {k: v for k, v in stats.items() if k != "details"}
    serializable_stats["details_count"] = len(stats.get("details", []))
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(serializable_stats, f, ensure_ascii=False, indent=2)

    sys.exit(0 if stats.get("success", 0) > 0 else 1)


if __name__ == "__main__":
    main()
