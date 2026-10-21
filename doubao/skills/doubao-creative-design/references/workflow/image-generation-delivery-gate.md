# 图像生成直接交付门禁

**HTML 预览截图例外**：`shot.py` 为完整 HTML 作品生成的同尺寸预览截图继续按 [HTML 预览协议](html-preview.md) 上传 CDN、核验公网 HTTP(S) 链接并用 Markdown 图片展示，不创建 IMAGE Item。

图片／视频的展示出口统一遵循主 SKILL：使用宿主实际支持的 `RichMediaCard`，涵盖生成、编辑及正式渲染／导出成品；HTML 预览截图保留上文 CDN＋Markdown 例外，Workspace／HTML Item 卡片仍使用原 `present_files` 协议。此映射只统一展示，不把图像工具的自动关联、免重复写入规则扩展到视频或其他处理工具，其存储与登记仍按各自协议执行。

本门禁适用于 `image_gen`、`image_edit` 的所有成功输出，包括核心资产、KV、候选、草稿、改稿、中间素材和最终图。只要调用时已经把当前对话的有效 Workspace ID 作为工具参数传入，工具结果返回后就**通过 `RichMediaCard` 直接交付该结果**；不得为这张结果执行 `design-cli +create`、`FileBatchUpload`、下载、复制、重传或另建 IMAGE Item，也不得在直接交付前插入媒体 `+get`。工具对 Workspace 的写入由 Workspace ID 参数承担，媒体交付负责将原始结果提供给用户。整批结果完成直接交付后，允许且必须按 [画布资产语义目录工作流](canvas-asset-organization.md#3-产物完成后的强制目录整理) 读取平台已关联对象并更新 `path`；该产后 `+get` 只服务目录归档，不是媒体写入、质量门禁或二次交付。

若当前环境或工具调用不存在可传的 Workspace ID，则仍通过 `RichMediaCard` 直接交付媒体结果；是否需要创建 Workspace 由主 Skill 的环境路由在调用前决定，不得在结果返回后补做媒体 Item。Mobile 环境禁止 Workspace／Canvas CLI 操作。

## 1. 调用前

1. 从当前对话解析唯一、有效且指向当前目标的 Workspace ID；存在时绑定为 `active_workspace_id`，并在每次 `image_gen`／`image_edit` 调用中显式透传。
2. 默认 Canvas 环境中如果没有 Workspace ID，按主 Skill 创建 Workspace，并先由主 Agent 调用 `present_files(<workspace_id>)` 交付新建画布卡片；成功后才能调用图像工具。
3. 出现多个冲突 ID、工具参数名无法由当前工具契约确认、或传入后校验失败时，停止调用并返回实际错误；不得省略 ID 降级重试。
4. Mobile 若对话已有有效 Workspace ID，只把它作为图像工具上下文透传，不查询、创建或写入 Workspace；没有 ID 时直接按 Mobile 流程调用和交付。

## 2. 每个结果的直接交付时序

```text
image_gen／image_edit（已按条件传入 Workspace ID）
→ 工具成功返回 result[i]
→ 主 Agent 使用 RichMediaCard 立即向用户交付当前结果 result[i]
→ 记录 delivery_status
→ 才可检查、选图、衍生或进入依赖步骤
```

- 每个结果分别使用 `RichMediaCard` 交付；一次工具调用返回多个结果时，按稳定返回顺序逐项交付。
- 使用工具返回的真实产物及其可核验资源，按宿主 `RichMediaCard` 契约完成展示，不为交付下载重传。卡片所需资源字段可使用真实结果句柄或原始资源地址；普通短链文本、缩略图、Markdown 图片或文本路径不替代媒体卡片交付。
- 不允许为 `image_gen`／`image_edit` 结果额外执行媒体 CLI 写入，也不允许在直接交付前回读。全部结果直交完成后，按目录工作流使用 `+tree`／`+ls` 定位真实 ID、`+get` 读取本轮对象并仅以 `+update`／`+update-batch` 写入稳定 path；素材清单或 Brief 仍记录 Workspace ID、工具调用标识、原始结果句柄、用途和交付状态。
- 主 Agent 亲自使用 `RichMediaCard` 完成媒体交付；Subagent／异步任务只能把未改写的真实结果句柄返回主 Agent。

## 3. 串行、并行与失败

- `serial`：当前结果通过 `RichMediaCard` 交付成功后，才启动依赖它的下一次生成、编辑、选图或组装。
- `parallel`：只并发预先锁定且互不依赖的固定批次；每个结果分别直接交付，整批交付状态汇合后再继续。并行生成 N 个同源编辑版本时仍发起 N 次独立 `image_edit`。
- `RichMediaCard` 交付失败：记录真实错误并立即停止依赖步骤；不得把工具预览或 Workspace 中可能存在的对象视为已经交付。
- 工具返回失败：不为不存在的结果创建 `RichMediaCard` 或伪造交付，按实际错误处理；不要伪造结果或重复原样请求。

## 4. 坏图与文字问题

工具成功返回的结果即使审美不佳、错字、身份漂移或预计需要返工，也先通过 `RichMediaCard` 直接交付，不得静默丢弃或先做修正版。

AI 图片内出现错字、缺字、多字、伪文字、字形异常或可读性问题时，交付后记录 `validation_status=delivered_with_text_issue`，停止自主修改并等待用户明确要求。若它是可编辑设计中承担准确文字的素材，则暂停下游 HTML 组装。用户要求修改后，新版本重新执行“传入 Workspace ID → 工具调用 → 通过 `RichMediaCard` 直接交付”流程。

## 5. 成功判据与记录

只有确认对应 `RichMediaCard` 已成功向用户展示真实结果，才记录 `delivery_status=delivered`。每个结果至少记录：

- `execution_mode`；并行时记录 `batch_id`、预期数量和稳定顺序；
- `generation_result_index` 与工具调用标识；
- 实际传入的 Workspace ID，或明确记录本次无 Workspace ID；
- 工具原始结果句柄和`RichMediaCard` 单项交付结果；
- `validation_status=passed | failed | delivered_with_text_issue`。

后续选图、确认、衍生和排版只能引用 `delivery_status=delivered` 的结果。产后目录整理取得的 Canvas Item ID 和 `+get` 结果只用于语义归档与后续恢复，不得反向成为 `image_gen`／`image_edit` 结果的准出条件或双通道交付证明。
