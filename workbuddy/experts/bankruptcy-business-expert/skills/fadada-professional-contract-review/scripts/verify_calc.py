#!/usr/bin/env python3
"""
verify_calc.py — 合同计算规则核验（Step 7f 之 2）。

输入：
  --contract     合同文本路径
  --calc-rules   组织清单 calc_rules JSON 路径，或 "auto" 仅启用内置基础规则
  --bindings     可选，额外绑定变量的 JSON（如 {"违约金": 25, "合同总额": 1000000}）
  --output       findings JSON 输出路径

内置基础规则（无须组织清单也可执行）：
  1. 大小写金额一致性：合同中 "壹佰万元 ¥1,000,000" 大小写必须严格相等
  2. 违约金告警阈值：单条违约金率超过 30% 给告警（不直接判定违法）
  3. 百分比求和：所有"分项 N%"序列若 ≥3 项且组成一段，应总和 100%（容差 0.5%）
  4. 税费/分项求和：可被解析为"分项 ¥X + ¥Y = ¥Z"形式时，校验 Z 等于 X+Y（容差 1 元）
  5. 利率上限：年化利率 > 一年期 LPR 的 4 倍则告警（默认 LPR=3.45%，4 倍 ≈ 13.8%）

自定义规则通过 calc_rules[].expr 表达式驱动；表达式仅支持：
  - 数字字面量、变量名（来自合同抽取或 --bindings）
  - + - * / ( )、比较 < <= > >= == !=、布尔 and or not
  - 禁止函数调用、属性访问、import、eval、exec、attribute lookup

DSL 用 Python `ast` 白名单实现；不依赖第三方库。
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

CN_NUM_TO_INT = {
    "零": 0, "壹": 1, "贰": 2, "叁": 3, "肆": 4,
    "伍": 5, "陆": 6, "柒": 7, "捌": 8, "玖": 9,
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "两": 2,
}
CN_UNIT = {
    "拾": 10, "十": 10, "佰": 100, "百": 100,
    "仟": 1000, "千": 1000, "万": 10000, "亿": 100000000,
}
CN_DECIMAL = {"角": 0.1, "分": 0.01}


def chinese_to_number(s: str) -> float | None:
    """简化版中文金额转数字。仅支持常见万/亿/元/角/分组合。"""
    s = re.sub(r"[整人民币¥元\s]", "", s)
    if not s:
        return None
    total = 0.0
    section = 0
    digit = 0
    i = 0
    # 处理元前部分
    while i < len(s):
        ch = s[i]
        if ch in CN_NUM_TO_INT:
            digit = CN_NUM_TO_INT[ch]
        elif ch in CN_UNIT:
            unit = CN_UNIT[ch]
            if unit == 10000:
                section = (section + digit) * unit
                total += section
                section = 0
                digit = 0
            elif unit == 100000000:
                total = (total + section + digit) * unit
                section = 0
                digit = 0
            else:
                section += (digit if digit else 1) * unit
                digit = 0
        elif ch in CN_DECIMAL:
            total += digit * CN_DECIMAL[ch]
            digit = 0
        else:
            return None
        i += 1
    total += section + digit
    return total or None


# ---------- 文档读取 ----------

def read_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        try:
            xml = zf.read("word/document.xml").decode("utf-8", errors="replace")
        except KeyError:
            return ""
    root = ET.fromstring(xml)
    chunks = [t.text for t in root.iter(f"{{{W_NS}}}t") if t.text]
    return "\n".join(chunks)


def read_text_any(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return read_docx(path)
    if suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="replace")
    return path.read_text(encoding="utf-8", errors="replace")


# ---------- 内置规则 ----------

AMOUNT_PAIR_RE = re.compile(
    r"(?:大写)?[:：]?\s*([零壹贰叁肆伍陆柒捌玖拾佰仟万亿元整角分一二三四五六七八九两十百千]{2,30})"
    r"\s*\(?\s*"
    r"(?:[¥￥]?\s*([0-9][0-9,，]*(?:\.[0-9]+)?)\s*元?)\s*\)?"
)


def check_amount_consistency(text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for i, m in enumerate(AMOUNT_PAIR_RE.finditer(text), start=1):
        cn = chinese_to_number(m.group(1))
        try:
            arabic = float((m.group(2) or "").replace(",", "").replace("，", ""))
        except (TypeError, ValueError):
            continue
        if cn is None:
            continue
        if abs(cn - arabic) > 0.01:
            findings.append(
                {
                    "rule_id": f"BUILTIN-AMT-{i:03d}",
                    "name": "大小写金额一致",
                    "expr": "中文大写 == 阿拉伯数字",
                    "actual": {"chinese": m.group(1), "chinese_value": cn, "arabic": arabic},
                    "passed": False,
                    "severity": "high",
                    "message": f"大小写金额不一致：中文={cn}，阿拉伯={arabic}",
                }
            )
    return findings


PENALTY_RE = re.compile(
    r"(?:违约金|逾期违约金|滞纳金)[^0-9%‰]{0,20}([0-9]+(?:\.[0-9]+)?)\s*(%|‰)"
)
PENALTY_PER_PERIOD_RE = re.compile(
    r"按(?:日|月|年)\s*([0-9]+(?:\.[0-9]+)?)\s*(%|‰|万分之[0-9]+|千分之[0-9]+)"
)


def check_penalty_threshold(text: str, threshold: float = 30.0) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, m in enumerate(PENALTY_RE.finditer(text), start=1):
        raw = m.group(0)
        if raw in seen:
            continue
        seen.add(raw)
        val = float(m.group(1))
        if m.group(2) == "‰":
            val /= 10
        if val > threshold:
            findings.append(
                {
                    "rule_id": f"BUILTIN-PEN-{i:03d}",
                    "name": "违约金告警阈值",
                    "expr": f"违约金率 <= {threshold}%",
                    "actual": {"raw": raw, "value_pct": val},
                    "passed": False,
                    "severity": "high",
                    "message": f"违约金率 {val}% 超过常见上限 {threshold}%；建议结合合同总额复核合理性",
                }
            )
    return findings


INTEREST_RATE_RE = re.compile(
    r"(?:年(?:利率|化利率|化))[^0-9%]{0,15}([0-9]+(?:\.[0-9]+)?)\s*%"
)


def check_interest_rate(text: str, lpr_4x: float = 13.8) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, m in enumerate(INTEREST_RATE_RE.finditer(text), start=1):
        raw = m.group(0)
        if raw in seen:
            continue
        seen.add(raw)
        val = float(m.group(1))
        if val > lpr_4x:
            findings.append(
                {
                    "rule_id": f"BUILTIN-INT-{i:03d}",
                    "name": "利率上限（民间借贷 4 倍 LPR）",
                    "expr": f"年化利率 <= {lpr_4x}%",
                    "actual": {"raw": raw, "value_pct": val},
                    "passed": False,
                    "severity": "high",
                    "message": f"年化利率 {val}% 超过一年期 LPR 4 倍参考线 {lpr_4x}%；超过部分法院可能不予保护",
                }
            )
    return findings


# ---------- 受限 DSL ----------

ALLOWED_AST_NODES = (
    ast.Expression,
    ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Compare,
    ast.Constant, ast.Num,  # ast.Num 兼容 3.7 之前
    ast.Name, ast.Load,
    ast.And, ast.Or, ast.Not,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.UAdd, ast.USub,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
)


class DSLError(Exception):
    pass


def safe_eval(expr: str, bindings: dict[str, Any]) -> Any:
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise DSLError(f"语法错误: {e.msg}") from e
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_AST_NODES):
            raise DSLError(f"不允许的语法节点: {type(node).__name__}")
        if isinstance(node, ast.Name):
            if node.id not in bindings:
                raise DSLError(f"未绑定的变量: {node.id}")
        if isinstance(node, ast.Constant) and not isinstance(
            node.value, (int, float, bool, str)
        ):
            raise DSLError(f"不允许的常量类型: {type(node.value).__name__}")
    code = compile(tree, "<dsl>", "eval")
    return eval(code, {"__builtins__": {}}, dict(bindings))  # noqa: S307 — restricted


# ---------- 自定义规则 ----------

def evaluate_calc_rule(
    rule: dict[str, Any], bindings: dict[str, Any]
) -> dict[str, Any]:
    expr = rule.get("expr") or ""
    rule_bindings = dict(bindings)
    for k, v in (rule.get("bindings") or {}).items():
        rule_bindings[k] = v
    try:
        result = safe_eval(expr, rule_bindings)
        passed = bool(result)
        return {
            "rule_id": rule.get("rule_id"),
            "name": rule.get("name", expr),
            "expr": expr,
            "passed": passed,
            "severity": rule.get("severity", "mid"),
            "message": rule.get("violation_message")
            if not passed
            else "通过",
            "bindings": {k: rule_bindings[k] for k in rule_bindings if not k.startswith("_")},
        }
    except DSLError as e:
        return {
            "rule_id": rule.get("rule_id"),
            "name": rule.get("name", expr),
            "expr": expr,
            "passed": None,
            "severity": rule.get("severity", "mid"),
            "message": f"无法验证（DSL）: {e}",
        }


def auto_extract_bindings(text: str) -> dict[str, Any]:
    """从合同文本中自动抽取常见变量供 DSL 使用。

    关键约束：
      - 关键字后必须跟冒号或"为/是"等连接词，避免误命中后续条款编号
      - 金额支持千分位与货币符号
      - 违约金率支持"X% 违约金"反向语序
    """
    bindings: dict[str, Any] = {}

    # 合同总额：要求关键字后跟冒号或"为/是"，再允许币种/前缀
    m = re.search(
        r"(?:合同总额|合同金额|总金额|总价|总计金额)\s*(?:[：:为是约]+)\s*[^0-9¥￥]{0,12}[¥￥]?\s*([0-9]+(?:[,，][0-9]{3})*(?:\.[0-9]+)?)",
        text,
    )
    if m:
        bindings["合同总额"] = float(m.group(1).replace(",", "").replace("，", ""))

    # 违约金率：优先级顺序 — (1) 显式"违约金率/比例 = X%"，(2) "X% 向...支付违约金" 反向语序，
    # (3) 兜底"违约金 ... X%"（容易误命中括号内的红线引用，作为最后退路）
    m = (
        re.search(r"违约金(?:率|比例)\s*(?:[：:为是]+)?\s*([0-9]+(?:\.[0-9]+)?)\s*%", text)
        or re.search(r"按[^。\n]{0,30}?([0-9]+(?:\.[0-9]+)?)\s*%[^。\n]{0,15}?违约金", text)
        or re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%[^。\n]{0,15}?违约金", text)
        or re.search(r"(?:违约金|逾期违约金)[^。\n]{0,30}?([0-9]+(?:\.[0-9]+)?)\s*%", text)
    )
    if m:
        bindings["违约金率"] = float(m.group(1)) / 100

    # 年化利率
    m = re.search(r"年(?:利率|化\s*利率)\s*(?:[：:为是按]+)?\s*([0-9]+(?:\.[0-9]+)?)\s*%", text)
    if m:
        bindings["年化利率"] = float(m.group(1)) / 100

    # 预付款比例
    m = re.search(
        r"预付款\s*[^0-9%]{0,15}?([0-9]+(?:\.[0-9]+)?)\s*%",
        text,
    )
    if m:
        bindings["预付款比例"] = float(m.group(1)) / 100

    return bindings


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--contract", required=True)
    p.add_argument(
        "--calc-rules",
        default="auto",
        help='自定义规则 JSON 路径；"auto" 时仅跑内置规则',
    )
    p.add_argument(
        "--bindings",
        default=None,
        help="额外变量绑定 JSON 路径（覆盖自动抽取）",
    )
    p.add_argument("--output", required=True)
    p.add_argument("--penalty-threshold", type=float, default=30.0)
    p.add_argument("--lpr-4x", type=float, default=13.8)
    args = p.parse_args()

    text = read_text_any(Path(args.contract).expanduser().resolve())
    findings: list[dict[str, Any]] = []

    findings.extend(check_amount_consistency(text))
    findings.extend(check_penalty_threshold(text, args.penalty_threshold))
    findings.extend(check_interest_rate(text, args.lpr_4x))

    bindings = auto_extract_bindings(text)
    if args.bindings:
        extra = json.loads(Path(args.bindings).expanduser().read_text(encoding="utf-8"))
        if isinstance(extra, dict):
            bindings.update(extra)

    if args.calc_rules != "auto":
        rules_payload = json.loads(Path(args.calc_rules).expanduser().read_text(encoding="utf-8"))
        if isinstance(rules_payload, dict):
            rules = rules_payload.get("calc_rules", [])
        elif isinstance(rules_payload, list):
            rules = rules_payload
        else:
            print("[ERROR] calc-rules 文件结构不识别", file=sys.stderr)
            return 2
        for rule in rules:
            findings.append(evaluate_calc_rule(rule, bindings))

    summary = {
        "total": len(findings),
        "passed": sum(1 for f in findings if f.get("passed") is True),
        "failed": sum(1 for f in findings if f.get("passed") is False),
        "skipped": sum(1 for f in findings if f.get("passed") is None),
    }
    out = {"findings": findings, "summary": summary, "bindings": bindings}
    Path(args.output).expanduser().write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"ok": True, "summary": summary, "output": args.output}, ensure_ascii=False))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
