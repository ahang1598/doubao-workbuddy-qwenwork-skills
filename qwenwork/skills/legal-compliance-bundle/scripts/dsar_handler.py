#!/usr/bin/env python3
"""dsar_handler.py — 个人信息请求处理 (Skill #39) 处理用户个人信息查阅/删除请求。"""
import sys
from datetime import datetime

REQUEST_TYPES = {
    "查阅": {"law": "PIPL第44条", "deadline": "15个工作日", "action": "提供个人信息副本"},
    "复制": {"law": "PIPL第44条", "deadline": "15个工作日", "action": "导出个人信息"},
    "更正": {"law": "PIPL第46条", "deadline": "15个工作日", "action": "核实并更正信息"},
    "删除": {"law": "PIPL第47条", "deadline": "15个工作日", "action": "删除个人信息"},
    "撤回同意": {"law": "PIPL第15条", "deadline": "即时", "action": "停止处理并删除"},
    "注销账户": {"law": "PIPL第47条", "deadline": "15个工作日", "action": "删除全部个人信息并注销"}
}

def handle_request(user_name: str, request_type: str, data_scope: str = "") -> str:
    info = REQUEST_TYPES.get(request_type, {"law": "PIPL", "deadline": "15个工作日", "action": "依法处理"})
    r = f"# 个人信息权利请求处理单\n\n"
    r += f"**处理时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    r += f"**请求人**: {user_name}\n"
    r += f"**请求类型**: {request_type}\n"
    r += f"**法律依据**: {info['law']}\n"
    r += f"**处理时限**: {info['deadline']}\n\n---\n\n"
    r += f"## 处理流程\n\n"
    r += f"1. **身份核验**: 确认请求人身份（手机号/邮箱/实名认证）\n"
    r += f"2. **请求受理**: 登记请求信息，开始计时\n"
    r += f"3. **信息检索**: 查询系统中该用户的所有个人信息\n"
    r += f"4. **执行操作**: {info['action']}\n"
    r += f"5. **结果通知**: 将处理结果告知用户\n"
    r += f"6. **记录存档**: 保存请求处理记录至少3年\n\n"
    r += f"## 注意事项\n\n- 身份核验是前置条件，防止冒名请求\n- 删除请求需评估是否存在法定保留义务（如财务记录）\n- 重复请求可收取合理费用\n- 拒绝请求需书面说明理由\n"
    return r

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--user", required=True)
    p.add_argument("--type", dest="req_type", default="查阅", choices=list(REQUEST_TYPES.keys()))
    p.add_argument("--output", "-o")
    a = p.parse_args()
    r = handle_request(a.user, a.req_type)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f: f.write(r)
        print(f"✅ 已保存至: {a.output}")
    else: print(r)
if __name__ == "__main__": main()
