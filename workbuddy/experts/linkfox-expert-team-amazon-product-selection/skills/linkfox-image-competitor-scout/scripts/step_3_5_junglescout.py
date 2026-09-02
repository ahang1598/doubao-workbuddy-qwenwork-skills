#!/usr/bin/env python3
"""
步骤 3.5：对 Sorftime 未覆盖的 ASIN 调用 JungleScout 日销量估算，加总为月销量，作为兜底数据。

逻辑：
  1. 读取 step4 合并脚本的候选列表（或 Sorftime 落盘文件），找出 monthlySales 仍为空的 ASIN
  2. 对每个空缺 ASIN 调用 JungleScout，查询上个自然月的日销量
  3. 将日销量加总写入输出文件，供 step_4_merge_rank.py 使用

Usage:
  python step_3_5_junglescout.py \
    --sorftime-files data/step3_batch1.json data/step3_batch2.json \
    --search-files data/step2_us.json \
    --marketplace us \
    --out data/step3_5_junglescout.json \
    [--month 202605]   # 可选，默认上个自然月

站点代码对照（--marketplace）：
  amazon.com    → us  |  amazon.co.uk → uk  |  amazon.de → de
  amazon.fr     → fr  |  amazon.it    → it  |  amazon.es → es
  amazon.co.jp  → jp  |  amazon.in    → in
"""

import argparse
import json
import os
import subprocess
import sys
from calendar import monthrange
from datetime import date, datetime
from pathlib import Path


DOMAIN_TO_MARKETPLACE = {
    "amazon.com": "us",
    "amazon.co.uk": "uk",
    "amazon.de": "de",
    "amazon.fr": "fr",
    "amazon.it": "it",
    "amazon.es": "es",
    "amazon.co.jp": "jp",
    "amazon.in": "in",
    "amazon.ca": "ca",
    "amazon.com.mx": "mx",
}


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def get_prev_month_range(month_str: str = None):
    """返回 (start_date, end_date) 字符串，默认上个自然月。"""
    if month_str:
        year = int(month_str[:4])
        month = int(month_str[4:6])
    else:
        today = date.today()
        month = today.month - 1 or 12
        year = today.year if today.month > 1 else today.year - 1
    last_day = monthrange(year, month)[1]
    return f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last_day:02d}"


def get_sorftime_covered(sorftime_files: list) -> set:
    """返回 Sorftime 已有月销量（>0）的 ASIN 集合。"""
    covered = set()
    for fpath in sorftime_files:
        try:
            d = load_json(fpath)
        except Exception:
            continue
        items = d.get("products") or d.get("data") or []
        for item in items:
            asin = item.get("asin")
            units = item.get("monthlySalesUnits")
            if asin and units and units > 0:
                covered.add(asin)
    return covered


def get_all_asins(search_files: list) -> list:
    """从 step2 搜索结果中提取所有 ASIN（保持顺序）。"""
    seen = []
    for fpath in search_files:
        try:
            d = load_json(fpath)
        except Exception:
            continue
        for p in d.get("products", []):
            asin = p.get("asin")
            if asin and asin not in seen:
                seen.append(asin)
    return seen


def query_junglescout(asin: str, marketplace: str, start_date: str, end_date: str) -> int | None:
    """调用 JungleScout 脚本，返回月销量合计（None 表示无数据）。"""
    script = Path(__file__).parent.parent.parent.parent \
        / "linkfox-junglescout-sales-estimates" / "scripts" / "junglescout_sales_estimates.py"

    # 兼容不同安装路径
    if not script.exists():
        candidates = [
            Path(os.environ.get("HOME", "C:/Users/Administrator")) / ".claude" / "skills"
            / "linkfox-junglescout-sales-estimates" / "scripts" / "junglescout_sales_estimates.py",
        ]
        script = next((c for c in candidates if c.exists()), None)
        if not script:
            print("Warning: junglescout_sales_estimates.py not found", file=sys.stderr)
            return None

    params = json.dumps({
        "marketplace": marketplace,
        "asin": asin,
        "startDate": start_date,
        "endDate": end_date,
    })

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        r = subprocess.run(
            [sys.executable, str(script), params],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=env, timeout=30,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return None
        d = json.loads(r.stdout.strip())
        estimates = (d.get("salesEstimateList") or [{}])[0].get("dailyEstimates") or []
        total = sum(e.get("estimatedUnitsSold", 0) or 0 for e in estimates)
        return total if total > 0 else None
    except Exception as e:
        print(f"Warning: JungleScout query failed for {asin}: {e}", file=sys.stderr)
        return None


def run(sorftime_files: list, search_files: list, marketplace: str,
        out_path: str, month_str: str = None) -> dict:

    start_date, end_date = get_prev_month_range(month_str)
    print(f"JungleScout 查询时间段: {start_date} ~ {end_date}", file=sys.stderr)

    covered = get_sorftime_covered(sorftime_files)
    all_asins = get_all_asins(search_files)
    missing = [a for a in all_asins if a not in covered]

    print(f"Sorftime 已覆盖: {len(covered)} 个 | 待补充: {len(missing)} 个", file=sys.stderr)

    js_map = {}
    for i, asin in enumerate(missing):
        print(f"  [{i+1}/{len(missing)}] {asin}...", file=sys.stderr, end=" ")
        units = query_junglescout(asin, marketplace, start_date, end_date)
        if units:
            js_map[asin] = units
            print(f"{units} 件", file=sys.stderr)
        else:
            print("无数据", file=sys.stderr)

    result = {
        "source": "junglescout",
        "marketplace": marketplace,
        "period": f"{start_date}~{end_date}",
        "queried": len(missing),
        "covered": len(js_map),
        "data": js_map,
    }

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def main():
    parser = argparse.ArgumentParser(description="JungleScout 月销量兜底（Step 3.5）")
    parser.add_argument("--sorftime-files", nargs="+", required=True)
    parser.add_argument("--search-files", nargs="+", required=True)
    parser.add_argument("--marketplace", required=True,
                        help="站点代码: us/uk/de/fr/it/es/jp/in")
    parser.add_argument("--out", required=True)
    parser.add_argument("--month", default=None,
                        help="月份 yyyyMM，默认上个自然月")
    args = parser.parse_args()

    try:
        result = run(args.sorftime_files, args.search_files,
                     args.marketplace, args.out, args.month)
        print(json.dumps({
            "status": "ok",
            "queried": result["queried"],
            "covered": result["covered"],
            "period": result["period"],
            "output": args.out,
        }, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"error": True, "message": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
