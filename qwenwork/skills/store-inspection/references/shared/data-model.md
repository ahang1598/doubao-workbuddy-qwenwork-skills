# 数据模型 / 字段字典（唯一来源）

> 表结构、字段语义、统计口径的唯一来源。`setup/` 与 `runtime/` 各文档涉及字段时
> 一律链接本文件。占位符规则见 `placeholders.md`，ID/时区见 `glossary.md`。

---

## 表结构总览

| 表名 | 类型 | 用途 | 主键字段 |
| :--- | :--- | :--- | :--- |
| `门店清单` | 固定表 | 门店与店长基础信息 | `store_id` |
| `巡店模版` | 固定表 | 任务蓝图：派发范围 + 自定义字段定义 + 时间策略 | `template_id` |
| `任务记录` | 固定表 | 每次派发的任务元信息（task_id / 表 ID / form_url / 统计） | `task_id` |
| `{模版名称}-{YYYYMMDD}` | 动态任务表 | 每次派发时创建，存储门店巡检数据 | `store_id`（行级） |
| `{模版名称}-{YYYYMMDD}-通知` | 动态通知表 | 每次派发时创建，记录通知发送明细（与任务表一对一） | `notification_id` |

> 表名硬编码不可改，详见 `hard-constraints.md#H3`。

---

## 门店清单

| 字段名 | 类型 | 必填 | 取值 / 说明 |
| :--- | :--- | :--- | :--- |
| `store_id` | text | ✅ | 全局唯一业务编码（推荐 `S001` `S002` …）。**主键，第一列** |
| `store_name` | text | ✅ | 门店名称（如 `北京朝阳店`） |
| `manager_user_id` | text | ✅ | 店长钉钉 UserID |
| `open_dingtalk_id` | text | ✅ | 店长 OpenDingTalkId（发消息时直接使用） |
| `manager_name` | text | ➖ | 店长姓名（冗余存储，便于报表展示） |
| `manager_mobile` | text | ➖ | 店长手机号（冗余，备查） |
| `tags` | multipleSelect | ➖ | 标签（如 `华北` `旗舰店`）。CLI 接收逗号分隔字符串 |
| `status` | singleSelect | ✅ | `active` / `inactive`。默认 `active`。inactive 门店派发时跳过 |

**业务约束**：
- `store_id` 一旦创建禁止改动。
- 想"暂停某门店派发"但保留历史 → 改 `--status inactive`，**不要 delete**。
- 大区 / 区域 / 示范店等分类属性统一通过 `--tags` 写入 `tags`（逗号分隔），不要单独新增字段。

---

## 巡店模版

| 分类 | 字段名 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| **基础** | `template_id` | text | 系统生成 | 主键，格式 `TPL_{yyyyMMddHHmmss}_{rand4}` |
|  | `name` | text | ✅ | 任务名称（如 `每日巡检`），也是动态任务表名的前缀 |
|  | `status` | singleSelect | ✅ | `enabled` / `disabled`。`disabled` 的模板在 `dispatch init` / `summary run` 中会被直接拒绝 |
|  | `created_by` | text | ➖ | 创建人 UserID |
|  | `description` | richText | ➖ | **模板介绍文本**（管理后台展示用，不参与消息渲染）。create 时未配置则以模板名兜底 |
| **派发消息** | `message_title` | text | ➖ | 派发消息标题，**提醒消息复用同一份**。详见 `placeholders.md` |
|  | `dispatch_message` | richText | ➖ | 派发消息正文 Markdown 模板，**提醒消息复用同一份**。详见 `placeholders.md` |
| **自定义字段** | `custom_fields` | text | ➖ | JSON 数组字符串，定义动态任务表的自定义巡检字段（见下） |
| **时间策略** | `remind_time` | text | ➖ | 再次提醒 cron 表达式（CLI 不消费，仅作元数据存储） |
| **汇总** | `summary_receivers` | text | ➖ | 逗号分隔的接收 UserID。为空则不推送 |

### custom_fields JSON 格式

