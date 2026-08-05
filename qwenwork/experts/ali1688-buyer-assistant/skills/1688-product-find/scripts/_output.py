#!/usr/bin/env python3
"""
统一输出工具

所有 cmd.py 通过此模块输出 JSON，保证格式一致。
"""

import json
import math
import os
import tempfile
import html
from typing import Any, List, Dict, Optional
from functools import lru_cache
from pathlib import Path

from _errors import SkillError, AuthError, GatewayAuthError

def make_output(success: bool, markdown: str = "", data: dict = None,
               error_code: str = "", required_scope: str = "",
               current_scope: str = "") -> dict:
    """构建标准输出字典（仅包含非空字段）"""
    result = {"success": success}
    if markdown:
        result["markdown"] = markdown
    if data is not None:
        result["data"] = data
    if error_code:
        result["error_code"] = error_code
    if required_scope:
        result["required_scope"] = required_scope
    if current_scope:
        result["current_scope"] = current_scope
    return result

# 内部别名保持向后兼容
_make_output = make_output

def print_output(success_or_dict, markdown: str = "", data: dict = None):
    """打印标准 JSON 输出。

    支持两种调用方式：
    1. print_output(True, "msg", {"key": "val"})  — 旧接口，直接传参
    2. print_output(make_output(success=True, ...))  — 新接口，传入 dict
    """
    if isinstance(success_or_dict, dict):
        output = success_or_dict
    else:
        output = _make_output(success_or_dict, markdown, data)
    print(json.dumps(output, ensure_ascii=False, indent=2))


def print_error(e: Exception, default_data: dict = None):
    """将异常转为标准错误输出并打印"""
    if isinstance(e, GatewayAuthError):
        output = _make_output(
            success=False,
            error_code=e.error_code,
            markdown=e.message,
            required_scope=e.required_scope,
        )
    elif isinstance(e, AuthError):
        output = _make_output(
            success=False,
            markdown=f"❌ {e.message}\n\n请检查 `ali1688-buyer` MCP 连接器是否已完成 OAuth 授权；如授权过期，请在连接器设置中重新授权。",
            data=default_data,
        )
    elif isinstance(e, SkillError):
        output = _make_output(success=False, markdown=f"❌ {e.message}", data=default_data)
    elif isinstance(e, ValueError):
        output = _make_output(success=False, markdown=f"❌ 参数错误：{e}", data=default_data)
    else:
        output = _make_output(success=False, markdown=f"❌ 操作失败：{e}", data=default_data)
    print(json.dumps(output, ensure_ascii=False, indent=2))

def _truncate(text: str, max_len: int = 20) -> str:
    """截断过长文本"""
    if not text:
        return ""
    text = str(text).replace("|", "｜").replace("\n", " ").strip()  # 替换管道符和换行
    if len(text) > max_len:
        return text[:max_len-2] + ".."
    return text


def _format_number(n: int) -> str:
    """将大数字缩写为易读格式"""
    if n >= 10000_0000:
        return f"{n / 10000_0000:.1f}亿"
    if n >= 10000:
        return f"{n / 10000:.0f}万"
    return str(n)



def _clean_url(url: str) -> str:
    """去掉 URL 中的冗余查询参数，缩短原始字符长度"""
    if not url:
        return ""
    idx = url.find('?')
    return url[:idx] if idx != -1 else url


def _escape_cell(text: str) -> str:
    """转义表格单元格中的特殊字符"""
    if not text:
        return ""
    return str(text).replace("|", "｜").replace("\n", " ").strip()


def _parse_items(raw_list: List) -> List[str]:
    """从 JSON 字符串或字典列表中提取 value 值"""
    items = []
    for item in (raw_list or []):
        try:
            data = json.loads(item) if isinstance(item, str) else item
            value = data.get('value', '')
            if value:
                items.append(value)
        except (json.JSONDecodeError, AttributeError):
            continue
    return items


