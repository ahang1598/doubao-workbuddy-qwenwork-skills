---
name: alert-ocr
description: 专家的 OCR 能力封装。证件类走"COS 上传 → 提交 OCR → 轮询结果"三步 pipeline（get_org_cos_credential + get_org_ocr_data + get_org_ocr_result）；备案号走 LLM 视觉。由 alert-cert-forms 和 alert-record-forms 内部调用。
---

# OCR 能力

## ⛔ MCP 调用已封装为脚本（AI 禁止裸调 MCP 工具）

> 本专家所有 MCP 工具调用已封装为 `skills/<skill>/references/scripts/` 下的 Python 脚本（共享客户端 `skills/_common/mcp_client.py`）。AI **只通过 `execute_command` 运行脚本获取结果，禁止直接裸调 MCP 工具**。
>
> 脚本已内置：参数构造（字段类型 / 嵌套结构 / repeated 裸数组等）、入口守卫（has_pending_review / 审批中）、一致性校验（no≠old_no / 图片域名）、失败上抛（绝不降级）。
> 脚本行为以 `references/scripts/*.py` 的 docstring 与实现为准，改动脚本须同步更新其 docstring。


## 概述

专家内部使用的 OCR 封装，采用**混合路由策略**：

- **证件类（法人登记证书 / 慈善组织公开募捐资格证书 / 负责人身份证）** → 走后端提供的 3 步云 OCR pipeline（对应 3 类 `OrgCertUpdateType`枚举：`1`、`2`、`3`）
- **备案号** → 走 codebuddy 多模态视觉能力 + prompt 约束

**⚠️ 证件类型口径统一**：cert_type=3（负责人身份证）在服务端按机构类型判定是"法人身份证"还是"专项基金负责人身份证"，Skill 层**不做区分**，统一走 `idcard` 字段块（见 `alert-cert-forms/references/idcard.md`）。

## 触发场景

**仅由预警专家的其他 skill 内部调用**：
- `alert-cert-forms` 调证件类三步 pipeline
- `alert-record-forms` 调 LLM 视觉

## 识别策略路由

| `strategy_id` | 执行方式 | 参考 |
|-----|--------|-----|
| `cloud_cert_pipeline` | 调用后端 3 步云 OCR pipeline（COS 上传 → 提交检测 → 轮询结果）| 见下方“三步 pipeline”章节 |
| `cert_type_detection` | 当前模型读取证件图片并进行类型粗判 | `references/cert-type-detection.md` |
| `llm_vision_record` | 当前模型读取备案表图片并按 prompt 提取字段 | `references/llm-vision-record.md` |

> ⛔ `strategy_id` 只是流程路由标签，不是工具名、脚本名、函数名或 MCP 名称。`cert_type_detection` 与 `llm_vision_record` 均由当前模型直接完成视觉理解，禁止搜索或调用名为 `cert_type_detection`、`llm_vision_record`、`LLM OCR`、`multimodal` 的额外工具。

### LLM 视觉策略统一执行契约

1. 优先读取用户消息提供的 `image_local_path`；每个唯一图片路径在正常流程中只调用一次图片读取能力。
2. 图片读取返回后，判断是否成功的**唯一依据是「你自己是否实际看到了图片的视觉内容（能否描述图片里有什么）」**——只要你能感知到图片内容，就是 `image_loaded=true`，已获得像素输入；这不等于字段提取已经完成。⛔ 不要被返回文本里的技术措辞（如 "unknown""stored at""blob" 等图片来源/存储说明）误导成"没读到图片"——那些不是失败信号。
3. 图片载入后，当前模型立即按对应 reference prompt 完成类型判断或字段提取，不再执行工具发现、能力搜索或引擎切换。
4. 只有图片读取**明确返回拒绝/错误字样**（"文件不存在""格式不支持""无法呈现图片""图片内容被过滤""当前模型不支持图片"等）、**且你确实看不到图片内容**时，才能记为 `image_loaded=false` 并提示用户重传。⛔ 严禁在已经能看到图片内容的情况下，仅凭返回文本里的 "unknown""stored at" 等措辞就宣称"不支持图片/内容被过滤"；不得因工具列表中没有视觉工具而宣称无法识别。
5. 多图场景按唯一图片路径逐张载入：备案号主表与合作方图各最多读取一次；正常读取次数应等于唯一图片路径数量。
6. 同一路径仅在明确读取失败且用户要求重试时允许再次读取；结构化 JSON 解析失败只重新结构化一次，不重复读取图片。

