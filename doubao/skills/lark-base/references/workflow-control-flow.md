# 工作流分支与循环契约

## 条件分支（IfElseBranch）

`children.links` 必须含 `if_true`、`if_false`。省略 `next` 或设为 `null`；不得设置公共后继，分支尾部不得指向同一 step ID，必须独立成链。见 [JSON 示例](workflow-examples.md#条件分支ifelsebranch)。

必填 `condition`：OrGroup，结构为 `(A and B) or (C and D)`。

```json
{"condition":{"conjunction":"or","conditions":[{"conjunction":"and","conditions":[{"left_value":{"value_type":"ref","value":"$.step_1.fieldxxx"},"operator":"isGreater","right_value":[{"value_type":"number","value":1000}]}]}]}}
```

## 多路分支（SwitchBranch）

`children.links` 含多个 `case` 边；`label` 按 `child_branch_list` 条件顺序优先用 `branch_1`、`branch_2`，语义写入 `desc`。

| 字段 | 必填 | 约束 |
|---|---|---|
| `mode` | 否 | `exclusive`：仅执行一个命中分支；`parallel`：执行全部命中分支。默认 `exclusive` |
| `no_match_action` | 否 | 仅 `exclusive`：`classifyToOther`（其他分支）/`fail`（报错终止）；默认前者 |
| `fail_mode` | 否 | 仅 `parallel`：`partialSuccess`（部分成功即继续）/`fail`（任一失败即终止）；默认前者 |
| `match_mode` | 否 | 仅 `parallel`：全不命中时 `noneMatchSkip`（跳过继续）/`noneMatchFail`（报错终止）；默认前者 |
| `child_branch_list` | 是 | BranchItem[]，1-10 项；每项含 string `name`（名称）、OrGroup `condition`（条件） |

```json
{"mode":"exclusive","no_match_action":"classifyToOther","child_branch_list":[{"name":"高优先级",
"condition":{"conjunction":"or","conditions":[{"conjunction":"and","conditions":[{"left_value":{"value_type":"ref","value":"$.step_1.fieldxxx"},"operator":"is","right_value":[{"value_type":"text","value":"P0"}]}]}]}}]}
```

## AI 分类分支（AIClassificationBranch）

用 AI 分类 `content`，沿 `children.links` 的 `case` 边进入命中步骤。`steps[].data` 使用公开 Agent Data 协议。

| 字段 | 必填 | 约束 |
|---|---|---|
| `classes` | 是 | 至少 2 项，每项必须含 `name`、`desc` |
| `classes[].name` | 是 | 等于普通 `children.links[].desc` |
| `classes[].desc` | 是 | 可为空字符串 |
| `content` | 是 | TextRefItem[]；支持 `text`/`ref` |
| `classification_rule` | 否 | 全局分类规则纯文本 |
| `no_match_action` | 否 | 无匹配：`classifyToOther` 默认分支；`fail` 节点失败；默认前者 |

命中步骤必须写入 `children.links`。普通边写 `kind:"case"`、稳定 `label:"branch_1"`/`"branch_2"`、与 `classes[i].name` 一致的 `desc`；`to` 指向入口 step。
`no_match_action` 为 `classifyToOther` 时必须加默认边 `{"kind":"case","label":"default","desc":"默认分支","to":"step_other_action"}`；为 `fail` 时不得加默认边。

```json
{"classes":[{"name":"Bug","desc":"功能报错、异常、不可用或结果错误"},{"name":"功能建议","desc":"希望新增能力或优化现有功能"}],"content":[{"value_type":"text","value":"请根据反馈内容判断类型："},{"value_type":"ref","value":"$.step_trigger.fldFeedback"}],"classification_rule":"信息不足时判定为无法匹配。"}
```

## 循环（Loop）

`children.links` 必须含指向循环体入口的 `kind:"loop_start"` 边；`next` 指向循环后的节点。`Loop.data` 必须传 `ref`，通常引用 `FindRecordAction.fieldRecords`。
循环体以 `$.{loopStepId}.item.{fieldId}` 引用当前元素，以 `$.{loopStepId}.index` 取从 0 开始的索引。

必填 `data`：ValueInfo[]，仅支持一个 `ref`。可选 `loop_mode` 决定单次错误时是否继续：`end` 终止，`continue` 继续；`max_loop_times` 为最大循环次数。

```json
{"loop_mode":"continue","max_loop_times":100,"data":[{"value_type":"ref","value":"$.find_record_stepIdxxx.fieldRecords"}]}
```

分支：[分支节点输出](workflow-outputs.md#分支节点输出)；Loop：[循环节点输出](workflow-outputs.md#循环节点输出)
