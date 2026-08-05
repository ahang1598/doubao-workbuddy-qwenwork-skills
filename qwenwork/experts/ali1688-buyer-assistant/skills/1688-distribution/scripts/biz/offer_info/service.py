#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""商品分销参谋数据查询服务"""

import os
import sys
from typing import List

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')))
from scripts._sys._mcp import fail_if_tool_error, loads_if_json, unwrap_mcp_payload
from scripts._sys._errors import ServiceError


def parse_offer_info_result(payload, offer_id: str = "") -> dict:
    """处理 MCP distribution_offer_info 返回结果。"""
    inner = unwrap_mcp_payload(payload)
    inner = loads_if_json(inner)
    fail_if_tool_error(inner)

    data = inner.get("data", {})
    if isinstance(data, dict) and "data" in data:
        result = data.get("data", {})
    else:
        result = data

    if not isinstance(result, dict):
        raise ServiceError(f"查询商品 {offer_id} 的分销参谋数据失败：返回数据格式异常")

    return result


def get_batch_offer_info(offer_ids: List[str]) -> dict:
    """
    批量查询多个商品的分销参谋数据已由 MCP 调用层负责。

    :param offer_ids: 商品 ID 列表
    :return: {offer_id: offer_info_dict, ...}
    """
    raise ServiceError("批量分销参谋 API 调用请由 MCP 侧完成；Python 仅处理单次 MCP 返回结果")


def extract_decision_factors(offer_info: dict) -> dict:
    """
    从分销参谋数据中提取选品决策关键因素。

    :param offer_info: get_offer_info 返回的原始数据
    :return: 结构化的决策因素
    """
    price_info = offer_info.get("priceInInfo", {}) or {}
    freight_info = offer_info.get("freightInfo", {}) or {}
    brand_info = offer_info.get("brandInfo", {}) or {}
    downstream = offer_info.get("downstreamPerformance", {}) or {}
    protections = offer_info.get("protectionInfoList", []) or []
    support_list = offer_info.get("supportList", []) or []
    advise_list = offer_info.get("adviseList", []) or []

    one_piece_price = _build_price(
        price_info.get("onePiecePriceInteger"),
        price_info.get("onePiecePriceDecimal"),
    )
    multi_piece_price = _build_price(
        price_info.get("multiPiecePriceInteger"),
        price_info.get("multiPiecePriceDecimal"),
    )

    supported_channels = [item.get("name", "") for item in support_list if item.get("name")]

    high_exp_channels = [
        item.get("name", "")
        for item in (downstream.get("highExperienceScoreList") or [])
        if item.get("name")
    ]

    high_lgt_channels = [
        item.get("name", "")
        for item in (downstream.get("highPerfectLgtRateList") or [])
        if item.get("name")
    ]

    protection_names = [p.get("serviceName", "") for p in protections if p.get("serviceName")]

    return {
        "onePiecePrice": one_piece_price,
        "multiPiecePrice": multi_piece_price,
        "startNum": price_info.get("startNum"),
        "onePieceFreePostage": price_info.get("onePieceFreePostage", False),
        "freePostage": price_info.get("freepostage", False),
        "freeDeliverFee": freight_info.get("freeDeliverFee", False),
        "officialLogistics": freight_info.get("officialLogistics", False),
        "freightCost": freight_info.get("totalCost"),
        "isBrandOffer": brand_info.get("isBrandOffer", False),
        "isBrandAuth": brand_info.get("isAuth", False),
        "brandName": brand_info.get("brandName", ""),
        "alreadyUpgrade": offer_info.get("alreadyUpgrade", False),
        "supportedChannels": supported_channels,
        "highExperienceScoreChannels": high_exp_channels,
        "highPerfectLgtRateChannels": high_lgt_channels,
        "protections": protection_names,
        "adviseList": advise_list,
    }


def _build_price(integer_part, decimal_part) -> str:
    """拼接价格字符串。"""
    if integer_part is None:
        return ""
    price = str(integer_part)
    if decimal_part:
        price += f".{decimal_part}"
    return price
