#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分销订单助手 - 查询 1688 分销订单/退款单信息、识别风险订单、自动催发催揽

功能：
1. 支持多种条件查询订单（订单 ID、创建时间、支付时间、订单状态、退款状态）
2. 查询退款单信息，支持退款状态跟踪
3. 自动识别风险订单
4. 订单结果展示（支持多种格式）
5. 发送旺旺消息给卖家
6. 批量催发风险订单
7. 生成催发消息模板
8. 查询商家回复记录（催发后定时查询）
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from scripts._sys._mcp import fail_if_tool_error, loads_if_json, unwrap_mcp_payload
from scripts._sys._errors import ServiceError


# ==================== 配置常量 ====================

# 订单状态映射
ORDER_STATUS_MAP = {
    "cancel": "已取消",
    "cancelled": "已取消",
    "waitbuyerpay": "等待买家付款",
    "waitingsellerconfirm": "等待卖家确认",
    "waitbuyerreceive": "等待买家收货",
    "finish": "完成",
    "waitsellersend": "等待卖家发货",
    "success": "交易完成"
}

# 退款状态映射（支持多种格式）
REFUND_STATUS_MAP = {
    "": "无退款",
    # 小写无下划线格式
    "waitselleragree": "等待卖家同意",
    "refundsuccess": "退款成功",
    "refundclose": "退款关闭",
    "waitbuyermodify": "商家拒绝待修改",
    "waitbuyersend": "待寄回退货",
    "waitsellerreceive": "等待卖家确认收货",
    "waitbuyerreceive": "等待买家确认收货",
    # 小写有下划线格式
    "wait_seller_agree": "等待卖家同意",
    "refund_success": "退款成功",
    "refund_closed": "退款关闭",
    "wait_buyer_modify": "商家拒绝待修改",
    "wait_buyer_send": "待寄回退货",
    "wait_seller_receive": "等待卖家确认收货",
    "wait_buyer_receive": "等待买家确认收货"
}


# ==================== 订单查询 ====================

def query_order(
    order_id: Optional[str] = None,
    create_start_time: Optional[str] = None,
    create_end_time: Optional[str] = None,
    pay_start_time: Optional[str] = None,
    pay_end_time: Optional[str] = None,
    order_status: Optional[str] = None,
    refund_status: Optional[str] = None,
    auto_default_today: bool = True,
    payload=None,
) -> Dict:
    """
    查询订单

    参数：
    - order_id: 订单 ID（选填）
    - create_start_time: 创建开始时间（选填，格式：YYYY-MM-DD HH:mm:ss）
    - create_end_time: 创建结束时间（选填，格式：YYYY-MM-DD HH:mm:ss）
    - pay_start_time: 支付开始时间（选填，格式：YYYY-MM-DD HH:mm:ss）
    - pay_end_time: 支付结束时间（选填，格式：YYYY-MM-DD HH:mm:ss）
    - order_status: 订单状态（选填）
    - refund_status: 退款状态（选填）
    - auto_default_today: 是否自动应用默认查询当天（选填，默认 True）

    返回：
    {
        "success": bool,
        "orders": list,
        "totalCount": int,
        "queryStartTime": str,
        "queryEndTime": str,
        "error": str  (仅失败时)
    }
    """
    arguments = {}

    # 检查是否没有任何筛选条件
    has_filter = any([
        order_id, create_start_time, create_end_time,
        pay_start_time, pay_end_time, order_status, refund_status
    ])

    # 如果没有任何筛选条件且启用了自动默认查询，则设置当天的时间范围
    if not has_filter and auto_default_today:
        default_times = get_date_range(days_back=1)
        create_start_time = default_times[0]
        create_end_time = default_times[1]

    # 添加选填参数
    if order_id:
        arguments["orderId"] = order_id
    if create_start_time:
        arguments["createStartTime"] = create_start_time
    if create_end_time:
        arguments["createEndTime"] = create_end_time
    if pay_start_time:
        arguments["payStartTime"] = pay_start_time
    if pay_end_time:
        arguments["payEndTime"] = pay_end_time
    if order_status:
        arguments["orderStatus"] = order_status
    if refund_status:
        arguments["refundStatus"] = refund_status

    # 记录查询参数用于返回
    query_start_time = create_start_time
    query_end_time = create_end_time
    query_days_back = 1 if not has_filter and auto_default_today else None

    # MCP 调用由 Agent/连接器完成，这里只做返回结果后处理。
    response_data = unwrap_mcp_payload(payload)
    response_data = loads_if_json(response_data)
    fail_if_tool_error(response_data)

    if isinstance(response_data, dict) and isinstance(response_data.get("data"), dict):
        response_data = response_data["data"]
    model_data = response_data.get("model", {}) if isinstance(response_data, dict) else {}
    if not isinstance(model_data, dict):
        model_data = {}

    orders_data = model_data.get("orderList", [])
    total_count = model_data.get("totalCount", len(orders_data))

    parsed_orders = []
    for order in orders_data:
        parsed_orders.append(_parse_order(order))

    result = {
        "success": True,
        "orders": parsed_orders,
        "totalCount": total_count,
        "actualCount": len(parsed_orders),
        "queryStartTime": query_start_time,
        "queryEndTime": query_end_time,
        "queryDaysBack": query_days_back
    }

    if total_count > 3000:
        result["warning"] = (
            f"⚠️ 重要提示：符合条件的订单共有 {total_count} 笔，"
            f"但单次最多返回 3000 笔。建议增加筛选条件以获取更精准的结果。"
        )
    if not has_filter and auto_default_today:
        result["notice"] = f"未提供筛选条件，默认查询当天的订单（{create_start_time} 至 {create_end_time}），最多支持查询近 7 天"

    return result


