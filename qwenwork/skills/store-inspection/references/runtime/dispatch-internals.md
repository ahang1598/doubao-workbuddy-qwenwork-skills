# dispatch-internals — 派发流程内部机制

> 本文件是**内部实现参考**，面向排错和深入了解派发底层逻辑，不影响日常使用。
> 日常派发请回到 [01-dispatch.md](./01-dispatch.md)。

---

## 阶段 1 · `ensure_task` — 创建/复用派发任务

入口：`dispatch init`（唯一建表入口，`--template-id` 必填）。

1. **解析 `reuse_strategy`**：CLI 层面固定使用 `latest` 策略（当前周期内有任务则复用，无则新建），`new` 和 `<task_id>` 策略仅供内部 API 使用：
   - CLI 默认行为等价于 `latest` → 根据模版的 `dispatch_cycle` 字段（`per_day` / `per_week` / `per_month`，默认 `per_day`）计算当前周期的日期范围，查「任务记录」表**当前周期内**最新一条，找到则进入步骤 2 复用，否则降级新建
   - `new` / `<task_id>` → 仅内部 API 调用时使用，不通过 CLI 暴露
2. **复用分支：按需补齐**
   - 巡检表 `aitable_table_get(task_table_id)` 探活，缺则 `_create_task_table` 重建（同表名）
   - 通知表同样探活，缺则 `_create_notification_table` 重建
   - 读取任务记录里的 `form_url`：
     - **合法**（含 `/notable/share/form/` 或 `/share/form/`）→ 直接复用
     - **非法 / 为空 / 是内部编辑链接（含 `/i/nodes/`）** → 弹引导让用户重新分享
3. **新建分支**：建表 + 表单视图 → 占位写入「任务记录」（`status=进行中`，表 ID 留空）→ 创建完毕回填 `task_table_id` / `notification_table_id` / `form_view_id`
4. **`form_url` 引导**：如果当前没拿到合法分享链接，提示用户去
   `https://docs.dingtalk.com/i/nodes/{baseId}?iframeQuery=sheetId%3D{tableId}%26viewId%3D{viewId}`
   修改/发布/共享表单 → 用户粘贴 → **校验链接格式**（必须含 `/notable/share/form/`，禁止 `/i/nodes/`）→ 通过则立即 `upsert` 写入任务记录
5. **输出 `task_context`**：`{task_id, task_table_id, task_table_name, notification_table_id, notification_table_name, notif_field_map, form_url, form_view_id, is_new}`

---

## 阶段 2 · `notify_targets` — 基于 task_context 通知人群

入口：`dispatch notify`（`--task-id` 必填）。

1. **校验 `form_url`**：缺失或非法（`_is_valid_share_link == False`）→ **整个 notify 直接拒绝**，所有目标门店标记 `failed`，不会真的发垃圾消息
2. **筛选目标门店**：取模板关联的全部 `active` 门店；可被 `--target-store-ids` / `--tags` / `--only-pending` 进一步收窄
3. **重复通知策略**（`duplicate_strategy`）：
   - `resend` → 不查历史，全部直接派发
   - `skip` → 通过 fieldId 精确读取通知表，已 `notify_status = sent` 的门店直接跳过
   - `ask`（默认）→ 同样查已通知列表，对每个已通知的门店弹 `(y/N/a/s/q)` 询问：
     - `y` 重发该店
     - `n`（默认）跳过该店
     - `a` 之后所有已通知的店都重发，不再问
     - `s` 之后所有已通知的店都跳过，不再问
     - `q` 中止派发，剩余目标全部 `skipped`
4. **逐店派发**：拼接 `form_url + prefill_store_id/template_id` → 发钉钉消息 → 写入动态通知表
5. **回写任务记录**：`upsert` 当前任务的最终统计（成功/失败/跳过数 + `status`）

---

## 关键校验：`_is_valid_share_link`

为避免把"内部编辑链接"误当作"店长可填的分享链接"派发出去：

```text
合法 ✅: https://docs.dingtalk.com/notable/share/form/v01abc?source=link
合法 ✅: https://docs.dingtalk.com/share/form/v01abc
非法 ❌: https://docs.dingtalk.com/i/nodes/BAS_xxx?iframeQuery=sheetId%3D...   # 编辑链接
非法 ❌: https://example.com/random                                              # 无关 URL
非法 ❌: ""                                                                      # 空值
```

引导文案中只用编辑链接做"打开表单设置面板"的入口，**绝不会把它写进任务记录的 `form_url`**。

> [!IMPORTANT]
> 如果你的「任务记录」表是旧 AI表格 创建的（缺 `form_url` / `form_view_id` 字段），
> 先跑 `init url <BASE_ID> --auto-repair` 补齐，否则复用任务时永远要重新引导分享。

---

## 重复创建硬保护

`_create_task_table` / `_create_notification_table` 在建表前会先按表名查 AI表格，
存在同名表则**直接复用 tableId**，确保任何路径都不会产生同名重复表。

这是兜底防线，同周期内重复执行 `dispatch init` 也会自动复用已有任务，不会产生重复。

---

## 动态表字段定义

> 以下为系统内部自动创建的动态表结构，面向排错和深入了解，日常使用无需关注。

### 动态任务表

每次派发时由系统动态创建，命名规则：`{模版名称}-{YYYYMMDD}`，如「每日巡检-20260424」。

#### 骨架字段（系统固定，每张任务表都有）

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `store_id` | text | 关联门店 |
| `store_name` | text | 门店名称 |
| `manager_user_id` | text | 店长 UserID |
| `manager_name` | text | 店长姓名 |
| `task_id` | text | 关联任务 ID |
| `template_id` | text | 关联模版 |
| `submit_status` | singleSelect | `待提交` / `已提交` |

#### 自定义字段

由模版的 `custom_fields` 定义，在骨架字段之后追加。店长通过表单视图填写这些字段。

> **骨架字段不可修改**：`dispatch update-instance` 拒绝修改任何骨架字段。

### 动态通知表

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

## 相关参考

- 命令参数与日常派发处方：[01-dispatch.md](./01-dispatch.md)
- 字段定义（任务记录）：`../shared/data-model.md#任务记录`
