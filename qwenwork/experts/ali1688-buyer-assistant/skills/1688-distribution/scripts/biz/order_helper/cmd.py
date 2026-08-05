#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分销订单助手命令 - 订单查询、旺旺催发催揽"""

import os
import sys
import io
import contextlib

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')))
from scripts._sys._output import print_output, print_error
from scripts._sys._mcp import load_json_payload
from scripts.biz.order_helper.service import (
    query_order, display_orders,
    send_ww_message, query_ww_task_reply,
    batch_urge_sellers, generate_urge_message
)


def query(
    order_id: str = "",
    create_start_time: str = "",
    create_end_time: str = "",
    pay_start_time: str = "",
    pay_end_time: str = "",
    order_status: str = "",
    refund_status: str = "",
    auto_default_today: str = "true",
    mcp_result_file: str = ""
):
    """
    查询订单

    用法：
      python3 scripts/cli.py order_helper query
      python3 scripts/cli.py order_helper query --order_id=4502201509012068443
      python3 scripts/cli.py order_helper query --order_status=waitbuyerreceive
      python3 scripts/cli.py order_helper query --create_start_time="2026-03-20 00:00:00" --create_end_time="2026-03-25 23:59:59"
    """
    try:
        payload = load_json_payload(mcp_result_file or None)
        result = query_order(
            order_id=order_id or None,
            create_start_time=create_start_time or None,
            create_end_time=create_end_time or None,
            pay_start_time=pay_start_time or None,
            pay_end_time=pay_end_time or None,
            order_status=order_status or None,
            refund_status=refund_status or None,
            auto_default_today=(auto_default_today.lower() != "false"),
            payload=payload,
        )

        if result.get("success"):
            orders = result.get("orders", [])
            total_count = result.get("totalCount", len(orders))
            days_back = result.get("queryDaysBack", 1)

            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                display_orders(
                    orders,
                    total_count=total_count,
                    days_back=days_back,
                    start_date=result.get("queryStartTime", ""),
                    end_date=result.get("queryEndTime", "")
                )
            markdown = buffer.getvalue().strip() or f"查询完成，共 {total_count} 笔订单"
            print_output(True, markdown, result)
        else:
            print_output(False, f"查询失败：{result.get('error', '未知错误')}", result)
    except Exception as e:
        print_error(e)


def send(question: str = "", order_ids: str = "", mcp_result_file: str = ""):
    """
    发送旺旺消息

    用法：
      python3 scripts/cli.py order_helper send --question="请尽快发货" --order_ids=4502201509012068443
      python3 scripts/cli.py order_helper send --question="请尽快发货" --order_ids=4502201509012068443,4502201509012068444
    """
    try:
        if not question:
            print_output(False, "❌ 缺少必填参数 question", {})
            return
        if not order_ids:
            print_output(False, "❌ 缺少必填参数 order_ids", {})
            return

        # 支持逗号分隔的多个订单 ID
        order_id_list = [oid.strip() for oid in order_ids.split(",") if oid.strip()]

        payload = load_json_payload(mcp_result_file or None)
        result = send_ww_message(question=question, order_ids=order_id_list, payload=payload)
        task_id = result.get("task_id", "")
        print_output(True, f"✅ 消息发送成功，任务 ID：{task_id}", result)
    except Exception as e:
        print_error(e)


def query_reply(task_id: str = "", mcp_result_file: str = ""):
    """
    查询商家回复记录

    用法：
      python3 scripts/cli.py order_helper query_reply --task_id=xxx
    """
    try:
        if not task_id:
            print_output(False, "❌ 缺少必填参数 task_id", {})
            return

        payload = load_json_payload(mcp_result_file or None)
        result = query_ww_task_reply(task_id=task_id, payload=payload)
        has_reply = result.get("hasReply", False)
        replies = result.get("replies", [])

        if has_reply:
            md = f"✅ 商家已回复，共 {len(replies)} 条回复记录"
        else:
            md = "⚠️ 商家暂未回复"

        print_output(True, md, result)
    except Exception as e:
        print_error(e)
