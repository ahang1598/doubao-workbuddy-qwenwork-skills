# open_invoice_match_review_ui — 呼起票据匹配 UI（MCP Apps）

> ⚠️ **参数填法以本文为准**：MCP 运行时的 `inputSchema` 常弱类型/失准（如 `repeated` 被标成无 `items` 的 `array`、`int32` 变 `string`、必填字段未暴露）。调用本工具时**禁止仅凭 inputSchema 猜测**，严格按本文的「请求参数」表与示例构造；类型/结构以本文为唯一权威。

> **🔄 2026-08-18 协议变更（`submit` 字段去 `next_step_modify`）**
> 1. **工具名**：`open_invoice_match_review_ui`。
> 2. **`UiReq.submit` 字段**：字段号 `13`；类型 `InvoiceMatchReviewSubmitConfig`，**只保留 `next_step`（= 1），删除 `next_step_modify`（= 2）**——提交在 UI 内直接完成，不再有「保存修改→重新匹配」的回调。

> **所属层级**: 第 3 层（依赖匹配结果 + 已上传的 `invoice_url`）
> **场景**: 票据处理流程 Step 9 —— 把两个分类列表交给页面，让用户勾选/修改
> **关联工具**: 前置 `cos_batch_upload.py`（**脚本内部静默调 `get_org_cos_credential(private=0)` 取临时密钥**后并发上传，必须先拿到 `invoice_url`，⛔ agent 不直接调该 MCP 工具）；后置由 UI 回调 `提交票据到远程` 命名步骤（提交在 UI 内完成）
> **最后更新**: 2026-08-18（删除 `next_step_modify`；提交改由 UI 内直接完成）

## 🔴 调用范式变更（2026-08-17：data_cache_id 模式）

> ⚠️ **`open_invoice_match_review_ui` 不再直接收完整 `UiReq`**。完整 `UiReq`（含两个 `repeated MatchItem` 数组）体量大、且经 agent stdout 透传极易被二次序列化成字符串, 触发 `[]json.RawMessage` 调用失败。新范式：**先把 `UiReq` 缓存到远程, 再用 `data_cache_id` 呼起 UI**（对齐 alert-expert 的 `build_record_ui_params.py`）。

agent 侧三步：

1. **生成 UI 参数 json**：`run_pipeline.py`（`full`）跑完会把完整 `ui_req` 落盘到 `ui_req.json`（两个分类列表 + `submit` + `org_no`）。这是「调用 UI 的参数」的唯一权威来源。
2. **缓存到远程 → `data_cache_id`**：调用脚本
   ```bash
   python build_invoice_match_ui_params.py --json-file <workspace>/ui_req.json
   ```
   它读取 `ui_req.json`, 经 `set_common_data_cache` 接口把 `UiReq` 缓存到远程, 产出 `data_cache_id`, 并写出 `ui_params.json = {"caller_expert_id": "invoice-expert", "data_cache_id": "<key>"}`。
3. **用 `data_cache_id` 呼起 UI**：把 `ui_params.json` 的内容（**只有** `caller_expert_id` + `data_cache_id` 两个字段）作为 `open_invoice_match_review_ui` 的入参。⛔ **不得**再把完整 `UiReq` 直接传给该工具。

> 📌 `build_invoice_match_ui_params.py` 已自动补 `caller_expert_id="invoice-expert"`、校验 `org_no` / `submit` 非空; 缓存失败会以 `{success:false}` 退出, 此时**不呼起** UI。完整 `UiReq` 结构定义见下方「缓存内容：`UiReq`」一节。

## ⚠️ 这是 MCP Apps，不是 webview postMessage

`UiReq` 是**一个 MCP 工具的入参本身**（对齐 alert-expert 的 `open_org_cert_update_review_ui` / `open_fund_raising_program_update_ui` 模式），**不是** webview 的 `INIT` payload。在 `data_cache_id` 模式下, 该入参先经 `set_common_data_cache` 缓存, 工具实际只收到 `{caller_expert_id, data_cache_id}`（见「真正传给 `open_invoice_match_review_ui` 的入参」一节）。

