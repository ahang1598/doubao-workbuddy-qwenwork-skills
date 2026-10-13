# 01 · dispatch — 任务派发（创建与派发物理隔离）

> 派发是**运行时核心命令族**。`init` 负责创建/复用任务，`notify` 负责通知人群，两者物理隔离。
> - `dispatch init`：创建或复用任务（当前周期内有任务自动复用，无则新建），输出 `task_context`，**不发消息**
> - `dispatch notify`：基于已有 `task_id` 通知目标门店，**`--task-id` 必填**
>
> **派发必须由用户明确要求，禁止自动派发**——Agent 不得自行判断"该派发了"并执行，
> 不得在查询、汇总等操作中顺带触发派发，不得预测用户意图抢先派发。
> 详见 [`../shared/hard-constraints.md#H6`](../shared/hard-constraints.md#H6)。

---

## 速查表

| 想做什么 | 跳转 |
| :--- | :--- |
| 立即派发某模板（首次） | [#手动派发init--notify-两步](#手动派发init--notify-两步) |
| 用户已提供表单分享链接 | [#携带-form_url-的两步式](#携带-form_url-的两步式) |
| 派发被中断 / 用户后回复链接 | [#form_url-缺失时的处理agent-必读](#form_url-缺失时的处理agent-必读) |
| 二次催办未填写门店 | [#二次催办--only-pending](#二次催办--only-pending) |
| 已知任务但要重新通知部分门店 | [#其他常见场景](#其他常见场景) |
| 想搞清楚派发内部走了哪几步 | [dispatch-internals.md](./dispatch-internals.md) |
| 按自定义字段筛实例 | [#查询任务实例记录](#查询任务实例记录) |
| 修改实例的自定义字段值 | [#更新实例记录的自定义字段](#更新实例记录的自定义字段) |
| 查任务列表 / 改任务状态 | [`dispatch query` / `dispatch set-status`](#dispatch-query) |

> 通知发送状态、未填写名单查询、再次提醒：见 [02-monitor.md](./02-monitor.md)。

---

## 命令参数（先查 -h，再读决策点）

> 完整参数清单以 `uv run python scripts/cli.py dispatch --help` / `uv run python scripts/cli.py dispatch <subcmd> --help` 为准。
> 本节只列出 Agent 在「决策时」必须知道的关键点（互斥关系、默认行为、输出结构、安全保护）。

### dispatch init（唯一任务创建入口）

- **职责**：创建/复用任务 + 引导表单分享，**不发任何消息**
- **输出 `task_context` JSON**：`{task_id, form_url, form_view_id, is_new, ...}`（其余为系统内部字段）
- **复用规则（固定）**：当前周期内有任务 → 返回已有任务；无任务 → 新建。周期由模版的 `dispatch_cycle` 字段控制（`per_day` 按天（默认）/ `per_week` 按周 / `per_month` 按月）
- **`--form-url`**：传入合法链接跳过交互式引导，必须含 `/notable/share/form/` 或 `/share/form/`；内部编辑链接（`/i/nodes/`）会被拒绝
- **`--extra-info`**：本次附加信息，渲染到 `{额外信息}` / `{extra_info}` 占位符；模板未含占位符时自动以 `> 📌 …` 引用块追加正文末尾；**持久化到任务记录**，后续提醒复用。**当用户指定了截止时间（如"明天18:00"）但模板未配置 `expected_duration` 时，必须通过 `--extra-info "截止时间：YYYY-MM-DD HH:MM"` 将截止时间透传到通知消息中**

### dispatch notify（派发入口，主命令）

> [!CAUTION]
> **发送范围决策规则（必须严格遵守）：**
>
> `dispatch notify` **必须显式指定发送范围**，不带范围参数会直接报错。四选一：
>
> | 用户表述 | 必须使用的参数 | 禁止行为 |
> |---------|--------------|---------|
> | "通知**所有**门店" / "派发给**全部**" / 未指定范围 | **`--all`**（显式全量派发） | ❌ 禁止不带任何范围参数（CLI 会拒绝执行） |
> | "只通知**XX店**" / "发给**某某店长**" / 指定了具体门店或人 | **`--target-store-ids <store_id>`** | ❌ 禁止用 `--all` 代替导致全量派发 |
> | "通知**未填写的**" / "催一下没交的" | **`--only-pending`** | ❌ 禁止不加此参数导致重复通知已完成的人 |
> | "通知**华北区**的门店" / 按标签 | **`--tags <标签>`** | ❌ 禁止用 `--all` 代替导致全量派发 |
>
> **互斥关系**：`--all` 与 `--target-store-ids` / `--tags` / `--only-pending` 互斥，只能选一种。
>
> **关键**：当用户指定了具体门店或店长时，Agent **必须先通过 `store list` 查到对应的 `store_id`**，然后用 `--target-store-ids` 精确控制范围。**绝对禁止在用户明确指定了发送对象时使用 `--all` 执行全量派发。**

> [!CAUTION]
> **消息发送方式（H15，必须严格遵守）：**
>
> 向店长发送任何业务消息**必须且只能**通过 `dispatch notify` 完成。
> **绝对禁止**直接调用 `dws chat message send` 手动构造消息并发送。
>
> **用户提供了消息格式/模板时的两种处理方式**：
>
> **方式 A · 永久修改**（用户说"以后都用这个格式"）：
> 1. 先 `template update --template-id <ID> --dispatch-message-file <TEMP>/msg.md` 写入模板表
> 2. 再 `dispatch notify --task-id <ID> --all`（或其他范围参数）派发
>
> **方式 B · 一次性使用**（用户说"这次用这个格式发"但不改模板）：
> 1. 直接 `dispatch notify --task-id <ID> --all --message-override-file <TEMP>/msg.md` 派发
> 2. 不写入模板表，下次派发仍使用模板中的 `dispatch_message`
>
> `dispatch notify` 内部会自动读取模板的 `dispatch_message` 字段、渲染占位符、生成个性化表单链接后发送。
> 直接 `dws chat message send` 会导致：通知记录不写入、去重保护失效、表单链接无 prefill 参数、统计全部失真。

- **`--task-id` 必填**，**不接受 `--template-id`**（强制走「先 init 再 notify」两步式）
- **输出 `DispatchSummary`**：`{task_id, template_id, total, success, failed, skipped, details}`；`details[].reason` 常见值：`form_url 未配置` / `店长 UserID 缺失` / `消息发送被钉钉拒绝`
- **`--all`**（显式全量）：向所有活跃门店派发。**必须显式传入**，不带任何范围参数时 CLI 直接报错拒绝执行
- **目标门店选择**：`--all` / `--target-store-ids` / `--tags` / `--only-pending` 四选一（互斥）；**不传任何范围参数 → CLI 报错**
- **`--on-duplicate` 4 种行为**（**Agent 决策核心**）：
  - **不传**（探测模式）→ 先探测是否有已通知门店；若命中则**不派发**，输出 `{"status": "need_user_decision", "already_sent_count": N, "options": [...]}`（退出码 0，**这是等待用户决策，不是错误**），Agent 必须把 `options` 呈现给用户确认后再带 `--on-duplicate <skip|resend>` 重跑；若无重复则自动按 `resend` 派发
  - `ask`（显式传入）→ 对每个已通知门店弹 `(y/N/a/s/q)` 询问（**仅适用于交互式终端**，Agent 通常用不到）
  - `resend` → 不查历史，所有目标门店全部重发
  - `skip` → 跳过所有 `notify_status = sent` 的门店，只补发未通知的
- **`--only-pending` 安全特性**（二次催办专用）：
  - 自动计算"已通知未填写"作为目标，无需手动 `--target-store-ids`
  - 自动跳过 `need_user_decision` 探测，强制按 `resend` 处理
  - **默认半小时冷却保护**：上次 `notified_at` < 1800s 的门店静默跳过（`reason = cooldown_active`），避免短时间重复骚扰
  - 用户要立即重发可加 `--cooldown-seconds 0` 关闭冷却
  - 用户诉求是"只发给未填写的人"时**优先选 `--only-pending`**，而不是进入 `need_user_decision` 流程
- **`--form-url`** 传入会自动写入任务记录持久化
- **`--message-override` / `--message-override-file`**（一次性覆盖）：本次派发使用自定义消息正文（Markdown），**不写入模板表**。优先级：`--message-override` > 模板表 `dispatch_message` > 内置默认模板。标题仍从模板表 `message_title` 读取。两参数互斥。适用于用户说"这次用 xxx 格式发"但不想永久修改模板的场景
- **去重机制**：同人+同任务的通知记录由 `notification_id` 唯一键去重，重发是 update + `send_count++`，不会产生多条记录
- **历史别名**：`dispatch task` 是旧别名，仍可工作但**不应再使用**

> [!IMPORTANT]
> **派发粒度是门店级，不按人去重。** 系统按门店逐条通知，每家门店独立发一条消息给该门店的 `manager`（店长 userId）。
> 如果多家门店的 `manager` 是同一个人，该人会收到**多条独立通知**（每条对应不同门店的表单链接），这是设计如此。
>
> **Agent 展示「接收人」的规范**：
> - `DispatchSummary` 中的 `total` / `success` / `failed` 是**门店数**，不是人数
> - `DispatchSummary.details` 只包含 `store_id` 和 `result`，**不含接收人姓名**
> - Agent 向用户报告派发结果时，**接收人信息必须从门店清单的实际 `manager` 字段获取**，不能凭记忆、用户初始化时提到的人名、或门店名称来推断
> - 正确话术示例：「已向 3 家门店派发任务（西溪店/亲橙里店/西湖店），通知发送给各门店的店长。」
> - **错误示例**：「已通知陈嘉健、李泽阳、声禾」——如果门店清单中三家店的 manager 都是陈嘉健，这样展示就是错误的

### dispatch query / update / set-status

- **`dispatch query`**：查询任务列表，关键过滤组合是 `--template-id` + `--today` / `--last-n N` / `--date-from/--date-to`；输出 `{count, tasks: [...]}`
- **`dispatch update`**：只更新任务信息（`--form-url` / `--scope`），不发消息；想发消息走 `dispatch notify`
- **`dispatch set-status`**：状态枚举 `进行中` / `已完成` / `部分失败` / `已禁用`；**`已禁用` 的任务无法继续派发**

### dispatch instances / update-instance

- **`dispatch instances`** 多维过滤要点：
  - `--filter <字段名> <值>` 可多次叠加（AND 语义）
  - `--filter-empty` / `--filter-not-empty` 用于按字段空/非空筛选
  - `--fields F1,F2` 仅输出指定字段，**减少输出噪音**
  - `--count-only` 仅输出 `{count: N}`，统计场景必备
- **`dispatch update-instance`**：
  - `--set <字段名> <值>` 可多次同时改多个字段
  - **骨架字段不可改**（`store_id` / `store_name` 等）；尝试修改会报错。骨架字段定义见 [dispatch-internals.md#骨架字段](./dispatch-internals.md#骨架字段系统固定每张任务表都有)

### dispatch list-pending / dispatch notifications

`dispatch list-pending` 是 `dispatch notifications --filter unfilled` 的兼容别名，详见 [02-monitor.md](./02-monitor.md)。

---

## 手动派发（init → notify 两步）

> [!IMPORTANT]
> 派发被显式拆分为 **2 个独立子命令**，创建与派发**物理隔离**，**各自需要独立的用户授权**：
> - `dispatch init`：唯一建表入口，**不发任何消息**。触发信号：用户说"创建任务"
> - `dispatch notify`：派发入口，**直接影响一线店长**。触发信号：用户**明确说"派发/通知/发送"**
>
> **"创建任务"只允许执行 `dispatch init`，执行完必须停下来报告结果并等待用户下一步指令。**
> **只有用户明确说出"派发/通知/发送"类指令后，才允许执行 `dispatch notify`。**
> 详见 [`H9`](../shared/hard-constraints.md#H9)。

### 标准两步式（推荐）

> [!CAUTION]
> **步骤 1 和步骤 2 之间存在用户授权门禁。**
>
> **步骤 1（`dispatch init`）完成后，Agent 必须：**
> 1. 检查 `form_url` 是否非空
> 2. 检查 AI 审核字段创建状态（H11）
> 3. **向用户报告结果并停下来等待指令**（H9）
>
> **只有当以下两个条件同时满足时，才允许执行步骤 2（`dispatch notify`）：**
> - ✅ `form_url` **非空**（H12：为空时**必须硬停**，见下方「form_url 缺失时的处理」）
> - ✅ 用户**明确说出了"派发/通知/发送"类指令**（H9）
>
> **`form_url` 为空时绝对禁止执行 `dispatch notify`**——无有效表单链接的派发会导致
> 店长收到无法打开的死链接，造成严重业务事故。详见 [`H12`](../shared/hard-constraints.md#H12)。

```bash
# 步骤 1：创建/复用派发任务（仅建表，不发消息）
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch init --template-id TPL_xxx
# ⚠️ 执行完毕后必须停下来！
# ⚠️ 检查输出：form_url 是否非空？AI 审核字段是否创建成功？
# ⚠️ 向用户报告结果，然后等待用户的下一步指令

# === 用户授权门禁 ===
# 等待用户明确说出"派发" / "通知" / "发送"类指令后，才继续执行步骤 2
# 如果用户只说了"创建任务"，到这里就结束了，不要自行继续

# 步骤 2：基于已有 task_id 通知目标门店（必须满足：form_url 非空 + 用户明确授权）
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch notify --task-id TASK_TPL_xxx_20260424XXXX
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch notify --task-id TASK_xxx --on-duplicate skip
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch notify --task-id TASK_xxx --target-store-ids S001,S002 --on-duplicate resend
```

### 携带 form_url 的两步式

用户已提前准备好分享链接时使用，跳过交互式引导：

```bash
# 步骤 1：创建任务时直接传入 form_url
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch init --template-id TPL_xxx --form-url "<分享链接>"

# 步骤 2：派发（只补发未通知的门店）
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch notify --task-id <task_id> --on-duplicate skip
```

### 输出解读（`DispatchSummary`）

- `success`：成功发送通知的门店数
- `failed`：失败的门店数（`details` 里有 `reason`，常见 `form_url 未配置`、`店长 UserID 缺失`、`消息发送被钉钉拒绝`）
- `skipped`：被重复策略跳过的门店数

---

## form_url 缺失时的处理（Agent 必读）

> [!CAUTION]
> `dispatch init` 会**自动创建表单视图并发布分享**，绝大多数情况下 `form_url` 会自动获取成功。
> 内部有 4 级 fallback 链：`view_create_form` → `view_publish_share` → `view_get_detail` → `extract_form_share_url`（从 `formInfo.shareUuid` 拼接）。
> 仅当所有 fallback 均失败时才需要用户介入。
>
> **Agent 绝对不要自行拼接或猜测分享链接格式**——`shareUuid` 由系统生成，无法通过 baseId/tableId/viewId 推导。
> 完整约束见 [`#H12`](../shared/hard-constraints.md#H12)。

### 正常流程（绝大多数情况）

`dispatch init` 内部会自动执行：创建表单视图 → 发布分享 → 提取分享链接（含 shareUuid fallback）→ 写入 `form_url`。
输出的 `task_context.form_url` 非空，直接进入 `dispatch notify` 即可。

### 异常场景：自动发布失败（`form_url` 为空）

如果 `dispatch init` 输出的 `form_url` 为空（退出码 `1`），说明自动发布表单视图失败。
按以下步骤处理：

#### 步骤 1：从首次 `dispatch init` 的 JSON 输出中取出 `task_id`

#### 步骤 2：引导用户手动发布表单

告知用户：「表单视图已创建，但自动获取分享链接失败。请在 AI 表格中打开表单视图，
点击右上角**分享**按钮开启分享开关，完成后回复「已发布」即可。」

> **不要要求用户复制粘贴链接**——这是最后的降级手段，不是首选方案。

#### 步骤 3：用户告知已发布后，重新执行 `dispatch init`（系统自动获取链接）

用户发布表单后，重新执行 `dispatch init --template-id <TPL> --reuse <task_id>`，
系统会通过 `extract_form_share_url` 自动从视图详情的 `formInfo.shareUuid` 提取分享链接。

```bash
# ✅ 用户已手动发布：重新 init 复用已有任务，系统自动获取分享链接
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch init --template-id <TPL> --reuse <task_id>
```

#### 步骤 4（降级）：如果重新 init 后 `form_url` 仍为空，才要求用户粘贴链接

```bash
# ✅ 所有自动方式都失败，最终降级：要求用户粘贴分享链接
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch notify --task-id <task_id> --form-url "<分享链接>" --on-duplicate resend
```

```bash
# ❌ 错误：Agent 自行拼接/猜测分享链接
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch notify --task-id <task_id> --form-url "https://docs.dingtalk.com/notable/share/form/猜的UUID"
# ❌ 错误：不带 --reuse 重新 init（会创建新任务表）
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch init --template-id TPL_xxx --reuse new
```

> [!NOTE]
> `--form-url` 参数会自动将链接持久化到任务记录，下次复用时无需重复传入。
> 复用任务时相关数据表如已被删，会自动同名重建，**已持久化的 `form_url` 不会被覆盖**。

---

## 二次催办（`--only-pending`）

**触发信号**：用户说"重新通知没填的人 / 再催一遍 / 没填表的再发一次"。

调用 `dispatch notify --task-id <ID> --only-pending`；完整参数（含 `--cooldown-seconds`）见 `uv run python scripts/cli.py dispatch notify --help`。

CLI 自动：

1. 计算"已通知未填写"的成员作为目标（无需手动 `--target-store-ids`）
2. 自动跳过 `need_user_decision` 探测（无须二次确认）
3. 强制按 `resend` 处理（同时显式传 `--on-duplicate skip` 会被忽略并 warning）
4. 默认启用**半小时冷却保护**：上次 `notified_at` 在 1800s 内的门店被静默跳过
   （`result = skipped, reason = cooldown_active`），避免短时间内重复骚扰
5. 用户若明确要立即重发，可加 `--cooldown-seconds 0` 关闭冷却

---

## 其他常见场景

| 场景 | 命令 |
| :--- | :--- |
| 我已经建好今天的任务了，再通知 S001 / S002 | `dispatch notify --task-id <ID> --target-store-ids S001,S002 --on-duplicate resend` |
| 只补发未通知的店 | `dispatch notify --task-id <ID> --on-duplicate skip` |
| 全部重新发一遍，不要问我 | `dispatch notify --task-id <ID> --on-duplicate resend` |
| 把当日某模板派发都列出来 | `dispatch query --template-id TPL_xxx --today` |
| 标记某任务为已完成 / 已禁用 | `dispatch set-status --task-id <ID> --set 已完成` |
| 查询任务列表（按状态 / 日期） | `dispatch query --status 进行中 --date-from 2026-04-01` |

> 派发失败的门店会在 `details` 里带 `reason`（常见：`form_url 未配置`、`店长 UserID 缺失`、`消息发送被钉钉拒绝`）。

> **`form_url` 校验**：`dispatch init` 在引导用户粘贴分享链接时校验格式，必须含 `/notable/share/form/` 或 `/share/form/`；
> 内部编辑链接（含 `/i/nodes/`）会被拒绝。**任务记录里的 `form_url` 在首次派发后立即持久化**，下次复用直接读取。

> **重复创建硬保护**：底层在创建数据表前会先按表名查 AI表格，存在同名表则直接复用 tableId，避免重复。详见 [dispatch-internals.md#重复创建硬保护](./dispatch-internals.md#重复创建硬保护)。同周期内重复执行 `dispatch init` 也会自动复用已有任务，不会产生重复。

> 如果「任务记录」表是旧 AI表格 创建的（缺 `form_url` / `form_view_id` 字段），先跑 `init url <BASE_ID> --auto-repair` 补齐。

> **想了解派发内部如何分阶段执行 / `form_url` 校验规则 / 重复创建硬保护的实现细节** → [dispatch-internals.md](./dispatch-internals.md)

---

## 查询任务实例记录

**触发信号**：用户问"按巡检类型筛一下记录 / 哪些店还没填整改状态 / 给我看华东这批的实例"。

通过 `dispatch instances` 查询任务的巡检实例记录，支持按自定义字段多维度过滤：

```bash
# 查询某任务的所有实例记录
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch instances --task-id TASK_xxx

# 按自定义字段值精确过滤（可多次使用 --filter 组合过滤）
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch instances --task-id TASK_xxx --filter 巡检类型 日常巡检
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch instances --task-id TASK_xxx --filter 巡检类型 日常巡检 --filter 区域 华东

# 筛选某字段为空的记录（如找出未评分的实例）
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch instances --task-id TASK_xxx --filter-empty 评分

# 筛选某字段不为空的记录（如找出已填写整改状态的实例）
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch instances --task-id TASK_xxx --filter-not-empty 整改状态

# 按门店 ID 过滤
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch instances --task-id TASK_xxx --store-id S001

# 仅输出指定字段（减少输出噪音）
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch instances --task-id TASK_xxx --fields store_name,巡检类型,整改状态

# 仅统计总数（用于统计场景）
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch instances --task-id TASK_xxx --filter-empty 评分 --count-only
```

> 通过 `task_id` 自动定位对应的巡检实例记录，无需用户手动给表名 / tableId。

---

## 更新实例记录的自定义字段

通过 `dispatch update-instance` 更新实例记录中的自定义字段值（**骨架字段不可修改**）：

```bash
# 先通过 dispatch instances 查到 record_id
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch instances --task-id TASK_xxx --store-id S001 --fields record_id,store_name

# 更新自定义字段值（可多次使用 --set 同时更新多个字段）
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch update-instance --task-id TASK_xxx --record-id <recordId> --set 整改状态 已完成
cd <SKILL_DIR> && uv run python scripts/cli.py dispatch update-instance --task-id TASK_xxx --record-id <recordId> --set 整改状态 已完成 --set 备注 "已现场复查"
```

**骨架字段不可修改**（如 `store_id` / `store_name` 等），尝试修改会报错。
骨架字段定义见 [dispatch-internals.md#骨架字段](./dispatch-internals.md#骨架字段系统固定每张任务表都有)。

---

## 相关参考

- 派发内部机制（阶段 1/2 状态机 / 重复创建硬保护）：[dispatch-internals.md](./dispatch-internals.md)
- 通知明细查询 / 未填写名单 / 催办：[02-monitor.md](./02-monitor.md)