def _parse_order(order: Dict) -> Dict:
    """解析单个订单数据，包含风险判断"""
    status_code = order.get("orderStatus", "")
    refund_status_code = order.get("refundStatus", "")
    risk_order_desc = order.get("riskOrderDesc", "")

    is_risk_order = False
    if risk_order_desc:
        is_cancelled_or_completed = status_code.lower() in [
            "cancel", "cancelled", "finish", "success"
        ]
        refund_ended = refund_status_code.lower() in [
            "refundsucceed", "refundsuccess", "refundclose", "success", "closed",
            "refund_success", "refund_closed"
        ]
        if not (is_cancelled_or_completed and refund_ended):
            is_risk_order = True

    return {
        "orderId": order.get("orderId"),
        "createTime": order.get("createTime"),
        "payTime": order.get("payTime"),
        "orderStatus": status_code,
        "orderStatusText": translate_order_status(status_code),
        "sellerLoginId": order.get("sellerLoginId"),
        "actualTotalFee": order.get("actualTotalFee"),
        "productName": order.get("productName"),
        "riskOrderDesc": risk_order_desc,
        "isRiskOrder": is_risk_order,
        "refundStatus": refund_status_code,
        "refundStatusText": translate_refund_status(refund_status_code)
    }


# ==================== 旺旺消息 ====================

def send_ww_message(question: str, order_ids: List[str], payload=None) -> Dict:
    """
    发送旺旺消息

    参数：
    - question: 问题内容（必填），即要发送给卖家的消息
    - order_ids: 关联的订单 ID 列表（必填），系统会自动根据订单 ID 定位卖家

    返回：
    {"success": True, "task_id": str} 或抛出 ServiceError
    """
    if not question:
        raise ServiceError("参数错误：question 为必填参数")

    if not order_ids or not isinstance(order_ids, list):
        raise ServiceError("参数错误：order_ids 为必填参数，必须是字符串数组")

    # fx_send_ww 返回的 data 结构：{"success": true, "model": "taskId"}
    response_data = unwrap_mcp_payload(payload)
    response_data = loads_if_json(response_data)
    fail_if_tool_error(response_data)

    if isinstance(response_data, dict) and isinstance(response_data.get("data"), dict):
        response_data = response_data["data"]
    model_data = response_data.get("model") if isinstance(response_data, dict) else response_data

    if isinstance(model_data, str) and model_data:
        return {
            "success": True,
            "task_id": model_data
        }
    else:
        msg = response_data.get("msg", "发送失败") if isinstance(response_data, dict) else f"发送失败：{model_data}"
        raise ServiceError(msg)


