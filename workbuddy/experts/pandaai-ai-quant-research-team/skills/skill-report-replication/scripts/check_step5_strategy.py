#!/usr/bin/env python3
"""
Step 5 门禁检查 — BACKTEST 策略产出检查

Usage:
    python check_step5_strategy.py /home/coder/project/replication/report-replication/{report_id}

检查项：
    1. strategy.py 是否存在且非空
    2. config.json 是否存在且非空
    3. backtest_report.html 是否存在且非空
    4. signal_log.jsonl 是否存在、非空、格式正确
    5. 策略代码中是否包含参数配置区域

Exit codes:
    0 — 通过
    1 — 存在错误
"""

import sys
import os
import json
import re
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def check_strategy(project_dir):
    errors = []
    warnings = []

    strategy_dir = Path(project_dir) / "04_backtest_strategy"

    print("=" * 70)
    print("Step 5 门禁检查 — BACKTEST 策略产出")
    print("=" * 70)

    files_to_check = [
        ("strategy.py", 1000),
        ("config.json", 100),
        ("backtest_report.html", 2500),
        ("backtest_logs/equity_curve.csv", 100),
        ("backtest_logs/performance_metrics.csv", 100),
        ("backtest_logs/trades.csv", 20),
    ]

    for filename, min_size in files_to_check:
        filepath = strategy_dir / filename
        if not filepath.exists():
            errors.append(f"[FAIL] 04_backtest_strategy/{filename} 不存在")
            continue

        size = filepath.stat().st_size
        if size < min_size:
            errors.append(f"[FAIL] {filename} 过小 ({size} bytes)，疑似空文件或无效")
        else:
            print(f"[PASS] {filename} 存在 ({size} bytes)")

    # signal_log.jsonl 专项检查
    print("\n--- signal_log.jsonl 检查 ---")
    log_path = strategy_dir / "backtest_logs" / "signal_log.jsonl"

    if not log_path.exists():
        errors.append(
            "[FAIL] 04_backtest_strategy/backtest_logs/signal_log.jsonl 不存在。"
            "这是强制产出物，策略回测时必须输出信号日志供 Phase B 对齐验证使用。"
        )
    else:
        size = log_path.stat().st_size
        if size == 0:
            errors.append("[FAIL] signal_log.jsonl 为空文件")
        else:
            print(f"[PASS] signal_log.jsonl 存在 ({size} bytes)")

        with open(log_path, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()

        if len(lines) == 0:
            errors.append("[FAIL] signal_log.jsonl 没有数据行")
        else:
            print(f"[PASS] signal_log.jsonl 包含 {len(lines)} 条记录")

        # 检查前 5 行的 JSON 格式
        valid = 0
        sample = None
        for i, line in enumerate(lines[:5]):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if "date" in rec and "signals" in rec:
                    valid += 1
                    if sample is None:
                        sample = rec
                else:
                    errors.append(
                        f"[FAIL] signal_log 第 {i+1} 行缺少 'date' 或 'signals' 字段"
                    )
            except json.JSONDecodeError as e:
                errors.append(f"[FAIL] signal_log 第 {i+1} 行 JSON 格式错误: {e}")

        if valid > 0:
            print(f"[PASS] signal_log 格式正确 ({valid}/{min(5, len(lines))} 行验证通过)")

        if sample:
            signals = sample.get("signals", {})
            if signals:
                sym = list(signals.keys())[0]
                val = signals[sym]
                has_ie = "ie" in val or "factor" in val
                has_dir = "direction" in val
                if has_ie and has_dir:
                    print(f"[PASS] signal_log 字段完整: {sym} -> {list(val.keys())}")
                else:
                    errors.append(
                        f"[FAIL] signal_log 字段不完整: {sym} -> {val} "
                        f"(需要包含 'ie'/'factor' 和 'direction')"
                    )

    # 检查 strategy.py 是否包含关键要素
    strategy_path = strategy_dir / "strategy.py"
    if strategy_path.exists():
        print("\n--- strategy.py 代码检查 ---")
        with open(strategy_path, "r", encoding="utf-8-sig") as f:
            code = f.read()

        if "signal_log" in code or "jsonl" in code:
            print("[PASS] 策略代码包含 signal_log.jsonl 写入逻辑")
        else:
            errors.append(
                "[FAIL] 策略代码未包含 signal_log.jsonl 写入逻辑。"
                "必须在策略中输出信号日志。"
            )

        if "long_pct" in code or "short_pct" in code or "direction" in code:
            print("[PASS] 策略代码包含多空方向逻辑")
        else:
            warnings.append("[WARN] 策略代码未找到多空方向逻辑")

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
        print("【结果】未通过 — 策略产出不符合要求。必须修复后重新检查。")
    elif warnings:
        print("【结果】有条件通过 — 建议修复警告项。")
    else:
        print("【结果】通过 — 策略产出质量合格。")


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_step5_strategy.py /home/coder/project/replication/report-replication/{report_id}")
        sys.exit(1)

    project_dir = sys.argv[1]
    if not os.path.exists(project_dir):
        print(f"错误: 目录不存在: {project_dir}")
        sys.exit(1)

    exit_code = check_strategy(project_dir)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
