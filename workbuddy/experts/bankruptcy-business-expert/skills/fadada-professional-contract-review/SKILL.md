---
name: 法大大专业合同审查(iterms)
name_en: fadada-professional-contract-review-iterms
description: |
  当用户明确要求审查、审核或审阅某份合同，或者要求检查合同风险、风控问题、合规问题时，
  使用本技能执行法大大专业合同审查；无需用户提到“法大大”或“平台”。明确要求“用法大大审查”时也触发。
  仅要求看看、阅读、总结、提取条款或解释合同内容时不触发；讨论审查方法、制作审查规则或评测审查效果时也不触发。
  本技能负责附件识别与上传、审查清单匹配或生成、发起审查、等待进度及展示风险；
  仅在用户明确要求时生成并下载审查意见书。
jurisdiction: 中国大陆
version: "1.9"
last_updated: "2026-08-17"
tags: ["合同审查", "流程编排", "MCP 工具", "中国大陆"]
---

# 法大大专业合同审查(iterms) (Fadada Professional Contract Review iterms)

## Skill 概述

本 Skill 是**平台审查流程的执行器**：把「附件预读与角色识别 → 文件直传 → 合同登记 → 清单匹配/生成 → 发起审查 → 展示风险」串成一站式流程。文件上传的控制面和合同登记走 BFF MCP 工具，文件数据通过 60 秒有效的 PUT 预签名 URL 直接上传；上传脚本不读取登录 token。审查意见书是可选的最后一步，**只有用户明确要求导出或生成意见书时才触发**，完成后由 PC 下载为本地 Word 附件。

## 输入与执行前确认

| 输入 | 必填 | 说明 |
|------|------|------|
| 合同文件 | 条件必填 | 会话中用户指定或模型预读识别的待审合同；已有 contractId 时可不再上传 |
| 自定义清单文件 | 可选 | 用户提供的审查清单；支持 docx/xlsx/xls |
| contractId | 条件必填 | 已有合同标识，或由合同文件上传并登记后取得 |
| contractFileCode | 条件必填 | `prepareReviewFileUpload` 返回的合同文件编码 |
| checklistFileCode | 生成清单时必填 | `prepareReviewFileUpload` 返回的清单文件编码，用于生成系统清单 |
| standpoint | ✅ 必填 | 审查立场（如：甲方、乙方、买方、卖方、出租方、承租方等） |
| strictness | 可选 | 审查尺度：1-强势 / 2-均势 / 3-弱势，不传使用系统默认 |
| taskId | 导出时必填 | `startReview` 返回的审查记录 ID；沿用当前会话已有值，不向用户重复询问 |

执行前确认用户明确要求合同审查；如果只是阅读、总结、提取或解释合同内容，则退出本流程，按用户的实际请求处理。

**文件路径来源**：对话中的会话附件或用户明确给出的路径；没有可用文件时向用户询问，**不要自行搜索文件系统**。

## 上传前附件预读与角色识别

当会话中存在多份候选附件时，上传前必须使用 `Read` 的 `attachment_ids` **一次读取全部候选附件**。运行时会自动提取 PDF、DOC、DOCX、XLS、XLSX 文本。

- 合同特征：当事人、标的、权利义务、价款/付款、违约、争议解决、签署等连续条款。
- 清单特征：审查项、风险等级、审查要求、判断标准、修改建议等规则或表格结构。
- 文件名和扩展名仅作辅助；DOCX 既可能是合同，也可能是清单。
- 用户明确指定的角色优先于模型判断。
- 恰好识别出一份合同和一份清单且置信度足够时，先向用户展示映射后继续。
- 多份同类文件、无法提取内容或判断不明确时，必须询问用户；禁止默认选择第一个附件。

识别完成后分别保存 `contractAttachmentId` 与 `checklistAttachmentId`。会话附件上传时把 ID 传给脚本，脚本从 `RICHEEAI_ATTACHMENTS` 精确解析运行时安全路径；不得由模型搜索文件系统。只有用户明确提供非附件本地路径时才使用 `--file-path`。

## 流程编排

与交互时序一致，将预签名上传脚本、MCP 原子工具和订阅工具按状态机编排。**每步的输出即时向用户展示，不静默执行**，但不得展示预签名 URL：

