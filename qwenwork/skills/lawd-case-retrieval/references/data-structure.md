# 类案检索数据结构

## 归一化分页 JSON（处理脚本输入契约）

案例检索连接器的原始返回 schema 因供应商而异。每一检索轮次（页）的返回必须先归一化为以下结构，再保存为分页文件；这也是 `scripts/process_case_results.py` 接受的唯一输入结构：

```json
{
  "Body": {
    "success": true,
    "data": {
      "caseResult": [
        {
          "caseDomain": {},
          "similarity": "0.85"
        }
      ],
      "currentPage": 1,
      "pageSize": 10,
      "query": "检索语句",
      "totalCount": 100
    }
  }
}
```

`Body.success` 缺失时不单独判错；明确为 `false` 时校验失败。`Body.data.caseResult` 必须是数组，每个元素及其 `caseDomain` 必须是对象。

归一化要求：

- 映射以连接器实际返回字段的 schema 为准（调用前用 schema 查询能力确认）；只映射连接器实际返回的字段；
- 连接器未返回的字段在 `caseDomain` 中保持为空，不得虚构、补全；
- `similarity`（相关度评分）、`currentPage`、`pageSize`、`query`、`totalCount` 为可选字段：连接器返回时如实填入，未返回时可省略。

## 连接器返回字段语义 → caseDomain 映射

按连接器实际返回字段的语义映射到 `caseDomain`；**具体字段名以连接器运行时 schema 为准**。下表为语义对照参考：

| 字段语义 | 归一化字段 | 说明 |
|---|---|---|
| 案例记录标识 | `caseId` | 连接器返回的唯一标识，用于去重与详情回读 |
| 案号 | `caseNo` | 逐字照录；缺失保持为空/null |
| 案件/文书名称 | `caseTitle` | |
| 案件类型 | `caseType` | 民事、刑事、行政等 |
| 案由 | `caseCause` / `openCaseCause` / `closeCaseCause` | |
| 审理法院 | `trialCourt.name` | 正式法院名称，不得由地域拼接 |
| 裁判/审理日期 | `trialDate` | 以返回语义为准 |
| 审级和程序 | `trialLevel` / `trialProgram` | |
| 参考级别 | `referLevel` | 指导性、典型、公报等；仅权威案例返回 |
| 争议焦点 | `disputeFocus` / `disputedpoints` | |
| 案情摘要 / 裁判要旨 | `keyfacts` / `caseBasic` / `caseSummary` | 连接器返回的裁判要旨、摘要、案例说明或整理后内容 |
| 裁判结果 | `verdict` | |
| 法律依据 | `legalBasis` / `appliedLaws` | |
| 法院观点 / “本院认为” | `courtThink` | 仅保留连接器实际返回的内容 |
| 案例内容 / 整理后全文 | `sourceContent` | **不等同于裁判文书逐字全文** |
| 数据来源 | `dataFrom` | 记录实际使用的连接器/数据来源名称 |

上表之外连接器实际返回的其他字段可原样保留在 `caseDomain` 中，不删除原始信息。

### 常见连接器映射示例（元典 yuandian）

以元典案例语义检索（`yuandian_case_vector_search` 一类工具）为例——**字段名仍以运行时 `qwenwork_mcp_tool_get` 返回的 schema 为准**，本表仅为常见形态参考：

| 元典返回字段（常见名） | caseDomain 归一化字段 | 备注 |
|---|---|---|
| `caseId` / `id` | `caseId` | 去重与详情回读键 |
| `caseNo` | `caseNo` | 逐字照录 |
| `caseTitle` / `title` | `caseTitle` | |
| `courtName` / `court` | `trialCourt.name` | 不得由地域拼接 |
| `trialDate` / `judgeDate` | `trialDate` | |
| `caseCause` | `caseCause` | |
| `content`（整理后内容） | `sourceContent` | **逐字照录、禁止截断/清理**；不等同于裁判文书全文 |
| `keyfacts` / `abstract` | `keyfacts` / `caseSummary` | 按返回语义择一映射 |
| `courtThink` | `courtThink` | 仅返回有时映射 |
| `score`（相关度） | `similarity` | 外层字段，非 caseDomain 内 |

