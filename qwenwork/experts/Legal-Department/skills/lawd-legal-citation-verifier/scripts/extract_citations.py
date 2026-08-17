#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""extract_citations.py — 从中文法律文本中提取法条引用与案号。

提取两类引用：
  1. 法条引用：形如《某某法》第X条（支持中文数字条号如"第五百七十七条"
     与阿拉伯数字条号如"第47条"，可带"之X/款/项"后缀）
  2. 案号：形如 (2023)京01民终5678号（支持全角/半角括号）

用法：
  python3 extract_citations.py --text "根据《民法典》第五百七十七条……"
  python3 extract_citations.py --file 文书.txt

输出 JSON 到 stdout：
  {
    "law_citations": [
      {"law_name": "中华人民共和国民法典", "article_no": "第五百七十七条", "snippet": "……"}
    ],
    "case_citations": [
      {"case_no": "(2023)京01民终5678号"}
    ]
  }

仅依赖 python3 标准库（re / json / argparse）。
"""

import argparse
import json
import re
import sys

# ---------------------------------------------------------------------------
# 正则定义
# ---------------------------------------------------------------------------

# 数字字符集：中文数字 + 半角/全角阿拉伯数字
_CN_NUM = "零〇一二三四五六七八九十百千"
_NUM = "[" + _CN_NUM + "0-9０-９]"

# 条号：第X条，可带"之X"、"第X款"、"第(X)项"后缀
_ARTICLE = (
    "第" + _NUM + "+条"
    "(?:之[" + _CN_NUM + "]+)?"
    "(?:第" + _NUM + "+款)?"
    "(?:第[（(]?" + _NUM + "+[）)]?项)?"
)

# 法条引用：《法规名》第X条（书名号与条号之间允许少量空白）
LAW_CITATION_RE = re.compile("(《[^《》\\n]{1,80}》)\\s*(" + _ARTICLE + ")")

# 案号：(2023)京01民终5678号 / （2021）最高法民申1234号 等
# 结构 = 括号内4位年份 + 法院代字/类型代字（汉字、字母、数字混合）+ 序号 + 号
CASE_NO_RE = re.compile(
    "[（(〔［\\[]\\s*\\d{4}\\s*[）)〕］\\]]"
    "[\\u4e00-\\u9fa5A-Za-z0-9]{1,12}?\\d+号"
)

# 片段截断的句末标点
_SENTENCE_END_RE = re.compile("[。；！？!?;\\n]")

# ---------------------------------------------------------------------------
# 提取逻辑
# ---------------------------------------------------------------------------


def _snippet_after(text, end, max_len=120):
    """取引用之后的原文片段：去掉起始标点，截到第一个句末标点（或 max_len）。"""
    seg = text[end:end + 200]
    seg = seg.lstrip("，,、：: 　\t")
    m = _SENTENCE_END_RE.search(seg)
    if m:
        seg = seg[:m.start() + 1]
    return seg.strip()[:max_len]


def _normalize_case_no(raw):
    """案号归一化：全角括号转半角、去空白，便于去重与比对。"""
    s = raw.strip()
    for ch in "（〔［【":
        s = s.replace(ch, "(")
    for ch in "）〕］】":
        s = s.replace(ch, ")")
    return re.sub(r"\s+", "", s)


def extract(text):
    """从文本中提取法条引用与案号，返回 dict。"""
    law_citations = []
    seen_laws = set()
    for m in LAW_CITATION_RE.finditer(text):
        law_name = m.group(1)[1:-1]  # 去掉书名号
        article_no = m.group(2)
        key = (law_name, article_no)
        if key in seen_laws:
            continue
        seen_laws.add(key)
        law_citations.append({
            "law_name": law_name,
            "article_no": article_no,
            "snippet": _snippet_after(text, m.end()),
        })

    case_citations = []
    seen_cases = set()
    for m in CASE_NO_RE.finditer(text):
        case_no = _normalize_case_no(m.group(0))
        if case_no in seen_cases:
            continue
        seen_cases.add(case_no)
        case_citations.append({"case_no": case_no})

    return {
        "law_citations": law_citations,
        "case_citations": case_citations,
    }


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description=(
            "从中文法律文本中提取法条引用（《法规名》第X条，支持中文数字条号）"
            "与案号（如 (2023)京01民终5678号），输出 JSON 到 stdout。"
        ),
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="待提取的法律文本（直接传入字符串）")
    group.add_argument("--file", help="包含法律文本的文件路径（UTF-8 编码）")
    args = parser.parse_args()

    if args.text is not None:
        text = args.text
    else:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            print("无法读取文件: {}".format(e), file=sys.stderr)
            sys.exit(1)

    result = extract(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
