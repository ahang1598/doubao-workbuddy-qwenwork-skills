# 刑事文书交付校验摘要模板

- 文种：{doc_type}
- 输出场景：{output_scene}
- 模式：{submission_mode}
- 状态：{status}
- 是否可交付：{deliverable}
- 是否允许一次定点修正：{retry_allowed}
- 是否已熔断：{fused}

## 阻断问题

{blocking_findings}

## 警告

{warnings}

## 需要用户补充

{missing_fields}

## 下一步

- PASS：交付。
- PASS_WITH_WARNINGS：交付并提示警告，不重试。
- NEEDS_INPUT：保留草稿并集中询问，不自动重试。
- BLOCKED 且 retry_allowed=true：仅修正定位问题一次。
- BLOCKED 且 fused=true：停止循环并保留问题清单。

