# Output Contracts

## Required Artifact Fields
- 流程清单
- 材料列表
- 负责部门
- 时间节点
- 咨询话术
- 风险拒绝表
- 关键事实校验表
- 对话摘要 + 完整可执行指南

## Minimum Quality Bar
- The result must match the user's context and audience.
- The result must include concrete wording, table rows, schedule, or checklist items when applicable.
- The result must not be only a framework unless the user explicitly asks for a framework.
- The result must label unknown facts and assumptions.
- Risk refusal table uses columns: `违规想法`, `不能做`, `合规替代`, `原因`.
- Key fact checks must cover department/office name, deadline, processing time, material entry, campus/college, identity category, and source freshness when these affect the outcome.
- Simple single-item requests should be compressed to a minimum actionable checklist, but still include source status and one consultation script.
- Complex multi-item requests should include a short conversational summary plus the complete guide in the same response.

## Final Review Checklist
- Trigger matched: yes/no.
- Required inputs complete or visibly marked.
- Deliverables present.
- Tone fits the audience.
- No fabricated fact.
- No unsafe or non-compliant instruction.
- User can take a next action immediately.
- Risk refusal table and key fact cross-check are present when relevant.
