#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交叉引用结构层验证脚本 — verify_cross_references.py

用于合同审查 Step 2 Layer 3 §3.4.6 的交叉引用核验（结构层）。
LLM 提取条款索引和交叉引用 → 本脚本执行结构层验证 → LLM 执行语义复核。

本脚本覆盖三层核验中的前两层：
  ① 编号存在性：被引条款编号在索引表中是否存在 → 确定性判断
  ② 标题相关性（初筛）：被引条款标题与引用上下文的关键词重叠度 → 辅助判断
  ③ 语义匹配：需 LLM 语义复核（本脚本仅标记"待语义复核"）

用法:
    python3 verify_cross_references.py --json cross_refs.json

输入 JSON 格式:
{
  "clause_index": [
    {"id": "第1条", "title": "合同标的", "level": 1},
    {"id": "第1.1条", "title": "产品描述", "level": 2},
    {"id": "第2条", "title": "价款与支付", "level": 1},
    {"id": "第2.1条", "title": "付款方式", "level": 2},
    {"id": "第3条", "title": "违约责任", "level": 1}
  ],
  "cross_references": [
    {
      "source_clause": "第5.2条",
      "source_context": "按照第2.1条约定的付款方式执行",
      "target_id": "第2.1条",
      "reference_expression": "第2.1条约定的付款方式"
    },
    {
      "source_clause": "第6条",
      "source_context": "依据第8条的违约责任承担赔偿",
      "target_id": "第8条",
      "reference_expression": "第8条的违约责任"
    },
    {
      "source_clause": "第4.3条",
      "source_context": "定义见第1.1条",
      "target_id": "第1.1条",
      "reference_expression": "定义见第1.1条"
    }
  ]
}

