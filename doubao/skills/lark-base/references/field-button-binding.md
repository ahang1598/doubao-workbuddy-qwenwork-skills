# 表格按钮工作流绑定 Reference

<a id="3-各类型写法"></a>

<a id="313-button"></a>

## 按钮字段 JSON

```json
{ "type": "button", "name": "按钮", "button_config": { "title": "点击按钮" } }
```

## 工作流绑定命令

绑定 Workflow 时，使用 `+button-rule-bind`；读取绑定关系时，使用 `+button-rule-get`；解除绑定用 `+button-rule-unbind`。
