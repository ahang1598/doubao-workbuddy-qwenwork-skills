# JSON 输出示例

本文件包含 modifications.json 和验证脚本输入 JSON 的完整示例。生成 JSON 时请参考这些示例的格式。

---

## ⭐  首选:TOML 聚合模板(一次生成全部 5 个 JSON)

**用法**:写一份 `review_all.toml`,然后:

```bash
python3 scripts/build_json.py --from-toml review_all.toml --multi
# 生成 modifications.json / amounts.json / dates.json / cross_refs.json / payment_flow.json

python3 scripts/verify_all.py --from-toml review_all.toml --output verify_results.json
# 一次执行全部 4 个 verify 子脚本,合并输出
```

**模板(直接复制修改)**:

```toml
# ============ modifications.json ============
[modifications]
author = "合同审查助手"

[[modifications.modifications]]
type = "track_change"
search_text = '''甲方应在合同签订后十个工作日内向乙方支付合同总额的"80%"作为预付款'''
old_text = '80%'
new_text = '30%'
comment = '''【风险等级】P0
【风险分析】预付款80%远超30%惯例，乙方违约则大额资金难追回。
【修改建议】将预付款比例降至30%，剩余按进度或验收节点支付。'''
risk_level = "P0"

[[modifications.modifications]]
type = "track_change"
search_text = '''本合同有效期自2026年2月1日起至2027年1月1日止,共1年'''
old_text = '2027年1月1日'
new_text = '2027年1月31日'
comment = '''【风险等级】P0
【风险分析】起止日期实际仅11个月，与"共1年"矛盾。
【修改建议】将结束日期修正为"2027年1月31日"，与"共1年"表述一致。'''
risk_level = "P0"

# ============ amounts.json ============
[amounts]
total_amount = 1000000
currency = "CNY"

[[amounts.installments]]
label = "首期款"
clause = "第4.1条"
amount = 300000
percentage = 30

[[amounts.installments]]
label = "尾款"
clause = "第4.2条"
amount = 700000
percentage = 70

[amounts.deposit]
amount = 200000
type = "定金"
clause = "第5条"

[[amounts.penalty_rates]]
party = "甲方"
daily_rate = 0.0005
clause = "第10.1条"

[[amounts.amounts_uppercase]]
clause = "第3条"
numeric = 1000000
uppercase_text = "壹佰万元整"

# ============ dates.json ============
[dates]
review_date = "2026-04-29"

[dates.contract_term]
start_date = "2026-02-01"
end_date = "2027-01-01"
stated_duration = "1年"
clause = "第10条"

[[dates.date_pairs]]
label = "保密期限"
clause = "第8条"
start_date = "2026-02-01"
end_date = "2029-01-31"
stated_duration = "3年"
relation_to_contract = "after_end"

[[dates.key_dates]]
label = "首期付款日"
clause = "第4.1条"
date = "2026-03-01"
dependency = '''合同生效后30日内'''

# ============ cross_refs.json ============
[cross_refs]

[[cross_refs.clauses]]
number = "第1条"
title = "定义"

[[cross_refs.clauses]]
number = "第2条"
title = "标的"

[[cross_refs.clauses]]
number = "第10条"
title = "合同期限"

[[cross_refs.references]]
position = "第2条"
target = "第1条"
expression = '''见第1条定义'''

[[cross_refs.references]]
position = "第5条"
target = "第99条"
expression = '''依据第99条'''

# ============ payment_flow.json ============
[payment_flow]

[payment_flow.parties]
party_a = "甲方公司全称"
party_b = "乙方公司全称"

[[payment_flow.payment_items]]
label = "预付款"
payer = "甲方"
payee = "乙方"
amount = 300000
clause = "第4.1条"

[[payment_flow.payment_items]]
label = "预付款"
payer = "甲方"
payee = "乙方"
amount = 300000
clause = "第4.3条"
```

**关键规则**:
1. 字符串一律用单引号 `'...'` 或三重单引号 `'''...'''`(字面串,零转义)
2. 双引号仅用于 ASCII 简单字符串(如 `type = "track_change"`)
3. 对象数组用 `[[table.items]]` 重复,每次定义一个新元素
4. 顶层 `[modifications]`、`[amounts]` 等的表名 = 生成的 JSON 文件名(去掉 .json)

