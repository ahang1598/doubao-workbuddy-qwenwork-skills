import json
import sys
from pathlib import Path
from typing import Any, Optional

from _errors import ParamError, ServiceError


def load_json_payload(path: Optional[str] = None) -> Any:
    """从文件或 stdin 读取 MCP 工具返回 JSON。"""
    raw = Path(path).read_text(encoding="utf-8") if path else sys.stdin.read()
    raw = raw.strip()
    if not raw:
        raise ValueError("缺少 MCP 工具返回结果，请通过 --mcp-result-file 或 stdin 传入 JSON")
    return json.loads(raw)


def _loads_if_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return value
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def unwrap_mcp_payload(payload: Any) -> Any:
    """解开常见 MCP / JSON-RPC 包装，返回业务数据。"""
    payload = _loads_if_json(payload)

    if isinstance(payload, dict) and payload.get("error"):
        error = payload["error"]
        message = error.get("message") if isinstance(error, dict) else str(error)
        raise ServiceError(message or "MCP 工具调用失败")

    result = payload.get("result") if isinstance(payload, dict) and "result" in payload else payload

    if isinstance(result, dict) and result.get("isError"):
        content = result.get("content") or []
        if content and isinstance(content[0], dict):
            raise ServiceError(content[0].get("text") or "MCP 工具调用失败")
        raise ServiceError("MCP 工具调用失败")

    if isinstance(result, dict) and "content" in result:
        content = result.get("content") or []
        if content and isinstance(content[0], dict) and "text" in content[0]:
            return unwrap_mcp_payload(content[0]["text"])
        return content

    return result


def process_procurement_result(payload: Any, offer_name: str, count: str, demand: str) -> dict:
    """
    处理 MCP `1688_procurement_digital_human_tool` 返回结果。

    Args:
        offer_name: 商品名称，如 "衣服"、"螺丝"
        count: 采购数量，如 "10"
        demand: 采购需求描述，如 "价格便宜"、"要求包邮"
        payload: MCP 工具原始返回

    Returns:
        标准后处理结果数据

    Raises:
        ParamError: 参数缺失或不合法
        ServiceError: MCP 返回异常
    """
    if not offer_name:
        raise ParamError("商品名称（offerName）不能为空")
    if not count:
        raise ParamError("采购数量（count）不能为空")
    if not count.isdigit():
        raise ParamError("采购数量（count）必须是纯数字，不能包含单位（如\"斤\"、\"件\"等），请去掉单位后重试")
    if not demand:
        raise ParamError("采购需求（demand）不能为空")

    result = unwrap_mcp_payload(payload)
    result = _loads_if_json(result)

    if not isinstance(result, (dict, str, list)):
        raise ServiceError("MCP 返回格式异常，请稍后重试")

    if isinstance(result, dict) and (result.get("success") is False or result.get("__success__") is False):
        message = result.get("message") or result.get("msgInfo") or result.get("error") or "MCP 工具调用失败"
        raise ServiceError(str(message))

    return {
        "offerName": offer_name,
        "count": count,
        "demand": demand,
        "raw": result,
    }