```json
[
  {"name": "鲜食柜照片", "type": "attachment", "ai_review": true, "ai_standards": ["核心单品≥5个", "无欠品", "陈列整齐"]},
  {"name": "饮料柜照片", "type": "attachment", "ai_review": true, "ai_standards": ["商品摆放整齐", "价签对应"]},
  {"name": "客流情况", "type": "singleSelect", "options": ["正常", "偏少", "偏多"]},
  {"name": "客流数", "type": "number"},
  {"name": "备注", "type": "richText"},
  {"name": "负责人", "type": "user", "config": {"multiple": false}},
  {"name": "巡店评分", "type": "rating", "config": {"min": 1, "max": 5, "icon": "star"}}
]
```

**常用字段类型**：`text`（单行文本）/ `richText`（多行文本）/ `number`（数字）/
`singleSelect`（单选）/ `multipleSelect`（多选）/ `checkbox`（勾选框）/
`date`（日期）/ `url`（链接）/ `attachment`（附件）/ `telephone`（电话）/ `email`（邮件）

**扩展字段类型**：`currency`（货币）/ `user`（人员）/ `department`（部门）/ `group`（群组）/
`progress`（进度）/ `rating`（评分）/ `idCard`（身份证）/ `barcode`（条码）/
`geolocation`（地理位置）/ `address`（行政区域）/ `unidirectionalLink`（单向关联）/ `bidirectionalLink`（双向关联）

**隐藏字段**：任何自定义字段均可附加 `"hidden": true` 属性，使其在表单视图中对店长不可见（字段仍会被创建并支持通过 prefill 写入与服务端读取）。通过 `template update --custom-fields` 修改字段的 `hidden` 属性后，已有任务实例表的表单视图会自动同步更新 `visibleFieldIds`。示例：`{"name": "内部标记", "type": "text", "hidden": true}`

**AI 审核字段（巡检拍照推荐）**：对于 `attachment` 类型的巡检拍照字段，附加 `"ai_review": true` 即可启用 AI 自动审核。系统会自动创建对应的「AI审核_xxx」文本字段，AI 根据预设标准自动判定照片是否合规（通过 / 不通过 / 待人工确认）。可选参数：
- `"ai_standards"`: 审核标准列表（如 `["核心单品≥5个", "无欠品"]`），不填则使用通用默认标准
- `"ai_prompt"`: 完全自定义的 Prompt 文本，覆盖 `ai_standards`
- AI 审核字段创建失败时自动**降级为纯文本字段**（不中断流程），用户可后续手动升级

**AI 字段（通用）**：任何类型的字段均可附加 `aiConfig` 配置使其成为 AI 字段（通过 `dws aitable field create` 创建）。

> 各字段类型的 `config` 参数详情可通过 `dws aitable table create -h` 查询；
> AI 字段的 `aiConfig` 参数详情可通过 `dws aitable field create -h` 查询。

---

## 任务记录

每次派发由系统写入 / 更新一条记录。**采用 upsert 策略**：按 `task_id` 查询，存在则 update，不存在则 create。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `task_id` | text | 主键，格式 `TASK_{template_id}_{yyyyMMddHHmm}` |
| `template_id` | text | 关联模版 |
| `template_name` | text | 模版名称（冗余，便于查阅） |
| `task_table_name` | text | 动态任务表名（如「每日巡检-20260424」） |
| `task_table_id` | text | 动态任务表 tableId |
| `notification_table_name` | text | 动态通知表名（如「每日巡检-20260424-通知」） |
| `notification_table_id` | text | 动态通知表 tableId |
| `form_url` | url | 任务表的表单分享链接，**首次派发后持久化**；同日复用任务时直接读取，避免重复引导 |
| `form_view_id` | text | 任务表的表单视图 ID，用于复用时拼接引导链接（`https://docs.dingtalk.com/i/nodes/{baseId}?iframeQuery=sheetId%3D{tableId}%26viewId%3D{viewId}`） |
| `initiated_by` | text | 发起人 UserID（手动派发时记录） |
| `initiated_at` | date | 发起时间 |
| `target_store_count` | number | 目标门店总数 |
| `success_count` | number | 通知成功数 |
| `failed_count` | number | 通知失败数 |
| `status` | singleSelect | `进行中` / `已完成` / `部分失败` / `已禁用` |
| `extra_info` | text | 派发命令 `--extra-info` 透传的额外信息；提醒消息复用同一份内容。详见 `placeholders.md` |
| `reminder_round` | number | 已发送的提醒次数（每次 `reminder.run` 完成一次提醒后 +1 写回） |
| `dispatch_log` | text | 历次派发范围 / 触发记录追加日志 |

