# 文献验真方法说明

本文件说明 `make prepare` 阶段文献验真的方法与判定标准。验真由
`scripts/verify_literature.py` 执行，`scripts/check_prepare.py` 编排调用；
本文件只讲**怎么准备候选文献、验真查什么、什么样的文献算通过**，不含流程门控
（门控在 Makefile 与脚本）。

## 验真在 workflow 里的位置

- 候选文献写入 `.workflow/candidates.json`（结构见下）。
- `make prepare` 调 `verify_literature.py` 联网核验（Crossref/OpenAlex/Semantic
  Scholar 三源），产出 `.workflow/verified_refs.json`。
- 只有通过真实性与质量门的 A/B 级文献进入 `verified_refs.json` 的
  `core_literature`；其余进 `rejected_literature` 并保留失败原因。
- `OFFLINE=1`只适用于`needs_citation=no`的任务。需要引用时离线或联网降级会阻断prepare，不生成可供正文使用的`verified_refs.json`。

本模块的输出**不是**正式论文的 References。`verified_refs.json`、`code_trace`、
`quality_basis`、`rejected_literature` 只是内部验真留痕；最终论文的 References
必须回到 `reference/apa7-format-guide.md` 等按体例重排，且正文与 References 里
**不得残留**这些验真中间字段（check_draft.py 会拦）。

## READ-GATE（开始前必须能回答）

1. 写作前检索与筛选步骤形成的候选文献池在哪里？
2. 每条候选是否至少含标题、第一作者、DOI 或 URL，以及期刊/会议/机构来源？
3. 哪些来源会因为缺 URL、仅 metadata、无权威凭据或 DOI 不匹配被拒收？

答不出，先在 `make prepare` 之前按 `literature-review-guide.md` 的范围、检索和筛选规则补齐候选池；不要先写综述正文。本模块不自行扩展主题或替换候选池。

## 验真主流程

1. 接收写作前检索步骤形成的候选文献池：不扩大或替换已经确定的范围。
2. 真实性核验：搜完整标题或关键片段；第一作者约束匹配；DOI 反查标题一致；
   核对摘要/可访问全文中的引述准确性。
3. 正向质量凭据筛选：记录 JCR、中科院分区、IF、顶刊顶会、高引经典、官方
   seminar、权威机构来源等凭据。
4. 只把通过 A/B 级核心凭据的文献留入 `core_literature`。

## 候选文献 JSON（candidates.json）

```json
{
  "references": [
    {
      "id": "short-id",
      "title": "Full article/report title",
      "first_author": "FamilyName",
      "doi": "10.xxxx/xxxxx",
      "year": 2024,
      "url": "https://publisher-or-official-url.example/item",
      "container_title": "Journal or conference name",
      "source_type": "journal_article",
      "key_fragments": ["distinctive title or abstract phrase"],
      "quoted_claims": [
        {"id": "q1", "quote": "Exact quoted sentence to verify", "context": "abstract_or_fulltext"}
      ]
    }
  ]
}
```

> **🔴 严重警告**
> 1. `quoted_claims` 的 `quote` 必须从目标文献原文或摘要**实际提取**。
> 2. **绝对禁止**把上面 JSON 示例里的占位符文本直接复制进真实输入；无法提取真实
>    原句就留空或让该文献落入 rejected。
> 3. `quoted_claims`、`key_fragments` 只用于验真中间环节；生成正式 References 时
>    必须彻底剥离这些字段。

样例见 `scripts/references.sample.json`。

## core_literature 通过标准

每条进入 `core_literature` 的文献必须满足：

- 有 `url`；`read_status` 不为 `metadata_only`。
- `source_quality` 为 `A` 或 `B`。
- 有 `authority_signal` 与 `quality_basis`。
- `title_author_match` 为 `pass`，`doi_match` 不为 `fail`。
- `reverification_required` 为 `no`。

任一出现缺 URL、仅 metadata、无权威凭据、DOI 不匹配、标题/作者不匹配，只能进
`rejected_literature` 并触发重新验真。

## 质量凭据登记

JCR、中科院分区和影响因子通常没有稳定开放 API，通过
`scripts/quality-registry.sample.json` 的结构维护本地凭据登记表。脚本用 ISSN、
期刊名、会议名和权威机构域名匹配正向质量凭据；引用量、高引经典和 DOI/标题
真实性优先由 Crossref、OpenAlex 和 Semantic Scholar API 核验。