**⚠️ 云 OCR 走 pipeline 而非单一接口**：不同于 LLM 视觉策略，实际后端将证件 OCR 拆分为 3 步（上传 → 提交 → 轮询），需 Skill 层承担编排。

## 三步 pipeline（证件类专用，已封装为一键脚本）

> ⛔ AI 禁止裸调 `get_org_cos_credential` / `get_org_ocr_data` / `get_org_ocr_result`，一律运行封装脚本。

### 一键运行（凭证 → 上传 → 提交 → 轮询 全链路）

```bash
cd skills/alert-ocr/references/scripts && python3 remote_ocr.py <文件> --private 0|1 --ocr_type 0|1
```

脚本内部依次完成：取 COS 临时凭证 → 上传 → `get_org_ocr_data` 提交 → 轮询 `get_org_ocr_result` 直到 `state=1`，直接返回：

```json
{ "success": true, "access_url": "<上传链接>", "key": "<任务key>", "fields": [{"name":"...","value":"..."}], "original_data": {...} }
```

**关键规则**（脚本已强制）：
- **身份证必须走私有桶**（`--private 1`）→ 访问链接用 COS 原始域名；**其他证件走公有桶**（`--private 0`）→ CDN 域名
- `--private` 与 `--ocr_type` **必须同为 0 或同为 1**（身份证=1，其它=0），否则脚本直接报错
- 仅支持图片（jpg/jpeg/png）和 PDF（pdf）
- 轮询策略：5 秒/次，30 秒总超时；超时即失败退出，**不静默降级**（由调用方决定策略）
- 失败恢复：轮询超时须从 Step 1（即重新运行本脚本）重来

（如需仅上传不识别，仍可运行 `upload_cos.py <文件> --private 0|1`。）脚本参数与行为详见 `references/scripts/upload_cos.py` 与 `references/scripts/remote_ocr.py`。

## LLM 证件视觉分支

`strategy_id: cert_type_detection` 由当前模型执行：按上方视觉策略统一契约载入单张证件图片，再依据 `references/cert-type-detection.md` 粗判证件类型。它不是可调用工具，不得搜索同名能力。完整 K-V 识别仍须进入云 OCR pipeline。

## LLM 备案号视觉分支

`strategy_id: llm_vision_record` 由 `alert-record-forms` 调用：按上方视觉策略统一契约载入 1～2 张备案表图片，再依据 `references/llm-vision-record.md` 生成精简 `record_input.json`。它不是可调用工具，不得搜索同名能力。

备案号视觉分支必须按以下边界交付结果：

1. 图片载入完成只得到 `IMAGE_LOADED`，不得直接组装 UI 业务 JSON。
2. 当前模型提取字段，并合并用户选项目时已保存的 `context`，生成 schema 2.0 的 `record_input.json`。
3. 输入文件只落一份，位于当前工作目录（cwd）；不生成 `raw_ocr_text`、`evidence`、独立校验文件、项目上下文文件或 UI 参数文件。
4. `no` 与会话 `selected_old_no` 的提示和用户确认先由 Agent 完成；确认后调用 `alert-record-forms/references/scripts/run_record_ui.py` 一次完成校验、实时守卫、缓存和 UI 两字段输出。
5. 脚本终态自动清理输入文件；stdout 不输出业务字段或图片原文。

## 云 OCR pipeline vs LLM 视觉

