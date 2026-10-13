#!/usr/bin/env python3
"""
在钉钉多维表中创建「SKU商品表」

说明：
- 在指定 Base 下创建名为「SKU商品表」的数据表
- 包含 31 个字段（ID、排序、图片、款号、名称、条码、颜色、尺码、库存、卖点、特征标签 等）
- 因 aitable table create 单次最多 15 个字段，分两批完成：先建表（前15个字段），再追加剩余字段

用法：
    python scripts/create_sku_table.py --base-id <BASE_ID>

输出：JSON { success, baseId, tableId, tableUrl }
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "references" / "sku_table_field_schema.json"
TABLE_NAME = "SKU商品表"
MAX_FIELDS_PER_BATCH = 15

# ── dws 工具函数（复用 try_on_cli.py 的查找逻辑） ──────────────────────────

DWS_SEARCH_PATHS = [
    "~/.qoderwork/bin/dws",
    "~/.local/bin/dws",
    "dws",
]


def resolve_dws_binary() -> str:
    """查找 dws 可执行文件路径。"""
    for candidate in DWS_SEARCH_PATHS:
        expanded = str(Path(candidate).expanduser())
        if Path(expanded).is_file():
            return expanded
    found = shutil.which("dws")
    if found:
        return found
    print(json.dumps({"success": False, "error": "找不到 dws 命令，请确认已安装 dws CLI 工具"}))
    sys.exit(1)


def run_dws(args: list[str], timeout: int = 120) -> dict | None:
    """执行 dws 命令并返回解析后的 JSON 结果。"""
    dws_bin = resolve_dws_binary()
    cmd = [dws_bin] + args
    print(f"执行命令: {' '.join(cmd)}", file=sys.stderr)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
        if result.returncode != 0:
            print(f"错误：{result.stderr.strip()}", file=sys.stderr)
            return None
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        print(f"错误：命令执行超时（{timeout}秒）", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print(f"无法解析响应：{result.stdout[:300]}...", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("错误：未找到 dws 命令", file=sys.stderr)
        return None


def extract_table_id(result: dict) -> str | None:
    """从 dws 响应中提取 tableId。"""
    result_data = result.get("data", result)
    if isinstance(result_data, dict):
        table_id = result_data.get("tableId")
        if table_id:
            return table_id
    table_id = result.get("tableId")
    if table_id:
        return table_id
    tables = result.get("tables", [])
    if tables:
        return tables[0].get("tableId")
    return None


# ── 主逻辑 ────────────────────────────────────────────────────────────────────

def create_sku_table(base_id: str) -> dict | None:
    """在指定 Base 下创建 SKU 商品表，返回结果字典。"""
    with open(SCHEMA_PATH, encoding="utf-8") as schema_file:
        schema = json.load(schema_file)

    all_fields = schema["fields"]

    # 第一批：建表（前 MAX_FIELDS_PER_BATCH 个字段）
    first_batch = all_fields[:MAX_FIELDS_PER_BATCH]
    remaining_fields = all_fields[MAX_FIELDS_PER_BATCH:]

    print(f"正在创建 {TABLE_NAME}（第1批 {len(first_batch)} 个字段）...", file=sys.stderr)
    fields_json = json.dumps(first_batch, ensure_ascii=False)
    result = run_dws([
        "aitable", "table", "create",
        "--base-id", base_id,
        "--name", TABLE_NAME,
        "--fields", fields_json,
        "--format", "json",
    ])

    if not result:
        return None

    table_id = extract_table_id(result)
    if not table_id:
        print(f"错误：无法从响应中提取 tableId：{json.dumps(result, ensure_ascii=False)}", file=sys.stderr)
        return None

    print(f"{TABLE_NAME} 已创建，tableId: {table_id}", file=sys.stderr)

    # 第二批：追加剩余字段
    if remaining_fields:
        print(f"正在追加剩余 {len(remaining_fields)} 个字段...", file=sys.stderr)
        for field in remaining_fields:
            field_json = json.dumps(field, ensure_ascii=False)
            add_result = run_dws([
                "aitable", "field", "add",
                "--base-id", base_id,
                "--table-id", table_id,
                "--field", field_json,
                "--format", "json",
            ])
            if not add_result:
                print(f"警告：追加字段 {field['fieldName']} 失败，请手动添加", file=sys.stderr)

    print(f"全部 {len(all_fields)} 个字段创建完成", file=sys.stderr)

    table_url = f"https://aitable.ai/workbench/{base_id}/{table_id}"
    return {
        "success": True,
        "baseId": base_id,
        "tableId": table_id,
        "tableUrl": table_url,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description=f"创建 {TABLE_NAME}")
    parser.add_argument("--base-id", required=True, help="多维表 Base ID")
    args = parser.parse_args()

    result = create_sku_table(args.base_id)
    if result:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(json.dumps({"success": False, "error": f"创建 {TABLE_NAME} 失败"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
