#!/usr/bin/env python3
"""
contract_extract.py — 合同关键信息提取技能 (Skill #4)
从合同文本中提取甲乙方、金额、期限、关键条款等结构化信息。

用法: python contract_extract.py <contract_file> [--output extracted.json]
"""

import sys
import re
import json
from datetime import datetime
from pathlib import Path


def load_contract(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    return path.read_text(encoding="utf-8")


def extract_info(text: str) -> dict:
    """Extract structured information from contract text."""
    info = {
        "extraction_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "title": None,
        "parties": {},
        "amount": None,
        "duration": None,
        "signing_date": None,
        "effective_date": None,
        "governing_law": None,
        "dispute_resolution": None,
        "key_obligations": [],
        "termination_conditions": [],
        "special_clauses": [],
    }
    
    # Title
    title_match = re.search(r'^(.{2,30}?(?:合同|协议|合约|契约))', text, re.MULTILINE)
    if title_match:
        info["title"] = title_match.group(1).strip()
    
    # Party A
    party_a = re.search(r'甲方[：:]\s*(.+?)(?:[\n（(]|$)', text)
    if party_a:
        name = party_a.group(1).strip()
        info["parties"]["甲方"] = name
    
    # Party B
    party_b = re.search(r'乙方[：:]\s*(.+?)(?:[\n（(]|$)', text)
    if party_b:
        name = party_b.group(1).strip()
        info["parties"]["乙方"] = name
    
    # Party C (if exists)
    party_c = re.search(r'丙方[：:]\s*(.+?)(?:[\n（(]|$)', text)
    if party_c:
        info["parties"]["丙方"] = party_c.group(1).strip()
    
    # Amount
    amount_patterns = [
        r'合同[总金]+额[：:]\s*(?:人民币)?\s*([￥¥]?\s*[\d,.]+\s*(?:万元|元|万))',
        r'价款[：:]\s*(?:人民币)?\s*([￥¥]?\s*[\d,.]+\s*(?:万元|元|万))',
        r'费用[：:]\s*(?:人民币)?\s*([￥¥]?\s*[\d,.]+\s*(?:万元|元|万))',
        r'合同价[为格]\s*(?:人民币)?\s*([￥¥]?\s*[\d,.]+\s*(?:万元|元|万))',
    ]
    for pat in amount_patterns:
        m = re.search(pat, text)
        if m:
            info["amount"] = m.group(1).strip()
            break
    
    # Duration
    duration_patterns = [
        r'合同期限[：:]\s*(.+?)(?:[\n。]|$)',
        r'有效期[：:]\s*(.+?)(?:[\n。]|$)',
        r'服务期限[：:]\s*(.+?)(?:[\n。]|$)',
    ]
    for pat in duration_patterns:
        m = re.search(pat, text)
        if m:
            info["duration"] = m.group(1).strip()[:100]
            break
    
    # Dates
    date_patterns = [
        (r'签订日期[：:]\s*(.+?)(?:[\n。]|$)', "signing_date"),
        (r'生效日期[：:]\s*(.+?)(?:[\n。]|$)', "effective_date"),
        (r'签署日期[：:]\s*(.+?)(?:[\n。]|$)', "signing_date"),
    ]
    for pat, key in date_patterns:
        m = re.search(pat, text)
        if m:
            info[key] = m.group(1).strip()[:50]
    
    # Governing law
    law_match = re.search(r'适用.+?法律[：:]\s*(.+?)(?:[\n。]|$)', text)
    if not law_match:
        law_match = re.search(r'本合同.+?适用(.+?)法律', text)
    if law_match:
        info["governing_law"] = law_match.group(1).strip()[:50]
    
    # Dispute resolution
    dispute_patterns = [
        r'争议解决[：:]\s*(.+?)(?:[\n。]|$)',
        r'(?:协商|调解|仲裁|诉讼).{0,50}(?:解决|处理)',
    ]
    for pat in dispute_patterns:
        m = re.search(pat, text)
        if m:
            info["dispute_resolution"] = m.group(0).strip()[:100]
            break
    
    # Key obligations (search for obligation-related clauses)
    obligation_keywords = ["应当", "必须", "负责", "义务", "承诺"]
    lines = text.split('\n')
    for line in lines:
        stripped = line.strip()
        if len(stripped) > 10 and any(kw in stripped for kw in obligation_keywords):
            if len(info["key_obligations"]) < 10:
                info["key_obligations"].append(stripped[:150])
    
    # Termination conditions
    term_keywords = ["解除", "终止", "提前", "违约"]
    for line in lines:
        stripped = line.strip()
        if len(stripped) > 10 and any(kw in stripped for kw in term_keywords):
            if len(info["termination_conditions"]) < 5:
                info["termination_conditions"].append(stripped[:150])
    
    return info


def generate_markdown_report(info: dict) -> str:
    """Generate a readable Markdown report."""
    lines = [
        "# 合同信息提取报告",
        "",
        f"**提取时间**: {info['extraction_time']}",
        "",
        "---",
        "",
        "## 基本信息",
        "",
        f"| 项目 | 内容 |",
        f"|------|------|",
        f"| 合同名称 | {info.get('title') or '未识别'} |",
    ]
    
    for party, name in info.get("parties", {}).items():
        lines.append(f"| {party} | {name} |")
    
    lines.extend([
        f"| 合同金额 | {info.get('amount') or '未识别'} |",
        f"| 合同期限 | {info.get('duration') or '未识别'} |",
        f"| 签订日期 | {info.get('signing_date') or '未识别'} |",
        f"| 生效日期 | {info.get('effective_date') or '未识别'} |",
        f"| 适用法律 | {info.get('governing_law') or '未识别'} |",
        f"| 争议解决 | {info.get('dispute_resolution') or '未识别'} |",
        "",
    ])
    
    if info["key_obligations"]:
        lines.extend(["## 关键义务条款", ""])
        for i, ob in enumerate(info["key_obligations"], 1):
            lines.append(f"{i}. {ob}")
        lines.append("")
    
    if info["termination_conditions"]:
        lines.extend(["## 解除/终止条件", ""])
        for i, tc in enumerate(info["termination_conditions"], 1):
            lines.append(f"{i}. {tc}")
        lines.append("")
    
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
    if len(sys.argv) < 2:
        print("用法: python contract_extract.py <contract_file> [--output result.json] [--format md]")
        sys.exit(1)
    
    contract_file = sys.argv[1]
    output_file = None
    fmt = "json"
    
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]
    
    if "--format" in sys.argv:
        idx = sys.argv.index("--format")
        if idx + 1 < len(sys.argv):
            fmt = sys.argv[idx + 1]
    
    try:
        text = load_contract(contract_file)
        print(f"已加载合同: {contract_file} ({len(text)} 字符)")
        
        info = extract_info(text)
        print(f"提取完成: {info.get('title', 'N/A')} | {len(info['parties'])}方 | {info.get('amount', 'N/A')}")
        
        if fmt == "md" or (output_file and output_file.endswith(".md")):
            output = generate_markdown_report(info)
        else:
            output = json.dumps(info, ensure_ascii=False, indent=2)
        
        if output_file:
            Path(output_file).write_text(output, encoding="utf-8")
            print(f"结果已保存: {output_file}")
        else:
            print("\n" + output)
    
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
