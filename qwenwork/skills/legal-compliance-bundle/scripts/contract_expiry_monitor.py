#!/usr/bin/env python3
"""技能ID: contract-expiry-monitor | 合同到期监控"""
import json
from datetime import date, datetime
from typing import Dict, Any

def skill_function(input_data):
    contracts = input_data.get("contracts", [])
    warning_days = int(input_data.get("warning_days", 30))
    today = date.today()
    alerts = []
    for c in contracts:
        name = c.get("name", "未命名合同")
        expiry_str = c.get("expiry_date", "")
        party = c.get("counterparty", "未知")
        try:
            expiry = datetime.strptime(expiry_str, "%Y-%m-%d").date()
            days_left = (expiry - today).days
            if days_left < 0:
                status = "已过期"
            elif days_left <= warning_days:
                status = f"即将到期(剩余{days_left}天)"
            else:
                status = "正常"
            alerts.append({"合同名称": name, "对方": party, "到期日": expiry_str, "剩余天数": days_left, "状态": status})
        except:
            alerts.append({"合同名称": name, "错误": f"日期格式无法解析: {expiry_str}"})
    alerts.sort(key=lambda x: x.get("剩余天数", 9999))
    urgent = [a for a in alerts if a.get("剩余天数", 9999) <= warning_days]
    return {"status": "success", "result": {"监控结果": alerts, "预警数量": len(urgent), "预警合同": urgent}}

if __name__ == "__main__":
    test = {"contracts": [{"name": "服务器租赁", "expiry_date": "2025-04-15", "counterparty": "阿里云"}, {"name": "办公场地", "expiry_date": "2026-12-31", "counterparty": "物业"}], "warning_days": 60}
    print(json.dumps(skill_function(test), ensure_ascii=False, indent=2))
