#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
formal_checker.py — 形式审查脚本(LLM 前置预处理)

目的
----
把"纯正则就能判定"的形式审查项,从 LLM 工作流里前移到 pipeline prepare 阶段。
LLM 不再需要逐段眼睛扫描"哪里留空、哪里序号断了",而是基于本脚本输出的
formal_report.json 直接拿到候选证据(段落号 + 命中片段),只做最终的语义判定。

为什么不让脚本"做完判断"?
- 形式审查是"线索发现",不是"结论生成"。
- 比如"金额一致性":脚本能找到合同里出现过的所有金额,但是否构成不一致(可能是
  分项金额相加 = 总额),仍需 LLM 结合上下文判断。
- 因此脚本只输出 candidates(候选清单 + 证据),LLM 拿到后做语义裁决。

检查项(Layer 1 形式审查)
------------------------
1. **占位符留空** — 搜索 ____/【】/[xxx]/{xxx}/TODO/XX/待定/null/None 等占位
2. **序号不连续** — 检测形如"第N条/(N)/N、"的序号是否跳号或重复
3. **日期格式异常** — 同一份合同里日期格式混用(YYYY-MM-DD vs YYYY 年 MM 月)
4. **金额表述不一致** — 阿拉伯数字与中文大写不一致;金额数字在同位置出现差异
5. **标的清单空缺** — "标的"/"产品清单"/"服务范围"等条款下未出现枚举项

输入
----
clean_text.json(由 preprocess_contract.py 输出),paragraphs[].text 是接受
修订后的可见文本。

输出
----
formal_report.json(供 LLM 在 Step 2 形式审查阶段读取):
{
  "version": "18.6",
  "input": "clean_text.json",
  "summary": {
    "placeholders_found": 3,
    "numbering_anomalies": 1,
    "date_format_mixes": 0,
    "amount_inconsistencies": 2,
    "subject_list_missing": 0,
    "total_candidates": 6
  },
  "candidates": [
    {
      "check_id": "FC-1-placeholder",
      "level": "P2",
      "paragraph_idx": 12,
      "evidence": "甲方应在合同签订后____个工作日内付款",
      "match": "____",
      "needs_llm_judge": true,
      "hint": "该处可能为应填写的工作日数,未填写"
    },
    ...
  ],
  "notes": "candidates 的 needs_llm_judge=true 表示脚本只是发现线索,LLM 必须做最终判定"
}

降级路径
--------
- clean_text.json 不存在 → exit 2(LLM 收到信号后切回 路径,自己读 docx 做形式审查)
- 解析异常 → exit 3,formal_report.json 含 "is_error": true,LLM 同样降级
- 任意正则崩溃 → 该检查项标 skipped 并继续,不影响其他检查项
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


# ----------------------- 检查器(每个返回 candidates 列表) -----------------------

PLACEHOLDER_PATTERNS = [
    # 下划线占位
    (re.compile(r"_{3,}"), "underscore_blank"),
    # 中文【】内为空或纯数字"X"占位:【】、【XX】、【XX%】、【0】、【x】
    (re.compile(r"【\s*[xX]+\s*】"), "cjk_brackets_x"),
    (re.compile(r"【\s*】"), "cjk_brackets_empty"),
    # 半角方括号占位
    (re.compile(r"\[\s*(?:xx+|XX+|TBD|tbd|TODO|todo|待定|待补充)\s*\]"), "square_brackets_placeholder"),
    # 大括号
    (re.compile(r"\{\s*(?:xx+|XX+|placeholder|TODO|TBD)\s*\}"), "curly_brackets_placeholder"),
    # 显式词
    (re.compile(r"(?:TBD|TODO|TBA|N\.?A\.?|待定|待补充|待填写|留空)", re.IGNORECASE), "explicit_word"),
]