| |说明 |
|---|---|
| **入参** | **`data_cache_id` 模式**下工具只收 `{caller_expert_id, data_cache_id}`（见**第二部分**）；完整 `UiReq` 经 `set_common_data_cache` 缓存（见**第一部分**）。⛔ MUST NOT 额外包裹自造的 session / wrapper 字段 |
| **返回** | **不同步返回**用户操作结果 |
| **后续** | **呼起 UI 的工具调用返回成功后，本轮必须立即结束，且本轮对话输出只能是「一句极简提示」**（如 `票据信息已识别完成，已为您打开匹配确认页面，请在页面中确认并选择提交。`）。⛔ **绝对禁止**在此句外再输出任何内容：不得输出摘要/统计表格/数量清单/分支说明/进度播报/文件路径，⛔ **不得回显内部思考或推理过程**，⛔ 不得追问或寒暄，⛔ 不得输出多行。之后**不再输出任何文字、不再发起任何工具调用**，原地等待用户操作——⛔⛔ 实测事故：继续输出会把刚打开的 UI 页面**刷没**（前端把新文字流当作新一轮渲染内容，覆盖掉已展示的 UI），用户将看不到票据确认页；UI 会依据 `submit` 文案告知 Host 接下来调哪个**命名步骤** |


## 文档结构（两部分）

本文档把「呼起票据匹配 UI」拆成两个**互不混杂**的部分，避免 agent 把大体积 `UiReq` 直接透传给工具：

- **第一部分 · `set_common_data_cache` 缓存内容（`UiReq`）**：经 `build_invoice_match_ui_params.py` 缓存到远程、并作为 UI 回调回传的「完整 `UiReq`」结构定义。agent **不直接**把它传给工具。
- **第二部分 · 调用 `open_invoice_match_review_ui` 的入参（`data_cache_id` 模式）**：agent 实际调用 MCP 工具时**只传**的两个字段 `{caller_expert_id, data_cache_id}`。

---

## 第一部分：`set_common_data_cache` 缓存内容（`UiReq`，即 UI 回传内容）

> 以下结构**不是**直接传给 `open_invoice_match_review_ui` 的入参, 而是交给 `build_invoice_match_ui_params.py` → `set_common_data_cache` 缓存的「完整 `UiReq`」, 也是 UI 回调时交还 Host 的完整数据结构。工具真正收到的只有 `{caller_expert_id, data_cache_id}`（见第二部分）。

