#!/usr/bin/env python3
"""商品下架 CLI 入口"""

COMMAND_NAME = "product_cancel_offer"
COMMAND_DESC = "下架商品"

import os
import sys
import argparse

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from _auth import get_ak_raw
from _output import make_output, print_output, print_error
from capabilities.product_cancel_offer.service import cancel_offer


def main():
    # 前置检查 AK
    try:
        get_ak_raw()
    except Exception:
        print_output(make_output(
            success=False,
            markdown="❌ AK 未配置，无法执行商品下架。\n\n"
                     "请执行 `python3 cli.py get_ak` 自动获取 AK。",
            data={"data": {}},
        ))
        return

    parser = argparse.ArgumentParser(description="商品下架")
    parser.add_argument("--offerId", "-o", nargs="+", required=True, help="要下架的商品 offerId（支持多个）")
    args = parser.parse_args()

    # 单个或多个统一转为列表
    offer_ids = args.offerId

    try:
        result = cancel_offer(offer_ids)

        # 从 API 响应的 data 中解析 success 和 message 判定操作结果
        api_success = False
        api_message = ""

        if isinstance(result, dict):
            data = result.get("data") if isinstance(result.get("data"), dict) else {}
            # 兼容 API 拼写："success" 或 "successs"（三个 s）
            data_success = data.get("success") if data.get("success") is not None else data.get("successs")
            api_message = data.get("message") or ""

            if data_success is True:
                api_success = True
            elif data_success is False:
                api_success = False
            else:
                # data 中无 success 字段时，回退到顶层 success
                api_success = result.get("success", False) is True

        # 错误消息翻译
        error_translations = {
            "user doesn't have these offer": "当前账号下没有该商品",
            "operate failed": "操作失败，请检查商品状态",
        }

        if api_success:
            translated_message = "下架成功"
            if len(offer_ids) == 1:
                md = f"✅ 商品 `{offer_ids[0]}` 下架成功"
            else:
                md = f"✅ {len(offer_ids)} 个商品下架成功：{', '.join(f'`{oid}`' for oid in offer_ids)}"
            print_output(make_output(
                success=True,
                markdown=md,
                data={"success": True, "message": translated_message},
            ))
        else:
            error_hint = api_message if api_message else "API 返回失败，请检查参数后重试"
            for eng, chn in error_translations.items():
                if eng in error_hint.lower():
                    error_hint = chn
                    break
            if len(offer_ids) == 1:
                md = f"❌ 商品 `{offer_ids[0]}` 下架失败：{error_hint}"
            else:
                md = f"❌ 商品下架失败：{error_hint}"
            print_output(make_output(
                success=False,
                markdown=md,
                data={"success": False, "message": error_hint},
            ))
    except Exception as e:
        print_error(e, {"data": {}})


if __name__ == "__main__":
    main()
