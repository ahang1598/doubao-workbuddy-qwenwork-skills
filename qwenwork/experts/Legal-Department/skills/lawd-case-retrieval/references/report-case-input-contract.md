# 类案检索报告输入契约

## 目的

本文件是 `律师类案检索与报告` **模式C（正式类案检索报告）**的输入契约，原属 `lawd-case-retrieval-report`（旧名「类案检索报告」）。生成器只接受 UTF-8 JSON。模型或检索工具先把原始结果映射为本契约，再运行校验与 DOCX 生成脚本。禁止为通过校验而推断或补造字段。

上游数据来自本技能**模式A（类案检索）**的交接 JSON；`full_text` 的唯一合法来源是本技能**模式B（按案号取裁判文书全文）**实际取得的逐字文书正文。

## 顶层结构

```json
{
  "schema_version": "1.0",
  "report": {},
  "query": "",
  "retrieval_targets": [],
  "conclusions": [],
  "explicit_constraints": {},
  "cases": []
}
```

## `report`

```json
{
  "title": "类案检索报告",
  "matter": "项目或案件名称",
  "prepared_by": "制作主体",
  "prepared_at": "2026-08-04",
  "data_source": "检索平台或数据来源",
  "retrieved_at": "2026-08-04",
  "methods": ["关键词检索法"]
}
```

- 除 `title` 外均可为空。
- 日期推荐使用 `YYYY-MM-DD`，但生成器不据此推断案例日期。
- `data_source` 必须是实际使用的来源。

## `explicit_constraints`

只记录用户明确提出的约束；未提出的键使用空值或省略。

```json
{
  "date_from": "2020-01-01",
  "date_to": "2026-08-04",
  "regions": ["北京", "上海"],
  "court_levels": ["高级人民法院"],
  "max_cases": 10,
  "other": ["仅纳入生效裁判"]
}
```

- 不设置默认时间、地域或案例数量。
- `regions` 按用户原话记录；校验时与正式法院名称作包含匹配。
- 有明确约束但案例字段缺失、导致无法证明符合约束时，校验失败。

## `cases`

```json
{
  "case_id": "source-unique-id",
  "title": "甲公司与乙公司买卖合同纠纷案",
  "case_no": "（2024）京01民终123号",
  "court": "北京市第一中级人民法院",
  "judges": ["张某"],
  "decision_date": "2024-05-20",
  "facts": "与检索目标相关的基本案情",
  "holding": "裁判要旨或检索摘要",
  "court_reasoning_quote": "来源中‘本院认为’的原文摘录",
  "legal_basis": ["来源数据明确提供的法律依据"],
  "source_url": "https://example.invalid/case/1",
  "raw_record_locator": "数据库记录ID或原始文件位置",
  "full_text": "案例全文；没有则为空字符串"
}
```

### 身份键与唯一性

- 按 `case_id → case_no → raw_record_locator` 依次取首个非空字段作为案例身份键。
- 三个身份字段至少有一个非空，身份键在本报告内必须唯一。
- `case_id` 仅在数据源实际提供时填写；不得为通过校验而虚构业务标识。
- `title`：必填，不得以占位符代替。
- 其他字段允许为空，但必须如实为空。
- `case_no` 非空时应唯一；发现重复通常意味着同案重复纳入。

### 字段边界

- `court`：只放数据源提供的正式法院名称，不从省市区和法院层级拼接。
- `decision_date`：只放明确裁判日期；推荐 `YYYY-MM-DD`。
- `facts`：可忠实压缩，不得补事实。
- `holding`：允许来源摘要或忠实概括，但不要标成法院原文。
- `court_reasoning_quote`：只能放来源中的原文摘录；没有则留空。
- `full_text`：必须是案例全文；摘要不得放入此字段。
- `raw_record_locator`：用于回溯原始记录，推荐保留。

## 缺失值

- 文本字段：`""` 或 `null`。
- 列表字段：`[]`。
- 生成器统一显示“检索结果未提供”。
- 禁止使用 `待补充`、`TBD`、`TODO`、方括号模板变量等占位符。

## 上游类案检索交接对接

案例数据来自类案检索能力的交接 JSON（`schemaVersion: case-retrieval-handoff/v1`）时，按以下规则转换后再运行校验。交接 JSON 由案例检索连接器返回并归一化而来，字段以连接器运行时实际返回为准。

- 报告案例范围以上游 `delivery` 集合为准；全文与原文回读用 `full` 集合。不得因报告模板增加、删减或重新排序案例。
- `report.data_source`：按本次实际使用的检索来源填写。交接 JSON 的 `source.provider` 为来源标识（`case-retrieval-connector`，即案例检索连接器）；检索说明中记录了具体连接器名称时按其如实填写。
- 字段映射（交接 JSON 的 `caseDomain` → 本契约 `cases`）：

| 本契约字段 | 上游 caseDomain 字段 | 说明 |
|---|---|---|
| `case_id` | `caseId` | 仅连接器实际返回时填写，不得虚构 |
| `title` | `caseTitle` | 必填 |
| `case_no` | `caseNo` | 逐字照录；为空时留空，报告统一显示“检索结果未提供” |
| `court` | `trialCourt.name` | 不得由地域或层级拼接 |
| `decision_date` | `trialDate` | 以返回语义为准 |
| `facts` | `keyfacts` / `caseBasic` / `caseSummary` | 忠实压缩，不补事实 |
| `holding` | `caseSummary` / 裁判要旨类字段 | 仅有摘要时标注“检索摘要” |
| `court_reasoning_quote` | `courtThink` | 仅放来源原文摘录；没有则留空 |
| `legal_basis` | `legalBasis` / `appliedLaws` | |
| `source_url` | 连接器返回的详情链接 | 没有则留空 |
| `raw_record_locator` | `caseId` 或分页文件位置+序号 | 推荐保留 |
| `full_text` | 见下条 | |

- `sourceContent` 为连接器整理后的案例内容，**不等同于裁判文书逐字全文**，不得放入 `full_text`；可作为 `facts` / `holding` 的素材并按“检索摘要”标注。`full_text` 仅放确实取得的逐字案例全文（如通过内置浏览器连接器读取的公开文书正文）；未取得全文时留空，报告附件部分如实注明“本次检索数据未包含案例全文”。
- 交接 JSON 未提供的字段一律按本契约缺失值规则处理，不得虚构。
- 交接 JSON 的 `processing` 统计（原始数、去重数、交付数、缺口等）可用于撰写“检索说明”部分的数量与去重说明。

## 案例顺序

`cases` 数组顺序即正式报告中的顺序。排序依据由用户要求和报告编制者基于已知数据确定；生成器不自动改变顺序。
