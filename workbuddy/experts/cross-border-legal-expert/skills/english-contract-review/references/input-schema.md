# Review Interfaces

All generated `--out`, `--redline`, `--clean`, report, bilingual, and render
paths must be under this skill's `outputs/` directory.

## Extract

```bash
python scripts/review_docx.py extract input.docx \
  --out outputs/run/inputs/extracted.json
```

Each paragraph receives a stable ID, visible text, table status, and flags for
revisions, comments, drawings, and fields.

## Apply Redline

```bash
python scripts/review_docx.py apply input.docx operations.json \
  --redline outputs/run/redline.docx \
  --redline-mode both \
  --state-out outputs/run/decision-state.json
```

`redline_mode` is `revisions_only`, `comments_only`, or `both`; default `both`.
Initial review must not generate a Clean file.

```json
{
  "operations": [
    {
      "issue_id": "R-001",
      "target": "p0012",
      "action": "replace_text",
      "old_text": "sole discretion",
      "new_text": "reasonable discretion",
      "risk": "medium",
      "basis_tag": "[要点]",
      "risk_description": "单方自由裁量缺少客观边界。",
      "recommended_action": "增加合理性标准并保留可核验依据。",
      "suggested_wording": "reasonable discretion"
    },
    {
      "issue_id": "R-002",
      "target": "p0020",
      "action": "comment",
      "risk": "low",
      "basis_tag": "[惯例]",
      "risk_description": "通知地址尚未核实。",
      "recommended_action": "签署前确认地址和电子邮箱。",
      "comment_only_reason": "事实确认事项，无需直接修改条款。"
    }
  ]
}
```

Allowed actions: `replace`, `replace_text`, `comment`. Every high/medium
finding must be a replacement unless `comment_only_reason` records an
uneditable structure, an absent term without an anchor, or a pending commercial
decision. Every operation requires a unique, stable `issue_id`.

## Risk Decisions

```json
{
  "accept_all_proposed": false,
  "risk_decisions": [
    {
      "issue_id": "R-001",
      "decision": "accept_proposed"
    },
    {
      "issue_id": "R-002",
      "decision": "retain_original_accept_risk",
      "note": "用户确认通知信息将在签署页另行补充，并接受当前文本风险。"
    }
  ]
}
```

Allowed decisions are `accept_proposed`, `retain_original_accept_risk`,
`custom_text`, and `pending`. `accept_all_proposed=true` applies only to
replacement operations; high/medium comment-only exceptions still require an
express decision. A retained risk requires `note`.

If the user gives custom wording, first regenerate the proposal:

```bash
python scripts/review_docx.py revise-operations \
  operations.json custom-decisions.json \
  --out outputs/run/operations-revised.json

python scripts/review_docx.py apply input.docx \
  outputs/run/operations-revised.json \
  --redline outputs/run/redline-revised.docx \
  --redline-mode both \
  --state-out outputs/run/decision-state-revised.json
```

The revised issue returns to `pending` and must be confirmed again.

## Finalize Clean

```bash
python scripts/review_docx.py finalize-clean \
  input.docx operations.json decisions.json \
  --out outputs/run/reviewed-clean.docx \
  --state-out outputs/run/final-state.json
```

`finalize-clean` fails closed while a blocking issue is `pending`, when a
retained risk lacks a note, or when `custom_text` has not been re-redlined.
The Clean is rebuilt from the original contract and contains no Redline
summary, comments, or revision markers.

After Clean validation succeeds:

```bash
python scripts/review_docx.py complete-state outputs/run/final-state.json \
  --out outputs/run/completed-state.json
```

## Bilingual Clean

Generate only from a confirmed Clean after the user confirms both order and
language priority.

```bash
python scripts/build_bilingual_data.py clean.docx \
  --translations translations.json \
  --language-mode en_zh \
  --language-priority-en "The English version prevails" \
  --language-priority-zh "英文版本优先" \
  --out outputs/bilingual.json

python scripts/build_bilingual_review.py \
  outputs/bilingual.json outputs/reviewed-bilingual.docx
```

```json
{
  "title_en": "Reviewed Services Agreement",
  "title_zh": "经审查的服务协议",
  "language_mode": "en_zh",
  "language_priority_en": "The English version prevails",
  "language_priority_zh": "英文版本优先",
  "paragraphs": [
    {
      "number": "1",
      "en": "English clause text",
      "zh": "中文条款文本",
      "kind": "clause"
    },
    {
      "kind": "table",
      "headers": [
        {"en": "Item", "zh": "项目"},
        {"en": "Fee", "zh": "费用"}
      ],
      "rows": [
        {
          "cells": [
            {"en": "Setup Fee", "zh": "设置费"},
            {"en": "$5,000", "zh": "5,000 美元"}
          ]
        }
      ]
    }
  ]
}
```

`kind` may be `clause`, `heading`, `article`, or `table`. Headings are black.
All table rows use `cantSplit`; signature rows must never cross pages.

## Review Report

```bash
python scripts/build_review_report.py report.json \
  outputs/run/review-report.docx
```

输入必须是 **report.json**（报告数据），**不可传 operations.json**（那是
`review_docx.py apply` 的修订操作文件，只含 `operations` 数组）——传错会被脚本
拒绝而非渲染空壳。核心字段（risks / scope / executive_summary /
structural_parameters）不得全空。

Required top-level fields:

