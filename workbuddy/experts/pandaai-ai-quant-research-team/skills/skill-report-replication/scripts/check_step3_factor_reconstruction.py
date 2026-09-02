#!/usr/bin/env python3
"""
Step 3 门禁检查 — 因子重构质量检查

Usage:
    python check_step3_factor_reconstruction.py /home/coder/project/replication/report-replication/{report_id}

检查项：
    1. ai_summary_and_factor_formula.md 是否存在且非空
    2. reference_implementation.py 是否存在且非空
    3. 是否包含研究问题、因子公式、变量定义
    4. 参考实现代码是否有核心计算函数

Exit codes:
    0 — 通过
    1 — 存在错误
"""

import sys
import os
import re
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def check_factor_reconstruction(project_dir):
    errors = []
    warnings = []

    doc_path = Path(project_dir) / "02_factor_reproduction" / "ai_summary_and_factor_formula.md"
    code_path = Path(project_dir) / "02_factor_reproduction" / "reference_implementation.py"

    print("=" * 70)
    print("Step 3 门禁检查 — 因子重构")
    print("=" * 70)

    # 1. 检查 ai_summary_and_factor_formula.md
    if not doc_path.exists():
        errors.append("[FAIL] 02_factor_reproduction/ai_summary_and_factor_formula.md 不存在")
    else:
        size = doc_path.stat().st_size
        if size < 1000:
            errors.append(f"[FAIL] 因子文档过短 ({size} bytes)")
        else:
            print(f"[PASS] 因子文档存在 ({size} bytes)")

        with open(doc_path, "r", encoding="utf-8") as f:
            doc = f.read()

        # 检查关键内容
        checks = [
            ("研究问题", [r"研究问题", r"Research Question", r"问题", r"question"]),
            ("因子公式", [r"公式", r"formula", r"Factor", r"定义", r"计算", r"=", r"\\["]),
            ("变量定义", [r"变量", r"其中", r"定义", r"参数", r"说明"]),
            ("资产池", [r"品种", r"资产", r"universe", r"commodity", r"期货"]),
            ("组合构建", [r"组合", r"portfolio", r"多空", r"long.short", r"权重"]),
            ("假设", [r"假设", r"assumption", r"proxy", r"代理"]),
        ]

        for name, keywords in checks:
            found = any(kw in doc for kw in keywords)
            if found:
                print(f"[PASS] 文档包含: {name}")
            else:
                errors.append(f"[FAIL] 文档缺少: {name} (关键词: {keywords})")

    # 2. 检查 reference_implementation.py（核心门禁）
    print("\n--- reference_implementation.py 检查 ---")
    if not code_path.exists():
        errors.append(
            "[FAIL] 02_factor_reproduction/reference_implementation.py 不存在。"
            "这是强制产出物，必须包含精确到函数级别的参考实现代码。"
        )
    else:
        size = code_path.stat().st_size
        if size < 500:
            errors.append(f"[FAIL] 参考实现代码过短 ({size} bytes)，疑似空文件")
        else:
            print(f"[PASS] 参考实现代码存在 ({size} bytes)")

        with open(code_path, "r", encoding="utf-8") as f:
            code = f.read()

        # 检查是否包含函数定义
        func_count = len(re.findall(r'def\s+\w+\s*\(', code))
        if func_count < 1:
            errors.append("[FAIL] 参考实现代码中没有函数定义")
        else:
            print(f"[PASS] 参考实现代码包含 {func_count} 个函数定义")

        # 检查是否有因子计算函数（常见命名）
        factor_funcs = re.findall(r'def\s+(compute_ie|calculate_ie|ie_factor|factor_value)\s*\(', code, re.IGNORECASE)
        if factor_funcs:
            print(f"[PASS] 发现因子计算函数: {factor_funcs}")
        else:
            warnings.append(
                "[WARN] 未发现标准命名的因子计算函数，"
                "请确认函数名能明确表示其计算的是哪个因子"
            )

        # 检查是否有参数/配置
        if "THRESHOLD" in code or "threshold" in code or "PARAMS" in code or "params" in code:
            print("[PASS] 参考实现代码包含参数定义")
        else:
            warnings.append("[WARN] 参考实现代码中未发现参数定义")

    print_summary(errors, warnings)
    return 1 if errors else 0


def print_summary(errors, warnings):
    print("\n" + "=" * 70)
    print("检查汇总")
    print("=" * 70)
    for e in errors:
        print(e)
    for w in warnings:
        print(w)

    print(f"\n错误: {len(errors)}, 警告: {len(warnings)}")
    if errors:
        print("【结果】未通过 — 因子重构不符合要求。必须修复后重新检查。")
    elif warnings:
        print("【结果】有条件通过 — 建议修复警告项。")
    else:
        print("【结果】通过 — 因子重构质量合格。")


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_step3_factor_reconstruction.py /home/coder/project/replication/report-replication/{report_id}")
        sys.exit(1)

    project_dir = sys.argv[1]
    if not os.path.exists(project_dir):
        print(f"错误: 目录不存在: {project_dir}")
        sys.exit(1)

    exit_code = check_factor_reconstruction(project_dir)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
