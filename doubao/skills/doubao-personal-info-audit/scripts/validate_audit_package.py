#!/usr/bin/env python3
"""Validate the schema and key consistency gates of an audit deliverable directory."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from validate_norm_hierarchy import validate_row as validate_norm_hierarchy_row


REQUIRED_SCHEMAS = {
    "附件与证据目录.csv": {"证据编号", "真实附件名称", "具体定位", "证据等级", "支持事实"},
    "事实与不确定性.csv": {
        "事实编号", "评价单元编号", "事实来源类型", "主体", "产品或系统", "事实期间",
        "处理动作", "原子化事实", "证据编号及精确定位", "证据状态与证明力",
        "样本与外推边界", "冲突或相反证据", "不确定性编号", "竞争性假设",
        "最小补证", "核验程序", "事实状态",
    },
    "证据矛盾与未决事项.csv": {"事项编号", "类型", "影响事实", "核验程序", "状态"},
    "信息分类.csv": {"数据分类编号", "数据项目或组合", "关联事实编号", "不确定性编号", "是否个人信息", "是否敏感个人信息", "是否达到匿名化"},
    "处理活动与角色.csv": {"活动编号", "处理活动", "处理主体", "数据分类编号", "关联事实编号", "不确定性编号", "法律角色编号", "角色结论"},
    "处理情形与模块适用性.csv": {"处理情形编号", "处理活动编号", "法律角色编号", "情形类型", "情形状态", "触发事实编号", "排除事实编号", "关键数据分类编号", "不确定性编号", "关联模块", "核验程序"},
    "第三方委托与跨境链路.csv": {"链路编号", "实际法律角色", "数据项目", "出境路径", "结论"},
    "AI系统与自动化决策清单.csv": {"系统编号", "系统名称", "系统确认状态", "发现来源与影子AI线索", "模型及版本", "训练微调RAG数据", "供应商训练保留配置", "PIA状态", "拟人化互动状态", "上线建议"},
    "AI高风险专项分析.csv": {"专项编号", "系统编号", "模型及版本", "分析链编号", "证据编号", "事实编号", "不确定性编号", "数据分类编号", "处理活动编号", "法律角色编号", "处理情形编号", "适用规则编号", "增强审计触发项", "测试名称", "实际结果及证据定位", "审计结论编号", "风险编号及等级", "整改编号及措施", "上线建议"},
    "法规文献数据库.csv": {"法源编号", "层级", "规范全称", "施行日期", "基准日状态", "具体规则内容", "内容属性", "官方URL", "最后核验日期"},
    "法规版本台账.csv": {"来源编号", "规范全称", "审计基准日状态", "关键条款", "具体规则内容", "内容属性", "官方直接链接", "访问日期", "上位依据编号", "配套下位或关联规范编号", "衔接类型", "权限及冲突核验"},
    "适用规范矩阵.csv": {
        "规则编号", "来源编号", "规范全称", "条款或章节", "具体规则内容", "内容属性", "本案对应事实", "核验状态",
        "上位依据编号及条款", "下位法或配套规范编号及条款", "衔接类型", "下位规范触发事实",
        "下位规范适用状态", "下位规范不适用理由", "层级权限冲突核验", "正文引用组合", "待补事实与核验程序",
    },
    "主要问题与整改.csv": {
        "问题编号", "证据编号", "事实编号", "不确定性编号", "数据分类编号", "处理活动编号",
        "法律角色编号", "处理情形编号", "适用规则编号", "审计观点", "参考法条表行",
        "规范名称及条款", "具体规则内容", "上位法基础引用", "下位法或配套规范补充引用",
        "上下位或配套衔接说明", "下位规范触发事实", "下位规范适用状态", "审计结论", "风险编号", "整改编号",
        "待补数据与核验程序", "管理层回应",
    },
    "审计程序点检.csv": {"点检编号", "审计结论", "事实基础", "审计证据"},
    "107项点检.csv": {
        "子项编号", "模块", "审计结论", "分析链编号", "审计证据", "关联事实",
        "不确定性编号", "数据分类编号", "处理活动编号", "法律角色编号", "处理情形编号",
        "适用规则编号", "对应正文问题", "风险编号", "整改编号", "直接法源",
    },
    "审计分析链.csv": {
        "链条编号", "审计发现编号", "环节序号", "分析环节", "本环节编号",
        "分析内容", "直接上游编号", "证据或法源定位", "状态或结论", "待补数据与核验程序",
    },
}

REQUIRED_REPORT_HEADINGS = (
    "任务一：证据、事实与不确定性识别",
    "任务二：数据与个人信息分类",
    "任务三：处理活动、法律角色与处理情形",
    "任务四：适用规则与合规审计分析",
    "任务五：风险评价与整改建议",
    "任务六：审计限制与补充材料",
)

CHAIN_MARKERS = (
    "| ①证据 |", "| ②事实 |", "| ③不确定性 |", "| ④数据分类 |", "| ⑤处理活动 |",
    "| ⑥法律角色 |", "| ⑦处理情形 |", "| ⑧适用规则 |", "| ⑨审计结论 |", "| ⑩风险 |", "| ⑪整改 |",
)

REQUIRED_REPORT_APPENDICES = (
    "附件一：审计发现与整改清单",
    "附件二：法源与文献数据库",
    "附件三：证据与材料目录",
)


def headers(path: Path) -> set[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return set(next(csv.reader(handle), []))


def nonempty_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        return sum(1 for row in reader if any(cell.strip() for cell in row))


def validate_source_database(path: Path) -> list[str]:
    errors: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    seen: set[str] = set()
    for line_no, row in enumerate(rows, 2):
        source_id = (row.get("法源编号") or "").strip()
        level = (row.get("层级") or "").strip()
        if not re.fullmatch(r"(?:L|AR|R|S|J|P)\d{3}", source_id):
            errors.append(f"法规文献数据库.csv第{line_no}行法源编号无效：{source_id or '空'}")
        if source_id in seen:
            errors.append(f"法规文献数据库.csv第{line_no}行法源编号重复：{source_id}")
        seen.add(source_id)
        if level == "行政法规" and not source_id.startswith("AR"):
            errors.append(f"法规文献数据库.csv第{line_no}行行政法规必须使用AR###，避免与处理活动A###冲突")
    if "L006" not in seen:
        errors.append("法规文献数据库.csv缺少《中华人民共和国立法法》层级核验基准L006")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验个人信息保护审计成果包")
    parser.add_argument("directory", help="成果目录")
    parser.add_argument("--report", help="审计报告Markdown；默认自动寻找目录中的报告")
    parser.add_argument("--schema-only", action="store_true", help="仅校验CSV结构，不要求数据行")
    args = parser.parse_args()

    root = Path(args.directory)
    if not root.is_dir():
        raise SystemExit(f"成果目录不存在：{root}")

    errors: list[str] = []
    warnings: list[str] = []
    for filename, required in REQUIRED_SCHEMAS.items():
        path = root / filename
        if not path.is_file():
            errors.append(f"缺少成果文件：{filename}")
            continue
        missing = sorted(required - headers(path))
        if missing:
            errors.append(f"{filename}缺少表头：{'、'.join(missing)}")
        if not args.schema_only and nonempty_rows(path) == 0:
            errors.append(f"{filename}没有有效数据行")

    source_database = root / "法规文献数据库.csv"
    if source_database.is_file():
        errors.extend(validate_source_database(source_database))

    norm_matrix = root / "适用规范矩阵.csv"
    if norm_matrix.is_file() and not args.schema_only:
        with norm_matrix.open("r", encoding="utf-8-sig", newline="") as handle:
            for line_no, row in enumerate(csv.DictReader(handle), 2):
                if any((value or "").strip() for value in row.values()):
                    errors.extend(validate_norm_hierarchy_row(row, line_no))

    report: Path | None = Path(args.report) if args.report else None
    if report is None:
        candidates = [p for p in root.glob("*.md") if "报告" in p.name]
        report = candidates[0] if candidates else None
    if report and report.is_file():
        text = report.read_text(encoding="utf-8")
        for heading in REQUIRED_REPORT_HEADINGS:
            if heading not in text:
                errors.append(f"报告缺少章节：{heading}")
        for heading in REQUIRED_REPORT_APPENDICES:
            if heading not in text:
                errors.append(f"报告缺少附件：{heading}")
        level_match = re.search(r"成果等级[：:]\*{0,2}\s*L([0-4])", text)
        if not level_match and not (args.schema_only and "L【0—4】" in text):
            errors.append("报告首页缺少L0—L4成果等级")
        elif level_match and level_match.group(1) in {"3", "4"} and "总体审计结论与意见" not in text:
            errors.append("L3—L4报告缺少总体审计结论与意见")
        if "| 法源编号及层级 | 规范名称及条款 | 具体规则内容 | 本案对应要件及效力说明 |" not in text:
            errors.append("报告缺少含具体规则内容的“参考法条与规范”表")
        fact_header = "| 链条编号 | 讨论项目 | 内容 |"
        if fact_header not in text:
            errors.append("任务一未使用统一的事实、证据与待补数据综合表")
        positions = [text.find(marker) for marker in CHAIN_MARKERS]
        if any(position < 0 for position in positions):
            errors.append("任务四未完整展示证据至整改的11环节审计分析链")
        elif positions != sorted(positions):
            errors.append("任务四的11环节审计分析链顺序错误")
        split_labels = ("**已确认事实：**", "**审计证据：**", "**待核实事项：**")
        if any(label in text for label in split_labels):
            errors.append("任务四仍以分散段落讨论事实、证据或待补数据，应合并到11环节分析链表")
        if "材料未提及" not in text or "证据不足" not in text or "已经证明不存在" not in text:
            warnings.append("任务一未完整区分材料未提及、证据不足和已经证明不存在")
        if not re.search(r"〔(?:L|AR|R|S|J|P|E|F|C)\d{3}(?:[，,；;][^〕]+)?〕", text):
            warnings.append("报告未发现规范的L/AR/R/S/J/P/E/F/C引文")
    elif not args.schema_only:
        errors.append("未找到审计报告Markdown")

    for item in errors:
        print("错误：" + item)
    for item in warnings:
        print("警告：" + item)
    if errors:
        print(f"成果包校验未通过：{len(errors)}项错误，{len(warnings)}项警告")
        return 1
    print(f"成果包校验通过：0项错误，{len(warnings)}项警告")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
