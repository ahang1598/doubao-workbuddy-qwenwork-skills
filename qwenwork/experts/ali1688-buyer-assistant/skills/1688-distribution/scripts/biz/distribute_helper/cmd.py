#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""铺货执行命令"""

import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')))
from scripts._sys._output import print_output, print_error
from scripts._sys._mcp import load_json_payload
from scripts.biz.distribute_helper.service import parse_distribute_result


def execute(app_key: str = "", shop_code: str = "", channel: str = "", offer_ids: str = "",
           shop_name: str = "", tool_name: str = "", mcp_result_file: str = ""):
    """执行铺货 MCP 结果后处理"""
    try:
        if not app_key or not shop_code or not channel or not offer_ids:
            print_output(False, "❌ 缺少必填参数（app_key, shop_code, channel, offer_ids）", {})
            return

        payload = load_json_payload(mcp_result_file or None)
        result = parse_distribute_result(payload)
        error_code = str(result.get("errorCode", ""))
        success_count = result.get("successCount", 0)
        fail_count = result.get("failCount", 0)
        all_count = result.get("allCount", 0)

        # 提取成功/失败的商品 ID 列表
        input_ids = [x.strip() for x in offer_ids.split(",") if x.strip()]
        success_ids = [str(x) for x in result.get("successOfferIds", [])]
        fail_ids = [str(x) for x in result.get("failOfferIds", [])]
        brand_invalid_ids = [str(x) for x in result.get("brandInvalidOfferIds", [])]

        # 如果接口未返回明细列表，根据总数推断
        if not success_ids and not fail_ids:
            if error_code in ("200", "0") and all_count >= len(input_ids):
                success_ids = input_ids
            elif error_code == "210" and brand_invalid_ids:
                fail_ids = [str(x) for x in brand_invalid_ids]
                success_ids = [x for x in input_ids if x not in fail_ids]

        # 识别未被接口处理的商品（传入但既不在成功也不在失败列表中）
        processed_ids = set(str(x) for x in success_ids) | set(str(x) for x in fail_ids)
        unprocessed_ids = [x for x in input_ids if x not in processed_ids]

        # 构建 markdown
        if error_code in ("200", "0"):
            if unprocessed_ids:
                md = f"⚠️ 铺货部分完成。成功 {success_count} 件，未处理 {len(unprocessed_ids)} 件，共传入 {len(input_ids)} 件"
            else:
                md = f"✅ 铺货完成！成功 {success_count} 件，共 {all_count} 件"
        elif error_code == "210":
            md = f"⚠️ 铺货部分成功。成功 {success_count} 件，失败 {fail_count} 件，共 {all_count} 件"
        elif error_code == "511":
            md = "❌ 铺货失败：下游店铺授权信息已失效，请重新授权后再试"
        elif error_code == "512":
            md = "❌ 铺货失败：您未完成铺货设置，请先完成设置后再铺货"
        elif error_code == "513":
            md = "❌ 铺货失败：品牌商品校验失败，所有商品均未通过品牌校验，请确认商品是否为授权品牌商品"
        elif error_code == "500":
            md = "❌ 铺货失败：三方工具服务请求错误（系统错误），请稍后重试或联系技术支持"
        else:
            md = f"❌ 铺货失败，请稍后重试或联系技术支持"

        # 目标店铺信息
        shop_info_parts = []
        if shop_name:
            shop_info_parts.append(f"店铺：{shop_name}")
        if tool_name:
            shop_info_parts.append(f"铺货工具：{tool_name}")
        if shop_info_parts:
            md += "\n" + " | ".join(shop_info_parts)

        # 商品 ID 明细
        if success_ids:
            md += f"\n- 成功商品 ID：{', '.join(str(x) for x in success_ids)}"
        if fail_ids:
            md += f"\n- 失败商品 ID：{', '.join(str(x) for x in fail_ids)}"
        if unprocessed_ids:
            md += f"\n- 未处理商品 ID：{', '.join(unprocessed_ids)}（接口未返回该商品的处理结果，可能原因：商品已下架/不支持该渠道/已铺过）"

        # 结束标记
        md += "\n\n---\n\n> ℹ️ 铺货结果到此结束。如有未铺货商品，请询问用户是否继续。"

        # 将明细列表也放入 data 供 Agent 使用
        result["successOfferIds"] = success_ids
        result["failOfferIds"] = fail_ids

        print_output(error_code in ("200", "0", "210"), md, result)
    except Exception as e:
        print_error(e)
