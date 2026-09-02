# Output Specification

This file is the package-internal format authority for all review deliverables.

## Delivery Gate

| Deliverable | Timing |
|---|---|
| Chinese Report | Default |
| Redline | Default; mode defaults to `both` |
| Decision state | Default internal artifact |
| Clean | Only after all blocking risk decisions close |
| Bilingual | Only after user confirms order and language priority |

## Common Rules

- A4, margins top/bottom 2.3 cm and left/right 2.6 cm.
- English Arial; Chinese PingFang SC; contract headings black.
- No emoji in generated DOCX content.
- Table grid width no more than 9026 DXA.
- Signature rows contain `w:cantSplit` and do not cross pages.
- Evidence tags are limited to `[用规]`, `[要点]`, `[法规]`, `[惯例]`.
- Every generated file stays under this skill's `outputs/`.
- Sources cite package files or web URLs, never absolute local paths.

## Redline

- Preserve the original contract structure.
- `revisions_only`: true `<w:ins>` and `<w:del>`; no Word comments.
- `comments_only`: Chinese Word risk comments; no `<w:ins>` or `<w:del>`.
- `both`: true revisions plus Chinese Word risk comments.
- Comments are authored by `法大大iTerms` and include risk number, risk level,
  risk explanation, recommended handling, suggested English wording, and basis.
- Append a summary keyed by `issue_id`.
- Do not include the report disclaimer.

## Report

- First 500 characters contain:
  `本文档由 AI 辅助生成，仅供参考，不构成正式法律意见，不能替代具有执业资格的律师。`
- The document title uses the semantic Word `Title` style; chapters use semantic `Heading 1/2/3` styles. All title and heading styles are explicitly black rather than simulated with manual bold formatting.
- Chinese body with 1.5 line spacing; bilingual dicts render **zh only**
  (en is reused by the Bilingual deliverable, never duplicated in the report).
- Report typography uses the enlarged Chinese size scale: Title 22pt, Heading 1
  18pt, Heading 2 16pt, Heading 3 14pt, body/list 12pt, disclaimer and table
  text 10.5pt. These sizes do not apply to Redline, Clean, or the source contract.
- 固定 14 章，章节序号由构建脚本**动态分配**，任何情况下不得跳号；
  无数据章节渲染"本节不适用：原因"一行，不整节省略。
- Black table headers with white text; restrained status colors only.
- 中西文字体：PingFang SC（中）/ Arial（西，含 Normal 样式 ascii/hAnsi），
  全文统一，不得混用默认字体。
- Each risk includes level, location, issue, impact and likelihood,
  recommendation, and evidence basis. Risk IDs render as `R-001…R-N` in final
  display order. Evidence labels must carry traceable content
  （`[法规]`＝法律名+条文号）；裸标签不合格。
- 待核查事项章必须与全文"待核查"标记一致（构建脚本交叉聚合）。
- No absolute safety, validity, compliance, or litigation outcome claims;
  no dramatized wording（毁灭性/灾难性/极其危险）; probability only 高/中/低.
- Under Agent Team orchestration, create a separate normalized report through `word-document-processing` with `mode=normalize` and `profile=richee-legal-report-v2`, then run `mode=validate`. Never overwrite the skill-native report and never normalize the Redline.
- Report tables use content-aware widths: serial columns are capped at 9% of table width, compact level/status columns at 20%, and narrative impact/recommendation columns receive the remaining width according to actual cell content. Do not default to equal columns or preserve an unreasonable upstream ratio.

## Clean

- Generate only from the original contract plus confirmed final decisions.
- Require closure of every high/medium issue and every proposed text edit.
- Apply `accept_proposed`; preserve original wording for
  `retain_original_accept_risk`; reject `pending`.
- Require `custom_text` to be re-redlined and reconfirmed before Clean.
- Remove comments, comment markers, revision markers, and track-revision setting.
- Remove the Redline review-summary section.
- Do not include the report disclaimer.

## Bilingual

- Allowed modes: `en_zh` and `zh_en`.
- Each substantive paragraph and cell contains equivalent English and Chinese.
- Include exactly one English priority field and one Chinese priority field:
  `language_priority_en` and `language_priority_zh`.
- Never place a mixed-language value into both priority fields.
- Record `language_mode` in DOCX core subject metadata.
- Do not include the report disclaimer.

## Validation

Run:

```bash
python scripts/validate_review_outputs.py \
  --redline outputs/redline.docx \
  --report outputs/report.docx \
  --operations outputs/operations.json \
  --redline-mode both \
  --decision-state outputs/decision-state.json \
  --result-json outputs/producer-validation.json
```

For Clean validation add `--clean`, `--source`, and the finalized decision
state. Add `--bilingual --bilingual-mode en_zh|zh_en` only after the confirmed
Clean exists. Render every delivered DOCX and inspect all pages.

`producer-validation.json` is producer-side evidence only. A successful local
check keeps each artifact at `validationStatus=warning`, sets
`producerValidation.trusted=false`, and adds `SELF_VALIDATED_ONLY`; only the
trusted platform validator may promote an artifact to `passed`.