---

## 早期 JSON 示例(保留作参考，注意批注格式已升级为三段式)


## 一、modifications.json 完整示例

### 示例 1：简单服务合同审查（5 条修改）

```python
import json

data = {
    "author": "合同审查助手",
    "modifications": [
        {
            "type": "track_change",
            "search_text": "甲方应在合同签订后十个工作日内向乙方支付合同总额的80%作为预付款",
            "old_text": "合同总额的80%",
            "new_text": "合同总额的30%",
            "comment": "【风险等级】P0\n【风险分析】预付款80%远超30%惯例，乙方违约则大额资金难追回。\n【修改建议】将预付款比例降至30%，剩余按进度或验收节点支付。",
            "risk_level": "P0"
        },
        {
            "type": "track_change",
            "search_text": "乙方应在收到甲方书面通知后三十日内完成整改",
            "old_text": "三十日",
            "new_text": "十五日",
            "comment": "【风险等级】P1\n【风险分析】30日整改期过长，可能延误项目进度。\n【修改建议】将整改期限从30日缩短至15日。",
            "risk_level": "P1"
        },
        {
            "type": "comment_only",
            "search_text": "本合同一式两份，双方各执一份",
            "comment": "【风险等级】P1\n【风险分析】无保密约定，泄密时无合同救济途径。\n【修改建议】合同末尾增加保密条款，约定保密义务及期限不少于3年。",
            "risk_level": "P1"
        },
        {
            "type": "insert_after",
            "search_text": "第十条 争议解决",
            "new_text": "第十一条 保密条款\n\n双方对本合同内容及履约过程中知悉的对方商业秘密承担保密义务，保密期限自合同终止之日起三年。违反保密义务的一方应赔偿由此给对方造成的全部损失。",
            "comment": "【风险等级】P1\n【风险分析】缺保密条款，履约中商业秘密无合同保护。\n【修改建议】新增保密条款，约定保密范围、期限及违约责任。",
            "risk_level": "P1"
        },
        {
            "type": "track_change",
            "search_text": "因不可抗力导致合同无法履行的，双方均不承担违约责任",
            "old_text": "双方均不承担违约责任",
            "new_text": "受影响方不承担违约责任，但应在不可抗力事件发生后五日内书面通知对方，并在十五日内提供相关证明",
            "comment": "【风险等级】P2\n【风险分析】缺通知时限与举证，对方可滥用不可抗力。\n【修改建议】增加通知义务（5日内）和举证要求（15日内）。",
            "risk_level": "P2"
        }
    ]
}

with open("modifications.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("JSON saved: modifications.json")
```

### 字段要点提醒

- **search_text**：从合同原文中逐字复制，越长越好（整句或半句），确保能唯一定位到目标段落
- **old_text**：必须是 search_text 所在段落内的精确子串，不能跨段落
- **new_text**：替换后的文本，注意保持与原文相同的标点风格（中文合同用中文标点）
- **comment**：必须包含 `【风险等级】`、`【风险分析】`、`【修改建议】` 三段式格式；字数上限：风险分析 P0≤60/P1≤60/P2≤35，修改建议 P0≤60/P1≤60/P2≤35。风险分析须点明后果、稍带法言法语、金额比例写具体，不写"畸高/不规范"这类结论式空话；定位一律用条款号/性质词，禁用 clean_text 段号。**豁免字数上限**：内容空置聚合那 1 条 P2 批注可超字数上限
- **risk_level**：只能是 P0/P1/P2 三个值之一
- **type**：只能是 track_change / comment_only / insert_after / delete 四个值之一。选择判据见 SKILL.md §七/modification-engine.md——能给确定替换文本→track_change、整条缺失且能补→insert_after、删除即解决→delete、只能指方向→comment_only

---

## 二、验证脚本输入 JSON 示例

### dates.json

