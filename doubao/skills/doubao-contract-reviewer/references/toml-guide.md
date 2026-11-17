# TOML 写入指南

本文件是 review_all.toml 的写法参考。所有需要写入磁盘的 JSON 文件必须先写成 TOML，再通过 `build_json.py --from-toml` 生成。

---

## 为什么用 TOML

合同原文含中文引号 `""`、全角括号 ``、反斜杠 `\`、换行符。TOML 的单引号和三单引号是"字面串"，不解析转义，零冲突。

---

## 速查

| 场景 | 写法 |
|------|------|
| 普通字符串 | `key = "abc"` |
| 含中文引号的字符串 | `key = '这里可含"中文引号"和'` |
| 含换行的多行字符串 | `key = '''第一行\n第二行'''`（直接换行） |
| 含单引号的字符串 | `key = "He said 'hi'"` |
| 布尔/数字 | `key = true` / `key = 123` |
| 数组 | `arr = ["a", "b"]` |
| 对象数组 | `[[items]]` 重复出现 |

**默认**：字符串用 `'...'` 单引号或 `'''...'''` 三引号。

---

## 陷阱

- TOML 没有 `null`/`None`：要表示空缺，直接不写这个键
- 顶层键不能放在 `[table]` 之后：先把顶层键写在文件最前面
- 对象数组下不能再跟普通键：`[[items]]` 内部只能是该元素的字段

---

## 完整示例（一次生成 5 个 JSON）

```toml
# review_all.toml

[modifications]
author = "合同审查助手"

[[modifications.modifications]]
type = "track_change"
search_text = '''甲方应在合同签订后十个工作日内向乙方支付合同总额的80%作为预付款'''
old_text = '合同总额的80%'
new_text = '合同总额的30%'
comment = '''【风险等级】P0
【风险分析】预付款80%远超30%惯例，乙方违约则大额资金难追回。
【修改建议】将预付款比例降至30%，剩余按进度支付。'''
risk_level = "P0"

[[modifications.modifications]]
type = "comment_only"
search_text = '''本合同一式两份，双方各执一份'''
comment = '''【风险等级】P1
【风险分析】无保密条款，泄密时无合同救济途径。
【修改建议】建议在合同末尾增加保密条款，约定保密义务及期限。'''
risk_level = "P1"

[amounts]
total_amount = 1000000
currency = "CNY"

[[amounts.installments]]
name = "预付款"
amount = 300000
percentage = "30%"
condition = '合同签订后五个工作日内'

[[amounts.installments]]
name = "尾款"
amount = 700000
percentage = "70%"
condition = '验收合格后'

[dates]
review_date = "2026-06-03"

[dates.contract_term]
start_date = "2026-02-01"
end_date = "2027-01-01"
stated_duration = "1年"
clause = "第10条"

[cross_refs]
# clauses / references 数组

[payment_flow]

[payment_flow.parties]
party_a = "甲方公司名称"
party_b = "乙方公司名称"

[[payment_flow.payment_items]]
payer = "甲方"
payee = "乙方"
amount = '合同总额的30%'
condition = '合同签订后五个工作日内'
clause = "第3条"
```

---

## 禁止的 JSON 写入方式

| 方式 | 为什么禁止 |
|------|-----------|
| `write_file` 直接写 .json | 中文引号漏转义 |
| bash `echo`/`heredoc` > *.json | shell 转义出错 |
| Python json.dump | 中文引号 SyntaxError |
