"""
模式 A 原文批注脚本 v3：纯 ZIP + XML 架构

架构说明：
- v1（已废弃）：Spire.Doc 插入 Comments + XML 插入修订标记。
  问题：Spire.Doc 重组 XML 结构，导致修订标记匹配全部失败。

- v2（已废弃）：Spire.Doc 仅做 .doc → .docx 格式转换，所有内容修改统一 XML 处理。
  问题：Spire.Doc 仍作为外部依赖引入大量兼容性问题（Python 3.12 猴子补丁、
  评估水印、pip 安装不稳定、许可证弹窗）。

- v3（当前）：完全去除 Spire.Doc 依赖。
  仅处理 .docx 文件（.doc 文件在 stage-4 层面直接降级为模式 B，不会到达本脚本）。
  所有操作通过 zipfile + xml.etree.ElementTree 在同一次 ZIP 读写中原子化完成：
    a. 插入批注（comments.xml + commentRange 标记）
    b. 插入修订标记（<w:del> + <w:ins>）
    c. 插入新段落（<w:ins> 整段）
  依赖：仅 Python 标准库（zipfile, xml.etree.ElementTree, json, re, copy, sys, os）。

  关键设计：批注标记（commentRange）先于修订标记插入。
  commentRangeStart/End 是段落级标记元素，不改变 <w:r> 内容，
  因此后续的修订标记插入（操作 <w:r> 元素）不受影响。

  insert_paragraphs 的逐条批注在 Step 3 插入新段落之后执行（Step 3b），
  避免链式锚点（第十一条之一等）在 Step 1 时尚未写入 document.xml。

输入 JSON 格式：
{
    "source_file": "合同文件路径（仅 .docx）",
    "output_file": "输出文件路径（.docx）",
    "author": "AI法律顾问",
    "tracked_changes": [
        {
            "old_text": "需要替换的原文文本",
            "new_text": "建议的替换文本",
            "comment": "批注内容（解释修改理由）"
        }
    ],
    "comments_only": [
        {
            "keyword": "定位关键字",
            "author_label": "重要风险",
            "comment": "批注完整内容"
        }
    ],
    "insert_paragraphs": [
        {
            "anchor_keyword": "插入位置的锚点关键字",
            "new_text": "建议插入的条款全文",
            "comment": "批注内容（解释补充理由）"
        }
    ]
}
"""

import json
import sys
import os
import re
import copy
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime


# ============================================================
# XML 文本安全（跨平台 Word 可打开）
# ============================================================

# XML 1.0 允许的字符范围；其余控制字符会导致 Word 报「文件已损坏」
_XML_ILLEGAL_RE = re.compile(
    r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x85-\x9f]'
)
# docx 被误当 UTF-8 文本写入 JSON 时常见 ZIP 头
_DOCX_ZIP_MAGIC = b'PK\x03\x04'


def _sanitize_xml_text(text):
    """移除 XML 1.0 非法控制字符，保留 \\t \\n \\r。"""
    if not text:
        return text
    if isinstance(text, bytes):
        text = text.decode('utf-8', errors='replace')
    return _XML_ILLEGAL_RE.sub('', text)


def _looks_like_embedded_docx(text):
    """检测是否误将 .docx 二进制/解压内容填入了 JSON 文本字段。"""
    if not text or not isinstance(text, str):
        return False
    if len(text) > 8000:
        return True
    sample = text[:512]
    if _DOCX_ZIP_MAGIC in sample.encode('utf-8', errors='ignore'):
        return True
    if '[Content_Types].xml' in sample or 'word/document.xml' in sample:
        return True
    if sample.count('\ufffd') >= 3:
        return True
    return False


def _validate_text_field(text, field_name):
    """校验 JSON 文本字段；异常内容返回 (False, reason)。"""
    if text is None:
        return True, None
    if not isinstance(text, str):
        return False, f'{field_name} 必须是字符串'
    if _looks_like_embedded_docx(text):
        return False, (
            f'{field_name} 疑似整份 docx 被当作文本填入（含 ZIP 头或 OOXML 路径）。'
            '请只复制合同原文中的 10-20 字连续片段，禁止 Read/cat 读取 .docx 文件内容。'
        )
    if '\x00' in text:
        return False, f'{field_name} 含空字节，可能来自二进制误读'
    return True, None


