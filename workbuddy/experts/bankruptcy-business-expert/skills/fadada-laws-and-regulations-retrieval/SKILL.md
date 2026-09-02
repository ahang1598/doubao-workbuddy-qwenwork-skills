---
name: 法大大法律法规检索
name_en: fadada-laws-and-regulations-retrieval
description: 检索中国大陆法律法规、行政法规、地方性法规、司法解释及条文内容的专用 skill，通过 MCP 工具 searchLawInfo 进行检索。当用户提到查法条、查法律、找法规、查规定、找司法解释、这条法律怎么说、有没有相关法律规定、查某部法律的具体条文、核验法规时效性等任务时，必须触发此 skill。即使用户只说"这个问题有法律依据吗"或"帮我找找相关规定"，也应触发此 skill 进行法规检索。如果用户同时需要法规和案例，先运行本 skill，再运行 fadada-legal-case-search。
---

<!-- Copyright © 深圳市法大大网络科技有限公司 版权所有 | Author: 法大大法律AI产品线 -->

# 法律法规检索 Skill

## 概述

用于中国大陆法律规范检索，覆盖法律法规、行政法规、地方性法规、司法解释及法条内容。

核心任务：判断检索场景，生成法律检索表达，保留法规名、条号、发文字号、日期和时效要求等定位信息。

---

## 对用户可见信息的约束

以下约束覆盖所有用户可见文本，包括过程叙述、进度说明、思考过程和最终回答，无一例外。

- 不出现内部标识符：scene 名（`law_article_exact`、`law_statute_exact`、`law_semantic` 等）、工具参数名（`retrievalScene`、`searchContent`、`structuredFields` 等）、MCP 工具名。
- 过程叙述只描述业务动作，不描述技术步骤。说"正在检索相关法律法规"，不说"先调用 searchLawInfo"或"使用 law_semantic 检索"。
- 内部概念对用户统一使用业务说法：

| 内部概念 | 对用户表述 |
| --- | --- |
| `law_article_exact` | 按法规名和条号核对指定法条 |
| `law_statute_exact` | 定位指定法规或规范性文件 |
| `law_semantic` | 检索相关法律依据 |
| 调用检索工具 | 正在检索法律法规库 |
| 复查、二次检索 | 补充检索、换一组条件再查一次 |

- 上表未覆盖的内部概念，转换为法律研究语境下的自然表达；禁止直接向用户抛出英文标识符或技术名词。

---

## 运行环境说明

本 skill 通过 MCP 工具 `searchLawInfo` 检索法律法规。工具由已配置的 MCP Server 提供，无需手动配置认证，直接调用工具即可。

调用契约：

- `searchContent`：检索内容，关键词或自然语言描述；精确法条/法规定位时可省略。
- `retrievalScene`：检索场景，取值 `law_article_exact`、`law_statute_exact`、`law_semantic`。
- `structuredFields`：结构化检索字段，精确法条/法规定位时使用。
- `searchContent` 与 `retrievalScene` 至少提供其一。

---

## 工作流程

1. 判断检索方式：精确法条核验、精确法规定位、开放式法律依据三选一（scene 分别取 `law_article_exact`、`law_statute_exact`、`law_semantic`）；不确定时按开放式处理（`law_semantic`）。
2. 改写检索表达：把口语问题改写成适合法律检索的完整自然语言表达（即 `searchContent`）；法规名、条号、发文字号、日期和时效要求原样保留。
3. 确定随附字段：非语义检索只给已确定的 `structuredFields`；必填字段不够时改用 `law_semantic`，不编造字段。
4. 构造调用：确定 `searchContent`、`retrievalScene` 与 `structuredFields` 的取值。
5. 执行检索：调用 MCP 工具 `searchLawInfo`。语义检索传入 `searchContent` 与 `retrievalScene`；精确检索传入 `retrievalScene` 与 `structuredFields`（`searchContent` 可省略）。
6. 校验并输出：精确法条核对法规名、条号和时效；精确法规核对法规名或发文字号。完全一致写成指定对象命中，相近结果只作相关依据。
7. 控制复查：默认一次检索；只有指定法条/法规未命中或版本时效无法核清时，最多再检索一次。开放式问题不要为了增加材料反复检索。

---

## 业务场景枚举

选择下列 scene：

