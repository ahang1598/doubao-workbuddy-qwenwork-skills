---
name: fadada-legal-case-search
name_en: fadada-legal-case-search
description: 检索中国大陆裁判文书、类案（相似案件）的专用 skill，通过 MCP 工具 searchLawCase 进行检索。当用户提到查判例、找案例、搜裁判文书、查案号、研究某类案件裁判趋势、找类似案件、类案检索、这类案件法院怎么判、有没有相关判例等任务时，必须触发此 skill。即使用户只说"帮我找找这个问题的相关案例"或"这种情况法院一般怎么判"，也应触发此 skill 进行案例检索。如果用户同时需要法规和案例，本 skill 在 legal-info-search 之后运行。
---

<!-- Copyright © 深圳市法大大网络科技有限公司 版权所有 | Author: 法大大法律AI产品线 -->

# 类案检索 Skill

## 概述

用于中国大陆裁判文书、权威案例和类案检索，覆盖案号核验、指定来源案例和裁判趋势研究。

核心任务：判断检索场景，生成法律检索表达，保留案号、法院、案由、裁判日期、文书类型、案例来源和入库编号等定位信息。

---

## 对用户可见信息的约束

以下约束覆盖所有用户可见文本，包括过程叙述、进度说明、思考过程和最终回答，无一例外。

- 不出现内部标识符：scene 名（`case_docket_exact`、`case_structured_search`、`case_semantic` 等）、工具参数名（`retrievalScene`、`searchContent`、`structuredFields` 等）、MCP 工具名。
- 过程叙述只描述业务动作，不描述技术步骤。说"正在按限定条件检索裁判文书"，不说"先调用 searchLawCase"或"使用 case_structured_search 检索"。
- 内部概念对用户统一使用业务说法：

| 内部概念 | 对用户表述 |
| --- | --- |
| `case_docket_exact` | 按案号核对目标案例 |
| `case_structured_search` | 按限定条件检索裁判文书 |
| `case_semantic` | 检索相似案例 |
| 调用检索工具 | 正在检索裁判文书库 |
| 复查、二次检索 | 补充检索、换一组条件再查一次 |

- 上表未覆盖的内部概念，转换为法律研究语境下的自然表达；禁止直接向用户抛出英文标识符或技术名词。

---

## 运行环境说明

本 skill 通过 MCP 工具 `searchLawCase` 检索法律类案。工具由已配置的 MCP Server 提供，无需手动配置认证，直接调用工具即可。

调用契约：

- `searchContent`：检索内容，关键词或自然语言描述；精确案号检索时可省略。
- `retrievalScene`：检索场景，取值 `case_docket_exact`、`case_structured_search`、`case_semantic`。
- `structuredFields`：结构化检索字段，精确案号/严格限定检索时使用。
- `searchContent` 与 `retrievalScene` 至少提供其一。

---

## 工作流程

1. 判断检索方式：精确案号核验、严格限定条件检索、普通类案趋势三选一（scene 分别取 `case_docket_exact`、`case_structured_search`、`case_semantic`）；指定官方案例来源的请求暂时按类案趋势处理（`case_semantic`），并原样保留来源、案例编号和入库编号。
2. 改写检索表达：把口语问题改写成适合法律检索的完整自然语言表达（即 `searchContent`）；案号、法院、案由、日期、案例来源、入库编号等定位信息原样保留。
3. 确定随附字段：非语义检索只给已确定的 `structuredFields`；必填字段不够时改用 `case_semantic`，不编造字段。
4. 构造调用：确定 `searchContent`、`retrievalScene` 与 `structuredFields` 的取值。
5. 执行检索：调用 MCP 工具 `searchLawCase`。语义检索传入 `searchContent` 与 `retrievalScene`；精确案号/严格限定检索传入 `retrievalScene` 与 `structuredFields`（`searchContent` 可省略）。
6. 校验并输出：精确案号核对案号；指定官方来源时，只有返回结果明确标注相应来源，才能确认来源符合；结构化检索核对硬条件和用户指定的裁判结果方向。
7. 控制复查：默认一次检索；只有指定案号、指定来源或硬条件结果无法支撑回答时，最多再检索一次。普通类案问题不要为了增加样本反复检索。

---

## 业务场景枚举

> **临时调整**：`case_authority_search` 当前暂停使用。指导性案例、参考案例、案例库编号等问题暂时走 `case_semantic`，完整保留来源和编号；没有核验来源时，不得声称已找到指定来源案例。

选择下列 scene：

| scene | 适用场景 | 示例 |
| --- | --- | --- |
| `case_docket_exact` | 已知案号，要求查目标案例 | `（2021）粤0104民初44725号` |
| `case_structured_search` | 少数严格限定检索；用户明确表示只要、限于、必须满足特定案由、法院、地域、日期、文书类型等条件 | `只要广东 2021-2025 相邻关系纠纷判决书` |
| `case_semantic` | 默认类案入口；适用于开放式争议事实、裁判趋势，以及带普通地域/时间/案由等条件的类案问题 | `竞业限制违约金过高法院会不会调低` |