def _assert_distinct_paths(source_file, output_file):
    """禁止输出覆盖源文件路径（规范化后比较）。"""
    src = os.path.abspath(os.path.normpath(source_file))
    out = os.path.abspath(os.path.normpath(output_file))
    if src == out:
        raise ValueError(
            f'source_file 与 output_file 不能相同：{source_file}\n'
            '请将 output_file 设为另存的批注版路径。'
        )


# ============================================================
# 文本归一化工具（三轮容错匹配）
# ============================================================

_PUNCT_RE = re.compile(
    r'[，。、；：\u201c\u201d\u2018\u2019【】（）《》？！…—·\s\u3000'
    r',.\;:\"\'()\[\]{}<>?!~`@#$%^&*_+=\/\\|\-]'
)


def _normalize(text):
    """去除所有标点和空白，只保留文字和数字。"""
    return _PUNCT_RE.sub('', text)


def _build_norm_map(text):
    """归一化文本，同时返回每个归一化字符对应的原始索引。
    返回 (normalized_str, list_of_original_indices)。"""
    norm_chars = []
    orig_indices = []
    for i, c in enumerate(text):
        if not _PUNCT_RE.match(c):
            norm_chars.append(c)
            orig_indices.append(i)
    return ''.join(norm_chars), orig_indices


# ============================================================
# OOXML 命名空间常量
# ============================================================

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'

NAMESPACES = {
    'w': W,
    'r': R_NS,
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'w14': 'http://schemas.microsoft.com/office/word/2010/wordml',
    'w15': 'http://schemas.microsoft.com/office/word/2012/wordml',
    'wps': 'http://schemas.microsoft.com/office/word/2010/wordprocessingShape',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'v': 'urn:schemas-microsoft-com:vml',
    'o': 'urn:schemas-microsoft-com:office:office',
}

for prefix, uri in NAMESPACES.items():
    ET.register_namespace(prefix, uri)


# ============================================================
# XML 辅助函数
# ============================================================

def make_run(rpr_template, text, is_del=False):
    """创建一个 <w:r>，复制格式属性，填入文本。"""
    r = ET.Element(f'{{{W}}}r')
    if rpr_template is not None:
        r.append(copy.deepcopy(rpr_template))
    tag = f'{{{W}}}delText' if is_del else f'{{{W}}}t'
    t = ET.SubElement(r, tag)
    t.set(XML_SPACE, 'preserve')
    t.text = _sanitize_xml_text(text)
    return r


def _get_para_text(para):
    """从 <w:p> 元素中提取纯文本（仅 <w:t>，不含 <w:delText>）。"""
    return ''.join(t.text or '' for t in para.findall(f'.//{{{W}}}t'))


def _find_para_xml(body, keyword):
    """在 body 中查找包含 keyword 的 <w:p> 段落。三轮容错匹配。
    返回 <w:p> Element 或 None。"""
    # 第一轮：精确匹配
    for para in body.iter(f'{{{W}}}p'):
        if keyword in _get_para_text(para):
            return para
    # 第二轮：去空格
    keyword_stripped = keyword.replace(' ', '').replace('\u3000', '')
    for para in body.iter(f'{{{W}}}p'):
        text = _get_para_text(para)
        if keyword_stripped in text.replace(' ', '').replace('\u3000', ''):
            return para
    # 第三轮：去标点归一化
    keyword_norm = _normalize(keyword)
    if keyword_norm:
        for para in body.iter(f'{{{W}}}p'):
            if keyword_norm in _normalize(_get_para_text(para)):
                return para
    return None


def _find_para_for_insert(body, ins):
    """
    Step 3 之后定位 insert 对应段落。
    优先用 new_text 首行（必在新插入段落内），再回退 anchor_keyword。
    """
    new_first = (ins.get('new_text') or '').split('\n')[0].strip()
    if new_first:
        para = _find_para_xml(body, new_first)
        if para is not None:
            return para
    kw = ins.get('anchor_keyword') or ''
    if kw:
        return _find_para_xml(body, kw)
    return None