def query_ww_task_reply(task_id: str, payload=None) -> Dict:
    """
    查询商家回复记录

    参数：
    - task_id: 催发任务 ID（由 send_ww_message 返回）

    返回：
    {
        "success": bool,
        "hasReply": bool,
        "replies": list  # [{"question": str, "answer": str}, ...]
    }
    """
    if not task_id:
        raise ServiceError("参数错误：task_id 为必填参数")

    import json as _json

    response_data = unwrap_mcp_payload(payload)
    response_data = loads_if_json(response_data)
    fail_if_tool_error(response_data)

    if isinstance(response_data, dict) and isinstance(response_data.get("data"), dict):
        response_data = response_data["data"]
    model_data = response_data.get("model") if isinstance(response_data, dict) else None

    # model 可能是 JSON 字符串、list 或 dict
    if isinstance(model_data, str):
        try:
            replies = _json.loads(model_data)
            if not isinstance(replies, list):
                replies = [replies] if replies else []
        except Exception:
            replies = []
    elif isinstance(model_data, list):
        replies = model_data
    elif isinstance(model_data, dict):
        replies = model_data.get("replyList", []) or model_data.get("records", []) or []
    else:
        replies = []

    return {
        "success": True,
        "hasReply": len(replies) > 0,
        "replies": replies
    }


def batch_urge_sellers(orders: List[Dict], template: str = "default") -> Dict:
    """
    批量催促卖家发货

    参数：
    - orders: 订单列表（可以是混合订单，函数会自动筛选风险订单）
    - template: 消息模板（default/polite/urgent）

    返回：发送结果统计
    """
    if not orders:
        raise ServiceError("订单列表为空")

    # 按卖家分组（自动筛选风险订单）
    seller_orders = defaultdict(list)
    risk_count = 0
    for order in orders:
        if order.get("isRiskOrder"):
            seller_id = order.get("sellerLoginId")
            if seller_id:
                seller_orders[seller_id].append(order)
                risk_count += 1

    if not seller_orders:
        return {
            "success": False,
            "error": "没有需要催促的风险订单",
            "total_orders_checked": len(orders),
            "risk_orders_found": 0
        }

    total_sent = 0
    total_failed = 0
    results = []

    print(f"\n开始批量催发，共 {len(seller_orders)} 个卖家，{risk_count} 个风险订单...\n")

    for seller_login_id, orders_list in seller_orders.items():
        try:
            message = generate_urge_message(orders_list, template)

            print("=" * 80)
            print("📋 催发消息内容:")
            print("=" * 80)
            print(f"卖家：{seller_login_id}")
            print(f"订单数：{len(orders_list)} 个")
            if len(orders_list) == 1:
                print(f"订单 ID: {orders_list[0].get('orderId', '')}")
            else:
                order_ids_str = ", ".join([o.get("orderId", "") for o in orders_list])
                print(f"订单 ID: {order_ids_str}")
            print()
            print(message)
            print("=" * 80)
            print()

            order_ids = [o.get("orderId", "") for o in orders_list]
            result = send_ww_message(question=message, order_ids=order_ids)

            total_sent += 1
            results.append({
                "seller": seller_login_id,
                "orders_count": len(orders_list),
                "status": "success",
                "task_id": result.get("task_id")
            })
            print(f"✅ 已向 {seller_login_id} 发送催发消息（{len(orders_list)}个订单）")

        except Exception as e:
            total_failed += 1
            error_detail = str(e)
            results.append({
                "seller": seller_login_id,
                "orders_count": len(orders_list),
                "status": "failed",
                "error": error_detail
            })
            print(f"❌ 向 {seller_login_id} 发送失败：{error_detail}")

    print(f"\n催发完成！成功：{total_sent} / 失败：{total_failed}\n")

    return {
        "success": True,
        "total_sellers": len(seller_orders),
        "sent": total_sent,
        "failed": total_failed,
        "details": results
    }