**业务约束**：
- `task_id` 一经创建禁止修改，作为 upsert 的判断依据。
- `form_url` 取值优先级：首次派发自动获取（`_create_form_view`）→ 失败时引导用户手动粘贴 → 写入任务记录后**永久保留**，同日复用任务直接读取。
- 用户在 AI 表格手动删除巡检表 / 通知表时，复用任务会自动重建（按 `task_table_name` / `notification_table_name` + 模版 schema 重建）。

---

## 动态任务表

每次派发时由系统动态创建，命名规则：`{模版名称}-{YYYYMMDD}`，如「每日巡检-20260424」。

### 骨架字段（系统固定，每张任务表都有，共 10 个）

骨架字段在表单视图中分为**可见**与**隐藏**两类。隐藏字段通过 URL prefill 自动写入，店长无感知；`inspection_id` 为系统主键（隐藏），「派发日期」和 `submitted_at` 为系统自动填充的可见信息。

#### 预写机制

派发时系统**不预创建骨架记录**，所有骨架字段通过 URL prefill 参数预填到表单链接中。
店长点击表单链接提交后，钉钉 FormDesigner 表单视图会**创建一条新记录**，
prefill 参数自动填充到对应字段。

- **prefill 字段**：`inspection_id`、`task_id`、`notification_id`、`派发日期`、`store_id`、`store_name`、`template_id`
- **不支持 prefill**：`店长`（user 类型不支持 URL prefill，需在表单中手动选择并设为必填）
- **自动记录**：`submitted_at`（createdTime 系统字段，自动记录表单提交时间）

| 字段名 | 类型 | 表单可见 | prefill | 说明 |
| :--- | :--- | :---: | :---: | :--- |
| `inspection_id` | text | ❌ | ✅ | **主键**，格式 `INSP_{task_id}_{store_id}`，每行唯一。**必须在第 0 位**（primaryDoc），避免 attachment 等类型做首字段被平台拒绝。不透出给店长，沿用英文内部名 |
| `task_id` | text | ❌ | ✅ | 关联任务记录，同一次任务所有行值相同 |
| `notification_id` | text | ❌ | ✅ | 关联通知表，用于判断是否已提交 |
| `派发日期` | date (YYYY-MM-DD) | ✅ | ✅ | 派发日期，共享表场景下按日期过滤。中文展示名 |
| `store_id` | text | ❌ | ✅ | 关联门店编码 |
| `store_name` | text | ❌ | ✅ | 门店名称（冗余，便于查阅） |
| `店长` | user | ✅（**必填**） | ❌ | 店长（钉钉人员类型），中文展示名。**user 类型不支持 URL prefill**，需在表单中手动选择自己。发布表单时务必将此字段设为必填 |
| `template_id` | text | ❌ | ✅ | 关联巡店模版 |
| `submitted_at` | createdTime (YYYY-MM-DD HH:mm) | ✅（自动） | — | 提交时间，AI 表格系统字段，自动记录记录创建时间（即店长提交表单的时间） |
| `特殊情况备注` | richText | ✅ | ❌ | 店长填写的文本备注，记录巡检中的异常情况。AI 审核 prompt 会参考此字段做豁免判定 |

