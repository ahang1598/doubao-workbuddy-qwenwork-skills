#!/usr/bin/env python3
"""
风险清单解析脚本

将法大大审查引擎下载的 Excel 风险清单解析为结构化 JSON，
供 Claude 本地生成修订版合同、带标注修订版合同和多角色评审报告使用。
"""

import json
import os
import sys


# 常见列名关键字映射（模糊匹配，顺序决定优先级）
_COLUMN_KEYWORDS = {
    "clause":     ["条款", "条文", "章节", "clause", "article", "section"],
    "issue":      ["风险项", "风险点", "问题", "issue", "risk item", "问题描述", "风险描述"],
    "risk_level": ["风险等级", "等级", "级别", "风险级别", "level", "severity", "risk level"],
    "suggestion": ["建议", "修改建议", "处理建议", "suggestion", "recommendation", "改法"],
}


def _fuzzy_match_columns(headers: list) -> dict:
    """将表头列名映射到标准字段名，返回 {标准字段: 列索引}。"""
    mapping = {}
    headers_lower = [str(h).lower().strip() for h in headers]
    for field, keywords in _COLUMN_KEYWORDS.items():
        for idx, h in enumerate(headers_lower):
            if any(kw.lower() in h for kw in keywords):
                if field not in mapping:
                    mapping[field] = idx
                    break
    return mapping


def _parse_with_openpyxl(file_path: str) -> dict:
    import openpyxl
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return {"success": False, "error": "Excel 文件为空"}

    # 第一行作为表头
    headers = [str(c) if c is not None else "" for c in rows[0]]
    col_map = _fuzzy_match_columns(headers)

    items = []
    counts = {"高": 0, "中": 0, "低": 0, "其他": 0}

    for i, row in enumerate(rows[1:], start=1):
        if all(c is None or str(c).strip() == "" for c in row):
            continue

        def get(field):
            idx = col_map.get(field)
            if idx is not None and idx < len(row):
                val = row[idx]
                return str(val).strip() if val is not None else ""
            return ""

        risk_level = get("risk_level") or "未知"
        # 标准化风险等级
        if "高" in risk_level or "high" in risk_level.lower():
            risk_level = "高"
        elif "中" in risk_level or "medium" in risk_level.lower() or "mid" in risk_level.lower():
            risk_level = "中"
        elif "低" in risk_level or "low" in risk_level.lower():
            risk_level = "低"
        else:
            counts["其他"] += 1

        if risk_level in counts:
            counts[risk_level] += 1

        items.append({
            "index": i,
            "clause": get("clause"),
            "issue": get("issue"),
            "risk_level": risk_level,
            "suggestion": get("suggestion"),
        })

    wb.close()

    return {
        "success": True,
        "data": {
            "total": len(items),
            "high": counts["高"],
            "medium": counts["中"],
            "low": counts["低"],
            "items": items,
        }
    }


def _parse_with_csv(file_path: str) -> dict:
    """当文件是 CSV 时的解析路径，或 openpyxl 不可用时的降级路径（先尝试转换）。"""
    import csv
    try:
        with open(file_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)
    except UnicodeDecodeError:
        with open(file_path, newline="", encoding="gbk", errors="replace") as f:
            reader = csv.reader(f)
            rows = list(reader)

    if not rows:
        return {"success": False, "error": "CSV 文件为空"}

    headers = rows[0]
    col_map = _fuzzy_match_columns(headers)

    items = []
    counts = {"高": 0, "中": 0, "低": 0, "其他": 0}

    for i, row in enumerate(rows[1:], start=1):
        if all(c.strip() == "" for c in row):
            continue

        def get(field):
            idx = col_map.get(field)
            if idx is not None and idx < len(row):
                return row[idx].strip()
            return ""

        risk_level = get("risk_level") or "未知"
        if "高" in risk_level or "high" in risk_level.lower():
            risk_level = "高"
        elif "中" in risk_level or "medium" in risk_level.lower() or "mid" in risk_level.lower():
            risk_level = "中"
        elif "低" in risk_level or "low" in risk_level.lower():
            risk_level = "低"
        else:
            counts["其他"] += 1

        if risk_level in counts:
            counts[risk_level] += 1

        items.append({
            "index": i,
            "clause": get("clause"),
            "issue": get("issue"),
            "risk_level": risk_level,
            "suggestion": get("suggestion"),
        })

    return {
        "success": True,
        "data": {
            "total": len(items),
            "high": counts["高"],
            "medium": counts["中"],
            "low": counts["低"],
            "items": items,
        }
    }


def extract_risk_data(file_path: str) -> dict:
    """
    解析风险清单文件（xlsx 或 csv），返回结构化 JSON。

    Args:
        file_path: 风险清单文件路径（.xlsx 或 .csv）

    Returns:
        dict: {
            "success": True/False,
            "data": {
                "total": int,
                "high": int,
                "medium": int,
                "low": int,
                "items": [{"index", "clause", "issue", "risk_level", "suggestion"}, ...]
            }
        }
    """
    if not os.path.exists(file_path):
        return {"success": False, "error": f"文件不存在: {file_path}"}

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".csv":
        return _parse_with_csv(file_path)

    # xlsx / xls：优先 openpyxl
    try:
        import openpyxl  # noqa: F401
        return _parse_with_openpyxl(file_path)
    except ImportError:
        return {
            "success": False,
            "error": (
                "缺少 openpyxl 库，无法解析 Excel 文件。\n"
                "请执行：pip install openpyxl\n"
                "安装后重新运行本脚本。\n"
                "如果无法安装，可将 Excel 文件另存为 CSV 格式后重新运行。"
            ),
            "error_type": "missing_dependency",
        }
    except Exception as e:
        return {"success": False, "error": f"解析 Excel 失败: {str(e)}"}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "请提供风险清单文件路径",
            "usage": "python extract_risk_data.py <风险清单文件路径(.xlsx 或 .csv)>"
        }, ensure_ascii=False))
        sys.exit(1)

    file_path = sys.argv[1].strip()
    if not file_path:
        print(json.dumps({"success": False, "error": "文件路径不能为空"}, ensure_ascii=False))
        sys.exit(1)

    result = extract_risk_data(file_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