def format_products_table(products: List[Dict], header: Optional[str] = None) -> str:
    """
    将商品列表格式化为 Markdown 表格（7列版，含图片）
    
    表头：序号 | 图片 | 商品名称 | 价格 | 供应商 | 服务与卖点 | 链接
    商品图片使用 Markdown 图片语法展示；商品名称完整展示；服务与卖点分行显示。
    
    Args:
        products: 商品列表
        header: 可选的表格前置标题/描述
    
    Returns:
        Markdown 格式的表格字符串
    """
    if not products:
        return "未找到匹配商品"
    
    # 过滤 API 返回的空数据（无标题且无详情链接的记录）
    valid_products = [p for p in products if p.get('title') or p.get('detail_url')]
    
    if not valid_products:
        return "未找到匹配商品"
    
    lines = []
    
    # 添加可选的标题
    if header:
        lines.append(header)
        lines.append("")
    
    # 7列表头（含商品图片）
    lines.append("| 序号 | 图片 | 商品名称 | 价格 | 供应商 | 服务与卖点 | 链接 |")
    lines.append("|:-:|:----:|:-----|------:|:------|:------|:----:|")
    
    # 表格内容
    for idx, p in enumerate(valid_products, 1):
        # 商品图片
        image_url = p.get('image_url', '')
        image_cell = f"![商品图]({image_url})" if image_url else "-"
        
        # 商品名称：纯文本，完整展示
        title = _escape_cell(p.get('title', '未知商品'))
        
        # 价格
        price = p.get('price')
        price_str = f"￥{price}" if price is not None else "-"
        
        # 供应商：截断8字符
        supplier = _truncate(p.get('supplier') or "-", 8)
        
        # 保障服务与卖点信息，分行显示
        services = _parse_items(p.get('service_infos', []))
        points = _parse_items(p.get('selling_points', []))
        
        tag_parts = []
        if services:
            tag_parts.append(f"🛡️ {'、'.join(services)}")
        if points:
            tag_parts.append(f"🏷️ {'、'.join(points)}")
        tag_cell = "<br>".join(tag_parts) if tag_parts else "-"
        
        # 链接：单独一列，去掉冗余参数缩短 URL
        detail_url = _clean_url(p.get('detail_url', ''))
        link_cell = f"[详情]({detail_url})" if detail_url else "-"
        
        lines.append(f"| {idx} | {image_cell} | {title} | {price_str} | {supplier} | {tag_cell} | {link_cell} |")
    
    return "\n".join(lines)


def _format_yx_index(p: Dict) -> str:
    """严选指数格式化：保留两位小数，截断不四舍五入"""
    yx_index = p.get('yx_index')
    if yx_index is not None:
        truncated = math.trunc(float(yx_index) * 100) / 100
        return f"{truncated:.2f}"
    return "-"


def _format_quantity(p: Dict) -> str:
    """起批量格式化：拼接 quantity_begin 和 unit"""
    quantity = p.get('quantity_begin')
    unit = p.get('unit') or ""
    if quantity is not None:
        return f"{int(quantity)}{unit}" if unit else str(int(quantity))
    return "-"


def _format_single_product_card(p: Dict, header: Optional[str] = None) -> str:
    """
    单款商品卡片式展示。
    当三个维度均指向同一商品时使用，用简洁的键值对形式展示。
    """
    lines = []
    if header:
        lines.append(header)
        lines.append("")

    label = p.get("_compare_label", "推荐")
    lines.append(f"**🏆 {label}**")
    lines.append("")

    # 用简单表格展示各维度
    lines.append("| 维度 | 详情 |")
    lines.append("|:-----|:-----|")
    lines.append(f"| 商品 | {_escape_cell(p.get('title', '未知商品'))} |")

    image_url = p.get('image_url', '')
    lines.append(f"| 📷 图片 | {f'![商品图]({image_url})' if image_url else '-'} |")

    price = p.get('price')
    lines.append(f"| 💰 单价 | {f'￥{price}' if price is not None else '-'} |")
    lines.append(f"| 📦 规格 | {_escape_cell(p.get('sku_title') or '-')} |")
    lines.append(f"| ⭐ 严选指数 | {_format_yx_index(p)} |")
    lines.append(f"| 📊 起批量 | {_format_quantity(p)} |")

    sold = p.get('sold_count') or 0
    lines.append(f"| 销量 | {_format_number(int(sold)) if sold else '-'} |")

    stock = p.get('stock_amount') or 0
    lines.append(f"| 库存 | {'有货' if int(stock) > 0 else '缺货'} |")

    services = _parse_items(p.get('service_infos', []))
    lines.append(f"| 服务 | {'、'.join(services) if services else '-'} |")

    points = _parse_items(p.get('selling_points', []))
    lines.append(f"| 卖点 | {'、'.join(points) if points else '-'} |")

    lines.append(f"| 供应商 | {_truncate(p.get('supplier') or '-', 12)} |")

    url = _clean_url(p.get('detail_url', ''))
    lines.append(f"| 链接 | {f'[查看]({url})' if url else '-'} |")

    return "\n".join(lines)