def check_placeholder(paragraphs):
    out = []
    for p in paragraphs:
        text = p.get("text", "")
        if not text or len(text) < 2:
            continue
        for rx, kind in PLACEHOLDER_PATTERNS:
            for m in rx.finditer(text):
                # 排除明显误伤:大段下划线可能是签名线
                if kind == "underscore_blank" and len(m.group(0)) > 30:
                    continue
                out.append({
                    "check_id": "FC-1-placeholder",
                    "level": "P2",
                    "paragraph_idx": p.get("idx"),
                    "evidence": text[:200],
                    "match": m.group(0),
                    "kind": kind,
                    "needs_llm_judge": True,
                    "hint": "占位符疑似未填写,请 LLM 判断是否为应填写却留空(签名线、流程图等可忽略)",
                })
    return out


# 序号不连续:检测"第N条"序列与"(N)"列表的跳号
NUMBERED_CLAUSE_RX = re.compile(r"第\s*([一二三四五六七八九十百零壹贰叁肆伍陆柒捌玖拾佰0-9]+)\s*条")
PAREN_LIST_RX = re.compile(r"^\s*[(（]\s*(\d{1,3})\s*[)）]")

CN_NUM_MAP = {
    "零": 0, "〇": 0,
    "一": 1, "壹": 1, "二": 2, "贰": 2, "三": 3, "叁": 3,
    "四": 4, "肆": 4, "五": 5, "伍": 5, "六": 6, "陆": 6,
    "七": 7, "柒": 7, "八": 8, "捌": 8, "九": 9, "玖": 9,
    "十": 10, "拾": 10, "百": 100, "佰": 100,
}


def parse_chinese_number(s):
    """简陋的中文数字解析:支持 1-99,够用即可。失败返回 None。"""
    if not s:
        return None
    if s.isdigit():
        try:
            return int(s)
        except ValueError:
            return None
    s = s.strip()
    # 形如"二十"、"二十三"
    if "十" in s or "拾" in s:
        parts = re.split(r"[十拾]", s, maxsplit=1)
        left = parts[0].strip()
        right = parts[1].strip() if len(parts) > 1 else ""
        tens = CN_NUM_MAP.get(left, 1) if left else 1
        ones = CN_NUM_MAP.get(right, 0) if right else 0
        return tens * 10 + ones
    return CN_NUM_MAP.get(s)


def check_numbering(paragraphs):
    """检测条款序号是否跳号。"""
    out = []

    # 第N条
    clause_seq = []  # [(idx, n, text, raw)]
    for p in paragraphs:
        text = p.get("text", "")
        for m in NUMBERED_CLAUSE_RX.finditer(text):
            n = parse_chinese_number(m.group(1))
            if n is not None:
                clause_seq.append((p.get("idx"), n, text[:120], m.group(0)))

    if len(clause_seq) >= 2:
        for i in range(1, len(clause_seq)):
            prev_idx, prev_n, _, prev_raw = clause_seq[i - 1]
            cur_idx, cur_n, cur_text, cur_raw = clause_seq[i]
            if cur_n == prev_n:
                out.append({
                    "check_id": "FC-2-numbering",
                    "level": "P2",
                    "paragraph_idx": cur_idx,
                    "evidence": cur_text,
                    "match": cur_raw,
                    "kind": "duplicate_clause_number",
                    "needs_llm_judge": True,
                    "hint": f"'{cur_raw}' 与上一条款序号重复(上次出现于段落 {prev_idx})",
                })
            elif cur_n != prev_n + 1:
                # 允许章节回跳(如附件单独编号),只在跳号 > 1 时报
                if 0 < cur_n - prev_n != 1:
                    out.append({
                        "check_id": "FC-2-numbering",
                        "level": "P2",
                        "paragraph_idx": cur_idx,
                        "evidence": cur_text,
                        "match": cur_raw,
                        "kind": "numbering_skip",
                        "needs_llm_judge": True,
                        "hint": f"条款序号从 第{prev_n}条 跳到 {cur_raw}(可能漏写或顺序错乱)",
                    })
    return out


