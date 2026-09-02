---
name: invoice-processing
description: 票据处理编排能力。负责机构待开票任务全流程：PDF 光栅化 → 全本地 OCR → 金额/项目/抬头处理 → 精确匹配 → 上传 → 呼起匹配 UI，用户在 UI 内直接提交。正常流程由 run_pipeline.py 一次性跑完，agent 只负责写 manifest、调脚本、呼起 UI 三件事。
---

# 票据处理编排

## ⛔ MCP 工具调用铁律

> agent 唯一直调的 MCP 工具是 `open_invoice_match_review_ui`（呼起 UI，入参仅 `{caller_expert_id, data_cache_id}`），其契约见 `references/tools/open_invoice_match_review_ui.md`。其余 MCP 工具（`get_project_list` / `list_pending_tickets` / `get_org_cos_credential` / `get_pending_invoice`）**参数已由脚本内部固定，agent 不直调、不构造参数**。

## ⛔ 全局对话铁律

- ⛔ **绝对禁止把内部思考 / 推理过程作为对话内容展示给用户**（思考链、工具调用前的推演、候选方案权衡、约束逐条比对、内部状态机推演等）。用户只应看到**结论性、可执行的反馈**。
- 需要"解释原因"时，**只给业务层结论**（如"该申请单已被本批其他票据占用"），⛔ 不得展开内部推导路径。
- 内部调试信息、脚本日志、断言细节 ⛔ 不得回显给用户。
- ⛔ **金额单位铁律：`amount` 恒为「分」（uint32），不是「元」**。凡向用户描述 / 播报金额，**必须**先做「分→元」换算，且**必须整数运算** `f"{c//100}.{c%100:02d}"`（⛔ 严禁浮点除法，`33000/100` 可能得到 `329.999...`）。

## 🚀 主编排器 run_pipeline.py（agent 主路径）

正常流程 agent 只需做三件事：

1. **写 `manifest.json`**：把用户 PDF 绝对路径（`pdf_paths`）+ `session_id` + `workspace` + `progress_log` 写入（`org_no` / `org_name` 可选，不传时脚本内部自查）。格式见脚本顶部 docstring。
2. **调一次**：`python skills/invoice-processing/scripts/run_pipeline.py --input-file manifest.json`（用 `run_in_background=true` 后台启动）。
3. **读落盘文件并呼起 UI**：读 `{workspace}/ui_req.json`（完整 `UiReq`）→ 调 `build_invoice_match_ui_params.py` 经 `set_common_data_cache` 缓存拿到 `data_cache_id` → 以 `{caller_expert_id, data_cache_id}` 调 `open_invoice_match_review_ui`（⛔ 不得把完整 `UiReq` 直接传给工具）。

脚本内部一次性跑完「md5 去重 → 光栅化 → 全本地 OCR → 金额换算 → 项目匹配 → 远程匹配 → m:n 分配 → COS 上传 → 组装 `ui_req`」。

> 🔴 **禁止运行时探查与手工装包**：不得为了"确认格式/兼容性"读取编排器源码、导入 OCR 包探测、执行 `pip install`。manifest 与启动命令是稳定契约，依赖初始化只由编排器内部单入口完成。

## ⛔ 核心红线（头等铁律）

1. **光栅化 vs 文本层**：PDF 必须光栅化成图片再 OCR。⛔ **严禁**用 `pypdf` / `pdfplumber` / `pdftotext` 读 PDF 文本层当字段来源（加密字体 → CID 乱码 → 假字段 → 假结论）。"PDF 里能提到文本" ≠ 可以跳过光栅化。
2. **匹配信号只有 3 个**：`title`（抬头）+ `amount`（金额，分）+ `project_id`（项目 ID，可选）。后端只吃这 3 个字段，⛔ 不得把其它字段当匹配条件。
3. **匹配结果二值**：只有 `match_status = 1`（命中）/ `2`（未命中），**没有置信度概念**。⛔ 不得自造 `match_confidence` / `default_selected` 等字段，⛔ 不得在对话里报告"置信度 92%"或 `high/medium` 档位。
4. **不 LLM 代算**：金额换算走 `amount_conversion.py`、抬头归一化走 `title_normalizer.py`、项目名映射走 `project_matcher.py`、匹配走 `list_pending_tickets`。⛔ 严禁 LLM 自己算金额、改写抬头、做子串匹配、实现编辑距离/语义匹配"救回"未命中的票。
5. **不手工装依赖 / 不过早放弃**：宣布"本环境做不到"前，**必须先运行编排器并读取结构化错误**。依赖缺失由脚本单入口补齐，⛔ 不得手工 `pip install`、拆包补装。
6. **匹配 0 命中 ≠ "捐赠人不存在"**：只代表"本次 filter 组合没找到候选"。⛔ 不得据此得出"捐赠人不存在""金额异常""用户走错机构"等结论。