def _format_multi_product_table(products: List[Dict], header: Optional[str] = None) -> str:
    """
    多款商品纵向对比 Markdown 表格。
    每列一款商品，每行一个对比维度。
    """
    lines = []
    if header:
        lines.append(header)
        lines.append("")

    # 表头
    col_headers = []
    for i, p in enumerate(products, 1):
        label = p.get("_compare_label", "推荐")
        col_headers.append(f"推荐 {i} ({label})")

    lines.append("| 维度 | " + " | ".join(col_headers) + " |")
    lines.append("|:-----" + "|:------" * len(products) + "|")

    # 商品名称
    cells = [_escape_cell(p.get('title', '未知商品')) for p in products]
    lines.append("| 商品 | " + " | ".join(cells) + " |")

    # 图片
    cells = [f"![商品图]({p.get('image_url', '')})" if p.get('image_url') else "-" for p in products]
    lines.append("| 📷 图片 | " + " | ".join(cells) + " |")

    # 单价
    cells = [f"￥{p.get('price')}" if p.get('price') is not None else "-" for p in products]
    lines.append("| 💰 单价 | " + " | ".join(cells) + " |")

    # 规格
    cells = [_escape_cell(p.get('sku_title') or "-") for p in products]
    lines.append("| 📦 规格 | " + " | ".join(cells) + " |")

    # 严选指数
    cells = [_format_yx_index(p) for p in products]
    lines.append("| ⭐ 严选指数 | " + " | ".join(cells) + " |")

    # 起批量
    cells = [_format_quantity(p) for p in products]
    lines.append("| 📊 起批量 | " + " | ".join(cells) + " |")

    # 销量
    cells = [_format_number(int(p.get('sold_count') or 0)) if p.get('sold_count') else "-" for p in products]
    lines.append("| 销量 | " + " | ".join(cells) + " |")

    # 库存
    cells = ["有货" if int(p.get('stock_amount') or 0) > 0 else "缺货" for p in products]
    lines.append("| 库存 | " + " | ".join(cells) + " |")

    # 服务
    cells = []
    for p in products:
        services = _parse_items(p.get('service_infos', []))
        cells.append('、'.join(services) if services else "-")
    lines.append("| 服务 | " + " | ".join(cells) + " |")

    # 卖点
    cells = []
    for p in products:
        points = _parse_items(p.get('selling_points', []))
        cells.append('、'.join(points) if points else "-")
    lines.append("| 卖点 | " + " | ".join(cells) + " |")

    # 供应商
    cells = [_truncate(p.get('supplier') or "-", 12) for p in products]
    lines.append("| 供应商 | " + " | ".join(cells) + " |")

    # 链接
    cells = []
    for p in products:
        url = _clean_url(p.get('detail_url', ''))
        cells.append(f"[查看]({url})" if url else "-")
    lines.append("| 链接 | " + " | ".join(cells) + " |")

    return "\n".join(lines)


def format_compare_table(products: List[Dict], header: Optional[str] = None) -> str:
    """
    将比价商品列表格式化为 Markdown。

    - 多款商品：纵向对比表格，每列一款商品
    - 单款商品：卡片式展示（三个维度均为同一商品时）
    商品通过 _compare_label 标记维度标签（销量最高/价格最低/综合最优，可合并）。

    Args:
        products: 比价商品列表（已由 _select_top 标记 _compare_label）
        header: 可选的表格前置标题/描述

    Returns:
        Markdown 格式的比价内容字符串
    """
    if not products:
        return "未找到可比价的同款商品"

    # 过滤空数据
    valid = [p for p in products if p.get('title') or p.get('detail_url')]
    if not valid:
        return "未找到可比价的同款商品"

    # 单款商品 → 卡片式展示
    if len(valid) == 1:
        return _format_single_product_card(valid[0], header)

    # 多款商品 → 纵向对比表格
    return _format_multi_product_table(valid, header)

