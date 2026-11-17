#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_all.py  — 新增

一次性执行 4 个 verify_*.py 子脚本,把原先 4 轮 bash 调用合并为 1 轮。

接收一份聚合 TOML(或 JSON)作为输入,内部拆分后分别调用 4 个子脚本,
合并输出为单一结果 JSON。

输入格式(TOML,推荐)
----------------------
由 build_json.py --multi 从 TOML 生成,或直接传 TOML 给本脚本:

    [amounts]
    total_amount = 1000000
    ...

    [dates]
    review_date = "2026-04-29"
    ...

    [cross_refs]
    ...

    [payment_flow]
    ...

用法
----
    # 直接从 TOML 运行(推荐)
    python3 verify_all.py --from-toml verify_inputs.toml --output verify_results.json

    # 或从已生成的 4 个 JSON 运行
    python3 verify_all.py \
        --amounts amounts.json \
        --dates dates.json \
        --cross-refs cross_refs.json \
        --payment-flow payment_flow.json \
        --output verify_results.json

输出 JSON 结构
--------------
{
  "amounts":       { ...verify_amounts.py 结果... },
  "dates":         { ...verify_dates.py 结果... },
  "cross_refs":    { ...verify_cross_references.py 结果... },
  "payment_flow":  { ...verify_payment_flow.py 结果... },
  "summary": {
    "total_checks": N,
    "failed_checks": M,
    "scripts_executed": 4,
    "scripts_failed": 0
  }
}

任何子脚本失败不会阻塞整体执行;失败的子模块在对应字段记录 error。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SUB_SCRIPTS = {
    "amounts": "verify_amounts.py",
    "dates": "verify_dates.py",
    "cross_refs": "verify_cross_references.py",
    "payment_flow": "verify_payment_flow.py",
}


def load_toml_as_dict(toml_path: str) -> dict:
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # Python 3.9/3.10 回退,API 与 tomllib 一致
        except ImportError:
            print(
                "[ERROR] 需要 tomllib(Python 3.11+)或回退库 tomli(pip install tomli)",
                file=sys.stderr,
            )
            sys.exit(1)
    with open(toml_path, "rb") as f:
        return tomllib.load(f)


def write_temp_json(obj, name: str, tmpdir: str) -> str:
    path = os.path.join(tmpdir, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return path


def run_sub_script(script_name: str, json_path: str) -> dict:
    """调用子脚本,返回它输出的结果 JSON(dict)。"""
    script_path = os.path.join(SCRIPT_DIR, script_name)
    if not os.path.isfile(script_path):
        return {"error": f"script not found: {script_name}"}
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tf:
        out_path = tf.name
    try:
        proc = subprocess.run(
            [
                sys.executable,
                script_path,
                "--json",
                json_path,
                "--output",
                out_path,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        # 注意:verify 子脚本在"发现问题"时也会 rc=1,这是正常的状态信号,
        # 不视为脚本执行失败。只要输出文件生成就认为脚本跑通了。
        if os.path.isfile(out_path) and os.path.getsize(out_path) > 0:
            with open(out_path, "r", encoding="utf-8") as f:
                return json.load(f)
        # 输出为空才算真失败
        return {
            "error": f"subprocess rc={proc.returncode}, no output produced",
            "stderr": proc.stderr[:500],
        }
    except subprocess.TimeoutExpired:
        return {"error": "subprocess timeout"}
    except Exception as exc:
        return {"error": f"subprocess exception: {exc}"}
    finally:
        try:
            os.unlink(out_path)
        except OSError:
            pass


def count_fails(result: dict) -> tuple[int, int]:
    """粗略统计 total/failed(只看 status=fail 字段)。"""
    if not isinstance(result, dict):
        return 0, 0
    total, failed = 0, 0
    for v in result.values():
        if isinstance(v, dict) and "status" in v:
            total += 1
            if v.get("status") == "fail":
                failed += 1
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict) and "status" in item:
                    total += 1
                    if item.get("status") == "fail":
                        failed += 1
    return total, failed


def main():
    parser = argparse.ArgumentParser(
        description="一次性执行全部 4 个 verify 子脚本"
    )
    parser.add_argument("--from-toml", help="聚合 TOML 输入文件")
    parser.add_argument("--amounts", help="amounts.json 路径")
    parser.add_argument("--dates", help="dates.json 路径")
    parser.add_argument("--cross-refs", help="cross_refs.json 路径")
    parser.add_argument("--payment-flow", help="payment_flow.json 路径")
    parser.add_argument(
        "--output", "-o", default="verify_results.json", help="合并输出 JSON"
    )
    args = parser.parse_args()

    json_paths: dict[str, str | None] = {
        "amounts": args.amounts,
        "dates": args.dates,
        "cross_refs": args.cross_refs,
        "payment_flow": args.payment_flow,
    }

    tmpdir = None
    if args.from_toml:
        data = load_toml_as_dict(args.from_toml)
        tmpdir = tempfile.mkdtemp(prefix="verify_all_")
        for key in SUB_SCRIPTS:
            if key in data and isinstance(data[key], dict):
                json_paths[key] = write_temp_json(data[key], key, tmpdir)

    merged: dict = {}
    total_all, failed_all, exec_count, fail_script_count = 0, 0, 0, 0

    for key, script_name in SUB_SCRIPTS.items():
        jpath = json_paths.get(key)
        if not jpath or not os.path.isfile(jpath):
            merged[key] = {"skipped": True, "reason": "no input provided"}
            continue
        exec_count += 1
        result = run_sub_script(script_name, jpath)
        merged[key] = result
        if "error" in result:
            fail_script_count += 1
        else:
            t, f = count_fails(result)
            total_all += t
            failed_all += f

    merged["summary"] = {
        "total_checks": total_all,
        "failed_checks": failed_all,
        "scripts_executed": exec_count,
        "scripts_failed": fail_script_count,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"[OK] merged → {args.output}")
    print(
        f"     scripts: {exec_count} executed, {fail_script_count} failed. "
        f"checks: {failed_all}/{total_all} failed."
    )

    if tmpdir:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
