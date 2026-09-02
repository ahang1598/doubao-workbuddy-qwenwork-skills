# 交付决策树（fadada 合同审查）

完成审查后**先默认交付两件套，再引导下一步**，不得交付即终止对话。
阶段：`reviewing` → `delivered_base` → `awaiting_decisions` → `clean_ready` → `completed`。

## 1. 默认交付两件套（自动执行，无需追问）

- **审查报告 docx**：`scripts/build_review_report.py <report.json> <out.docx>`（report.json 的 `report_title` 填「合同审查报告」）。
  含免责声明、执行摘要、结构参数硬检查表、风险清单表、缺失保护、建议、待核查；表格单元格垂直居中、文字顶格。
- **带批注修订版 redline docx**：`review_docx.py` operations 管线（OOXML 真修订 `<w:ins>/<w:del>` + 风险批注）。
  高/中风险默认落修订、例外才批注（见 `references/shared-core/review-methodology-core.md` §7）；报告中处置标注须与 redline 实际操作一致。
- **缺件降级**：`review_build.py` 返回 `delivered_partial` 时，红线确实生成不出来，
  交付消息**首行**必须写「缺件：带批注修订版 redline + 原因 + 用户可执行的补救」，
  阶段停在 `delivered_base` 之前不得标记完成，也不得再默默重试红线。
- 交付消息末尾附**交付清单 manifest**（文件名 / 实际落位路径，取 `review_build.py` 返回的 `outdir` 与 `artifacts[].path` / 用途 / 状态）。
- 进入 `delivered_base`。

## 2. 引导下一步（交付后必呈现一次，列出选项）

**先请用户确认审查结果（审查报告 + redline）符合预期，再按需生成下列可选产物**——其余文件不默认生成：

> 已生成审查报告与带批注修订版 redline，请确认审查结果是否符合预期。接下来您需要：
> **A.** 逐条确认风险处置（接受建议 / 保留原文并承担风险 / 自定义措辞）→ 生成清洁版 Clean；
> **B.** 追加输出（可多选）：多角色评审报告（法务/财务/业务/风险管理七视角）/ 风险清单（审查结果列表 Excel）/ 文字与计算审查 / 跨文件核验表 /（引擎完成时）审查意见书；
> **C.** 调整立场或审查范围后重审；
> **D.** 无需更多，结束。

## 3. 风险决策 → Clean（用户选 A）

- 对每条高/中风险与每处改文，要求决策：`接受建议` / `保留原文并书面承担风险` / `自定义措辞` / `待定`。
- 无条件认可（如「没问题，出 Clean」）视为接受全部建议。
- 保留原文须记书面风险承担说明，保留于决策状态文件。
- 自定义措辞 → 重生成 redline，回到确认。
- 仅当无阻塞性「待定」项，才从原文 + 生效操作 + 决策生成 Clean 清洁版，置 `completed`。低风险纯批注项不阻塞。

## 4. 追加输出（用户选 B）

按所选生成。**多角色评审报告**用 `build_review_report.py`（report.json 七视角内容，见 `local-output-playbook.md` §4），与风险清单复用同一风险 JSON，保证与 redline 决策一致。

## 5. 一致性

同一合同 + 同一规则的重复/复核审查，先按 `review_cache.py` 哈希冻结复用既有已核准结论（0 偏差）；合同变更只重审变化条款。
