# references 与 Makefile 的对应关系

`references/` 只解释怎么补内容，不决定阶段是否通过。阶段状态只看 Makefile 和 `scripts/` 在 `.workflow/` 下生成的检查报告。

| make目标 | 手写文件 | 失败时先读 | 作用 |
|---|---|---|---|
| `make prepare` | `.workflow/meta.json`、必要时 `.workflow/source_pool.md` | `stem/SKILL.md` 或 `hss/SKILL.md`；引用任务读 `literature-search/SKILL.md` 和 `literature-review/SKILL.md` | 定学科分支、来源层级、引用体例 |
| `make write` | `.workflow/paper_draft.md` | `evidence-driven-writing/SKILL.md`、`writing-chapters/SKILL.md`、`writing-core/SKILL.md` | 把证据写成单文件正文，并清理语言和格式事故 |
| `make deliver` | 无新增手写文件 | `writing-core/SKILL.md`；HSS按需读 `hss/formatting-output.md` | 终稿读回前确认正文干净 |

HSS细分材料只在对应问题出现时读取：引用体例看`hss/citation-policy-examples.md`，章节模板看`hss/section-templates.md`，期刊版式看`hss/journal-formats.md`，综述问题定位看`hss/review-question-framing.md`，投稿前自查看`hss/submission-checklist.md`。

## 学科分支路由

| 分支 | 必读学科文件 | 说明 |
|---|---|---|
| `technical` | `stem/SKILL.md` | 工程、计算机、算法、自然科学实验等 |
| `medical` | `stem/SKILL.md` | 医学、生物、临床、护理、公共卫生、药学 |
| `law` | `hss/SKILL.md` | 法条、判例、司法解释、制度规范、比较法 |
| `hss_empirical` | `hss/SKILL.md` | 问卷、访谈、统计、案例、政策分析 |
| `hss_humanities` | `hss/SKILL.md` | 文本、史料、概念辨析、思辨论证 |
| `review` | `literature-review/SKILL.md`，再按主题读 `stem` 或 `hss` | 文献综述、研究现状、述评 |

## 边界

投稿前评审、稿件挑硬伤、研究设计评价或研究价值判断走`/doubao-academic-evaluator`。需要独立执行检索、纳排、去重、质量评价和证据综合的系统性文献调研或survey走`/doubao-literature-research`；基于用户已有或本workflow已核验来源撰写论文内文献综述、related work或review article仍由本workflow处理。
