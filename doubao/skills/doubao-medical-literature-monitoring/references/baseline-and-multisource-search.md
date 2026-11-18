# 多源检索与日期核验

## 目录

- 检索顺序
- 查询构造
- PubMed MCP 优先与结构化入口常规补充
- 临床试验注册专线
- 按需预印本
- 医学资讯
- 日期、回源与去重

## 检索顺序

每期按三阶段执行：

1. **General Search + Scholar Search 并行优先**：先发现最近正式发表的研究；General 同时负责中文和国际医学资讯、指南监管与机构动态。
2. **PubMed MCP 优先与结构化入口常规补充**：General/Scholar 首批完成后，无论数量是否已足，都运行 PubMed、Europe PMC MED、Crossref 补充通道。PubMed 优先使用检索前确认可调用的 `pubmed-medical-literature` MCP；未检测到可调用 MCP 时使用参数化 PubMed URL。Europe PMC 与 Crossref 继续使用参数化 URL。用户明确关注最新临床试验、注册、招募、状态或结果发布时，同批增加 ClinicalTrials.gov 专线。
3. **预印本按需补充**：只有正式发表研究仍不充足时才检索预印本。预印本不是每期必跑，也不是判断检索完成的必要来源线。

来源范围偏好只用于查询加权、补充和排序，不是白名单、硬准入或逐站完成清单。三类结构化入口均尽量尝试，但单个入口失败不阻塞完成。合并后按相关性、研究设计质量、来源可信度、证据成熟度和时效性统一择优。窗口内只有少量达到质量底线的研究时，有多少呈现多少；没有合格论文时宁可少写或不写。已有约 5–6 篇较强候选时提高纳入门槛，剔除边缘相关、低信息量或来源较弱的条目。不把篇数作为硬完成门，也不为凑数保留垃圾文献。

每期在执行任何检索前，只查看一次当前会话明确暴露的已加载 Skill、MCP 与可用工具清单。不要用 Bash、`find`、`rg` 或类似方法扫描用户本地/隐藏 Skill 目录，也不要试装连接器或猜测工具名。只有明确存在 `pubmed-medical-literature` 且其 PubMed MCP 工具可调用时，才把本轮 PubMed 通道标记为 MCP 可用。只有 Skill 名但没有可调用 MCP 时，按不可用处理并直接使用 PubMed URL fallback；不要声称连接器已经激活。

该检查只决定 PubMed 一条通道的执行方式，不改变总顺序，也不取代 General、Scholar、Europe PMC、Crossref 或按需启用的 ClinicalTrials.gov。PubMed MCP 成功返回后不重复拼接 PubMed URL；若已明确可用的 MCP 单次调用失败，可回退一次 PubMed URL 继续，但不循环重试，也不把临时调用错误等同于“未激活”。

论文选择遵循“宁缺勿滥”。明确命中预警名单、疑似掠夺性/劫持期刊、期刊身份或同行评议机制不透明、来源信誉明显不足的候选不进入报告。开放获取（OA）只是获取模式，不等同于低质量：不得仅凭 OA 标签排除正规期刊，也不得把“可付费发表”当作质量证明。无法判断期刊质量且研究设计与来源支持又偏弱时，宁可不纳入。

检索过程中把候选保留在当前上下文，完成全部可用通道、筛选和去重后写入一次 `report-data.json`，随后只允许期刊分区脚本原地富化一次。不要生成第二份报告数据、`batch-general-01.json`、`evidence-ledger.json` 或其他逐批快照；不要把完整 JSON 再包成带反斜杠的字符串。

### 关键或重大研究模式

用户要求“关键研究、重大研究、重磅研究、里程碑更新”时，不按普通进展报告的自适应数量补位：

- 优先多中心随机研究、大型前瞻性队列、改变指南或监管状态的研究、高质量系统综述/Meta、重要验证研究，以及权威期刊正式发表且结果信息完整的研究；
- 排除边缘相关、小样本低信息量、仅题录、会议标题空壳、方法学明显薄弱、预警/疑似掠夺性或来源身份不清的论文；
- 期刊分区是权威性辅助信号，不替代对研究设计、对象、终点、效应与局限的判断；命中较高分区不自动等于重大研究，未命中本地索引也不自动等于低质量；
- 严格窗口及必要扩展窗口内仍没有合格研究时，保留空结果并向用户解释：“当前核心期刊未检索到符合条件的有效更新。”不要降级塞入低质量论文。

### 用户主动检索的一周窗口不足

仅在**非定时任务触发**且用户明确要求“一周/近 7 天”时使用：

1. 先按用户窗口完成 General、Scholar、PubMed MCP/URL 条件通道、Europe PMC/Crossref 与必要的预印本检索，不因首批结果少而过早放宽日期；
2. 若严格窗口内仍缺少足够有效、权威的信息，主动扩大到近 30 天；领域更新很慢且仍不足时，可视情况扩大到近 90 天；
3. 扩大窗口是为了补充近期背景，不改变用户原始问题。筛选质量标准不因扩大窗口而降低，也不为凑数纳入低质量内容；
4. 在 `report-data.json` 顶层记录 `requested_date_range`、`included_date_range`、`window_expanded=true` 与 `window_note`；在报告开头、总览画板和聊天摘要明确显示原始窗口与实际纳入跨度，例如：“原始窗口 2026-07-24 至 2026-07-31 仅检出 2 条可核验进展；实际补充范围扩展至 2026-07-01，共纳入 4 条高质量进展。”正文或画板清晰区分“原始窗口新增”和“扩大窗口补充”。

定时任务按已确认订阅周期使用本次运行日前一个完整周期的真实时间范围：每周一次取近 1 周，每两周一次取近 2 周，每月一次取近 1 个日历月；运行时计算精确起止日期供检索接口与报告使用，但用户可见任务说明只写相对范围。定时任务不套用首期的 30 天或 90 天扩展规则，也不把旧内容重复包装为本期更新。

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

## PubMed MCP 优先与结构化入口常规补充

第一阶段完成后，尽量并行尝试 PubMed、Europe PMC MED、Crossref 三个论文入口；不是只有“结果不足”才调用。PubMed 入口使用检索前已经确定的条件路线，其他两路继续使用参数化 URL。

### PubMed 与 Europe PMC MED

若 `pubmed-medical-literature` 及其 PubMed MCP 在本轮开始时已确认可调用，PubMed 通道优先按该 Skill 的说明使用 MCP，并沿用相同日期窗口与概念簇；MCP 成功后不要重复请求下面的 PubMed URL。若本轮没有可调用 MCP，则直接使用下面的 PubMed 参数化 URL，不阻塞报告、不要求用户先安装。Europe PMC URL 两种情况下都照常执行。

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

PubMed 条件通道、Europe PMC MED、Crossref 尽量在同一补充阶段执行。任一入口不可用、返回 0 条或解析失败时直接跳过；不要为补齐“三路成功”循环重试。只有关键概念明显缺口时，才在可用入口缩短概念簇扩展一次。入口返回的大 `total-results` 只说明匹配总量，不要求读取全部结果；按当前窗口、相关性和可见页筛选。

PubMed、PubMed Central/PMC、Europe PMC、Crossref 是数据库、全文库或检索来源，不是期刊。无论 PubMed 结果来自 MCP 还是参数化 URL，`record_source` 都写 `PubMed`，不能把 `pubmed-medical-literature` 或 MCP 名称写成期刊。把真实期刊写入 `journal_name`。期刊字段按以下顺序批量补全：

1. Europe PMC `resultType=core` 的 `journalInfo.journal.title`，其次 `journalTitle`；
2. PubMed ESummary 的 `fulljournalname`，其次 `source` 期刊缩写；
3. Crossref 的 `container-title`；
4. 只有 PMCID 时，把最终候选的 PMCID/PMID 合并进一次 Europe PMC `resultType=core` 精确查询，而不是逐篇打开 PMC 页面。

可批量使用：

```text
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={comma_separated_pmids}&retmode=json

https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=({pmid_or_pmcid_list})&format=json&pageSize=100&resultType=core
```

只要结构化元数据返回真实刊名，用户可见报告必须显示该期刊，不得写“来源：PubMed Central”。确实未取得真实刊名时保持 `journal_name` 为空，显示“收录平台：PubMed Central”或实际 `record_source`；不得写“期刊：PubMed/Europe PMC/PubMed Central/Crossref”，也不能猜测刊名。

## 临床试验注册专线

仅在用户明确关注“最新临床试验、试验注册、招募、NCT、试验状态、试验结果发布”等意图时启用。它与三路论文补充同批执行，不等待论文不足后才调用。使用 ClinicalTrials.gov API v2：

