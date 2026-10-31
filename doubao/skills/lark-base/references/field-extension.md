# 字段插件配置与单元格生成 Reference

## 能力与适用范围

字段插件扩展基础字段能力：同行其他单元格更新时触发 LLM 推理，向已有目标字段生成内容；不创建或修改字段 schema。当前公开插件 ID 仅 `builtin_llm_completion`，支持文本、单选、多选、数字、日期目标字段，以 prompt 和字段引用生成内容；也可手动触发异步更新。

| 命令 | 动作 | scope/约束 |
|---|---|---|
| `+field-extension-get` | 读取当前可识别配置 | `base:field:read`，只读 |
| `+field-extension-update` | 安装、更新、清空目标字段自动生成配置 | `base:field:update`，高风险写，必须 `--yes` |
| `+field-extension-update-cells` | 对已配置插件字段发起手动异步更新任务 | `base:record:update`，高风险写，必须 `--yes` |

## 读取插件配置

```bash
lark-cli base +field-extension-get \
  --base-token "<base_token>" --table-id "<table_id>" \
  --field-id "<target_field_id>" --as user
```

## 安装、更新与清空配置

`+field-extension-update --json` 接收插件配置 envelope：

| 字段 | 类型 | 规则 |
|---|---|---|
| `extension_id` | string | 当前公开仅 `builtin_llm_completion` |
| `inputs` | object | 结构由 `extension_id` 决定，不得将一种插件的结构用于所有插件 |
| `inputs.prompt` | PromptSegment[] | `builtin_llm_completion` 的有序 prompt 片段 |
| `prompt[].type` | string | `text`、`field_ref` |
| `prompt[].text` | string | `type=text` 时必填 |
| `prompt[].field` | string | `type=field_ref` 时必填；传当前表字段 ID 或字段名 |

`field_ref` 只能引用当前表其他字段，不得引用目标字段、附件字段或其他不支持字段。

安装或更新：

```bash
lark-cli base +field-extension-update \
  --base-token "<base_token>" --table-id "<table_id>" \
  --field-id "<target_field_id>" \
  --json '{"extension_id":"builtin_llm_completion","inputs":{"prompt":[{"type":"text","text":"请根据 "},{"type":"field_ref","field":"状态"},{"type":"text","text":" 输出一句简洁结论。"}]}}' \
  --as user --yes
```

清空时传空对象：

```bash
lark-cli base +field-extension-update \
  --base-token "<base_token>" --table-id "<table_id>" \
  --field-id "<target_field_id>" --json '{}' --as user --yes
```

安装或更新后自动更新强制开启；没有单独关闭自动更新而仅保留手动生成的参数。该命令不返回 `input_schemas`。

## 读取与写配置的返回

读取和写配置均返回 `current_extension`：

- 配置可识别：`.extension_id` 为插件 ID，`.inputs` 为对应配置对象。
- 未配置、无法识别或存量配置无法转换：均可能为 `null`，仅凭该值无法区分原因。
- 读取所得 `field_ref.field` 通常是字段名；名称不可用时可能是字段 ID。

## 触发单元格更新

生成和写回异步执行，耗时随单元格数量增加。

| 范围 | 参数与语义 |
|---|---|
| `--type column` | 可选 `--view-id`；更新该视图内目标字段单元格，未传时后端使用目标表首视图；不得传 `--record-id` |
| `--type row` | 必须传一个或多个 `--record-id`；仅更新指定记录的目标字段单元格；不得传 `--view-id` |

```bash
lark-cli base +field-extension-update-cells \
  --base-token "<base_token>" --table-id "<table_id>" \
  --field-id "<target_field_id>" --type column \
  --view-id "<view_id>" --as user --yes
```

```bash
lark-cli base +field-extension-update-cells \
  --base-token "<base_token>" --table-id "<table_id>" \
  --field-id "<target_field_id>" --type row \
  --record-id "<record_id_1>" --record-id "<record_id_2>" \
  --as user --yes
```

响应只返回任务 ID，表示任务已创建，不表示单元格已生成或写回；通过记录读取实际值：

```json
{"task_id":"<task_id>"}
```

## 权限与适用限制

触发更新任务必须具备管理目标表或目标字段插件的权限，并满足上表 scope；目标字段类型必须属于上述支持范围。