- `review_position`: `{party(当事人名+角色，如 "卖方（[公司名]）"), basis(声明/推定及理由)}`。
  全文唯一声明立场，渲染为免责声明下方的立场横幅。缺失时脚本从 `facts` 推断；
  推断不出则按无立场处理（不做立场校验）。**建议始终显式提供。**
- 凡叙述型分节（`scope`/`facts`/`playbook_status`/`executive_summary`/
  `verification`/`deliverables` 等），用 string 或 `{zh, en, items}` 形状。
  **禁止 `{"items":[...]}` 裸结构**或用键名承载内容——脚本已健壮兜底（不再渲染
  键名），但正确形状是 `{zh:"…", items:[…]}`。
- `scope`: string or `{en, zh, items}`.
- `facts`: string or `{en, zh, items}`. 用户未给立场时，此节必须含推定立场声明
  （"本报告基于 X 方（推定）立场审查"），与 `review_position` 一致。
- `playbook_status`.
- `executive_summary`: string 或 `{zh, items}`。其中声称的风险数量（高/中/低 N 项）
  **必须与 `risks` 实际数量一致**——脚本从 `risks` 计算权威计数并渲染在风险清单下，
  摘要数字与实际不符即 **FAIL**。
- `structural_parameters`: `{parameter, preferred, bottom_line, actual, status, basis_tag}`.
  status 为 deviates/below bottom line/reversed/absent 的参数，`basis_tag` 必须含
  **具体依据内容**（不能仅 `[惯例]` 裸标签）——否则脚本告警。条款号引用须与源合同一致。
- `risks`: `{issue_id, level, location, issue, impact_likelihood, recommendation, basis_tag}`.
  渲染时按列表顺序重编号为 `R-001…R-N`（脚本自动执行，最终排序即编号顺序），
  **并自动把正文各处对旧 ID 的交叉引用同步改写为新号**（修复"表用 R- 正文引 ISS-"
  的前后不一致）。全文引用风险一律用 `issue_id`，勿另造 `ISS-`/`#` 等并行编号；
  构建脚本对未对应到任何风险的悬挂引用发出警告。
  `impact_likelihood`（影响×可能性）对**高/中风险为必填**，留空将 FAIL；可写
  `impact`/`影响与可能性` 等别名，脚本会规整到 `impact_likelihood`。
  **立场单一性（硬约束）**：每条风险只从 `review_position` 一方视角评估不利后果，
  建议措辞保护己方。**禁止在同一条目内并列对方风险**（如"对我方不利……反之对方
  也面临……"）——构建脚本检测到「转折词 + 对方被框定为担险主体」即 FAIL。
  对方的损失仅可作为"己方赔付敞口"出现，不得描述为对方的风险。双方对比一律放入
  `symmetry`。若某问题实为对己方有利或仅加重对方，它属于强项或对称性条目，不进风险清单。
- `coverage`: structured list `{item(中文描述), direction(正向/反向),
  status(已覆盖/缺失/部分), location}`, or `{empty_reason}` when no playbook.
  禁止把 playbook 内部键名（如 `universal_rules`）直接作为条目——构建脚本会拒绝
  裸英文标识符。
- `missing_terms`：仅列**全文确无对应条款**的缺失保护。列入前须反向走查合同
  （含英文标题，如 Protection of Personal Data / Anti-Corruption）；已存在的条款
  不得列为缺失——validator 会拿"缺失保护"节与源合同交叉核验，疑似误判即告警。
- `symmetry`: `{right, client_position, counterparty_position, assessment}`.
  立场列用**当事人名+角色**（如 `[公司名]（卖方）`），禁用裸"客户"。空时可省略或
  `[]` —— 报告渲染"本节不适用"一行，章节编号保持连续（不再整节跳过）。
- `ip_analysis`: `{category, ownership, control, enforcement}`. 空时同上。
- `recommendations`.
- `verification`.
- `pending`: 必须汇总全文所有 `待核查` 条目。若留空而正文存在待核查项，
  构建脚本会自动聚合并告警。
- `deliverables`（可选）：一句中文交付与验证说明（交付了哪些文件、校验结论），
  作为存档报告内的简要记录。**仅当为含中文的实质说明时才渲染成「交付与验证说明」章；
  纯文件名 token（如 `["report","redline"]`）或空值会被整章省略**——文件清单由对话
  交付消息负责，报告内不重复裸键名。

Bilingual dicts（`{en, zh}`）渲染为 **zh-primary**：中文报告只输出 `zh`，
`zh` 缺失时回退 `en`；`en` 字段供双语版交付物复用，不再在中文报告中双段排版。

Status and risk values use text such as `【高风险】`, `【符合】`, `【缺失】`,
`【关注】`, `【反转】`; do not use emoji. 风险措辞克制专业：禁用
`毁灭性`/`灾难性`/`极其危险`；概率仅 高/中/低。

**所有字段值为纯文本，禁止 Markdown 标记**（`##`、`**…**`、`` ` ``、`- ` 列表、
`[]()` 链接）——docx 不渲染 Markdown，记号会字面泄漏进报告。需要小节分组时用
列表结构（items 数组）而非 `##`；需要强调时直接陈述，不加粗。构建脚本会把
`**…**` 兜底转为真实加粗、行首 `#` 转为小节标题、其余记号剥离；校验器对最终
docx 中残留的原始记号判 FAIL。
