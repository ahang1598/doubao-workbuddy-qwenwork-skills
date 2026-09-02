#!/usr/bin/env python3
"""
lint_contract.py — 合同文字校对（Step 7f 之 1）。

三类检查：
  1. 错别字：基于内置「合同语境常见混淆字对照表」
  2. 敏感词：组织清单 lint_rules.sensitive_words ∪ 内置「绝对化禁用措辞」
  3. 自定义正则：组织清单 lint_rules.custom_patterns

输入：
  --contract <合同文本路径>（.docx/.doc/.txt/.md）
  --lint-rules <JSON 文件，含 lint_rules 子对象，或为该子对象本身；传 auto 仅用内置词表>
  --output <findings JSON 输出路径>

输出 JSON：
  {
    "findings": [
      {"category":"typo|sensitive|custom","hit":"竟争","suggestion":"竞争",
       "snippet":"...","line":12,"severity":"mid","rule_id":null}
    ],
    "summary":{"total":N,"by_category":{"typo":N,"sensitive":N,"custom":N}}
  }
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

# 合同语境常见混淆字对照表（前者错，后者对；仅在合同/法律文本语境下才校）
TYPO_PAIRS: list[tuple[str, str, str]] = [
    ("竟争", "竞争", "在法律/商业语境中应为'竞争'"),
    ("既使", "即使", "应为'即使'"),
    ("即然", "既然", "应为'既然'"),
    ("反应", "反映", "在 '将…向…反映' 等语境下应为'反映'"),
    ("以至", "以致", "在 '以致造成损失' 等语境下应为'以致'"),
    ("帐户", "账户", "现代合同应统一使用'账户'"),
    ("帐号", "账号", "现代合同应统一使用'账号'"),
    ("帐单", "账单", "现代合同应统一使用'账单'"),
    ("帐目", "账目", "现代合同应统一使用'账目'"),
    ("帐面", "账面", "现代合同应统一使用'账面'"),
    ("拨款", "拨款", ""),  # 占位 - 防止重复定义
    ("不能履行", "不履行", "保证条款中'不能履行'易被认定为一般保证；'不履行'更可能为连带保证（按双方真实意思选择）"),
    ("欠条", "借条", "借款关系应使用'借条'或'借款合同'，'欠条'仅证明欠款事实"),
    ("收条", "借条", "'收条'仅证明给付事实，不证明债权债务，借款应使用'借条'"),
    ("乙方", "乙方", ""),  # 占位
    ("订金", "定金", "在希望主张定金罚则时必须使用'定金'，'订金'通常仅视为预付款"),
    ("签字", "签署", "正式合同更建议使用'签署'，含义更全（可含盖章）"),
    ("劳动合同", "劳动合同", ""),  # 占位
    ("分公司", "分公司", ""),  # 占位
    ("公司印章", "公司公章", "更准确"),
    ("公章", "公章", ""),
    ("逾期", "逾期", ""),
    ("逾期付款", "逾期付款", ""),
    ("解释权", "解释权", ""),
]

# 内置「绝对化禁用措辞」清单（与 A 知识库对齐）
DEFAULT_SENSITIVE = [
    "保证胜诉", "必然胜诉", "绝对", "稳赢", "包赢", "100%不会", "绝无风险",
    "确定胜诉", "必胜", "零风险", "不会输", "完全合规", "绝对合法",
    "毫无疑问", "板上钉钉", "铁定", "肯定胜诉", "万无一失",
    "保证通过", "保证中标", "保证成功",
]


def read_docx(path: Path) -> tuple[str, list[str]]:
    """返回 (full_text, lines)；按段落切分。"""
    with zipfile.ZipFile(path) as zf:
        try:
            xml = zf.read("word/document.xml").decode("utf-8", errors="replace")
        except KeyError:
            return "", []
    root = ET.fromstring(xml)
    lines: list[str] = []
    for p_node in root.iter(f"{{{W_NS}}}p"):
        chunks = [t.text or "" for t in p_node.iter(f"{{{W_NS}}}t")]
        line = "".join(chunks)
        if line.strip():
            lines.append(line)
    return "\n".join(lines), lines


def read_text_any(path: Path) -> tuple[str, list[str]]:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return read_docx(path)
    if suffix in (".txt", ".md", ".csv"):
        text = path.read_text(encoding="utf-8", errors="replace")
        return text, text.splitlines()
    if suffix in (".doc", ".wps"):
        return f"[unsupported-format:{suffix}]", []
    text = path.read_text(encoding="utf-8", errors="replace")
    return text, text.splitlines()


def load_lint_rules(arg: str) -> dict[str, Any]:
    if arg == "auto":
        return {"typo": True, "sensitive_words": DEFAULT_SENSITIVE, "custom_patterns": []}
    payload = json.loads(Path(arg).expanduser().read_text(encoding="utf-8"))
    rules = payload.get("lint_rules") if isinstance(payload, dict) and "lint_rules" in payload else payload
    if not isinstance(rules, dict):
        raise SystemExit("[ERROR] lint-rules 文件结构不识别")
    # 合并默认敏感词
    sw = list(dict.fromkeys((rules.get("sensitive_words") or []) + DEFAULT_SENSITIVE))
    rules["sensitive_words"] = sw
    rules.setdefault("typo", True)
    rules.setdefault("custom_patterns", [])
    return rules


def find_line_no(lines: list[str], snippet: str) -> int:
    for i, line in enumerate(lines, start=1):
        if snippet in line:
            return i
    return -1


def lint_typos(text: str, lines: list[str], enabled: bool) -> list[dict[str, Any]]:
    if not enabled:
        return []
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for wrong, right, note in TYPO_PAIRS:
        if not wrong or wrong == right:
            continue
        for m in re.finditer(re.escape(wrong), text):
            line_no = find_line_no(lines, wrong)
            key = (wrong, line_no)
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                {
                    "category": "typo",
                    "hit": wrong,
                    "suggestion": right,
                    "note": note,
                    "snippet": text[max(0, m.start() - 8) : m.end() + 8],
                    "line": line_no,
                    "severity": "mid",
                    "rule_id": None,
                }
            )
    return findings


def lint_sensitive(text: str, lines: list[str], words: list[str]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for w in words:
        if not w:
            continue
        for m in re.finditer(re.escape(w), text):
            line_no = find_line_no(lines, w)
            key = (w, line_no)
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                {
                    "category": "sensitive",
                    "hit": w,
                    "suggestion": "删除该绝对化措辞或改为客观描述",
                    "snippet": text[max(0, m.start() - 8) : m.end() + 8],
                    "line": line_no,
                    "severity": "high",
                    "rule_id": None,
                }
            )
    return findings


def lint_custom(text: str, lines: list[str], patterns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for p in patterns:
        try:
            r = re.compile(p["pattern"])
        except re.error as e:
            print(f"[WARN] 自定义正则 {p.get('pattern')} 编译失败: {e}", file=sys.stderr)
            continue
        for m in r.finditer(text):
            line_no = find_line_no(lines, m.group(0))
            findings.append(
                {
                    "category": "custom",
                    "hit": m.group(0),
                    "suggestion": p.get("message", "请按公司规则修正"),
                    "snippet": text[max(0, m.start() - 8) : m.end() + 8],
                    "line": line_no,
                    "severity": p.get("severity", "mid"),
                    "rule_id": p.get("rule_id"),
                }
            )
    return findings


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--contract", required=True)
    p.add_argument("--lint-rules", default="auto")
    p.add_argument("--output", required=True)
    args = p.parse_args()

    path = Path(args.contract).expanduser().resolve()
    if not path.exists():
        print(f"[ERROR] 合同文件不存在: {path}", file=sys.stderr)
        return 2
    text, lines = read_text_any(path)
    if not text or text.startswith("[unsupported-format:"):
        print(f"[ERROR] 无法读取合同正文: {text}", file=sys.stderr)
        return 3

    rules = load_lint_rules(args.lint_rules)
    findings = (
        lint_typos(text, lines, rules.get("typo", True))
        + lint_sensitive(text, lines, rules.get("sensitive_words", []))
        + lint_custom(text, lines, rules.get("custom_patterns", []))
    )

    summary = {
        "total": len(findings),
        "by_category": {
            "typo": sum(1 for f in findings if f["category"] == "typo"),
            "sensitive": sum(1 for f in findings if f["category"] == "sensitive"),
            "custom": sum(1 for f in findings if f["category"] == "custom"),
        },
        "by_severity": {
            "high": sum(1 for f in findings if f["severity"] == "high"),
            "mid": sum(1 for f in findings if f["severity"] == "mid"),
            "low": sum(1 for f in findings if f["severity"] == "low"),
        },
    }

    out = {"findings": findings, "summary": summary}
    Path(args.output).expanduser().write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"ok": True, "summary": summary, "output": args.output}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
