# 写入值与高频错误（aitable-write）

> 本文件只讲「cells 里各字段类型的写入值格式」和「已踩过的高频错误」。建 Base/表/字段/视图的完整命令序列见 `create-ledger.md`，取数见 `task-pull.md` / `agent-tasks-listing.md`，人员/附件详见 `people-attachment.md`。
> cells 的 key 一律是 fieldId，不是字段名；所有坐标运行时现场解析，不硬编码。

## 一、cellValue 速查（关键类型）

| 类型 | 写入格式 | 关键坑 |
|---|---|---|
| text | `"字符串"` | 直接字符串 |
| singleSelect | `"选项名"` | 传 name 字符串；不存在的 name 会自动建选项 |
| date | `"2026-08-14"` 或 `"2026-08-14 10:00"` | 日期串或 RFC3339 |
| checkbox | `true` / `false` | 布尔值 |
| user（人员） | `[{"userId":"<userId>","corpId":"<corpId>"}]` | **对象数组，单选也要数组**；详见 people-attachment.md |
| attachment | `[{"fileToken":"ft_xxx"}]` | 必须先 upload 拿 fileToken；禁用钉盘 drive |
| unidirectionalLink | `{"linkedRecordIds":["rec_xxx"]}` | 父记录字段即使 multiple=false 也只传 1 个父 recordId |
| url | `{"text":"钉钉","link":"https://..."}` | 对象或纯 URL 字符串 |
| progress | `0.75` | 0~1，写 75 会变成 7500% |
| rating | `4` | 整数，不能超 max |

只读字段（creator/lastModifier/createdTime/lastModifiedTime/formula/lookup/filterUp/AI 字段）**禁止写入**。

## 二、建表/字段硬约束

- `table create --fields` 第一个字段自动成为主字段，主字段只能是 text；把「任务标题」放第一位。
- 单次建表最多 15 个字段；超出需建表后用 `field create` 补。
- `singleSelect` 建表时 `options` 只传 `name`，`id` 由系统生成。
- `field update` 不能改类型，只能改名/改 config；`field` 只有 get/create/update/delete 四个子命令，没有 list/reorder。自关联 `unidirectionalLink` 要建表后再 `field create` 补，`linkedTableId` 填本表 tableId。

## 三、高频错误（严格避免）

- 参数名写 `--data` → 正确是 `--records`
- cells key 用字段名 `"任务标题"` → 必须用 fieldId `"fldXXX"`
- 不先 `table get` 拿 fieldId 就直接写 → 必错
- `--record-id rec --cells '...'` → 正确 `--records '[{"recordId":"rec","cells":{...}}]'`
- singleSelect 写入时传 option id 字符串 → 传 name 字符串
- user 字段传 `"姓名"` 字符串 → 传 `[{"userId":"<userId>","corpId":"<corpId>"}]`
- attachment 直接传本地路径 → 先 upload 拿 fileToken
- attachment upload 不传 `--mime-type` → 服务端不识别 .md 等扩展名直接报错，必须显式传（与 PUT 的 Content-Type 同值，对照表见 people-attachment.md）
- progress 写 75 → 写 0.75
- `record create/update` 返回空就判失败重跑 → stdout 可能为空但已写成功，用 `record query` 回读确认，盲目重跑会产生重复记录
- `workflow get` 用 `--flow-id` → list 返回的键叫 `flowId`，但 get 的 flag 是 `--workflow-id`