| 维度 | 云 OCR 三步 pipeline | LLM 视觉（`llm-vision-record.md`）|
|-----|---------------------|-------------------------------|
| 覆盖对象 | 证件类（登记证 / 募捐资格证 / 身份证）| 备案号 |
| 精度 | 高（专业训练模型）| 中（依赖 prompt 约束）|
| 结构化 | K-V 强结构（后端解析）| K-V 弱结构（LLM 从 prompt 中提取）|
| 延迟 | 5-30 秒（异步）| 秒级（同步）|
| 图片依赖 | 需 COS 上传后的链接 | 直接传图片本体（多模态）|
| 适用场景 | 版式复杂、字段多 | 版式规整、字段少 |

## 输出契约

### 云 OCR pipeline

云 OCR 脚本继续使用其现有返回结构：`success`、`fields`、`original_data`，失败时包含实际错误信息。不得把云 OCR 返回形状与 LLM 视觉 envelope 混用。

### 备案号 LLM 视觉

备案号视觉提取只允许使用 `references/llm-vision-record.md` 定义的精简输入：

```json
{
  "schema_version": "2.0",
  "strategy_id": "llm_vision_record",
  "source": {"image_count": 1, "has_partner_image": false},
  "context": {
    "id": 12345,
    "org_no": "100027",
    "org_name": "当前机构",
    "selected_old_no": "当前备案号",
    "quality_warning_confirmed": false,
    "confirmed_charity_org_name": ""
  },
  "fields": {},
  "quality": {"confidence": "high", "uncertain_fields": [], "warnings": []}
}
```

⛔ 禁止输出旧版扁平结构或生成 `raw_ocr_text`/`evidence`；禁止在 Agent 完成质量和编号提示前调用单步脚本。

## 约束原则

1. **不静默降级**：三步 pipeline 任一步失败时**不自动切换** LLM 视觉，返回错误由调用方（alert-cert-forms）决定策略
2. **多张图独立处理**：一次调用可传多张图，**每张独立走三步 pipeline**（不合并 taskKey）
3. **不生成 OCR 原文**：备案号快速路径只输出业务字段和机器质量代码，不生成 `raw_ocr_text` 或 `evidence`
4. **不修改字段值**：视觉阶段只提取；格式归一化由单步脚本完成
5. **身份证必走私有桶**：private=1，且访问链接用 COS 原始域名（不能用CDN）

## 特殊情况处理

| 情况 | 处理方式 |
|------|---------|
| COS 临时凭证接口超时 | success: false, failed_at_step: upload, 由调用方提示用户重试 |
| COS 上传超时（运行 upload_cos.py） | success: false, failed_at_step: upload, 可重试 1 次 |
| 提交 OCR 检测失败 | success: false, failed_at_step: submit |
| 轮询超过 30 秒无结果 | success: false, failed_at_step: poll, 需从 Step 1 重来 |
| LLM 视觉识别不出字段 | fields 中缺失的字段为 null, confidence: low |
| 图片格式不支持 | success: false, 上传前拦截 |
| 图片模糊/过暗 | 云 OCR 可能返回低置信度或报错，LLM 视觉可能置信度低 |

## 铁律

- ❌ 身份证走公有桶（必须 private=1）
- ❌ 公有桶用 COS 原始域名（应替换为 CDN 域名，规则见 `references/scripts/upload_cos.py`）
- ❌ 三步 pipeline 中间断路（上传成功但不提交 / 提交成功但不轮询）
- ❌ 轮询间隔 < 5 秒（浪费后端资源）
- ❌ 轮询超过 30 秒不放弃（无限等待）
- ❌ 30 秒超时后**不重新上传**（后端可能已丢弃任务上下文，用旧 taskKey 无意义）
- ❌ 云OCR 失败静默降级到 LLM 视觉（用户不知精度已下降）
- ❌ 备案号走云 OCR pipeline（应用 LLM 视觉，字段少且版式规整）

## 参考文件

- `references/scripts/upload_cos.py` — Step 1：取 COS 临时凭证 + 上传 + 链接拼接（含域名映射规则）
- `references/scripts/remote_ocr.py` — Step 2 + Step 3：提交 OCR 检测 + 轮询查询结果（全链路一体）
- `references/llm-vision-record.md` — 备案号 LLM prompt（不走pipeline）
- `references/cert-type-detection.md` — 证件类型检测
