# Example 001: 债权审查成果校验

## 输入

```yaml
deliverables:
  - "债权审查结论表.docx (claim-review O1)"
  - "claim_review_summary.json (claim-review O3)"
report_type: "claim_review"
```

## 场景

对claim-review产出的债权审查结论进行V1-V8八维校验。假设发现：一笔职工债权金额与claim_review_summary.json不一致（docx中15万，json中18万）。

## 预期输出

O1 成果校验报告（docx）：
- 可交付判断：needs_modification
- 阻断问题：职工债权金额矛盾（docx:150,000 vs json:180,000），须退回claim-review Phase 5修正
- V1意图达成：部分达成
- V4金额核验：发现1处不一致
- V6法条引用：通过（法条号正确）
- V8程序合规：通过（法定章节完整）

O2 结构化校验记录（json）：deliverable_status=needs_modification
