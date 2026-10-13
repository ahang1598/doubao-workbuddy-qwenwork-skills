#!/usr/bin/env python3
"""
数据源切换脚本

逻辑：
1. 调用 ensure-aitable 接口确保多维表已创建（已有则直接返回，否则自动创建）
2. 用返回的 aitableDentryUuid 作为 BASE_ID
3. 用 BASE_ID 调用 init_aitable_tables.py 初始化所有表

用法：
    python scripts/switch_datasource.py
    python scripts/switch_datasource.py --source mongodb

输出：JSON { success, baseId, created, skipped }
"""

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
CLI_SCRIPT = SCRIPTS_DIR / "cli.py"
INIT_TABLES_SCRIPT = SCRIPTS_DIR / "init_aitable_tables.py"


def run_cli(args: list[str]) -> dict | None:
    """执行 cli.py 命令并返回解析后的 JSON。"""
    cmd = [sys.executable, str(CLI_SCRIPT)] + args
    print(f"执行: {' '.join(cmd)}", file=sys.stderr)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=120)
        if result.returncode != 0:
            print(f"错误: {result.stderr.strip()}", file=sys.stderr)
            if result.stdout.strip():
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    pass
            return None
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        print("错误: 命令执行超时", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print(f"无法解析响应: {result.stdout[:300]}", file=sys.stderr)
        return None


def get_store_detail() -> dict | None:
    """获取店铺详情。"""
    result = run_cli(["try-on", "store-detail"])
    if not result or not result.get("success"):
        return None
    return result.get("store", {})


def ensure_aitable() -> dict | None:
    """确保多维表已创建，返回 { aitableDentryUuid, created }。"""
    result = run_cli(["try-on", "ensure-aitable"])
    if not result or not result.get("success"):
        return None
    return result.get("result", {})


def switch_sku_source(aitable_url: str) -> dict | None:
    """切换 SKU 数据源到多维表。"""
    result = run_cli(["try-on", "sku-source", "--aitable-url", aitable_url])
    if not result or not result.get("success"):
        return None
    return result.get("skuSource", {})


def switch_to_mongodb() -> dict | None:
    """切换 SKU 数据源回系统数据库。"""
    result = run_cli(["try-on", "sku-source", "--source", "mongodb"])
    if not result or not result.get("success"):
        return None
    return result.get("skuSource", {})


def init_all_tables(base_id: str) -> dict | None:
    """调用 init_aitable_tables.py 初始化所有表。"""
    cmd = [sys.executable, str(INIT_TABLES_SCRIPT), "--base-id", base_id]
    print(f"执行: {' '.join(cmd)}", file=sys.stderr)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=300)
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        print("错误: 初始化表超时", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print(f"无法解析响应: {result.stdout[:300]}", file=sys.stderr)
        return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="数据源切换：确保多维表已创建 → 初始化所有表")
    parser.add_argument("--source", required=False, default="",
                        help="切换数据源类型：aitable 或 mongodb")
    args = parser.parse_args()

    # 切换回 MongoDB 模式
    if args.source == "mongodb":
        result = switch_to_mongodb()
        if result:
            print(json.dumps({"success": True, "source": "mongodb", "result": result}, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"success": False, "error": "切换到 MongoDB 失败"}, ensure_ascii=False))
            sys.exit(1)
        return

    # 调用 ensure-aitable 接口：已有多维表则直接返回，否则自动创建
    print("正在确保多维表已创建...", file=sys.stderr)
    aitable_result = ensure_aitable()
    if not aitable_result:
        print(json.dumps({"success": False, "error": "多维表创建失败，请确认店铺已初始化"}, ensure_ascii=False))
        sys.exit(1)

    base_id = aitable_result.get("aitableDentryUuid", "")
    if not base_id:
        print(json.dumps({"success": False, "error": "无法获取多维表 BASE_ID"}, ensure_ascii=False))
        sys.exit(1)

    newly_created = aitable_result.get("created", False)
    if newly_created:
        print(f"已自动创建多维表，BASE_ID: {base_id}", file=sys.stderr)
    else:
        print(f"多维表已存在，BASE_ID: {base_id}", file=sys.stderr)

    # 初始化所有表
    print(f"正在初始化所有表...", file=sys.stderr)
    init_result = init_all_tables(base_id)

    if not init_result or not init_result.get("success"):
        print(json.dumps({"success": False, "error": "初始化多维表失败", "baseId": base_id}, ensure_ascii=False))
        sys.exit(1)

    output = {
        "success": True,
        "source": "aitable",
        "baseId": base_id,
        "created": init_result.get("created", []),
        "skipped": init_result.get("skipped", []),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