输出: JSON 格式的验证结果。
"""

import argparse
import json
import re
import sys
from typing import Dict, List, Optional, Set, Tuple


def normalize_clause_id(clause_id: str) -> str:
    """
    归一化条款编号，支持多种格式：
    "第1条" / "第1.1条" / "1.1" / "第一条" / "Article 1" 等。
    返回统一格式的编号字符串用于匹配。
    """
    if not clause_id:
        return ""

    text = clause_id.strip()

    # 去除"第"和"条"/"款"/"项"
    text = re.sub(r'^第\s*', '', text)
    text = re.sub(r'\s*[条款项]$', '', text)

    # 中文数字转阿拉伯数字
    cn_map = {'一': '1', '二': '2', '三': '3', '四': '4', '五': '5',
              '六': '6', '七': '7', '八': '8', '九': '9', '十': '10',
              '十一': '11', '十二': '12', '十三': '13', '十四': '14', '十五': '15',
              '十六': '16', '十七': '17', '十八': '18', '十九': '19', '二十': '20'}

    if text in cn_map:
        text = cn_map[text]

    # "Article X" / "Section X"
    text = re.sub(r'(?i)^(article|section|clause)\s*', '', text)

    return text.strip()


def build_clause_map(clause_index: List[Dict]) -> Dict[str, Dict]:
    """
    构建条款编号 → 条款信息的映射。
    同一条款可能有多种写法，全部注册。
    """
    clause_map = {}

    for entry in clause_index:
        raw_id = entry.get("id", "")
        title = entry.get("title", "")
        level = entry.get("level", 1)

        # 原始 ID
        norm = normalize_clause_id(raw_id)
        info = {"raw_id": raw_id, "title": title, "level": level, "norm_id": norm}

        # 注册多种变体
        clause_map[raw_id] = info
        clause_map[norm] = info

        # 如果是 "第X条" 格式，也注册纯数字
        if norm and norm not in clause_map:
            clause_map[norm] = info

    return clause_map


def extract_keywords(text: str) -> Set[str]:
    """从文本中提取关键词（中文 n-gram 2~4字 + 英文词 ≥3字）。"""
    cn_chars = re.sub(r'[^\u4e00-\u9fff]', ' ', text)
    cn_segments = cn_chars.split()

    keywords = set()
    for seg in cn_segments:
        for n in range(2, min(5, len(seg) + 1)):
            for i in range(len(seg) - n + 1):
                keywords.add(seg[i:i + n])
        if 2 <= len(seg) <= 6:
            keywords.add(seg)

    en_words = re.findall(r'[a-zA-Z]{3,}', text)
    keywords.update(w.lower() for w in en_words)
    return keywords


def keyword_overlap_score(text_a: str, text_b: str) -> float:
    """计算两段文本的关键词重叠度。"""
    kw_a = extract_keywords(text_a)
    kw_b = extract_keywords(text_b)

    if not kw_a or not kw_b:
        return 0.0

    overlap = kw_a & kw_b
    # Jaccard 系数
    union = kw_a | kw_b
    return len(overlap) / len(union) if union else 0.0


def verify_single_reference(ref: Dict, clause_map: Dict) -> Dict:
    """验证单条交叉引用。"""
    source_clause = ref.get("source_clause", "未知")
    source_context = ref.get("source_context", "")
    target_id = ref.get("target_id", "")
    ref_expression = ref.get("reference_expression", "")

    result = {
        "source_clause": source_clause,
        "reference_expression": ref_expression,
        "target_id": target_id,
        "checks": {},
    }

    # ① 编号存在性检查
    target_norm = normalize_clause_id(target_id)
    target_info = clause_map.get(target_id) or clause_map.get(target_norm)

    if target_info:
        result["checks"]["existence"] = {
            "status": "pass",
            "matched_id": target_info["raw_id"],
            "matched_title": target_info["title"],
        }

        # ② 标题相关性初筛
        title = target_info.get("title", "")
        if title and source_context:
            overlap = keyword_overlap_score(source_context, title)
            if overlap >= 0.2:
                result["checks"]["title_relevance"] = {
                    "status": "pass",
                    "score": round(overlap, 3),
                    "message": f"标题「{title}」与引用语境关键词重叠度 {overlap:.1%}",
                }
            elif overlap >= 0.05:
                result["checks"]["title_relevance"] = {
                    "status": "needs_review",
                    "score": round(overlap, 3),
                    "message": f"标题「{title}」与引用语境关键词重叠度较低 {overlap:.1%}，需语义复核",
                }
            else:
                result["checks"]["title_relevance"] = {
                    "status": "suspect",
                    "score": round(overlap, 3),
                    "message": f"标题「{title}」与引用语境「{source_context[:30]}」几乎无关联，高度疑似内容不匹配",
                }
        else:
            result["checks"]["title_relevance"] = {
                "status": "skip",
                "message": "标题或上下文缺失，跳过初筛",
            }

        # ③ 语义匹配（标记为待 LLM 复核）
        title_status = result["checks"].get("title_relevance", {}).get("status", "skip")
        if title_status in ("needs_review", "suspect"):
            result["checks"]["semantic_match"] = {
                "status": "pending_llm_review",
                "message": "标题相关性不足，需 LLM 语义复核被引条款实际内容与引用意图是否匹配",
                "review_instruction": (
                    f"请核查：{target_info['raw_id']}「{title}」的实际内容，"
                    f"是否与引用处的语境「{source_context[:50]}」相关。"
                    f"如内容不匹配，标记为 P0。"
                ),
            }
        else:
            result["checks"]["semantic_match"] = {
                "status": "likely_pass",
                "message": "标题相关性通过，语义匹配大概率通过（可选复核）",
            }

    else:
        # 编号不存在
        result["checks"]["existence"] = {
            "status": "fail",
            "message": f"被引条款「{target_id}」在合同中不存在",
            "risk_level": "P0",
        }
        result["checks"]["title_relevance"] = {"status": "skip", "message": "编号不存在，跳过"}
        result["checks"]["semantic_match"] = {"status": "skip", "message": "编号不存在，跳过"}

        # 尝试模糊匹配，给出建议
        suggestions = []
        for key, info in clause_map.items():
            if key == info["raw_id"]:  # 只用原始 ID 避免重复
                sim = keyword_overlap_score(target_id, key)
                if sim > 0 or (target_norm and target_norm in normalize_clause_id(key)):
                    suggestions.append(info["raw_id"])
        if suggestions:
            result["checks"]["existence"]["suggestions"] = suggestions[:3]

    # 综合结论
    statuses = [v.get("status") for v in result["checks"].values()]
    if "fail" in statuses:
        result["conclusion"] = "P0"
        result["conclusion_message"] = "引用目标不存在"
    elif "suspect" in statuses:
        result["conclusion"] = "P0_suspect"
        result["conclusion_message"] = "引用目标存在但标题高度不相关，疑似内容不匹配，需语义复核确认"
    elif "needs_review" in statuses or "pending_llm_review" in statuses:
        result["conclusion"] = "needs_review"
        result["conclusion_message"] = "引用目标存在，标题相关性不确定，需语义复核"
    else:
        result["conclusion"] = "pass"
        result["conclusion_message"] = "引用验证通过"

    return result


def verify_clause_numbering(clause_index: List[Dict]) -> Dict:
    """验证条款编号的连续性和唯一性。"""
    result = {
        "check": "clause_numbering",
        "issues": [],
    }

    # 按 level 分组检查连续性
    level_1_ids = []
    for entry in clause_index:
        if entry.get("level", 1) == 1:
            norm = normalize_clause_id(entry["id"])
            try:
                num = int(norm.split('.')[0])
                level_1_ids.append((num, entry["id"]))
            except (ValueError, IndexError):
                pass

    level_1_ids.sort()

    # 检查唯一性
    seen = {}
    for entry in clause_index:
        raw_id = entry["id"]
        if raw_id in seen:
            result["issues"].append({
                "type": "duplicate",
                "id": raw_id,
                "message": f"条款编号「{raw_id}」重复出现",
                "risk_level": "P3",
            })
        seen[raw_id] = True

    # 检查一级条款连续性
    for i in range(1, len(level_1_ids)):
        prev_num = level_1_ids[i-1][0]
        curr_num = level_1_ids[i][0]
        if curr_num - prev_num > 1:
            for missing in range(prev_num + 1, curr_num):
                result["issues"].append({
                    "type": "gap",
                    "between": [level_1_ids[i-1][1], level_1_ids[i][1]],
                    "missing_number": missing,
                    "message": f"条款编号跳号：第{prev_num}条之后直接是第{curr_num}条，缺少第{missing}条",
                    "risk_level": "P3",
                })

    result["status"] = "fail" if result["issues"] else "pass"
    result["total_clauses"] = len(clause_index)
    return result


def run_all_checks(data: Dict) -> Dict:
    """执行所有交叉引用验证。"""
    clause_index = data.get("clause_index", [])
    cross_references = data.get("cross_references", [])

    clause_map = build_clause_map(clause_index)

    results = {
        "summary": {
            "total_clauses": len(clause_index),
            "total_references": len(cross_references),
        },
        "numbering_check": verify_clause_numbering(clause_index),
        "reference_checks": [],
        "llm_review_queue": [],  # 需要 LLM 语义复核的条目
    }

    # 逐条验证交叉引用
    for ref in cross_references:
        check_result = verify_single_reference(ref, clause_map)
        results["reference_checks"].append(check_result)

        # 收集需要 LLM 复核的条目
        semantic = check_result.get("checks", {}).get("semantic_match", {})
        if semantic.get("status") == "pending_llm_review":
            results["llm_review_queue"].append({
                "source_clause": check_result["source_clause"],
                "target_id": check_result["target_id"],
                "instruction": semantic.get("review_instruction", ""),
            })

    # 汇总统计
    conclusions = [r["conclusion"] for r in results["reference_checks"]]
    results["summary"]["pass"] = conclusions.count("pass")
    results["summary"]["fail_not_exist"] = conclusions.count("P0")
    results["summary"]["suspect_mismatch"] = conclusions.count("P0_suspect")
    results["summary"]["needs_review"] = conclusions.count("needs_review")

    if results["summary"]["fail_not_exist"] > 0:
        results["summary"]["overall"] = "FAIL"
        results["summary"]["message"] = (
            f"{results['summary']['fail_not_exist']} 条引用目标不存在（P0）"
        )
    elif results["summary"]["suspect_mismatch"] > 0:
        results["summary"]["overall"] = "SUSPECT"
        results["summary"]["message"] = (
            f"{results['summary']['suspect_mismatch']} 条疑似内容不匹配，需语义复核"
        )
    elif results["summary"]["needs_review"] > 0:
        results["summary"]["overall"] = "NEEDS_REVIEW"
        results["summary"]["message"] = (
            f"{results['summary']['needs_review']} 条需要语义复核"
        )
    else:
        results["summary"]["overall"] = "PASS"
        results["summary"]["message"] = "所有交叉引用验证通过"

    # LLM 复核指引
    if results["llm_review_queue"]:
        results["llm_review_instructions"] = (
            "以下引用已通过编号存在性验证，但标题相关性不足，"
            "请逐条阅读被引条款的实际内容，判断是否与引用语境的语义一致。"
            "不一致则标记为 P0（内容不匹配）。"
        )

    return results


def main():
    parser = argparse.ArgumentParser(description="合同交叉引用结构层验证脚本")
    parser.add_argument("--json", "-j", required=True, help="输入 JSON 文件路径")
    parser.add_argument("--output", "-o", help="输出结果 JSON 文件路径")
    args = parser.parse_args()

    with open(args.json, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = run_all_checks(data)

    output_json = json.dumps(results, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"[OK] 验证结果已写入 {args.output}")
    else:
        print(output_json)

    overall = results["summary"]["overall"]
    sys.exit(1 if overall == "FAIL" else 0)


if __name__ == "__main__":
    main()
