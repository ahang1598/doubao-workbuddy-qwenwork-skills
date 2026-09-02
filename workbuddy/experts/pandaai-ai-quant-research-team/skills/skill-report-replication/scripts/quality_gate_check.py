#!/usr/bin/env python3
"""
Quality Gate Check Script — 研报复现交付前自动检查

Usage:
    python quality_gate_check.py /home/coder/project/replication/report-replication/{report_id}

检查项：
    1. 目录结构完整性
    2. 强制产出物存在性（文件级别）
    3. HTML 报告标准章节结构
    4. 图表数量和命名规范
    5. 数据文件完整性
    6. 诚实性声明（manifest.json 中是否有 incident 记录）

Exit codes:
    0 — 全部通过
    1 — 存在错误（具体见 stderr 输出）
"""

import sys
import os
import json
import re
import io
import csv
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"


def print_header(title):
    print(f"\n{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.CYAN}{title}{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*70}{Colors.RESET}")


def print_pass(msg):
    print(f"  {Colors.GREEN}[PASS]{Colors.RESET} {msg}")


def print_fail(msg):
    print(f"  {Colors.RED}[FAIL]{Colors.RESET} {msg}")


def print_warn(msg):
    print(f"  {Colors.YELLOW}[WARN]{Colors.RESET} {msg}")


def print_info(msg):
    print(f"  {Colors.CYAN}[INFO]{Colors.RESET} {msg}")