# ── [DISABLED] 以下函数已暂时禁用：可视化商品墙 & 后续操作引导 ──
# def _products_for_visual_payload(products: List[Dict]) -> List[Dict[str, Any]]:
#     """
#     将 API 商品列表整理为可视化页面前端所需的精简结构。
#
#     @param products: 原始商品字典列表
#     @returns 每项包含序号、展示字段与详情链接，供 JSON 嵌入 HTML
#     """
#     valid = [p for p in products if p.get("title") or p.get("detail_url")]
#     out: List[Dict[str, Any]] = []
#     for idx, p in enumerate(valid, 1):
#         services = _parse_items(p.get("service_infos", []))
#         points = _parse_items(p.get("selling_points", []))
#         price = p.get("price")
#         price_str = f"￥{price}" if price is not None else "-"
#         sim = p.get("similarity_score")
#         sim_str = None
#         if sim is not None:
#             try:
#                 sim_str = f"{float(sim):.0%}"
#             except (TypeError, ValueError):
#                 sim_str = str(sim)
#         out.append({
#             "index": idx,
#             "product_id": str(p.get("product_id", "") or ""),
#             "title": (p.get("title") or "未知商品").strip(),
#             "image_url": (p.get("image_url") or "").strip(),
#             "detail_url": (p.get("detail_url") or "").strip(),
#             "price_str": price_str,
#             "supplier": (p.get("supplier") or "-").strip() or "-",
#             "tags": (services + points)[:6],
#             "similarity_str": sim_str,
#         })
#     return out
#
#
# def _json_embed_in_script(obj: Any) -> str:
#     """将对象序列化为可安全嵌入 <script> 的 JSON（防止 </script> 截断）。"""
#     return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c")
#
#
# @lru_cache(maxsize=1)
# def _products_view_html_template() -> str:
#     """读取与 output.py 同目录下 templates/product_list.html（含占位符，见 build_products_view_html）。"""
#     path = Path(__file__).resolve().parent / "templates" / "product_list.html"
#     return path.read_text(encoding="utf-8")
#
#
# def build_products_view_html(
#     products: List[Dict],
#     page_title: str = "1688 商品结果",
#     subtitle: str = "",
# ) -> str:
#     """
#     基于商品数据生成单文件 HTML：网格卡片、点击勾选、打开详情、复制选中链接。
#
#     @param products: 与 format_products_table 相同的商品列表
#     @param page_title: 页面标题与顶部主标题
#     @param subtitle: 可选副标题（如搜索词、图片来源说明）
#     @returns 完整 HTML 文档字符串（由同目录 templates/products_view.html 渲染，单文件可离线打开）
#     """
#     payload = _products_for_visual_payload(products)
#     if not payload:
#         return ""
#
#     data_js = _json_embed_in_script(payload)
#     sub_html = html.escape(subtitle) if subtitle else ""
#
#     page_title_esc = html.escape(page_title)
#     sub_block = f'<p class="sub">{sub_html}</p>' if subtitle else ""
#
#     tpl = _products_view_html_template()
#     return (
#         tpl.replace("@@@PAGE_TITLE_ESC@@@", page_title_esc)
#         .replace("@@@SUBTITLE_BLOCK@@@", sub_block)
#         .replace("@@@DATA_JS@@@", data_js)
#     )
#
#
# def write_products_html_file(html_content: str, prefix: str = "1688-products-") -> str:
#     """
#     将 HTML 写入系统临时目录并返回绝对路径。
#
#     @param html_content: 完整 HTML 字符串
#     @param prefix: 临时文件名前缀
#     @returns 已写入文件的绝对路径
#     """
#     fd, path = tempfile.mkstemp(prefix=prefix, suffix=".html", text=True)
#     try:
#         with os.fdopen(fd, "w", encoding="utf-8") as f:
#             f.write(html_content)
#     except Exception:
#         os.close(fd)
#         raise
#     return os.path.abspath(path)
#
#
# def append_visual_hint_markdown(message: str, html_path: Optional[str]) -> str:
#     """
#     在 Markdown 正文后追加可视化页面路径说明（不修改原有表格内容）。
#
#     @param message: 已有 Markdown（通常含表格）
#     @param html_path: 可视化 HTML 绝对路径，若为 None 则原样返回
#     @returns 追加提示后的 Markdown
#     """
#     if not html_path:
#         return message
#     return (
#         message
#         + "\n\n---\n\n"
#         + "📱 **可视化商品墙**（浏览器打开后可点击图片区域多选、复制选中链接）：\n\n"
#         + f"`{html_path}`\n"
#     )
#   def append_next_actions_markdown(message: str, product_count: int) -> str:
#       """
#       在 Markdown 正文末尾追加后续操作提示，引导用户选择展示方式。
#   
#       搜索成功且有商品结果时，提示用户可以：
#       1. 生成钉钉表格 —— 便于团队协作、批量管理
#       2. 生成可视化页面 —— 商品卡片展示，支持勾选、打开链接、下单
#   
#       @param message: 已有 Markdown（通常含表格 + 可视化提示）
#       @param product_count: 本次返回的商品数量
#       @returns 追加后续操作提示后的 Markdown
#       """
#       if product_count <= 0:
#           return message
#   
#       return (
#           message
#           + "\n\n---\n\n"
#           + f"共找到 **{product_count}** 个商品，你可以：\n\n"
#           + "- 回复 **「生成页面」** → 查看选品、挑选下单\n"
#           + "- 回复 **「生成钉钉表格」** → 团队协作管理\n"
#       )
#
# ── [/DISABLED] ──


def append_next_actions_markdown(message: str, product_count: int) -> str:
    """
    在 Markdown 正文末尾追加后续操作提示，引导用户生成钉钉表格。

    @param message: 已有 Markdown（通常含表格）
    @param product_count: 本次返回的商品数量
    @returns 追加后续操作提示后的 Markdown
    """
    if product_count <= 0:
        return message

    return (
        message
        + "\n\n---\n\n"
        + f"共找到 **{product_count}** 个商品，你可以：\n\n"
        + "- 回复 **「生成钉钉表格」** → 团队协作管理\n"
    )