## 批处理与性能

### 实时进度协议（日志文件）

- **脚本侧（写）**：`run_pipeline.py` 向 `progress_log` 追加用户可读的中文进度（如 `🔍 OCR识别阶段：已处理 10/100`），节点前缀形如「📋 准备 / 🖼️ 光栅化 / 🔍 OCR识别 / 📝 字段抽取 / 📚 项目库 / 🔗 项目匹配 / 🌐 远程匹配 / ☁️ 原件上传 / 🧩 组装」。
- **对话侧（读）**：agent 后台启动脚本后用 `TaskOutput(task_id, block=false)` 取权威状态，`running` 时 `tail -n 1 <progress_log>` **原样转述末行**（短任务 3~5s / 长任务 10~30s 轮询），`completed` 时 `wc -l` + `tail -n 3` 汇总后停止。⛔ **不解析、不润色、不重算耗时**。
- 🔴 **远程匹配完成行固定「已处理/总数量」口径**（如 `已处理 100/100，自动匹配 13 笔，待人工确认 87 笔`）。⛔ 不得写成「成功 13 / 待处理 87」——`待处理` 会让 agent 误判"还有 87 张没匹配完"，实则该阶段已完成，87 笔是待用户在确认页确认的 `pending_list`。
- 🔴 **严禁只发一句「OCR识别中」就长时间静默**——必须持续转述节点/分批进度。
- 进度分母一律是本批上传数 `N`，⛔ 不得用全机构待开票总数 `M`。

### 耗时预估口径

1. 启动前用默认系数给一次预估区间（如"预计 4~6 分钟出确认列表"）+ 说明主要耗时来源。
2. 之后靠 `tail -n 1` 持续转述进度。⛔ **脚本一次跑完、agent 不重算耗时、不给"预计完成时刻"**（不存在"先跑一批→实测均值→二次播报"的分批校准）。

### 并发边界与话术

- ⛔ **不得向用户承诺 OCR / 匹配的并行加速**（匹配/提交接口不能并发）。
- 并发与阶段重叠都在脚本内部完成，agent 只需如实转述进度。

### 轮次预算软着陆

- 轮次到软着陆阈值主动收尾：落 checkpoint + 输出进度 + 告知"回复「继续」我接着处理"，⛔ 不硬跑到被截断。
- ⛔ **不得依赖"轮次用完平台会自动提示继续"**（续跑完全靠 checkpoint）。

### Token 治理与上传规模

- **候选池 / OCR 全文 / 全量匹配数据一律不进 agent 上下文**（脚本落盘，agent 只收计数级摘要）。⛔ 不得逐条罗列每张票据字段，向用户/调度方反馈用计数级摘要。
- 单次消息建议 ≤500 份 PDF；超过照常处理（路径长吃 token，但不阻断）。
- ⛔ **不要求"凑齐 M 张再开始"、不展示门槛式进度**（"1/M 张"）；处理中的进度反馈（分母是本批上传数）是合规且必要的。

### 对话话术硬约束（MUST 执行）

- **OCR 精度提示**：全本地 OCR 对印章/手写体识别率偏低，呼起 UI 前 MUST 告知用户"本批使用本地识别引擎, 精度可能下降, 请在确认页面重点核对"。

## 触发场景

- 用户直接对话："我要处理待开票的票据"、"帮我处理这些 PDF"、"批量上传票据"等。
- 被 today-todo-team-lead 调度，prompt 明确"引导用户完成票据处理流程"。

## 工作流程

