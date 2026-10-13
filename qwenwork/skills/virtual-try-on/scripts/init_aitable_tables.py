#!/usr/bin/env python3
"""
一键初始化多维表所有表（SKU商品表 + 业务表）

说明：
- 自动检测多维表中已有哪些表（通过表名判断）
- 跳过已存在的表，只创建缺失的表
- 支持的表：SKU商品表、顾客表、预约表、订单表、心愿单、穿搭笔记、风格测评、试穿记录表
- SKU商品表字段较多（31个），自动分批创建（先建表再追加字段）

用法：
    python scripts/init_aitable_tables.py --base-id <BASE_ID>

输出：JSON { success, created: [...], skipped: [...] }
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

REFERENCES_DIR = Path(__file__).resolve().parent.parent / "references"

# 表名 → 字段 schema 文件的映射
TABLE_DEFINITIONS = {
    "SKU商品表": REFERENCES_DIR / "sku_table_field_schema.json",
    "顾客表": REFERENCES_DIR / "customer_table_field_schema.json",
    "预约表": REFERENCES_DIR / "booking_table_field_schema.json",
    "订单表": REFERENCES_DIR / "order_table_field_schema.json",
    "心愿单": REFERENCES_DIR / "wishlist_table_field_schema.json",
    "穿搭笔记": REFERENCES_DIR / "style_note_table_field_schema.json",
    "风格测评": REFERENCES_DIR / "style_analysis_table_field_schema.json",
    "试穿记录表": REFERENCES_DIR / "try_on_record_table_field_schema.json",
}

# SKU 商品表字段多，需分批创建（aitable table create 单次最多 15 个字段）
MAX_FIELDS_PER_BATCH = 15

# ── dws 工具函数 ──────────────────────────────────────────────────────────────

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


# ── 核心逻辑 ──────────────────────────────────────────────────────────────────

def list_existing_tables(base_id: str) -> set[str]:
    """查询多维表中已有的表名集合。"""
    result = run_dws([
        "aitable", "table", "list",
        "--base-id", base_id,
        "--format", "json",
    ])

    if not result:
        return set()

    data = result.get("data", result)
    tables = data.get("tables", [])
    return {table.get("tableName", "") for table in tables}


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


def create_table(base_id: str, table_name: str, schema_path: Path) -> dict | None:
    """创建单张表，返回结果。SKU商品表自动分批创建。"""
    with open(schema_path, encoding="utf-8") as schema_file:
        raw_schema = json.load(schema_file)

    # SKU 表 schema 格式为 {"fields": [...]}, 其他表直接是 [...]
    if isinstance(raw_schema, dict) and "fields" in raw_schema:
        fields = raw_schema["fields"]
    else:
        fields = raw_schema

    needs_batch = len(fields) > MAX_FIELDS_PER_BATCH

    # 第一批字段建表
    first_batch = fields[:MAX_FIELDS_PER_BATCH] if needs_batch else fields
    print(f"正在创建「{table_name}」（{len(fields)} 个字段{', 分批创建' if needs_batch else ''}）...", file=sys.stderr)

    fields_json = json.dumps(first_batch, ensure_ascii=False)
    result = run_dws([
        "aitable", "table", "create",
        "--base-id", base_id,
        "--name", table_name,
        "--fields", fields_json,
        "--format", "json",
    ])

    if not result:
        return None

    table_id = extract_table_id(result)

    if not table_id:
        print(f"  ⚠️ 「{table_name}」创建成功但无法提取 tableId", file=sys.stderr)
        return {"tableName": table_name, "tableId": None}

    # 分批追加剩余字段
    if needs_batch:
        remaining_fields = fields[MAX_FIELDS_PER_BATCH:]
        print(f"  正在追加剩余 {len(remaining_fields)} 个字段...", file=sys.stderr)
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
                print(f"  ⚠️ 追加字段「{field.get('fieldName', '?')}」失败", file=sys.stderr)

    print(f"  ✅ 「{table_name}」已创建，tableId: {table_id}", file=sys.stderr)
    return {"tableName": table_name, "tableId": table_id}


def init_all_tables(base_id: str) -> None:
    """检测并初始化所有缺失的业务表。"""
    print(f"正在查询 Base {base_id} 中已有的表...", file=sys.stderr)
    existing_tables = list_existing_tables(base_id)
    print(f"已有 {len(existing_tables)} 张表: {', '.join(existing_tables) or '（空）'}", file=sys.stderr)

    created = []
    skipped = []

    for table_name, schema_path in TABLE_DEFINITIONS.items():
        if table_name in existing_tables:
            print(f"  ⏭️  「{table_name}」已存在，跳过", file=sys.stderr)
            skipped.append(table_name)
            continue

        if not schema_path.exists():
            print(f"  ❌ 「{table_name}」的 schema 文件不存在: {schema_path}", file=sys.stderr)
            continue

        result = create_table(base_id, table_name, schema_path)
        if result:
            created.append(result)
        else:
            print(f"  ❌ 「{table_name}」创建失败", file=sys.stderr)

    output = {
        "success": True,
        "baseId": base_id,
        "created": created,
        "skipped": skipped,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def main():
    import argparse
    parser = argparse.ArgumentParser(description="一键初始化多维表所有业务表（自动跳过已存在的表）")
    parser.add_argument("--base-id", required=True, help="多维表 Base ID（即 dentryUuid）")
    args = parser.parse_args()

    init_all_tables(args.base_id)


if __name__ == "__main__":
    main()
