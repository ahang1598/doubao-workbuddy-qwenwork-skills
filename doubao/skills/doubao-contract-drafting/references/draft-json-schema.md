# 草案 JSON Schema

所有校验和生成脚本共用同一 JSON 文件。机器可执行结构以 `draft.schema.json` 为准；本文用于解释字段和示例，不另行改变其约束。最小结构如下：

```json
{
  "title": "合同名称",
  "placeholder": "",
  "use_comments": false,
  "use_colors": false,
  "allow_tables": true,
  "contract_form": "single",
  "parameter_profile": {"family": "货物买卖/采购", "role": "drafting_party_payer", "required": []},
  "signature_ready": false,
  "facts": [],
  "sections": [],
  "appendices": [],
  "signature": []
}
```

| 字段 | 类型/可选值 | 说明 |
|---|---|---|
| `title` | string | 合同标题，必填 |
| `placeholder` | 空字符串 `""` | 必填；合同中不输出文字型占位符 |
| `use_comments` / `use_colors` | boolean | 必须为 `false` |
| `allow_tables` | boolean | 用户禁止表格时为 `false` |
| `contract_form` | `single` / `framework` | 单项或框架合同 |
| `parameter_profile` | object | 单项合同必填；见下文，列明应覆盖的默认参数 |
| `signature_ready` | boolean | 单项合同无关键事实空白时才可为 `true` |
| `has_blanks` | boolean | 是否仍存在待填写的交易事实；有空白时为 `true` |
| `facts` | array | 交易信息拆解记录 |
| `sections` | array | 合同正文，按顺序输出 |
| `appendices` | array | 受控附件，置于签署页前 |
| `signature` | array[string] | 签署主体名称；为空时不生成签署页 |
| `tables` | array | 仅 `allow_tables=true` 时可用 |

## facts

```json
{
  "key": "高校成果转化审批",
  "value": "尚未完成",
  "source": "附件1：第八部分",
  "status": "pending",
  "aliases": ["成果转化审批", "内部审批"],
  "forbidden_assertions": ["已完成", "已取得批准"]
}
```

`status` 只能为 `confirmed`、`derived`、`standard_term`、`standard_parameter`、`pending` 或 `disputed`。`standard_parameter` 必须附 `basis`，说明适用的场景规则，并提供 `coverage_terms`（正文中应出现的一个或多个字符串）；对于 `pending`，提供 `aliases` 与 `forbidden_assertions`；校验器只在同一句同时出现别名和禁止确认表述时拦截，避免全文关键词误报。

## parameter_profile

单项合同必须根据 `default-parameter-profiles.md` 填写：

```json
{
  "parameter_profile": {
    "family": "委托开发/技术服务",
    "role": "drafting_party_payer",
    "required": ["争议解决", "书面验收规则", "验收期", "付款期限", "付款节点", "交付期", "质保/维护期", "逾期履行违约金", "普通责任上限", "合同期限"],
    "not_applicable": {}
  }
}
```

`required` 中每一项必须在 `facts` 中有同名条目，状态为 `confirmed` 或 `standard_parameter`；其 `coverage_terms` 必须实际出现在合同正文。用户已明确的数值应标为 `confirmed`，其余标为 `standard_parameter`。确实不适用的覆盖项只能写入 `not_applicable`，并逐项说明理由。该机制用于阻止把应预填参数留成空白。

## delivery_summary

草案完成时另整理下列内容，用于交付后的对话，**不得写入合同正文**：

```json
{
  "delivery_summary": {
    "confirmed_facts": [{"key": "工程价款", "value": "29000元", "source": "题干第6项"}],
    "prefilled_parameters": [{"key": "验收期", "value": "10个工作日", "basis": "工程施工：一般验收期"}],
    "blank_items": [{"key": "苗木规格", "suggestion": "在附件一中补充品种、规格、数量及单价"}],
    "negotiation_items": []
  }
}
```

## sections

每项格式为：`{"level": 1|2, "text": "第一条 …"}`。`level=1` 为一级条款标题，`level=2` 为正文或子条款。正文不得出现任何文字型占位符；需要填写的事实以 `__________` 留空。

## appendices

用户提供的原始附件必须写为受控附件，不得替换为空白模板：

```json
{
  "number": "附件一",
  "title": "项目需求与商务条件摘要",
  "source": "附件1-项目需求与商务条件摘要.docx",
  "content": ["一、标准功能模块清单", "……"],
  "tables": [[ ["模块", "要求"], ["客户画像", "……"] ]]
}
```

`content` 为段落数组；`tables` 为表格数组，每张表为行数组。仅当用户明确要求“仅列附件清单”时可使用 `"list_only": true` 而省略 `content`。`allow_tables=false` 时，附件也不得含 `tables`。
