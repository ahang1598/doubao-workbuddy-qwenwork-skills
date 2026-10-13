#!/usr/bin/env python3
"""技能ID: contract-nlp-search | 合同智能搜索"""
import json, re
from typing import Dict, Any

def skill_function(input_data):
    query = input_data.get("query", "")
    contracts = input_data.get("contracts", [])
    if not query or not contracts:
        return {"status": "error", "message": "请提供搜索关键词和合同列表"}
    keywords = [w for w in re.findall(r"[\w\u4e00-9fff]+", query) if len(w) > 1]
    results = []
    for c in contracts:
        name = c.get("name", "")
        text = c.get("text", "")
        combined = name + " " + text
        matched = [kw for kw in keywords if kw in combined]
        if matched:
            context = ""
            for kw in matched[:3]:
                idx = combined.find(kw)
                if idx >= 0:
                    start, end = max(0, idx - 30), min(len(combined), idx + 50)
                    context += combined[start:end].replace("\n", " ") + " ... "
            results.append({"合同名称": name, "匹配关键词": matched, "匹配度": len(matched), "上下文": context[:200]})
    results.sort(key=lambda x: x["匹配度"], reverse=True)
    return {"status": "success", "result": {"搜索关键词": query, "结果数量": len(results), "搜索结果": results[:10]}}

if __name__ == "__main__":
    test = {"query": "保密 知识产权", "contracts": [{"name": "NDA-2025", "text": "保密协议，保护商业秘密和知识产权"}, {"name": "采购合同", "text": "采购服务器10台"}]}
    print(json.dumps(skill_function(test), ensure_ascii=False, indent=2))
