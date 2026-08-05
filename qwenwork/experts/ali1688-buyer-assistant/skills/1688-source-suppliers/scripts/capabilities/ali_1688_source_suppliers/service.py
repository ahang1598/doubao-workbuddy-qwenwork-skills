#!/usr/bin/env python3
"""1688供应商信息 MCP 结果后处理"""

import json
import sys
from pathlib import Path
from typing import Any, Optional

from _errors import ServiceError


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


def process_1688_source_suppliers_result(payload: Any, query: str = "") -> dict:
    """处理 MCP `1688_source_suppliers` 原始返回，不发起 HTTP/API 调用。"""
    result = unwrap_mcp_payload(payload)
    result = _loads_if_json(result)

    if not isinstance(result, dict):
        raise ServiceError("MCP 返回格式异常：期望 JSON 对象")

    if result.get("success") is False or result.get("__success__") is False:
        msg_info = result.get("msgInfo") or result.get("message") or result.get("error") or "未知错误"
        raise ServiceError(f"MCP 工具调用失败: {msg_info}")

    factories_info = _extract_factories_from_response(result)
    markdown_output = _generate_markdown_output(factories_info)

    return {
        "query": query,
        "factories": factories_info,
        "markdown": markdown_output,
        "raw": result,
    }


def _parse_json_field(field_value: str) -> list:
    """解析 JSON 数组字段，例如: "[\"OEM\",\"ODM\"]" -> ["OEM", "ODM"]"""
    if not field_value:
        return []
    try:
        result = json.loads(field_value)
        return result if isinstance(result, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _find_retrieval_data(data_list: list) -> list:
    """从列表中查找 RETRIEVAL 阶段的数据"""
    for item in data_list:
        if isinstance(item, dict) and item.get("currentPhase") == "RETRIEVAL":
            response_data = item.get("responseData", {})
            if isinstance(response_data, dict) and "data" in response_data:
                factories = response_data["data"]
                if isinstance(factories, list) and len(factories) > 0:
                    return factories
    return []


def _get_factories_data(result: dict) -> list:
    """从API响应中获取工厂数据列表
    
    支持三种数据格式：
    1. 顶层 originResponses 数组
    2. data.result.originResponses 数组
    3. data.result.model 数组
    """
    # 格式1 & 格式2：originResponses
    origin_responses = result.get("originResponses", [])
    if not origin_responses:
        origin_responses = result.get("data", {}).get("result", {}).get("originResponses", [])
    
    factories = _find_retrieval_data(origin_responses)
    if factories:
        return factories
    
    # 格式3：data.result.model
    model = result.get("data", {}).get("result", {}).get("model", [])
    if isinstance(model, list):
        factories = _find_retrieval_data(model)
        if factories:
            return factories
    
    return []


def _extract_factories_from_response(result: dict) -> list:
    """从API响应中提取所有工厂信息"""
    try:
        factories = _get_factories_data(result)
        
        extracted_factories = []
        for factory in factories:
            if not isinstance(factory, dict):
                continue
            
            ext_infos = factory.get("extInfos", {})
            
            # 基础信息
            company_name = factory.get("companyName", "")
            oem_mode = _parse_json_field(ext_infos.get("oem_mode", ""))
            manufacture_type = _parse_json_field(ext_infos.get("manufacture_type", ""))
            
            # 数据质量过滤
            if not company_name or not oem_mode or not manufacture_type:
                continue
            
            # 所在地区
            province = ext_infos.get("reg_prov_name", "")
            city = ext_infos.get("reg_city_name", "")
            location = f"{province}{city}" if province or city else ""
            
            extracted_factories.append({
                "companyName": company_name,
                "companyUrl": factory.get("companyUrl", ""),
                "cooperationMode": oem_mode,
                "services": manufacture_type,
                "location": location,
                "factoryLevel": ext_infos.get("factory_level", ""),
                "factoryType": _parse_json_field(ext_infos.get("factory_type_tag", [])),
                "recTags": _parse_json_field(ext_infos.get("rec_tags", [])),
                "satisfiedRate": ext_infos.get("satisfied_rate_std_001", ""),
                "monthlyOrders": ext_infos.get("pay_ord_byr_cnt_1m_004", 0),
                "supportProofing": ext_infos.get("is_proofing", "") == "Y",
                "score": factory.get("score", 0)
            })
        
        return extracted_factories
        
    except Exception as e:
        raise ServiceError(f"提取工厂信息失败: {e}")


def _generate_markdown_output(factories: list) -> str:
    """生成展示用的Markdown表格输出，公司名称可点击跳转"""
    if not factories:
        return "未找到供应商信息"
    
    lines = [f"找到 {len(factories)} 家供应商\n"]
    
    # 表头：公司名称带链接，不再单独显示链接列
    lines.append("| 序号 | 公司名称 | 所在地区 | 合作方式 | 服务 | 工厂信息 | 服务指标 |")
    lines.append("|:----:|---------|---------|---------|------|---------|---------|")
    
    for i, f in enumerate(factories, 1):
        # 公司名称（可点击链接）
        company_name = f.get("companyName", "-")
        company_url = f.get("companyUrl", "")
        if company_url:
            company_display = f"[{company_name}]({company_url})"
        else:
            company_display = company_name
        
        # 所在地区
        location = f.get("location", "-")
        
        # 合作方式
        cooperation = ", ".join(f.get("cooperationMode", [])) or "-"
        
        # 服务
        services = ", ".join(f.get("services", [])) or "-"
        
        # 工厂信息
        factory_info = []
        if f.get("factoryLevel"):
            factory_info.append(f["factoryLevel"])
        factory_type = ", ".join(f.get("factoryType", []))
        if factory_type:
            factory_info.append(factory_type)
        factory_str = ", ".join(factory_info) or "-"
        
        # 服务指标
        indicators = []
        if f.get("satisfiedRate"):
            indicators.append(f["satisfiedRate"])
        if f.get("monthlyOrders"):
            indicators.append(f"月{f['monthlyOrders']}单")
        if f.get("supportProofing"):
            indicators.append("支持打样")
        indicator_str = ", ".join(indicators) or "-"
        
        lines.append(f"| {i} | {company_display} | {location} | {cooperation} | {services} | {factory_str} | {indicator_str} |")
    
    return "\n".join(lines)
