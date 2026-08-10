# Requirement Checklist Schema

动笔前在 `<workspace>/.doubao-book-writer/requirement-checklist.json` 写入需求清单。`make prepare` 会现场校验；缺失或格式错误会阻断整条依赖链。

```json
{
  "topic": "一句话描述项目",
  "contentProfile": {
    "id": "general",
    "genreGuide": "general",
    "audience": "目标读者",
    "purpose": "交付目的"
  },
  "structureRules": {
    "headingPolicy": "chinese-publication",
    "maxContentFilesPerBatch": 2
  },
  "sourcePolicy": {
    "mode": "search-before-writing",
    "minimumDirections": 3,
    "requireGapReview": true
  },
  "sourceInputs": [
    {
      "id": "user-brief",
      "kind": "pdf",
      "path": "materials/user-brief.pdf",
      "writePolicy": "read-only"
    }
  ],
  "delivery": {
    "mode": "lark-docx",
    "requireReadBack": true
  },
  "requirements": [
    {
      "id": "R1",
      "requirement": "用户需求原文",
      "priority": "main",
      "in_scope": "yes",
      "carrier": "落实章节或形式",
      "resolution": ""
    }
  ],
  "wordCountRules": [
    {
      "id": "total-length",
      "target": 10000,
      "tolerancePercent": 10
    }
  ]
}
```

## 字段规则

- `requirements` 至少一项；至少一项 `priority: main`。
- `in_scope` 只能是 `yes` 或 `no`；交付前所有 `yes` 项必须填写 `resolution`。
- `contentProfile.id` 与 `genreGuide` 只允许小写字母、数字和连字符；未知 genre guide 自动回退 `general`。
- `structureRules.headingPolicy` 固定为 `chinese-publication`；每批正文文件数只能是 1 或 2。
- `sourcePolicy.mode` 支持 `search-before-writing`、`targeted-when-needed`、`user-materials-only`、`offline-disclosed`。
- 用户提供附件时必须写入 `sourceInputs`；本地附件使用 book root 内相对 `path`，在线链接使用 HTTPS `url` 且 `kind: link`。`writePolicy` 固定为 `read-only`，附件只读不覆盖。
- `delivery.mode` 支持 `lark-docx` 和 `markdown-only`。`lark-docx` 强制云端读回；`markdown-only` 只有在用户显式提出时才可选用（全程加 `SKIP_LARK=1`），并必须设置 `userExplicitlyRequested: true` 与非空 `requestEvidence`。
- `wordCountRules` 可使用 `target`、`minimum`、`maximum`、`minimumAdded` 与 `tolerancePercent`；可选 `path` 必须位于 book root 内。
- 字数要求是硬门禁：`tolerancePercent` 默认 20，且只能在 0–20 之间；`target` 的实际结果不得低于目标的 80% 或高于 120%。显式 `minimum` / `maximum` 只能进一步收紧该区间，不能放宽。
- `minimumAdded` 用于续写、改写和扩写；`make write` 一次性全量检查时把它按"当前正文至少 N 字"的全量下限校验（三阶段模型不再使用写作前的增量基线）。
- 长稿大纲必须把全书目标完整分配到各章，各章目标合计必须等于大纲总目标；大纲总目标还必须落在无 `path` 的全书级 `wordCountRules` 边界内。
- `make write` 对当前全部正文一次性执行完整上下限检查：低于下限或超出上限即阻断，不做写作前后差值比较。