字段明细、易错边界和复查策略见 `references/query-recipes.md`。

---

## 输出格式

默认输出 Markdown 预览，不声称已生成外部附件。正式回答使用法律研究语境下自然的检索结果说明；所有用户可见文本（含过程叙述）的表述约束见「对用户可见信息的约束」一节。

回答开头或结尾包含简短提示：

```text
以下检索和分析由 AI 辅助生成，仅供法律研究和业务参考，不构成正式法律意见；具体案件或交易应结合完整事实和有效证据复核。
```

检索结果状态使用固定表达。正式回答避免使用产品内部技术判断词。

- `已核验到指定案例`：用户案号与返回案号完全一致。
- `检索到指定来源案例`：案例来源符合指导性案例、参考案例、公报案例、典型案例或人民法院案例库等要求。
- `检索到符合条件的案例`：案由、法院、地域、日期、审级、文书类型等关键条件基本一致。
- `检索到类案材料`：开放式事实或争议焦点查到同类案例，可用于观察裁判倾向。
- `检索到可供参考的相关案例`：与用户问题局部相关、事实类似或裁判观点可参考，但不是指定案例或指定来源案例。
- `未检索到指定案例或指定来源案例`：精确查询未找到一致对象。

禁止使用绝对化法律结论，不把裁判倾向写成固定结果。涉及地区差异、审级差异、裁判时间差异或样本不足时，写明不确定性。

---

## 选择规则

- 明确案号：`case_docket_exact`。
- 指定最高法发布、人民法院案例库、指导性案例、参考案例、公报案例或典型案例等官方来源：当前使用 `case_semantic`，并在 `searchContent` 中原样保留来源、案例编号和入库编号。
- 明确使用"只要、限于、必须、排除其他"等表达限定条件：`case_structured_search`。
- 普通类案趋势、开放式争议事实、普通地域/时间/案由条件：`case_semantic`。
- 同时出现案号和类案趋势时，先用 `case_docket_exact` 查目标案例，再用 `case_semantic` 查同类案例；输出时分为"目标案例"和"同类案例"。
- 不确定是否足够精确时，使用 `case_semantic`。

---

## 随附业务字段

核心规则：字段抽不准就省略；非语义 scene 缺少必填字段时改用 `case_semantic`；`case_semantic` 不传 `structuredFields`。

| scene | searchContent | structuredFields |
| --- | --- | --- |
| `case_docket_exact` | 可省略 | 必填 `docketNo`；可选 `caseType` |
| `case_structured_search` | 可省略 | 必填 `hardFilters: true`，并至少提供一个受支持的硬条件字段；用户明确要求裁判分析必须讨论某一问题时，可以使用 `case_structured_search` 并传 `reasoningKeyword`；用户明确要求案例必须援引某一法条时，传 `citedLaw`。 |
| `case_semantic` | 必填 | 不传 |

日期统一使用 `YYYY-MM-DD`。`caseType` 仅支持 `ptal`（普通案例）或 `qwal`（权威案例）。构造调用时不要传 `caseNo`、`top_k` 或其他未定义字段。

### MCP 调用示例

精确案号查询（可省略 `searchContent`）：

```text
searchLawCase(retrievalScene="case_docket_exact",
              structuredFields={docketNo: "（2021）粤0104民初44725号", caseType: "ptal"})
```

严格限定条件查询：

```text
searchLawCase(retrievalScene="case_structured_search",
              structuredFields={hardFilters: true, province: "广东", dateStart: "2021-01-01",
                                dateEnd: "2025-12-31", causeOfAction: "相邻关系纠纷", documentType: "判决书"})
```

相似案例检索：

```text
searchLawCase(searchContent="竞业限制违约金过高，法院是否会酌情调低", retrievalScene="case_semantic")
```

---

## 检索与输出要点

- 区分目标案例、指定官方案例来源、严格限定条件和普通类案趋势；多个任务分开输出。
- 保留案号、法院名、案由、裁判日期、案例来源、入库编号等定位信息，不压成短关键词。
- `searchContent` 只改表达方式，不新增事实、法院、案由、案号或裁判结论。
- 用户指定裁判结果方向时，必须核对返回案例结果；方向不同的只作相反或例外案例。
- 法律判断仅供参考，重要事项提示咨询专业律师。
- 更细的弱结果诊断、条件放宽顺序、相关案例展示规则见 `references/query-recipes.md`。

---

## 案例类型与参考强度

输出案例时，必须标注案例类型，参考强度依次递减：

| 类型              | 参考强度 | 说明                           |
| ----------------- | -------- | ------------------------------ |
| 指导性案例        | 高（★★★） | 最高法院发布，具有准约束力     |
| 参考案例/公报案例 | 较高（★★） | 参考价值高                     |
| 典型案例          | 较高（★★） | 最高法院或高院发布，参考价值高 |
| 裁判文书          | 一般（★） | 普通判决，仅说明裁判趋势       |

---

## Read Next

- 检索场景选择策略：`references/query-recipes.md`
- 输出格式规范：`references/output-template.md`