# ============================================================
# 修订标记操作
# ============================================================

def add_tracked_change(body, old_text, new_text, author, rev_id, date_str):
    """
    文本替换型修订：找到 old_text 所在段落，用 <w:del>+<w:ins> 替换。
    三轮容错匹配：精确 -> 去空格 -> 去标点归一化。
    返回更新后的 rev_id。

    注意：此函数只操作 <w:r> 元素（通过 ch.tag == <w:r> 过滤），
    因此不会影响段落中已存在的 commentRangeStart/End 标记。
    commentReference <w:r> 没有 <w:t> 子元素，text_content 为空，也被跳过。
    """

    def _strip(s):
        return s.replace(' ', '').replace('\u3000', '')

    for para in body.iter(f'{{{W}}}p'):
        runs, pos = [], 0
        for ch in list(para):
            if ch.tag == f'{{{W}}}r':
                t_texts = [t.text or '' for t in ch.findall(f'{{{W}}}t')]
                text_content = ''.join(t_texts)
                if text_content:
                    runs.append({'elem': ch, 'text': text_content,
                                 'start': pos, 'end': pos + len(text_content)})
                    pos += len(text_content)
        full = ''.join(r['text'] for r in runs)

        # 第一轮：精确匹配
        idx = full.find(old_text)
        actual_old = old_text

        # 第二轮：去空格
        if idx < 0:
            full_s = _strip(full)
            old_s = _strip(old_text)
            idx_s = full_s.find(old_s)
            if idx_s >= 0:
                count = 0
                idx = None
                for i, c in enumerate(full):
                    if c not in (' ', '\u3000'):
                        if count == idx_s and idx is None:
                            idx = i
                        count += 1
                        if count == idx_s + len(old_s):
                            end_orig = i + 1
                            break
                    else:
                        if count == idx_s and idx is None:
                            idx = i
                if idx is not None:
                    actual_old = full[idx:end_orig]

        # 第三轮：去标点归一化
        if idx is None or idx < 0:
            full_norm, orig_map = _build_norm_map(full)
            old_norm = _normalize(old_text)
            idx_n = full_norm.find(old_norm)
            if idx_n >= 0 and idx_n + len(old_norm) <= len(orig_map):
                idx = orig_map[idx_n]
                end_orig = orig_map[idx_n + len(old_norm) - 1] + 1
                actual_old = full[idx:end_orig]
            else:
                continue

        end = idx + len(actual_old)
        affected = [r for r in runs if r['end'] > idx and r['start'] < end]
        if not affected:
            continue
        first, last = affected[0], affected[-1]
        before = first['text'][:idx - first['start']]
        after = last['text'][end - last['start']:]
        rpr_copy = copy.deepcopy(first['elem'].find(f'{{{W}}}rPr'))
        ins_pos = list(para).index(first['elem'])
        for a in affected:
            para.remove(a['elem'])
        new_elems = []
        if before:
            new_elems.append(make_run(rpr_copy, before))
        # <w:del>
        del_el = ET.Element(f'{{{W}}}del')
        del_el.set(f'{{{W}}}id', str(rev_id))
        del_el.set(f'{{{W}}}author', author)
        del_el.set(f'{{{W}}}date', date_str)
        del_el.append(make_run(rpr_copy, actual_old, is_del=True))
        new_elems.append(del_el)
        # <w:ins>
        ins_el = ET.Element(f'{{{W}}}ins')
        ins_el.set(f'{{{W}}}id', str(rev_id + 1))
        ins_el.set(f'{{{W}}}author', author)
        ins_el.set(f'{{{W}}}date', date_str)
        ins_el.append(make_run(rpr_copy, new_text))
        new_elems.append(ins_el)
        if after:
            new_elems.append(make_run(rpr_copy, after))
        for i, el in enumerate(new_elems):
            para.insert(ins_pos + i, el)
        return rev_id + 2
    return rev_id