元典返回无 `referLevel`、`legalBasis` 等字段时，对应归一化字段保持为空，不得补全。

## 处理后交接结构

`cases_full.json` 与 `cases_delivery.json` 使用同一稳定结构：

```json
{
  "schemaVersion": "case-retrieval-handoff/v1",
  "setType": "full | delivery",
  "query": "检索语句",
  "source": {
    "provider": "case-retrieval-connector",
    "pageCount": 1,
    "serviceTotalCount": 100
  },
  "processing": {
    "requestedCount": null,
    "rawCaseCount": 10,
    "uniqueCaseCount": 9,
    "deliveryCount": 9,
    "duplicateCount": 1,
    "shortfall": 0,
    "missingCaseNoCount": 1,
    "heavyFieldsTrimmed": true,
    "courtThinkIncluded": false
  },
  "cases": []
}
```

- `source.provider` 固定为 `case-retrieval-connector`，表示数据来自案例检索连接器；实际使用的连接器名称记录在检索说明与案例的 `dataFrom` 字段中。
- `full`：`cases` 保存全部去重后的原始案例对象，`heavyFieldsTrimmed=false`。
- `delivery`：`cases` 仅保存本次应交付的前 N 条或首页全部结果，并裁剪重字段。
- 两个集合保持检索返回的首次出现顺序，不自行按相似度重排。
- 报告能力应读取 `full` 获取原文，读取 `delivery` 确定本次报告案例范围。

## 去重规则

按以下稳定优先级确定同一案例：

1. 非空 `caseDomain.caseId`；
2. 非空 `caseDomain.caseNo`；
3. `caseTitle + trialCourt.name + trialDate` 的组合；
4. `caseDomain` 完整 JSON 的稳定摘要。

去重只决定保留哪条记录，不修改任何案件字段；保留第一次出现的数据。

## 列表常用字段

| 字段 | 用途 |
|---|---|
| `caseId` | 案例唯一标识，优先用于去重 |
| `caseNo` | 案号，必须逐字引用；缺失显示“无” |
| `caseTitle` | 案件或文书名称 |
| `caseType` | 案件类型 |
| `caseCause` / `openCaseCause` / `closeCaseCause` | 案由 |
| `trialDate` | 裁判或审理日期，以返回语义为准 |
| `trialLevel` / `trialProgram` | 审级和程序 |
| `referLevel` | 指导性、参考性或其他类型 |
| `trialCourt.name` | 审理法院名称 |
| `disputeFocus` / `disputedpoints` | 争议焦点 |
| `keyfacts` / `caseBasic` / `caseSummary` | 案情摘要 |
| `verdict` | 裁判结果 |
| `legalBasis` / `appliedLaws` | 法律依据 |
| `dataFrom` | 数据来源 |

字段为空时不得从其他字段猜测。法院名称不得通过地域拼接生成。

## 默认裁剪字段

交付集默认移除：

- `courtFindOut`
- `courtThink`
- `sourceContent`
- `trialProcess`
- `preTrialProcess`

指定 `--include-court-think` 时只保留 `courtThink`，其余重字段仍裁剪。完整集合始终保留全部原始字段。

## 案号规则

- 非空字符串：展示时原样输出，不清理空格、不替换括号、不纠错。
- 空字符串、仅空白、`null` 或字段缺失：展示 `案号：无`。
- 不要求案号必须匹配某个固定正则；真实数据可能包含不同文书编号格式。
- 不在案号后附加“推测”“待核验”等文字。

## 字段使用边界

- `similarity` 仅代表服务端返回的相关度，不等于胜诉概率。
- `verdict` 不能在语义不清时被机械转换为原告胜诉或败诉。
- `totalCount` 是服务端报告数量，不等于本地已取得或去重后的数量。
- `sourceContent` 是连接器整理后的案例内容，不等同于裁判文书逐字全文；向用户展示全文诉求时按 SKILL.md 的浏览器兜底与降级规则处理。
- AI 洞察使用 `delivery`；用户查看原文或下游生成正式报告时按需回读 `full`。