| 步骤（用户侧名称） | 工具 / 动作 | 前置条件 | 展示给用户 |
|------|-------------|----------|------------|
| 1 | 使用 `Read(attachment_ids=[...])` 预读候选附件，识别并展示合同/清单映射 | 多份候选附件 | 合同附件、可选审查清单附件；不明确时询问用户 |
| 2. 提取合同 | 先用 `upload-review-file.mjs --inspect` 取得文件名；调用 `prepareReviewFileUpload(fileName, CONTRACT)`；再用同一脚本和返回的 `uploadUrl` 执行 PUT；成功后调用 `createContractFromUploadedFile(contractFileCode)` | 尚无 contractId | 合同编码、合同文件编码、参与方 |
| 3A | 有自定义清单时，先用 `upload-review-file.mjs --inspect` 取得文件名；调用 `prepareReviewFileUpload(fileName, CHECKLIST)`；再用同一脚本和返回的 `uploadUrl` 执行 PUT | 已明确清单文件 | 清单文件编码 |
| 4A | 调用 `generateReviewList(checklistFileCode, reviewListName, standpoint, reviewPoints?)` | 步骤 2、3A 成功 | 审查清单记录编码 |
| 5A | 调用 `getReviewListById(ruleListId)` | 步骤 4A 成功 | 审查清单编码；无需等待清单生成完成 |
| 3B | 没有自定义清单时，调用 `matchReviewList(contractId, standpoint)` | 步骤 2 成功 | 候选系统清单，由用户确认审查清单 |
| 6 | 调用 `startReview(contractId, ruleListCode, standpoint, strictness)` | 5A 或 3B 已取得编码 | 审查任务编码；后端会等待 AI 清单生成完成 |
| 7 | 客户端提供 `subscribeTaskProgress` 时订阅审查进度；未提供时有限轮询 `getReviewResult(taskId)` | taskId | 告知用户审查已启动；订阅模式完成后主动汇报，轮询模式查询到终态后汇报 |
| 8 | 用户中途询问时，单次调用 `getReviewResult(taskId)` | 用户询问 | 当前阶段、完成进度、审查项进度 |
| 9 | 意见书导出分支：`downloadReviewReport(taskId)` → 必要时订阅生成进度 → 使用返回的预签名 URL 执行 `download-review-opinion.mjs` | **用户明确说“导出/生成意见书”** | 下载后的本地 `.docx` Markdown 链接与文件附件 |

### 预签名上传命令

会话附件使用精确 attachment ID，本地文件使用用户明确给出的路径。申请 URL 前先读取本地元数据：

```bash
node scripts/upload-review-file.mjs --attachment-id <attachmentId> --inspect
node scripts/upload-review-file.mjs --file-path <filePath> --inspect
```

取得 `fileName` 后调用 `prepareReviewFileUpload`。文件大小由服务端在上传完成时读取对象存储元数据并校验。返回的 `uploadUrl` 仅传给脚本，不向用户展示：

```bash
node scripts/upload-review-file.mjs --attachment-id <attachmentId> --upload-url '<uploadUrl>'
node scripts/upload-review-file.mjs --file-path <filePath> --upload-url '<uploadUrl>'
```

脚本返回 `code=PRESIGNED_URL_EXPIRED` 时，重新调用一次 `prepareReviewFileUpload` 并重试 PUT；最多重新申请一次。其他错误不自动重试。合同支持 pdf/doc/docx，自定义清单支持 docx/xls/xlsx。

### 进度等待兼容策略（步骤 7）

`subscribeTaskProgress` 是客户端可选能力，不是合同审查 MCP 的前置条件。先检查当前客户端暴露的工具：存在时使用订阅模式；不存在、未注册或调用返回工具不可用时，直接使用轮询模式。不得因为缺少该工具而提示“审查能力未开通”。

**订阅模式**：

- `taskId`：审查任务标识；`endpoint`：进度推送端点路径（审查为 `/claw/contract/progress-sse?recordId=`，含查询参数名）；`prompt`：完成时注入本 Agent 的汇报指令（需说明任务与汇报要求，如：审查完成请调用 getReviewResult 查询并汇报风险概况）；`title`：任务标题（审查用「合同审查」，显示于全局进度徽章）

- 审查进行中应用层静默接收进度事件，Agent 不做任何轮询调用；**应用在会话底部工具栏显示全局进度徽章**（任务标题 + 百分比 + 进度条，点击展开阶段与审查项进度详情），不在对话流中注入任何消息，用户可在工具栏看到过程，无需 Agent 处理
- **审查完成（或失败）时应用自动触发本 Agent 一次回合**（以系统消息形式呈现，不占用用户发言位），LLM 按 prompt 调用 `getReviewResult` 查询结果并**主动向用户汇报**（风险概况 + 关键风险条款 / 失败原因），无需用户发消息
- 用户中途问「审查好了吗 / 进度如何」时，单次调用 `getReviewResult(taskId)` 返回当前状态即可，不要循环调用

