#!/usr/bin/env python3
"""
validate_product_payload.py — 对 skill 运行时输出的 JSON 做 product_list 载荷静态校验。

适用场景：
- 新建 / 调整 Tier 2/3 编排 skill 时，跑一份 mock 输出，确认是否符合
  references/output-contract.md §2.3.1 的 product_list payload。
- CI / 上线前的一键体检。

输入：
- 文件路径：`python scripts/validate_product_payload.py path/to/output.json`
- stdin：    `cat output.json | python scripts/validate_product_payload.py -`

退出码：
  0 - 通过（可能含 WARNINGS）
  1 - 有 ERRORS
  2 - 文件 / JSON 解析失败

校验范围：
  - 推荐：裸 payload `{ "products": [...], "total"?: n, "type"?: "productList" }`
  - 兼容（WARNING）：legacy `type: "skill-output"` + `props.data.products`
  - 每条 product：至少 asin 或 title；数值字段类型 / 单位合理

注意：本脚本不发起任何网络 / API 调用，纯静态结构校验。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _is_nonempty_str(v: Any) -> bool:
    return isinstance(v, str) and len(v.strip()) > 0


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def extract_product_list_data(
    payload: Any,
) -> tuple[dict[str, Any] | None, list[str], list[str]]:
    """从裸 payload 或 legacy envelope 中提取 product_list 数据对象。"""
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(payload, dict):
        errors.append(f"顶层必须是对象，实际为 {type(payload).__name__}")
        return None, errors, warnings

    if isinstance(payload.get("products"), list):
        return payload, errors, warnings

    if payload.get("type") == "skill-output":
        warnings.append(
            '检测到已废弃的 type:"skill-output" envelope；'
            "请改为裸 payload { products: [...] }，见 output-contract.md §2.3.1"
        )
        props = payload.get("props")
        if isinstance(props, dict) and isinstance(props.get("data"), dict):
            data = props["data"]
            if isinstance(data.get("products"), list):
                return data, errors, warnings
        errors.append("legacy envelope 中未找到 props.data.products 数组")
        return None, errors, warnings

    if isinstance(payload.get("data"), list) and payload.get("errcode") is not None:
        warnings.append("检测到 API envelope { errcode, data: [...] }；将按商品数组校验")
        return {"products": payload["data"]}, errors, warnings

    errors.append('未找到 products 数组；期望 { "products": [...] } 形状')
    return None, errors, warnings


def _validate_product_item(
    p: Any, idx: int, errors: list[str], warnings: list[str]
) -> None:
    path = f"products[{idx}]"
    if not isinstance(p, dict):
        errors.append(f"{path} 必须是对象")
        return

    has_asin = _is_nonempty_str(p.get("asin"))
    has_title = _is_nonempty_str(p.get("title"))
    if not (has_asin or has_title):
        errors.append(f"{path} 至少要有 asin 或 title 之一")

    if "asin" in p and p["asin"] is not None and not isinstance(p["asin"], str):
        errors.append(f"{path}.asin 必须是字符串")

    price = p.get("price")
    if price is not None and not _is_number(price):
        errors.append(f"{path}.price 必须是数字")

    rating = p.get("rating")
    if rating is not None:
        if not _is_number(rating):
            errors.append(f"{path}.rating 必须是数字")
        elif not (0 <= float(rating) <= 5):
            warnings.append(f"{path}.rating={rating} 超出 0~5 范围")

    units = p.get("unitsSold")
    if units is not None and not _is_number(units):
        errors.append(f"{path}.unitsSold 必须是数字")

    bsr = p.get("bsr")
    if bsr is not None and not _is_number(bsr):
        errors.append(f"{path}.bsr 必须是数字")

    seller = p.get("sellerCount")
    if seller is not None and not _is_number(seller):
        errors.append(f"{path}.sellerCount 必须是数字")
    if "sellerNum" in p and "sellerCount" not in p:
        warnings.append(f"{path} 用了旧字段 sellerNum，建议改名 sellerCount")

    revenue = p.get("revenue")
    if revenue is not None and not _is_number(revenue):
        errors.append(f"{path}.revenue 必须是数字")

    profit = p.get("profit")
    if profit is not None:
        if not _is_number(profit):
            errors.append(f"{path}.profit 必须是数字（百分比，已 ×100）")
        elif 0 < float(profit) < 1:
            warnings.append(
                f"{path}.profit={profit} 在 (0,1) 区间，疑似未 ×100（应写 12.3 表示 12.3%）"
            )

    ratings = p.get("ratings")
    if ratings is not None and not _is_number(ratings):
        errors.append(f"{path}.ratings 必须是数字")

    imgs = p.get("productImageUrls")
    if imgs is not None and not isinstance(imgs, list):
        errors.append(f"{path}.productImageUrls 必须是数组")

    five_point = p.get("aboutItemFivePoint")
    if five_point is not None and not isinstance(five_point, list):
        errors.append(f"{path}.aboutItemFivePoint 必须是数组")


def _validate_product_list_data(
    data: dict[str, Any], errors: list[str], warnings: list[str]
) -> None:
    products = data.get("products")
    if not isinstance(products, list):
        errors.append("products 必填且为数组")
        return
    if len(products) == 0:
        warnings.append("products 是空数组；若无结果建议在业务文案中说明")

    total = data.get("total")
    if total is not None:
        if not isinstance(total, int):
            errors.append("total 必须是整数")
        elif total < len(products):
            warnings.append(
                f"total={total} 小于 products 长度 {len(products)}，建议核对"
            )

    for i, p in enumerate(products):
        _validate_product_item(p, i, errors, warnings)


def validate_product_payload(payload: Any) -> tuple[bool, list[str], list[str]]:
    data, errors, warnings = extract_product_list_data(payload)
    if data is None:
        return False, errors, warnings
    _validate_product_list_data(data, errors, warnings)
    return len(errors) == 0, errors, warnings


def _load_payload(arg: str) -> Any:
    if arg == "-":
        text = sys.stdin.read()
        if not text.strip():
            print("ERROR: stdin 为空", file=sys.stderr)
            sys.exit(2)
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"ERROR: stdin 不是合法 JSON：{e}", file=sys.stderr)
            sys.exit(2)

    path = Path(arg)
    if not path.exists():
        print(f"ERROR: 找不到文件 {arg}", file=sys.stderr)
        sys.exit(2)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: {arg} 不是合法 JSON：{e}", file=sys.stderr)
        sys.exit(2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "对 skill 运行时输出 JSON 做 product_list 载荷静态校验。"
            " 详细契约见 references/output-contract.md §2.3.1。"
        )
    )
    parser.add_argument(
        "input",
        help="JSON 文件路径，或 - 从 stdin 读",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="把 WARNINGS 升级为 ERRORS",
    )
    args = parser.parse_args()

    payload = _load_payload(args.input)
    ok, errors, warnings = validate_product_payload(payload)

    if args.strict and warnings:
        errors.extend(warnings)
        warnings = []
        ok = len(errors) == 0

    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"  - {e}")
    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  - {w}")
    if ok:
        print("Product list payload is valid!")
        sys.exit(0)
    sys.exit(1)


if __name__ == "__main__":
    main()