def generate_urge_message(orders: List[Dict], template: str = "default") -> str:
    """
    生成催发消息

    参数：
    - orders: 订单列表
    - template: 消息模板类型（default/polite/urgent）
    """
    if not orders:
        return ""

    order_ids = ", ".join([o.get("orderId", "") for o in orders[:5]])
    if len(orders) > 5:
        order_ids += f" 等{len(orders)}个订单"

    if template == "polite":
        message = f"老板好，我这边有几个订单想催一下：{order_ids}，麻烦帮忙尽快安排发货哈，谢谢啦！"
    elif template == "urgent":
        message = f"老板，这几个订单已经超过 48 小时没有揽收了：{order_ids}，买家那边催得比较急，麻烦尽快处理一下哥！"
    else:  # default
        message = f"老板您好，我这边有几个订单需要发货：{order_ids}，麻烦尽快处理一下哦，谢谢！"

    return message


# ==================== 辅助函数 ====================

def get_date_range(days_back: int = 7) -> Tuple[str, str]:
    """
    获取最近 N 天的时间范围（按自然日计算）

    返回：(开始时间，结束时间) 格式：YYYY-MM-DD HH:mm:ss
    """
    today = datetime.now().date()
    start_date = today - timedelta(days=days_back - 1)
    end_date = today
    return (
        start_date.strftime("%Y-%m-%d") + " 00:00:00",
        end_date.strftime("%Y-%m-%d") + " 23:59:59"
    )


def translate_order_status(status_code: str) -> str:
    """翻译订单状态"""
    if not status_code:
        return "未知状态"
    return ORDER_STATUS_MAP.get(status_code.lower(), status_code)


def translate_refund_status(refund_status_code: str) -> str:
    """翻译退款状态"""
    if not refund_status_code:
        return "无退款"
    lower_code = refund_status_code.lower()
    if lower_code in REFUND_STATUS_MAP:
        return REFUND_STATUS_MAP[lower_code]
    return refund_status_code


# ==================== 展示函数 ====================

def display_orders(
    orders: List[Dict],
    total_count: int = None,
    show_summary: bool = True,
    days_back: int = 7,
    start_date: str = "",
    end_date: str = ""
) -> None:
    """展示订单汇总信息"""
    if total_count is None:
        total_count = len(orders)

    if show_summary:
        _print_detailed_summary(orders, total_count, days_back, start_date, end_date)


def _print_order_row(order: Dict, idx: int) -> None:
    """打印单行订单数据"""
    pay_time = order.get('createTime', '')
    amount = order.get('actualTotalFee', 0)
    risk_mark = "⚠️ " if order.get("isRiskOrder", False) else ""

    product_name = order.get('productName', '')
    if len(product_name) > 8:
        product_name = product_name[:8] + "..."

    status_text = order.get('orderStatusText', '未知状态')
    refund_status = order.get('refundStatus', '')
    refund_status_text = order.get('refundStatusText', '')

    if status_text == '已取消' and refund_status and refund_status != '':
        status_display = f"{status_text}({refund_status_text})"
    else:
        status_display = status_text

    print(f"{risk_mark}{idx:<4}{order.get('orderId', ''):<22}{product_name:<12}{status_display:<16}{pay_time:<20}¥{amount:<9.2f}")


