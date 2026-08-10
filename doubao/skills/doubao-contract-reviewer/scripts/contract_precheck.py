#!/usr/bin/env python3
"""
Contract precheck utility for doubao-contract-reviewer.

Purpose:
- Deterministically extract text and common risk clues from DOCX files.
- Provide a factual precheck JSON for the model to use before legal analysis.
- Avoid asking the model to write ad-hoc scripts during review.

Dependencies: Python standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

MODULE_KEYWORDS = {
    "payment_settlement": ["付款", "支付", "价款", "费用", "结算", "发票", "税", "账期", "预付款", "退款", "定金", "保证金"],
    "delivery_acceptance": ["交付", "交货", "验收", "验收标准", "验收期限", "视为验收", "返工", "拒收", "风险转移"],
    "liability_indemnity": ["违约", "违约金", "赔偿", "损失", "责任上限", "无限责任", "间接损失", "律师费", "连带责任", "免责"],
    "termination_exit": ["解除", "终止", "提前终止", "通知期", "整改期", "交接", "返还", "销毁", "存续"],
    "confidentiality": ["保密", "保密信息", "披露", "接收方", "披露方", "商业秘密", "保密期限", "返还或销毁"],
    "ip_results": ["知识产权", "著作权", "版权", "专利", "商标", "成果", "归属", "背景权利", "侵权", "开源", "第三方权利"],
    "data_privacy": ["数据", "个人信息", "隐私", "数据安全", "泄露", "跨境", "委托处理", "处理目的", "保存期限", "安全措施"],
    "service_sla": ["服务", "SLA", "响应", "服务级别", "人员", "资质", "替换", "服务中断", "服务报告", "考核"],
    "goods_sale": ["货物", "产品", "规格", "数量", "质量标准", "包装", "运输", "质保", "所有权", "风险负担"],
    "license_authorization": ["授权", "许可", "使用范围", "地域", "期限", "独占", "排他", "转授权", "撤销", "下架"],
    "channel_agency": ["代理", "渠道", "经销", "销售区域", "业绩目标", "价格政策", "客户归属", "窜货"],
    "lease_use": ["租赁", "租金", "押金", "用途", "维修", "转租", "退租", "返还标准"],
    "compliance_qualification": ["资质", "许可", "合规", "反商业贿赂", "制裁", "出口管制", "监管", "备案"],
}

BLANK_PATTERNS = [
    r"_{2,}",
    r"【\s*】",
    r"\[\s*\]",
    r"（\s*）",
    r"\(\s*\)",
    r"X{2,}|x{2,}",
    r"待填写|待补充|另行约定|双方另行协商",
    r"年\s*月\s*日",
]

AMOUNT_PATTERN = re.compile(
    r"(?:人民币\s*)?(?:[零壹贰叁肆伍陆柒捌玖拾佰仟万亿元整角分]+|[￥¥]?\s*\d[\d,]*(?:\.\d+)?\s*(?:元|万元|亿元)?|\d+(?:\.\d+)?\s*%)"
)
DATE_PATTERN = re.compile(
    r"\d{4}[年\-/\.]\s*\d{1,2}[月\-/\.]\s*\d{1,2}日?|\d{1,3}\s*(?:个)?工作日|\d{1,3}\s*(?:日|天|个月|月|年)|自.{0,20}?起.{0,20}?(?:至|到).{0,30}?(?:止|届满|为止)"
)
CLAUSE_PATTERN = re.compile(r"第\s*[一二三四五六七八九十百千万零〇\d]+\s*(?:条|款|项|章|节)")
CROSS_REF_PATTERN = re.compile(r"(?:按照|依据|根据|见|详见|适用|约定于|依照).{0,12}?第\s*[一二三四五六七八九十百千万零〇\d]+\s*(?:条|款|项|章|节)|附件\s*[一二三四五六七八九十\dA-Za-z-]+")
ATTACHMENT_PATTERN = re.compile(r"附件\s*[一二三四五六七八九十\dA-Za-z-]*|补充协议|报价单|订单|SOW|工作说明书|服务说明书|保密协议|数据处理协议|隐私协议")


def node_text(el: ET.Element) -> str:
    parts = []
    for node in el.iter():
        tag = node.tag.split("}")[-1]
        if tag in {"t", "delText"} and node.text:
            parts.append(node.text)
        elif tag == "tab":
            parts.append("\t")
        elif tag in {"br", "cr"}:
            parts.append("\n")
    return "".join(parts)


def extract_docx(path: Path) -> dict:
    result = {
        "paragraphs": [],
        "tables": [],
        "comments": [],
        "footnotes": [],
        "endnotes": [],
    }
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        if "word/document.xml" not in names:
            raise ValueError("DOCX missing word/document.xml")
        root = ET.fromstring(zf.read("word/document.xml"))
        body = root.find("w:body", NS)
        if body is not None:
            for child in list(body):
                tag = child.tag.split("}")[-1]
                if tag == "p":
                    text = normalize_space(node_text(child))
                    if text:
                        result["paragraphs"].append(text)
                elif tag == "tbl":
                    rows = []
                    for tr in child.findall(".//w:tr", NS):
                        row = []
                        for tc in tr.findall("./w:tc", NS):
                            row.append(normalize_space(node_text(tc)))
                        if any(row):
                            rows.append(row)
                    if rows:
                        result["tables"].append(rows)

        for part, key in [
            ("word/comments.xml", "comments"),
            ("word/footnotes.xml", "footnotes"),
            ("word/endnotes.xml", "endnotes"),
        ]:
            if part in names:
                part_root = ET.fromstring(zf.read(part))
                for el in part_root:
                    text = normalize_space(node_text(el))
                    if text:
                        result[key].append(text)
    return result


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def flatten_text(extracted: dict) -> list[str]:
    lines = []
    lines.extend(extracted.get("paragraphs", []))
    for table in extracted.get("tables", []):
        for row in table:
            line = " | ".join(cell for cell in row if cell)
            if line:
                lines.append(line)
    for key in ["comments", "footnotes", "endnotes"]:
        for item in extracted.get(key, []):
            lines.append(f"{key}: {item}")
    return [normalize_space(x) for x in lines if normalize_space(x)]


def clipped(line: str, max_len: int = 180) -> str:
    line = normalize_space(line)
    return line if len(line) <= max_len else line[:max_len] + "…"


def find_matches(lines: list[str], pattern: re.Pattern | str, max_items: int = 50) -> list[dict]:
    compiled = re.compile(pattern) if isinstance(pattern, str) else pattern
    out = []
    for idx, line in enumerate(lines, 1):
        matches = [m.group(0) for m in compiled.finditer(line)]
        if matches:
            out.append({"line_no": idx, "matches": unique(matches), "text": clipped(line)})
        if len(out) >= max_items:
            break
    return out


def unique(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        item = normalize_space(item)
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def detect_module_hits(lines: list[str]) -> dict:
    result = {}
    for module, keywords in MODULE_KEYWORDS.items():
        hits = []
        for idx, line in enumerate(lines, 1):
            matched = [kw for kw in keywords if kw.lower() in line.lower()]
            if matched:
                hits.append({"line_no": idx, "keywords": unique(matched), "text": clipped(line)})
            if len(hits) >= 12:
                break
        result[module] = hits
    return result


def detect_formal_issues(lines: list[str]) -> dict:
    combined = re.compile("|".join(f"(?:{p})" for p in BLANK_PATTERNS))
    blank_items = find_matches(lines, combined, max_items=80)
    signature_clues = []
    for idx, line in enumerate(lines, 1):
        if any(kw in line for kw in ["签署", "盖章", "法定代表人", "授权代表", "联系人", "地址", "开户行", "账号", "税号"]):
            if any(marker in line for marker in ["__", "【】", "（ ）", "年月日", "待填写", "XXX", "xx"]):
                signature_clues.append({"line_no": idx, "text": clipped(line)})
        if len(signature_clues) >= 30:
            break
    return {"blank_or_placeholder_items": blank_items, "signature_or_account_clues": signature_clues}


def detect_inconsistency_clues(lines: list[str], amounts: list[dict], dates: list[dict], attachments: list[dict]) -> list[dict]:
    clues = []

    amount_values = []
    for item in amounts:
        amount_values.extend(item.get("matches", []))
    normalized_amounts = [re.sub(r"\s+|,", "", x) for x in amount_values if any(ch.isdigit() for ch in x)]
    amount_counter = Counter(normalized_amounts)
    if len(amount_counter) >= 2:
        clues.append({
            "type": "multiple_amount_values",
            "message": "合同中出现多个金额/比例表达，需核对主合同、附件、报价单和付款条款是否一致。",
            "examples": list(amount_counter.keys())[:10],
        })

    date_values = []
    for item in dates:
        date_values.extend(item.get("matches", []))
    if len(unique(date_values)) >= 4:
        clues.append({
            "type": "multiple_date_or_period_values",
            "message": "合同中出现多个日期/期限表达，需核对合同期限、服务期限、付款期限、验收期限和解除通知期是否冲突。",
            "examples": unique(date_values)[:10],
        })

    attachment_values = []
    for item in attachments:
        attachment_values.extend(item.get("matches", []))
    if attachment_values:
        clues.append({
            "type": "attachment_cross_check_required",
            "message": "合同存在附件/补充文件线索，需做跨主合同与附件复查，尤其是金额、期限、交付、保密、数据和赔偿责任。",
            "examples": unique(attachment_values)[:10],
        })

    for idx, line in enumerate(lines, 1):
        if any(kw in line for kw in ["无限责任", "不设上限", "全部损失", "任何损失", "连带责任", "间接损失"]):
            clues.append({"type": "liability_boundary", "line_no": idx, "message": "发现责任边界偏重或无上限线索。", "text": clipped(line)})
        if len(clues) >= 30:
            break
    return clues


def infer_basic_info(path: Path, lines: list[str], extracted: dict) -> dict:
    possible_title = ""
    for line in lines[:20]:
        if any(word in line for word in ["协议", "合同", "订单", "SOW", "工作说明书"]):
            possible_title = clipped(line, 80)
            break
    possible_parties = []
    party_pattern = re.compile(r"(?:甲方|乙方|丙方|买方|卖方|委托方|受托方|服务方|客户方|授权方|被授权方|披露方|接收方)[:：]?\s*([^；;，,\n]{2,80})")
    for idx, line in enumerate(lines[:80], 1):
        matches = party_pattern.findall(line)
        for match in matches:
            possible_parties.append({"line_no": idx, "party_text": clipped(match, 100), "source": clipped(line)})
        if len(possible_parties) >= 12:
            break
    return {
        "file_name": path.name,
        "possible_title": possible_title,
        "possible_parties": possible_parties,
        "paragraph_count": len(extracted.get("paragraphs", [])),
        "table_count": len(extracted.get("tables", [])),
        "comment_count": len(extracted.get("comments", [])),
        "footnote_count": len(extracted.get("footnotes", [])),
        "endnote_count": len(extracted.get("endnotes", [])),
    }


def build_review_focus(module_hits: dict, formal_issues: dict, inconsistency_clues: list[dict]) -> list[str]:
    focus = []
    module_name_map = {
        "payment_settlement": "付款结算",
        "delivery_acceptance": "交付验收",
        "liability_indemnity": "责任赔偿",
        "termination_exit": "解除终止",
        "confidentiality": "保密",
        "ip_results": "知识产权/成果",
        "data_privacy": "数据与隐私",
        "service_sla": "服务/SLA",
        "goods_sale": "货物买卖",
        "license_authorization": "许可/授权",
        "channel_agency": "渠道/代理",
        "lease_use": "租赁/使用",
        "compliance_qualification": "合规/资质",
    }
    hit_modules = [module_name_map[k] for k, v in module_hits.items() if v]
    if hit_modules:
        focus.append("命中交易模块：" + "、".join(hit_modules))
    if formal_issues.get("blank_or_placeholder_items"):
        focus.append("存在空白项/占位符，需列入形式完善项并要求签署前补全。")
    if any(c.get("type") == "attachment_cross_check_required" for c in inconsistency_clues):
        focus.append("存在附件或补充文件线索，必须做跨条款/跨附件复查。")
    if any(c.get("type") == "liability_boundary" for c in inconsistency_clues):
        focus.append("发现责任边界偏重或无上限线索，需重点检查赔偿上限和责任例外。")
    return focus


def precheck(path: Path) -> dict:
    extracted = extract_docx(path)
    lines = flatten_text(extracted)
    amounts = find_matches(lines, AMOUNT_PATTERN, max_items=80)
    dates = find_matches(lines, DATE_PATTERN, max_items=80)
    clauses = find_matches(lines, CLAUSE_PATTERN, max_items=100)
    cross_refs = find_matches(lines, CROSS_REF_PATTERN, max_items=80)
    attachments = find_matches(lines, ATTACHMENT_PATTERN, max_items=80)
    module_hits = detect_module_hits(lines)
    formal_issues = detect_formal_issues(lines)
    inconsistency_clues = detect_inconsistency_clues(lines, amounts, dates, attachments)
    return {
        "file": str(path),
        "basic_info": infer_basic_info(path, lines, extracted),
        "formal_issues": formal_issues,
        "amounts": amounts,
        "dates_and_periods": dates,
        "clause_numbers": clauses,
        "cross_references": cross_refs,
        "attachment_clues": attachments,
        "module_hits": module_hits,
        "possible_inconsistency_clues": inconsistency_clues,
        "model_handoff": {
            "review_focus": build_review_focus(module_hits, formal_issues, inconsistency_clues),
            "must_check_cross_references": [
                "主合同与附件金额/付款是否一致",
                "主合同期限、服务期限、附件期限是否一致",
                "责任/赔偿上限是否覆盖保密、数据、IP、服务附件",
                "附件是否引入更重义务或更高赔偿",
                "同一事项在不同条款是否冲突",
            ],
            "usage_note": "本结果只提供事实线索和结构化预检查，不替代法律判断；审查报告仍需结合用户立场和合同全文输出。",
        },
        "text_preview": lines[:30],
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Precheck a DOCX contract and output structured JSON clues.")
    parser.add_argument("docx", help="Path to .docx contract file")
    parser.add_argument("--output", "-o", help="Output JSON path. Defaults to stdout.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON with indentation")
    args = parser.parse_args(argv)

    path = Path(args.docx).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if path.suffix.lower() != ".docx":
        raise ValueError("Only .docx files are supported by this precheck script.")

    result = precheck(path)
    text = json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise
