# 多源检索与日期核验

## 目录

- 检索顺序
- 查询构造
- 结构化 URL 常规补充
- 按需预印本
- 医学资讯
- 日期、回源与去重

## 检索顺序

每期按三阶段执行：

1. **General Search + Scholar Search 并行优先**：先发现最近正式发表的研究；General 同时负责中文和国际医学资讯、指南监管与机构动态。
2. **结构化 URL 常规补充**：General/Scholar 首批完成后，无论数量是否已足，都尽量并行调用 PubMed、Europe PMC MED、Crossref 的参数化 URL，补充高质量正式论文与结构化元数据。
3. **预印本按需补充**：只有正式发表研究仍不充足时才检索预印本。预印本不是每期必跑，也不是判断检索完成的必要来源线。

来源范围偏好只用于查询加权、补充和排序，不是白名单、硬准入或逐站完成清单。三类结构化入口均尽量尝试，但单个入口失败不阻塞完成。合并后按相关性、研究设计质量、来源可信度、证据成熟度和时效性统一择优。窗口内只有少量达到质量底线的研究时，有多少呈现多少；没有合格论文时宁可少写或不写。已有约 5–6 篇较强候选时提高纳入门槛，剔除边缘相关、低信息量或来源较弱的条目。不把篇数作为硬完成门，也不为凑数保留垃圾文献。

论文选择遵循“宁缺勿滥”。明确命中预警名单、疑似掠夺性/劫持期刊、期刊身份或同行评议机制不透明、来源信誉明显不足的候选不进入报告。开放获取（OA）只是获取模式，不等同于低质量：不得仅凭 OA 标签排除正规期刊，也不得把“可付费发表”当作质量证明。无法判断期刊质量且研究设计与来源支持又偏弱时，宁可不纳入。

检索过程中把候选保留在当前上下文，完成全部可用通道、筛选和去重后，只写一次最终 `report-data.json`。不要生成 `batch-general-01.json`、`evidence-ledger.json` 或其他逐批快照；不要把完整 JSON 再包成带反斜杠的字符串。

### 用户主动检索的一周窗口不足

仅在**非定时任务触发**且用户明确要求“一周/近 7 天”时使用：

1. 先按用户窗口完成 General、Scholar、结构化 URL 与必要的预印本检索，不因首批结果少而过早放宽日期；
2. 若严格窗口内仍缺少足够有效、权威的信息，主动扩大到近 30 天；领域更新很慢且仍不足时，可视情况扩大到近 90 天；
3. 扩大窗口是为了补充近期背景，不改变用户原始问题。筛选质量标准不因扩大窗口而降低，也不为凑数纳入低质量内容；
4. 在报告开头和聊天摘要中用一句话说明，例如：“近 7 天仅检出 2 条可核验进展，为提高参考价值，另补充近 30 天内 4 条高质量进展。”正文或画板用清晰标签区分“近 7 天新增”和“扩大窗口补充”。

定时任务以 `last_success_at-overlap` 后的真实增量为准，不套用本规则，也不把旧内容重复包装为本期更新。

## 查询构造

先建立概念簇：

- 疾病/主题的中英文、缩写和常用同义词；
- 干预、标志物、研究对象、结局或用户重点实体；
- 明确的 `start_date`、`end_date` 及对应 `YYYY年M月`、`Month YYYY`。

第一批并行执行：

- `general_search`：宽主题 + 时间词；重点概念各自拆成短查询。搜论文时可用 `site:pubmed.ncbi.nlm.nih.gov`、期刊或出版商域名，但不要求每个站点都有结果；
- `scholar_search`：宽主题和重点概念，均传 `publish_start_date`、`publish_end_date`（`YYYY-MM-DD`）；
- `general_search` 资讯：中英文宽发现和相关信源定向发现。

不要把全部概念塞进一条过窄的 `AND` 式。首次零结果时保留日期窗，减少一个概念或换同义词扩展一次。General 论文查询可写成：

```text
site:pubmed.ncbi.nlm.nih.gov Alzheimer blood biomarker July 2026
site:nature.com Alzheimer p-tau217 July 2026
Alzheimer blood biomarker study July 2026
```

检索结果足以支持候选时直接筛选，不为了获取 PMID、DOI 或期刊名逐篇打开页面。PMID、DOI 不是展示或纳入必填项。

### 从研究报道反查论文

General Search 命中医学媒体、大学/医院新闻稿、学会会议报道或企业稿件时，不止停留在报道页：

1. 从标题和摘要提取论文原题、DOI、PMID、第一作者、期刊、试验/队列简称等稳定线索；
2. 优先用 General/Scholar 批量搜索精确题名或 DOI；必要时使用 `site:pubmed.ncbi.nlm.nih.gov`、Europe PMC/Crossref 精确查询，或直接构造可解析的 `https://doi.org/{DOI}`；
3. 找到论文后，将论文页、PubMed/Europe PMC、DOI 落地页或正式预印本页写为研究条目的 `source_url`；报道页可保留为 `discovery_source_url`；
4. 找不到对应论文时，该内容只能按有价值的“资讯/报道”处理，不能伪装成研究条目，也不能把报道中的二手表述升级为论文结论。

这一反查属于检索阶段的定向补充，不要求逐篇 `web.fetch` 全文。一个报道指向多篇论文时，只纳入能明确匹配题名、作者、DOI/PMID 或试验标识的论文。

## 结构化 URL 常规补充

第一阶段完成后，尽量并行尝试以下三个入口；不是只有“结果不足”才调用：

### PubMed 与 Europe PMC MED

```text
https://pubmed.ncbi.nlm.nih.gov/?term={pubmed_query}+AND+("{start}"[Date+-+Publication]:"{end}"[Date+-+Publication])&sort=date

https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={epmc_query}%20AND%20SRC:MED%20AND%20FIRST_PDATE:[{start}%20TO%20{end}]&format=json&pageSize=100&resultType=lite
```

PubMed `[dp]` 与 Europe PMC `SRC:MED/FIRST_PDATE` 分别使用各自语法，不复制同一原始查询串。高价值题录需要摘要时，把多个 PMID 合并为一次 Europe PMC `resultType=core` 精确查询；不要逐篇补摘要。

### Crossref Online First

```text
https://api.crossref.org/works?query.bibliographic={crossref_cluster}&filter=type:journal-article,from-online-pub-date:{start},until-online-pub-date:{end}&rows=100&select=DOI,title,published-online,URL,type,container-title,publisher,abstract
```

先查宽主题；仅对合并结果仍存在的重点缺口补概念簇。请求同时包含 `container-title` 和 `abstract`；返回非空 `abstract` 时保存为 `support_excerpt` 并标记 `support_level=abstract`。

PubMed、Europe PMC MED、Crossref 尽量一次并行尝试。任一端点不可用、返回 0 条或解析失败时直接跳过；不要为补齐“三路成功”循环重试。只有关键概念明显缺口时，才在可用端点缩短概念簇扩展一次。端点返回的大 `total-results` 只说明匹配总量，不要求读取全部结果；按当前窗口、相关性和可见页筛选。

PubMed、Europe PMC、Crossref 是数据库或检索来源，不是期刊。把明确返回的 `journalTitle`、`fullJournalName`、`container-title` 写入 `journal_name`，把检索入口写入 `record_source`；没有刊名时保持为空并显示“来源：PubMed/Europe PMC/Crossref”，不得写“期刊：PubMed/Europe PMC”，也不能写“期刊：Crossref”。

## 期刊质量与可选指标

对入选论文尽量补充期刊质量信息，但不把补齐指标变成完成门：

- 影响因子只能写明确可核对的 Journal Impact Factor，并附年份，如 `journal_impact_factor=12.3`、`journal_metric_year=2025`、`journal_metric_source=JCR/期刊官方页`；
- 分区必须写明体系和年份，如 `journal_quartile=JCR Q1（2025）` 或 `中科院医学 2 区（2025）`；不同体系不能混写；
- CiteScore、SJR 等只能按本名展示，不能冒充影响因子；
- 搜索结果未明确给出、来源不可信或口径不清时全部省略，不根据期刊印象、过往年份或模型记忆猜测；
- 先按期刊名去重后做少量批量/定向查询，不为每篇论文重复查一次，也不因缺少指标排除本来质量明确的论文。

## 按需预印本

只有第一阶段和结构化常规补充后，正式发表研究仍无法覆盖主问题或重点话题时才执行。可使用：

```text
site:medrxiv.org {topic} {Month YYYY}
site:biorxiv.org {topic} {Month YYYY}
site:researchsquare.com {topic} {Month YYYY}
site:preprints.org {topic} {Month YYYY}
```

按领域补 SSRN、arXiv、OSF，或使用：

```text
https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={ppr_query}%20AND%20SRC:PPR%20AND%20FIRST_PDATE:[{start}%20TO%20{end}]&format=json&pageSize=100&resultType=lite
```

已发表研究充足时跳过预印本，不把“未搜预印本”写成检索不完整。纳入的预印本必须标“未经同行评议”；旧预印本本期发布新版本时标为版本更新，后续正式发表时合并进同一事件链。

## 医学资讯

General 资讯发现同时覆盖中文和英文结果。中文使用 `YYYY年M月`，英文使用 `Month YYYY`；跨月分别执行两个自然月，不加具体日号。先做宽查询：

```text
临床实践 / 专家动态：{中文主题} {YYYY年M月} 临床 进展；{中文主题} {YYYY年M月} 专家 访谈
医学资讯 / 学会会议：{中文主题} {YYYY年M月} 医学资讯；{中文主题} {YYYY年M月} 学会 会议
机构发布 / 临床应用：{中文主题或重点话题} {YYYY年M月} 医院 检测 应用；{中文主题} {YYYY年M月} 研究机构 发布
指南 / 共识：{中文主题} {YYYY年M月} 指南 共识；{中文主题} {YYYY年M月} 推荐 更新
监管 / 安全：{中文主题或产品通用名} {YYYY年M月} 监管 批准；{产品通用名} {YYYY年M月} 安全警示 召回
英文临床 / 研究资讯：{英文主题} {Month YYYY} clinical research news
英文政策 / 产业资讯：{英文主题或产品通用名} {Month YYYY} policy biotech industry
```

再从相关分组选择中外信源，将**一个信源名**追加到一条查询中：

| 资讯方向 | 中文建议信源 | 国际建议信源 |
|---|---|---|
| 临床医学进展 / 临床研究新闻 | 医脉通、丁香园、梅斯医学、壹生 | Medscape、Healio、Reuters |
| 政策与医疗体系 | 健康报、健康界、赛柏蓝、健识局 | Reuters、Healthcare Dive、STAT |
| 医疗 AI、数字医疗 | 动脉网、健识局 | MobiHealthNews、Healthcare Dive、STAT |
| 创新药、生物医药与产业 | 医药魔方、动脉网、健识局 | STAT、Endpoints、Fierce Biotech、Fierce Pharma、BioPharma Dive |

这些是优先发现信源，不是白名单，也不取代学会、监管机关、医院、研究机构、会议或企业的原始发布。遇到更适合当前专科的一手来源或高质量专业媒体可以纳入。窗口内有多条真实临床资讯时不要默认只截取 1–2 条；按相关性、来源质量和临床价值去重择优。

需要定位官方页时再回搜：

```text
site:{学会/会议/研究机构官方域名} {主题或事件核心词}
site:{指南发布机构官方域名} {文件名核心词} filetype:pdf
site:{监管机构官方域名} {产品通用名} {批准/授权/警示/召回}
```

不知道官方域名时先搜“机构全称 官网”。只命中二次报道时，只要网页日期、来源和本期报道动作清楚，也可进入资讯章；涉及疗效、安全性、诊断性能或推荐强度时仍需论文、指南或监管原文支持，不能单独依赖中文资讯。

## 日期、回源与去重

先用标题、搜索摘要、Scholar 元数据和结构化题录完成日期与主题筛选。不要逐篇读取论文全文，也不得为了确认日期或补期刊名把全部论文再逐篇 `web.fetch`；只选择性处理少量最终冲突项。

每个候选记录 `source_url`、`source_page_date`、`underlying_action_date`、`delta_date`、`delta_statement`：

- 研究章只纳入首次公开 `Published/Online/posted` 日期在窗口内的条目；PMID、DOI 或预印本 DOI 不是准入条件；
- 指南/共识/监管章只纳入原文或官方动作日在窗口内的条目；
- 网页在窗口内二次报道更早动作时可进资讯章，`source_page_date/delta_date` 取报道日，标题或紧邻标题的灰字元信息写“二次报道”，底层原日期另列；
- 标题中的动词必须与 `delta_date` 对应。规范 7 月 7 日发表、媒体 7 月 22 日报道时，只能写“媒体报道 7 月 7 日发表的规范”，不得写“7 月 22 日规范发布”；7 月 13 日出现的另一篇转载不能替代原始题录日期；
- 搜索片段出现“将/拟/预计/预告”时保留未来时态，不改写成已经举行或完成；
- 非官方页面声称获批、授权或发布安全动作，但没有官方页面或稳定编号支持时，标为“官方状态待核验”；
- 底层日期无法确认时写“底层动作原日期：未核验”，不猜日期、动作等级或医学结论。

同批结果优先以 DOI、PMID、NCT、指南版本、监管编号或 canonical URL 合并明显重复项；没有稳定 ID 时参考来源链接、标准化题名、年份和第一作者。定时运行可结合 `seen_source_keys` 与上一期报告尽量减少重复，但历史状态缺失不阻塞；预印本正式发表、指南修订、试验状态变化、勘误、撤稿或安全警示可作为真实增量再次呈现。

只要 General/Scholar 或结构化补充至少有一条可用检索路径，并已对主问题做合理扩展，即可根据结果说明“无更新”；不要求固定来源全部有结果。所有主要入口都不可用时写“本期检索未完整，暂不能判断是否无更新”，并保留旧 `last_success_at`。
