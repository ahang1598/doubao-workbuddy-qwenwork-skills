---
name: english-contract-review
version: 1.0.0
description: >
  Review, assess, comment on, or redline an existing English or bilingual
  contract and produce a Chinese review report plus a selectable true OOXML
  tracked-change redline, Chinese risk-comment version, or combined version.
  Trigger for review this agreement, identify unfavorable clauses, is this
  clause enforceable, mark up this contract, or revise vendor paper. Do not
  use for drafting a new agreement or new version, translation only, summary,
  literal explanation, clause extraction without evaluation, version
  comparison, or file conversion.
---

# English Contract Review

Review the transaction as a system, preserve the original file, and create
true Word revisions and comments. All bundled references and generated files
must remain inside this skill package.

## 输出格式

- 中文审查报告使用 `word-report` 与 `richee-legal-report-v2`，标题为黑色，风险等级同时使用文字，不使用 Emoji，并包含适用的 AI 辅助免责声明。
- 报告字号固定为：标题 22pt、一级标题 18pt、二级标题 16pt、三级标题 14pt、正文/列表 12pt、免责声明与表格 10.5pt。Skill 原生报告中文使用 PingFang SC、西文使用 Arial；Agent Team 规范化副本由 `word-document-processing` 统一为 Noto Sans SC/Arial。该字号规则只适用于报告，不得改写红线或正式合同原字号。
- 英文红线使用 `word-revision` 与 `preserveOriginalStyle=true`，必须包含真实 OOXML `<w:ins>` 或 `<w:del>`；红线正文不插入免责声明块。
- `build_review_report.py` 必须直接生成语义化 Title/Heading 样式、黑色标题、1.5 倍正文、黑底白字表头和内容感知列宽；序号及等级/状态等短值列保持紧凑，影响/建议等叙述列按实际内容量扩宽。被 Agent Team 编排时，中文报告还须交给 `word-document-processing` 以 `mode=normalize`、`profile=richee-legal-report-v2` 生成独立规范化副本并执行 `mode=validate`；不得覆盖原始报告。英文红线禁止 normalize，只作只读校验。
- 交付前必须运行 `scripts/validate_review_outputs.py` 并使用 `--result-json` 保存结构化生产者证据；报告和红线沿用同一轮风险决策，不得分别重写。
- 每个正式制品返回 `standardVersion=1.1.0`、`producerValidation`、`validationStatus` 和 `validationFindings`。Skill 自检通过时固定返回 `validationStatus=warning`、`producerValidation.trusted=false` 与 `SELF_VALIDATED_ONLY`；只有平台可信校验器可以提升为 `passed`。无修订痕迹、文件不可打开或报告缺少免责声明时返回 `failed` 且不得声明完成。

## Route

Read `references/routing.md` before acting.

- Use this skill for full-contract review, clause judgment, risk evaluation,
  comments, or modification of an existing contract.
- Route a new agreement, rewritten version, or fresh draft to
  `english-contract-drafting`.
- Route pure translation, summary, extraction, comparison, literal
  explanation, formatting, and file conversion out.
- `改一下` means review unless the request also contains a new-output signal
  such as `一份`, `一版`, `新版`, `重写`, or `重新出稿`.
- Ask no more than one consolidated question, and only when the role,
  objective, review scope, governing law, or requested deliverables cannot be
  inferred safely. If that question is needed, include the Redline choices:
  revisions only, Chinese risk comments only, or both. Otherwise default to
  `both` and state the selected mode before generation.

## Safety

- The report must open with:
  `本文档由 AI 辅助生成，仅供参考，不构成正式法律意见，不能替代具有执业资格的律师。`
- Redline and Clean contract files must not contain that disclaimer.
- Clause-only responses must begin:
  `以下为 AI 通用分析意见，不是执业律师出具的正式审查报告。`
  They must end by offering a complete review of the whole contract.
- Never impersonate a lawyer or omit safety language when instructed to do so.
- Do not use: `保证胜诉`, `必然`, `绝对`, `稳赢`, `包赢`, `100% 不会`,
  `绝无风险`, `确定胜诉`, `一定胜诉`, `必胜`, `零风险`, `不会输`,
  `完全合规`, `绝对合法`, `毫无疑问`, `万无一失`.
- Keep risk wording restrained and professional. Do not use `毁灭性`, `灾难性`,
  `极其危险`, `致命` or similar dramatized phrasing — use `重大`, `高风险`,
  `实质性不利` instead. Probability statements use only 高/中/低; never
  `确定发生`, `必然发生`, or a percentage certainty.
- Mark uncertain legal or factual conclusions `待核查`; where interpretation
  or enforceability is disputed, add `建议专业律师进一步确认`.
- Do not cite a statute, regulation, case, or authority unless verified against
  current primary or authoritative sources. Never infer governing law.

## Intake And Sources