```python
dates_data = {
    "review_date": "2026-04-24",
    "contract_term": {
        "start_date": "2026-02-01",
        "end_date": "2027-01-01",
        "stated_duration": "1年",
        "clause": "第10条"
    },
    "date_pairs": [
        {
            "label": "保密期限",
            "clause": "第8条",
            "start_date": "2026-02-01",
            "end_date": "2029-01-31",
            "stated_duration": "3年",
            "relation_to_contract": "after_end"
        }
    ],
    "key_dates": [
        {
            "label": "首期付款日",
            "clause": "第4.1条",
            "date": "2026-03-01",
            "dependency": "合同生效后30日内"
        }
    ],
    "renewal": {
        "auto_renew": True,
        "renewal_period": "1年",
        "notice_days": 30,
        "clause": "第10.2条"
    }
}
with open("dates.json", "w", encoding="utf-8") as f:
    json.dump(dates_data, f, ensure_ascii=False, indent=2)
```

### amounts.json

```python
amounts_data = {
    "total_amount": 1000000,
    "currency": "CNY",
    "installments": [
        {"label": "首期款", "clause": "第4.1条", "amount": 300000, "percentage": 30},
        {"label": "中期款", "clause": "第4.2条", "amount": 500000, "percentage": 50},
        {"label": "尾款", "clause": "第4.3条", "amount": 200000, "percentage": 20}
    ],
    "deposit": {"amount": 200000, "type": "定金", "clause": "第5条"},
    "penalty_rates": [
        {"party": "甲方", "daily_rate": 0.0005, "clause": "第10.1条"},
        {"party": "乙方", "daily_rate": 0.001, "clause": "第10.2条"}
    ],
    "amounts_uppercase": [
        {"clause": "第3条", "numeric": 1000000, "uppercase_text": "壹佰万元整"}
    ]
}
with open("amounts.json", "w", encoding="utf-8") as f:
    json.dump(amounts_data, f, ensure_ascii=False, indent=2)
```

### cross_refs.json

```python
cross_refs_data = {
    "clause_index": [
        {"id": "第1条", "title": "合同标的", "level": 1},
        {"id": "第1.1条", "title": "产品描述", "level": 2},
        {"id": "第2条", "title": "价款与支付", "level": 1},
        {"id": "第3条", "title": "违约责任", "level": 1}
    ],
    "cross_references": [
        {
            "source_clause": "第5.2条",
            "source_context": "按照第2条约定的付款方式执行",
            "target_id": "第2条",
            "reference_expression": "第2条约定的付款方式"
        }
    ]
}
with open("cross_refs.json", "w", encoding="utf-8") as f:
    json.dump(cross_refs_data, f, ensure_ascii=False, indent=2)
```

### payment_flow.json

```python
payment_flow_data = {
    "parties": {"party_a": "甲方/XX公司", "party_b": "乙方/YY公司"},
    "payment_items": [
        {"label": "服务费", "clause": "第4条", "payer": "甲方", "payee": "乙方", "amount": 1000000, "context": "甲方应向乙方支付服务费"}
    ],
    "fee_items": [
        {"label": "差旅费", "clause": "第6条", "bearer": "乙方", "context": "差旅费由乙方自行承担"}
    ],
    "obligation_items": [
        {"label": "交付义务", "clause": "第5条", "executor": "乙方", "context": "乙方应按期交付成果物"}
    ],
    "right_items": [
        {"label": "知识产权", "clause": "第7条", "owner": "甲方", "context": "成果物知识产权归甲方所有"}
    ]
}
with open("payment_flow.json", "w", encoding="utf-8") as f:
    json.dump(payment_flow_data, f, ensure_ascii=False, indent=2)
```

---

## 三、合并写入模式（可选）

如果你需要一次性生成多个验证 JSON，可以在同一个 Python 脚本中完成：

```python
import json

# ... 构建 dates_data, amounts_data, cross_refs_data, payment_flow_data ...

for filename, obj in [
    ("dates.json", dates_data),
    ("amounts.json", amounts_data),
    ("cross_refs.json", cross_refs_data),
    ("payment_flow.json", payment_flow_data),
]:
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f"Saved: {filename}")
```
