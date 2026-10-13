# 成员内容整合规则

## Intake

要求每份提交带有 `member_id`、`task_id`、原始内容和来源状态。缺少归属时先放入
`unresolved_submissions`，不要按文风或主题猜测作者。

归一化贡献集合后运行 [`audit_contributions.py`](../scripts/audit_contributions.py)。退出码为 1 时先修正
成员或任务归属、重复 ID 和失效证据引用；只有警告时可以继续，但必须保留相应人工复核项。

先收集所有成员包的 evidence，建立全局 `evidence_id -> source_member_id/source/locator` 索引，再处理
claims。跨成员引用是允许的，但在 `evidence_map` 中标记 `shared_from`，并在输出中保留原始证据所有者；
只有不存在的 evidence ID 才是错误。

## Synthesis loop

1. 先完整阅读全部提交，建立主题和评分标准索引；
2. 按主张/主题聚类，合并同义表达并删除重复段落；对完全相同或高度相似的主张保留一个 canonical
   claim，并在 `duplicate_register` 中列出所有被合并的 claim ID 和成员。
3. 统一术语、日期、单位、口径和语气，保留原始证据定位和共享证据归属；
4. 分离事实、解释、建议和假设。事实和解释必须有证据；建议可以没有直接证据，但必须有 `rationale`
   或关联问题/主张；假设和问题只能进入待确认区。
5. 将冲突放入 `conflict_register`，记录两方说法、来源、影响和需要谁决定；
6. 将缺失评分项、没有证据的事实/解释、缺少来源的数字、无 rationale 的建议和未完成任务放入
   `gap_register`；
7. 输出合稿，同时保留主张到证据、原始证据所有者和成员的映射。

## Duplicate and relationship classification

| 关系 | 处理 |
| --- | --- |
| `exact_duplicate` | 合并为一个 canonical claim，联合证据和贡献者 |
| `paraphrase` | 合并表达，保留双方证据与贡献者 |
| `supporting_detail` | 不删除；放到主张下作为细节或证据说明 |
| `related_topic` | 不计入重复；按结构分别保留 |

不得仅因出现相同主题词就判定重复。例如“治理主体包括三方”是背景事实，“三方权责边界不清”是分析，
二者属于 `supporting_detail`/`related_topic`，不能删成一句。

## Conflict classification

| 类型 | 处理 |
| --- | --- |
| `direct_contradiction` | 进入 `conflict_register`，阻止相关结论进入 final_ready |
| `scope_difference` | 明确对象/指标范围后并列或重写 |
| `time_difference` | 标出年份或阶段，不当作直接冲突 |
| `source_quality_difference` | 保留主张，突出来源等级和待核验项 |
| `complementary_tension` | 进入 `tension_register`，说明为何可以同时成立 |

“社会组织参与不足”和“总体满意度较高”可以同时成立，通常属于 `complementary_tension` 或
`source_quality_difference`；只有两条主张对同一指标、对象和时间给出互不相容结论时，才算直接冲突。

## Draft coverage

成员正文中的事实不因“来自成员”而自动可追溯。合并前检查：

- 每个百分比、数量、年份、金额和排名是否出现在 claim statement 中；
- 每个事实性 claim 是否有 evidence ID；
- 合并后的每个内容块是否列出 `source_claim_ids`。

无法对应的数字或事实进入 `gap_register`，不能直接写入 final_ready 合稿。

不得因为要求“统一口径”而删除不利结果、抹平矛盾或把未核验材料写成事实。不得编造调查样本、访谈、
 实验结果、论文引用、网页链接或成员完成状态。

## Claim classification

| 类型 | 规则 |
| --- | --- |
| `fact` | 有来源和定位；没有则标记 `unresolved` 并进入缺口 |
| `interpretation` | 有证据支撑的分析；区分事实和推论 |
| `recommendation` | 可无直接证据，但必须说明 rationale、适用条件和关联问题 |
| `assumption` | 为继续起草而设的前提；不得写成已证实事实 |
| `question` | 待成员或小组回答的问题；不进入正式结论 |

旧数据缺少 `claim_type` 时，不静默判断。将其标为 `unclassified`，在 `team_review` 中请求确认。

## Incremental merge

用户补交或修改成员内容时：

1. 读取上一版 `MergeResult` 和新提交；
2. 保留未受影响的 block/claim/evidence ID；
3. 只重算受影响的重复、张力、冲突、缺口和内容块；
4. 增加 revision 和 change log；
5. 重新执行贡献审计，不以旧版通过结果替代当前检查。

合稿后对 `MergeResult` 再运行同一脚本。纯结果只做结构检查；要交叉核对内容块的主张引用，需在审计副本
中同时保留原始 `contributions`。

## Status

- `draft`：有占位符、假设或未核验来源；
- `team_review`：结构完整但需要成员确认、补缺或解决冲突；
- `final_ready`：关键字段齐全，强主张可追溯，冲突已解决或明确不影响交付，且评分标准无明显遗漏。

`final_ready` 只表示内容包完成本 Skill 的检查，不表示已经提交或教师认可。
