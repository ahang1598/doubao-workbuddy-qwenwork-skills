# content/+video-report-get

本文命令统一从已核验的 Inspect 根目录下的 `video/` 执行；文档位于 `video/references/` 不代表需要进入该目录。`../scripts/report-link.mjs` 相对 `video/` 解析。

先遵循 [产品边界](../../references/product-boundary.md)；内部参数不可向用户展示。

<!-- SHORTCUT_PARAMETERS_START -->
## 参数

运行 `node ../scripts/api.mjs --operation 'content/+video-report-get' --schema` 读取当前内置运行时的参数、枚举、风险和输入输出合同；不要从 Skill 复制字段表。
<!-- SHORTCUT_PARAMETERS_END -->

## When

- 获取单个视频质检任务的报告。

## Avoid when

- 任务尚未完成或报告仍在生成时，不得把空结果当作通过。

## Prerequisites

- 准备唯一 `ProjectName` 和 `TaskId`，必要时先查询任务状态。

## 豆包工作交付（优先执行）

按 [豆包工作交付](../../references/doubao-delivery.md) 执行。先核对任务状态，再用 `content/+video-report-get` 读取服务端报告；不生成本地质检 HTML，不调用本地报告渲染或服务脚本。报告就绪后运行 `node ../scripts/report-link.mjs`，显式传入 `kind:"video"`、原任务 environment、项目和任务编号，核验远端控制台报告可读后，在 Chat 中交付报告链接、中文结论、违规内容与证据。远端页面不可用时保留链接和已有摘要，说明实际阻塞，不生成本地 HTML 或附件兜底。质检交付不依赖 JSON 上传。

不运行回环服务，不把本地 URL 或文件路径交给用户。

## Tips

- 按 [服务端报告读取约束](../../references/doubao-delivery.md#服务端报告读取约束) 在内存中捕获并过滤内置运行时输出，先核验请求成功和任务终态，再判断报告是否就绪。认证、网络、解析或响应结构异常不当作报告生成中。完整交付流程的报告等待最多 10 分钟、每 30 秒查询一次；到期保留原任务与已有结果供续办，单次查询不自动循环。

- 区分接口事实、报告命中和推断；不把命中片段描述成完整视频内容。
- 违规内容的时间严格遵循 [风险证据时间格式](../../references/chat-delivery.md#风险证据时间格式直播与视频共用)，用 `HH:mm:ss ~ HH:mm:ss` 展示，不直接输出 `62–93s`；缺少结束时间只展示已知时点。
- 最终答案先给自动质检结论和任务信息，再单列“违规内容”。逐条列出规则/类别、时间点或时间段、命中文本/画面证据和处置结论；接口未返回的字段写“未返回”。
- 只有报告明确返回空违规集合时才写“未识别到违规内容”；报告尚未生成、字段缺失或解析失败均不得写成通过。
- 报告查询只读取服务端数据，不生成文件、不启动服务。命令参数以 `content/+video-report-get` 的精确 Schema 为准，显式使用原任务 environment、profile、项目和任务编号；只提取结论、规则命中与必要证据，不在对话或日志中输出原始响应、完整转写或媒体地址。
- 远端控制台展示任务摘要、播放器、语音识别、风险时间轴、违规证据与规则结果，以实际可用内容为准；媒体不可用时如实说明。
- 任务仍在检测、检测失败或报告未就绪时按状态说明，不猜测替代地址，也不把未生成解释为通过。

## Examples

```text
# 先按精确 Schema 查询任务与服务端报告，确认报告就绪后生成远端链接
printf '%s\n' '{"kind":"video","environment":"online","project_name":"<project>","task_id":<id>}' | node ../scripts/report-link.mjs
```
