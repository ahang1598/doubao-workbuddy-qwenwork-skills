#!/usr/bin/env python3
"""validate_mermaid.py - Markdown 文件中 Mermaid 代码块的启发式语法校验器。

检查项（ERROR 必须修复，WARN 建议修复）：
  1. 代码块未闭合
  2. 首行不是已知 Mermaid 图类型
  3. 空代码块
  4. 括号 () [] {} 不配平（忽略引号与注释内内容）
  5. flowchart/graph 中 subgraph 与 end 数量不匹配
  6. 节点 label 含特殊字符但未加双引号
  7. 边标签竖线 | 不配平
  8. 使用了未定义的 classDef 类（WARN）
  9. 同一节点 ID 被赋予不同 label（WARN）

用法：
  python validate_mermaid.py <文件.md> [更多文件.md ...]
退出码：存在任一 ERROR 时为 1，否则为 0。
"""

import re
import sys

KNOWN_DIAGRAMS = (
    "flowchart", "graph", "timeline", "sequenceDiagram", "classDiagram",
    "stateDiagram", "stateDiagram-v2", "erDiagram", "gantt", "pie",
    "journey", "mindmap", "gitGraph", "quadrantChart", "xychart-beta",
    "block-beta", "sankey-beta", "requirementDiagram", "C4Context",
)

SPECIAL_RE = re.compile(r"[()\[\]{}:;&#|]")
NODE_DEF_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(\[|\(|\{)([^\]\)\{\}]*)")
EDGE_RE = re.compile(r"(-+>|=+>|-+\.-+>|--+>?|==+>?)")
CLASSDEF_RE = re.compile(r"^\s*classDef\s+([A-Za-z_][A-Za-z0-9_]*)")
CLASS_STMT_RE = re.compile(r"^\s*class\s+\S+\s+([A-Za-z_][A-Za-z0-9_]*)\s*$")
INLINE_CLASS_RE = re.compile(r":::([A-Za-z_][A-Za-z0-9_]*)")


def strip_quoted(text):
    """移除双引号包裹的内容与 %% 注释，避免误报。"""
    text = re.sub(r'"[^"\n]*"', '""', text)
    text = re.sub(r"%%.*$", "", text)
    return text


def extract_blocks(lines):
    """返回 (blocks, unclosed)。blocks: [(fence行号, [(行号, 原文), ...]), ...]"""
    blocks = []
    in_block = False
    start = 0
    buf = []
    unclosed = False
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if not in_block and s.lower().startswith("```mermaid"):
            in_block, start, buf = True, i, []
        elif in_block and s == "```":
            blocks.append((start, buf))
            in_block = False
        elif in_block:
            buf.append((i, line))
    if in_block:
        blocks.append((start, buf))
        unclosed = True
    return blocks, unclosed


def check_block(start_line, rows):
    """对单个 mermaid 块执行全部检查，返回 (errors, warnings) 两类问题列表。"""
    errors, warnings = [], []
    content_rows = [(n, l) for n, l in rows if l.strip() and not l.strip().startswith("%%")]

    if not content_rows:
        errors.append((start_line, "空的 mermaid 代码块"))
        return errors, warnings

    first_no, first_line = content_rows[0]
    first_token = first_line.strip().split()[0]
    if first_token not in KNOWN_DIAGRAMS:
        errors.append((first_no, "首行不是已知 Mermaid 图类型: '%s'" % first_token))

    is_flow = first_token in ("flowchart", "graph")

    # 括号配平（整块累计，忽略引号/注释）
    depth = {"(": 0, "[": 0, "{": 0}
    pairs = {")": "(", "]": "[", "}": "{"}
    for no, line in rows:
        for ch in strip_quoted(line):
            if ch in depth:
                depth[ch] += 1
            elif ch in pairs:
                depth[pairs[ch]] -= 1
                if depth[pairs[ch]] < 0:
                    errors.append((no, "括号不配平: 多余的 '%s'" % ch))
                    depth[pairs[ch]] = 0
    for ch, d in depth.items():
        if d > 0:
            errors.append((start_line, "括号不配平: '%s' 缺少 %d 个闭合" % (ch, d)))

    # subgraph / end 配平
    if is_flow:
        sub_open = [n for n, l in rows if re.match(r"^\s*subgraph\b", l)]
        sub_close = [n for n, l in rows if re.match(r"^\s*end\s*$", l)]
        if len(sub_open) != len(sub_close):
            errors.append((start_line, "subgraph(%d) 与 end(%d) 数量不匹配"
                           % (len(sub_open), len(sub_close))))

    # 节点 label 特殊字符未加引号
    for no, line in rows:
        if ":::" in line or "classDef" in line or line.strip().startswith("class "):
            continue
        for m in NODE_DEF_RE.finditer(line):
            label = m.group(3)
            if not label:
                continue
            if label.strip().startswith('"'):
                continue
            if SPECIAL_RE.search(label):
                errors.append((no, "节点 '%s' 的 label 含特殊字符但未加双引号: %s"
                               % (m.group(1), label.strip()[:40])))

    # 边标签竖线配平
    for no, line in rows:
        stripped = strip_quoted(line)
        if EDGE_RE.search(stripped) and stripped.count("|") % 2 != 0:
            errors.append((no, "边标签竖线 | 不配平"))

    # classDef 定义与使用
    if is_flow:
        defined = set()
        used = set()
        for no, line in rows:
            m = CLASSDEF_RE.match(line)
            if m:
                defined.add(m.group(1))
            m = CLASS_STMT_RE.match(line)
            if m:
                for c in m.group(1).split(","):
                    used.add(c.strip())
            for c in INLINE_CLASS_RE.findall(line):
                used.add(c)
        for c in sorted(used - defined):
            warnings.append((start_line, "使用了未定义的 classDef 类: '%s'" % c))

    # 同一节点 ID 多个不同 label
    labels = {}
    for no, line in rows:
        for m in NODE_DEF_RE.finditer(line):
            nid, label = m.group(1), m.group(3).strip()
            if not label:
                continue
            if nid in labels and labels[nid] != label:
                warnings.append((no, "节点 '%s' 被重复定义且 label 不一致" % nid))
            else:
                labels.setdefault(nid, label)

    return errors, warnings


def main(argv):
    if len(argv) < 2:
        print("用法: python validate_mermaid.py <文件.md> [更多文件.md ...]")
        return 2
    total_err = 0
    for path in argv[1:]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().split("\n")
        except OSError as e:
            print("[ERROR] 无法读取 %s: %s" % (path, e))
            total_err += 1
            continue
        blocks, unclosed = extract_blocks(lines)
        print("== %s: 发现 %d 个 mermaid 块 ==" % (path, len(blocks)))
        if not blocks:
            print("  [WARN] 未发现任何 mermaid 代码块")
        if unclosed:
            print("  [ERROR] 行 %d: mermaid 代码块未闭合（缺少 ```）"
                  % (blocks[-1][0] if blocks else 0))
            total_err += 1
        for idx, (start, rows) in enumerate(blocks, 1):
            errs, warns = check_block(start, rows)
            for no, msg in errs:
                print("  [ERROR] 块%d 行%d: %s" % (idx, no, msg))
            for no, msg in warns:
                print("  [WARN ] 块%d 行%d: %s" % (idx, no, msg))
            if not errs and not warns:
                print("  [OK   ] 块%d (起始于行 %d) 通过全部检查" % (idx, start))
            total_err += len(errs)
    print("校验完成: %s" % ("存在错误，请修复后重试" if total_err else "全部通过"))
    return 1 if total_err else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
