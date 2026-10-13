#!/usr/bin/env python3
"""
contract_compare.py — 合同对比技能 (Skill #3)
对比两份合同的差异点，标记新增/删除/修改的条款。

用法: python contract_compare.py <contract_a> <contract_b> [--output diff_report.md]
"""

import sys
import re
import difflib
from datetime import datetime
from pathlib import Path
from typing import Optional


def load_contract(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    return path.read_text(encoding="utf-8")


def extract_clauses(text: str) -> dict[str, str]:
    """Extract numbered clauses from contract text."""
    clauses = {}
    # Match patterns like "第一条", "第1条", "一、", "1.", "（一）"
    pattern = r'(第[零一二三四五六七八九十百\d]+条|[一二三四五六七八九十]+、|\d+\.[\s]|（[一二三四五六七八九十\d]+）)'
    
    parts = re.split(pattern, text)
    current_heading = "前言"
    
    for part in parts:
        stripped = part.strip()
        if not stripped:
            continue
        if re.match(pattern, stripped):
            current_heading = stripped
        else:
            if current_heading in clauses:
                clauses[current_heading] += "\n" + stripped
            else:
                clauses[current_heading] = stripped
    
    return clauses


def compare_contracts(text_a: str, text_b: str) -> dict:
    """Compare two contracts and identify differences."""
    clauses_a = extract_clauses(text_a)
    clauses_b = extract_clauses(text_b)
    
    all_keys = list(dict.fromkeys(list(clauses_a.keys()) + list(clauses_b.keys())))
    
    added = []      # Only in B
    removed = []    # Only in A
    modified = []   # In both but different
    unchanged = []  # In both and same
    
    for key in all_keys:
        in_a = key in clauses_a
        in_b = key in clauses_b
        
        if in_a and not in_b:
            removed.append({
                "clause": key,
                "content": clauses_a[key][:200],
                "type": "removed"
            })
        elif not in_a and in_b:
            added.append({
                "clause": key,
                "content": clauses_b[key][:200],
                "type": "added"
            })
        elif in_a and in_b:
            # Compare content similarity
            ratio = difflib.SequenceMatcher(None, clauses_a[key], clauses_b[key]).ratio()
            if ratio < 0.95:
                diff = list(difflib.unified_diff(
                    clauses_a[key].splitlines(),
                    clauses_b[key].splitlines(),
                    lineterm='',
                    n=1
                ))
                modified.append({
                    "clause": key,
                    "similarity": round(ratio * 100, 1),
                    "diff": "\n".join(diff[2:]) if len(diff) > 2 else "",
                    "content_a": clauses_a[key][:200],
                    "content_b": clauses_b[key][:200],
                    "type": "modified"
                })
            else:
                unchanged.append({"clause": key, "type": "unchanged"})
    
    return {
        "added": added,
        "removed": removed,
        "modified": modified,
        "unchanged": unchanged,
        "total_clauses_a": len(clauses_a),
        "total_clauses_b": len(clauses_b),
    }


def generate_report(file_a: str, file_b: str, comparison: dict) -> str:
    """Generate comparison report in Markdown."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    lines = [
        "# 合同对比报告",
        "",
        f"**生成时间**: {now}",
        f"**合同A**: {file_a}",
        f"**合同B**: {file_b}",
        "",
        "---",
        "",
        "## 对比概要",
        "",
        f"| 指标 | 数量 |",
        f"|------|------|",
        f"| 合同A条款数 | {comparison['total_clauses_a']} |",
        f"| 合同B条款数 | {comparison['total_clauses_b']} |",
        f"| 🟢 新增条款 | {len(comparison['added'])} |",
        f"| 🔴 删除条款 | {len(comparison['removed'])} |",
        f"| 🟡 修改条款 | {len(comparison['modified'])} |",
        f"| ⚪ 未变条款 | {len(comparison['unchanged'])} |",
        "",
    ]
    
    if comparison["added"]:
        lines.extend(["## 🟢 新增条款（仅合同B包含）", ""])
        for item in comparison["added"]:
            lines.append(f"### {item['clause']}")
            lines.append(f"> {item['content']}")
            lines.append("")
    
    if comparison["removed"]:
        lines.extend(["## 🔴 删除条款（仅合同A包含）", ""])
        for item in comparison["removed"]:
            lines.append(f"### {item['clause']}")
            lines.append(f"> {item['content']}")
            lines.append("")
    
    if comparison["modified"]:
        lines.extend(["## 🟡 修改条款", ""])
        for item in comparison["modified"]:
            lines.append(f"### {item['clause']}（相似度: {item['similarity']}%）")
            lines.append("```diff")
            lines.append(item["diff"] if item["diff"] else "(细微调整)")
            lines.append("```")
            lines.append("")
    
    if not comparison["added"] and not comparison["removed"] and not comparison["modified"]:
        lines.append("✅ 两份合同内容完全一致。")
    
    lines.extend([
        "---",
        "",
        "## 免责声明",
        "",
        "本报告由AI自动生成，仅供参考，不构成法律意见。",
        "",
        f"*Generated by Legal Compliance Skill Bundle v1.0.0*",
    ])
    
    return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        print("用法: python contract_compare.py <contract_a> <contract_b> [--output report.md]")
        sys.exit(1)
    
    file_a = sys.argv[1]
    file_b = sys.argv[2]
    output_file = None
    
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]
    
    try:
        text_a = load_contract(file_a)
        text_b = load_contract(file_b)
        print(f"已加载: 合同A({len(text_a)}字) 合同B({len(text_b)}字)")
        
        comparison = compare_contracts(text_a, text_b)
        print(f"对比完成: {len(comparison['added'])}新增, {len(comparison['removed'])}删除, {len(comparison['modified'])}修改")
        
        report = generate_report(file_a, file_b, comparison)
        
        if output_file:
            Path(output_file).write_text(report, encoding="utf-8")
            print(f"报告已保存: {output_file}")
        else:
            print("\n" + report)
    
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
