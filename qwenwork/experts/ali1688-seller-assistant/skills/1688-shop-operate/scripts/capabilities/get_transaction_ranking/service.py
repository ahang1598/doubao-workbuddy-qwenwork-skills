#!/usr/bin/env python3
"""行业交易排名数据查询服务"""

from _http import api_post
from _errors import ServiceError

VALID_DATE_TYPES = {"RECENT_7", "RECENT_30"}

def get_transaction_ranking(date_type: str = "RECENT_7") -> dict:
    """获取行业交易排名数据

    Args:
        date_type: 日期类型，仅支持 RECENT_7/RECENT_30（不支持 RECENT_1）

    Returns:
        API 响应 data 字段，包含行业排名、百分位、标杆数据
    """
    if date_type not in VALID_DATE_TYPES:
        raise ValueError(
            f"date_type 必须为 {', '.join(sorted(VALID_DATE_TYPES))} 之一（不支持 RECENT_1），"
            f"当前值: {date_type}"
        )

    data = api_post("/api/get_transaction_ranking/1.0.0", {
        "date_type": date_type,
        "device": "ALL",
    })

    if not isinstance(data, dict):
        raise ServiceError("格式异常，请稍后重试")

    return data
