# 贡献与合稿契约

## 目录

- [ContributionPacket](#contributionpacket)
- [MergeResult](#mergeresult)
- [来源、主张与状态约束](#来源主张与状态约束)

## ContributionPacket

结构化提交从 [贡献模板](../assets/contributions.template.json) 开始；成员也可填写
[Markdown 提交模板](../assets/member-submission.template.md)，再由模型归一化为 JSON。

```json
{
  "contributions": [
    {
      "member_id": "M01",
      "task_id": "T01",
      "status": "submitted",
      "claims": [
        {
          "claim_id": "C01",
          "statement": "可核验的观点",
          "claim_type": "fact",
          "classification_source": "supplied",
          "evidence_ids": ["E01"]
        }
      ],
      "evidence": [
        {
          "evidence_id": "E01",
          "source_member_id": "M01",
          "source": "用户提供的文件或链接",
          "locator": "页码、章节或 URL",
          "verification": "supplied"
        }
      ],
      "draft_content": "成员原始内容",
      "open_questions": []
    }
  ]
}
```

`claim_type` 允许 `fact`、`interpretation`、`recommendation`、`assumption`、`question`；旧提交缺失时使用
`unclassified` 并在合并时请求确认。`classification_source` 使用 `supplied` 或 `inferred`。

`verification` 允许 `supplied`、`verified`、`unresolved`、`conflict`。`evidence_id` 在整个合并包内全局唯一。
跨成员复用证据时保留 `source_member_id` 和原始定位；没有来源的事实或解释主张进入缺口登记表。

保存 JSON 后运行：

```bash
python3 scripts/audit_contributions.py path/to/contributions.json
```

## MergeResult

从 [合稿结果模板](../assets/merge-result.template.json) 复制结构。

```json
{
  "artifact_id": "MERGE-001",
  "revision": 1,
  "status": "team_review",
  "content_blocks": [
    {
      "block_id": "B01",
      "heading": "背景",
      "content": "整合后的文字",
      "source_claim_ids": ["C01", "C02"]
    }
  ],
  "evidence_map": [
    {"evidence_id": "E01", "source_member_id": "M01", "shared_by_claim_ids": ["C01", "C07"]}
  ],
  "duplicate_register": [],
  "tension_register": [],
  "conflict_register": [],
  "gap_register": [],
  "contribution_map": {}
}
```

`duplicate_register` 只收录完全重复或同义改写；补充细节与同主题的不同分析不算重复。
`tension_register` 收录可以同时成立但评价方向不同的主张；`conflict_register` 只收录无法同时成立的主张。

可直接运行同一脚本检查纯 `MergeResult` 的结构：

```bash
python3 scripts/audit_contributions.py path/to/merge-result.json
```

纯合稿结果不含原始 `contributions` 时，脚本只能证明合稿结构成立，不能交叉核对 `source_claim_ids`。
如需深度审计，把非空 `contributions` 一并保存在审计副本中再运行脚本。

## 来源、主张与状态约束

每份提交必须保留非空 `member_id`、`task_id` 和 `draft_content` 原文；每条 claim 必须有非空 `claim_id`、`statement`、`claim_type`、`classification_source` 和 `evidence_ids`。`fact`、`interpretation` 和 `unclassified` 必须至少引用一条 evidence；`recommendation` 没有 evidence 时必须提供 `rationale` 或 `related_claim_ids`。每条 evidence 必须有 `evidence_id`、`source_member_id`、`source`、`locator` 和合法 `verification`。

`MergeResult` 根级 `status` 必须参与审计：当 status 为 `final_ready` 时，`unresolved_submissions`、`gap_register`、`conflict_register`、未分类 claim 或 unresolved/conflict evidence 任一非空，都必须返回错误；`draft`、`team_review` 可以保留这些登记项。