> **核心节奏（铁律）**：用户一次性发送本次要处理的全部票据 PDF，agent 收到后**立即**写 manifest → 调一次 `run_pipeline.py` → 拿 `ui_req` → **直接呼起 UI**。⛔ 不弹"继续上传/开始匹配"二选一、不要求分批、不提醒可多次发。

### Step 1: 提示上传 PDF

```
请上传您本次要处理的票据 PDF（可一条消息附带多份），发送后我会识别并直接打开匹配页面供您确认。
（单次消息建议不超过 500 份）
```

> ⛔ 措辞要点：不说"请上传全部 M 张后开始"、"进度 X/M"、"可分几次发"。`M` 只是背景信息，不是本轮要凑够的目标数。

### Step 1.5: 收到 PDF 立即跑全流程

用户在一条消息里发送了 ≥1 份 PDF → 立即写 manifest → 后台启动 `run_pipeline.py` → 按实时进度协议转述进度 → 脚本结束后读落盘文件呼起 UI。

### Step 2-8: 降级参考（仅脚本报错需调试时查阅）

正常流程不逐条执行各子脚本。脚本报错时，按「特殊情况处理」对应条目应对：

| Step | 脚本（均在 run_pipeline.py 内） | 出错时 agent 应对 |
|------|------|------|
| 光栅化 | `pdf_to_images.py` | 读编排器 `message` + `install_log` 如实上报；可原 manifest 重跑一次；⛔ 不手工装包 |
| OCR | `local_ocr_batch.py` | 引擎缺失脚本自动装；装失败如实上报 `attempted_remediation`，建议提高分辨率重试；⛔ 不拆包安装 |
| 金额换算 | `amount_conversion.py` | 失败 → 该票 `match_status=2` + reason「票据信息识别不完整」；⛔ 不 LLM 兜底算 |
| 项目映射 | `project_matcher.py` | 无命中/多 ID → `project_id=""`；⛔ 不 LLM 自由匹配、不因此得出"项目不存在" |
| 抬头归一化 | `title_normalizer.py` | ⛔ 不 LLM 自己改写抬头 |
| 远程匹配 | `list_pending_tickets` | 失败 → 该批 `match_status=2`，如实说明是接口失败；⛔ 不降级到 `get_pending_invoice` |
| COS 上传 | `cos_batch_upload.py` | 部分失败 → 如实告知明细，失败票 ⛔ 不得以空 `invoice_url` 进 UiReq；可重试 1 次 |

### Step 9: 呼起 UI

> 🔴 **`data_cache_id` 范式**：完整 `UiReq`（含两个 `repeated` 数组）先经 `build_invoice_match_ui_params.py` → `set_common_data_cache` 缓存拿 `data_cache_id`，再用 `{caller_expert_id, data_cache_id}` 两个字段呼起 UI。⛔ 不得把完整 `UiReq` 塞进工具。

1. 读 `{workspace}/ui_req.json`（含 `org_no` / `matched_items` / `matched_failed_items` / `submit`），⛔ 不得手抄改写；某侧列表为空时脚本会【省略该字段】，agent 必须保持它不存在，⛔ 不得"好心补" `""` 或 `[]`。
2. 调 `python skills/invoice-processing/scripts/build_invoice_match_ui_params.py --json-file <workspace>/ui_req.json` → 写出 `ui_params.json`（`{caller_expert_id, data_cache_id}`）。
3. 以 `ui_params.json` 内容调 `open_invoice_match_review_ui`。

`submit.next_step` 固定文案（脚本写入）：`使用提交票据到远程步骤，剔除本地已提交项`。

**🔴 呼起 UI 成功后，本轮立即结束，全部对话输出只能是「一句极简提示」**：
- ✅ 唯一允许：`票据信息已识别完成，已为您打开匹配确认页面，请在页面中确认并选择提交。`
- ⛔ 不得输出处理摘要/统计表格/数量清单/分支说明/进度播报/文件路径，不得把内部思考回显，不得追问或寒暄，不得输出多行。
- ⛔⛔ **实测事故**：调起成功后继续输出内容，会把刚打开的 UI 页面刷没（前端把新文字流当作新一轮渲染，覆盖掉 UI），用户看不到票据确认页。
- ⛔ 不阻塞等待、不编造用户勾选/修改结果。

### 提交后增量处理 + 命名步骤「提交票据到远程」

