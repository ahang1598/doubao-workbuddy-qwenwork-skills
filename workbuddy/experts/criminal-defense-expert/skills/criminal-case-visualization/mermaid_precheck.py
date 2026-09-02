#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mermaid_precheck.py — Mermaid 产物预检脚本（v3.0.0 扩展）

用法：
  python mermaid_precheck.py <html_file> [--json] [--strict]

退出码：
  0 — 全部通过（warning 可有可无）
  1 — 存在 block 级违规（产物不可交付，必须修复）
  2 — 仅 warning（建议修复但可交付）

校验规则（共 16 条，对应 chart-specifications.md §0/§3/§6/§7/§8/§9）：
  块级（block，阻断）：
    R1  节点 ID 不含中文/空格/特殊字符
    R3  箭头语法错误
    R4  style 指令引用未定义 ID
    R5  style 颜色值含 var(--xxx) CSS 变量
    R6  gantt 缺 dateFormat
    R7  gantt 任务名含 〔〕（） 特殊符号
    R8  gantt 单图跨度 > 12 个月（应拆为双图表）
    R9  pie 数值非整数
    R10 quadrantChart quadrant 标签非英文
    R12 pie 类别 > 8 或占比 < 5% 未合并
    R13 timeline section 标题含特殊符号
    R14 [v3.0.0] flow/LR/TD 节点数 > 12
    R15 [v3.0.0] gantt section 数 > 2
    R16 [v3.0.0] gantt 单 section 任务+里程碑 > 10

  警告（warning，不阻断）：
    R2  中文标签未用双引号包裹
    R11 timeline 单条标签 > 10 字符