> **表单视图配置**：
> - **visibleFieldIds**：`[派发日期] + [店长] + [submitted_at] + [特殊情况备注] + [可见的自定义字段]`。`inspection_id`（首字段/主键）不再加入可见列表，避免店长误改。不在列表中的字段自动隐藏（钉钉 AI 表格平台行为）。
> - **必填设置**：钉钉 AI 表格 view config API 不支持 `requiredFieldIds` / `readonlyFieldIds`，「店长」字段的必填需在发布表单时**手动配置**。

### 自定义字段

由模版的 `custom_fields` 定义，在骨架字段之后追加。店长通过表单视图填写这些字段。

**重要**：骨架字段包含系统级元数据和通用的业务备注字段（`特殊情况备注`）。
其他业务语义的用户填写字段**必须作为自定义字段**在 `template create --custom-fields` 中定义：

- **巡检拍照类**：如「鲜食柜照片」「饮料柜照片」 → `attachment` 类型（可配合 `ai_review: true`）
- **评价/判定类**：如「客流情况」「整洁度评价」 → `singleSelect` / `rating` 类型
- **人员类**：如「督导员」「巡检负责人」 → `user` 类型
- **备注类**：如「整改意见」 → `richText` 类型（注意：`特殊情况备注` 已在骨架字段中，无需重复定义）
- **数值类**：如「客流数」「评分」 → `number` / `rating` 类型

> **骨架字段不可修改**：`dispatch update-instance` 拒绝修改任何骨架字段。

---

## 动态通知表

每次派发时由系统动态创建，命名规则：`{模版名称}-{YYYYMMDD}-通知`。

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `notification_id` | text | 主键，格式 `NOTIF_{task_id}_{store_id}` |
| `task_id` | text | 任务 ID |
| `task_table_name` | text | 动态任务表名 |
| `template_id` | text | 关联模版 |
| `store_id` | text | 关联门店 |
| `store_name` | text | 门店名称（冗余） |
| `manager_user_id` | text | 店长 UserID |
| `manager_name` | text | 店长姓名（冗余） |
| `notify_status` | singleSelect | `pending` / `sent` / `failed` |
| `notify_fail_reason` | text | 通知失败原因 |
| `message_id` | text | 钉钉消息 ID |
| `form_link` | url | 表单链接（如有） |
| `notified_at` | date | 实际通知时间 |
| `send_count` | number | 通知发送次数（含历次重发） |
| `remind_status` | singleSelect | `not_required` / `pending` / `reminded` |

> Agent 通常通过 `monitor query` / `dispatch notifications` 读取，不直接写入。

---

## 统计口径（`stats` 命令族 + `summary run`）

`stats template / task / store / trend` 与 `summary run` 输出的所有指标均基于以下口径。

| 指标 | 计算方式 |
| :--- | :--- |
| **完成定义** | 动态任务表中**存在记录**即视为已提交（纯 prefill 模式下记录仅在店长提交表单时创建） |
| **平均完成耗时** | 对每条已提交的行，`submitted_at - 任务记录.initiated_at`（秒）；`submitted_at` 缺失或与 `initiated_at` 差值 ≤ 0 的行被剔除 |
| **dispatch_count** | 时间窗口内任务记录（`任务记录` 表）的条数 |
| **total_targets** | 累加任务记录的 `target_store_count` 字段 |
| **完成率** | `submitted / total_targets`（target 为 0 时记 0.0） |
| **模板活跃率** | 时间窗口内有派发的模板数 / 全部模板数 |
| **enabled 占比** | `status=enabled` 的模板数 / 全部模板数（与时间窗口无关） |
| **趋势桶** | `day` → `YYYY-MM-DD`；`week` → ISO 周编号 `YYYY-Www`（与 `datetime.strftime("%G-W%V")` 一致） |

**时间范围**：所有 `stats *` 命令按 `--days N`（最近 N 天，默认 7）或 `--from / --to`（含起含止）切片。
底层用任务记录的 `initiated_at` 字段做过滤；`--days` 与 `--from / --to` 互斥。

**容错**：若任务记录里 `task_table_id` 为空，或对应动态任务表已被手工删除，
统计会**跳过该任务**并记 warning，不会让整次统计失败。