用户在 UI 内点提交 → UI 内完成 `update_tickets` → UI 回传「已提交成功的 pdf 列表」+ `submit.next_step` 文案交还 Host → Host 重新调度本专家执行命名步骤：

1. 调 `title_normalizer.py --input '{"mode":"prune",...}'` 剔除已提交项（按 `invoice_url`）。
2. 按 `remaining_count` 分流告知：`0` → "已提交 X 条，本批票据已全部提交完成"；`>0` → "已提交 X 条，剩余 Y 条待处理"（⛔ 不重新呼起 UI，UI 侧已自行刷新）。

> 🔴 **会话边界前置约束**：`prune` 复用存量/剔除已提交项，**一律以 `session_id` 与当前会话完全一致为前提**。跨会话（session_id 不一致）→ 视为全新批次，重新走完整流程，⛔ 不得采信他会话的 `invoice_url` / 旧匹配结果。

## 未匹配原因文案（agent 向用户解释用）

| 来源 | `match_status_reason` | 用户该做什么 |
|-----|---------------------|------------|
| `pending_list` 无命中 | 识别的信息匹配不到待开票记录 | 改抬头/金额后重匹配 |
| 候选行被同组前序票占用（m>n） | **已经有别的票据匹配上了** | 确认是否真有多笔捐赠 |
| 命中 `success_list` | **该票据对应的开票申请已提交** | 无需再提交 |
| 本批 md5 重复 | **存在相同文件** | 删掉重复上传那份 |
| 抬头缺失 / 金额换算失败 | 票据信息识别不完整, 请补填后重新匹配 | 在页面补填 |

> ⚠️ 已提交、md5 重复、申请单被占用这三种情况，票据识别信息**完全正确**，不能用默认文案让用户改抬头（改多少次都匹配不上，死循环）。

## 特殊情况处理

| 情况 | agent 应对 |
|------|-----------|
| 脚本报"没有可用的 PDF 光栅化后端" | 读编排器 `message` + `install_log` 如实上报；可原 manifest 重跑一次，⛔ 不手工装包 |
| 本地 OCR 引擎缺失/安装失败 | 脚本自动装；失败如实上报 `attempted_remediation`，建议提高分辨率重试或分批 |
| 沙箱不允许多进程 | 脚本自动退回串行；耗时预估相应上调，如实告知 |
| PDF 加密/损坏 | 提示"PDF 文件损坏或加密, 请重新导出后上传"；不降级 |
| 金额大小写冲突 | 以大写为准送匹配，对话里告知"该票金额识别存疑"；⛔ 不自造置信度字段 |
| `list_pending_tickets` 调用失败 | 该批 `match_status=2`，如实说明是接口失败而非无候选；⛔ 不降级 `get_pending_invoice` |
| `list_pending_tickets` 返回 0 候选 | 如实标 `match_status=2`；⛔ 不得得出"捐赠人不存在" |
| 同时命中 pending + success | 优先按 pending 处理（`match_status=1`），提示"存在历史已提交记录，请核对是否重复" |
| COS 上传部分失败 | 如实告知明细；失败票不得以空 `invoice_url` 进 UiReq；可重试 1 次，仍失败则本轮不呼起 UI |
| 提交回传含非本会话 `invoice_url` | `prune` 照常剔除匹配项、未知项列入 `unknown_invoice_urls` 上报；⛔ 不据此中断剔除 |
| 轮次接近软着陆阈值 | 落 checkpoint + 输出进度 + 告知"回复「继续」我接着处理"，主动结束本轮 |
| 用户上传 0 张 / 非 PDF | 0 张提示"未收到有效 PDF"；图片（PNG/JPG）跳过光栅化直接 OCR，其它格式提示"仅支持 PDF" |
| 用户中途关闭页面 | 视同取消；checkpoint 已落盘，下次可续跑 |
| A/A'/B/C 全失败 | 才提 Plan D：请用户把 PDF 导出为 PNG/JPG 重发；上报时列出 `attempted_remediation` |

## 参考文件

- `references/tools/open_invoice_match_review_ui.md` — Step 9：呼起票据匹配 UI（agent 唯一直调的 MCP 工具；入参仅 `{caller_expert_id, data_cache_id}`）
- `scripts/README.md` — 各脚本用法（降级调试时查）
