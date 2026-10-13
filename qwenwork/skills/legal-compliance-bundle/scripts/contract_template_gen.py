#!/usr/bin/env python3
"""技能ID: contract-template-gen | 合同模板生成"""
import json, re
from typing import Dict, Any
from datetime import date

TEMPLATES = {
    "买卖合同": """# 买卖合同

**合同编号**: [编号]
**签订日期**: {today}

## 甲方（卖方）
- 名称: [甲方名称]
- 地址: [甲方地址]
- 法定代表人: [甲方法人]

## 乙方（买方）
- 名称: [乙方名称]
- 地址: [乙方地址]
- 法定代表人: [乙方法人]

## 第一条 标的物
| 商品名称 | 规格型号 | 数量 | 单价(元) | 金额(元) |
|----------|----------|------|----------|----------|
| {product} | {spec} | {qty} | {price} | {total} |

## 第二条 质量标准
标的物质量应符合国家标准及双方约定的技术规格。

## 第三条 交货
- 交货时间: {delivery_date}
- 交货地点: {delivery_place}

## 第四条 付款
- 合同总价: 人民币{total}元
- 付款方式: 银行转账

## 第五条 违约责任
逾期交货/付款，按合同金额日万分之五支付违约金。

## 第六条 争议解决
协商不成，提交甲方所在地人民法院诉讼解决。

**甲方签章**: ___________ **乙方签章**: ___________
""",
    "保密协议": """# 保密协议

**签订日期**: {today}
甲方: [披露方]  乙方: [接收方]

## 第一条 保密信息
技术资料、商业计划、客户信息、财务数据等。

## 第二条 保密义务
未经书面同意不得向第三方披露。

## 第三条 保密期限
自签订之日起{years}年。

## 第四条 违约责任
违约方赔偿守约方一切损失。

甲方签章: ___________ 乙方签章: ___________
""",
    "服务合同": """# 服务合同

**签订日期**: {today}
甲方(委托方): [名称]  乙方(服务方): [名称]

## 第一条 服务内容
{service_desc}

## 第二条 服务期限
自{start_date}至{end_date}

## 第三条 服务费用
总费用: 人民币{fee}元

## 第四条 知识产权
服务成果知识产权归[甲方/乙方/双方共有]。

甲方签章: ___________ 乙方签章: ___________
""",
}

def skill_function(input_data):
    ctype = input_data.get("contract_type", "买卖合同")
    terms = input_data.get("key_terms", {})
    tpl = TEMPLATES.get(ctype)
    if not tpl:
        return {"status": "success", "result": {"提示": f"暂无'{ctype}'模板", "可选": list(TEMPLATES.keys())}}
    terms.setdefault("today", date.today().isoformat())
    placeholders = set(re.findall(r"\{([^}]+)\}", tpl))
    fill = {k: terms.get(k, f"[{k}]") for k in placeholders}
    try:
        filled = tpl.format(**fill)
    except:
        filled = tpl
    return {"status": "success", "result": {"合同类型": ctype, "模板": filled}}

if __name__ == "__main__":
    print(json.dumps(skill_function({"contract_type": "买卖合同", "key_terms": {"product": "服务器", "spec": "Dell R750", "qty": "10台", "price": "50000", "total": "500000", "delivery_date": "2025-04-01", "delivery_place": "北京市海淀区"}}), ensure_ascii=False, indent=2))