# 日期格式
DATE_PATTERNS = {
    "iso_dash": re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}\b"),
    "iso_slash": re.compile(r"\b\d{4}/\d{1,2}/\d{1,2}\b"),
    "iso_dot": re.compile(r"\b\d{4}\.\d{1,2}\.\d{1,2}\b"),
    "cjk_year": re.compile(r"\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日"),
}


def check_date_formats(paragraphs):
    """如果同一份合同里出现 ≥2 种日期格式,提示一致性问题。"""
    occurrences = {k: [] for k in DATE_PATTERNS}
    for p in paragraphs:
        text = p.get("text", "")
        for kind, rx in DATE_PATTERNS.items():
            for m in rx.finditer(text):
                occurrences[kind].append({
                    "paragraph_idx": p.get("idx"),
                    "evidence": text[:120],
                    "match": m.group(0),
                })
    used_kinds = [k for k, lst in occurrences.items() if lst]
    out = []
    if len(used_kinds) >= 2:
        # 只取首个不一致的样例,避免噪音
        primary = max(used_kinds, key=lambda k: len(occurrences[k]))
        for kind in used_kinds:
            if kind == primary:
                continue
            sample = occurrences[kind][0]
            out.append({
                "check_id": "FC-3-date-format",
                "level": "P3",
                "paragraph_idx": sample["paragraph_idx"],
                "evidence": sample["evidence"],
                "match": sample["match"],
                "kind": f"date_format_mix_{primary}_vs_{kind}",
                "needs_llm_judge": True,
                "hint": f"全文主用 '{primary}' 格式,此处出现 '{kind}' 格式;LLM 判断是否为引用文献等合理例外",
            })
    return out


# 金额不一致:粗筛"数字 + 元" + "中文大写元"组合,看是否打架
AMOUNT_RX_DIGITS = re.compile(r"(?:RMB|人民币|¥|￥)?\s*([\d,]+(?:\.\d+)?)\s*(元|万元|万|亿)")
AMOUNT_RX_CHINESE = re.compile(r"((?:零|壹|贰|叁|肆|伍|陆|柒|捌|玖|拾|佰|仟|万|亿|圆|元|角|分|整){2,})")


def check_amounts_quick(paragraphs):
    """提供"金额疑似不一致"线索,真正的相加校验由 verify_amounts.py 做。"""
    digits = []
    chinese = []
    for p in paragraphs:
        text = p.get("text", "")
        for m in AMOUNT_RX_DIGITS.finditer(text):
            digits.append({
                "paragraph_idx": p.get("idx"),
                "evidence": text[:120],
                "match": m.group(0),
                "value_str": m.group(1),
                "unit": m.group(2),
            })
        for m in AMOUNT_RX_CHINESE.finditer(text):
            chinese.append({
                "paragraph_idx": p.get("idx"),
                "evidence": text[:120],
                "match": m.group(0),
            })
    out = []
    # 仅当大写中文金额出现 ≥1 次,但同段落或前后段落没有相邻数字金额对照,提示 LLM 复核
    if chinese and digits:
        # 配对:同段落或相邻段落 ±1 的中文 + 数字
        for c in chinese:
            c_idx = c["paragraph_idx"]
            nearby = [d for d in digits if abs((d["paragraph_idx"] or 0) - (c_idx or 0)) <= 1]
            if not nearby:
                out.append({
                    "check_id": "FC-4-amount",
                    "level": "P2",
                    "paragraph_idx": c_idx,
                    "evidence": c["evidence"],
                    "match": c["match"],
                    "kind": "chinese_amount_no_digit_pair",
                    "needs_llm_judge": True,
                    "hint": "中文大写金额未在邻近段落找到对应数字金额,LLM 判断是否需要补充阿拉伯数字对照",
                })
    return out


SUBJECT_TERMS_RX = re.compile(r"(标的|产品清单|服务范围|交付物|工作内容|采购清单|授权范围)")


