#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""商品分销参谋数据查询命令"""

import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')))
from scripts._sys._output import print_output, print_error
from scripts._sys._mcp import load_json_payload
from scripts.biz.offer_info.service import parse_offer_info_result, extract_decision_factors


def query(offer_id: str = "", decision: str = "", mcp_result_file: str = ""):
    """查询商品分销参谋数据 MCP 结果后处理"""
    try:
        if not offer_id:
            print_output(False, "❌ 缺少必填参数 offer_id", {})
            return

        payload = load_json_payload(mcp_result_file or None)
        raw_data = parse_offer_info_result(payload, offer_id=offer_id)

        if decision and decision.lower() in ("true", "1", "yes"):
            factors = extract_decision_factors(raw_data)
            markdown = _format_decision_factors(offer_id, factors, offer_id)
            print_output(True, markdown, {"raw": raw_data, "decision_factors": factors})
        else:
            markdown = f"✅ 商品 {offer_id} 的分销参谋数据查询成功"
            print_output(True, markdown, raw_data)
    except Exception as e:
        print_error(e)


def _format_decision_factors(offer_id: str, factors: dict, raw_offer_id: str = "") -> str:
    """将决策因素格式化为可读的 Markdown。"""
    lines = [f"### 商品 {offer_id} 分销参谋分析\n"]

    if factors.get("onePiecePrice"):
        lines.append(f"- **一件包邮价**：¥{factors['onePiecePrice']}")
    if factors.get("multiPiecePrice"):
        lines.append(f"- **分销专属价**：¥{factors['multiPiecePrice']}（起批量 {factors.get('startNum', '-')}）")

    if factors.get("onePieceFreePostage"):
        lines.append("- **包邮**：✅ 支持一件包邮")
    elif factors.get("freePostage"):
        lines.append("- **包邮**：✅ 多件包邮")
    elif factors.get("freeDeliverFee"):
        lines.append("- **包邮**：✅ 包邮")
    else:
        cost = factors.get("freightCost")
        lines.append(f"- **运费**：¥{cost}" if cost else "- **运费**：需自付")

    if factors.get("officialLogistics"):
        lines.append("- **物流**：✅ 官方物流")

    if factors.get("isBrandOffer"):
        auth_status = "✅ 已授权" if factors.get("isBrandAuth") else "❌ 未授权"
        lines.append(f"- **品牌**：{factors.get('brandName', '品牌商品')}（{auth_status}）")
        if not factors.get("isBrandAuth"):
            oid = raw_offer_id or offer_id
            brand_url = f"https://air.1688.com/app/channel-fe/distribution-work/brand.html#/auth_apply?offerId={oid}"
            lines.append(f"  - 🚫 品牌未授权，不能铺货，有侵权风险 → [申请品牌授权]({brand_url})")

    if factors.get("alreadyUpgrade"):
        lines.append("- **分销品**：✅ 已升级为分销品")

    channels = factors.get("supportedChannels", [])
    if channels:
        lines.append(f"- **支持渠道**：{', '.join(channels)}")

    high_exp = factors.get("highExperienceScoreChannels", [])
    if high_exp:
        lines.append(f"- **高体验分渠道**：{', '.join(high_exp)}")

    high_lgt = factors.get("highPerfectLgtRateChannels", [])
    if high_lgt:
        lines.append(f"- **高履约率渠道**：{', '.join(high_lgt)}")

    protections = factors.get("protections", [])
    if protections:
        lines.append(f"- **服务保障**：{', '.join(protections)}")

    return "\n".join(lines)
