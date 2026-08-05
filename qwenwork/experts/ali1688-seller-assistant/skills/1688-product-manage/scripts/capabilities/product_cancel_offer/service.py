#!/usr/bin/env python3
"""商品下架服务"""

from _http import api_post_raw
from _auth import get_user_id
from _errors import ParamError


def cancel_offer(offer_ids) -> dict:
    """
    下架指定商品（支持单个或批量）。

    API: POST /api/product_cancel_offer/1.0.0
    请求体: {"offerIds": ["id1", "id2", ...], "__userId__": "<auto>"}
    userId 由 get_user_id() 从 AK 中提取。

    Args:
        offer_ids: 单个 offerId (str) 或 offerId 列表 (list[str])

    Returns:
        网关返回的完整响应（包含 success 字段）

    Raises:
        ParamError / AuthError / RateLimitError / ServiceError
    """
    # 统一转为列表
    if isinstance(offer_ids, str):
        offer_ids = [offer_ids]
    if not isinstance(offer_ids, list):
        offer_ids = list(offer_ids)

    # 清洗并校验
    offer_ids = [str(oid).strip() for oid in offer_ids if str(oid).strip()]
    if not offer_ids:
        raise ParamError("offerIds 不能为空")

    user_id = get_user_id()

    return api_post_raw(
        "/api/product_cancel_offer/1.0.0",
        {"offerIds": offer_ids, "__userId__": user_id},
    )