```protobuf
message UiReq {
  string org_no = 1;                                  // 机构ID
  repeated MatchItem matched_items = 11;              // 匹配成功列表
  repeated MatchItem matched_failed_items = 12;       // 未匹配/异常列表
  InvoiceMatchReviewSubmitConfig submit = 13;         // ★ 续接Prompt, 见下方专节
}

message InvoiceMatchReviewSubmitConfig {
  string next_step = 1;         // 提交时回传给 Host 的续接 Prompt（唯一字段）
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|-----|-----|------|
| `org_no` | string | ✅ | **必须**是 `get_user_and_org_info` 返回的真实值，⛔ 不得传空或占位 |
| `caller_expert_id` | string | ✅ | **本专家固定传 `"invoice-expert"`**。真实 MCP `inputSchema` 必填（对齐 alert-expert 的 `open_org_cert_update_review_ui`），遗漏会被参数校验拒绝；机构由 MCP Token 绑定，无需另传 `org_no` 之外的机构标识 |
| `matched_items` | `repeated MatchItem` | — | `match_status = 1` 的票据，`status = 1`（默认勾选）|
| `matched_failed_items` | `repeated MatchItem` | — | `match_status = 2` 的票据，`status = 0` |
| `submit` | `InvoiceMatchReviewSubmitConfig` | ✅ | **固定文案**的自然语言续接 Prompt，由 `title_normalizer.py` 统一写入，⛔ agent 不得自行拼装或改写，见下方「★ submit」专节 |

> ⛔ **只有这两个列表。** `matched_suspect_items`（可疑）与 `no_need_process_items`（无需处理）**已从协议删除** —— 单一远程精确匹配下匹配结果是**二值**的。
>
> md5 重复与命中 `success_list` 的票据归入 `matched_failed_items`，靠 `match_status_reason` 区分。

## `MatchItem` 字段表

```protobuf
message MatchItem {
  // 已移除的识别置信度和申请字段不能被后续业务复用。
  reserved 8, 21 to 23;
  reserved "match_confidence", "application_title", "application_amount", "application_project_name_list";

  // 用户勾选状态：0-未选中，1-选中。仅匹配成功项可在 UI 中切换。
  int32 status = 1;
  // 票据原文件链接。
  string invoice_url = 2;

  // 从票据识别出的抬头、金额（单位：分）及项目列表。
  string title = 3;
  uint32 amount = 4;                      // 识别出来的票据金额, 单位:分
  repeated string project_name_list = 5;

  // 匹配状态：1-匹配成功（默认勾选），2-未匹配/异常。
  int32 match_status = 6;
  string match_status_reason = 7;

  // 平台票据申请编号。
  string application_number = 11;

  // 是否已在 UI 编辑：0-未修改，1-已修改。
  // （已无「保存修改→重新匹配」回调，本字段仅作协议兼容保留，不再触发 Host 侧动作）
  int32 modify_status = 31;
}
```

| 字段 | 填法 |
|-----|-----|
| `status` | `match_status=1` → `1`；`match_status=2` → `0`（⛔ 未匹配票**不得**预勾选）|
| `invoice_url` | **COS 上传后的 CDN 链接**，⛔ 不得为空。它同时是 item 的**唯一标识键**（协议无 `pdf_id`）|
| `title` | 识别值（匹配成功时**恒等于**申请单抬头）|
| `amount` | **`uint32`，单位分**。直接用 `value_cents`（脚本 `to_match_item()` 输出整数）|
| `project_name_list` | **由项目列表匹配出来的项目名**（`project_matcher.py` 出参 `project_name_list`）；未匹配到填`[]`；⛔ 不放票据识别的"项目名称"/"备注"原文 |
| `match_status` | `1` 或 `2`，**二值** |
| `match_status_reason` | 按实际原因取五种文案之一（见 `../../SKILL.md`），⛔ 不得一律用默认文案 |
| `application_number` | `match_status=1` 填候选行编号；`match_status=2` **留空** |
| `modify_status` | 出参恒为 `0`；入参（回调时）`1` 表示用户改过|

### ⛔ 严禁出现的字段

| 字段 | 原因 |
|-----|-----|
| `match_confidence` | 三档置信度已废除，协议无此字段 |
| `default_selected` | 勾选态由 `status` 承载 |
| `pdf_id` | 协议无 id 类字段，唯一键是 `invoice_url` |
| `project_id` | 它只属于 `filters`，UI 层只暴露项目**名** |
| `application_title` / `application_amount` / `application_project_name_list` | v3 协议已删除 |

> **为什么删掉申请侧字段**：语义是「**要么完全匹配上，要么匹配不上**」。匹配成功时 `title` / `amount` **就是**申请单的值，分列展示无信息量。
>
> ⚠️ **副作用**：UI 上**没有**"识别值 vs 申请单值"的对比界面，用户只能看到一个 `application_number`，无法自行验证 agent 匹配到了哪一笔。因此**恒等式断言**（见下）是唯一的正确性保障。

## ⚠️ 空 repeated 字段处理（2026-08-12 新增：规避 agent 把空列表写成 `""`）

`matched_items` / `matched_failed_items` 都是 proto `repeated` 字段，**允许缺省**（缺省即等价于空列表）。

**🐞 根因（实测）**：调用接口失败，不是框架序列化丢的，是 **agent 在把脚本输出的 `ui_req` 转写成 MCP 工具参数时，把某侧为空的列表字段写成了 `""`**（字符串），而 proto 期望 `array`，`""` 直接导致接口调用失败。典型场景：本批票据全部匹配成功 → `matched_failed_items` 为空 → agent 自作主张填 `""`。

**🛠 工程化实现（已在 `title_normalizer.py` 的 `build_ui_req()` 落地）**：空列表**直接省略该字段**，连 `[]` 这个 token 都不输出。这样 `ui_req.json` 里**压根不存在**该字段，agent 把它原样交给 `build_invoice_match_ui_params.py` 缓存时无从把它写成 `""`，从根上杜绝该事故。

**📋 正向指引（agent 构造 / 透传 UiReq 时必须遵守）**：

| 做法 | 是否允许 | 说明 |
|-----|---------|------|
| **原样把 `ui_req.json` 交给 `build_invoice_match_ui_params.py` 缓存** | ✅ 强制 | 脚本已自动省略空字段；脚本读 `ui_req.json` → 校验 `org_no`/`submit` → 补 `caller_expert_id` → `set_common_data_cache` 产出 `data_cache_id`，agent ⛔ 不得手抄改写、⛔ 不得把完整 `UiReq` 直接当工具入参 |
| 空列表 → **省略该字段** | ✅ 允许 | 缺省等价于空，proto 合法 |
| 显式传 `[]` | ✅ 允许 | 合法空数组；仅当 agent 必须手写时才用 |
| 用 `""` 代替空列表 | ❌ **禁止** | 类型不匹配（proto 期望 array），**会直接调用失败** |

> **🔴 铁律**：agent **必须原样把脚本 `ui_req.json` 交给 `build_invoice_match_ui_params.py` 缓存生成 `data_cache_id` 后再呼起 UI**（⛔ 不得把完整 `UiReq` 直接作为 `open_invoice_match_review_ui` 入参）。当 `ui_req.json` 里 `matched_items` 或 `matched_failed_items` 任一侧"不存在"（被脚本省略 = 该侧无票据）时，agent **必须保持它不存在**，⛔ **不得"好心补" `""`**、⛔ 不得补 `[]`、⛔ 不得手抄重组。完整 `UiReq` 已随 `data_cache_id` 缓存在远程，工具只收 `{caller_expert_id, data_cache_id}`。

**🔁 回传防御**：万一 Host 侧收到 UI 交还的空 repeated 字段是 `""`，解析前**必须先把 `""` 当作 `[]` 处理**，⛔ 不得直接对字符串做迭代（`do_prune()` 已对 `submitted_invoice_urls` 做 `or []` 兜底）。

## 呼起前的强制断言

| 断言 | 失败处理 |
|-----|---------|
| `matched_items` 内全部 `match_status==1`且 `status==1` 且 `application_number` 非空 | 内部错误，**不呼起** |
| `matched_failed_items` 内全部 `match_status==2` 且 `status==0` 且 `application_number` 为空 且 reason 非空 | 内部错误，**不呼起** |
| **条数守恒**：两列表长度之和 == 本会话累计识别票据数 | 内部错误，**不呼起**（宁可报错也不推残缺数据）|
| **恒等式**：`match_status==1` ⟹ `title`/`amount` 与命中候选行恒等 | **反向映射 bug**，上抛内部错误 |
| `org_no` 非空且为真实值 | 内部错误 |
| 每个 item 的 `invoice_url` 非空 | 内部错误（上传失败的票不得进 UI）|

`title_normalizer.py` 的 `allocate` / `prune` 出参已带`ui_req`与 `assertions`，断言已由脚本完成；agent 侧**直接读 `build_invoice_match_ui_params.py` 产出的 `ui_params.json`**（含 `data_cache_id`）呼起 UI 即可，⛔ 不要手工重组两个列表、⛔ 不要把完整 `ui_req` 再塞回工具（`ui_req.submit` 也已由脚本填好，随 `data_cache_id` 一并缓存在远程）。

## ★ UiReq.submit：UI 内提交时回传给 Host 的续接Prompt

`submit` 是 `UiReq` 顶层字段，**固定一条自然语言文案**，由 `title_normalizer.py` 的 `build_ui_req()` 统一写入（常量 `SUBMIT_NEXT_STEP`），⛔ agent 不得自行拼装、改写或省略：

| 字段 | 触发时机 | 固定文案 |
|-----|---------|---------|
| `submit.next_step` | 用户在 UI 里点**提交** | `使用提交票据到远程步骤，剔除本地已提交项` |

**机制**：UI 内直接完成提交（`update_tickets` 由 UI 侧执行）后，把**「已提交成功的 pdf 链接列表」**连同该文案一并交还 **Host**（谁在驱动当前对话，就是谁；不保证是本专家自己）。Host 依据文案里的步骤名重新调度本专家执行「提交票据到远程」命名步骤（剔除已提交项 → 告知剩余，UI 侧已自行刷新展示剩余）。

> ⛔ 本专家常以 `Agent` 工具的 **subagent 模式**被调度（例如由 `today-todo-team-lead` 派发，须带 `subagent_type` + `team_name` + `name`）。subagent 调用同步且一次性——调 `open_invoice_match_review_ui` 后本专家这一轮就结束、把控制权交还调度方；而 UI 是**异步**的，用户点提交发生在未来某个不确定时刻。`submit` 的文案就是把"接下来该做什么"显式写清楚的**唯一**续接信号，不依赖任何隐式会话上下文。

**MUST**：
- `submit.next_step` 内容 MUST 逐字符使用上表固定文案，不得意译或精简
- ⛔ 不存在 `target_expert_name` / `next_skill_step` / `next_step_modify` 这类结构化路由字段——路由信息已编码在文案本身里

## 唯一命名步骤（在 agent 正文表格声明，规范中无 `steps` 字段）

| 步骤名 | 由谁触发 | 入参 | 产出 |
|-------|-------|-----|-----|
| `提交票据到远程` | 用户在 UI 内点"提交" → UI 回传已提交 pdf 列表 + `submit.next_step` → Host 重新调度 | UI 回传的「已提交成功的 pdf 链接列表」| 提交已在 UI 内完成 → `prune` 剔除已提交项 → 告知已提交 X 条、剩余 Y 条（不重新呼起 UI）|

### `提交票据到远程` 的关键约束

- ⛔ **agent 不得再调 `update_tickets` / `checkpoint guard`**（提交已在 UI 内完成）
- 用 `title_normalizer.py` 的 `prune` 按 `invoice_url` 剔除已提交项，重新组装剩余 `ui_req`
- 剩余 >0 → 告知"已提交 X 条，剩余 Y 条待处理"；剩余 =0 → 告知全部完成，两种情况都**不重新呼起 UI**（UI 侧已自行刷新）
- ⛔ 提交阶段**不得**重新上传 PDF（复用已有 `invoice_url`）
- ⛔ 已提交项 MUST 从 `items.json` 剔除，不得重新混入下一轮 `ui_req`（重复提交是真事故）

---

## 第二部分：调用 `open_invoice_match_review_ui` 的入参（`data_cache_id` 模式，即 agent 实际调用工具）

> 本部分只关心「agent 怎么调 MCP 工具」。工具入参**只有** `{caller_expert_id, data_cache_id}` 两个字段, 完整 `UiReq` 已随 `data_cache_id` 缓存在远程（见第一部分）。

### 工具入参：`{caller_expert_id, data_cache_id}`

工具入参**只剩两个字段**, 由 `build_invoice_match_ui_params.py` 写出的 `ui_params.json` 提供：

| 字段 | 类型 | 必填 | 说明 |
|------|-----|-----|------|
| `caller_expert_id` | string | ✅ | **固定 `"invoice-expert"`**（脚本已填） |
| `data_cache_id` | string | ✅ | `set_common_data_cache` 返回的缓存 key, 后端据此拉取完整 `UiReq` |

调用示例（agent 直接读 `ui_params.json` 内容作为入参，**不要**再拼任何别的东西）：

```json
{
  "caller_expert_id": "invoice-expert",
  "data_cache_id": "<set_common_data_cache 返回的 key>"
}
```

> ⛔ **铁律**：本工具入参**禁止**出现 `org_no` / `matched_items` / `matched_failed_items` / `submit` 等完整 `UiReq` 字段——那些已随 `data_cache_id` 缓存在远程。一旦把这些字段又原样塞进来, 既冗余也违背 `data_cache_id` 模式设计（且会重新触发数组二次序列化风险）。

## 🔴 运行时报错排查：`cannot unmarshal string into Go value of type []json.RawMessage`

**🐞 现象**：呼起 UI 接口返回 `json: cannot unmarshal string into Go value of type []json.RawMessage`（或类似 `[]json.RawMessage` 解码失败）。

**🔍 根因（确定性）**：`[]json.RawMessage` 是 Go 侧对 **`repeated` 消息字段** 的解码目标类型 —— 在本协议里**唯一**对应 `matched_items` 与 `matched_failed_items`（二者都是 `repeated MatchItem`）。报错意为：**这两个数组字段里至少有一个，到达后端时整体是「一个字符串」**（即被二次 JSON 编码成 `"[{...}]"` 这样的字符串），而非「数组对象」。

> 💡 **`data_cache_id` 模式下面向 agent 的风险已消除**：agent 现在只传 `{caller_expert_id, data_cache_id}` 两个字符串字段, 完全不碰两个 `repeated` 数组, 因此不会再出现二次序列化。`[]json.RawMessage` 事故只可能发生在 `build_invoice_match_ui_params.py` 调用 `set_common_data_cache` 时——该脚本用 Python `json.dumps` 单次序列化 `ui_req`(dict), 链路正确, 正常情况下不会触发。以下内容保留用于理解根因, 以及脚本需要调试时参考。

**🚫 两个常见误判（与本案无关，勿在此浪费时间）**：
- ❌ **`submit` 是嵌套对象还是顶层字段**：`submit` 的 `next_step` 是 `string` 类型。即使 `submit` 结构传错，错误也不会是 `[]json.RawMessage`（那只会发生在 `repeated` 消息字段）。Runtime `inputSchema` 若把 `submit` 拍平成顶层 `next_step`，按 schema 实际形态填即可；**无论嵌套还是拍平，都不会触发本错误**。
- ❌ **`project_name_list` 写成空对象 `{}` / 空字符串**：`project_name_list` 是 `repeated string`，解码目标是 `[]string`，报错会是 `cannot unmarshal ... into []string`，**不是** `[]json.RawMessage`。把它改成 `{}`（对象）反而会引发新的类型错误。正确值永远是数组（`[]` 或 `["项目名"]`）。

**🛠 修复（`data_cache_id` 模式下已工程化消除）**：`title_normalizer.py` 的 `build_ui_req()` 出参 `ui_req` 本就是正确结构（数组 / 嵌套对象齐全）。旧模式下「把脚本出参交给 MCP 工具」这一步容易被 agent 二次序列化; **新 `data_cache_id` 模式下这一步改由 `build_invoice_match_ui_params.py` 用 Python 单次 `json.dumps` 完成**, agent 只负责把 `ui_params.json` 的 `{caller_expert_id, data_cache_id}` 交给工具, 不再触碰数组, 因此该事故在 agent 侧已根除。

> 若 `build_invoice_match_ui_params.py` 自身缓存失败（如鉴权过期 / 网络异常）, 它会以 `{success:false}` 退出并**不产出** `ui_params.json`, 此时直接按报错排查 `set_common_data_cache`, ⛔ 不得把完整 `ui_req` 拿回来硬塞给 UI 工具兜底。

## 铁律

- ❌⛔ **直接把完整 `UiReq` 传给 `open_invoice_match_review_ui`**（必须经 `build_invoice_match_ui_params.py` 缓存得到 `data_cache_id` 后, 仅传 `{caller_expert_id, data_cache_id}`；完整 `UiReq` 已随 `data_cache_id` 缓存在远程）
- ❌ 入参外面包一层自造的 session / wrapper 字段
- ❌ 阻塞等待用户操作结果
- ❌ **编造用户的勾选或修改结果**
- ❌⛔ **调起 UI 成功后继续输出文字/发起其它工具调用**（只允许一句极简提示 `票据信息已识别完成，已为您打开匹配确认页面，请在页面中确认并选择提交。`，之后本轮立即结束；⛔ 不得输出摘要/表格/清单/文件路径/思考过程，否则会把刚打开的 UI 页面刷没）
- ❌ 呼起 UI 前没上传票据（`invoice_url` 为空）
- ❌ 只上传匹配成功的票据（两个列表**全部**都要上传 —— 未匹配的票用户更需要看原件才知道怎么改）
- ❌ 未匹配票据预先勾选
- ❌ 两列表归属与 `match_status` 不自洽就呼起
- ❌ 条数不守恒就呼起
- ❌ 出现协议未定义字段
- ❌ 给 `repeated` 字段传 `""`（空列表**必须省略该字段**或写 `[]`；⛔ 绝对禁止 `""`，否则接口直接调用失败）；且**必须原样把 `ui_req.json` 交给 `build_invoice_match_ui_params.py` 缓存**，⛔ 不得手抄改写、不得"好心补"空字段（完整 `UiReq` 经 `data_cache_id` 缓存在远程，工具只收 `{caller_expert_id, data_cache_id}`）
- ❌ `org_no` 传空或占位值
- ❌ **省略 `submit` 或其中字段**（Host 收不到续接指令）
- ❌ **`submit.next_step` 文案意译/精简**（必须逐字符使用固定文案）
- ❌ **自造 `submit.target_expert_name` / `submit.next_skill_step` / `submit.next_step_modify`**（不存在这类结构化字段，路由信息已编码进文案本身）

## 参考

- **参数装配脚本**：[`build_invoice_match_ui_params.py`](../../scripts/build_invoice_match_ui_params.py)（读 `ui_req.json` → `set_common_data_cache` → 写 `ui_params.json`）
- **SOP**：`../../SKILL.md` Step 9