def _print_detailed_summary(
    orders: List[Dict],
    total_count: int = None,
    days_back: int = 7,
    start_date: str = "",
    end_date: str = ""
) -> None:
    """打印详细的订单汇总信息"""
    if total_count is None:
        total_count = len(orders)

    actual_count = len(orders)
    risk_count = sum(1 for o in orders if o.get("isRiskOrder", False))
    normal_count = actual_count - risk_count
    refund_orders = [o for o in orders if o.get('refundStatus') and o.get('refundStatus') != '']
    refund_count = len(refund_orders)

    # 标题
    if start_date and end_date:
        print(f"\n## 📊 订单汇总（{start_date} 至 {end_date}）")
    elif days_back is not None:
        print(f"\n## 📊 近 {days_back} 天订单汇总")
    else:
        print(f"\n## 📊 订单查询结果")

    # 查询结果统计
    print("\n### 📈 查询结果统计")
    risk_percent = f" ({risk_count/total_count*100:.1f}%)" if total_count > 0 else ""
    print(f"- 总订单数：{total_count} 个（全部返回，无分页限制）")
    print(f"- 风险订单：{risk_count} 个{risk_percent}")
    print(f"- 正常订单：{normal_count} 个")
    print(f"- 退款订单：{refund_count} 个")

    # 订单列表
    print(f"\n### 📋 订单列表（共 {total_count} 条）")
    print()

    if actual_count == 0:
        print("暂无订单数据")
    else:
        print(f"{'序号':<6}{'订单 ID':<22}{'商品名称':<12}{'订单状态':<16}{'支付时间':<20}{'支付金额':<10}")
        if actual_count <= 10:
            for idx, order in enumerate(orders, 1):
                _print_order_row(order, idx)
        else:
            for idx, order in enumerate(orders[:8], 1):
                _print_order_row(order, idx)
            print(f"{'...':<6}{'...':<22}{'...':<12}{'...':<16}{'...':<20}{'...':<10}")
            for idx, order in enumerate(orders[-2:], actual_count - 1):
                _print_order_row(order, idx)

    # 风险订单明细
    print(f"\n### ⚠️ 风险订单明细（{risk_count} 个）")
    if risk_count > 0:
        risk_orders = [o for o in orders if o.get("isRiskOrder", False)]
        risk_by_seller = defaultdict(list)
        for order in risk_orders:
            seller = order.get('sellerLoginId', '未知商家')
            risk_by_seller[seller].append(order)

        for seller, seller_risk_orders in sorted(risk_by_seller.items()):
            print(f"\n**商家：{seller}（{len(seller_risk_orders)} 个）**")
            print()
            for order in seller_risk_orders:
                pay_time = order.get('payTime') or order.get('createTime', '')
                risk_desc = order.get('riskOrderDesc', '')
                if '问题描述：' in risk_desc:
                    risk_desc = risk_desc.split('问题描述：')[1].split(';')[0]
                    if '，问题原因：' in risk_desc:
                        risk_desc = risk_desc.replace('，问题原因：', '，')

                print(f"订单 ID: {order.get('orderId', '')}")
                print(f"支付时间：{pay_time}")
                print(f"订单状态：{order.get('orderStatusText', '')}")
                print(f"风险描述：{risk_desc}")
                print(f"金额：¥{order.get('actualTotalFee', 0)}")
                if order.get('refundStatus') and order.get('refundStatus') != '':
                    print(f"退款状态：{order.get('refundStatusText', '')} ⚠️")
                print()
    else:
        print("暂无风险订单")

    # 退款订单明细
    print(f"\n### 💰 退款订单明细（{refund_count} 个）")
    if refund_count > 0:
        refund_by_status = defaultdict(list)
        for order in refund_orders:
            status_text = order.get('refundStatusText', '未知状态')
            refund_by_status[status_text].append(order)

        for status_text, status_orders in sorted(refund_by_status.items()):
            order_ids = [o.get('orderId', '') for o in status_orders]
            is_risk_flags = [o.get('isRiskOrder', False) for o in status_orders]
            if len(status_orders) == 1:
                risk_note = "，同时也是风险订单" if is_risk_flags[0] else ""
                print(f"- {status_text}：1 笔（订单 {order_ids[0]}{risk_note}）")
            else:
                risk_count_in_group = sum(is_risk_flags)
                risk_note = f"（其中 {risk_count_in_group} 笔为风险订单）" if risk_count_in_group > 0 else ""
                print(f"- {status_text}：{len(status_orders)} 笔{risk_note}")
    else:
        print("暂无退款订单")

    print()