class QualityGateChecker:
    def __init__(self, project_dir):
        self.project_dir = Path(project_dir).resolve()
        self.report_id = self.project_dir.name
        self.errors = []
        self.warnings = []
        self.infos = []
        self.passes = 0

    def error(self, msg):
        self.errors.append(msg)
        print_fail(msg)

    def warn(self, msg):
        self.warnings.append(msg)
        print_warn(msg)

    def info(self, msg):
        self.infos.append(msg)
        print_info(msg)

    def pass_(self, msg):
        self.passes += 1
        print_pass(msg)

    # ──────────────────────────────────────────────────────────────────────────
    # Check 1: 目录结构
    # ──────────────────────────────────────────────────────────────────────────
    def check_directory_structure(self):
        print_header("Check 1: 目录结构完整性")

        required_dirs = [
            "01_translation",
            "02_factor_reproduction",
            "03_factor_validation",
            "03_factor_validation/data",
            "03_factor_validation/charts",
            "03_factor_validation/data_cache",
            "04_backtest_strategy",
            "04_backtest_strategy/backtest_logs",
            "06_delivery",
        ]

        for d in required_dirs:
            full_path = self.project_dir / d
            if full_path.exists() and full_path.is_dir():
                self.pass_(f"目录存在: {d}/")
            else:
                self.error(f"目录缺失: {d}/")

    # ──────────────────────────────────────────────────────────────────────────
    # Check 2: 强制文件清单
    # ──────────────────────────────────────────────────────────────────────────
    def check_required_files(self):
        print_header("Check 2: 强制产出物存在性")

        required_files = [
            # Step 1~3
            "01_translation/full_translation.md",
            "02_factor_reproduction/ai_summary_and_factor_formula.md",
            "02_factor_reproduction/reference_implementation.py",

            # Step 4: HTML 报告
            "03_factor_validation/factor_validation_report.html",

            # Step 4: data/ 强制 CSV
            "03_factor_validation/data/ie_factor_matrix.csv",
            "03_factor_validation/data/direction_matrix_from_strategy.csv",
            "03_factor_validation/data/portfolio_returns_ew_full.csv",
            "03_factor_validation/data/portfolio_returns_ew_is.csv",
            "03_factor_validation/data/portfolio_returns_ew_oos.csv",
            "03_factor_validation/data/portfolio_returns_dir_full.csv",
            "03_factor_validation/data/portfolio_returns_dir_is.csv",
            "03_factor_validation/data/portfolio_returns_dir_oos.csv",
            "03_factor_validation/data/ic_series.csv",
            "03_factor_validation/data/benchmark_comparison.csv",
            "03_factor_validation/data/backtest_alignment_audit.csv",

            # Step 5: 策略
            "04_backtest_strategy/strategy.py",
            "04_backtest_strategy/config.json",
            "04_backtest_strategy/backtest_report.html",
            "04_backtest_strategy/backtest_logs/signal_log.jsonl",
            "04_backtest_strategy/backtest_logs/equity_curve.csv",
            "04_backtest_strategy/backtest_logs/performance_metrics.csv",
            "04_backtest_strategy/backtest_logs/trades.csv",

            "manifest.json",
        ]

        for f in required_files:
            full_path = self.project_dir / f
            if full_path.exists() and full_path.is_file():
                size = full_path.stat().st_size
                if size == 0:
                    self.error(f"文件为空: {f}")
                else:
                    self.pass_(f"文件存在 ({size} bytes): {f}")
            else:
                self.error(f"文件缺失: {f}")

        # 检查 failure_report.md 或 final_delivery_summary.md 至少有一个。
        # 成功交付需要 final_delivery_summary.md；失败或阻塞场景允许只提交 failure_report.md。
        has_failure = (self.project_dir / "failure_report.md").exists()
        has_summary = (self.project_dir / "06_delivery/final_delivery_summary.md").exists()
        if has_failure or has_summary:
            self.pass_("failure_report.md 或 final_delivery_summary.md 至少存在一个")
            if has_summary:
                summary_size = (self.project_dir / "06_delivery/final_delivery_summary.md").stat().st_size
                if summary_size == 0:
                    self.error("final_delivery_summary.md 为空")
            if has_failure:
                failure_size = (self.project_dir / "failure_report.md").stat().st_size
                if failure_size == 0:
                    self.error("failure_report.md 为空")
        else:
            self.error("failure_report.md 和 final_delivery_summary.md 都不存在")

    # ──────────────────────────────────────────────────────────────────────────
    # Check 3: HTML 报告结构
    # ──────────────────────────────────────────────────────────────────────────
    def check_html_report_structure(self):
        print_header("Check 3: HTML 报告标准章节结构")

        html_path = self.project_dir / "03_factor_validation/factor_validation_report.html"
        if not html_path.exists():
            self.error("factor_validation_report.html 不存在，跳过 HTML 结构检查")
            return

        try:
            with open(html_path, "r", encoding="utf-8-sig") as f:
                html_content = f.read()
        except Exception as e:
            self.error(f"无法读取 HTML 报告: {e}")
            return

        # 检查文件大小（不能太小）
        size = len(html_content)
        if size < 10000:
            self.warn(f"HTML 报告过小 ({size} bytes)，可能内容不完整")
        else:
            self.pass_(f"HTML 报告大小: {size} bytes")

        # 检查是否包含 base64 图片（内嵌图表）
        img_count = html_content.count("data:image/png;base64,")
        if img_count < 4:
            self.error(f"HTML 内嵌图表数量不足: {img_count} < 4")
        else:
            self.pass_(f"HTML 内嵌图表: {img_count} 张")

        # Reader-facing explanation layer: charts and metrics must be understandable
        # without opening CSV files or knowing quantitative jargon.
        explanation_markers = [
            "How To Read",
            "阅读指南",
            "metric dictionary",
            "指标字典",
            "本报告中怎么判断",
            "chart-note",
            "怎么看",
            "本图解读",
        ]
        if any(marker in html_content for marker in explanation_markers):
            self.pass_("HTML 包含阅读指南/图表解释层")
        else:
            self.error("HTML 缺少阅读指南或图表解释层")

        chart_note_count = (
            html_content.count('class="chart-note"')
            + html_content.count("class='chart-note'")
        )
        if chart_note_count < img_count:
            self.error(f"图表解释块数量不足: {chart_note_count}，图表数: {img_count}；每张图都必须有解释块")
        else:
            self.pass_(f"图表解释块数量: {chart_note_count}")

        required_metric_terms = ["IC", "Rank IC", "ICIR", "Sharpe", "Max DD", "NAV", "OOS"]
        missing_metric_terms = [term for term in required_metric_terms if term not in html_content]
        if missing_metric_terms:
            self.warn(f"指标解释可能不完整，缺少关键词: {missing_metric_terms}")
        else:
            self.pass_("关键指标术语已覆盖")

        robustness_markers = {
            "红黄绿判定/打分卡": ["RAG Scorecard", "红黄绿", "打分卡"],
            "基准对照": ["Benchmark Comparison", "基准对照", "reverse_factor", "random_factor"],
            "BACKTEST 差异审计": ["BACKTEST Alignment Audit", "BACKTEST 差异审计", "口径差异"],
        }
        for check_name, markers in robustness_markers.items():
            if any(marker in html_content for marker in markers):
                self.pass_(f"HTML 包含{check_name}")
            else:
                self.error(f"HTML 缺少{check_name}")

        blocker_terms = [
            "QUALITY_GATE_BLOCKER",
            "requires review",
            "scorecard_missing",
            "benchmark_comparison_missing",
            "alignment_audit_missing",
        ]
        found_blockers = [term for term in blocker_terms if term in html_content]
        if found_blockers:
            self.error(f"HTML 仍包含占位/阻塞内容: {found_blockers}")

        benchmark_terms = ["reverse_factor", "random_factor", "equal_weight", "zero_return"]
        missing_benchmark_terms = [term for term in benchmark_terms if term not in html_content]
        if missing_benchmark_terms:
            self.error(f"HTML 基准对照缺少关键基准: {missing_benchmark_terms}")
        else:
            self.pass_("HTML 基准对照覆盖反向、随机、等权、零收益基准")

        # 10 个标准章节（检查标题关键词）
        required_sections = [
            ("报告头/标题", [r"验证报告", r"因子验证", r"Factor Validation"]),
            ("因子审计", [r"因子审计", r"Bias Check", r"审计", r"look.ahead", r"price leakage", r"偷价"]),
            ("数据诊断", [r"数据诊断", r"Data Diagnostic", r"品种数量", r"覆盖率"]),
            ("因子横截面分布", [r"因子横截面分布", r"横截面分布", r"Factor Distribution", r"distribution"]),
            ("IC 分析", [r"IC", r"Rank IC", r"ICIR", r"信息系数"]),
            ("等权重组合回测", [r"等权重", r"Equal Weight", r"分层组合", r"Quantile"]),
            ("策略等手数组合", [r"等手数", r"Equal Lot", r"策略方向", r"strategy direction"]),
            ("Walk-forward", [r"Walk.forward", r"Walkforward", r"滚动窗口"]),
            ("成本敏感性", [r"成本敏感", r"Cost Sensitivity", r"手续费", r"transaction cost"]),
            ("验证结论", [r"结论", r"Conclusion", r"验证结论"]),
        ]

        for section_name, keywords in required_sections:
            found = False
            for kw in keywords:
                if re.search(kw, html_content, re.IGNORECASE):
                    found = True
                    break
            if found:
                self.pass_(f"章节存在: {section_name}")
            else:
                self.error(f"章节缺失: {section_name} (关键词: {keywords})")

        # 检查诚实性声明
        honesty_keywords = [r"数据不足", r"未执行", r"未计算", r"无法判断", r"inconclusive"]
        has_honesty = any(re.search(kw, html_content, re.IGNORECASE) for kw in honesty_keywords)
        if has_honesty:
            self.pass_("报告包含诚实性声明（数据不足/未执行等）")
        else:
            self.warn("报告未找到诚实性声明关键词（如果全部执行完成则正常，否则需检查）")

    # ──────────────────────────────────────────────────────────────────────────
    # Check 4: 图表文件
    # ──────────────────────────────────────────────────────────────────────────
    def check_charts(self):
        print_header("Check 4: 图表文件清单")

        charts_dir = self.project_dir / "03_factor_validation/charts"
        if not charts_dir.exists():
            self.error("charts/ 目录不存在")
            return

        # 强制图表
        required_charts = {
            "01_ie_distribution.png": "factor distribution",
            "02_ic_series.png": "IC time series",
            "03_is_oos_ic_comparison.png": "IS vs OOS IC comparison",
            "04_cumulative_nav_equal_weight.png": "equal-weight validation NAV",
            "05_cumulative_nav_strategy_direction.png": "strategy-direction validation NAV",
            "06_drawdown.png": "drawdown",
        }

        for filename, desc in required_charts.items():
            full_path = charts_dir / filename
            if full_path.exists():
                size = full_path.stat().st_size
                self.pass_(f"图表存在 ({size} bytes): {filename} ({desc})")
            else:
                self.error(f"图表缺失: {filename} ({desc})")

        # 可选图表
        optional_charts = {
            "07_ic_distribution.png": "IC distribution",
            "08_rolling_ic.png": "rolling IC",
            "09_quantile_nav.png": "quantile NAV",
            "10_quantile_return_bar.png": "quantile return monotonicity",
            "15_benchmark_nav_comparison.png": "benchmark NAV comparison",
            "16_backtest_alignment_nav.png": "BACKTEST alignment",
            "18_cost_sensitivity.png": "cost sensitivity",
            "19_walkforward.png": "Walk-forward",
        }

        for filename, desc in optional_charts.items():
            full_path = charts_dir / filename
            if full_path.exists():
                self.pass_(f"可选图表存在: {filename} ({desc})")
            else:
                self.warn(f"可选图表缺失: {filename} ({desc})")

        # 检查命名规范：不允许中文文件名、不允许空格
        all_charts = list(charts_dir.glob("*.png"))
        bad_names = [c.name for c in all_charts if " " in c.name or any(ord(ch) > 127 for ch in c.name)]
        if bad_names:
            self.error(f"图表命名不规范（含中文或空格）: {bad_names}")
        else:
            self.pass_("图表命名符合规范（英文小写+下划线）")

        # 检查是否有编号前缀
        numbered = [c.name for c in all_charts if re.match(r"^\d{2}_", c.name)]
        if len(numbered) >= 6:
            self.pass_(f"图表编号规范: {len(numbered)} 张使用 01_ ~ 08_ 前缀")
        else:
            self.warn(f"图表编号不规范: 仅 {len(numbered)} 张使用 01_ 前缀")

    # ──────────────────────────────────────────────────────────────────────────
    # Check 5: 数据文件
    # ──────────────────────────────────────────────────────────────────────────
    def check_data_files(self):
        print_header("Check 5: 数据文件完整性")

        data_dir = self.project_dir / "03_factor_validation/data"
        if not data_dir.exists():
            self.error("data/ 目录不存在")
            return

        # 检查每个 CSV 非空且有数据行
        csv_files = [
            "ie_factor_matrix.csv",
            "direction_matrix_from_strategy.csv",
            "portfolio_returns_ew_full.csv",
            "portfolio_returns_ew_is.csv",
            "portfolio_returns_ew_oos.csv",
            "portfolio_returns_dir_full.csv",
            "portfolio_returns_dir_is.csv",
            "portfolio_returns_dir_oos.csv",
            "ic_series.csv",
            "benchmark_comparison.csv",
            "backtest_alignment_audit.csv",
        ]

        for csv_name in csv_files:
            csv_path = data_dir / csv_name
            if not csv_path.exists():
                self.error(f"CSV 缺失: {csv_name}")
                continue

            try:
                with open(csv_path, "r", encoding="utf-8-sig") as f:
                    lines = f.readlines()
            except Exception as e:
                self.error(f"无法读取 {csv_name}: {e}")
                continue

            if len(lines) < 2:
                self.error(f"CSV 无数据行: {csv_name} (仅 {len(lines)} 行)")
            elif len(lines) < 5:
                self.warn(f"CSV 数据行过少: {csv_name} (仅 {len(lines)} 行)")
            else:
                self.pass_(f"CSV 数据完整: {csv_name} ({len(lines)} 行)")

        self.check_benchmark_comparison_csv(data_dir / "benchmark_comparison.csv")

    def check_benchmark_comparison_csv(self, csv_path):
        if not csv_path.exists():
            return

        try:
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)
        except Exception as e:
            self.error(f"无法解析 benchmark_comparison.csv: {e}")
            return

        if len(rows) < 2:
            self.error("benchmark_comparison.csv 缺少数据行")
            return

        header = [str(col).strip().lower() for col in rows[0]]
        text = " ".join(",".join(str(cell).strip().lower() for cell in row) for row in rows[:200])
        text = " ".join(header) + " " + text

        required_baselines = {
            "reverse_factor": ["reverse_factor", "reverse factor", "反向"],
            "random_factor": ["random_factor", "random factor", "random_factor_fixed_seed", "random_factor_seed", "随机"],
            "equal_weight_buy_hold": ["equal_weight", "buy_hold", "buy-and-hold", "等权"],
            "zero_return": ["zero_return", "always_flat", "flat", "零收益"],
        }
        missing = [
            name
            for name, tokens in required_baselines.items()
            if not any(token in text for token in tokens)
        ]
        if missing:
            self.error(f"benchmark_comparison.csv 缺少必需基准: {missing}")
        else:
            self.pass_("benchmark_comparison.csv 覆盖必需基准")

        numeric_cells = 0
        for row in rows[1:]:
            for cell in row[1:]:
                try:
                    float(str(cell).strip())
                    numeric_cells += 1
                except ValueError:
                    pass
        if numeric_cells == 0:
            self.error("benchmark_comparison.csv 没有可解析的数值收益/绩效数据")
        else:
            self.pass_(f"benchmark_comparison.csv 包含数值数据: {numeric_cells} cells")

    # ──────────────────────────────────────────────────────────────────────────
    # Check 6: manifest.json 诚实性记录
    # ──────────────────────────────────────────────────────────────────────────
    def check_manifest(self):
        print_header("Check 7: manifest.json 完整性")

        manifest_path = self.project_dir / "manifest.json"
        if not manifest_path.exists():
            self.error("manifest.json 不存在")
            return

        try:
            with open(manifest_path, "r", encoding="utf-8-sig") as f:
                manifest = json.load(f)
        except Exception as e:
            self.error(f"manifest.json 解析失败: {e}")
            return

        required_keys = ["report_id", "title", "data_sources", "parameters", "run_history", "artifacts"]
        for key in required_keys:
            if key in manifest:
                self.pass_(f"manifest.json 包含键: {key}")
            else:
                self.error(f"manifest.json 缺失键: {key}")

        # 检查是否有 quality_control / incident 记录（诚实性）
        if "quality_control" in manifest:
            qc = manifest.get("quality_control", {})
            if qc.get("incident"):
                self.pass_(f"manifest.json 记录了质量事件: {qc.get('incident')}")
            if qc.get("status") == "resolved":
                self.pass_("manifest.json 质量事件已标记为 resolved")
        else:
            self.warn("manifest.json 缺少 quality_control 字段（建议记录数据事件）")

        # 检查 run_history 是否有记录
        run_history = manifest.get("run_history", [])
        if len(run_history) > 0:
            self.pass_(f"manifest.json run_history 记录数: {len(run_history)}")
        else:
            self.warn("manifest.json run_history 为空")

    # ──────────────────────────────────────────────────────────────────────────
    # Check 7: signal_log.jsonl 格式检查
    # ──────────────────────────────────────────────────────────────────────────
    def check_signal_log(self):
        print_header("Check 8: signal_log.jsonl 格式检查")

        log_path = self.project_dir / "04_backtest_strategy/backtest_logs/signal_log.jsonl"
        if not log_path.exists():
            self.error("signal_log.jsonl 不存在")
            return

        try:
            with open(log_path, "r", encoding="utf-8-sig") as f:
                lines = f.readlines()
        except Exception as e:
            self.error(f"无法读取 signal_log.jsonl: {e}")
            return

        if len(lines) == 0:
            self.error("signal_log.jsonl 为空")
            return

        self.pass_(f"signal_log.jsonl 行数: {len(lines)}")

        # 检查前几行的 JSON 格式
        valid_count = 0
        sample = None
        for i, line in enumerate(lines[:10]):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if "date" in rec and "signals" in rec:
                    valid_count += 1
                    if sample is None:
                        sample = rec
                else:
                    self.error(f"signal_log 第 {i+1} 行缺少 date/signals 字段")
            except json.JSONDecodeError as e:
                self.error(f"signal_log 第 {i+1} 行 JSON 解析失败: {e}")

        if valid_count > 0:
            self.pass_(f"signal_log 格式正确: {valid_count}/{min(10, len(lines))} 行验证通过")

        if sample:
            signals = sample.get("signals", {})
            if signals:
                first_sym = list(signals.keys())[0]
                first_val = signals[first_sym]
                has_factor = "factor" in first_val or "ie" in first_val
                has_direction = "direction" in first_val
                if has_factor and has_direction:
                    self.pass_(f"signal_log 字段格式正确: {first_sym} -> {first_val}")
                else:
                    self.error(f"signal_log 字段不完整: {first_val} (需要 factor/ie + direction)")

    # ──────────────────────────────────────────────────────────────────────────
    # 汇总报告
    # ──────────────────────────────────────────────────────────────────────────
    def print_summary(self):
        print_header("检查汇总")

        total_checks = self.passes + len(self.warnings) + len(self.errors) + len(self.infos)

        print(f"\n  通过:   {Colors.GREEN}{self.passes}{Colors.RESET}")
        print(f"  警告:   {Colors.YELLOW}{len(self.warnings)}{Colors.RESET}")
        print(f"  错误:   {Colors.RED}{len(self.errors)}{Colors.RESET}")
        print(f"  信息:   {Colors.CYAN}{len(self.infos)}{Colors.RESET}")
        print(f"  总检查: {total_checks}")

        if self.errors:
            print(f"\n{Colors.RED}【结果】Quality Gates 未通过 — 存在 {len(self.errors)} 个错误，必须修复后才能交付。{Colors.RESET}")
            return 1
        elif self.warnings:
            print(f"\n{Colors.YELLOW}【结果】Quality Gates 有条件通过 — 存在 {len(self.warnings)} 个警告，建议修复。{Colors.RESET}")
            return 0
        else:
            print(f"\n{Colors.GREEN}【结果】Quality Gates 全部通过 — 可以交付。{Colors.RESET}")
            return 0

    def run_all(self):
        print(f"\n{Colors.CYAN}Quality Gate Check for: {self.project_dir}{Colors.RESET}")
        print(f"{Colors.CYAN}检查时间: {datetime.now().isoformat()}{Colors.RESET}")

        self.check_directory_structure()
        self.check_required_files()
        self.check_html_report_structure()
        self.check_charts()
        self.check_data_files()
        self.check_manifest()
        self.check_signal_log()

        return self.print_summary()


def main():
    if len(sys.argv) < 2:
        print("Usage: python quality_gate_check.py /home/coder/project/replication/report-replication/{report_id}")
        print("Example: python quality_gate_check.py /home/coder/project/replication/report-replication/ssrn-3391784")
        sys.exit(1)

    project_dir = sys.argv[1]
    if not os.path.exists(project_dir):
        print(f"错误: 项目目录不存在: {project_dir}")
        sys.exit(1)

    checker = QualityGateChecker(project_dir)
    exit_code = checker.run_all()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