"""

import re
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime, date

# ════════════════════════════════════════════════════════════════════
# 1. 提取 <div class="mermaid"> 块
# ════════════════════════════════════════════════════════════════════

MERMAID_BLOCK_RE = re.compile(
    r'<div class="mermaid">(.*?)</div>',
    re.DOTALL
)

# ════════════════════════════════════════════════════════════════════
# 2. 工具函数
# ════════════════════════════════════════════════════════════════════

def parse_gantt_dates(code: str) -> Tuple[str, str, int]:
    """提取 gantt 第一条任务/里程碑的起止日期，返回 (date_from, date_to, days)"""
    dates = []
    # 任务行: 任务名 :id, 2024-03-22, 37d
    for m in re.finditer(r',\s*(\d{4}-\d{2}-\d{2}),\s*(\d+)d', code):
        dates.append((m.group(1), int(m.group(2))))
    if not dates:
        return ("", "", 0)
    # 按起始日期推算所有结束日期
    starts = []
    cur = None
    for m in re.finditer(r',\s*(\d{4}-\d{2}-\d{2}),\s*(\d+)d', code):
        d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        days = int(m.group(2))
        starts.append(d)
        cur = d
    if not starts:
        return ("", "", 0)
    last_end = max(d for d in starts)
    first = min(d for d in starts)
    span_days = (max(d for d, n in [(starts[i] + __import__('datetime').timedelta(days=int(re.findall(r', (\d+)d', code)[i])), 0) for i in range(len(starts))] for d in [starts[i]]).max() - first).days
    return (first.isoformat(), last_end.isoformat(), span_days)


def is_chinese(s: str) -> bool:
    return bool(re.search(r'[\u4e00-\u9fa5]', s))


def is_english_only(s: str) -> bool:
    """判定字符串是否只含英文/空格/数字"""
    return bool(re.match(r'^[A-Za-z0-9 \-><]+$', s.strip()))


# ════════════════════════════════════════════════════════════════════
# 3. 16 条校验规则
# ════════════════════════════════════════════════════════════════════

def check_r1_node_id(code: str) -> List[str]:
    """R1: 节点 ID 不含中文/空格/特殊字符"""
    issues = []
    # graph 模式: 提取 "ID[" 或 "ID{" 或 "ID(" 开头的 ID
    for m in re.finditer(r'^\s*([A-Za-z0-9_一-鿿]+)\s*[\[\{\(]', code, re.MULTILINE):
        node_id = m.group(1)
        if is_chinese(node_id) or ' ' in node_id:
            issues.append(f"节点ID含中文或空格: `{node_id}`")
    return issues


def check_r2_quote(code: str) -> List[str]:
    """R2: 中文标签未用双引号包裹（warning）"""
    issues = []
    for m in re.finditer(r'\[\s*([^\]\n]*[\u4e00-\u9fa5][^\]\n]*)\s*\]', code):
        label = m.group(1)
        # 检查是否被双引号包裹
        if not (label.strip().startswith('"') and label.strip().endswith('"')):
            issues.append(f"中文标签未用双引号包裹: `{label[:30]}`")
    return issues


def check_r3_arrow(code: str) -> List[str]:
    """R3: 箭头语法错误"""
    issues = []
    # 检查  -- 或  -> 单字符错误（应为 -->）
    # 排除注释行
    for m in re.finditer(r'^\s*[^%\n]*\s-\s->', code, re.MULTILINE):
        issues.append(f"箭头语法错误（疑似 - -> 单字符）: `{m.group(0).strip()[:50]}`")
    return issues


def check_r4_style_id(code: str) -> List[str]:
    """R4: style 指令引用未定义 ID"""
    issues = []
    is_gantt = code.lower().lstrip().startswith('gantt')
    # 提取所有已定义节点 ID
    defined_ids = set()
    # 1) graph 模式：行首 ID 修饰符：ID[...], ID{...}, ID(...)
    for m in re.finditer(r'^\s*([A-Za-z][A-Za-z0-9_]*)\s*[\[\{\(]', code, re.MULTILINE):
        defined_ids.add(m.group(1))
    # 1b) graph 链式箭头右侧 ID：`--> B{...}` 或 `-->|"text"| C[...]`
    for m in re.finditer(r'-->\s*(?:\|\s*"?[^"|]*"?\s*\|\s*)?([A-Za-z][A-Za-z0-9_]*)\s*[\[\{\(]', code):
        defined_ids.add(m.group(1))
    # 1c) graph 链式箭头纯 ID：`A --> B --> C`（无修饰符，纯串联）
    for m in re.finditer(r'-->\s*([A-Za-z][A-Za-z0-9_]*)\s*(?:-->|$|\n)', code, re.MULTILINE):
        defined_ids.add(m.group(1))
    # 2) gantt 模式: 任务/里程碑 ID 出现在 :done, a1, ... 或 :milestone, m1, ...
    if is_gantt:
        for m in re.finditer(r':\s*(?:done|active|crit)?,?\s*(?:milestone,)?\s*([A-Za-z][A-Za-z0-9_]*)\s*,', code):
            defined_ids.add(m.group(1))
    # 提取 style 指令的 ID
    for m in re.finditer(r'^\s*style\s+([A-Za-z][A-Za-z0-9_]*)\s', code, re.MULTILINE):
        sid = m.group(1)
        if sid not in defined_ids:
            issues.append(f"style 引用未定义节点ID: `{sid}`")
    return issues


def check_r5_style_var(code: str) -> List[str]:
    """R5: style 颜色值含 var(--xxx)"""
    issues = []
    for m in re.finditer(r'var\(--[\w-]+\)', code):
        issues.append(f"style 含 CSS 变量（Mermaid 不支持）: `{m.group(0)}`")
    return issues


def check_r6_gantt_dateformat(code: str) -> List[str]:
    """R6: gantt 缺 dateFormat"""
    issues = []
    if 'gantt' not in code.lower():
        return issues
    if not re.search(r'^\s*dateFormat\s+', code, re.MULTILINE | re.IGNORECASE):
        issues.append("gantt 缺 dateFormat 指令")
    return issues


def check_r7_gantt_taskname(code: str) -> List[str]:
    """R7: gantt 任务名含 〔〕（） 特殊符号"""
    issues = []
    if 'gantt' not in code.lower():
        return issues
    for m in re.finditer(r'^\s*([^:\n]+?)\s*:\s*(?:done|active|crit)?,?\s*(?:milestone,)?\s*\w+,\s*\d{4}-\d{2}-\d{2}', code, re.MULTILINE):
        task_name = m.group(1).strip()
        if re.search(r'[〔〕（）]', task_name):
            issues.append(f"gantt 任务名含特殊符号 〔〕（）: `{task_name}`")
    return issues


def check_r8_gantt_span(code: str) -> List[str]:
    """R8: gantt 单图跨度 > 12 个月"""
    issues = []
    if 'gantt' not in code.lower():
        return issues
    # 提取所有日期与天数
    tasks = []
    for m in re.finditer(r',\s*(\d{4}-\d{2}-\d{2}),\s*(\d+)d', code):
        try:
            start = datetime.strptime(m.group(1), "%Y-%m-%d").date()
            days = int(m.group(2))
            tasks.append((start, days, start.toordinal() + days))
        except ValueError:
            pass
    if not tasks:
        return issues
    min_start = min(t[0] for t in tasks)
    max_end = date.fromordinal(max(t[2] for t in tasks))
    span_days = (max_end - min_start).days
    if span_days <= 365:
        return issues
    # v2.3.1 豁免：长档刑期执行段（图B，标题/任务名含"刑期"）属合法拆分
    if any(kw in code for kw in ['刑期执行', '图B', '有期徒刑']):
        return issues
    issues.append(f"gantt 单图跨度 {span_days} 天（> 12 个月），应按 §3.0.1 拆为双图表（图A强制措施+图B刑期）")
    return issues


def check_r9_pie_integer(code: str) -> List[str]:
    """R9: pie 数值非整数"""
    issues = []
    if not re.search(r'^\s*pie\b', code, re.MULTILINE | re.IGNORECASE):
        return issues
    for m in re.finditer(r':\s*(\d+\.\d+)', code):
        issues.append(f"pie 数值含小数（Mermaid 仅支持整数）: `{m.group(1)}`")
    return issues


def check_r10_quadrant_lang(code: str) -> List[str]:
    """R10: quadrantChart quadrant 标签非英文"""
    issues = []
    if 'quadrantChart' not in code:
        return issues
    for m in re.finditer(r'quadrant-([1-4])\s+(.+)', code):
        label = m.group(2).strip()
        if is_chinese(label):
            issues.append(f"quadrant-{m.group(1)} 含中文标签: `{label}`，应改为英文（Priority Action/Key Breakthrough/Auxiliary Argument/Cautious Use）")
        # 允许英中混合: 接受英文（含空格）或纯英文
        if not re.match(r'^[A-Za-z][A-Za-z ]*$', label):
            if not is_chinese(label):  # 排除纯中文（已上抛）
                issues.append(f"quadrant-{m.group(1)} 标签含特殊字符: `{label}`")
    # 同样检查 x-axis / y-axis
    for m in re.finditer(r'(x-axis|y-axis)\s+(.+)', code):
        label = m.group(2).strip()
        if is_chinese(label):
            issues.append(f"{m.group(1)} 含中文标签: `{label}`，应改为英文（Low Feasibility --> High Feasibility）")
    return issues


def check_r11_timeline_label(code: str) -> List[str]:
    """R11: timeline 单条标签 > 10 字符（warning）"""
    issues = []
    if not re.search(r'^\s*timeline\b', code, re.MULTILINE | re.IGNORECASE):
        return issues
    for m in re.finditer(r'^\s*([^：:\n]+?)\s*[:：]\s*([^\n]+)', code, re.MULTILINE):
        left = m.group(1).strip()
        right = m.group(2).strip()
        if left in ('title', 'section'):
            continue
        if left.startswith('section'):
            continue
        # 单条事件: 时间: 事件
        if len(left) > 6:
            issues.append(f"timeline 时间标签超 6 字符: `{left}`")
        if len(right) > 12:
            issues.append(f"timeline 事件描述超 12 字符: `{right}`")
    return issues


def check_r12_pie_merge(code: str) -> List[str]:
    """R12: pie 类别 > 8 或占比 < 5% 未合并"""
    issues = []
    if not re.search(r'^\s*pie\b', code, re.MULTILINE | re.IGNORECASE):
        return issues
    entries = []
    for m in re.finditer(r'"([^"]+)"\s*:\s*(\d+(?:\.\d+)?)', code):
        entries.append((m.group(1), float(m.group(2))))
    if len(entries) > 8:
        issues.append(f"pie 类别数 {len(entries)} > 8，应按 §8.0.2 合并到 '其他'")
    total = sum(v for _, v in entries)
    if total > 0:
        for label, val in entries:
            pct = val / total * 100
            if pct < 5 and '其他' not in label:
                issues.append(f"pie 类别 `{label}` 占比 {pct:.1f}% < 5%，应合并到 '其他'")
    return issues


def check_r13_timeline_section(code: str) -> List[str]:
    """R13: timeline section 标题含特殊符号"""
    issues = []
    if not re.search(r'^\s*timeline\b', code, re.MULTILINE | re.IGNORECASE):
        return issues
    for m in re.finditer(r'^\s*section\s+(.+)', code, re.MULTILINE):
        section_title = m.group(1).strip()
        if re.search(r'[·（）📅]', section_title):
            issues.append(f"timeline section 标题含特殊符号: `{section_title}`")
    return issues


def check_r14_flow_node_count(code: str) -> List[str]:
    """R14 [v3.0.0]: flow/LR/TD 节点数 > 12"""
    issues = []
    # 检查是否为 graph/flowchart 类型
    code_lower = code.lower().lstrip()
    if not (code_lower.startswith('graph') or code_lower.startswith('flowchart')):
        return issues
    # 统计已定义节点ID：行首 ID[...] / ID{...} / ID(...)
    node_ids = set()
    for m in re.finditer(r'^\s*([A-Za-z][A-Za-z0-9_]*)\s*[\[\{\(]', code, re.MULTILINE):
        node_ids.add(m.group(1))
    count = len(node_ids)
    if count > 12:
        issues.append(f"flow 节点数 {count} > 12（硬上限），应按 §0.5.3 拆为多图或降级为表格")
    return issues


def check_r15_gantt_section_count(code: str) -> List[str]:
    """R15 [v3.0.0]: gantt section 数 > 2"""
    issues = []
    if 'gantt' not in code.lower():
        return issues
    sections = re.findall(r'^\s*section\s+', code, re.MULTILINE)
    count = len(sections)
    if count > 2:
        issues.append(f"gantt section 数 {count} > 2（硬上限），应按 §3.5.1 去除法定期限对比 section（改为 HTML 表格注解）")
    return issues


def check_r16_gantt_section_items(code: str) -> List[str]:
    """R16 [v3.0.0]: gantt 单 section 任务+里程碑 > 10"""
    issues = []
    if 'gantt' not in code.lower():
        return issues
    # 按 section 分组统计任务数
    sections = re.split(r'^\s*section\s+[^\n]*\n', code, flags=re.MULTILINE)
    # 第一个元素是 title/dateFormat 等头部，跳过
    for i, sec_body in enumerate(sections[1:], 1):
        # 统计该 section 内的任务/里程碑行（排除 style 指令行）
        # style 行格式: "style ID fill:#xxx,..." — 不计入任务数
        lines = sec_body.split('\n')
        task_lines = [l for l in lines if l.strip() and not l.strip().startswith('style ')]
        count = len(task_lines)
        if count > 10:
            issues.append(f"gantt section #{i} 含 {count} 条任务/里程碑 > 10（硬上限），应按 §0.5.3 精简或拆 section")
    return issues


# ════════════════════════════════════════════════════════════════════
# 4. 规则注册表
# ════════════════════════════════════════════════════════════════════

RULES = [
    ("R1", "block", "节点ID含中文/空格", check_r1_node_id),
    ("R2", "warning", "中文标签未用双引号包裹", check_r2_quote),
    ("R3", "block", "箭头语法错误", check_r3_arrow),
    ("R4", "block", "style引用未定义ID", check_r4_style_id),
    ("R5", "block", "style含CSS变量", check_r5_style_var),
    ("R6", "block", "gantt缺dateFormat", check_r6_gantt_dateformat),
    ("R7", "block", "gantt任务名含特殊符号", check_r7_gantt_taskname),
    ("R8", "block", "gantt跨度>12个月应拆双图", check_r8_gantt_span),
    ("R9", "block", "pie数值含小数", check_r9_pie_integer),
    ("R10", "block", "quadrant非英文标签", check_r10_quadrant_lang),
    ("R11", "warning", "timeline标签超长", check_r11_timeline_label),
    ("R12", "block", "pie类别过多或小类未合并", check_r12_pie_merge),
    ("R13", "block", "timeline section含特殊符号", check_r13_timeline_section),
    ("R14", "block", "flow节点数>12", check_r14_flow_node_count),
    ("R15", "block", "gantt section数>2", check_r15_gantt_section_count),
    ("R16", "block", "gantt单section任务>10", check_r16_gantt_section_items),
]


# ════════════════════════════════════════════════════════════════════
# 5. 主流程
# ════════════════════════════════════════════════════════════════════

def extract_mermaid_blocks(html: str) -> List[Tuple[int, str]]:
    """返回 [(块序号, mermaid代码), ...]"""
    blocks = []
    for i, m in enumerate(MERMAID_BLOCK_RE.finditer(html), 1):
        code = m.group(1).strip()
        # 跳过空块
        if not code:
            continue
        blocks.append((i, code))
    return blocks


def detect_chart_type(code: str) -> str:
    """识别图表类型"""
    code_lower = code.lower().lstrip()
    if code_lower.startswith('gantt'):
        return 'gantt'
    elif code_lower.startswith('pie'):
        return 'pie'
    elif code_lower.startswith('quadrantchart'):
        return 'quadrantChart'
    elif code_lower.startswith('timeline'):
        return 'timeline'
    elif code_lower.startswith('graph') or code_lower.startswith('flowchart'):
        return 'graph'
    elif code_lower.startswith('sequencediagram'):
        return 'sequenceDiagram'
    else:
        return 'unknown'


def check_html(html: str) -> Dict:
    """主检查函数"""
    blocks = extract_mermaid_blocks(html)
    report = {
        "summary": {"total_blocks": len(blocks), "block_violations": 0, "warnings": 0},
        "blocks": []
    }
    for idx, code in blocks:
        chart_type = detect_chart_type(code)
        block_result = {
            "index": idx,
            "type": chart_type,
            "violations": [],
            "warnings": []
        }
        for rule_id, severity, desc, fn in RULES:
            issues = fn(code)
            for issue in issues:
                entry = {"rule": rule_id, "desc": desc, "detail": issue}
                if severity == "block":
                    block_result["violations"].append(entry)
                    report["summary"]["block_violations"] += 1
                else:
                    block_result["warnings"].append(entry)
                    report["summary"]["warnings"] += 1
        report["blocks"].append(block_result)
    return report


def render_markdown_report(report: Dict, html_file: str) -> str:
    """渲染 Markdown 报告"""
    lines = []
    lines.append(f"# Mermaid 预检报告 — {Path(html_file).name}")
    lines.append("")
    lines.append(f"**生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**扫描图表块数**：{report['summary']['total_blocks']}")
    lines.append(f"**块级违规**：{report['summary']['block_violations']} {'🔴' if report['summary']['block_violations'] > 0 else '✅'}")
    lines.append(f"**警告数**：{report['summary']['warnings']} {'⚠️' if report['summary']['warnings'] > 0 else '✅'}")
    lines.append("")
    if report['summary']['block_violations'] == 0 and report['summary']['warnings'] == 0:
        lines.append("> 🎉 **全部通过！** 产物可交付。")
        lines.append("")
        return "\n".join(lines)
    lines.append("---")
    lines.append("")
    for blk in report["blocks"]:
        if not blk["violations"] and not blk["warnings"]:
            continue
        status = "🔴" if blk["violations"] else "⚠️"
        lines.append(f"## {status} 块 #{blk['index']} ({blk['type']})")
        lines.append("")
        if blk["violations"]:
            lines.append("### 块级违规（必须修复）")
            lines.append("")
            for v in blk["violations"]:
                lines.append(f"- **[{v['rule']}] {v['desc']}** — {v['detail']}")
            lines.append("")
        if blk["warnings"]:
            lines.append("### 警告（建议修复）")
            lines.append("")
            for w in blk["warnings"]:
                lines.append(f"- [{w['rule']}] {w['desc']} — {w['detail']}")
            lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Mermaid 产物预检脚本（v3.0.0 扩展）")
    parser.add_argument("html_file", help="待预检的 HTML 文件路径")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    parser.add_argument("--strict", action="store_true", help="严格模式（warning 也算失败）")
    args = parser.parse_args()

    html_path = Path(args.html_file)
    if not html_path.exists():
        print(f"❌ 文件不存在: {args.html_file}", file=sys.stderr)
        sys.exit(2)

    html = html_path.read_text(encoding="utf-8")
    report = check_html(html)

    if args.json:
        # JSON 直接输出到 stdout（确保 UTF-8）
        sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        md = render_markdown_report(report, args.html_file)
        # 控制台简版（强制 UTF-8 输出避免 Windows GBK 报错）
        sys.stdout.reconfigure(encoding="utf-8")
        try:
            print(md)
        except UnicodeEncodeError:
            # 退化：去除 emoji 后输出
            print(md.encode("ascii", "ignore").decode("ascii"))
        # 同时写报告文件
        report_path = html_path.parent / f"{html_path.stem}.precheck-report.md"
        report_path.write_text(md, encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
        print(f"\n[REPORT] 报告已写入: {report_path}", file=sys.stderr)

    # 退出码
    if report['summary']['block_violations'] > 0:
        sys.exit(1)
    if args.strict and report['summary']['warnings'] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