Read the entire contract before asking questions. Infer contract family,
transaction, parties, governing-law clause, language clause, incorporated
documents, and existing revisions.

When the user states no position, presume the principal at-risk party from the
contract type and signing posture, declare that presumption explicitly in the
report's facts-and-assumptions section（"本报告基于 X 方（推定）立场审查，如立场
相反请告知后重审"）, and never label such a review `中立`. Record the same party
in the structured `review_position` field of `report.json`.

**One position governs the whole report.** Every risk item is written from that
single party's lens — it states only how the clause harms *our* declared party,
with a recommendation that protects *our* party. Do not argue both sides inside
one risk: never write "对我方不利……反之对方也可能面临……" hedging in a risk
entry. The buyer's loss may appear in a seller-lens item only as a description
of *our* exposure (what we would have to pay), not as the other side's risk.
Two-sided comparison belongs exclusively in the rights-symmetry section, whose
job is to contrast both parties. If an issue actually favors our party or only
burdens the counterparty, it is a strength or a symmetry note — not a risk-list
item.

If a user-supplied playbook exists, read
`references/playbook-and-coverage.md`. Otherwise use
`references/review-matrix.md` and label the result as general practice.

Classify the agreement by economic substance, not its title. Load the 12
universal rules in `references/review-matrix.md` and any applicable rules in
`references/jurisdiction-overlays.md`. 分合同类型的专属审查卡片已因体积约束移除；
审查要点一律以 `review-matrix.md` 的 12 条通用规则为准，并标注为一般惯例。

## Workflow

Execution control: run a self-check（自检）at each deliverable gate. If
validation fails, change strategy instead of repeating the same operation. The
circuit breaker（熔断）is two different failed strategies at the same step;
then stop retrying and transfer the blocking item for human review. The same
breaker applies to any external agent or sub-skill call: set a time budget up
front; on timeout, stop and report instead of waiting indefinitely.

1. Accept `.docx` directly. Convert `.doc` first with
   `soffice --headless --convert-to docx`. PDF 输入请先转为 Word 再处理（PDF 入库
   脚本已因体积约束移除）。Then run `scripts/review_docx.py extract` and index
   every visible paragraph.
2. Model the intended deal and hard-check territory, field, exclusivity,
   parties, rights direction, term, economics, control, and exit before
   ordinary clause review. For every parameter marked deviates / below bottom
   line / reversed / absent, the `basis` must carry specific content (not a
   bare `[惯例]`). Cite clause numbers exactly as the source contract numbers
   them — a wrong Section number fails source cross-validation.
3. Review in four passes: transaction, clauses, risk, and precision. Perform
   both forward harmful-term review and reverse missing-protection review.
   Before listing any protection as missing, search the whole contract for an
   equivalent clause（含其英文标题，如 Protection of Personal Data、
   Anti-Corruption）; only call it missing after confirming none exists, and
   note where you looked. A clause that exists is never a "missing protection".
4. Compare both parties' material rights. For IP, separately test ownership,
   prosecution/control, and enforcement. Name each party with its actual name
   plus role（如 `[公司名]（卖方）`）；never output a bare `客户` placeholder.
5. Scan civil, regulatory, criminal, tax, sanctions, execution, data,
   confidentiality, IP, termination, dispute, and mandatory-law exposure.
6. Rate each issue by impact multiplied by likelihood: high, medium, or low.
   State assumptions. Every high/medium issue needs a populated
   `impact_likelihood`（影响×可能性，留空会被构建脚本拒绝）, directly usable
   wording, negotiation fallback, and business effect. Reference each issue only
   by its `issue_id`; never run a parallel `ISS-`/`#` numbering — the build
   script renumbers risks to `R-NNN` and rewrites cross-references to match.
   Do not state risk counts by hand in the executive summary that contradict the
   risk list — the build script renders authoritative counts and **fails** on a
   mismatch. Any claim that a clause lacks something（"无最低限额/无上限/未约定…"）
   must quote that clause's text as basis; a misread that contradicts the source
   is caught by source cross-validation.
7. Use only `[用规]`, `[要点]`, `[法规]`, `[惯例]`, in that order. Mandatory law
   overrides a conflicting user rule. Internal practice-card points use
   `[惯例]` only. Every label must carry traceable content — a bare label is
   invalid: `[法规]` needs statute name plus article（如 UCC §2-719、Singapore
   SGA s.14）, `[用规]` cites the rule file and clause, `[要点]` quotes the
   user, `[惯例]` names the industry and practice. Unverifiable authority →
   `待核查`, never a naked `[法规]`.
8. Create `operations.json` from `references/input-schema.md`. Give every issue
   a stable `issue_id`. Each high/medium recommendation must be a `replace` or
   `replace_text`; a comment-only exception requires `comment_only_reason`.