**轮询模式**：

- 使用同一 `taskId` 调用 `getReviewResult`，间隔 30 秒，最多 20 次（约 10 分钟）；不得并发轮询或无上限重试。
- 查询到 `COMPLETED` 时立即停止并汇报风险结果；查询到 `FAILED` 时立即停止并汇报失败原因。
- 轮询期间不逐次播报；达到上限仍未结束时停止等待，提示「任务仍在处理，可稍后重查」，并保留 `taskId` 供用户后续查询。

### 审查意见书导出（步骤 9，仅显式触发）

不得因为审查完成而自动生成意见书。只有用户明确表达“生成审查意见书”“导出意见书”“把意见书下载下来”等意图时，才进入本分支；“查看审查结果”“有哪些风险”等请求不属于导出意图。

1. 复用当前会话的 `taskId`，单次调用 `downloadReviewReport(taskId)`。不要询问或传递 `contractType`。
2. 返回 `COMPLETED` 时，不向用户展示或记录完整 `fileUrl`，将 MCP 返回的 `fileUrl` 和 `fileName` 原样传给脚本：

   ```bash
   node scripts/download-review-opinion.mjs --url '<fileUrl>' --file-name '<fileName>'
   ```

3. 脚本返回 `code=PRESIGNED_URL_EXPIRED` 时，用同一 `taskId` 重新调用一次 `downloadReviewReport` 获取新 URL，并重试下载一次；第二次失败后停止。其他下载错误不自动重试。
4. 脚本成功返回 `{ success, fileName, localPath, size }` 后，最终回复必须包含本地文件 Markdown 链接：`[fileName](localPath)`。仅说明路径而不生成链接，PC 不会把文件展示为附件。
5. 返回 `GENERATING` 时，按客户端能力等待：
   - 提供 `subscribeTaskProgress`：调用 `subscribeTaskProgress(taskId, endpoint=/claw/contract/opinion-export-progress-sse?recordId=, title=审查意见书, prompt=意见书完成处理指令)`。完成处理指令必须要求：单次调用 `downloadReviewReport` 确认状态；`COMPLETED` 后执行上述下载脚本；最后输出本地 Markdown 文件链接；失败时汇报原因。
   - 未提供、未注册或调用返回工具不可用：每隔 30 秒调用一次 `downloadReviewReport(taskId)`，最多 20 次；`COMPLETED` 后立即下载，`FAILED` / `RETRYABLE` 时立即停止，达到上限仍为 `GENERATING` 时提示稍后重查。
6. 返回 `FAILED` 或 `RETRYABLE` 时展示 `errorMessage`，询问用户是否重试；不得自行无限重试。
7. 用户在审查仍进行中时已经明确要求导出：订阅模式重新订阅当前审查进度，并把完成指令改为“审查完成后进入本节的意见书导出分支”；轮询模式则继续有限轮询审查结果，完成后直接进入导出分支。这次明确意图已经有效，不要求用户完成后再说一次。

下载脚本只接受本次 `downloadReviewReport` 返回的 HTTPS 预签名 URL 和文件名，不读取 `RICHEEAI_API_BASE` 或 `RICHEEAI_TOKEN`，也不发送 `richee-token`。文件下载到当前会话工作目录的 `.cowork-temp/attachments/generated/contract-review/`；脚本限制 50MB、校验 DOCX，并使用 `.part` 临时文件后原子落盘。

## 结果展示约定

### 风险明细（COMPLETED）

按风险等级分组展示（`risks[].ruleItemList[]` 中 `ruleLevel`：1-高危 / 2-中危 / 3-低危）：

- 每条风险包含：条款原文（`originalTextList`）、风险说明（`ruleRisks`）、修改建议（`ruleSuggestionList`）、法律依据（`lawAccordings`）
- 无风险时明示「未发现高风险条款」
- 展示风险等级标记（如 🔴高危 / 🟠中危 / 🟡低危），便于用户快速定位

### 进度（REVIEWING）

进度由应用层全局展示（会话底部工具栏徽章：任务标题 + 百分比 + 进度条，点击展开阶段与审查项进度详情），不写入对话流。数据字段：`stage`（阶段文案，如「正在阅读合同内容」「正在分析合同关键条款」「正在逐项审查合同条款」）；「正在逐项审查合同条款」阶段附带 `reviewItemProgress`（如「已完成 12/23 项审查」）与 `currentReviewItem`（最近完成项名）。stage 文案由 contract-service 按进度阶段权重映射（粗粒度用户向表述，不暴露内部实现步骤）。