def insert_tracked_paragraph(body, anchor_text, new_para_text, author, rev_id, date_str):
    """
    段落插入型修订：在 anchor_text 所在段落之后插入新段落（显示为绿色新增）。
    三轮容错匹配。返回更新后的 rev_id。
    """
    anchor_stripped = anchor_text.replace(' ', '').replace('\u3000', '')
    anchor_norm = _normalize(anchor_text)
    for para in body.iter(f'{{{W}}}p'):
        texts = [t.text or '' for t in para.findall(f'.//{{{W}}}t')]
        joined = ''.join(texts)
        # 三轮匹配
        if (anchor_text not in joined
                and anchor_stripped not in joined.replace(' ', '').replace('\u3000', '')
                and anchor_norm not in _normalize(joined)):
            continue
        new_p = ET.Element(f'{{{W}}}p')
        ppr = ET.SubElement(new_p, f'{{{W}}}pPr')
        rpr_ppr = ET.SubElement(ppr, f'{{{W}}}rPr')
        ins_mark = ET.SubElement(rpr_ppr, f'{{{W}}}ins')
        ins_mark.set(f'{{{W}}}id', str(rev_id))
        ins_mark.set(f'{{{W}}}author', author)
        ins_mark.set(f'{{{W}}}date', date_str)
        ins_el = ET.Element(f'{{{W}}}ins')
        ins_el.set(f'{{{W}}}id', str(rev_id + 1))
        ins_el.set(f'{{{W}}}author', author)
        ins_el.set(f'{{{W}}}date', date_str)
        ins_el.append(make_run(None, new_para_text))
        new_p.append(ins_el)
        children = list(body)
        if para in children:
            body.insert(children.index(para) + 1, new_p)
        return rev_id + 2
    return rev_id


# ============================================================
# XML 批注操作
# ============================================================

def add_xml_comment_to_para(para, comment_id):
    """
    在段落中添加 OOXML 批注标记：
    - commentRangeStart 插入段落最前面
    - commentRangeEnd + commentReference 插入段落末尾

    这些是标记元素，不修改任何 <w:r> 文本内容，
    因此不会干扰后续 add_tracked_change 的文本匹配。
    """
    # <w:commentRangeStart>
    crs = ET.Element(f'{{{W}}}commentRangeStart')
    crs.set(f'{{{W}}}id', str(comment_id))
    para.insert(0, crs)

    # <w:commentRangeEnd>
    cre = ET.Element(f'{{{W}}}commentRangeEnd')
    cre.set(f'{{{W}}}id', str(comment_id))
    para.append(cre)

    # <w:r> with <w:commentReference>
    ref_run = ET.Element(f'{{{W}}}r')
    ref_rpr = ET.SubElement(ref_run, f'{{{W}}}rPr')
    ref_style = ET.SubElement(ref_rpr, f'{{{W}}}rStyle')
    ref_style.set(f'{{{W}}}val', 'CommentReference')
    ref_cr = ET.SubElement(ref_run, f'{{{W}}}commentReference')
    ref_cr.set(f'{{{W}}}id', str(comment_id))
    para.append(ref_run)


def _build_comment_element(comment_id, author, date_str, text):
    """创建单个 <w:comment> 元素，用于 comments.xml。"""
    comment = ET.Element(f'{{{W}}}comment')
    comment.set(f'{{{W}}}id', str(comment_id))
    comment.set(f'{{{W}}}author', author)
    comment.set(f'{{{W}}}date', date_str)
    comment.set(f'{{{W}}}initials', author[:2] if author else 'AI')

    has_content = False
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        p = ET.SubElement(comment, f'{{{W}}}p')
        r = ET.SubElement(p, f'{{{W}}}r')
        t = ET.SubElement(r, f'{{{W}}}t')
        t.set(XML_SPACE, 'preserve')
        t.text = _sanitize_xml_text(line)
        has_content = True

    # 确保至少一个段落
    if not has_content:
        p = ET.SubElement(comment, f'{{{W}}}p')
        r = ET.SubElement(p, f'{{{W}}}r')
        t = ET.SubElement(r, f'{{{W}}}t')
        t.text = _sanitize_xml_text(text[:200] if text else '(empty)')

    return comment


