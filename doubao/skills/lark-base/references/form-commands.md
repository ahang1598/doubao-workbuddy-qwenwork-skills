# 表单管理命令与导航

## 适用范围

本页维护表单生命周期命令、调用约定，以及题目、配置、填写和分享协议的入口。任务范围、底表选择、执行规则和完成条件先按 [Form Scene](../scenes/form.md) 确定；已读取且仍有效的决策直接复用。

创建入口的返回只证明表单对象存在；自动带入的题目、必填状态和顺序仍是平台初始值。执行 `+form-create` 前完成 [Form 开工必读](../scenes/form.md#开工必读)，创建后按其中的配置顺序处理，不以视图数量或记录条数收尾。

## 表单生命周期命令

| 操作 | 命令 |
|---|---|
| 列出、读取表单 | `+form-list` / `+form-get` |
| 创建、更新、删除表单 | `+form-create` / `+form-update` / `+form-delete` |

## 创建语义与初始题目

- `+form-create` 将执行时表内全部表单支持类型的字段转成题目，没有选择初始题目子集的参数；支持类型统一见 [题目创建协议](form-questions.md#创建请求与支持类型)。表里已有的电话号码、超链接、签字、公式、查找引用字段也属于支持类型，会被自动带成题目；后续需要调整题型、必填或范围时再用 `+form-questions-list` 取得当前题目。
- `auto_number`、`created_at`、`created_by` 等系统字段不属于支持类型，因此不会自动生成题目；字段类型与定义见 [字段协议](field-config.md)。
- 初始顺序不保证继承底表，题目属性更新也不改题序；用户要求调整收集项、必填、显隐或题序时，按 [可见题目与排序](form-questions.md#可见题目与排序)读取现状并更新。
- 表的初始字段和平台默认结构见 [Table 创建协议](table-commands.md#创建时的初始字段)，表单描述的换行写法见 [描述与换行](form-questions.md#描述与换行)。

## 调用约定

- Form 创建用 `--name`；分享和题目管理保留 `--base-token`、`--table-id`、`--form-id`，`+form-detail` 用 `--share-token`。
- 分享参数、布尔 flag 及更新语义见 [分享协议](form-share.md#分享设置form-share-get--form-share-update)；题目移除与底层字段删除的参数区别见 [删除题目协议](form-questions.md#删除题目form-questions-delete)。

## 按操作读取协议

| 操作 | 命令或协议入口 |
|---|---|
| 列出、创建、更新、删除题目 | `+form-questions-list/create/update/delete`；见[题目协议](form-questions.md) |
| 调整可见题目与题序 | `+view-get-visible-fields` / `+view-set-visible-fields`；见[可见题目与排序](form-questions.md#可见题目与排序) |
| 展示、提交、通知、结果页与抽奖配置 | 见[表单配置协议](form-settings.md) |
| 读取分享表单详情与提交 | `+form-detail` / `+form-submit`；详情见[分享表单详情协议](form-fill.md#读取表单详情form-detail)，提交见[填写与提交协议](form-fill.md) |
| 分享读取与更新、二维码、提交后查询页 | `+form-share-get/update`；见[分享与查询入口协议](form-share.md) |
