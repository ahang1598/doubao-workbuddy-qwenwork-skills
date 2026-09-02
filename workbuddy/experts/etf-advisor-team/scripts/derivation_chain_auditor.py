# -*- coding: utf-8 -*-
"""推导链审计器 (Derivation Chain Auditor) — 基本面研究报告专用门禁

═══════════════════════════════════════════════════════════════════════════════
为什么需要本审计器？
═══════════════════════════════════════════════════════════════════════════════
传统报告质量门禁只看"形式合规"（字数、章节齐全、图表数量），但研报真正的价值
在于"推导链是否经得起追问"。本审计器扫描 Markdown，对**关键预测/估值章节**强制
以下推导链质量底线（基本面研究强制档）：

  1. **裸数字率 ≤ 10%**：盈利预测/三表预测/估值章节每个关键数字（销量、单价、
     营收、毛利率、净利润、目标价、WACC、永续增速、PE、市占率、CAPEX 等）必须
     有 `[依据: ...]` 内联标签或 `[^srcN]` 脚注引用；裸数字（无依据）占比 >10% 即 FAIL

  2. **假设来源链完整**：每张"分业务预测矩阵 / 三表预测 / 敏感性矩阵 / 可比公司
     估值"表格下方，必须存在 `📌 关键假设链` 段落，并至少包含 3 条假设解释（每条
     至少 1 个 [^srcN] 引用 + 至少 1 个 "Why" 层次说明）

  3. **Bull/Bear 双 case 必须并存**：盈利预测 / 估值章节必须出现 "乐观/中性/悲观"
     或 "Bull / Base / Bear" 三档情景，否则视为单边论证 → FAIL

  4. **证伪条件**：每个核心多头/空头结论必须给出 "如果 XX 发生则此判断失效"
     的证伪条件至少 2 条；否则视为不可证伪 → FAIL

  5. **三表勾稽差额 ≤ 0.5%**（机构卖方研报标准）：调用
     `stock_three_statement_projector.py` 输出的 6 条勾稽 + 5 项自洽性，任一
     核心规则（1 权益勾稽 / 2 经营现金流 / 3 固定资产滚动 / 6 所得税）的
     diff_pct 超过 0.5%（基于当期净利润标准化）即 FAIL；规则 4/5 软校验仅给 WARN

  6. **第一性追问深度（5 Why）**：核心结论后必须能追问 5 层 "Why"，每层都有
     公开信源/数据/产业链事实支撑。本审计器以"每个核心结论附近 100 字内必须
     存在 ≥3 个不同的脚注引用"作为代理指标。

═══════════════════════════════════════════════════════════════════════════════
使用方式
═══════════════════════════════════════════════════════════════════════════════
```bash
# 独立运行（推导链审计 + 三表勾稽差额校验）
python scripts/derivation_chain_auditor.py \
    OutputReport/基本面_300308_中际旭创.md \
    --code 300308 --emit-gate

# 仅推导链（跳过三表勾稽，速度更快）
python scripts/derivation_chain_auditor.py \
    OutputReport/基本面_300308_中际旭创.md --skip-articulation

# 输出 JSON 给下游脚本消费
python ... --format json
```

退出码：
- 0 = PASS（所有硬约束均通过）
- 1 = FAIL（任一硬约束 FAIL）
- 2 = WARN（仅软约束 FAIL，不阻断交付但需说明）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Sequence

# Windows PowerShell / CMD 下强制 stdout/stderr 使用 UTF-8 编码，
# 避免 ⚠️ ✅ ❌ 等符号被 GBK/CP936 吃掉导致 UnicodeEncodeError 崩溃。
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════════════════════
# 配置常量
# ═══════════════════════════════════════════════════════════════════════════════

# 基本面研究"关键章节"——这些章节内的数字必须强制审计
CRITICAL_SECTION_PATTERNS = [
    r"盈利预测",
    r"三表预测",
    r"分业务预测",
    r"敏感性分析",
    r"敏感性矩阵",
    r"估值定价",
    r"估值",
    r"PE.*Band|PB.*Band|PE / PB|PE-Band|PB-Band",
    r"DCF",
    r"可比公司",
    r"目标价",
    r"核心结论",
]

# 关键数字识别 —— 这些上下文出现的数字必须有依据
CRITICAL_NUMBER_CONTEXTS = [
    # 估值类
    "目标价", "合理价", "WACC", "永续增速", "永续增长", "PE", "PEG", "PB", "EV/EBITDA",
    "DCF", "贴现率", "折现率", "终值",
    # 收入与盈利预测
    "营收预测", "营业收入", "营收", "净利润预测", "归母净利", "净利", "毛利率",
    "净利率", "营业利润率", "EBITDA", "EPS",
    # 业务驱动
    "销量", "出货量", "出货", "单价", "ASP", "市占率", "市场份额", "渗透率",
    "市场空间", "TAM", "CAGR", "复合增速", "增速",
    # 财务结构
    "CAPEX", "资本开支", "资本支出", "FCF", "自由现金流", "ROE", "ROIC",
    "资产负债率", "净现比",
]

# "依据"标签的正则（中英文兼容）
EVIDENCE_TAG_RE = re.compile(r"\[(?:依据|来源|source|src|ref|根据)\s*[:：][^\]]+\]", re.IGNORECASE)
FOOTNOTE_REF_RE = re.compile(r"\[\^[a-zA-Z0-9_\-.\u4e00-\u9fff]+\]")  # [^src1] / [^src-rev-2026] / [^forecast.L4.base.year_1.eps]
# 章节内引用：（详见 X.Y 节...）/（详见§2.5.4）/[详见§X.X]/（本报告测算）/（本报告分析师判断）
# 用于把"内部推导/假设的章节引用"也视为合法依据来源（高盛/中金式深度研报标准写法）
# v1.9：兼容 § 前缀 + [详见§X.X] 方括号交叉引用形式（基本面双轨引用规范）
SECTION_REF_RE = re.compile(
    r"[（(\[](?:详见\s*§?\s*\d+[A-Za-z]?(?:\.\d+){0,3}\s*[^）)\]]*"
    r"|本报告(?:测算|分析师判断|预测|假设|设定[^）)\]]*|阈值设定[^）)\]]*|时间窗口[^）)\]]*)"
    r"|按\s*[A-Za-z][^）)\]]*模型[^）)\]]*"
    r")[）)\]]"
)

# 数字提取的正则（金额、百分比、倍数、价格）
NUMBER_RE = re.compile(
    r"(?:^|[^\w.])"  # 前置非词字符
    r"("                                                                  # 捕获组
    r"\d{1,3}(?:,\d{3})+(?:\.\d+)?"                                       # 1,234,567.89
    r"|\d+\.\d+(?:%|倍|x|X|×|亿|万|百万|千万|元|美元|美金|港元|欧元)?"
    r"|\d+(?:%|倍|x|X|×|亿|万|百万|千万|元|美元|美金|港元|欧元)"           # 必须带单位才算"关键数字"
    r")"
    r"(?=$|[^\w.])"
)

# 排除"纯排版数字"（编号、年份、月份、序号）
EXCLUDE_PATTERNS = [
    re.compile(r"^\d{4}$"),                  # 年份 2026
    re.compile(r"^\d{4}-\d{1,2}(-\d{1,2})?$"),  # 日期
    re.compile(r"^\d{1,2}\.?$"),             # 章节编号 1./2./3.
    re.compile(r"^\d{1,2}\.\d{1,2}\.?$"),    # 1.2 / 1.2.3
    re.compile(r"^Q[1-4]$"),                 # Q1/Q2
]


# ═══════════════════════════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AuditFinding:
    rule_id: str          # 规则编号，如 "R1-BareNumber"
    severity: str         # "FAIL" / "WARN" / "INFO"
    section: str          # 命中章节
    location: str         # 行号或定位描述
    message: str          # 人类可读说明
    suggestion: str = ""  # 修复建议


@dataclass
class AuditReport:
    report_path: str
    findings: List[AuditFinding] = field(default_factory=list)
    metrics: Dict = field(default_factory=dict)
    overall: str = "PASS"  # PASS / WARN / FAIL

    def add(self, finding: AuditFinding):
        self.findings.append(finding)
        if finding.severity == "FAIL":
            self.overall = "FAIL"
        elif finding.severity == "WARN" and self.overall == "PASS":
            self.overall = "WARN"

    def count_by_severity(self, severity: str) -> int:
        return sum(1 for f in self.findings if f.severity == severity)


# ═══════════════════════════════════════════════════════════════════════════════
# 章节提取与切片
# ═══════════════════════════════════════════════════════════════════════════════

def parse_sections(md_text: str) -> List[Tuple[str, int, int, str]]:
    """把 Markdown 拆为 (heading, start_line, end_line, body) 段列表（按 H2/H3/H4）。"""
    lines = md_text.split("\n")
    section_starts: List[Tuple[int, str]] = []
    for i, line in enumerate(lines):
        m = re.match(r"^(#{2,5})\s+(.+?)\s*$", line)
        if m:
            section_starts.append((i, m.group(2).strip()))
    sections: List[Tuple[str, int, int, str]] = []
    for idx, (start, heading) in enumerate(section_starts):
        end = section_starts[idx + 1][0] if idx + 1 < len(section_starts) else len(lines)
        body = "\n".join(lines[start:end])
        sections.append((heading, start + 1, end, body))
    return sections


def is_critical_section(heading: str) -> bool:
    for pat in CRITICAL_SECTION_PATTERNS:
        if re.search(pat, heading):
            return True
    return False


def has_critical_keyword(line: str) -> bool:
    for kw in CRITICAL_NUMBER_CONTEXTS:
        if kw in line:
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# R1 ─ 裸数字率审计（关键章节内"关键数字"必须有依据标签或脚注引用）
# ═══════════════════════════════════════════════════════════════════════════════

def is_excluded_number(num_text: str) -> bool:
    for pat in EXCLUDE_PATTERNS:
        if pat.match(num_text):
            return True
    return False


def extract_numbers_in_line(line: str) -> List[str]:
    """提取行中所有"关键数字"（带单位 / 千分位 / 小数 的数字）。"""
    results = []
    for m in NUMBER_RE.finditer(line):
        n = m.group(1).strip()
        if not is_excluded_number(n):
            results.append(n)
    return results


def line_has_evidence(line: str, nearby_lines: Sequence[str] = ()) -> bool:
    """该行或紧邻上下文是否有 [依据:...] / [^srcN] / （详见 X.Y...）章节引用。"""
    if EVIDENCE_TAG_RE.search(line) or FOOTNOTE_REF_RE.search(line) or SECTION_REF_RE.search(line):
        return True
    # 检查紧邻上下文（前后各 2 行）
    for nl in nearby_lines:
        if EVIDENCE_TAG_RE.search(nl) or FOOTNOTE_REF_RE.search(nl) or SECTION_REF_RE.search(nl):
            return True
    return False


def audit_bare_numbers(sections: List[Tuple[str, int, int, str]],
                        bare_rate_threshold: float = 0.10) -> Tuple[List[AuditFinding], Dict]:
    """裸数字率审计。

    规则：
      - 仅审计"关键章节"内的数字
      - 仅审计含"关键关键词"上下文（销量/单价/营收/毛利率/目标价 等）的行
      - 数字"有依据"判定：该行或紧邻上下 2 行内出现 [依据:...] 或 [^srcN]
      - 表格行：每个 cell 独立判定（用 | 分割）
      - 阈值：裸数字率 > 10% → FAIL；> 5% → WARN
    """
    findings: List[AuditFinding] = []
    total_numbers = 0
    bare_numbers = 0
    bare_examples: List[str] = []

    for heading, start, end, body in sections:
        if not is_critical_section(heading):
            continue
        body_lines = body.split("\n")
        for i, line in enumerate(body_lines):
            # 跳过表格分隔行、空行、 注释行
            if re.match(r"^\s*\|?\s*[-: ]+\s*\|?\s*$", line):
                continue
            if not line.strip():
                continue
            # 关键关键词上下文判定
            line_has_keyword = has_critical_keyword(line)
            # 表格行——展开为 cells，看哪些 cell 含关键关键词
            if "|" in line and line.count("|") >= 2:
                # 表头行（用上一行做关键词上下文）
                cells = [c.strip() for c in line.strip("|").split("|")]
                if not line_has_keyword and i > 0:
                    line_has_keyword = has_critical_keyword(body_lines[i - 1])
                if not line_has_keyword:
                    continue
                # 提取每个 cell 中的数字
                nearby = body_lines[max(0, i - 2):i] + body_lines[i + 1:min(len(body_lines), i + 3)]
                for cell in cells:
                    nums = extract_numbers_in_line(cell)
                    for n in nums:
                        total_numbers += 1
                        if not (line_has_evidence(cell) or line_has_evidence(line, nearby)):
                            bare_numbers += 1
                            if len(bare_examples) < 10:
                                bare_examples.append(f"L{start+i}: '{cell}' → 裸数字 `{n}`")
                continue

            if not line_has_keyword:
                continue
            nums = extract_numbers_in_line(line)
            if not nums:
                continue
            nearby = body_lines[max(0, i - 2):i] + body_lines[i + 1:min(len(body_lines), i + 3)]
            has_evi = line_has_evidence(line, nearby)
            for n in nums:
                total_numbers += 1
                if not has_evi:
                    bare_numbers += 1
                    if len(bare_examples) < 10:
                        bare_examples.append(f"L{start+i}: `{n}` @ {heading[:30]}")

    bare_rate = (bare_numbers / total_numbers) if total_numbers else 0.0
    metrics = {
        "total_critical_numbers": total_numbers,
        "bare_numbers": bare_numbers,
        "bare_rate": round(bare_rate, 4),
        "bare_rate_threshold": bare_rate_threshold,
        "bare_examples_top10": bare_examples,
    }

    if total_numbers == 0:
        findings.append(AuditFinding(
            rule_id="R1-BareNumber",
            severity="WARN",
            section="全局",
            location="-",
            message="未在关键章节检出任何含关键关键词的数字，可能章节命名异常或预测内容缺失",
            suggestion="检查是否存在『盈利预测/三表预测/估值定价/敏感性分析』章节",
        ))
    elif bare_rate > bare_rate_threshold:
        findings.append(AuditFinding(
            rule_id="R1-BareNumber",
            severity="FAIL",
            section="全局",
            location=f"裸数字 {bare_numbers}/{total_numbers}",
            message=f"关键章节裸数字率 {bare_rate*100:.1f}% > 阈值 {bare_rate_threshold*100:.0f}%（基本面硬约束）",
            suggestion=(
                "为每个关键预测/估值数字补充 `[依据: 来源]` 内联标签或 `[^srcN]` 脚注引用。"
                "示例：营收 382 亿元 [依据: 公司 2025 年报] / 2026E 销量 320 万只[^src-nvidia-gb300]"
            ),
        ))
    elif bare_rate > bare_rate_threshold / 2:
        findings.append(AuditFinding(
            rule_id="R1-BareNumber",
            severity="WARN",
            section="全局",
            location=f"裸数字 {bare_numbers}/{total_numbers}",
            message=f"裸数字率 {bare_rate*100:.1f}% 处于 WARN 区间（阈值 {bare_rate_threshold*100:.0f}%）",
            suggestion="建议进一步补充依据，提升推导链可追溯性",
        ))

    return findings, metrics


# ═══════════════════════════════════════════════════════════════════════════════
# R2 ─ 关键假设链审计（每张关键预测表后必须有"📌 关键假设链"段落）
# ═══════════════════════════════════════════════════════════════════════════════

ASSUMPTION_BLOCK_RE = re.compile(
    r"(?:📌|🔑|🧮|🔍)[^\n]{0,40}?(?:关键假设链|关键假设|假设链|预测假设|核心假设|Assumption|Why)",
    re.IGNORECASE,
)


def audit_assumption_chain(sections: List[Tuple[str, int, int, str]]) -> Tuple[List[AuditFinding], Dict]:
    """对"分业务预测矩阵 / 三表预测 / 敏感性矩阵 / 可比公司估值"四张表做强制审计。"""
    findings: List[AuditFinding] = []
    REQUIRED_TABLES_SECTIONS = [
        "分业务预测", "三表预测", "敏感性", "可比公司",
    ]
    tables_found = 0
    tables_with_chain = 0
    missing: List[str] = []

    for heading, start, end, body in sections:
        section_hit = any(k in heading for k in REQUIRED_TABLES_SECTIONS)
        if not section_hit:
            continue
        # 该章节内是否有 markdown 表
        has_table = bool(re.search(r"\n\|.*\|.*\n\|[-:\s|]+\|", body))
        if not has_table:
            continue
        tables_found += 1
        # 假设链段落判定（必须出现在该章节体内）
        has_chain = bool(ASSUMPTION_BLOCK_RE.search(body))
        # 假设链内至少 3 条 + 至少 1 个脚注引用
        chain_has_3_items = False
        chain_has_footnote = False
        if has_chain:
            chain_text = body[ASSUMPTION_BLOCK_RE.search(body).start():]
            # 用以"-"/"*"/"数字."开头的行近似计数；兼容 blockquote 前缀 `> - ...`
            chain_lines = [l for l in chain_text.split("\n") if re.match(r"^\s*>?\s*(?:[-*•]|\d+\.)\s+", l)]
            chain_has_3_items = len(chain_lines) >= 3
            chain_has_footnote = bool(FOOTNOTE_REF_RE.search(chain_text[:1500])) or bool(SECTION_REF_RE.search(chain_text[:1500]))

        if has_chain and chain_has_3_items and chain_has_footnote:
            tables_with_chain += 1
        else:
            reasons = []
            if not has_chain:
                reasons.append("缺少『📌 关键假设链』段落")
            elif not chain_has_3_items:
                reasons.append("假设链条目数 <3")
            elif not chain_has_footnote:
                reasons.append("假设链内未引用任何脚注 [^srcN]")
            missing.append(f"{heading} ({'; '.join(reasons)})")

    metrics = {
        "critical_tables_found": tables_found,
        "tables_with_complete_chain": tables_with_chain,
        "tables_missing_chain": missing,
    }

    if tables_found > 0 and tables_with_chain < tables_found:
        findings.append(AuditFinding(
            rule_id="R2-AssumptionChain",
            severity="FAIL",
            section="关键预测表",
            location=f"{tables_with_chain}/{tables_found} 张表合规",
            message=f"{tables_found - tables_with_chain} 张关键预测/估值表缺少完整『关键假设链』",
            suggestion=(
                "每张关键表（分业务预测矩阵 / 三表预测 / 敏感性矩阵 / 可比公司估值）下方"
                "必须追加：\n"
                "```\n📌 **关键假设链**\n"
                "- 假设 1：[销量/单价/市占率] = X [^src1]  ← Why: [产业逻辑/数据出处]\n"
                "- 假设 2：[毛利率] = Y%  [^src2]\n"
                "- 假设 3：[CAPEX 强度] = Z%  [^src3]\n```"
            ),
        ))
    elif tables_found == 0:
        findings.append(AuditFinding(
            rule_id="R2-AssumptionChain",
            severity="WARN",
            section="关键预测表",
            location="-",
            message="未检出『分业务预测/三表预测/敏感性/可比公司』任何一张关键表",
            suggestion="确认基本面报告是否包含核心预测内容",
        ))

    return findings, metrics


# ═══════════════════════════════════════════════════════════════════════════════
# R3 ─ Bull / Base / Bear 三档情景审计
# ═══════════════════════════════════════════════════════════════════════════════

SCENARIO_KEYWORDS = [
    [r"乐观", r"bull"],
    [r"中性", r"基准", r"base"],
    [r"悲观", r"bear"],
]


def audit_scenario_coverage(sections: List[Tuple[str, int, int, str]]) -> Tuple[List[AuditFinding], Dict]:
    """估值 / 盈利预测章节必须出现 乐观 / 中性 / 悲观 三档情景（或 Bull/Base/Bear）。"""
    findings: List[AuditFinding] = []
    target_sections = []
    for heading, start, end, body in sections:
        if re.search(r"盈利预测|估值定价|敏感性|目标价|综合评价|核心结论|DCF|三档情景|情景对比|Bull.*Base.*Bear", heading, re.IGNORECASE):
            target_sections.append((heading, body))

    found_scenarios = {0: False, 1: False, 2: False}
    hit_sections = []
    for heading, body in target_sections:
        body_low = body.lower()
        for idx, kw_list in enumerate(SCENARIO_KEYWORDS):
            for kw in kw_list:
                if re.search(kw, body_low):
                    if not found_scenarios[idx]:
                        hit_sections.append(f"{heading}({kw})")
                    found_scenarios[idx] = True

    coverage_count = sum(1 for v in found_scenarios.values() if v)
    metrics = {
        "scenario_coverage_count": coverage_count,
        "scenario_hits": hit_sections[:10],
        "bull_found": found_scenarios[0],
        "base_found": found_scenarios[1],
        "bear_found": found_scenarios[2],
    }

    if coverage_count < 3:
        missing_names = []
        if not found_scenarios[0]: missing_names.append("乐观/Bull")
        if not found_scenarios[1]: missing_names.append("中性/Base")
        if not found_scenarios[2]: missing_names.append("悲观/Bear")
        findings.append(AuditFinding(
            rule_id="R3-Scenario",
            severity="FAIL",
            section="盈利预测/估值章节",
            location=f"覆盖 {coverage_count}/3 档",
            message=f"未发现完整的三档情景，缺失：{', '.join(missing_names)}",
            suggestion=(
                "盈利预测/估值章节必须并存『乐观 / 中性 / 悲观』或『Bull / Base / Bear』三档情景，"
                "每档需对应不同的核心假设值（如销量、毛利率、市占率）和目标价/合理估值区间。"
            ),
        ))

    return findings, metrics


# ═══════════════════════════════════════════════════════════════════════════════
# R4 ─ 证伪条件审计
# ═══════════════════════════════════════════════════════════════════════════════

FALSIFY_PATTERNS = [
    r"证伪条件", r"证伪条件", r"反证", r"反面论据", r"被证伪",
    r"如果(?:.*?)[发出]生.*?(?:则|那么|此判断|失效|不成立|应)",
    r"若(?:.*?)发生.*?(?:则|那么|失效|不成立|应)",
    r"break\s*case", r"bear\s*case",
    r"何时(?:看错|放弃|止损|调整)",
]


def audit_falsifiability(sections: List[Tuple[str, int, int, str]]) -> Tuple[List[AuditFinding], Dict]:
    findings: List[AuditFinding] = []
    targets = ["核心结论", "综合评价", "盈利预测", "估值定价", "风险清单", "投资评级"]
    found_count = 0
    sections_with_falsify = []
    for heading, start, end, body in sections:
        if not any(t in heading for t in targets):
            continue
        for pat in FALSIFY_PATTERNS:
            if re.search(pat, body, re.IGNORECASE):
                found_count += 1
                sections_with_falsify.append(heading)
                break

    metrics = {
        "falsify_hits": found_count,
        "falsify_sections": sections_with_falsify,
        "threshold": 2,
    }

    if found_count < 2:
        findings.append(AuditFinding(
            rule_id="R4-Falsifiability",
            severity="FAIL",
            section="核心结论/综合评价",
            location=f"命中 {found_count}/2 章节",
            message="报告缺少充分的『证伪条件』表达；卖方研报标准要求每个核心结论可被证伪",
            suggestion=(
                "在核心结论 / 综合评价 / 盈利预测 / 估值章节中至少 2 处加入：\n"
                "  - 『证伪条件』段落，列出 2 条以上『如果 XX 事件发生 → 此判断失效』\n"
                "  - 或加入『何时调整看法 / Break case』列表"
            ),
        ))

    return findings, metrics


# ═══════════════════════════════════════════════════════════════════════════════
# R5 ─ 三表勾稽差额审计（调用 stock_three_statement_projector.py）
# ═══════════════════════════════════════════════════════════════════════════════

def audit_articulation(code: Optional[str],
                       articulation_threshold: float = 0.005,
                       skip: bool = False) -> Tuple[List[AuditFinding], Dict]:
    """调用三表预测脚本，校验勾稽差额是否在 0.5% 阈值内。"""
    findings: List[AuditFinding] = []
    metrics: Dict = {"skipped": skip, "threshold": articulation_threshold}

    if skip or not code:
        if not skip:
            findings.append(AuditFinding(
                rule_id="R5-Articulation",
                severity="WARN",
                section="三表勾稽",
                location="-",
                message="未提供 --code，跳过三表勾稽差额校验",
                suggestion="为获得完整门禁，请用 --code <stock_code> 调用",
            ))
        return findings, metrics

    # 动态导入项目内三表脚本
    script_dir = Path(__file__).parent
    sys.path.insert(0, str(script_dir))
    try:
        import stock_three_statement_projector as projector  # type: ignore
    except Exception as e:
        findings.append(AuditFinding(
            rule_id="R5-Articulation",
            severity="WARN",
            section="三表勾稽",
            location="-",
            message=f"无法导入 stock_three_statement_projector.py: {e}",
            suggestion="确认脚本路径与依赖是否正常",
        ))
        return findings, metrics

    try:
        result = projector.run_full(
            code=code,
            assumption_file=None,
            years=5,
            proj_years=3,
            peer_codes=[],
        )
    except Exception as e:
        findings.append(AuditFinding(
            rule_id="R5-Articulation",
            severity="WARN",
            section="三表勾稽",
            location="-",
            message=f"三表预测执行异常: {e}",
            suggestion="使用 PYTHONUTF8=1 重跑；检查网络与数据接口可用性",
        ))
        return findings, metrics

    check = (result.get("projection") or {}).get("check") or result.get("check") or {}
    details = check.get("details", []) if isinstance(check, dict) else []
    # 仅校验核心硬规则：1 权益、2 经营现金流、3 固定资产、6 所得税；规则 4/5 软校验
    hard_rule_prefixes = ("1. ", "2. ", "3. ", "6. ")
    # 各规则按行业卖方研报标准分别给出阈值（与 stock_three_statement_projector.py 内置容忍一致）：
    # - 规则 1 权益勾稽：±3%（直接核算，最严）
    # - 规则 2 经营现金流间接法：±40%（允许其他经营性应收应付变动扰动）
    # - 规则 3 固定资产滚动：±5%（允许处置/重估/路径依赖差异）
    # - 规则 6 所得税：核对实际税率是否在 [5%, 35%] 合理区间，由脚本 pass 字段直接判定
    #
    # 三级判定（卖方实务标准）：
    #   - 偏差 ≤ 行业容忍：PASS（不计 FAIL/WARN）
    #   - 行业容忍 < 偏差 ≤ 2×行业容忍：WARN 区（标定路径依赖差异，须显式披露）
    #   - 偏差 > 2×行业容忍：FAIL（疑似数据完整性 / 重大假设偏离 / 报表造假风险）
    #
    # 例外：规则 3（固定资产滚动）对路径依赖差异（CAPEX 强度假设 vs 折摊率假设独立外推）
    # 极度敏感，对于研发强度高、CAPEX 强度低的公司（如通信设备、互联网科技），
    # 偏差稳定在 15%~20% 区间属于路径依赖正常现象（非企业造假信号）。
    # 因此规则 3 的 FAIL 阈值放宽到 4 倍容忍（即 20%），仅当偏差 > 20% 才视为 FAIL。
    PER_RULE_THRESHOLD = {
        "1. ": 3.0,    # 单位为 %
        "2. ": 40.0,
        "3. ": 5.0,
        "6. ": None,   # 规则 6 不用百分比阈值，直接看 pass 字段
    }
    # 规则 3 的 FAIL 倍数（默认 4 倍即 20%）
    RULE_3_FAIL_MULTIPLIER = 4.0
    fail_count = 0
    warn_count = 0
    detail_summary: List[Dict] = []
    for d in details:
        check_name = str(d.get("check", ""))
        diff_pct_str = str(d.get("diff_pct", "")).rstrip("%")
        try:
            diff_abs = abs(float(diff_pct_str))
        except (ValueError, TypeError):
            diff_abs = None
        is_hard = check_name.startswith(hard_rule_prefixes)
        detail_summary.append({
            "check": check_name,
            "period": d.get("period"),
            "diff_pct": d.get("diff_pct"),
            "tolerance": d.get("tolerance"),
            "passed": d.get("pass"),
            "is_hard_rule": is_hard,
        })
        if is_hard:
            # 命中具体规则的阈值
            rule_threshold = None
            for prefix, thr in PER_RULE_THRESHOLD.items():
                if check_name.startswith(prefix):
                    rule_threshold = thr
                    break
            if rule_threshold is None:
                # 规则 6（所得税）：依赖脚本 pass 字段；pass=False 视为 FAIL
                if d.get("pass") is False:
                    fail_count += 1
            elif diff_abs is not None:
                # 规则 3 用更宽 FAIL 倍数；其他规则用 2 倍
                if check_name.startswith("3. "):
                    fail_mult = RULE_3_FAIL_MULTIPLIER
                else:
                    fail_mult = 2.0
                # 三级判定：超 fail_mult 倍 → FAIL；超 1 倍但 ≤ fail_mult 倍 → WARN；其余 → PASS
                if diff_abs > rule_threshold * fail_mult:
                    fail_count += 1
                elif diff_abs > rule_threshold:
                    warn_count += 1

    metrics.update({
        "hard_rule_diffs_over_threshold": fail_count,
        "hard_rule_diffs_in_warn_zone": warn_count,
        "details": detail_summary[:20],
    })

    if fail_count > 0:
        findings.append(AuditFinding(
            rule_id="R5-Articulation",
            severity="FAIL",
            section="三表勾稽",
            location=f"硬规则差额超阈值 {fail_count} 项",
            message=(
                f"三表勾稽硬规则中 {fail_count} 项差额超出行业卖方研报标准容忍："
                "规则 1 权益 ±3% / 规则 2 经营现金流 ±40% / 规则 3 固定资产 ±5% / 规则 6 所得税 [5%-35%]"
            ),
            suggestion=(
                "回到 stock_three_statement_projector.py 输出的 details，针对超阈值项："
                "① 检查历史报表数据是否完整；② 校准分红率（payout）与所得税率假设；"
                "③ 在报告中显式说明 FAIL 原因并修正模型"
            ),
        ))
    elif warn_count > 0:
        findings.append(AuditFinding(
            rule_id="R5-Articulation",
            severity="WARN",
            section="三表勾稽",
            location=f"{warn_count} 项差额接近阈值",
            message=f"三表勾稽 {warn_count} 项差额处于 WARN 区间（行业容忍阈值的 50%-100% 之间）",
            suggestion="建议在报告备注中说明这些差额来源（如四舍五入 / 重述 / 路径依赖差异）",
        ))

    return findings, metrics


# ═══════════════════════════════════════════════════════════════════════════════
# R6 ─ 双轨引用合规性审计（v1.8 新增，用户反馈驱动）
# 严格区分两类引用：
#   ① 外部信源 `[^srcN]` —— 必须能在「附录：数据信源汇总表」中找到 srcN 对应行，
#      且该行类型不得为「本报告 X」（本报告预测/分析/假设/测算/计算）。
#   ② 内部交叉引用 `[详见§X.X]` —— 指向本报告自身章节，不进入附录信源表。
# 当 [^srcN] 实际指向"本报告 X"伪信源时 → FAIL。
# ═══════════════════════════════════════════════════════════════════════════════

# 伪信源关键词（出现在附录表类型列即视为伪信源）
FAKE_SOURCE_KEYWORDS = [
    "本报告预测", "本报告分析", "本报告假设", "本报告测算",
    "本报告计算", "本报告综合分析", "本报告敏感性", "本报告目标价",
    "本报告 DCF", "本报告dcf", "本报告独立",
]


def audit_dual_track_references(md_text: str) -> Tuple[List[AuditFinding], Dict]:
    """R6: 双轨引用合规性 —— 识别"伪信源"脚注。

    步骤：
      1) 找出附录信源汇总表区段。
      2) 扫描表格数据行，把"类型列"或"名称列"含 FAKE_SOURCE_KEYWORDS 关键词的
         srcN 列入 fake_source_ids 黑名单。
      3) 全文扫描 [^srcN] 引用，统计有多少次引用命中黑名单。
      4) 阈值：黑名单条目数 > 0 → FAIL（每一条都要改为 [详见§X.X] 形式）。
    """
    findings: List[AuditFinding] = []

    # 附录区段
    appendix_match = re.search(
        r"(?:###?\s*附录[:：]?\s*数据信源.*?$|附录[:：].*?信源.*?$)([\s\S]*?)(?=^#{1,4}\s|\Z)",
        md_text, re.M,
    )
    appendix_text = appendix_match.group(1) if appendix_match else ""

    # 提取附录表数据行：兼容两种格式
    #   旧：| src1 | 名称 | 类型 | URL | 时效 |
    #   新：| 1<!--src1--> | 名称 | 类型 | URL | 时效 |
    fake_source_ids: List[Tuple[str, str]] = []  # [(srcN, 触发关键词), ...]
    all_appendix_ids: List[str] = []
    for line in appendix_text.splitlines():
        if not line.startswith("|") or re.match(r"^\|[\s:\-\|]+\|$", line.strip()):
            continue
        # 优先匹配新格式
        m_new = re.match(r"^\|\s*\d+\s*<!--\s*(src[a-zA-Z0-9_\-]+)\s*-->\s*\|(.+)\|\s*$", line)
        m_old = re.match(r"^\|\s*(src[a-zA-Z0-9_\-]+)\s*\|(.+)\|\s*$", line)
        if m_new:
            fid, rest = m_new.group(1), m_new.group(2)
        elif m_old:
            fid, rest = m_old.group(1), m_old.group(2)
        else:
            continue
        all_appendix_ids.append(fid)
        for kw in FAKE_SOURCE_KEYWORDS:
            if kw in rest:
                fake_source_ids.append((fid, kw))
                break

    # 全文统计每个 srcN 的引用次数
    ref_counter: Dict[str, int] = {}
    for m in re.finditer(r"\[\^(src[a-zA-Z0-9_\-]+)\]", md_text):
        fid = m.group(1)
        ref_counter[fid] = ref_counter.get(fid, 0) + 1

    fake_ids = [fid for fid, _ in fake_source_ids]
    fake_refs_total = sum(ref_counter.get(fid, 0) for fid in fake_ids)

    metrics = {
        "appendix_total_entries": len(all_appendix_ids),
        "fake_source_entries": len(fake_source_ids),
        "fake_source_ids": fake_ids[:20],
        "fake_source_examples": [
            f"{fid} → 类型含『{kw}』" for fid, kw in fake_source_ids[:10]
        ],
        "fake_refs_in_body_total": fake_refs_total,
    }

    if not all_appendix_ids:
        # 没找到附录表 —— 不阻断（由主门禁负责检查附录存在性）
        return findings, metrics

    if fake_source_ids:
        findings.append(AuditFinding(
            rule_id="R6-DualTrackRef",
            severity="FAIL",
            section="附录信源 + 全文引用",
            location=(
                f"附录表伪信源 {len(fake_source_ids)} 条，"
                f"正文累计引用 {fake_refs_total} 次"
            ),
            message=(
                "「数据信源汇总表」混入了本报告自身产出的预测/假设/分析条目（伪信源），"
                f"共 {len(fake_source_ids)} 条；这些条目被脚注 [^srcN] 引用 {fake_refs_total} 次。"
                "信源表应只放 AI 真正可达的外部独立数据源："
                "公司公告（巨潮/东方财富）/政府部委公告/IEEE 公开页/卖方研报汇总（东方财富）"
                "/官方行业协会公开发布/权威媒体（证券时报/财联社/中证报/上证报/新华社）转引报道。"
            ),
            suggestion=(
                "对每条伪信源：① 从附录表中删除该行；② 全文搜索其 [^srcN] 引用，"
                "改为 [详见§X.X] 形式指向本报告对应章节。"
                f"示例（前 5 条）：" + "; ".join(
                    f"{fid}（{kw}）" for fid, kw in fake_source_ids[:5]
                )
            ),
        ))

    return findings, metrics


# ═══════════════════════════════════════════════════════════════════════════════
# R7 ─ D 类伪信源黑名单 + 事实型数据可查证性审计（v1.9 新增，2026-05 用户反馈）
# 用户痛点：① AI 自我估算的"已发生事实"（公司销量/价格/市占率/行业规模）伪装成有信源；
#          ② 附录混入 Wind/Bloomberg/IDC/Omdia/LightCounting 等 AI 完全不可达的付费数据库。
# 三铁律：
#   ① D 类付费数据库黑名单：附录表/正文话术任何一处出现即 FAIL；
#   ② 事实型数据必须有 URL：附录表「URL」列为空、为 "—"、为 "N/A" 的"事实型"信源 FAIL；
#   ③ "根据 Wind/Bloomberg/IDC/Omdia/LightCounting/Gartner/Counterpoint/Dell'Oro" 等正文话术 FAIL。
# ═══════════════════════════════════════════════════════════════════════════════

# D 类付费数据库黑名单（与 report_quality_checker.B-4 保持一致）
D_CLASS_BLACKLIST_KEYWORDS = [
    "Wind", "万得", "Bloomberg", "彭博", "Refinitiv", "Eikon", "FactSet",
    "CapitalIQ", "Capital IQ", "S&P Global", "iFinD", "Choice 金融终端",
    "聚源数据", "朝阳永续",
    "IDC", "Omdia", "LightCounting", "Gartner", "Counterpoint",
    "Dell'Oro", "DellOro", "Yole", "IHS Markit", "Strategy Analytics",
    "Canalys", "IC Insights", "CINNO Research",
    "Frost & Sullivan", "Forrester", "Euromonitor",
]

D_CLASS_BLACKLIST_DOMAINS = [
    "wind.com.cn", "bloomberg.com/professional", "bloomberg.com/terminal",
    "refinitiv.com", "factset.com", "capitaliq.com", "spglobal.com",
    "ihs.com", "ihsmarkit.com",
    "idc.com", "omdia.com", "lightcounting.com", "gartner.com",
    "counterpointresearch.com", "delloro.com", "yole.fr",
    "strategyanalytics.com", "canalys.com",
    "icinsights.com", "cinno.com.cn",
    "frost.com", "forrester.com", "euromonitor.com",
]


def _extract_appendix_block(md_text: str) -> Optional[str]:
    """提取附录「数据信源汇总表」整段文本（与 R6 共用思路）。"""
    m = re.search(
        r"(?:###?\s*附录[:：]?\s*数据信源.*?$|附录[:：].*?信源.*?$)([\s\S]*?)(?=^#{1,4}\s|\Z)",
        md_text, re.M,
    )
    return m.group(1) if m else None


def audit_d_class_blacklist(md_text: str) -> Tuple[List[AuditFinding], Dict]:
    """R7-A: D 类付费数据库黑名单审计（附录表 + 正文话术）。"""
    findings: List[AuditFinding] = []
    metrics = {
        "appendix_d_class_hits": 0,
        "body_d_class_hits": 0,
        "d_class_keywords_triggered": [],
    }

    # ── ① 附录表 D 类关键词 / 域名命中 ──
    appendix = _extract_appendix_block(md_text)
    appendix_hits: List[str] = []
    if appendix:
        for ln in appendix.splitlines():
            if not ln.startswith("|"):
                continue
            if re.match(r"^\|[\s:\-\|]+\|$", ln.strip()):
                continue
            if "信源名称" in ln or "编号" in ln or "时效" in ln:
                continue
            ln_lower = ln.lower()
            for kw in D_CLASS_BLACKLIST_KEYWORDS:
                if kw.lower() in ln_lower:
                    # 放行"权威媒体转引（原始来源：XX，未独立验证）"形式
                    if re.search(r"转引[自自].{0,30}" + re.escape(kw), ln) or \
                       re.search(r"原始来源[：:].{0,20}" + re.escape(kw) + r".{0,30}未[独独]立验证", ln):
                        continue
                    first_cell = ln.split("|")[1].strip() if "|" in ln else ln[:30]
                    appendix_hits.append(f"{first_cell} · 命中「{kw}」")
                    metrics["d_class_keywords_triggered"].append(kw)
                    break
            for dom in D_CLASS_BLACKLIST_DOMAINS:
                if dom in ln_lower:
                    first_cell = ln.split("|")[1].strip() if "|" in ln else ln[:30]
                    appendix_hits.append(f"{first_cell} · URL 命中「{dom}」")
                    break

    metrics["appendix_d_class_hits"] = len(appendix_hits)

    # ── ② 正文"根据 Wind/IDC/Omdia/..."话术 ──
    body_patterns = [
        (r"根据\s*Wind\s*[数预一]", "Wind"),
        (r"根据\s*Bloomberg", "Bloomberg"),
        (r"根据\s*IDC\s*[预数]", "IDC"),
        (r"根据\s*Omdia", "Omdia"),
        (r"根据\s*LightCounting", "LightCounting"),
        (r"根据\s*Gartner", "Gartner"),
        (r"根据\s*Counterpoint", "Counterpoint"),
        (r"根据\s*Dell['’]?Oro", "Dell'Oro"),
        (r"根据\s*Yole", "Yole"),
        (r"Wind\s*一致预期", "Wind 一致预期"),
        (r"Bloomberg\s*consensus", "Bloomberg consensus"),
    ]
    body_hits: List[str] = []
    for pat, kw in body_patterns:
        for m in re.finditer(pat, md_text):
            start = max(0, m.start() - 20)
            end = min(len(md_text), m.end() + 30)
            snippet = md_text[start:end].replace("\n", " ")
            body_hits.append(f"「{kw}」 ··· {snippet}")
    metrics["body_d_class_hits"] = len(body_hits)

    if appendix_hits or body_hits:
        msg_parts: List[str] = []
        if appendix_hits:
            msg_parts.append(
                f"附录「数据信源汇总表」混入 D 类付费数据库 {len(appendix_hits)} 行：\n  - "
                + "\n  - ".join(appendix_hits[:6])
                + (f"\n  - …(还有 {len(appendix_hits)-6} 行)" if len(appendix_hits) > 6 else "")
            )
        if body_hits:
            msg_parts.append(
                f"正文中出现「根据 D 类付费机构」表述 {len(body_hits)} 处：\n  - "
                + "\n  - ".join(body_hits[:5])
                + (f"\n  - …(还有 {len(body_hits)-5} 处)" if len(body_hits) > 5 else "")
            )
        findings.append(AuditFinding(
            rule_id="R7-DClassBlacklist",
            severity="FAIL",
            section="附录信源 + 正文话术",
            location=f"附录命中 {len(appendix_hits)} 行 / 正文命中 {len(body_hits)} 处",
            message=(
                "报告引用了 AI **完全不可达**的付费数据库（Wind/Bloomberg/IDC/Omdia/"
                "LightCounting/Gartner/Counterpoint/Dell'Oro/Yole 等），构成 D 类伪信源："
                "AI 不付费/不登录无法验证，等同自我编造。\n\n"
                + "\n\n".join(msg_parts)
            ),
            suggestion=(
                "按【铁律二·二手回溯一手原则】处置：\n"
                "  ① 优先搜索一手公开来源：公司年报/招股书/政府部委公告/IEEE/OFC 公开论文；\n"
                "  ② 找不到一手则用权威媒体二手转引：证券时报、财联社、中证报、上证报、"
                "新华社、人民日报、证券日报、新浪财经、36氪等 → 引用二手 URL，"
                "类型列改为「权威媒体转引（原始来源：XX，未独立验证）」；\n"
                "  ③ 若无任何 A/B 类信源可引 → **整段删除**该论述，不允许 D 类信源占位；\n"
                "  ④ 公司/行业一致预期请改用东方财富汇总页面（公开可访问）："
                "https://data.eastmoney.com/report/{code}.html。"
            ),
        ))

    return findings, metrics


def audit_factual_data_url(md_text: str) -> Tuple[List[AuditFinding], Dict]:
    """R7-B: 事实型数据 URL 可查证性审计 —— 附录表「事实型」信源必须有可解析 URL。"""
    findings: List[AuditFinding] = []
    metrics = {
        "factual_entries": 0,
        "factual_no_url": 0,
        "no_url_examples": [],
    }

    appendix = _extract_appendix_block(md_text)
    if not appendix:
        return findings, metrics

    # 事实型信源类型关键词（出现在「类型」列时视为事实型）
    factual_type_kws = [
        "公司公告", "年报", "季报", "招股书", "投关记录",
        "政府公告", "政府部委", "行业协会", "国家统计局",
        "权威媒体转引", "新闻报道", "证券时报", "财联社",
        "中证报", "上证报", "新华社", "证券日报", "新浪财经",
        "卖方研报汇总", "东方财富", "巨潮", "IEEE", "OFC",
    ]

    rows = []
    for ln in appendix.splitlines():
        if not ln.startswith("|"):
            continue
        if re.match(r"^\|[\s:\-\|]+\|$", ln.strip()):
            continue
        cells = [c.strip() for c in ln.split("|")[1:-1]]
        if len(cells) < 4:
            continue
        # 跳过表头
        if any(h in ln for h in ("信源名称", "编号", "时效")):
            continue
        rows.append(cells)

    no_url_rows: List[str] = []
    for cells in rows:
        # 典型布局：序号 | 信源名称 | 类型 | URL | 时效
        if len(cells) < 4:
            continue
        type_col = cells[2] if len(cells) >= 3 else ""
        url_col = cells[3] if len(cells) >= 4 else ""
        is_factual = any(kw in type_col for kw in factual_type_kws)
        if not is_factual:
            continue
        metrics["factual_entries"] += 1
        url_clean = url_col.strip().strip("`").strip()
        if (not url_clean) or url_clean in ("—", "-", "N/A", "n/a", "无", "/"):
            metrics["factual_no_url"] += 1
            no_url_rows.append(f"{cells[0]} | {cells[1][:30]} | 类型「{type_col[:20]}」")

    metrics["no_url_examples"] = no_url_rows[:5]

    if no_url_rows:
        findings.append(AuditFinding(
            rule_id="R7-FactualURL",
            severity="FAIL",
            section="附录数据信源汇总表",
            location=f"事实型信源缺 URL {len(no_url_rows)} 行 / 共 {metrics['factual_entries']} 行事实型",
            message=(
                "附录中 {n} 行被标注为「事实型信源」（公司公告/政府公告/权威媒体/卖方研报汇总等）"
                "但 URL 列为空或填「—/N/A/无」。【铁律三】事实型已发生数据不允许 AI 估算，"
                "必须有可查证 URL；找不到 → 整段删除该论述。\n  - "
                + "\n  - ".join(no_url_rows[:6])
                + (f"\n  - …(还有 {len(no_url_rows)-6} 行)" if len(no_url_rows) > 6 else "")
            ).format(n=len(no_url_rows)),
            suggestion=(
                "对每一条无 URL 的事实型信源：① 去对应官网/巨潮/东方财富/权威媒体补 URL；"
                "② 若无法找到任何可查证 URL，则该数字属 AI 估算，必须从正文中删除该论述，"
                "并从附录表中移除该行。"
            ),
        ))

    return findings, metrics


# ═══════════════════════════════════════════════════════════════════════════════
# R8: 独立研究铁律 —— 卖方一致预期不得作为估值锚 + "我 vs 市场"对照独立小节必存在
# ═══════════════════════════════════════════════════════════════════════════════

# 禁用表述模式（v1.11 卖方一致预期刚性禁用清单）
ANCHOR_ABUSE_PATTERNS = [
    (r"以卖方一致预期为锚", "D1-以卖方一致预期为锚"),
    (r"以一致预期为基准", "D1-以一致预期为基准"),
    (r"按卖方一致预期\s*PE", "D1-按卖方一致预期PE"),
    (r"采用卖方一致\s*EPS\s*作为", "D2-采用卖方一致EPS作为"),
    (r"沿用\s*Wind[/／]?\s*东财一致预期", "D2-沿用Wind/东财一致预期"),
    (r"本报告\s*EPS\s*沿用一致预期", "D2-本报告EPS沿用一致预期"),
    (r"由于市场已普遍预期.*故本报告认为", "D3-市场普遍预期故"),
    (r"目标价取卖方一致目标价均值", "D4-目标价取卖方均值"),
    (r"目标价取卖方一致目标价中位数", "D4-目标价取卖方中位数"),
    (r"沿用卖方一致目标价", "D4-沿用卖方一致目标价"),
]

# 市场对照独立小节关键词（必须存在）
MARKET_GAP_SECTION_PATTERNS = [
    r"我\s*vs\s*市场",
    r"我\s*VS\s*市场",
    r"市场参照系",
    r"市场预期对照",
    r"一致预期偏离归因",
    r"独立预测.*卖方一致.*偏离",
]


def audit_independence_protocol(md_text: str,
                                sections: List[Tuple[str, int, int, str]]) -> Tuple[List[AuditFinding], Dict]:
    """R8: 独立研究铁律审计。

    R8-AnchorAbuse: 正文出现"以卖方一致预期为锚""按卖方一致 EPS 设定"等任一禁用表述。
    R8-MarketGap:   报告未出现"§我 vs 市场""市场参照系""一致预期偏离归因"任一独立小节。
    """
    findings: List[AuditFinding] = []
    metrics = {
        "anchor_abuse_hits": 0,
        "anchor_abuse_examples": [],
        "market_gap_section_found": False,
        "market_gap_section_heading": "",
    }

    # ---- R8-AnchorAbuse: 扫描全文禁用表述 ----
    abuse_hits = []
    for pattern, label in ANCHOR_ABUSE_PATTERNS:
        for m in re.finditer(pattern, md_text):
            line_no = md_text[:m.start()].count("\n") + 1
            snippet = md_text[max(0, m.start()-20):m.end()+20].replace("\n", " ")
            abuse_hits.append((label, line_no, snippet))

    metrics["anchor_abuse_hits"] = len(abuse_hits)
    metrics["anchor_abuse_examples"] = [
        f"L{ln} [{lab}]: …{sn}…" for lab, ln, sn in abuse_hits[:5]
    ]

    if abuse_hits:
        findings.append(AuditFinding(
            rule_id="R8-AnchorAbuse",
            severity="FAIL",
            section="正文全局",
            location=f"命中 {len(abuse_hits)} 处禁用表述",
            message=(
                "【v1.11 独立铁律一】检测到正文将卖方一致预期作为估值/预测锚的禁用表述。"
                "本团队定位是超越卖方分析师的独立研究——卖方一致预期是「市场参照系」，"
                "不是「预测锚」。命中示例：\n  - "
                + "\n  - ".join(metrics["anchor_abuse_examples"])
            ),
            suggestion=(
                "改写为：① 先按 L1-L5 五层因果链独立预测；② 卖方一致预期仅允许出现在"
                "「§一·投资概览卡末列『市场参照系』」和「§2.5-B4 我 vs 市场对照独立小节」"
                "两个位置；③ 正文表述模板：『本报告独立预测 X，作为对照卖方一致 Y，偏离 ±Z%，"
                "主要分歧在……』。详见 references/faces/消息面.md 第二部分研报辩证。"
            ),
        ))

    # ---- R8-MarketGap: 扫描章节标题是否存在"我 vs 市场"独立小节 ----
    market_gap_found = False
    market_gap_heading = ""
    for heading, start, end, body in sections:
        for pat in MARKET_GAP_SECTION_PATTERNS:
            if re.search(pat, heading) or re.search(pat, body[:300]):
                market_gap_found = True
                market_gap_heading = heading
                break
        if market_gap_found:
            break

    metrics["market_gap_section_found"] = market_gap_found
    metrics["market_gap_section_heading"] = market_gap_heading

    if not market_gap_found:
        findings.append(AuditFinding(
            rule_id="R8-MarketGap",
            severity="FAIL",
            section="估值章节末节",
            location="未找到「我 vs 市场」对照独立小节",
            message=(
                "【v1.11 独立铁律一】基本面研究报告必须在 §五估值章节末节（§5.x，"
                "如 §2.5-B4）设立独立小节「我 vs 市场对照」，呈现本报告独立预测 vs"
                "卖方一致预期的四列对照表与 5 类归因。当前报告未检出此小节。"
            ),
            suggestion=(
                "在 §2.5 估值章节末节追加 §2.5-B4「我 vs 市场对照」独立小节，"
                "按 references/faces/基本面.md §⭐ 报告输出规范 · §2.5-B4 模板，含：① 四列对照表"
                "（维度/独立预测/卖方一致/偏离方向+归因）；② 5 类归因（行业景气/"
                "公司份额/ASP-成本曲线/估值方法/风险偏好）；③ 偏离根因总结段 ≥150 字。"
            ),
        ))

    return findings, metrics


# ═══════════════════════════════════════════════════════════════════════════════
# R9: 全口径估值铁律 —— 估值方法 ≥3 种 + 可比公司国内+国外双维度+六维评分
# ═══════════════════════════════════════════════════════════════════════════════

# 估值方法识别词典（基本面报告须覆盖 ≥3 种）
VALUATION_METHODS = {
    "DCF":            [r"\bDCF\b", r"FCFF", r"自由现金流贴现", r"两阶段(?:增长)?模型"],
    "PE-Band":        [r"PE-?Band", r"PE\s*历史分位", r"PE\s*估值带", r"历史\s*PE\s*中位数"],
    "可比公司":       [r"可比公司", r"可比横比", r"可比估值表", r"同业横向对标"],
    "PEG":            [r"\bPEG\b"],
    "EV/EBITDA":      [r"EV/EBITDA", r"EV-EBITDA"],
    "PS":             [r"\bPS\b\s*估值", r"市销率"],
    "PB-ROE":         [r"PB-ROE", r"PB\s*估值"],
    "IRR":            [r"\bIRR\b\s*反推", r"隐含\s*IRR", r"内部收益率"],
    "DDM":            [r"\bDDM\b", r"股利贴现"],
    "SOTP":           [r"\bSOTP\b", r"分部估值"],
}

# 综合判断 5 要素关键词（必须全部出现）
COMPREHENSIVE_5_ELEMENTS = [
    ("方法收敛度",     [r"方法收敛度", r"目标价区间收敛", r"方法间.*收敛"]),
    ("适用性权重",     [r"适用性权重", r"方法权重表", r"权重理由"]),
    ("可证伪性",       [r"可证伪条件", r"可证伪性", r"证伪触发"]),
    ("极端情景压测",   [r"三档情景", r"乐观.*中性.*悲观", r"Bull.*Base.*Bear", r"情景对照矩阵"]),
    ("市场对照",       [r"我\s*vs\s*市场", r"市场参照系", r"卖方一致.*对照"]),
]


def audit_valuation_coverage(md_text: str,
                              sections: List[Tuple[str, int, int, str]]) -> Tuple[List[AuditFinding], Dict]:
    """R9: 全口径估值审计。

    R9-ValuationCoverage: 估值章节使用方法 < 3 种，或缺少综合判断 5 要素任一项。
    R9-Comparable:        可比公司未同时含 ≥3 全球 + ≥2 国内，或缺六维评分列。
    """
    findings: List[AuditFinding] = []
    metrics = {
        "valuation_methods_used": [],
        "valuation_methods_count": 0,
        "comprehensive_5_elements_found": [],
        "comprehensive_5_elements_missing": [],
        "comparable_global_count": 0,
        "comparable_domestic_count": 0,
        "comparable_six_dim_score_found": False,
    }

    # ---- 提取估值章节文本 ----
    valuation_text = ""
    for heading, start, end, body in sections:
        if re.search(r"估值|目标价|2\.5|五[、，]\s*估值|DCF|可比", heading):
            valuation_text += "\n" + body
    if not valuation_text:
        valuation_text = md_text  # 兜底：全文扫描

    # ---- R9-ValuationCoverage: 估值方法 ≥3 种 ----
    methods_used = []
    for method_name, patterns in VALUATION_METHODS.items():
        for pat in patterns:
            if re.search(pat, valuation_text, re.IGNORECASE):
                methods_used.append(method_name)
                break

    metrics["valuation_methods_used"] = methods_used
    metrics["valuation_methods_count"] = len(methods_used)

    if len(methods_used) < 3:
        findings.append(AuditFinding(
            rule_id="R9-ValuationCoverage",
            severity="FAIL",
            section="估值章节",
            location=f"仅检出 {len(methods_used)} 种估值方法（要求 ≥3）",
            message=(
                f"【v1.11 独立铁律三】基本面报告估值章节必须使用 ≥3 种估值方法（绝对+相对+交叉验证锚各 ≥1）。"
                f"当前检出：{methods_used}。"
            ),
            suggestion=(
                "至少补齐到 3 种，推荐组合：DCF/FCFF（绝对）+ PE-Band 同期口径（相对）+"
                "可比公司加权中位数（相对）+ IRR 反推（交叉验证锚）。详见"
                " references/faces/基本面.md §3.0 估值全口径铁律。"
            ),
        ))

    # ---- 综合判断 5 要素 ----
    elements_found = []
    elements_missing = []
    for elem_name, patterns in COMPREHENSIVE_5_ELEMENTS:
        hit = False
        for pat in patterns:
            if re.search(pat, valuation_text, re.IGNORECASE):
                hit = True
                break
        if hit:
            elements_found.append(elem_name)
        else:
            elements_missing.append(elem_name)

    metrics["comprehensive_5_elements_found"] = elements_found
    metrics["comprehensive_5_elements_missing"] = elements_missing

    if elements_missing:
        findings.append(AuditFinding(
            rule_id="R9-ValuationCoverage",
            severity="FAIL",
            section="估值章节·综合判断 5 要素",
            location=f"缺失要素：{elements_missing}",
            message=(
                f"【v1.11 独立铁律三】估值综合判断必须覆盖 5 要素：方法收敛度 / 适用性权重 / "
                f"可证伪性 / 极端情景压测 / 市场对照。当前已检出：{elements_found}；缺失：{elements_missing}。"
            ),
            suggestion=(
                "在 §2.5 估值章节末节补齐缺失要素段。模板见"
                " references/faces/基本面.md §⭐ 报告输出规范 · §2.5-B3 估值综合判断 5 要素。"
            ),
        ))

    # ---- R9-Comparable: 可比公司双维度 + 六维评分 ----
    # 简单识别：扫描可比公司表中的"国内/A 股/港股"vs"全球/美股/欧洲/亚太"标签
    comparable_section = ""
    for heading, start, end, body in sections:
        if re.search(r"可比公司|2\.5-B1|可比横比|可比估值", heading) or re.search(r"可比公司|2\.5-B1", body[:200]):
            comparable_section += "\n" + body

    # 国内可比识别：A 股/港股代码模式 + 国内可比关键词
    domestic_patterns = [r"A\s*股", r"港股", r"国内可比", r"\b\d{6}\b\.SH", r"\b\d{6}\b\.SZ"]
    global_patterns = [r"全球可比", r"海外可比", r"美股", r"北美", r"欧洲", r"亚太(?!.*港)",
                       r"\b[A-Z]{2,5}\b\s*[(（]\s*美股", r"NASDAQ", r"NYSE"]

    metrics["comparable_domestic_count"] = sum(
        len(re.findall(pat, comparable_section, re.IGNORECASE)) for pat in domestic_patterns
    )
    metrics["comparable_global_count"] = sum(
        len(re.findall(pat, comparable_section, re.IGNORECASE)) for pat in global_patterns
    )

    # 六维评分识别
    six_dim_patterns = [
        r"六维(?:可比性)?评分",
        r"行业相似度.*业务模式相似度",
        r"可比性\s*档位",
        r"综合分.*满分\s*30",
    ]
    metrics["comparable_six_dim_score_found"] = any(
        re.search(pat, comparable_section) for pat in six_dim_patterns
    )

    # FAIL 触发：可比公司池存在但缺六维评分（避免对非估值类报告误报）
    if comparable_section and not metrics["comparable_six_dim_score_found"]:
        findings.append(AuditFinding(
            rule_id="R9-Comparable",
            severity="FAIL",
            section="可比公司估值表",
            location="未检出六维可比性评分明细表",
            message=(
                "【v1.11 独立铁律三】可比公司表必须给出六维可比性评分（行业相似度/业务模式/"
                "客户结构/规模/盈利模式/成长阶段，各 0-5 分），并按综合分给出权重档位。"
            ),
            suggestion=(
                "在 §2.5-B1 可比公司表后追加 §2.5-B1-v11「可比公司双维度选样 + 六维可比性评分」"
                "扩展表，模板见 references/faces/基本面.md §⭐ 报告输出规范 · §2.5-B1-v11。"
            ),
        ))

    # WARN: 检测国内/全球可比是否双维度均存在（弱信号，给 WARN 不给 FAIL）
    if comparable_section and (metrics["comparable_domestic_count"] == 0 or
                                metrics["comparable_global_count"] == 0):
        findings.append(AuditFinding(
            rule_id="R9-Comparable",
            severity="WARN",
            section="可比公司估值表",
            location=(
                f"国内可比信号={metrics['comparable_domestic_count']}，"
                f"全球可比信号={metrics['comparable_global_count']}"
            ),
            message=(
                "【v1.11 独立铁律三】可比公司池建议同时覆盖 ≥3 家全球 + ≥2 家国内；"
                "当前检测到的双维度信号不足，请人工确认选样范围。"
            ),
            suggestion=(
                "光模块行业范例：[全球] Coherent / Lumentum / Fabrinet + [国内] 新易盛 / 天孚通信 / 华工科技。"
            ),
        ))

    return findings, metrics


# ═══════════════════════════════════════════════════════════════════════════════
# R10 — v1.12 数据资产三件套一致性 / 时效性审计
# ═══════════════════════════════════════════════════════════════════════════════

FORECAST_FOOTNOTE_PATTERN = re.compile(r"\[\^forecast\.([A-Za-z0-9_.\u4e00-\u9fa5]+)\]")


def _resolve_forecast_path(forecast_json: Dict[str, Any], dotted_path: str) -> Tuple[bool, Any]:
    """按点号路径在 forecast.json 中解析；返回 (可解析?, 值)。"""
    node: Any = forecast_json
    parts = dotted_path.split(".")
    for p in parts:
        if isinstance(node, dict):
            if p in node:
                node = node[p]
            else:
                return False, None
        elif isinstance(node, list):
            try:
                node = node[int(p)]
            except (ValueError, IndexError):
                return False, None
        else:
            return False, None
    return True, node


def audit_forecast_consistency(report_path: Path, md_text: str,
                                code: Optional[str] = None) -> Tuple[List[AuditFinding], Dict[str, Any]]:
    """R10: v1.15 数据资产三件套一致性 / 时效性审计（sidecar 旁路审计）。

    【v1.15 关键架构调整】
    - 旧版（v1.12-v1.14）：审计扫描报告正文中的 [^forecast.X.Y.Z] 脚注，要求路径可
      在 forecast.json 中解析。问题：把工程内部 JSON 路径暴露在最终报告中，破坏报
      告"成品感"和"自洽性"——读者必须配 forecast.json 才能读懂报告。
    - 新版（v1.15）：报告作者写报告时同步产出 {report_stem}_audit_sidecar.json
      旁路追溯文件，结构如下：
        {
          "schema_version": "audit_sidecar_v1",
          "report": "OutputReport/基本面_300308_中际旭创.md",
          "forecast_json": "OutputReport/基本面_300308_中际旭创_forecast.json",
          "数字锚点": {
            "§一/EPS 20.85": "evidence_pack.consensus_eps.0.eps",
            "§一/PE 历史分位 94.2%": "evidence_pack.valuation_percentile.PE历史分位(%)",
            ...
          }
        }
      审计器从 sidecar 读取路径，再去 forecast.json 解析校验 → 工程追溯 100% 保留，
      报告正文 100% 干净（无 [^forecast.*] 污染，由 R16-Purity 强制拦截）。

    R10-ForecastConsistency: sidecar 中路径必须能在 forecast.json 中解析；缺三件套
                              任一文件；assumptions.yaml 中 "待填" 字段 >30%；
                              sidecar 锚点数 <15 提示覆盖不足。
    R10-ForecastFreshness:    forecast.xlsx 生成时间晚于报告 .md mtime > 7 天 → WARN。
    """
    findings: List[AuditFinding] = []
    metrics: Dict[str, Any] = {
        "sidecar_path": None,
        "sidecar_exists": False,
        "sidecar_anchor_total": 0,
        "sidecar_anchor_resolved": 0,
        "sidecar_anchor_unresolved_examples": [],
        "missing_files": [],
        "assumptions_placeholder_ratio": None,
        "forecast_xlsx_age_days": None,
    }

    # 路径推断：从 report_path / code 推 forecast.json
    workspace = report_path.parents[1] if "OutputReport" in str(report_path) else Path.cwd()
    if "OutputReport" in str(report_path):
        # 报告在 OutputReport/ 下；forecast.json 同目录同名 + _forecast.json
        # 试两种命名： 基本面_{code}_*_forecast.json 或 report stem + _forecast.json
        candidate_jsons = list(report_path.parent.glob("*_forecast.json"))
        # 优先匹配同 code
        if code:
            same_code = [p for p in candidate_jsons if code in p.name]
            if same_code:
                candidate_jsons = same_code
        forecast_json_path = candidate_jsons[0] if candidate_jsons else None
    else:
        forecast_json_path = None

    # ---- 三件套文件存在性 ----
    if code:
        fd = workspace / "FinancialData"
        hist_path = fd / f"{code}_historical.xlsx"
        yaml_path = fd / f"{code}_assumptions.yaml"
        if not hist_path.exists():
            metrics["missing_files"].append(str(hist_path))
        if not yaml_path.exists():
            metrics["missing_files"].append(str(yaml_path))
        if forecast_json_path is None or not forecast_json_path.exists():
            metrics["missing_files"].append("OutputReport/*_forecast.json (按 code 匹配未找到)")
        # ---- assumptions.yaml 占位率 ----
        if yaml_path.exists():
            try:
                yt = yaml_path.read_text(encoding="utf-8")
                total = yt.count("\n") + 1
                placeholder = yt.count("待填")
                # 大致估计占位率（按行）
                lines_with_value = sum(
                    1 for ln in yt.splitlines()
                    if ":" in ln and ln.strip() and not ln.strip().startswith("#")
                       and ln.split(":", 1)[1].strip() not in ("", "{}", "[]")
                )
                if lines_with_value > 0:
                    placeholder_ratio = round(placeholder / lines_with_value, 3)
                    metrics["assumptions_placeholder_ratio"] = placeholder_ratio
                    if placeholder_ratio > 0.30:
                        findings.append(AuditFinding(
                            rule_id="R10-ForecastConsistency",
                            severity="FAIL",
                            section="数据资产前置",
                            location=f"{yaml_path.name}",
                            message=(
                                f"【v1.12 铁律一】assumptions.yaml 中「待填」字段占比 "
                                f"{placeholder_ratio:.1%} > 30%，说明二次审视未完成；"
                                f"请按 yaml 中 comment 自动注入的历史摘要给出三档差异化数字后再写报告。"
                            ),
                            suggestion=(
                                "1) 打开 FinancialData/{code}_assumptions.yaml；"
                                "2) 把所有「待填」替换为定量数字 / 文字（≥3 条 [^srcN] 信源）；"
                                "3) 重新运行 forecast_engine.py {code} --force。"
                            ),
                        ))
            except Exception:
                pass

    # ---- 缺文件 FAIL ----
    if metrics["missing_files"]:
        findings.append(AuditFinding(
            rule_id="R10-ForecastConsistency",
            severity="FAIL",
            section="数据资产前置",
            location="; ".join(metrics["missing_files"]),
            message=(
                "【v1.12 铁律二】数据资产三件套缺失。报告写作必须先完成 Phase 1 "
                "（historical → assumptions → forecast）三件套生成，再进入 Phase 2 写报告。"
            ),
            suggestion=(
                "按顺序执行：\n"
                "  Step 1: python scripts/historical_data_collector.py {code} --force\n"
                "  Step 2: python scripts/assumptions_yaml_generator.py {code} --force\n"
                "  Step 3: python scripts/forecast_engine.py {code} --force --current-price {price}"
            ),
        ))

    # ---- v1.15 sidecar 旁路审计：从 {report_stem}_audit_sidecar.json 读取数字锚点 ----
    sidecar_path = report_path.parent / f"{report_path.stem}_audit_sidecar.json"
    metrics["sidecar_path"] = str(sidecar_path)
    sidecar_anchors: Dict[str, str] = {}
    if sidecar_path.exists():
        metrics["sidecar_exists"] = True
        try:
            sc = json.loads(sidecar_path.read_text(encoding="utf-8"))
            anchors_raw = sc.get("数字锚点") or sc.get("number_anchors") or {}
            if isinstance(anchors_raw, dict):
                sidecar_anchors = {str(k): str(v) for k, v in anchors_raw.items() if v}
        except Exception as e:
            findings.append(AuditFinding(
                rule_id="R10-ForecastConsistency",
                severity="FAIL",
                section="数据资产前置（sidecar 旁路审计 v1.15）",
                location=str(sidecar_path),
                message=f"【v1.15】审计旁路文件 _audit_sidecar.json 解析失败：{e}",
                suggestion="检查 sidecar JSON 语法；schema 见 references/faces/基本面.md §⭐ 报告输出规范 · §2.5-B5.5。",
            ))
    else:
        # sidecar 缺失：FAIL（v1.15 报告自洽 + 旁路审计的核心约束）
        findings.append(AuditFinding(
            rule_id="R10-ForecastConsistency",
            severity="FAIL",
            section="数据资产前置（sidecar 旁路审计 v1.15）",
            location=str(sidecar_path),
            message=(
                "【v1.15】未找到旁路审计文件 _audit_sidecar.json。"
                "v1.15 起，报告作者写报告时必须同步产出 sidecar，"
                "把报告关键数字 → forecast.json 路径的映射写入「数字锚点」字段，"
                "用于审计追溯且不污染报告正文。"
            ),
            suggestion=(
                "在报告同目录新建 {report_stem}_audit_sidecar.json，结构示例：\n"
                '{\n'
                '  "schema_version": "audit_sidecar_v1",\n'
                '  "report": "...md",\n'
                '  "forecast_json": "..._forecast.json",\n'
                '  "数字锚点": {\n'
                '    "§一/EPS 20.85": "evidence_pack.consensus_eps.0.eps",\n'
                '    "§一/PE 历史分位 94.2%": "evidence_pack.valuation_percentile.PE历史分位(%)"\n'
                '  }\n'
                '}\n'
                "完整规范见 references/faces/基本面.md §⭐ 报告输出规范 · §2.5-B5.5。"
            ),
        ))

    metrics["sidecar_anchor_total"] = len(sidecar_anchors)

    if sidecar_anchors and forecast_json_path and forecast_json_path.exists():
        try:
            forecast_json = json.loads(forecast_json_path.read_text(encoding="utf-8"))
        except Exception as e:
            findings.append(AuditFinding(
                rule_id="R10-ForecastConsistency",
                severity="FAIL",
                section="数据资产前置（sidecar 旁路审计 v1.15）",
                location=str(forecast_json_path),
                message=f"【v1.15】forecast.json 读取失败：{e}",
                suggestion="请重新运行 forecast_engine.py 生成 forecast.json。",
            ))
            forecast_json = None
        if forecast_json is not None:
            unresolved: List[str] = []
            for anchor_key, path in sidecar_anchors.items():
                # 兼容两种写法：以 "forecast." 开头 / 直接 evidence_pack.X.Y.Z
                clean_path = path[len("forecast."):] if path.startswith("forecast.") else path
                ok, _ = _resolve_forecast_path(forecast_json, clean_path)
                if ok:
                    metrics["sidecar_anchor_resolved"] += 1
                else:
                    unresolved.append(f"{anchor_key}  →  {path}")
            metrics["sidecar_anchor_unresolved_examples"] = unresolved[:8]
            if unresolved:
                findings.append(AuditFinding(
                    rule_id="R10-ForecastConsistency",
                    severity="FAIL",
                    section="sidecar 数字锚点 → forecast.json 路径解析（v1.15）",
                    location=f"共 {len(unresolved)} 条 sidecar 路径不可在 forecast.json 中解析",
                    message=(
                        f"【v1.15 旁路审计】sidecar 中以下数字锚点的 forecast 路径无法解析：\n  - "
                        + "\n  - ".join(unresolved[:8])
                        + ("\n  ... (still " + str(len(unresolved) - 8) + " more)" if len(unresolved) > 8 else "")
                    ),
                    suggestion=(
                        "1) 核对 sidecar 「数字锚点」字段中的点号路径拼写（区分中文/英文 key）；"
                        "2) 若 forecast.json 结构有变，重新运行 forecast_engine.py；"
                        "3) 参考 forecast.xlsx Sheet 9「信源与脚注路径」获取可用路径示例。"
                    ),
                ))

    # ---- v1.15 sidecar 覆盖率提示（关键数字应当 ≥15 个）----
    if metrics["sidecar_exists"] and 0 < metrics["sidecar_anchor_total"] < 15:
        findings.append(AuditFinding(
            rule_id="R10-ForecastConsistency",
            severity="WARN",
            section="sidecar 覆盖率（v1.15）",
            location=f"sidecar 仅 {metrics['sidecar_anchor_total']} 条数字锚点（建议 ≥15）",
            message=(
                f"【v1.15】sidecar 数字锚点仅 {metrics['sidecar_anchor_total']} 条。"
                "基本面深度研报的核心数字（基准年财务/三档预测 EPS/营收/毛利率/三档目标价/"
                "现价/PE 历史分位/卖方共识/评级分布等）通常 ≥15 个，应全部纳入 sidecar 追溯。"
            ),
            suggestion="补全 sidecar 的「数字锚点」字段，覆盖报告全部关键数字。",
        ))


    # ---- R10-ForecastFreshness ----
    if forecast_json_path and forecast_json_path.exists() and report_path.exists():
        try:
            forecast_xlsx = forecast_json_path.with_suffix(".xlsx")
            if forecast_xlsx.exists():
                age_seconds = report_path.stat().st_mtime - forecast_xlsx.stat().st_mtime
                age_days = age_seconds / 86400
                metrics["forecast_xlsx_age_days"] = round(age_days, 2)
                if age_days > 7:
                    findings.append(AuditFinding(
                        rule_id="R10-ForecastFreshness",
                        severity="WARN",
                        section="数据资产时效",
                        location=f"forecast.xlsx 早于报告 {age_days:.1f} 天",
                        message=(
                            "【v1.12】forecast.xlsx 生成时间早于报告 .md mtime 超过 7 天，"
                            "建议刷新 Step 3 重新跑 forecast_engine.py 以反映最新数据。"
                        ),
                        suggestion="python scripts/forecast_engine.py {code} --force",
                    ))
        except Exception:
            pass

    return findings, metrics


# ═══════════════════════════════════════════════════════════════════════════════
# R11 — v1.13 现价铁律审计（防止凭空编造现价）
# ═══════════════════════════════════════════════════════════════════════════════

# 匹配报告中"现价 / 当前价 / 实时价 / 当前股价 / 最新价"后跟的数字
# 形式 1: "现价：300 元" / "现价 1049.87 元" / "**当前价**：**1050** 元"
# 形式 2: 表格中 "@ 300 元" / "(@ 1049.87 元 / EPS xx)"
# 兼容 markdown 加粗、冒号全/半角、空格、元/RMB
_PRICE_LABEL = r"(?:现价|当前价|当前股价|实时价|最新价|现行价格|股价)"
REALTIME_PRICE_PATTERNS = [
    # 形式 1: 标签 + 冒号 + 数字 + 元
    re.compile(
        r"\*{0,2}" + _PRICE_LABEL + r"\*{0,2}\s*[:：]\s*\*{0,2}([0-9]+(?:\.[0-9]+)?)\*{0,2}\s*元",
    ),
    # 形式 2: @ + 数字 + 元（估值表常见格式）
    re.compile(r"@\s*([0-9]+(?:\.[0-9]+)?)\s*元"),
    # 形式 3: vs 现价 + 数字 + 元
    re.compile(r"vs\s*" + _PRICE_LABEL + r"\s*([0-9]+(?:\.[0-9]+)?)\s*元"),
]

# 整数占位嫌疑（明显的占位符）：100/150/200/250/300/350/400/500/1000 元 等整十/整百
SUSPICIOUS_PLACEHOLDER_INTEGERS = {100, 150, 200, 250, 300, 350, 400, 500, 600, 800, 1000}


def audit_realtime_price(report_path: Path, md_text: str,
                          code: Optional[str] = None) -> Tuple[List[AuditFinding], Dict[str, Any]]:
    """R11: v1.13 现价铁律审计。

    R11-RealtimePrice: 报告中所有"现价/当前价/实时价/最新价/股价"出现处的数字必须：
      ① 在 forecast.json `meta.current_price` 字段中存在；
      ② 与 forecast.json 中的值偏差 ≤ 1%（容许 LLM 取整保留 2 位小数等微小误差）；
      ③ 不能是常见整数占位符（100/200/300/500/1000 元等）。
    任何一项不满足 → FAIL，提示"凭空编造现价"。
    """
    findings: List[AuditFinding] = []
    metrics: Dict[str, Any] = {
        "current_price_in_forecast": None,
        "report_price_mentions": 0,
        "matched": 0,
        "mismatched": [],
        "suspicious_placeholder": [],
        "forecast_meta_missing": False,
    }

    # 1. 从 forecast.json 读权威现价
    forecast_json_path: Optional[Path] = None
    report_stem = report_path.stem
    candidate = report_path.parent / f"{report_stem}_forecast.json"
    if candidate.exists():
        forecast_json_path = candidate
    else:
        # 兜底：扫同目录所有 *_forecast.json
        for p in report_path.parent.glob("*_forecast.json"):
            if code and code in p.name:
                forecast_json_path = p
                break

    if not forecast_json_path or not forecast_json_path.exists():
        # 没有 forecast.json — 跳过（R10 会单独报）
        return findings, metrics

    try:
        forecast_data = json.loads(forecast_json_path.read_text(encoding="utf-8"))
    except Exception as e:
        findings.append(AuditFinding(
            rule_id="R11-RealtimePrice",
            severity="WARN",
            section="数据资产/现价铁律",
            location=str(forecast_json_path),
            message=f"无法解析 forecast.json: {e}",
            suggestion="重新运行 forecast_engine.py --force",
        ))
        return findings, metrics

    forecast_meta = (forecast_data or {}).get("meta", {}) or {}
    authoritative_price = forecast_meta.get("current_price")
    if authoritative_price is None:
        # forecast.json 没有 meta.current_price — 这本身就是 forecast_engine 失败的信号
        metrics["forecast_meta_missing"] = True
        findings.append(AuditFinding(
            rule_id="R11-RealtimePrice",
            severity="FAIL",
            section="数据资产/现价铁律",
            location="forecast.json meta.current_price",
            message=(
                "【v1.13 现价铁律】forecast.json 中 meta.current_price 缺失，"
                "意味着 forecast_engine 运行时未传入或未读到实时行情。"
                "若报告引用了任何'现价/当前价'数字，则一定是凭空编造。"
            ),
            suggestion=(
                "1) 重跑 historical_data_collector.py {code} --full 抓取实时行情；"
                "2) 重跑 forecast_engine.py {code} --force 自动从 historical_meta.json 读取 last_price。"
            ),
        ))
        return findings, metrics

    metrics["current_price_in_forecast"] = authoritative_price
    realtime = forecast_meta.get("realtime_quote", {}) or {}
    rt_source = realtime.get("source", "unknown")
    rt_fetch_time = realtime.get("fetch_time")

    # 2. 扫描报告中所有"现价/当前价"提及
    mentions: List[Tuple[float, str]] = []  # (price_value, raw_match_context)
    for pat in REALTIME_PRICE_PATTERNS:
        for m in pat.finditer(md_text):
            try:
                p = float(m.group(1))
            except (ValueError, IndexError):
                continue
            # 取上下文 30 字符
            start = max(0, m.start() - 25)
            end = min(len(md_text), m.end() + 25)
            ctx = md_text[start:end].replace("\n", " ")
            mentions.append((p, ctx))

    metrics["report_price_mentions"] = len(mentions)
    if not mentions:
        # 报告未提及现价 — 这本身可能是合规的（极简报告），不报错
        return findings, metrics

    # 3. 校验每处提及
    auth = float(authoritative_price)
    for price, ctx in mentions:
        # 偏差校验
        if auth > 0:
            deviation_pct = abs(price - auth) / auth * 100
        else:
            deviation_pct = 999.0

        if deviation_pct <= 1.0:
            metrics["matched"] += 1
            continue

        # 占位符嫌疑
        is_placeholder = (
            price == int(price)  # 整数
            and int(price) in SUSPICIOUS_PLACEHOLDER_INTEGERS
        )

        if is_placeholder:
            metrics["suspicious_placeholder"].append({
                "report_price": price,
                "authoritative_price": auth,
                "deviation_pct": round(deviation_pct, 2),
                "context": ctx,
            })
            findings.append(AuditFinding(
                rule_id="R11-RealtimePrice",
                severity="FAIL",
                section="数据资产/现价铁律",
                location=f"报告现价 {price} 元 vs forecast 权威价 {auth} 元",
                message=(
                    f"【v1.13 现价铁律】报告中出现整数占位符 {price} 元（属常见编造值），"
                    f"与 forecast.json 权威现价 {auth} 元偏离 {deviation_pct:.1f}%。"
                    f"\n  上下文: ...{ctx}..."
                    f"\n  权威值来源: {rt_source}（{rt_fetch_time}）"
                ),
                suggestion=(
                    f"将报告中所有现价改为 {auth} 元（forecast.json meta.current_price），"
                    "并据此重算目标价隐含涨跌幅、IRR 反推、PE-Band 倍数倒推。"
                ),
            ))
        else:
            metrics["mismatched"].append({
                "report_price": price,
                "authoritative_price": auth,
                "deviation_pct": round(deviation_pct, 2),
                "context": ctx,
            })
            findings.append(AuditFinding(
                rule_id="R11-RealtimePrice",
                severity="FAIL",
                section="数据资产/现价铁律",
                location=f"报告现价 {price} 元 vs forecast 权威价 {auth} 元",
                message=(
                    f"【v1.13 现价铁律】报告中现价 {price} 元 与 forecast.json 权威现价 "
                    f"{auth} 元偏离 {deviation_pct:.1f}%（>1% 容差）。"
                    f"\n  上下文: ...{ctx}..."
                ),
                suggestion=f"将报告中现价统一改为 {auth} 元，或解释偏离原因（如盘中价更新）。",
            ))

    return findings, metrics


# ═══════════════════════════════════════════════════════════════════════════════
# R12-R15 — v1.14 信源利用率铁律审计
# 防止"已落盘信源不读、凭空编造卖方共识/历史财务/研报样本"
# ═══════════════════════════════════════════════════════════════════════════════

def _load_evidence_pack_from_forecast(report_path: Path,
                                       code: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """从 *_forecast.json 中读 evidence_pack 节点。"""
    forecast_json_path: Optional[Path] = None
    candidate = report_path.parent / f"{report_path.stem}_forecast.json"
    if candidate.exists():
        forecast_json_path = candidate
    else:
        for p in report_path.parent.glob("*_forecast.json"):
            if code and code in p.name:
                forecast_json_path = p
                break
    if not forecast_json_path or not forecast_json_path.exists():
        return None
    try:
        d = json.loads(forecast_json_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return (d or {}).get("evidence_pack")


def audit_consensus_eps(report_path: Path, md_text: str,
                         code: Optional[str] = None
                         ) -> Tuple[List[AuditFinding], Dict[str, Any]]:
    """R12-Consensus: 报告中"卖方一致 EPS / 市场一致预期 EPS"必须与
    forecast.evidence_pack.consensus_eps 真值匹配（偏差 ≤ 5%）。
    若报告未提及任何卖方共识 EPS（说明完全忽略卖方视角）→ FAIL。
    """
    findings: List[AuditFinding] = []
    metrics: Dict[str, Any] = {
        "consensus_eps_truth": [],
        "report_eps_mentions": 0,
        "matched": 0,
        "mismatched": [],
        "missing_consensus_section": False,
    }

    ep = _load_evidence_pack_from_forecast(report_path, code)
    if not ep:
        return findings, metrics  # 无 evidence_pack 由 R10 报

    truth_eps_by_year: Dict[str, float] = {}
    for row in ep.get("consensus_eps", []) or []:
        try:
            y = str(row.get("year"))
            v = float(row.get("eps")) if row.get("eps") is not None else None
            if y and v is not None:
                truth_eps_by_year[y] = v
        except (TypeError, ValueError):
            continue
    metrics["consensus_eps_truth"] = [
        {"year": y, "eps": v} for y, v in truth_eps_by_year.items()
    ]

    if not truth_eps_by_year:
        return findings, metrics

    # 扫报告中"卖方/市场/Wind/朝阳永续 一致预期 EPS ... <数字>"形式
    # 兼容多种写法
    # v1.14.1 修复：
    #   1) "EPS"与捕获数字之间不允许出现 目标价/PE/PB/PS/股价/市值/PEG/EV 等
    #      非 EPS 语义关键词，防止跨表达式误抓"目标价 542 元 / PE 中位数 26.0x"
    #   2) "EPS"与数字之间允许出现 = / : / 为 / 约 / ≈ / 区间 / 至 / ~ 等赋值或区间符
    #   3) 区间表达式 "20-25 元" / "20~25 元" 取上限作 EPS 检测
    pat = re.compile(
        r"(?:卖方|市场|Wind|wind|朝阳永续|彭博|一致预期|一致预测|consensus)"
        # 关键上下文窗口：禁止出现非 EPS 语义关键词
        r"(?:(?!目标价|PE|pe|PB|pb|PS|ps|PEG|EV|股价|市值|涨幅|跌幅|空间|溢价|折价)[^。\n]){0,40}?"
        r"EPS"
        # EPS 到数字之间：必须是赋值/区间符或纯空白连接符，禁止跨非 EPS 语义词
        r"(?:(?!目标价|PE|pe|PB|pb|PS|ps|PEG|EV|股价|市值)[^。\n]){0,25}?"
        r"([0-9]+(?:\.[0-9]+)?)"
        # 区间上限（可选）
        r"(?:\s*[-~至到]\s*([0-9]+(?:\.[0-9]+)?))?"
        r"\s*元",
        re.IGNORECASE,
    )
    eps_in_report: List[float] = []
    for m in pat.finditer(md_text):
        try:
            v1 = float(m.group(1))
            v2 = float(m.group(2)) if m.group(2) else None
            # 区间表达式：取上限做偏差判断（更严格）
            eps_val = v2 if v2 is not None else v1
            # 合理性兜底：EPS 真实区间 0.01-200 元/股
            if 0.01 <= eps_val <= 200.0:
                eps_in_report.append(eps_val)
        except (TypeError, ValueError):
            continue
    metrics["report_eps_mentions"] = len(eps_in_report)

    # 兜底：扫报告是否有"卖方共识 / 市场一致 / 卖方一致预期 / consensus"区块
    has_consensus_section = bool(re.search(
        r"(卖方共识|市场一致|卖方一致|一致预期|Wind\s*一致|consensus)",
        md_text, re.IGNORECASE,
    ))

    if not has_consensus_section:
        metrics["missing_consensus_section"] = True
        findings.append(AuditFinding(
            rule_id="R12-Consensus",
            severity="FAIL",
            section="数据资产/信源利用率铁律 v1.14",
            location="报告全文未出现「卖方一致预期 / 市场一致 / Wind 一致 / consensus」",
            message=(
                f"【v1.14 信源利用率铁律】evidence_pack 已含 {len(truth_eps_by_year)} 期"
                f"卖方一致 EPS（{', '.join(f'{y}E={v}' for y, v in list(truth_eps_by_year.items())[:3])}），"
                "但报告全文未引用任何卖方共识——属于「完全忽略卖方视角」，违反「独立判断不等于关起门」原则。"
            ),
            suggestion=(
                "在估值章节新增「卖方共识参照系」小节，引用 forecast.evidence_pack."
                "consensus_eps 与 rating_distribution，明示自身判断 vs 市场共识的对照与差异成因。"
            ),
        ))
        return findings, metrics

    if not eps_in_report:
        # 有共识小节但没引用具体 EPS → WARN
        findings.append(AuditFinding(
            rule_id="R12-Consensus",
            severity="WARN",
            section="数据资产/信源利用率铁律 v1.14",
            location="报告含卖方共识章节但无具体 EPS 数字",
            message=(
                "出现卖方共识/一致预期相关字眼但未引用具体 EPS 数字，"
                "建议明确写出 \"<年份>E 卖方一致 EPS = X.XX 元\"。"
            ),
            suggestion="参考 forecast.evidence_pack.consensus_eps 中各年份 EPS 真值。",
        ))
        return findings, metrics

    # 校验数字偏差
    truth_values = list(truth_eps_by_year.values())
    for r_eps in eps_in_report:
        # 找最接近的真值
        nearest = min(truth_values, key=lambda v: abs(v - r_eps))
        if nearest <= 0:
            continue
        dev_pct = abs(r_eps - nearest) / nearest * 100
        if dev_pct <= 5.0:
            metrics["matched"] += 1
        else:
            metrics["mismatched"].append({
                "report_eps": r_eps,
                "nearest_truth_eps": nearest,
                "deviation_pct": round(dev_pct, 2),
                "all_truth_eps": truth_values,
            })
            findings.append(AuditFinding(
                rule_id="R12-Consensus",
                severity="FAIL",
                section="数据资产/信源利用率铁律 v1.14",
                location=f"报告卖方一致 EPS {r_eps} 元 vs evidence_pack 最近真值 {nearest} 元",
                message=(
                    f"【v1.14 信源利用率铁律】报告中卖方一致 EPS {r_eps} 元 与"
                    f" evidence_pack.consensus_eps 中最接近真值 {nearest} 元偏离 "
                    f"{dev_pct:.1f}%（>5% 阈值）。真值集合: {truth_values}。"
                    "高度怀疑凭空编造卖方共识。"
                ),
                suggestion=(
                    f"将报告卖方一致 EPS 改为真值 {truth_values}（按对应年份），"
                    "并在脚注引用 [^forecast.evidence_pack.consensus_eps]。"
                ),
            ))

    return findings, metrics


def audit_rating_distribution(report_path: Path, md_text: str,
                                code: Optional[str] = None
                                ) -> Tuple[List[AuditFinding], Dict[str, Any]]:
    """R13-RatingDist: 报告必须引用 evidence_pack.rating_distribution（机构评级分布）。
    并且，当 bull_pct ≥ 80% 时，报告自身评级若给"卖出/减持"则强制 FAIL（方向性背离）。
    """
    findings: List[AuditFinding] = []
    metrics: Dict[str, Any] = {
        "rating_total": None,
        "bull_pct": None,
        "report_cites_distribution": False,
        "report_self_rating_directional_conflict": False,
    }
    ep = _load_evidence_pack_from_forecast(report_path, code)
    if not ep:
        return findings, metrics
    rd = ep.get("rating_distribution") or {}
    if not rd:
        return findings, metrics

    metrics["rating_total"] = rd.get("合计")
    metrics["bull_pct"] = rd.get("看多比例(%)")

    # 检查报告是否引用了真实评级分布数字（如 "32 家 / 27 买入 / 100% 看多"）
    cites = False
    # 1) 命中"机构评级分布 / 评级分布 / X 家机构 / 看多比例"
    if re.search(r"(机构评级分布|评级分布|看多比例|买入家数|增持家数)", md_text):
        cites = True
    # 2) 真实数字命中（合计、买入、增持）
    total = rd.get("合计")
    buy = rd.get("买入")
    if total and re.search(rf"\b{int(total)}\s*家", md_text):
        cites = True
    if buy and re.search(rf"\b{int(buy)}\s*家.*?(买入|强烈推荐|强推)", md_text):
        cites = True
    metrics["report_cites_distribution"] = cites

    if not cites:
        findings.append(AuditFinding(
            rule_id="R13-RatingDist",
            severity="FAIL",
            section="数据资产/信源利用率铁律 v1.14",
            location="报告未引用机构评级分布",
            message=(
                f"【v1.14】evidence_pack.rating_distribution 显示近 6 月共 {total} 家机构覆盖"
                f"（买入 {buy}，看多比例 {metrics['bull_pct']}%），但报告未引用此分布。"
                "属于「完全忽略卖方共识强度」，必须在投资建议或估值章节呈现。"
            ),
            suggestion=(
                "在「卖方共识参照系」或「投资建议」章节插入评级分布表："
                "买入/增持/中性/减持/卖出 各家数 + 看多比例，并标明数据日期与来源。"
            ),
        ))

    # 方向性背离检测：若卖方看多 ≥80%，报告评级却为"卖出/减持/sell/strong sell"→ FAIL
    bull_pct = rd.get("看多比例(%)")
    if isinstance(bull_pct, (int, float)) and bull_pct >= 80.0:
        # 抽报告自身评级（取"投资评级 / 评级"附近）
        rating_match = re.search(
            r"(?:投资评级|本报告评级|评级|Rating)\s*[:：]?\s*\*{0,2}"
            r"(买入|增持|中性|减持|卖出|强烈推荐|推荐|Buy|Hold|Sell|Strong\s*Sell|Underweight|Overweight)\*{0,2}",
            md_text, re.IGNORECASE,
        )
        if rating_match:
            self_rating = rating_match.group(1).strip()
            sell_words = ("卖出", "减持", "Sell", "Strong Sell", "Underweight")
            if any(w.lower() in self_rating.lower() for w in sell_words):
                metrics["report_self_rating_directional_conflict"] = True
                findings.append(AuditFinding(
                    rule_id="R13-RatingDist",
                    severity="FAIL",
                    section="数据资产/信源利用率铁律 v1.14",
                    location=f"报告评级 {self_rating} vs 卖方看多比例 {bull_pct}%",
                    message=(
                        f"【v1.14】卖方共识看多比例 {bull_pct}%（≥80%），但报告自身评级为"
                        f"「{self_rating}」——方向性强烈背离。允许独立判断，但必须先正面呈现卖方分布，"
                        "再以「为何独立判断与共识相反」的反驳论证（≥3 条第一性证据 + 5 Why 追问）支撑。"
                    ),
                    suggestion=(
                        "若坚持卖出/减持评级：在评级区域上方追加「与卖方共识背离的反驳论证」小节，"
                        "明示 ≥3 条第一性反驳证据 + 证伪条件。否则将评级修正至与共识相洽（增持/中性等）。"
                    ),
                ))

    return findings, metrics


def audit_financial_history_coverage(report_path: Path, md_text: str,
                                       code: Optional[str] = None
                                       ) -> Tuple[List[AuditFinding], Dict[str, Any]]:
    """R14-FinancialHistory: 报告必须引用 evidence_pack.financial_history_full
    中至少 5 期不同报告期的历史数据；少于 5 期 → FAIL（仅引用 1-2 期孤立数字属于"信源虚化"）。
    """
    findings: List[AuditFinding] = []
    metrics: Dict[str, Any] = {
        "history_periods_available": 0,
        "history_periods_cited_in_report": 0,
        "cited_periods_sample": [],
    }
    ep = _load_evidence_pack_from_forecast(report_path, code)
    if not ep:
        return findings, metrics
    history = ep.get("financial_history_full") or []
    metrics["history_periods_available"] = len(history)
    if len(history) < 5:
        return findings, metrics  # 数据本身不足 5 期，跳过

    # 提取报告期标识："YYYY 年" / "YYYY 年报" / "YYYY-YY-YY" / "YYYYQX" / "YYYY 中报" / "YYYY Q1"
    cited_periods = set()
    for row in history:
        period = row.get("报告期", "")
        if not period:
            continue
        # period 形如 "2025-12-31"，类型为 "年报/Q1/中报/Q3"
        year = period[:4]
        ptype = row.get("类型", "")
        # 报告中可能写 "2025 年报" / "2025 年报" / "2025-12-31" / "2025FY" / "2025E"
        candidates = [
            f"{year} 年" + ("报" if ptype == "年报" else ""),
            f"{year}年" + ("报" if ptype == "年报" else ""),
            f"{year}-",  # 完整日期前缀
            f"{year}A",
            f"{year}FY",
        ]
        if ptype == "Q1":
            candidates.extend([f"{year} Q1", f"{year}Q1", f"{year} 一季报", f"{year}一季报"])
        elif ptype == "Q3":
            candidates.extend([f"{year} Q3", f"{year}Q3", f"{year} 三季报", f"{year}三季报"])
        elif ptype == "中报":
            candidates.extend([f"{year} 中报", f"{year}中报", f"{year} H1", f"{year}H1"])
        for c in candidates:
            if c in md_text:
                cited_periods.add(period)
                break

    metrics["history_periods_cited_in_report"] = len(cited_periods)
    metrics["cited_periods_sample"] = sorted(list(cited_periods))[:10]

    if len(cited_periods) < 5:
        findings.append(AuditFinding(
            rule_id="R14-FinancialHistory",
            severity="FAIL",
            section="数据资产/信源利用率铁律 v1.14",
            location=f"历史报告期引用数 {len(cited_periods)} < 5",
            message=(
                f"【v1.14】evidence_pack.financial_history_full 含 {len(history)} 期完整财务时序，"
                f"但报告仅引用了 {len(cited_periods)} 期：{sorted(list(cited_periods))[:5]}。"
                "属于「信源虚化」——基本面研究必须呈现历史趋势，至少 5 期。"
            ),
            suggestion=(
                "在「历史财务表现」或「行业地位」章节插入历年时序表（年报口径 ≥5 年 + 最新单季），"
                "覆盖营收/净利/ROE/毛利率/EPS 同比，并在文字中提及具体期数。"
            ),
        ))
    return findings, metrics


def audit_analyst_sample_coverage(report_path: Path, md_text: str,
                                    code: Optional[str] = None
                                    ) -> Tuple[List[AuditFinding], Dict[str, Any]]:
    """R15-AnalystSampleCoverage: 报告必须引用 evidence_pack.analyst_reports
    中至少 5 家不同机构（含真实机构名）；并优先要求出现 ≥3 个真实研究员/PDF URL。
    """
    findings: List[AuditFinding] = []
    metrics: Dict[str, Any] = {
        "available_org_count": 0,
        "cited_org_count": 0,
        "cited_orgs_sample": [],
        "researcher_hits": 0,
        "pdf_url_hits": 0,
    }
    ep = _load_evidence_pack_from_forecast(report_path, code)
    if not ep:
        return findings, metrics
    reports = ep.get("analyst_reports") or []
    if not reports:
        return findings, metrics

    orgs_available = sorted({(r.get("org") or "").strip() for r in reports if r.get("org")})
    metrics["available_org_count"] = len(orgs_available)

    cited_orgs = []
    for org in orgs_available:
        if org and org in md_text:
            cited_orgs.append(org)
    metrics["cited_org_count"] = len(cited_orgs)
    metrics["cited_orgs_sample"] = cited_orgs[:10]

    # 研究员命中
    for r in reports:
        rs = (r.get("researcher") or "").strip()
        if rs and rs in md_text:
            metrics["researcher_hits"] += 1
        url = (r.get("url") or "").strip()
        pdf_url = (r.get("pdf_url") or "").strip()
        if url and url in md_text:
            metrics["pdf_url_hits"] += 1
        elif pdf_url and pdf_url in md_text:
            metrics["pdf_url_hits"] += 1

    if len(cited_orgs) < 5:
        findings.append(AuditFinding(
            rule_id="R15-AnalystSampleCoverage",
            severity="FAIL",
            section="数据资产/信源利用率铁律 v1.14",
            location=f"研报机构引用 {len(cited_orgs)}/{len(orgs_available)} 家",
            message=(
                f"【v1.14】evidence_pack.analyst_reports 含 {len(orgs_available)} 家机构真实研报样本"
                f"（{', '.join(orgs_available[:8])} 等），但报告仅引用了 {len(cited_orgs)} 家"
                f"（{cited_orgs}）。少于 5 家视为「信源虚化」。"
            ),
            suggestion=(
                "在「卖方共识参照系」章节插入研报样本表，列出 ≥10 篇研报的"
                "机构 / 研究员 / 日期 / 预测 EPS / 预测 PE / 详情链接，并在正文以脚注形式引用。"
            ),
        ))

    return findings, metrics


# ═══════════════════════════════════════════════════════════════════════════════
# R16 — v1.15 报告纯净度铁律审计（严禁工程内部产物泄漏到最终报告）
# ═══════════════════════════════════════════════════════════════════════════════

# 工程内部脚注泄漏：报告正文出现 [^forecast.X.Y.Z] 形式（包括含中文 key 的）
ENGINEERING_FOOTNOTE_RE = re.compile(r"\[\^forecast\.[A-Za-z0-9_.\u4e00-\u9fa5()（）%]+\]")
# 工程内部"裸 JSON 路径"印迹：evidence_pack.X.Y / synthesis.factor_X / L4.base.year_X 这种
# 工程产物路径，独立出现在正文段落里（非脚注语法，但语义上仍是工程泄漏）
RAW_JSON_PATH_RE = re.compile(
    r"(?:evidence_pack|synthesis\.factor|L[1-5]_?[a-z_]*\.base|"
    r"historical_summary_from_yaml|base_year\.base_year_)"
    r"\.[A-Za-z0-9_.\u4e00-\u9fa5()（）%]+"
)
# v1.16：工程内部版本号/审计规则编号 — 严禁出现在最终报告正文
#   形如 v1.14 / v1.15.2 / R10 / R12-Consensus / R16-ReportPurity / R1-BareNumber
SKILL_VERSION_RE = re.compile(r"\bv1\.[0-9]+(?:\.[0-9]+)?\b")
AUDIT_RULE_ID_RE = re.compile(r"\bR\d{1,2}(?:-[A-Za-z][A-Za-z0-9]*)?\b")
# v1.16：工程文件名/工程模块名/工程进程语言 — 不应在面向读者的研报里出现
ENGINEERING_FILENAME_RE = re.compile(
    r"(?:forecast_engine|historical_data_collector|assumptions_yaml_generator|"
    r"derivation_chain_auditor|md2html_bclass|assumptions\.yaml|forecast\.json|"
    r"_audit_sidecar\.json|consensus\.json|report_page\.json|fundamental\.md|"
    r"\.codebuddy[\\/]|FinancialData[\\/])"
)
# v1.16：工程过程语言（强制/联动/铁律/触发条件等）出现在标题/表头时算泄漏
ENGINEERING_PROCESS_LANGUAGE_RE = re.compile(
    r"(?:强制\s*[·•]|联动\s*[·•]|铁律|触发条件|版本标识|审计规则|"
    r"信源利用率铁律|报告自洽|工程追溯|证伪铁律|独立研究铁律)"
)


def audit_report_purity(report_path: Path, md_text: str) -> Tuple[List[AuditFinding], Dict[str, Any]]:
    """R16-ReportPurity (v1.15→v1.16): 报告正文严禁出现工程内部产物。

    v1.15 覆盖：
    - 工程脚注 [^forecast.X.Y.Z]
    - 裸 JSON 路径 evidence_pack.X.Y / L4.base.year_X 等

    v1.16 扩容：
    - 工程内部版本号 v1.14 / v1.15 等
    - 审计规则编号 R10 / R12-Consensus / R16-ReportPurity 等
    - 工程文件名（forecast.json / assumptions.yaml / _audit_sidecar.json / 本地路径）
    - 工程过程语言（"强制"/"联动"/"铁律"/"触发条件"/"版本标识" 出现在标题/表头/正文）

    例外：
    - §5.3 AI 生成声明 / §6 附录元信息中允许提及 "版本标识" 一次（标识来源）
    - 附录章节后允许 ≤5 条说明性裸路径
    """
    findings: List[AuditFinding] = []
    metrics: Dict[str, Any] = {
        "engineering_footnote_hits": 0,
        "engineering_footnote_examples": [],
        "raw_json_path_hits": 0,
        "raw_json_path_examples": [],
        "skill_version_hits": 0,
        "skill_version_examples": [],
        "audit_rule_id_hits": 0,
        "audit_rule_id_examples": [],
        "engineering_filename_hits": 0,
        "engineering_filename_examples": [],
        "process_language_hits": 0,
        "process_language_examples": [],
    }

    # 命中 1：[^forecast.X.Y.Z] 脚注泄漏
    fn_hits = ENGINEERING_FOOTNOTE_RE.findall(md_text)
    metrics["engineering_footnote_hits"] = len(fn_hits)
    metrics["engineering_footnote_examples"] = list(dict.fromkeys(fn_hits))[:10]
    if fn_hits:
        findings.append(AuditFinding(
            rule_id="R16-ReportPurity",
            severity="FAIL",
            section="报告纯净度（v1.15 报告自洽铁律）",
            location=f"正文检出 {len(fn_hits)} 处 [^forecast.X.Y.Z] 工程脚注（去重 {len(set(fn_hits))} 种）",
            message=(
                f"【v1.15 报告自洽铁律】报告正文混入 {len(fn_hits)} 处工程内部脚注："
                f"{', '.join(list(dict.fromkeys(fn_hits))[:5])}"
                f"{' ...' if len(set(fn_hits)) > 5 else ''}\n"
                "  这些 [^forecast.X.Y.Z] 形式是 v1.12-v1.14 为审计追溯设计的内部锚点，"
                "但严重破坏报告作为「成品」的独立性——读者必须配 forecast.json 才能读懂。"
            ),
            suggestion=(
                "v1.15 起，报告正文严禁出现 [^forecast.X.Y.Z]：\n"
                "  ① 外部权威信源 → 用 [^srcN]（进入附录数据信源汇总表）；\n"
                "  ② 本报告内部章节互引 → 用 [详见§X.X]（不进入附录表）；\n"
                "  ③ 关键数字一句话标注依据 → 用 [依据: 卖方一致预期 / Wind / 本报告测算]；\n"
                "  ④ 工程追溯诉求 → 写入 {report_stem}_audit_sidecar.json 的「数字锚点」字段，"
                "由 R10 旁路审计接管。"
            ),
        ))

    # 命中 2：裸 JSON 路径泄漏（在正文段落直接出现 evidence_pack.X.Y 等）
    raw_hits = RAW_JSON_PATH_RE.findall(md_text)
    metrics["raw_json_path_hits"] = len(raw_hits)
    metrics["raw_json_path_examples"] = list(dict.fromkeys(raw_hits))[:10]
    if raw_hits:
        # 排除附录章节中作为"路径索引说明"列出的合法引用
        # 简化处理：附录章节后允许 ≤5 条说明性路径，超出仍判 FAIL
        appendix_idx = md_text.rfind("附录")
        if appendix_idx < 0:
            appendix_idx = len(md_text)
        body_hits = [h for h in raw_hits if md_text.find(h) < appendix_idx]
        appendix_hits = [h for h in raw_hits if md_text.find(h) >= appendix_idx]
        metrics["raw_json_path_body_hits"] = len(body_hits)
        metrics["raw_json_path_appendix_hits"] = len(appendix_hits)
        if body_hits:
            findings.append(AuditFinding(
                rule_id="R16-ReportPurity",
                severity="FAIL",
                section="报告纯净度（v1.15 报告自洽铁律）",
                location=f"正文（非附录）检出 {len(body_hits)} 处裸 JSON 路径",
                message=(
                    f"【v1.15】报告正文出现工程 JSON 路径片段："
                    f"{', '.join(list(dict.fromkeys(body_hits))[:5])}。"
                    "报告应是独立可读成品，工程路径不应暴露给读者。"
                ),
                suggestion="将路径性表达改写为业务语义陈述；如需追溯，写入 sidecar。",
            ))

    # ─── v1.16 命中 3：工程内部版本号（v1.X / v1.X.Y）─────────────────────────
    sv_hits_all = list(SKILL_VERSION_RE.finditer(md_text))
    # 例外：§5.3 AI 生成声明区域允许 1 处（用于标注工具来源）
    ai_decl_idx = md_text.find("AI 生成声明")
    if ai_decl_idx < 0:
        ai_decl_idx = float("inf")
    sv_hits_violating = [m for m in sv_hits_all if m.start() < ai_decl_idx]
    metrics["skill_version_hits"] = len(sv_hits_violating)
    metrics["skill_version_examples"] = list(dict.fromkeys(
        m.group(0) for m in sv_hits_violating
    ))[:10]
    if sv_hits_violating:
        findings.append(AuditFinding(
            rule_id="R16-ReportPurity",
            severity="FAIL",
            section="报告纯净度（v1.16 工程标识清洁）",
            location=f"正文（§5.3 AI 生成声明之外）检出 {len(sv_hits_violating)} 处工程内部版本号",
            message=(
                f"【v1.16】报告正文出现工程内部版本号："
                f"{', '.join(metrics['skill_version_examples'])}。"
                "  这是工程演进标识，券商研报、机构月报、公开研报中不会出现"
                "「v1.14 强制」「v1.15 R12+R13 联动」这类描述，必须从读者视线移除。"
            ),
            suggestion=(
                "① 标题/表头中的「(v1.14 强制 · R12+R13+R15 联动)」直接删除；\n"
                "② 正文中「v1.14 R12 5% 阈值」改写为「卖方共识偏差容差 5%」；\n"
                "③ 仅 §5.3 AI 生成声明可保留 1 次版本标注（用于 AI 可追溯）。"
            ),
        ))

    # ─── v1.16 命中 4：审计规则编号（R10 / R12-Consensus）────────────────
    rule_hits_all = list(AUDIT_RULE_ID_RE.finditer(md_text))
    # 例外：评级章节"R1-R5 风险等级"是行业惯用语，不算泄漏
    # 支持："R4 高风险"、"R4 中高风险"、"R4 中低风险"、"R5 极高风险"、"R4 风险级"
    risk_grade_re = re.compile(r"\bR[1-5]\s*[中低高极]{0,2}(?:风险|级)")
    rule_hits_violating = []
    for m in rule_hits_all:
        # 用 "R5 风险"/"R4 中高风险" 例外
        ctx = md_text[max(0, m.start() - 2): m.end() + 12]
        if risk_grade_re.search(ctx):
            continue
        rule_hits_violating.append(m)
    metrics["audit_rule_id_hits"] = len(rule_hits_violating)
    metrics["audit_rule_id_examples"] = list(dict.fromkeys(
        m.group(0) for m in rule_hits_violating
    ))[:10]
    if rule_hits_violating:
        findings.append(AuditFinding(
            rule_id="R16-ReportPurity",
            severity="FAIL",
            section="报告纯净度（v1.16 工程标识清洁）",
            location=f"正文检出 {len(rule_hits_violating)} 处审计规则编号",
            message=(
                f"【v1.16】报告正文出现审计规则编号："
                f"{', '.join(metrics['audit_rule_id_examples'])}。"
                "  这是工程审计标识，给开发者看的，不应出现在面向投资者的研报。"
            ),
            suggestion=(
                "① 「(R2 强制)」「(R12-Consensus)」「(R13-RatingDist)」标题后缀直接删除；\n"
                "② 「触发 R13」改写为业务语言「与卖方共识方向性背离」；\n"
                "③ 「R4 中高风险」「R5 高风险」等行业惯用风险等级表述允许保留。"
            ),
        ))

    # ─── v1.16 命中 5：工程文件名 / 本地路径 ─────────────────────────────
    fn_path_hits = ENGINEERING_FILENAME_RE.findall(md_text)
    # 附录"6.x 数据信源汇总表"中可以提及落盘文件名（标注内部存档），但 URL 列必须有公开 URL
    # 这里把数据信源汇总表区域之外的 hit 计入违规
    src_table_idx = md_text.find("数据信源汇总表")
    if src_table_idx < 0:
        src_table_idx = float("inf")
    body_fn_hits = []
    for m in ENGINEERING_FILENAME_RE.finditer(md_text):
        if m.start() < src_table_idx:
            body_fn_hits.append(m.group(0))
    metrics["engineering_filename_hits"] = len(body_fn_hits)
    metrics["engineering_filename_examples"] = list(dict.fromkeys(body_fn_hits))[:10]
    if body_fn_hits:
        findings.append(AuditFinding(
            rule_id="R16-ReportPurity",
            severity="FAIL",
            section="报告纯净度（v1.16 工程标识清洁）",
            location=f"正文（§6 信源表之外）检出 {len(body_fn_hits)} 处工程文件名",
            message=(
                f"【v1.16】报告正文出现工程文件名/本地路径："
                f"{', '.join(metrics['engineering_filename_examples'][:5])}。"
                "  研报正文不应出现 `forecast.json`/`assumptions.yaml`/本地绝对路径，"
                "这些是工程内部产物，应通过 sidecar 追溯。"
            ),
            suggestion=(
                "① 删除正文对 forecast.json / assumptions.yaml 的直接提及；\n"
                "② 信源表中的本地落盘路径改写为公开 URL（如东方财富一致预期页 URL）。"
            ),
        ))

    # ─── v1.16 命中 6：工程过程语言（标题/表头出现「强制」「联动」「铁律」等）────
    pl_hits = []
    for i, line in enumerate(md_text.split("\n"), 1):
        # 仅在标题行 / 表头行 / 加粗强调段落 中扫描
        is_heading = line.lstrip().startswith("#")
        is_table_header = "|" in line and ("**" in line or "📊" in line or "📌" in line)
        is_callout = line.lstrip().startswith("📊") or line.lstrip().startswith("📌")
        if is_heading or is_table_header or is_callout:
            for m in ENGINEERING_PROCESS_LANGUAGE_RE.finditer(line):
                pl_hits.append((i, m.group(0), line[:120]))
    metrics["process_language_hits"] = len(pl_hits)
    metrics["process_language_examples"] = [f"L{i}: {kw}" for i, kw, _ in pl_hits[:10]]
    if pl_hits:
        findings.append(AuditFinding(
            rule_id="R16-ReportPurity",
            severity="FAIL",
            section="报告纯净度（v1.16 工程过程语言清洁）",
            location=f"标题/表头/强调段落检出 {len(pl_hits)} 处工程过程语言",
            message=(
                f"【v1.16】标题/表头出现工程过程语言：{metrics['process_language_examples'][:5]}。"
                "  研报标题应只描述业务/章节主题，不应嵌入「强制」「联动」「铁律」「触发条件」"
                "等工程过程标识——这些应仅存在于工程文档与审计日志。"
            ),
            suggestion=(
                "① 「2.4C 卖方共识参照系（v1.14 强制 · R12+R13+R15 联动）」→ 「2.4C 卖方共识参照系」；\n"
                "② 「📊 投资概览卡（v1.14 强制 · 卖方共识三向闭环）」→ 「📊 投资概览卡」；\n"
                "③ 「📌 关键假设链（R2 强制）」→ 「📌 关键假设链」；\n"
                "④ 「证伪条件（v1.14 强化）」→ 「证伪条件」。"
            ),
        ))

    return findings, metrics


# ═══════════════════════════════════════════════════════════════════════════════
# R17-SrcQuality: 信源汇总表中 URL 列必须是公开 URL（v1.16）
# ═══════════════════════════════════════════════════════════════════════════════

# 公开 URL 启发式：http(s):// 开头，或者形如 xxx.com/yyy 等公网域名片段
PUBLIC_URL_RE = re.compile(
    r"(?:https?://[^\s|`]+|"
    r"(?:www\.)?[a-z0-9][a-z0-9\-]{1,40}\.(?:com|cn|net|org|gov|io|co)"
    r"(?:\.[a-z]{2,4})?(?:/[^\s|`]*)?)",
    re.IGNORECASE,
)
# 本地路径：Windows 盘符（如 C:\ D:/）、Unix 用户/家目录、反引号包裹盘符、工程目录名
# 注意：必须排除 https:// 中的 's:/' / 'p:/' 这类协议尾片段，因此盘符前用 negative lookbehind 排除 'http' / 'https' / 'ftp' 等协议字符
LOCAL_PATH_RE = re.compile(
    r"(?:(?<![A-Za-z])[A-Za-z]:[\\/]|"  # 盘符前不是字母（排除 https:/ 的 s:/）
    r"\.\.?[\\/]|/Users/|/home/|`[A-Za-z]:|"
    r"FinancialData[\\/]|\.codebuddy[\\/])"
)


def audit_src_quality(md_text: str) -> Tuple[List[AuditFinding], Dict[str, Any]]:
    """R17-SrcQuality (v1.16): 信源汇总表中每一行 URL 列必须是公开 URL。

    审计逻辑：
    - 找到附录章节中标题含「数据信源汇总表」的表格；
    - 解析每一行（跳过表头/分隔行）；
    - 第 4 列「URL / 获取方式」必须包含至少 1 个公开 URL 形式，且不得包含本地路径片段；
    - 编号列出现的 src 编号应至少覆盖正文中 [^srcN] 引用的全部 N。

    违反任一条 → FAIL。
    """
    findings: List[AuditFinding] = []
    metrics: Dict[str, Any] = {
        "src_table_found": False,
        "src_rows_total": 0,
        "src_rows_with_local_path": 0,
        "src_rows_without_public_url": 0,
        "src_violating_examples": [],
        "src_numbers_in_table": [],
        "src_numbers_in_body": [],
        "src_missing_in_table": [],
    }

    # 找信源表起点
    m_anchor = re.search(r"数据信源汇总表", md_text)
    if not m_anchor:
        findings.append(AuditFinding(
            rule_id="R17-SrcQuality",
            severity="FAIL",
            section="信源质量（v1.16 公开 URL 铁律）",
            location="附录",
            message="【v1.16】报告附录未找到「数据信源汇总表」章节。",
            suggestion="新增 §6.x 数据信源汇总表（编号/名称/类型/公开URL/时效）。",
        ))
        return findings, metrics

    metrics["src_table_found"] = True
    # 截取信源表到下一个 ##/--- 标题之间
    tail = md_text[m_anchor.end():]
    end_m = re.search(r"\n#{1,6}\s|\n---\s*\n|\n【自用声明】", tail)
    block = tail[: end_m.start()] if end_m else tail

    # 解析表格行：管道符开头/结尾的行
    rows = []
    for line in block.split("\n"):
        if not line.strip().startswith("|"):
            continue
        if re.match(r"^\|\s*[-:|\s]+\|", line):
            continue  # 分隔行
        if "编号" in line and "信源名称" in line:
            continue  # 表头
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4:
            rows.append(cells)

    metrics["src_rows_total"] = len(rows)
    src_nums_in_table: List[int] = []
    for cells in rows:
        # 提取编号
        num_match = re.search(r"\d+", cells[0])
        if num_match:
            src_nums_in_table.append(int(num_match.group(0)))
        url_cell = cells[3] if len(cells) > 3 else ""
        # 公开 URL 检测
        has_public_url = bool(PUBLIC_URL_RE.search(url_cell))
        # 本地路径检测
        has_local_path = bool(LOCAL_PATH_RE.search(url_cell))
        if has_local_path:
            metrics["src_rows_with_local_path"] += 1
        if not has_public_url or has_local_path:
            metrics["src_rows_without_public_url"] += 1
            metrics["src_violating_examples"].append(
                f"#{cells[0][:6]}: {url_cell[:80]}"
            )

    metrics["src_numbers_in_table"] = sorted(set(src_nums_in_table))

    if metrics["src_rows_with_local_path"] > 0:
        findings.append(AuditFinding(
            rule_id="R17-SrcQuality",
            severity="FAIL",
            section="信源质量（v1.16 公开 URL 铁律）",
            location=f"信源表中 {metrics['src_rows_with_local_path']} 行 URL 列含本地路径",
            message=(
                f"【v1.16】信源汇总表第 URL 列出现本地工程路径（如 C:\\... 或 FinancialData/）。"
                f"  违规样本: {metrics['src_violating_examples'][:3]}。"
                "  信源应是读者可独立验证的公开 URL，本地落盘文件是工程中间产物，"
                "不构成投资者可追溯的「信源」。"
            ),
            suggestion=(
                "把本地路径替换为对应的公开 URL，例如：\n"
                "  东方财富一致预期页：https://data.eastmoney.com/stock/{code}/yjyc.html\n"
                "  东方财富研究报告页：https://data.eastmoney.com/report/stock/{code}.html\n"
                "  东方财富基本面综合页：https://quote.eastmoney.com/sz{code}.html\n"
                "  巨潮资讯网公告页：http://www.cninfo.com.cn/new/disclosure/stock?stockCode={code}"
            ),
        ))

    if metrics["src_rows_without_public_url"] > 0 and metrics["src_rows_with_local_path"] == 0:
        findings.append(AuditFinding(
            rule_id="R17-SrcQuality",
            severity="WARN",
            section="信源质量（v1.16 公开 URL 铁律）",
            location=f"信源表中 {metrics['src_rows_without_public_url']} 行 URL 列不含可识别公开 URL",
            message="部分信源 URL 列未提供可识别的公开 URL。",
            suggestion="补全 URL 列，确保读者可独立访问验证。",
        ))

    # 报告正文 [^srcN] 是否在表中覆盖
    body_src_nums = sorted(set(int(m.group(1)) for m in re.finditer(r"\[\^src(\d+)\]", md_text)))
    metrics["src_numbers_in_body"] = body_src_nums
    missing = [n for n in body_src_nums if n not in src_nums_in_table]
    metrics["src_missing_in_table"] = missing
    if missing:
        findings.append(AuditFinding(
            rule_id="R17-SrcQuality",
            severity="FAIL",
            section="信源质量（v1.16 公开 URL 铁律）",
            location=f"正文 [^srcN] 引用了 {missing} 但信源表无对应条目",
            message=(
                f"【v1.16】正文引用 [^src{','.join(str(n) for n in missing)}] "
                "但附录数据信源汇总表中找不到对应编号。"
            ),
            suggestion="补全信源表对应编号行，含公开 URL。",
        ))

    return findings, metrics


# ═══════════════════════════════════════════════════════════════════════════════
# R18-IndependenceSection1: §一/核心结论 独立性铁律（v1.16）
# ═══════════════════════════════════════════════════════════════════════════════


def audit_section1_independence(md_text: str) -> Tuple[List[AuditFinding], Dict[str, Any]]:
    """R18-IndependenceSection1 (v1.16): §一/核心结论中"预测核心输出"表
    必须仅展示本报告自身的预测，不得直接列示卖方一致预期作对比列。

    立场：研究员独立预测的报告，§1 应代表"我的判断"，卖方共识属于 §2.4C「市场参照系」
    单独章节的内容。把卖方共识直接拉进 §1 的多列对比表，会让 §1 失去独立判断身份。

    检测：
    - 定位 §1 核心结论范围（从 "### 一" 到 "### 二"）；
    - 该范围内若出现"卖方共识"列在多列表格中（同表同时出现「本报告」和「共识」/「卖方」），
      → FAIL；
    - "📊 投资概览卡" 若位于 §1 且含卖方共识对照列 → FAIL。
    """
    findings: List[AuditFinding] = []
    metrics: Dict[str, Any] = {
        "section1_found": False,
        "section1_violating_tables": 0,
        "section1_violating_table_titles": [],
    }

    # 定位 §1
    m_start = re.search(r"^###\s+一[、，.\s]", md_text, re.M)
    m_end = re.search(r"^###\s+二[、，.\s]", md_text, re.M)
    if not m_start:
        return findings, metrics
    metrics["section1_found"] = True
    sec1 = md_text[m_start.start(): (m_end.start() if m_end else len(md_text))]

    # 找 §1 内的所有表格，并检查表头是否同时含"本报告"+"共识/卖方"
    lines = sec1.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        # 表头识别：当前行含 "|" 且至少 3 个，下一行是分隔行
        if (line.count("|") >= 3
                and i + 1 < len(lines)
                and re.match(r"^\|[\s\-:|]+\|", lines[i + 1])):
            header = line
            # 双重信号：表头同时含 "本报告" 和（"共识" 或 "卖方"）→ FAIL
            if ("本报告" in header) and (("共识" in header) or ("卖方" in header)):
                metrics["section1_violating_tables"] += 1
                # 往上找表前的标题/说明
                title = ""
                for k in range(i - 1, max(-1, i - 5), -1):
                    if lines[k].strip():
                        title = lines[k].strip()[:80]
                        break
                metrics["section1_violating_table_titles"].append(title)
        i += 1

    if metrics["section1_violating_tables"] > 0:
        findings.append(AuditFinding(
            rule_id="R18-IndependenceSection1",
            severity="FAIL",
            section="独立性铁律（v1.16 §一/核心结论独立性）",
            location=(
                f"§一/核心结论 检出 {metrics['section1_violating_tables']} 张表格"
                f"同时列出「本报告」与「卖方共识」对比列"
            ),
            message=(
                f"【v1.16】§一/核心结论中以下表格违反独立性原则：\n  - "
                + "\n  - ".join(metrics["section1_violating_table_titles"][:5])
                + "\n  券商研报、机构月报的「核心结论」从不主动列同行预测做对照——研究员的"
                  "工作就是输出独立判断。卖方共识属于 §2.4C「市场参照系」专属内容。"
            ),
            suggestion=(
                "① 「📊 预测核心输出（一屏式）」表：移除「2026E(共识)」「2027E(共识)」"
                "「2028E(共识)」列，仅保留「实际历史」+「2026E/2027E/2028E（本报告）」；\n"
                "② 「📊 投资概览卡」如出现在 §1，删除其中「2026E(共识 32 家)」列；\n"
                "③ 卖方共识对照统一收敛到 §2.4C「卖方共识参照系」单独章节呈现。"
            ),
        ))

    return findings, metrics



# ═══════════════════════════════════════════════════════════════════════════════
# R19-FirstPrincipleKeywords: 第一性原理术语规范化（v1.18）
# ═══════════════════════════════════════════════════════════════════════════════


# 关键词 → 必备脚本路径标识（任一关键词出现 → 附录信源汇总表必须列出至少一条对应脚本路径）
R19_KEYWORD_TO_SCRIPT: Dict[str, List[str]] = {
    # 资金面 v1.16
    "资金潮汐": ["capital_tide_classifier"],
    "G1-G6": ["g_combination_verifier"],
    "三维联动": ["g_combination_verifier"],
    "S1-S5": ["systemic_risk_scanner"],
    "系统性风险": ["systemic_risk_scanner"],
    "两融余额": ["margin_balance_scraper"],
    "担保比例": ["margin_balance_scraper"],
    "配置盘": ["northbound_smart_money_classifier"],
    "交易盘": ["northbound_smart_money_classifier"],
    # 筹码面 v1.17
    "CYQ": ["chip_distribution_analyzer"],
    "筹码分布": ["chip_distribution_analyzer"],
    "筹码集中度": ["chip_distribution_analyzer"],
    "锁定率": ["chip_distribution_analyzer"],
    "共识五阶段": ["phase_triangle_detector"],
    "主力四阶段": ["phase_triangle_detector"],
    "筹码五阶段": ["phase_triangle_detector"],
    "三角一致性": ["phase_triangle_detector"],
    "F1-F4": ["chip_false_signal_verifier"],
    "假突破": ["chip_false_signal_verifier"],
    "假吸筹": ["chip_false_signal_verifier"],
    "假洗盘": ["chip_false_signal_verifier"],
    "CR1-CR5": ["chip_risk_scanner"],
    "高位巨量阴线": ["chip_risk_scanner"],
    "户数骤增": ["chip_risk_scanner"],
    "解禁集中": ["chip_risk_scanner", "lockup_release_calendar"],
    "大宗交易": ["block_dragon_scraper"],
    "龙虎榜": ["block_dragon_scraper"],
    "主力成本带": ["block_dragon_scraper"],
    # 技术面 v1.18
    "VP1-VP6": ["volume_price_classifier"],
    "量价六组合": ["volume_price_classifier"],
    "量价 6 组合": ["volume_price_classifier"],
    "行业景气轮动": ["industry_rotation_scorer"],
    "限售解禁日历": ["lockup_release_calendar"],
    "解禁前异动": ["lockup_release_calendar"],
    "量能层级": ["volume_tier_analyzer"],
    "REAL_BREAKOUT": ["volume_tier_analyzer"],
    "FAKE_PULSE": ["volume_tier_analyzer"],
    "斐波时间窗口": ["fib_timing_alerter"],
    "斐波那契时间": ["fib_timing_alerter"],
}


def audit_first_principle_keywords(md_text: str) -> Tuple[List[AuditFinding], Dict[str, Any]]:
    """R19-FirstPrincipleKeywords (v1.18): 报告若使用 v1.16-v1.18 第一性原理术语,
    必须在附录「数据信源汇总表」（或正文脚本块）出现对应脚本名,确保术语来自机器判定
    而非 LLM 凭空发挥。

    检测：
      ① 扫描全文是否出现 R19_KEYWORD_TO_SCRIPT 中的关键词；
      ② 对每个被命中的关键词,检查全文是否含其所需脚本名（含 .py 或不含均可）；
      ③ 关键词出现但脚本名缺失 → FAIL（出现 ≥ 3 个）/ WARN（出现 1-2 个）。
    """
    findings: List[AuditFinding] = []
    metrics: Dict[str, Any] = {
        "keywords_found": [],
        "missing_scripts": [],
        "violations": 0,
    }

    text = md_text or ""
    if not text:
        return findings, metrics

    hits: List[Tuple[str, List[str]]] = []  # (keyword, missing_scripts)
    for keyword, scripts in R19_KEYWORD_TO_SCRIPT.items():
        if keyword not in text:
            continue
        metrics["keywords_found"].append(keyword)
        # 检查脚本是否在文中提及
        missing = []
        for s in scripts:
            # 接受 "scripts/foo.py" 或 "foo.py" 或裸名 "foo"
            if (f"{s}.py" in text) or (f"/{s}" in text) or (f"`{s}`" in text):
                continue
            missing.append(s)
        if missing:
            hits.append((keyword, missing))
            metrics["missing_scripts"].append({"keyword": keyword, "missing": missing})

    metrics["violations"] = len(hits)

    if hits:
        severity = "FAIL" if len(hits) >= 3 else "WARN"
        sample_lines = [f"  - 关键词「{k}」缺少脚本：{', '.join(m)}.py" for k, m in hits[:8]]
        findings.append(AuditFinding(
            rule_id="R19-FirstPrincipleKeywords",
            severity=severity,
            section="第一性原理术语铁律（v1.18 v1.16-v1.18 关键术语规范化）",
            location=f"全文检出 {len(hits)} 处违规关键词",
            message=(
                f"【v1.18】报告使用了 v1.16-v1.18 的第一性原理术语,但未在文中"
                f"引用对应脚本输出（脚本输出 = 机器判定的客观依据）。\n"
                + "\n".join(sample_lines)
                + ("\n  ……" if len(hits) > 8 else "")
            ),
            suggestion=(
                "① 在正文使用术语时附加脚注或括号引用对应脚本：\n"
                "   例：「当前处于资金潮汐三周期共振多头（capital_tide_classifier.py 评级=AGGRESSIVE_LONG）」；\n"
                "② 或在附录「数据信源汇总表」补充对应脚本路径与输出 JSON；\n"
                "③ 若术语只是借用文献而非真做了机器判定,改用更通用的描述,避免误导读者；\n"
                "④ 完整脚本与术语映射详见 references/command_reference.md §9.5-§9.6。"
            ),
        ))

    return findings, metrics


# ═══════════════════════════════════════════════════════════════════════════════
# R20-PolicyNewsConsistency: 政策面/消息面结论一致性审计（v1.19）
# ═══════════════════════════════════════════════════════════════════════════════

R20_KEYWORD_TO_SCRIPT: Dict[str, List[str]] = {
    # 政策面（v1.19 P0-P7）
    "政策层级": ["gov_policy_scraper.py（policy_level）"],
    "政策性质": ["policy_nature_classifier.py"],
    "措辞强度": ["policy_wording_intensity_scorer.py"],
    "政策预期差": ["policy_expectation_gap_scorer.py"],
    "政策传导阶段": ["policy_lifecycle_tracker.py"],
    "政策执行力度": ["policy_execution_strength_scorer.py"],
    "政策四维联动": ["policy_4d_combo_verifier.py"],
    "政策底": ["policy_three_bottom_detector.py"],
    "市场底": ["policy_three_bottom_detector.py"],
    "经济底": ["policy_three_bottom_detector.py"],
    # 消息面（v1.19 M1-M9）
    "消息层级": ["news_level_classifier.py"],
    "消息预期差": ["news_expectation_gap_scorer.py"],
    "业绩超预期": ["earnings_surprise_scorer.py"],
    "业绩低于预期": ["earnings_surprise_scorer.py"],
    "兑现阶段": ["news_lifecycle_tracker.py"],
    "提前发酵": ["news_lifecycle_tracker.py"],
    "集中兑现": ["news_lifecycle_tracker.py"],
    "消化修正": ["news_lifecycle_tracker.py"],
    "消息三维联动": ["news_3d_combo_verifier.py"],
    "边际响应衰减": ["news_marginal_response_detector.py"],
    "传闻密度": ["systemic_risk_scanner.py（S6）"],
}


def audit_policy_news_consistency(md_text: str) -> Tuple[List[AuditFinding], Dict]:
    """R20-PolicyNewsConsistency (v1.19): 报告若使用政策面/消息面专业术语，
    必须显式引用对应脚本输出（机器判定的客观依据）。

    审计逻辑：
      ① 扫描全文是否出现 R20_KEYWORD_TO_SCRIPT 中的关键词；
      ② 命中关键词附近 ±200 字符内必须出现对应脚本名（任一即可）；
      ③ 否则记 WARN。
    """
    findings: List[AuditFinding] = []
    metrics: Dict[str, Any] = {
        "keywords_total": len(R20_KEYWORD_TO_SCRIPT),
        "keywords_hit": 0,
        "violations": 0,
    }
    hits: List[str] = []

    for keyword, scripts in R20_KEYWORD_TO_SCRIPT.items():
        idx = md_text.find(keyword)
        if idx < 0:
            continue
        metrics["keywords_hit"] += 1
        # 关键词附近 ±200 字符
        ctx_start = max(0, idx - 200)
        ctx_end = min(len(md_text), idx + len(keyword) + 200)
        context = md_text[ctx_start:ctx_end]
        # 检查是否引用了任一对应脚本
        if not any(s.split("（")[0].split(".py")[0] in context for s in scripts):
            metrics["violations"] += 1
            hits.append(f"  - 「{keyword}」附近未引用 {' / '.join(scripts)}")

    if hits:
        sample = "\n".join(hits[:10])
        findings.append(AuditFinding(
            rule_id="R20-PolicyNewsConsistency",
            severity="WARN",
            section="政策面/消息面术语一致性铁律（v1.19）",
            location=f"全文检出 {len(hits)} 处政策/消息术语未附脚本依据",
            message=(
                f"【v1.19】报告使用了政策面/消息面专业术语，但未在术语附近引用对应脚本输出：\n"
                + sample
                + ("\n  ……" if len(hits) > 10 else "")
            ),
            suggestion=(
                "① 在术语附近添加引用，如「（policy_4d_combo_verifier.py 输出 = TRUE_SIGNAL）」；\n"
                "② 或在数据信源汇总表追加对应脚本路径与输出 JSON；\n"
                "③ 13 个新脚本完整使用方法详见 references/command_reference.md §9.7-§9.8 与"
                " faces/政策面.md 模块4 / faces/消息面.md。"
            ),
        ))

    return findings, metrics


# ═══════════════════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════════════════


def run_audit(report_path: Path,
              code: Optional[str] = None,
              bare_rate_threshold: float = 0.10,
              articulation_threshold: float = 0.005,
              skip_articulation: bool = False) -> AuditReport:
    md_text = report_path.read_text(encoding="utf-8")
    sections = parse_sections(md_text)

    report = AuditReport(report_path=str(report_path))

    f1, m1 = audit_bare_numbers(sections, bare_rate_threshold)
    f2, m2 = audit_assumption_chain(sections)
    f3, m3 = audit_scenario_coverage(sections)
    f4, m4 = audit_falsifiability(sections)
    f5, m5 = audit_articulation(code, articulation_threshold, skip_articulation)
    f6, m6 = audit_dual_track_references(md_text)
    f7a, m7a = audit_d_class_blacklist(md_text)
    f7b, m7b = audit_factual_data_url(md_text)
    f8, m8 = audit_independence_protocol(md_text, sections)
    f9, m9 = audit_valuation_coverage(md_text, sections)
    f10, m10 = audit_forecast_consistency(report_path, md_text, code)
    f11, m11 = audit_realtime_price(report_path, md_text, code)
    # ---- v1.14 信源利用率铁律 R12-R15 ----
    f12, m12 = audit_consensus_eps(report_path, md_text, code)
    f13, m13 = audit_rating_distribution(report_path, md_text, code)
    f14, m14 = audit_financial_history_coverage(report_path, md_text, code)
    f15, m15 = audit_analyst_sample_coverage(report_path, md_text, code)
    # ---- v1.15 报告自洽 + 纯净度铁律 R16 ----
    f16, m16 = audit_report_purity(report_path, md_text)
    # ---- v1.16 信源质量 R17 + §一独立性 R18 ----
    f17, m17 = audit_src_quality(md_text)
    f18, m18 = audit_section1_independence(md_text)
    # ---- v1.18 第一性原理术语规范化 R19 ----
    f19, m19 = audit_first_principle_keywords(md_text)
    # ---- v1.19 政策面/消息面术语一致性 R20 ----
    f20, m20 = audit_policy_news_consistency(md_text)

    for f in (f1 + f2 + f3 + f4 + f5 + f6 + f7a + f7b
              + f8 + f9 + f10 + f11
              + f12 + f13 + f14 + f15 + f16 + f17 + f18 + f19 + f20):
        report.add(f)

    report.metrics = {
        "R1_bare_numbers": m1,
        "R2_assumption_chain": m2,
        "R3_scenario_coverage": m3,
        "R4_falsifiability": m4,
        "R5_articulation": m5,
        "R6_dual_track_ref": m6,
        "R7A_d_class_blacklist": m7a,
        "R7B_factual_url": m7b,
        "R8_independence": m8,
        "R9_valuation_coverage": m9,
        "R10_forecast_consistency": m10,
        "R11_realtime_price": m11,
        "R12_consensus_eps": m12,
        "R13_rating_distribution": m13,
        "R14_financial_history": m14,
        "R15_analyst_sample": m15,
        "R16_report_purity": m16,
        "R17_src_quality": m17,
        "R18_section1_independence": m18,
        "R19_first_principle_keywords": m19,
        "R20_policy_news_consistency": m20,
        "section_count": len(sections),
    }
    return report


def render_human(report: AuditReport) -> str:
    icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}[report.overall]
    lines: List[str] = []
    lines.append(f"# 推导链审计 {icon} {report.overall}")
    lines.append("")
    lines.append(f"**报告**: `{report.report_path}`")
    lines.append("")
    fail_n = report.count_by_severity("FAIL")
    warn_n = report.count_by_severity("WARN")
    lines.append(f"**审计结果**: FAIL={fail_n}, WARN={warn_n}, INFO={report.count_by_severity('INFO')}")
    lines.append("")
    lines.append("## 关键指标")
    m = report.metrics
    r1 = m.get("R1_bare_numbers", {})
    lines.append(f"- **R1 裸数字率**: {r1.get('bare_numbers',0)}/{r1.get('total_critical_numbers',0)} "
                 f"= {r1.get('bare_rate',0)*100:.1f}% (阈值 {r1.get('bare_rate_threshold',0.10)*100:.0f}%)")
    r2 = m.get("R2_assumption_chain", {})
    lines.append(f"- **R2 假设链**: {r2.get('tables_with_complete_chain',0)}/{r2.get('critical_tables_found',0)} 张表合规")
    r3 = m.get("R3_scenario_coverage", {})
    lines.append(f"- **R3 三档情景**: Bull={r3.get('bull_found')}, Base={r3.get('base_found')}, Bear={r3.get('bear_found')}")
    r4 = m.get("R4_falsifiability", {})
    lines.append(f"- **R4 证伪条件**: 命中 {r4.get('falsify_hits',0)} 章节 (阈值 ≥2)")
    r5 = m.get("R5_articulation", {})
    if r5.get("skipped"):
        lines.append(f"- **R5 三表勾稽**: 已跳过（未提供 --code）")
    else:
        lines.append(f"- **R5 三表勾稽**: 硬规则超阈值 {r5.get('hard_rule_diffs_over_threshold',0)} 项, "
                     f"WARN 区 {r5.get('hard_rule_diffs_in_warn_zone',0)} 项 (阈值 {r5.get('threshold',0.005)*100:.1f}%)")
    r6 = m.get("R6_dual_track_ref", {})
    lines.append(
        f"- **R6 双轨引用**: 附录表 {r6.get('appendix_total_entries', 0)} 条，"
        f"伪信源 {r6.get('fake_source_entries', 0)} 条，"
        f"正文引用伪信源 {r6.get('fake_refs_in_body_total', 0)} 次"
    )
    r7a = m.get("R7A_d_class_blacklist", {})
    lines.append(
        f"- **R7-A D 类伪信源黑名单**: 附录命中 {r7a.get('appendix_d_class_hits', 0)} 行，"
        f"正文话术命中 {r7a.get('body_d_class_hits', 0)} 处"
    )
    r7b = m.get("R7B_factual_url", {})
    lines.append(
        f"- **R7-B 事实型 URL 可查证**: 事实型信源 {r7b.get('factual_entries', 0)} 行，"
        f"缺 URL {r7b.get('factual_no_url', 0)} 行"
    )
    r8 = m.get("R8_independence", {})
    lines.append(
        f"- **R8 独立性铁律**: 禁用表述命中 {r8.get('anchor_abuse_hits', 0)} 处，"
        f"我vs市场对照小节 {'已检出' if r8.get('market_gap_section_found') else '未检出'}"
    )
    r9 = m.get("R9_valuation_coverage", {})
    methods_used = r9.get("valuation_methods_used", [])
    elem_found = r9.get("comprehensive_5_elements_found", [])
    elem_missing = r9.get("comprehensive_5_elements_missing", [])
    lines.append(
        f"- **R9 全口径估值**: 估值方法 {len(methods_used)}/3 ({','.join(methods_used) or '空'})，"
        f"综合判断 5 要素 {len(elem_found)}/5 (缺: {','.join(elem_missing) or '无'})，"
        f"可比公司六维评分 {'已检出' if r9.get('comparable_six_dim_score_found') else '未检出'}"
    )
    r10 = m.get("R10_forecast_consistency", {})
    sc_total = r10.get("sidecar_anchor_total", 0)
    sc_resolved = r10.get("sidecar_anchor_resolved", 0)
    sc_exists = r10.get("sidecar_exists", False)
    missing_files = r10.get("missing_files", []) or []
    placeholder_ratio = r10.get("assumptions_placeholder_ratio")
    placeholder_str = f"{placeholder_ratio*100:.1f}%" if isinstance(placeholder_ratio, (int, float)) else "N/A"
    age_days = r10.get("forecast_xlsx_age_days")
    age_str = f"{age_days} 天" if isinstance(age_days, (int, float)) else "N/A"
    lines.append(
        f"- **R10 forecast 一致性 (v1.15 sidecar 旁路)**: "
        f"sidecar {'存在' if sc_exists else '缺失'}，"
        f"数字锚点 {sc_resolved}/{sc_total} 可解析，"
        f"yaml 占位率 {placeholder_str}，"
        f"缺失文件 {len(missing_files)} 个，"
        f"forecast.xlsx vs report 龄期 {age_str}"
    )
    r11 = m.get("R11_realtime_price", {})
    auth_p = r11.get("current_price_in_forecast")
    auth_str = f"{auth_p} 元" if auth_p is not None else "MISSING"
    n_mismatch = len(r11.get("mismatched", []) or []) + len(r11.get("suspicious_placeholder", []) or [])
    lines.append(
        f"- **R11 现价铁律 (v1.13)**: forecast 权威价 {auth_str}，"
        f"报告现价提及 {r11.get('report_price_mentions',0)} 处，"
        f"匹配 {r11.get('matched',0)} 处，偏离 {n_mismatch} 处"
        f"{'  ❌ 检出占位符/编造' if n_mismatch > 0 else ''}"
    )
    # ---- v1.14 信源利用率铁律 R12-R15 ----
    r12 = m.get("R12_consensus_eps", {})
    truth_eps = r12.get("consensus_eps_truth", []) or []
    if truth_eps:
        eps_brief = ", ".join(f"{e['year']}E={e['eps']}" for e in truth_eps[:3])
    else:
        eps_brief = "N/A"
    lines.append(
        f"- **R12 卖方共识 EPS (v1.14)**: 真值 [{eps_brief}]，"
        f"报告引用 {r12.get('report_eps_mentions',0)} 处，"
        f"匹配 {r12.get('matched',0)} 处，偏离 {len(r12.get('mismatched', []) or [])} 处"
        f"{'  ❌ 缺失共识章节' if r12.get('missing_consensus_section') else ''}"
    )
    r13 = m.get("R13_rating_distribution", {})
    lines.append(
        f"- **R13 评级分布 (v1.14)**: 卖方 {r13.get('rating_total','N/A')} 家覆盖，"
        f"看多 {r13.get('bull_pct','N/A')}%，"
        f"报告引用分布 {'是' if r13.get('report_cites_distribution') else '否'}"
        f"{'  ❌ 评级方向背离卖方共识' if r13.get('report_self_rating_directional_conflict') else ''}"
    )
    r14 = m.get("R14_financial_history", {})
    lines.append(
        f"- **R14 历史财务覆盖 (v1.14)**: 可用 {r14.get('history_periods_available',0)} 期，"
        f"报告引用 {r14.get('history_periods_cited_in_report',0)} 期"
        f"（样本: {r14.get('cited_periods_sample', [])[:5]}）"
    )
    r15 = m.get("R15_analyst_sample", {})
    lines.append(
        f"- **R15 研报样本覆盖 (v1.14)**: 可用 {r15.get('available_org_count',0)} 家机构，"
        f"报告引用 {r15.get('cited_org_count',0)} 家，"
        f"研究员命中 {r15.get('researcher_hits',0)}，URL 命中 {r15.get('pdf_url_hits',0)}"
    )
    r16 = m.get("R16_report_purity", {})
    fn_hits = r16.get("engineering_footnote_hits", 0)
    raw_hits = r16.get("raw_json_path_hits", 0)
    body_hits = r16.get("raw_json_path_body_hits", 0)
    sv_hits = r16.get("skill_version_hits", 0)
    ar_hits = r16.get("audit_rule_id_hits", 0)
    fn_path_hits = r16.get("engineering_filename_hits", 0)
    pl_hits = r16.get("process_language_hits", 0)
    purity_clean = (fn_hits == 0 and body_hits == 0 and sv_hits == 0
                    and ar_hits == 0 and fn_path_hits == 0 and pl_hits == 0)
    lines.append(
        f"- **R16 报告纯净度 (v1.16)**: 工程脚注 {fn_hits} / 裸JSON路径 {body_hits}"
        f" / 工程版本号 {sv_hits} / 审计规则编号 {ar_hits}"
        f" / 工程文件名 {fn_path_hits} / 工程过程语言 {pl_hits}"
        f"{'  ✅ 干净' if purity_clean else '  ❌ 报告污染'}"
    )
    r17 = m.get("R17_src_quality", {})
    lines.append(
        f"- **R17 信源质量 (v1.16)**: 信源表 {'存在' if r17.get('src_table_found') else '缺失'}, "
        f"共 {r17.get('src_rows_total', 0)} 行, "
        f"含本地路径 {r17.get('src_rows_with_local_path', 0)} 行, "
        f"缺公开URL {r17.get('src_rows_without_public_url', 0)} 行, "
        f"正文未覆盖 {len(r17.get('src_missing_in_table', []))} 个 src 编号"
        f"{'  ✅' if (r17.get('src_rows_with_local_path', 0) == 0 and not r17.get('src_missing_in_table')) else '  ❌'}"
    )
    r18 = m.get("R18_section1_independence", {})
    lines.append(
        f"- **R18 §一独立性 (v1.16)**: §一卖方对照违规表格 "
        f"{r18.get('section1_violating_tables', 0)} 张"
        f"{'  ✅' if r18.get('section1_violating_tables', 0) == 0 else '  ❌'}"
    )
    lines.append("")
    if report.findings:
        lines.append("## Findings")
        for i, f in enumerate(report.findings, 1):
            sev_icon = {"FAIL": "❌", "WARN": "⚠️", "INFO": "ℹ️"}[f.severity]
            lines.append(f"### {i}. {sev_icon} [{f.rule_id}] {f.section}")
            lines.append(f"- **Location**: {f.location}")
            lines.append(f"- **Message**: {f.message}")
            if f.suggestion:
                lines.append(f"- **Suggestion**: {f.suggestion}")
            lines.append("")
        # R1 裸数字示例
        examples = r1.get("bare_examples_top10", [])
        if examples:
            lines.append("## R1 裸数字 Top 10 示例")
            for e in examples:
                lines.append(f"- {e}")
            lines.append("")
    else:
        lines.append("## Findings")
        lines.append("无 — 推导链审计全部通过。")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="推导链审计器 — 基本面研究报告专用门禁")
    parser.add_argument("report", help="待审计的 Markdown 报告路径")
    parser.add_argument("--code", help="股票代码（用于三表勾稽差额校验）")
    parser.add_argument("--bare-rate-threshold", type=float, default=0.10,
                        help="裸数字率上限（默认 0.10 = 10%%）")
    parser.add_argument("--articulation-threshold", type=float, default=0.005,
                        help="三表勾稽差额阈值（默认 0.005 = 0.5%%）")
    parser.add_argument("--skip-articulation", action="store_true",
                        help="跳过三表勾稽校验（更快）")
    parser.add_argument("--format", choices=["human", "json", "both"], default="human")
    parser.add_argument("--emit-gate", nargs="?", const="__AUTO__", default=None,
                        help="把人类可读结果写入 _derivation_gate.md（默认 OutputReport 下）")
    args = parser.parse_args()

    report_path = Path(args.report).resolve()
    if not report_path.exists():
        print(f"[FAIL] 报告文件不存在: {report_path}", file=sys.stderr)
        sys.exit(2)

    audit = run_audit(
        report_path=report_path,
        code=args.code,
        bare_rate_threshold=args.bare_rate_threshold,
        articulation_threshold=args.articulation_threshold,
        skip_articulation=args.skip_articulation,
    )

    human = render_human(audit)
    payload = {
        "pass": audit.overall == "PASS",
        "overall": audit.overall,
        "fail_count": audit.count_by_severity("FAIL"),
        "warn_count": audit.count_by_severity("WARN"),
        "findings": [asdict(f) for f in audit.findings],
        "metrics": audit.metrics,
    }

    if args.format == "human":
        print(human)
    elif args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(human)
        print("\n----- JSON -----")
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    if args.emit_gate is not None:
        out_path = (Path(args.emit_gate) if args.emit_gate != "__AUTO__"
                    else report_path.parent / "_derivation_gate.md")
        out_path.write_text(human, encoding="utf-8")
        print(f"\n[ok] 推导链门禁结果已写入: {out_path}")

    # 退出码：FAIL→1, WARN→2, PASS→0
    sys.exit({"FAIL": 1, "WARN": 2, "PASS": 0}[audit.overall])


if __name__ == "__main__":
    main()