def build_comments_xml_bytes(comments_data):
    """
    构建 word/comments.xml 文件内容。
    comments_data: list of (comment_id, author, date_str, text)
    返回 bytes。
    """
    root = ET.Element(f'{{{W}}}comments')
    for cid, cauthor, cdate, ctext in comments_data:
        root.append(_build_comment_element(cid, cauthor, cdate, ctext))
    return (
        b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        + ET.tostring(root, encoding='unicode').encode('utf-8')
    )


# ============================================================
# 统一 XML 处理（核心）
# ============================================================

def process_unified_xml(input_docx, output_file, input_data):
    """
    统一 XML 处理：在同一次 ZIP 读写中原子化完成所有文档修改。

    执行顺序（精心设计，不可调换）：
    1. 插入批注标记（tc / comments_only；inserts 仅汇总批注）
    2. 插入修订标记（del/ins —— 修改 <w:r>，但 comment 标记不受影响）
    3. 插入新段落（ins 整段 —— 在已有段落之后追加）
    3b. 为 insert_paragraphs 逐条添加批注（须在 Step 3 之后，支持链式锚点）

    为什么批注先于修订标记：
    - commentRangeStart/End 是段落级标记元素（与 <w:r> 同级但独立）
    - add_tracked_change 只操作 <w:r> 元素（收集文本 -> 定位 -> 替换）
    - 它通过 ch.tag == <w:r> 过滤，自动跳过 commentRange 标记
    - commentReference <w:r> 没有 <w:t> 子元素，text_content 为空，也被跳过
    - 因此批注标记不会干扰修订标记的文本匹配和定位
    """
    author = input_data.get("author", "AI法律顾问")
    date_str = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')

    comments_data = []  # (comment_id, author, date_str, text)
    comment_id_counter = 100
    stats = {'comments': 0, 'tracked_changes': 0, 'insertions': 0,
             'comments_skipped': 0, 'tc_skipped': 0, 'ins_skipped': 0}

    _assert_distinct_paths(input_docx, output_file)

    # ── 读取 ZIP（保留 ZipInfo，写出时兼容 Windows / macOS Word）──
    zip_entries = {}
    with zipfile.ZipFile(input_docx, 'r') as zin:
        for item in zin.infolist():
            zip_entries[item.filename] = (item, zin.read(item.filename))

    # ── 解析 document.xml ──
    if 'word/document.xml' not in zip_entries:
        raise RuntimeError(f'无效的 docx：缺少 word/document.xml — {input_docx}')
    _, doc_xml = zip_entries['word/document.xml']
    root = ET.fromstring(doc_xml)
    body = root.find(f'{{{W}}}body')

    # ── Step 1: 插入所有批注（仅添加标记，不修改文本） ──
    inserts = input_data.get("insert_paragraphs", [])

    def _skip_bad_item(item, field, stats_key):
        ok, reason = _validate_text_field(item.get(field), field)
        if not ok:
            print(f'[WARN] 跳过条目（{field}）：{reason}')
            stats[stats_key] += 1
            return True
        return False

    # 1a. 为 tracked_changes 添加批注
    for tc in input_data.get("tracked_changes", []):
        if _skip_bad_item(tc, 'old_text', 'comments_skipped'):
            continue
        para = _find_para_xml(body, tc["old_text"])
        if para is not None:
            cid = comment_id_counter
            comment_id_counter += 1
            add_xml_comment_to_para(para, cid)
            comment_text = tc["comment"] + "\n已通过修订标记建议修改，请审阅。"
            comments_data.append((cid, author, date_str, comment_text))
            stats['comments'] += 1
        else:
            stats['comments_skipped'] += 1

    # 1b. 为 comments_only 添加批注
    for co in input_data.get("comments_only", []):
        if _skip_bad_item(co, 'keyword', 'comments_skipped'):
            continue
        para = _find_para_xml(body, co["keyword"])
        if para is not None:
            cid = comment_id_counter
            comment_id_counter += 1
            add_xml_comment_to_para(para, cid)
            al = co.get("author_label", author)
            comments_data.append((cid, al, date_str, co["comment"]))
            stats['comments'] += 1
        else:
            stats['comments_skipped'] += 1

    # 1c. 为 insert_paragraphs 添加批注
    if inserts:
        # 汇总批注：在第一个锚点段落上
        anchor_para = _find_para_xml(body, inserts[0]["anchor_keyword"])
        if anchor_para is not None:
            cid = comment_id_counter
            comment_id_counter += 1
            summary = "【缺失条款提示】以下关键条款已通过修订标记建议新增，请审阅："
            for ins in inserts:
                summary += "\n- " + ins["new_text"].split('\n')[0]
            add_xml_comment_to_para(anchor_para, cid)
            comments_data.append((cid, "缺失条款", date_str, summary))
            stats['comments'] += 1
        # 逐条批注见 Step 3b（须在插入新段落之后，链式锚点才能命中）

    print(f"[Step 1] 批注插入完成：{stats['comments']} 条成功"
          + (f"，{stats['comments_skipped']} 条关键字未匹配" if stats['comments_skipped'] else ""))

    # ── Step 2: 插入修订标记（文本替换） ──
    rev_id = 200
    for tc in input_data.get("tracked_changes", []):
        if (_validate_text_field(tc.get("old_text"), "old_text")[0] is False
                or _validate_text_field(tc.get("new_text"), "new_text")[0] is False):
            stats['tc_skipped'] += 1
            continue
        old_rev = rev_id
        rev_id = add_tracked_change(
            body,
            _sanitize_xml_text(tc["old_text"]),
            _sanitize_xml_text(tc["new_text"]),
            author, rev_id, date_str,
        )
        if rev_id > old_rev:
            stats['tracked_changes'] += 1
        else:
            stats['tc_skipped'] += 1

    print(f"[Step 2] 修订标记插入完成：{stats['tracked_changes']} 条成功"
          + (f"，{stats['tc_skipped']} 条关键字未匹配" if stats['tc_skipped'] else ""))

    # ── Step 3: 插入新段落（缺失条款） ──
    for i, ins in enumerate(inserts):
        if (_validate_text_field(ins.get("anchor_keyword"), "anchor_keyword")[0] is False
                or _validate_text_field(ins.get("new_text"), "new_text")[0] is False):
            stats['ins_skipped'] += 1
            continue
        anchor = ins["anchor_keyword"]
        if i > 0:
            prev_text = inserts[i - 1]["new_text"]
            first_line = prev_text.split('\n')[0]
            if first_line.strip():
                anchor = first_line.strip()
        old_rev = rev_id
        rev_id = insert_tracked_paragraph(
            body, anchor, _sanitize_xml_text(ins["new_text"]),
            author, rev_id, date_str)
        if rev_id > old_rev:
            stats['insertions'] += 1
        else:
            stats['ins_skipped'] += 1

    if inserts:
        print(f"[Step 3] 新增段落插入完成：{stats['insertions']} 条成功"
              + (f"，{stats['ins_skipped']} 条锚点未匹配" if stats['ins_skipped'] else ""))

    # ── Step 3b: 为已插入段落添加逐条批注（链式锚点须在 Step 3 之后）──
    insert_comment_ok = 0
    insert_comment_skip = 0
    for ins in inserts:
        if _skip_bad_item(ins, 'anchor_keyword', 'comments_skipped'):
            insert_comment_skip += 1
            continue
        para = _find_para_for_insert(body, ins)
        if para is not None:
            cid = comment_id_counter
            comment_id_counter += 1
            add_xml_comment_to_para(para, cid)
            comments_data.append((cid, "缺失条款", date_str, ins["comment"]))
            stats['comments'] += 1
            insert_comment_ok += 1
        else:
            stats['comments_skipped'] += 1
            insert_comment_skip += 1

    if inserts:
        print(f"[Step 3b] 缺失条款逐条批注：{insert_comment_ok} 条成功"
              + (f"，{insert_comment_skip} 条未匹配" if insert_comment_skip else ""))

    # ── Step 4: 序列化并写出 ──
    doc_xml_new = (
        b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        + ET.tostring(root, encoding='unicode').encode('utf-8')
    )

    # 构建 comments.xml
    comments_xml_bytes = None
    if comments_data:
        comments_xml_bytes = build_comments_xml_bytes(comments_data)

    def _write_entry(zout, filename, payload, orig_info=None):
        if orig_info is not None:
            info = zipfile.ZipInfo(filename, orig_info.date_time)
            info.compress_type = orig_info.compress_type
            info.external_attr = orig_info.external_attr
            info.internal_attr = orig_info.internal_attr
            info.create_system = orig_info.create_system
            info.flag_bits = orig_info.flag_bits
            zout.writestr(info, payload)
        else:
            zout.writestr(filename, payload)

    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zout:
        for filename, entry in zip_entries.items():
            orig_info, data = entry
            if filename == 'word/document.xml':
                _write_entry(zout, filename, doc_xml_new, orig_info)
            elif filename == 'word/comments.xml' and comments_xml_bytes:
                # 替换已有的 comments.xml
                _write_entry(zout, filename, comments_xml_bytes, orig_info)
            elif filename == '[Content_Types].xml' and comments_data:
                # 确保 comments content type 已注册
                ct_str = data.decode('utf-8')
                if '/word/comments.xml' not in ct_str:
                    ct_str = ct_str.replace(
                        '</Types>',
                        '<Override PartName="/word/comments.xml" '
                        'ContentType="application/vnd.openxmlformats-officedocument.'
                        'wordprocessingml.comments+xml"/>\n</Types>'
                    )
                _write_entry(zout, filename, ct_str.encode('utf-8'), orig_info)
            elif filename == 'word/_rels/document.xml.rels' and comments_data:
                # 确保 comments relationship 已注册
                rels_str = data.decode('utf-8')
                if 'relationships/comments' not in rels_str:
                    rids = [int(m) for m in re.findall(r'rId(\d+)', rels_str)]
                    next_rid = max(rids) + 1 if rids else 1
                    rels_str = rels_str.replace(
                        '</Relationships>',
                        f'<Relationship Id="rId{next_rid}" '
                        f'Type="http://schemas.openxmlformats.org/officeDocument/'
                        f'2006/relationships/comments" Target="comments.xml"/>\n'
                        f'</Relationships>'
                    )
                _write_entry(zout, filename, rels_str.encode('utf-8'), orig_info)
            else:
                _write_entry(zout, filename, data, orig_info)

        # 如果原 ZIP 中没有 comments.xml，新增之
        if comments_xml_bytes and 'word/comments.xml' not in zip_entries:
            _write_entry(zout, 'word/comments.xml', comments_xml_bytes)

    return stats