| scene | 适用场景 | 示例 |
| --- | --- | --- |
| `law_article_exact` | 已知法规名或司法解释名，并指定条号 | `民诉法解释第二十七条` |
| `law_statute_exact` | 定位整部法规、司法解释、规范性文件 | `人社部关于企业实施竞业限制合规指引的通知` |
| `law_semantic` | 开放式法律依据、法律规则、适用边界、合规判断 | `竞业限制补偿金没约定还能主张吗` |

字段明细、易错边界和复查策略见 `references/query-recipes.md`。

---

## 输出格式

默认输出 Markdown 预览，不声称已生成外部附件。正式回答使用法律研究语境下自然的检索结果说明；所有用户可见文本（含过程叙述）的表述约束见「对用户可见信息的约束」一节。

回答开头或结尾包含简短提示：

```text
以下检索和分析由 AI 辅助生成，仅供法律研究和业务参考，不构成正式法律意见；具体案件或交易应结合完整事实和有效证据复核。
```

检索结果状态使用固定表达。正式回答避免使用产品内部技术判断词。

- `已核验到指定法条`：法规名称、条号、时效要求均一致。
- `已定位到指定规范`：法规、司法解释、规范性文件名称或发文字号一致。
- `检索到相关法律依据`：开放式问题查到可支撑分析的依据，不表示唯一答案。
- `检索到补充参考依据`：与用户问题局部相关、相邻、类似或可辅助理解，但不是指定对象。
- `未检索到指定法条或规范`：精确查询未找到一致对象。

禁止使用绝对化法律结论，不对胜败、合规或风险作无条件承诺。涉及争议、地方差异、历史版本或时效不明时，写明不确定性。

---

## 选择规则

- 法规名 + 条号：`law_article_exact`。
- 已知法规、司法解释或规范性文件名称并要求定位整个文件：`law_statute_exact`。
- 只有发文字号、无法确定文件名称时：使用 `law_semantic`，并在 `searchContent` 中原样保留发文字号。
- 法律依据、法律规则、适用边界、事实评价，或"某部法中关于某个主题/概念的规定"：`law_semantic`。
- 只有"第几条"但无法确定法规对象时，使用 `law_semantic`，并在回答中说明需要结合上下文确认法规对象。
- 不确定是否构成精确查询时，使用 `law_semantic`。

---

## 随附业务字段

核心规则：字段抽不准就省略；非语义 scene 缺少必填字段时改用 `law_semantic`；`law_semantic` 不传 `structuredFields`。

| scene | searchContent | structuredFields |
| --- | --- | --- |
| `law_article_exact` | 可省略 | 必填 `lawTitle`、`articleNo`；可选 `referDate` |
| `law_statute_exact` | 可省略 | 必填 `lawTitle`；可选 `effectiveness`、`effectLevel`、`region` |
| `law_semantic` | 必填 | 不传 |

`documentNo` 和 `issuingAuthority` 仅保留在 `searchContent` 中并用于结果核验，不传入 `structuredFields`。

日期统一使用 `YYYY-MM-DD`。构造调用时不要传 `top_k` 或其他未定义字段。

### MCP 调用示例

精确法条查询（可省略 `searchContent`）：

```text
searchLawInfo(retrievalScene="law_article_exact",
              structuredFields={lawTitle: "中华人民共和国公司法", articleNo: "第二十三条"})
```

按法规名称和效力状态定位规范：

```text
searchLawInfo(retrievalScene="law_statute_exact",
              structuredFields={lawTitle: "中华人民共和国公司法", effectiveness: "现行有效", effectLevel: "法律"})
```

开放式法律依据检索：

```text
searchLawInfo(searchContent="竞业限制补偿金未约定时劳动者能否主张补偿", retrievalScene="law_semantic")
```

---

## 检索与输出要点

- 保留定位信息，不把法规名、条号、发文字号、日期或时效要求改写成短关键词。
- `searchContent` 只改表达方式，不新增事实、法规名称、条号或结论。
- 区分依据层级，不把低层级、地方性文件、草案或征求意见稿写成全国现行规则。
- 法律判断仅供参考，重要事项提示咨询专业律师。
- 更细的弱结果诊断、版本复核、相关依据展示规则见 `references/query-recipes.md`。

---

## Read Next

- 检索场景选择策略：`references/query-recipes.md`
- 输出格式规范：`references/output-template.md`
