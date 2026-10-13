# 输出合同：赢单策略与商业叙事包

<!-- delivery-hygiene-v4 -->
> **以下 JSON 是内部结构，用于工具校验与状态控制，不得整体或逐字段呈现给用户。**
> 用户可见交付要求见本文件末尾「用户可见交付」，以及 SKILL.md 的「交付卫生」段。

## 状态行（首行必现）

```text
artifact_state: <ready|degraded|intake_required|confirmation_required|routed|stopped>
delivery_tier: <direct|brief|full>
mode: <full_win_package|competitive_battle|commercial_case|poc_alignment|execution_overlay>
permission_state: <read_only|confirmation_required|denied_side_effect>
```

## 主工件结构（模式共用）

```markdown
# 赢单策略与商业叙事包：{商机锚点}

## 元信息
- 客户/商机：
- 阶段：
- 模式：
- 金额/关单：待确认或用户值
- 证据充分度：高|中|低

## 1. 执行摘要
- 赢单判断（条件化）
- 最大风险（1-3）
- 本周单一最重要动作

## 2. 交易与 MEDDPICC 评估
| 要素 | 现状摘要 | 证据强度 | 缺口 | 下一步 |
|------|----------|----------|------|--------|

## 3. 采购委员会图谱
| 姓名/角色 | 组织角色 | 立场 | 影响力 | 信心 | 策略 |

## 4. 风险登记
| ID | 摘要 | 类型 | 严重度 | 可能性 | 缓解 | 负责人 |

## 5. 优先行动（5-7）
编号列表：行动 / 负责人 / 时间 / 预期结果 / 关联风险 / 干系人

## 6. 竞争定位与 Battle Card 要点
- 竞争格局一句话
- 分竞品：分离点 / 应对话术 / 禁忌 / 发现题
- 对比表（≤5竞品）

## 7. 商业案例与 ROI 叙事
- 客户语言痛点
- Known/Inferred/Assumed/Missing 输入表（名称/数值或待确认/来源）
- 价值逻辑链
- 确定性公式、输入、单位、期间、币种、low/base/high 与敏感性
- 不被支持的结论（明确「非鉴证」）

## 8. 提案 / RFP 叙事架构
章节大纲 + 需求-证据映射要点 + 开放问题

## 9. POC 范围与成功标准
范围 / 排除 / 成功度量 / 依赖 / 晋级与退出 / 评审闸门

## 10. 执行附件（按需）
- 会前简报要点
- 通话复盘要点与跟进邮件草稿（如有输入）

## 11. 证据缺口
| 缺口 | 影响 | 最小收集步骤 |

## 11A. Claim ledger 与工件索引
- 关键 claim、unknown、来源与冲突
- ROI full/compact JSON 路径、schema 版本和哈希关系

## 12. 局限与边界
- 降级原因（如有）
- 未提供的法律/审计意见声明
- 事实 vs 推断声明

## 13. 完整结尾
- artifact_state 复述
- 待用户确认项（外发/外写/关键待确认字段）
- 建议的下一轮输入
```

## 模式权重

- `competitive_battle`：第6章加长；7-9可压缩但不可缺标题  
- `commercial_case`：第7-8章加长  
- `poc_alignment`：第9章加长  
- `execution_overlay`：第5与第10章加长；若无基础评估则先建最小第2章  
- `full_win_package`：均衡  

## intake_required / routed / stopped 最小输出

```markdown
# 状态说明
artifact_state: ...
reason: ...
questions_or_route: ...
next: ...
```

## confirmation_required 附加块

```markdown
## 待确认外部动作
- action_type:
- payload_summary:
- idempotency_key:
- audit_preview:
- 用户需回复：确认 / 修改 / 取消
```

## 禁止出现

- 伪造的客户签字、竞品机密、「保证ROI≥x%」无假设  
- 最终法律意见、审计鉴证口吻  
- 未确认却声称「已发送/已写入」  
- 内部绝对路径、专有连接器名称  
- unknown 进入赢率、Top K、优先级或“大概率成交”隐性排名

## 工件回执

`roi_full_json|roi_compact_json|roi_final_json|claim_ledger` 必须全部真实落盘。每个 JSON 含一致的 `manifest.artifact_state`、`manifest.counts` 和 runtime 固定 `required_artifacts` 全集；独立 gate 只接受真实路径与 `expected_sha256` 回执，名称列表不能代替。


<!-- delivery-hygiene-v4 -->
## 用户可见交付

给用户的正文按这个顺序组织，用业务语言，中文表头：

1. **结论先行**：先给判断、关键风险或矛盾点，一段话说清。
2. **支撑主体**：表格或分点，来源直接标在结论后面（例：「差额 2 万（银行流水第 3 行重复入账）」）。
3. **证据与自检**（归档 / 审计 / 合规留痕类任务）：用中文表头列出结论、依据材料、来源角色、日期、状态；关键项自检写清通过与否和卡点。
4. **待确认项**：缺什么、影响哪个结论、找谁补、补上能得到什么。
5. **可直接使用的正文**：清单 / 通知 / 邮件 / 分录草稿等，给完整内容，不给名目。

不出现：哈希、内部文件名、schema、路由、英文机器字段与裸状态词，以及「主张台账 / Hard Gate / 能力槽 / 工件索引」这类内部术语标题。