### 失败（FAILED）

展示 `failReason` 与建议动作：重试、更换审查清单、联系管理员。

## 异常处理

| 场景 | 处理 |
|------|------|
| 附件角色不明确 | 预读后停止并询问用户，禁止默认选择第一个附件 |
| 未上传文件 | 合同和自定义清单统一使用 `upload-review-file.mjs`；会话附件必须传精确 attachment ID，本地文件必须传明确路径；脚本失败后不继续 |
| 上传预签名 URL 失效 | 仅当上传脚本返回 `PRESIGNED_URL_EXPIRED` 时重新调用 `prepareReviewFileUpload` 并重试一次；再次失败后停止 |
| 下载预签名 URL 失效 | 仅当下载脚本返回 `PRESIGNED_URL_EXPIRED` 时重新调用 `downloadReviewReport` 并重试一次；再次失败后停止 |
| 没有文件路径 | 直接向用户询问文件，禁止 Glob / find / 文件名搜索 |
| 合同上传或类型识别失败 | 停止流程并按脚本错误提示处理，不生成清单 |
| 清单匹配为空 | 询问用户是否提供自定义清单或改选系统预置清单 |
| 进度订阅工具未提供 / 未注册 | 不视为审查能力缺失；按“进度等待兼容策略”降级为有限轮询 |
| 核心 MCP 工具未启用 | `startReview`、`getReviewResult`、`downloadReviewReport` 等当前步骤必需的 MCP 工具不存在 / 未注册时，提示「审查能力未开通，请联系管理员」 |
| 服务不可用 / 超时 | 给出降级文案与重试指引，保持对话可用 |
| 参数缺失 | 缺 standpoint 时先向用户询问立场，不猜测默认值 |
| 未明确要求导出意见书 | 不调用 `downloadReviewReport`，审查结果展示后结束 |
| 意见书生成中 | 有订阅工具时订阅 `/claw/contract/opinion-export-progress-sse?recordId=`；否则按 30 秒间隔、最多 20 次有限轮询 |
| 意见书下载失败 | 展示脚本 JSON 中的 `message`；残留 `.part` 文件由脚本清理 |

## 能力边界

- ✅ 可以：基于已上传合同发起审查、展示进度与风险明细；在用户明确要求时生成并下载审查意见书附件
- ❌ 不做：匿名申请上传地址、把预签名 URL 展示给用户、AI 生成之外的审查清单手工创建/编辑/删除、审查中间数据（合同切分、条款关联）的获取——中间数据为进阶能力，接口开放后另行演进

## 输出格式

每个流程步骤完成后，使用 Markdown 表格展示结果，不直接输出工具返回的原始 JSON。只保留用户理解当前进展所需的关键字段：

- 每个已执行步骤对应一行；连续完成多个步骤时可合并到同一张表，按执行顺序追加。
- 固定使用「步骤、状态、关键结果、说明」四列。
- 成功、处理中、失败分别使用 `成功`、`处理中`、`失败`，不要只展示内部状态码。
- 内部标识可放入「关键结果」，但必须转换为面向用户的业务名称：`contractId` 显示为“合同编码”，`taskId` 显示为“审查任务编码”，`ruleListCode` 显示为“审查清单编码”。
- 任何面向用户的内容都不得出现 `contractId`、`taskId`、`ruleListCode` 等内部字段名或其他 camelCase 参数名；其他编码也使用“合同文件编码”“清单文件编码”“审查清单记录编码”等中文业务名称。
- 字段值包含换行或竖线时，先转换为适合 Markdown 单元格展示的文本。

例如，发起审查后输出：

| 步骤 | 状态 | 关键结果 | 说明 |
|------|------|----------|------|
| 发起审查 | 处理中 | 合同：采购合同.pdf；审查任务编码：123456 | 审查已启动，完成后将主动汇报结果。 |

最终结果仍按「结果展示约定」组织，风险明细按等级分组展示。意见书下载成功时，将本地 Markdown 附件链接放入表格的「关键结果」列，例如：

| 步骤 | 状态 | 关键结果 | 说明 |
|------|------|----------|------|
| 生成审查意见书 | 成功 | [采购合同-审查意见书.docx](/absolute/session/path/.cowork-temp/attachments/generated/contract-review/采购合同-审查意见书.docx) | 已下载为本地 Word 附件。 |