# ============================================================
# 预检函数
# ============================================================

def pre_check(input_data):
    """
    预检：验证所有关键字是否能在文档中匹配到对应段落。
    仅支持 .docx 文件（.doc 文件应在 stage-4 层面降级为模式 B）。

    返回 dict:
        {
            "total": int,
            "matched": [(type, keyword_preview)],
            "failed": [(type, keyword_preview)],
            "match_rate": float  # 0.0 ~ 1.0
        }
    调用方可据此决定是否需要修正关键字后重试。
    """
    if isinstance(input_data, str):
        with open(input_data, 'r', encoding='utf-8') as f:
            input_data = json.load(f)

    source_file = input_data["source_file"]

    # .doc 文件不应到达本脚本
    if source_file.lower().endswith('.doc') and not source_file.lower().endswith('.docx'):
        raise RuntimeError(
            f"不支持 .doc 格式：{source_file}\n"
            ".doc 文件应在阶段四模式判断中降级为模式 B，不应到达本脚本。"
        )

    # 解析 XML
    with zipfile.ZipFile(source_file, 'r') as z:
        doc_xml = z.read('word/document.xml')
    root = ET.fromstring(doc_xml)
    body = root.find(f'{{{W}}}body')

    matched, failed = [], []

    for tc in input_data.get("tracked_changes", []):
        kw = tc["old_text"]
        preview = kw[:40] + ("..." if len(kw) > 40 else "")
        if _find_para_xml(body, kw) is not None:
            matched.append(("tracked_change", preview))
        else:
            failed.append(("tracked_change", preview))

    for co in input_data.get("comments_only", []):
        kw = co["keyword"]
        preview = kw[:40] + ("..." if len(kw) > 40 else "")
        if _find_para_xml(body, kw) is not None:
            matched.append(("comment_only", preview))
        else:
            failed.append(("comment_only", preview))

    for ins in input_data.get("insert_paragraphs", []):
        kw = ins["anchor_keyword"]
        preview = kw[:40] + ("..." if len(kw) > 40 else "")
        if _find_para_xml(body, kw) is not None:
            matched.append(("insert_paragraph", preview))
        else:
            failed.append(("insert_paragraph", preview))

    total = len(matched) + len(failed)
    result = {
        "total": total,
        "matched": matched,
        "failed": failed,
        "match_rate": len(matched) / total if total > 0 else 1.0,
    }

    # 打印摘要
    print(f"\n[Pre-check] 关键字匹配预检完成："
          f"{len(matched)}/{total} 命中（{result['match_rate']:.0%}）")
    if failed:
        print(f"[Pre-check] 以下 {len(failed)} 个关键字未匹配到：")
        for typ, preview in failed:
            print(f"  - [{typ}] {preview}")
        if result['match_rate'] < 0.5:
            print(f"[Pre-check] 匹配率低于 50%，强烈建议修正关键字后重试！")
    else:
        print(f"[Pre-check] 所有关键字均已匹配。")

    return result


