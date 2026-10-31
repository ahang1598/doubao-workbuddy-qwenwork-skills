# 静态选项管理与检索 Reference

## 单选与多选的通用结构

单/多选用 `select`，以 `multiple` 区分，默认 `false`。静态传 `options`，动态传 `dynamic_options_source`，不得同时传。
写记录：单选也传选项名数组 `{"状态":["Done"]}`；多选传需保留的全部选择。写入、迁移见 [Record](../scenes/record.md)。

## 静态选项

| 项 | 规则 |
|---|---|
| `options` | ≤`10000` 项；元素 `{name,hue?,lightness?}`；`name` 必填，无 `id` |
| `hue` | Red、Orange、Yellow、Lime、Green、Turquoise、Wathet、Blue、Carmine、Purple、Gray；默认 Blue |
| `lightness` | Lighter、Light、Standard、Dark、Darker；默认 Lighter |
| `default_value` | 选项名数组；`multiple=false` 也传数组 |

```json
{"type":"select","name":"状态","multiple":false,"default_value":["Todo"],"options":[{"name":"Todo","hue":"Blue","lightness":"Lighter"}]}
```

## 动态选项

不支持 `default_value`。

| 项 | 规则 |
|---|---|
| `dynamic_options_source` | `{table_id,field_id}`；`table_id` 填来源表 id/表名，`field_id` 填来源字段 id/字段名；仅创建支持，更新已有字段时不得传 |
| 引用选项条件、级联筛选条件 | Base 前端支持，属 UI-only；OpenAPI 不支持，CLI 无法读取、创建、更新；不得因接口返回缺失判定未配置 |

```json
{"type":"select","name":"动态状态","multiple":false,"dynamic_options_source":{"table_id":"选项表","field_id":"候选状态"}}
```

## 已有选项变更入口

字段更新按目标选项集合处理存量值；移除被记录引用的旧选项使相应值丢失或变空。[选项变更决策](../scenes/field.md#选项变更决策) 确定业务变更方式及是否迁移。