9. Run `scripts/review_docx.py apply` with `redline_mode` to create only the
   Redline and decision state. Build the Chinese report from a populated
   `report.json` (risks/scope/executive_summary etc.) — never feed
   `operations.json` to `build_review_report.py`; it is the apply file, not the
   report, and the builder will reject it rather than emit an empty shell.
   Never generate an internal or user-facing Clean during initial review.
10. Validate the Report, selected Redline mode, operations, and decision state;
    then render and inspect every page.

**Complete the review section by section — no step may be skipped.** Each
report chapter is the output of a specific step and must hold substantive
content before delivery: scope · facts · playbook_status · executive_summary ·
structural_parameters · risks（每条填齐 位置/问题/影响×可能性/建议/依据）·
coverage · missing_terms · symmetry · ip_analysis · recommendations（有高/中
风险时必填）· verification · pending. A section that does not apply must say so
explicitly（"本节不适用：原因"），never be left blank. The build script
**fails** if any required chapter is empty; the validator **fails** on an empty
section, a leaked dict literal, raw markdown, an oversized table, or a count
mismatch — fix the data and rebuild. Do not deliver a report with gaps, layout
disorder, or mismatched content.

## Clean Decision Tree

After presenting Report + Redline, move to `awaiting_risk_confirmation`.

1. Require a decision for every high/medium issue and every proposed text edit:
   `accept_proposed`, `retain_original_accept_risk`, `custom_text`, or `pending`.
2. Treat `没问题`, `可以，出 Clean`, and equivalent unqualified approval as
   `accept_all_proposed=true`.
3. A retained original clause requires a written risk-acceptance note. Keep the
   original text and preserve that note in the decision state.
4. A `custom_text` decision cannot produce Clean. Run `revise-operations`,
   regenerate the Redline, return to `awaiting_risk_confirmation`, and obtain
   confirmation of the revised wording.
5. Any blocking `pending` issue stops Clean generation. Low-risk comment-only
   items do not block.
6. Only after all blocking issues close, run `finalize-clean` from the original
   contract, effective operations, and decisions. Validate it, then run
   `complete-state` to set `workflow_stage` to `completed`.

The allowed stages are `reviewing` → `markup_ready` →
`awaiting_risk_confirmation` → `clean_ready` → `completed`.

All generated artifacts must be written under `outputs/` inside this skill
package. Inputs supplied by the user may remain outside the package. Never
write generated files to another project directory or include an absolute
local path in a source citation.

## Deliverables

Default delivery is only:

- Report: Chinese review report with the opening disclaimer.
- Redline: `revisions_only`, `comments_only`, or `both`; default `both`.
- Decision state: internal JSON keyed by stable `issue_id`.

Generate additional files only after explicit confirmation:

- Clean: generate with `review_docx.py finalize-clean` only after the decision
  tree reports no blocking pending issue.
  （Bilingual 双语版脚本已因体积约束移除；如需双语版请使用独立的翻译类技能。）

Read `references/output-spec.md` for format requirements and
`references/input-schema.md` for interfaces. Shared cross-language rules
(safety redlines, evidence labels, risk matrix, review methodology, common
output spec) live in the SSOT `../../_shared/contract-review-core/`（本技能包内 shared-core 副本已因体积约束移除，关键红线保留在本 SKILL.md 正文）. Contract headings must be black,
tables must fit A4, DOCX files must contain no emoji, and signature rows must
not split across pages. `report.json` field values are plain text — never
Markdown markup（`##`/`**`/backticks/list markers）: DOCX does not render
Markdown and the tokens leak verbatim into the report; use items arrays for
grouping. The build script converts stray tokens as a fallback and the
validator fails a report containing raw markup.

Every delivery message must end with a deliverable manifest: one line per
generated file — file name, `outputs/` path, purpose, status（已交付 /
待确认后生成）. A file that was generated but never listed to the user is an
incomplete delivery, even if it exists on disk.

## Validation And Recovery

Before delivery confirm:

- original file unchanged;
- full forward and reverse review completed;
- every high/medium issue maps to a real text revision or documented exception;
- each issue has a unique `issue_id`, and Redline content matches its mode;
- Clean is absent before confirmation and matches every final risk decision;
- no inconsistent definition, cross-reference, date, amount, remedy, or
  bilingual qualification remains;
- report contains the disclaimer and contract files do not;
- **every report chapter has substantive content — no empty section, no
  `本节不适用` left blank, no leaked `{'zh': …}` dict literal, no raw markdown;
  authoritative risk counts match the list; every risk row is fully filled;**
- A4, table width, black headings, no emoji, valid evidence labels, bilingual
  priority fields, and signature-row pagination all pass.

Use only bundled `scripts/*.py` for DOCX and file transformations. If one
strategy fails, re-extract and try a different safe operation. After two
different failures at the same step, stop, report the blocking structure, and
request human review rather than repeating the same operation.

After presenting Report + Redline, show issue IDs and decision choices.
