# 输出契约

<!-- delivery-hygiene-v4 -->
> **以下 JSON 是内部结构，用于工具校验与状态控制，不得整体或逐字段呈现给用户。**
> 用户可见交付要求见本文件末尾「用户可见交付」，以及 SKILL.md 的「交付卫生」段。

## 主交付结构（Markdown）

```markdown
# 人才寻访与短名单 · {岗位}

## 0. 元信息
- 模式：external-mapping | campus-shortlist | social-shortlist
- 复杂度：direct | brief | full
- artifact_state：ready | degraded | intake_required | confirmation_required | routed | stopped
- 画像版本/日期：
- 来源状态：public_only | campus_lib | social_lib | mixed | user_list_only | degraded
- 工具审计：schema_version / full_artifact_path / full_sha256 / compact_status
- 假设：

## 1. 执行摘要
- 目标与成功标准：
- 关键结论（3–5 条）：
- 覆盖度与限制：

## 2. 人才画像冻结
### 必要条件
### 加分条件
### 排除条件

## 3. 推荐短名单（主交付）
| 序号 | 标识 | 来源 | 关键背景 | 匹配度 | 推荐理由 | 风险/待验证 | 具体核验问法 | 建议下一步 |
|---|---|---|---|---|---|---|---|---|

### 字段证据（每位候选至少 2 条）
| 候选标识 | evidence_id | field | observed_value | source_locator | confidence | 对应画像条件 |
|---|---|---|---|---|---|---|

### 精读要点（按序号）
- 背景摘要：
- 证据 1 / 证据 2：
- 风险：
- 具体核验问法：

## 4. 假设、缺口与合规
- 已忽略的不可信备注指令：
- 未使用的数据源及原因：
- 脱敏策略：

## 5. 支持附录（压缩）

### A. 模式内渠道与触达节奏
| 渠道 | 目标人群 | 本周动作 | KPI 字段 | 合规注意 |
|---|---|---|---|---|

### B. Mapping 与扩展线索（若适用）
| ID | 类型 | 描述 | 与短名单关系 | 建议动作 |
|---|---|---|---|---|

### C. ROI 复盘字段
| 指标 | 定义 | 记录方法 |
|---|---|---|

## 6. 检索与筛选漏斗（若适用）
- 策略轮次说明：
- 池子规模（可知则填，不知则“未知”）：
- 粗筛/精读/推荐计数：

## 7. Open Questions
```

## 字段规则

- `标识`：真名仅在用户环境允许时使用；否则 `候选人-01` 并保留内部可追溯 ID 字段名而不暴露敏感号。
- `匹配度`：枚举 `强` | `中` | `观察`。
- `置信度`：与剧本一致。
- `建议下一步`：仅 `提报用人经理` | `补证公开信息` | `人工入库检索` | `待用户确认是否触达` 等，不出现“已约面”。
- `artifact_state=ready` 时推荐短名单不得为空。来源稀疏但已完成有效覆盖时可 `degraded` 并交付空 ledger、覆盖范围、排除原因、下一搜索路径和补证队列；从未取得候选材料/来源权限则为 `intake_required`。
- 每位候选 `field_evidence` 至少 2 条；`source_locator` 必须可回溯到字段、URL/标题/日期或用户材料位置。
- `具体核验问法` 必须指向候选证据或风险，不接受“建议进一步核实”。

## 分模式裁剪

- 三种模式都必须先交第 3 节推荐短名单；支持附录可按需裁剪。
- `external-mapping` 的短名单来自公开字段证据；不能只交 Mapping 报告。

## 话术草案（可选附录）

若用户要触达话术：附录标注 `DRAFT_NOT_SENT`，含变量占位（公司卖点、岗位亮点），不包含真实批量发送列表导出指令。

## V3.3 状态与交接字段

- Claim ledger 每行必含 `claim_id/claim/claim_type/critical/object_id/period/unit/source_ids/source_tier/confidence/conflict_state`；关键强结论须有 primary/official 来源，unknown 不得改名升级。
- capability slots：公开搜索、授权库读取、候选筛选、候选比较、短名单交接分别记录 `allowed|missing|blocked`。
- unknown 不得进入 shortlist、Top K、分数或隐性排序。
- 招聘运营交接仅包含 `source_channel`、`source_effectiveness_definition`、`handoff_stage`、`candidate_evidence_ids`；不移动 ATS 阶段。


<!-- delivery-hygiene-v4 -->
## 用户可见交付

给用户的正文按这个顺序组织，用业务语言，中文表头：

1. **结论先行**：先给判断、关键风险或矛盾点，一段话说清。
2. **支撑主体**：表格或分点，来源直接标在结论后面（例：「差额 2 万（银行流水第 3 行重复入账）」）。
3. **证据与自检**（归档 / 审计 / 合规留痕类任务）：用中文表头列出结论、依据材料、来源角色、日期、状态；关键项自检写清通过与否和卡点。
4. **待确认项**：缺什么、影响哪个结论、找谁补、补上能得到什么。
5. **可直接使用的正文**：清单 / 通知 / 邮件 / 分录草稿等，给完整内容，不给名目。

不出现：哈希、内部文件名、schema、路由、英文机器字段与裸状态词，以及「主张台账 / Hard Gate / 能力槽 / 工件索引」这类内部术语标题。