def check_subject_list(paragraphs):
    """简陋探测:'标的/产品清单/...' 出现后的接下来 5 段内是否有枚举(包含数字开头或破折号)。"""
    out = []
    paragraphs_list = list(paragraphs)
    for i, p in enumerate(paragraphs_list):
        text = p.get("text", "")
        if not text:
            continue
        m = SUBJECT_TERMS_RX.search(text)
        if not m:
            continue
        window = paragraphs_list[i + 1: i + 6]
        has_list = any(
            re.search(r"^\s*(?:\d+[.、)]|[(（]\d+[)）]|[-—•])", w.get("text", ""))
            for w in window
        )
        if not has_list:
            out.append({
                "check_id": "FC-5-subject-list",
                "level": "P1",
                "paragraph_idx": p.get("idx"),
                "evidence": text[:200],
                "match": m.group(0),
                "kind": "subject_term_without_enumeration",
                "needs_llm_judge": True,
                "hint": "提到'标的/产品清单/服务范围'等核心条款但 5 段内未出现枚举,LLM 判断是否漏列(可能在附件)",
            })
    return out


# ----------------------- 主流程 -----------------------

def run_all(paragraphs):
    summary = {
        "placeholders_found": 0,
        "numbering_anomalies": 0,
        "date_format_mixes": 0,
        "amount_inconsistencies": 0,
        "subject_list_missing": 0,
        "total_candidates": 0,
    }
    candidates = []
    skipped = []

    runners = [
        ("placeholder", check_placeholder, "placeholders_found"),
        ("numbering", check_numbering, "numbering_anomalies"),
        ("date_format", check_date_formats, "date_format_mixes"),
        ("amount", check_amounts_quick, "amount_inconsistencies"),
        ("subject_list", check_subject_list, "subject_list_missing"),
    ]
    for name, func, key in runners:
        try:
            r = func(paragraphs)
            candidates.extend(r)
            summary[key] = len(r)
        except Exception as e:
            skipped.append({"check": name, "error": str(e)})
    summary["total_candidates"] = len(candidates)
    return summary, candidates, skipped


def main():
    ap = argparse.ArgumentParser(description="形式审查脚本(只给 LLM 候选证据,不下结论)")
    ap.add_argument("clean_text", nargs="?", default="clean_text.json",
                    help="preprocess_contract.py 的输出;默认 ./clean_text.json")
    ap.add_argument("--output", default="formal_report.json",
                    help="输出 JSON 文件,默认 ./formal_report.json")
    args = ap.parse_args()

    if not os.path.exists(args.clean_text):
        err = {"is_error": True, "error": f"clean_text.json not found: {args.clean_text}"}
        print(json.dumps(err, ensure_ascii=False), file=sys.stderr)
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(err, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
        return 2

    try:
        with open(args.clean_text, encoding="utf-8") as f:
            clean = json.load(f)
        paragraphs = clean.get("paragraphs", [])
    except (json.JSONDecodeError, OSError) as e:
        err = {"is_error": True, "error": f"failed to read clean_text: {e}"}
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(err, f, ensure_ascii=False, indent=2)
        print(json.dumps(err, ensure_ascii=False), file=sys.stderr)
        return 3

    summary, candidates, skipped = run_all(paragraphs)
    report = {
        "version": "18.6",
        "input": str(Path(args.clean_text).resolve()),
        "summary": summary,
        "candidates": candidates,
        "skipped_checks": skipped,
        "notes": (
            "candidates[].needs_llm_judge=true 表示脚本只发现线索,LLM 必须基于 evidence "
            "做最终判定。skipped_checks 为本轮跑挂的检查器,LLM 在该维度需要降级到人工形式审查。"
        ),
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    # stdout 透出摘要,便于 pipeline 日志
    print(json.dumps({"is_error": False, "summary": summary, "output": args.output},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