```text
# 窗口内首次发布的干预性试验
https://clinicaltrials.gov/api/v2/studies?query.cond={topic}&query.term=AREA[StudyType]INTERVENTIONAL%20AND%20AREA[StudyFirstPostDate]RANGE[{start_mm/dd/yyyy},%20{end_mm/dd/yyyy}]&format=json&countTotal=true&pageSize=100&sort=StudyFirstPostDate:desc

# 窗口内首次发布结果的干预性试验
https://clinicaltrials.gov/api/v2/studies?query.cond={topic}&query.term=AREA[StudyType]INTERVENTIONAL%20AND%20AREA[HasResults]Y%20AND%20AREA[ResultsFirstPostDate]RANGE[{start_mm/dd/yyyy},%20{end_mm/dd/yyyy}]&format=json&countTotal=true&pageSize=100&sort=ResultsFirstPostDate:desc

# 窗口内发生注册记录更新的干预性试验
https://clinicaltrials.gov/api/v2/studies?query.cond={topic}&query.term=AREA[StudyType]INTERVENTIONAL%20AND%20AREA[LastUpdatePostDate]RANGE[{start_mm/dd/yyyy},%20{end_mm/dd/yyyy}]&format=json&countTotal=true&pageSize=100&sort=LastUpdatePostDate:desc
```

有明确干预物时可追加 `query.intr={drug_or_intervention}`。按 NCT 号合并三类结果，优先级通常为“首次发布结果 > 新注册 > 普通记录更新”：

- `StudyFirstPostDate` 对应 `trial_delta_type=new_registration`；
- `ResultsFirstPostDate` 对应 `trial_delta_type=results_first_posted`；
- `LastUpdatePostDate` 对应 `trial_delta_type=record_update`。

条目 `source_url` 固定指向 `https://clinicaltrials.gov/study/{NCTId}`，并记录 NCT 号、状态、可得分期、申办方、入组规模和与用户重点直接相关的主要终点。ClinicalTrials.gov 是注册平台，不是期刊；注册结果发布也不等同于同行评议论文。`LastUpdatePostDate` 只能表述为“试验记录更新”：没有跨期字段差异或记录文本支持时，不写具体状态变化，不写“公布结果”，也不据此推断疗效。仅联系人、地点或其他低价值行政更新不必进入报告。

## 期刊质量与可选指标

本 Skill 内置 2025 年中科院 1–4 区与北大核心索引；直接调用包内 `scripts/match-journal-rank.js` 做确定性本地匹配，不重新打开 Excel，也不联网逐篇查询分区。脚本从自身所在 Skill 包及邻近层级自动发现索引；不要复制脚本或索引到报告工作目录，不创建 `assets` 目录，不推导 `__dirname`、检查软链接或搬运文件。只有环境明确给出另一索引时才可选传 `--index <path>`。索引不可用时脚本返回 `journal_rank_index_unavailable`，此时直接省略分区继续成文，不排查路径或阻塞报告。

- 初筛重大研究时，可把去重后的真实期刊名批量传给 `node scripts/match-journal-rank.js --json '["NEJM","中华内科杂志"]'`，把返回分区作为来源权威性的辅助信号；
- 最终 `report-data.json` 写完后运行 `node scripts/match-journal-rank.js --report-json report-data.json --in-place`，脚本读取 `report_items[].journal_name`，仅对 exact/alias/高置信 fuzzy 命中写入 `journal_rank_2025`；
- 指南、共识、监管、资讯、预印本和没有真实 `journal_name` 的条目跳过；未命中或匹配歧义时留空，不显示占位符；
- 用户可见报告将非空 `journal_rank_2025` 展示为“期刊级别：中科院 X 区/北大核心（2025）”；它与研究设计质量是两个独立维度；
- 影响因子只能写明确可核对的 Journal Impact Factor，并附年份和来源；JCR 分区必须写清体系与年份。CiteScore、SJR 等只能按本名展示，不能冒充影响因子；
- 搜索结果未明确给出、来源不可信或口径不清的其他指标全部省略，不根据期刊印象、过往年份或模型记忆猜测，也不因缺少指标排除本来质量明确的论文。

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

同批结果优先以 DOI、PMID、NCT、指南版本、监管编号或 canonical URL 合并明显重复项；没有稳定 ID 时参考来源链接、标准化题名、年份和第一作者。定时运行不单独维护跨期去重清单，只在筛选和写作时避免重复明显的历史旧内容。预印本正式发表、指南修订、试验状态变化、勘误、撤稿或安全警示属于本期新内容，可再次呈现并说明较历史版本发生的变化。

只要 General/Scholar 或结构化补充至少有一条可用检索路径，并已对主问题做合理扩展，即可根据结果说明“无更新”；不要求固定来源全部有结果。所有主要入口都不可用时写“本期检索未完整，暂不能判断是否无更新”，并保留旧 `last_success_at`。