# ============================================================
# 主入口
# ============================================================

def run(input_data):
    """
    主函数。接收 input_data（dict 或 JSON 文件路径），执行统一 XML 处理。
    仅支持 .docx 文件（.doc 文件应在 stage-4 层面降级为模式 B）。

    流程：
    1. 验证源文件为 .docx 格式
    2. 在 .docx 上执行统一 XML 处理（批注 + 修订 + 插入）
    3. 输出最终 .docx 文件
    """
    if isinstance(input_data, str):
        with open(input_data, 'r', encoding='utf-8') as f:
            input_data = json.load(f)

    source_file = input_data["source_file"]
    output_file = input_data["output_file"]
    _assert_distinct_paths(source_file, output_file)

    if not os.path.isfile(source_file):
        raise FileNotFoundError(f'源文件不存在：{source_file}')

    # .doc 文件不应到达本脚本
    if source_file.lower().endswith('.doc') and not source_file.lower().endswith('.docx'):
        raise RuntimeError(
            f"不支持 .doc 格式：{source_file}\n"
            ".doc 文件应在阶段四模式判断中降级为模式 B，不应到达本脚本。"
        )

    # 统一 XML 处理
    print(f"[处理] 统一 XML 处理（批注 + 修订标记）...")
    stats = process_unified_xml(source_file, output_file, input_data)

    # 汇总
    total_ops = stats['comments'] + stats['tracked_changes'] + stats['insertions']
    total_skipped = stats['comments_skipped'] + stats['tc_skipped'] + stats['ins_skipped']
    print(f"\n[Done] 输出文件：{output_file}")
    print(f"[Done] 处理汇总：{total_ops} 项成功"
          + (f"，{total_skipped} 项跳过（关键字未匹配）" if total_skipped else ""))

    return stats


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  python mode_a_annotator.py <input.json>           # 执行主流程")
        print("  python mode_a_annotator.py --precheck <input.json> # 仅预检关键字匹配")
        sys.exit(1)

    if sys.argv[1] == '--precheck':
        if len(sys.argv) < 3:
            print("用法: python mode_a_annotator.py --precheck <input.json>")
            sys.exit(1)
        result = pre_check(sys.argv[2])
        # 以退出码反映匹配率：0=通过(>=80%), 1=不通过(<80%)
        sys.exit(0 if result['match_rate'] >= 0.8 else 1)
    else:
        run(sys.argv[1])
