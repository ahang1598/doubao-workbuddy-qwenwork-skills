#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mode_a_verifier.py — 模式 A 批注/修订二次校验工具
版本：v4.0.1
用途：在 mode_a_annotator.py 执行完毕后，读取输出 .docx 的 XML，
      统计实际嵌入的批注数与修订数，与 mode_a_input.json 的期望数量对比，
      输出校验报告。退出码 0 = 全部通过，退出码 1 = 存在缺失。

用法：
    python mode_a_verifier.py <input_json> <output_docx>

示例：
    python mode_a_verifier.py mode_a_input.json 合同名称_原文批注版.docx
"""

import sys
import json
import zipfile
import unicodedata
import re
from xml.etree import ElementTree as ET

# ── XML 命名空间 ──────────────────────────────────────────────────────────────
NS = {
    "w":   "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
}


def _strip_ns(tag: str) -> str:
    """去除 Clark 格式命名空间，返回本地名称。"""
    return tag.split("}")[-1] if "}" in tag else tag


def _normalize(text: str) -> str:
    """归一化：去空格、去标点、NFKC Unicode 规范化，用于容错比对。"""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\s\u3000]+", "", text)
    text = re.sub(r"[^\w\u4e00-\u9fff]", "", text)
    return text.lower()


def _iter_text(elem) -> str:
    """递归提取 w:t / w:delText 文本（修订删除内容在 delText 而非 t）。"""
    parts = []
    for node in elem.iter():
        local = _strip_ns(node.tag)
        if local in ("t", "delText") and node.text:
            parts.append(node.text)
    return "".join(parts)


# XML 1.0 非法控制字符（Word 会报文件损坏）
_XML_ILLEGAL_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x85-\x9f]"
)
_DOCX_ZIP_MAGIC = b"PK\x03\x04"


def check_document_integrity(doc_xml: bytes) -> list:
    """
    检测 document.xml 是否含 docx 误嵌入、非法控制字符或正文近乎为空。
    返回问题描述列表；空列表表示通过。
    """
    issues = []
    if not doc_xml:
        issues.append("document.xml 为空")
        return issues

    if _DOCX_ZIP_MAGIC in doc_xml[:4096]:
        issues.append(
            "document.xml 含 ZIP 文件头 PK\\x03\\x04，疑似将 .docx 二进制写入了正文"
        )

    try:
        root = ET.fromstring(doc_xml)
    except ET.ParseError as e:
        issues.append(f"document.xml 无法解析：{e}")
        return issues

    text_nodes = 0
    meaningful = 0
    illegal_count = 0
    for node in root.iter():
        local = _strip_ns(node.tag)
        if local not in ("t", "delText") or not node.text:
            continue
        text_nodes += 1
        illegal_count += len(_XML_ILLEGAL_RE.findall(node.text))
        stripped = re.sub(r"[\s\u3000\.\-]+", "", node.text)
        if stripped:
            meaningful += 1

    if illegal_count > 0:
        issues.append(
            f"document.xml 含 {illegal_count} 个 XML 非法控制字符（Word 将拒绝打开）"
        )

    if text_nodes > 20 and meaningful < max(3, text_nodes // 10):
        issues.append(
            f"正文文本节点 {text_nodes} 个，但有效内容节点仅 {meaningful} 个，疑似正文被污染或清空"
        )

    return issues


# ── 读取输入 JSON ─────────────────────────────────────────────────────────────

def load_input(json_path: str) -> dict:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    tracked    = data.get("tracked_changes",   [])
    comments   = data.get("comments_only",     [])
    inserts    = data.get("insert_paragraphs", [])
    # inserts：每条 1 个逐条批注 + 有 inserts 时额外 1 条汇总批注（annotator Step 1c）
    insert_comment_slots = len(inserts) + (1 if inserts else 0)
    return {
        "tracked":  tracked,
        "comments": comments,
        "inserts":  inserts,
        "expected_comment_count": len(tracked) + len(comments) + insert_comment_slots,
        "expected_tc_count":      len(tracked),
        "expected_insert_count":  len(inserts),
    }


# ── 读取输出 DOCX ─────────────────────────────────────────────────────────────

def load_docx(docx_path: str) -> dict:
    """解压 .docx，返回 comments.xml 和 document.xml 的解析树。"""
    with zipfile.ZipFile(docx_path, "r") as z:
        names = z.namelist()
        doc_xml      = z.read("word/document.xml")      if "word/document.xml"      in names else b""
        comments_xml = z.read("word/comments.xml")      if "word/comments.xml"      in names else b""
        comments_ext = z.read("word/commentsExtended.xml") if "word/commentsExtended.xml" in names else b""

    doc_tree      = ET.fromstring(doc_xml)      if doc_xml      else None
    comments_tree = ET.fromstring(comments_xml) if comments_xml else None

    return {
        "doc_tree":      doc_tree,
        "comments_tree": comments_tree,
        "has_comments":  comments_xml != b"",
    }


# ── 统计实际批注数 ─────────────────────────────────────────────────────────────

def count_actual_comments(comments_tree) -> int:
    """统计 comments.xml 中 w:comment 节点数量。"""
    if comments_tree is None:
        return 0
    return sum(1 for elem in comments_tree
               if _strip_ns(elem.tag) == "comment")


# ── 统计实际修订标记 ──────────────────────────────────────────────────────────

def count_actual_tracked_changes(doc_tree) -> dict:
    """
    统计 document.xml 中修订相关节点。
    返回 {"ins": N, "del": N}（段落级，去重计数）
    """
    if doc_tree is None:
        return {"ins": 0, "del": 0}

    ins_ids = set()
    del_ids = set()

    for elem in doc_tree.iter():
        local = _strip_ns(elem.tag)
        if local == "ins":
            rid = elem.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id", "")
            ins_ids.add(rid or id(elem))
        elif local == "del":
            rid = elem.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id", "")
            del_ids.add(rid or id(elem))

    return {"ins": len(ins_ids), "del": len(del_ids)}


# ── 逐条校验 tracked_changes 的 old_text 是否出现在 del 节点中 ─────────────────

def verify_tracked_items(doc_tree, tracked_items: list) -> list:
    """
    对每条 tracked_change，检查其 old_text 是否能在 document.xml 的
    w:del 节点文本中找到（三轮容错：精确 → 去空格 → 归一化）。
    返回未命中条目列表：[{"index": i, "old_text": "...", "reason": "..."}]
    """
    if doc_tree is None or not tracked_items:
        return []

    # 预先提取所有 w:del 节点的文本
    del_texts = []
    for elem in doc_tree.iter():
        if _strip_ns(elem.tag) == "del":
            t = _iter_text(elem)
            if t:
                del_texts.append(t)

    misses = []
    for i, item in enumerate(tracked_items):
        old = item.get("old_text", "").strip()
        if not old:
            continue

        # 轮一：精确包含
        if any(old in dt for dt in del_texts):
            continue
        # 轮二：去空格
        old_nospace = re.sub(r"\s+", "", old)
        if any(old_nospace in re.sub(r"\s+", "", dt) for dt in del_texts):
            continue
        # 轮三：归一化
        old_norm = _normalize(old)
        if any(old_norm in _normalize(dt) for dt in del_texts):
            continue

        misses.append({
            "index":    i + 1,
            "old_text": old[:40] + ("…" if len(old) > 40 else ""),
            "reason":   "在输出文档的删除标记中未找到对应文本",
        })

    return misses


# ── 逐条校验 insert_paragraphs 的 anchor_keyword 是否出现在 ins 节点中 ────────

def verify_insert_items(doc_tree, insert_items: list) -> list:
    """
    对每条 insert_paragraph，检查其 anchor_keyword 附近是否有 w:ins 节点。
    策略：检查 w:ins 节点文本中是否包含 new_text 的前 10 个字符。
    """
    if doc_tree is None or not insert_items:
        return []

    ins_texts = []
    for elem in doc_tree.iter():
        if _strip_ns(elem.tag) == "ins":
            t = _iter_text(elem)
            if t:
                ins_texts.append(t)

    misses = []
    for i, item in enumerate(insert_items):
        new_text = item.get("new_text", "").strip()
        anchor   = item.get("anchor_keyword", "").strip()
        probe    = new_text[:15] if new_text else anchor

        if not probe:
            continue

        probe_norm = _normalize(probe)
        if any(probe_norm in _normalize(it) for it in ins_texts):
            continue

        misses.append({
            "index":    i + 1,
            "anchor":   anchor[:30] + ("…" if len(anchor) > 30 else ""),
            "new_text": new_text[:40] + ("…" if len(new_text) > 40 else ""),
            "reason":   "在输出文档的插入标记中未找到对应新文本",
        })

    return misses


# ── 生成校验报告 ──────────────────────────────────────────────────────────────

def build_report(inp: dict, actual_comments: int, actual_tc: dict,
                 missed_tracked: list, missed_inserts: list,
                 integrity_issues: list) -> tuple:
    """
    构建文本报告，返回 (report_text, passed)。
    passed=True 表示全部校验通过。
    """
    exp_comments = inp["expected_comment_count"]
    exp_tc       = inp["expected_tc_count"]
    exp_ins      = inp["expected_insert_count"]

    lines = []
    lines.append("=" * 60)
    lines.append("  mode_a_verifier — 批注/修订二次校验报告")
    lines.append("=" * 60)
    lines.append("")

    # ── 汇总表 ──
    lines.append("【汇总】")
    lines.append(f"  期望批注数（comments）：{exp_comments}")
    lines.append(f"  实际批注数（comments）：{actual_comments}")
    comment_ok = actual_comments >= exp_comments
    lines.append(f"  批注校验：{'✅ 通过' if comment_ok else f'❌ 缺失 {exp_comments - actual_comments} 条'}")
    lines.append("")

    lines.append(f"  期望修订标记（tracked_changes）：{exp_tc} 条")
    lines.append(f"  实际 w:del 节点数：{actual_tc['del']}")
    lines.append(f"  实际 w:ins 节点数：{actual_tc['ins']}")
    tc_ok = len(missed_tracked) == 0
    lines.append(f"  修订文本校验：{'✅ 全部命中' if tc_ok else f'❌ {len(missed_tracked)} 条未命中'}")
    lines.append("")

    lines.append(f"  期望插入段落（insert_paragraphs）：{exp_ins} 条")
    ins_ok = len(missed_inserts) == 0
    lines.append(f"  插入段落校验：{'✅ 全部命中' if ins_ok else f'❌ {len(missed_inserts)} 条未命中'}")
    lines.append("")

    integrity_ok = len(integrity_issues) == 0
    passed = comment_ok and tc_ok and ins_ok and integrity_ok

    if not integrity_ok:
        lines.append("─" * 60)
        lines.append("【文档完整性校验】❌ 未通过（文件可能在 Word 中无法打开）")
        for issue in integrity_issues:
            lines.append(f"  - {issue}")
        lines.append("  可能原因：Agent 用 Read/cat 读取了 .docx 并写入 JSON，或未使用 mode_a_annotator.py。")
        lines.append("  建议：重新用脚本生成；old_text/keyword 仅填原文 10-20 字片段。")
        lines.append("")

    # ── 批注缺失详情 ──
    if not comment_ok:
        lines.append("─" * 60)
        lines.append(f"【批注缺失详情】实际批注数 {actual_comments} < 期望 {exp_comments}")
        lines.append("  可能原因：部分关键字未在原文中匹配，对应批注被静默跳过。")
        lines.append("  建议：检查 mode_a_input.json 中 old_text / keyword 字段，")
        lines.append("        确保与合同原文精确对应（短片段、单段落、含条款编号）。")
        lines.append("")

    # ── 修订文本未命中详情 ──
    if not tc_ok:
        lines.append("─" * 60)
        lines.append("【修订标记未命中详情】以下条目的 old_text 未在输出文档的删除标记中找到：")
        lines.append("")
        for m in missed_tracked:
            lines.append(f"  条目 #{m['index']}：{m['old_text']}")
            lines.append(f"    → {m['reason']}")
        lines.append("")
        lines.append("  建议：回到合同原文，重新复制对应段落的精确文本填入 old_text，")
        lines.append("        优先使用「条款编号 + 前 10-20 字」格式。")
        lines.append("")

    # ── 插入段落未命中详情 ──
    if not ins_ok:
        lines.append("─" * 60)
        lines.append("【插入段落未命中详情】以下条目的 new_text 未在输出文档的插入标记中找到：")
        lines.append("")
        for m in missed_inserts:
            lines.append(f"  条目 #{m['index']}  锚点：{m['anchor']}")
            lines.append(f"    new_text 前段：{m['new_text']}")
            lines.append(f"    → {m['reason']}")
        lines.append("")
        lines.append("  建议：检查 anchor_keyword 是否与合同原文中某段落精确匹配，")
        lines.append("        并确认 new_text 不为空。")
        lines.append("")

    # ── 结论 ──
    lines.append("=" * 60)
    if passed:
        lines.append("  ✅ 校验通过：所有批注与修订标记均已成功嵌入。")
    else:
        lines.append("  ❌ 校验未通过：存在批注或修订标记缺失，详见上方报告。")
        lines.append("  建议修正后重新执行 mode_a_annotator.py，再次运行本校验。")
        lines.append("  若修正 2 轮后仍不通过，按阶段五规则降级为模式 B。")
    lines.append("=" * 60)

    return "\n".join(lines), passed


# ── 主入口 ────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) != 3:
        print("用法：python mode_a_verifier.py <input_json> <output_docx>")
        print("示例：python mode_a_verifier.py mode_a_input.json 合同_原文批注版.docx")
        sys.exit(2)

    json_path = sys.argv[1]
    docx_path = sys.argv[2]

    # 1. 加载输入 JSON
    try:
        inp = load_input(json_path)
    except Exception as e:
        print(f"[ERROR] 无法读取输入 JSON：{e}")
        sys.exit(2)

    # 2. 加载输出 DOCX
    try:
        docx = load_docx(docx_path)
    except Exception as e:
        print(f"[ERROR] 无法读取输出 DOCX：{e}")
        sys.exit(2)

    with zipfile.ZipFile(docx_path, "r") as z:
        raw_doc_xml = z.read("word/document.xml") if "word/document.xml" in z.namelist() else b""
    integrity_issues = check_document_integrity(raw_doc_xml)

    # 3. 统计实际批注数
    actual_comments = count_actual_comments(docx["comments_tree"])

    # 4. 统计实际修订节点
    actual_tc = count_actual_tracked_changes(docx["doc_tree"])

    # 5. 逐条校验 tracked_changes
    missed_tracked = verify_tracked_items(docx["doc_tree"], inp["tracked"])

    # 6. 逐条校验 insert_paragraphs
    missed_inserts = verify_insert_items(docx["doc_tree"], inp["inserts"])

    # 7. 生成报告
    report, passed = build_report(inp, actual_comments, actual_tc,
                                  missed_tracked, missed_inserts,
                                  integrity_issues)
    print(report)

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
