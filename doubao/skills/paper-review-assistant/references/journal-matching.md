# 期刊匹配与外部事实核验

> **文件定位**：用于生成候选期刊、核验 IF/分区/审稿周期、记录来源并制定顺序投稿策略。
> **何时加载**：涉及目标期刊推荐、期刊指标、相似文章或投稿策略时必读。
> **更新时间**：2026-08-29。期刊指标会变化，本文件只保存检索协议和候选线索，不保存可直接复用的 IF、分区或审稿周期数值。

## 目录

- [一、事实类型与权威来源](#一事实类型与权威来源)
- [二、逐项核验流程](#二逐项核验流程)
- [三、来源与时间记录规范](#三来源与时间记录规范)
- [四、期刊匹配维度](#四期刊匹配维度)
- [五、候选期刊检索种子](#五候选期刊检索种子)
- [六、范例文章核验](#六范例文章核验)
- [七、冲突与失败降级](#七冲突与失败降级)
- [八、输出模板](#八输出模板)
- [九、投稿策略](#九投稿策略)
- [十、本文件来源记录](#十本文件来源记录)

## 一、事实类型与权威来源

外部期刊信息按字段分别核验，不能用一个来源替代全部字段。

| 字段 | 首选来源 | 记录要点 | 不可接受的替代 |
|---|---|---|---|
| 期刊名称、ISSN、出版社 | 期刊官网或出版社官网 | 正式刊名、ISSN、官网 URL | 仅凭搜索摘要或聚合站 |
| Aims & Scope、文章类型 | 期刊官网对应页面 | 页面标题、适用范围、查询日期 | 凭学科印象判断 |
| JIF、JCR 学科与分区 | Clarivate Journal Citation Reports | JCR 版本/指标年份、学科类别、JIF、quartile | 把 CiteScore/SJR 当作 JIF/JCR 分区 |
| 中科院分区 | 中国科学院文献情报中心期刊分区表 | 发布年份、大类/小类、分区、是否 Top | 用第三方转载表替代官方记录 |
| CiteScore、Scopus 分位 | Scopus Sources | 指标年份、类别、percentile/quartile | 与 JCR 指标混写 |
| 首轮决定/同行评审/接收周期 | 期刊或出版社官方 metrics 页面 | 指标定义、统计年份、均值/中位数、是否含 desk reject | 论坛经验或投稿者个案 |
| 录用率 | 期刊或出版社官方 metrics 页面 | 统计时间和样本口径 | 非官方估算 |
| 投稿格式与字数 | 最新作者指南 | 文章类型、正文/摘要字数、更新日期 | 旧版模板或二手博客 |

Clarivate 明确把 JCR 描述为给定时点的年度报告；不能用 Web of Science 的动态数据自行复算并声称等同 JCR。JIF 也不能单独决定期刊质量或论文匹配度。

## 二、逐项核验流程

### 2.1 先确认期刊身份

1. 打开出版社或期刊官网。
2. 核对正式刊名、ISSN、出版社和官网域名。
3. 遇到同名刊、改名刊或镜像站时，以出版社页面和 ISSN 为准。
4. 找不到官方页面时，将期刊身份标为 `[待核验]`，不继续填指标。

### 2.2 核验范围与格式

读取 Aims & Scope、article types、author guidelines 和近三年目录，记录：

- 研究主题是否在明确范围内
- 论文方法与文章类型是否有近期发表先例
- 字数、摘要、匿名化、数据共享、注册报告等要求
- 页面 URL 与查询日期

“近三年常发某主题”属于可检验结论，应给出检索式和至少两篇代表文章；没有结果时不能写“偏好”或“拒绝”。

### 2.3 核验 IF 与 JCR 分区

1. 在 Clarivate JCR 中按刊名或 ISSN 查找。
2. 记录 JCR 版本或指标年份、JIF、学科类别和该类别 quartile。
3. 同一期刊属于多个学科时逐类列出，不能只挑最高分区。
4. 无 JCR 权限、页面不可访问或年份不清时，写 `[待核验]`。
5. 第三方页面可用作定位线索，但不能把其数值写成已核验 JCR 数据。

### 2.4 核验中科院分区

1. 在中国科学院文献情报中心期刊分区表官方平台按 ISSN 或刊名查询。
2. 记录分区表发布年份、大类/小类和查询日期。
3. JCR 分区与中科院分区是不同体系，必须分列。
4. 官方站当前说明自 2026 年起不再更新与发布期刊分区表；因此不得虚构“2026 中科院分区”。需要使用历史最新版本时，明确写出发布年份，并以官方可访问结果为准。
5. 若官方数据因权限或可访问性无法核验，写 `[待核验]`，不要引用公开转载表替代。

### 2.5 核验审稿周期与录用率

优先打开该期刊官网的 metrics、journal insights 或 overview 页面。逐项辨别：

- time to first decision 是否包含 desk reject
- peer review time 与 first decision 是否为不同指标
- submission to acceptance 与 acceptance to publication 是否分开
- 数值是均值还是中位数
- 数据对应哪个完整年份或滚动周期

若官网只写笼统承诺，不能转换成精确天数。若无官方指标，写 `[待核验]`，可以说明“出版社未公开可核验统计”。

## 三、来源与时间记录规范

每个可变事实使用以下最小记录：

```text
字段：JIF / JCR 分区 / 中科院分区 / 首轮决定 / 同行评审 / 录用率
值：数值或结论
指标年份/版本：例如 JCR 20XX；不得只写“最新”
统计口径：学科类别、平均/中位数、是否包含 desk reject 等
来源：完整 URL
查询日期：YYYY-MM-DD
核验状态：已核验 / [待核验] / 来源冲突
```

规则：

- “最新”是相对概念，最终报告必须改成明确年份。
- 同一行多个指标可能来自不同 URL；逐项放置来源，不用一个总脚注覆盖全部。
- 来源 URL 可点击且直接落到指标或说明页面，避免只给搜索结果页。
- 查询日期记录实际访问日，不回填或估算发布日期。
- 搜索引擎摘要只能帮助定位原页，不能作为最终来源。

## 四、期刊匹配维度

在事实核验后，从六个维度判断高/中/低匹配：

| 维度 | 核心问题 | 最低证据 |
|---|---|---|
| 主题 | 期刊是否持续发表该主题 | Aims & Scope + 近三年文章 |
| 方法 | 是否有相同或可比方法先例 | 真实文章的方法摘要或全文 |
| 理论 | 是否与相同理论传统对话 | 真实文章题录和理论定位 |
| 贡献 | 论文贡献类型是否符合期刊定位 | 官网定位 + 近期文章讨论 |
| 样本 | 样本、区域或分析层级是否有先例 | 近期文章方法信息 |
| 格式 | 字数、文章类型、开放科学要求是否满足 | 最新作者指南 |

不要用 IF 或分区替代匹配度。没有证据的维度标 `[待核验]`，不能默认“中”。

## 五、候选期刊检索种子

下列名称仅用于启动检索，不代表当前分区、影响力、审稿速度、录用率或必然适配。正式输出前必须逐刊核对官网、范围和指标。

### 5.1 传播、新媒体与新闻

- Journal of Communication
- Communication Research
- Human Communication Research
- Communication Monographs
- New Media & Society
- Journal of Computer-Mediated Communication
- Media, Culture & Society
- Political Communication
- Journalism & Mass Communication Quarterly
- Digital Journalism
- Social Media + Society

### 5.2 健康、科学与公共传播

- Health Communication
- Journal of Health Communication
- Science Communication
- Public Understanding of Science
- Social Science & Medicine
- Health Education & Behavior
- Patient Education and Counseling
- BMC Public Health

### 5.3 心理、消费、管理与信息系统

- Journal of Personality and Social Psychology
- Personality and Social Psychology Bulletin
- Journal of Experimental Social Psychology
- Social Psychological and Personality Science
- Journal of Consumer Research
- Journal of Marketing
- Journal of Marketing Research
- Journal of Applied Psychology
- Academy of Management Journal
- Information Systems Research
- MIS Quarterly
- Computers in Human Behavior
- Telematics and Informatics

候选列表不穷尽。应从 draft 参考文献、数据库主题检索和用户目标层级扩展，而不是机械地从本表挑选。

UTD24 身份若与任务相关，应以 UT Dallas 官方列表逐刊核验；“被列入 UTD24”不等于某年 JCR Q1，也不适用于所有社会科学领域。

## 六、范例文章核验

对每篇用于比对的文章至少核验：

- 完整题名
- 作者
- 发表年份
- 期刊
- DOI、PMID 或其他稳定标识（如有）
- 出版社落地页或权威索引 URL
- 查询日期

优先级：出版社落地页/DOI → Crossref、PubMed、Web of Science 等权威索引 → 机构仓储。搜索摘要和引用列表只能作为线索。

只有摘要时，只评价摘要可见的结构；不能声称已核验全文写法。访问受限时明确写“全文未核验”，避免捏造章节细节。

## 七、冲突与失败降级

- **JCR 与中科院分区不同**：分别列出，不判定为冲突。
- **同一指标不同年份不同**：按年份并列，优先使用用户指定年份；未指定时使用可核验的最新发布年份。
- **官方与第三方不同**：保留官方值；第三方值不进入最终结论。
- **两个官方页面不同**：记录两个 URL、查询日期、统计口径，状态标“来源冲突”。
- **付费墙或权限不足**：写 `[待核验]` 和受阻来源，不借用记忆填值。
- **无审稿周期数据**：写 `[待核验]`，不得根据投稿论坛、个案或学科均值估算。
- **无录用率数据**：写 `[待核验]`，不得把“投稿难度高/低”伪装成录用率。

未核验字段不得参与定量排名。此时按主题、方法、理论和格式的已核验证据做定性排序，并披露限制。

## 八、输出模板

| 期刊 | 主题/方法匹配证据 | JIF（年份） | JCR 分区（类别、年份） | 中科院分区（年份） | 审稿周期（口径） | 来源 URL | 查询日期 | 状态 |
|---|---|---|---|---|---|---|---|---|
| Journal A | 官网范围 + 近期文章 | `[待核验]` | `[待核验]` | `[待核验]` | `[待核验]` | 待补 | YYYY-MM-DD | 待核验 |

已核验示例应写成：

```text
首轮决定：X 天（中位数；是否包含 desk reject 以页面定义为准；来源：URL；查询于 YYYY-MM-DD）
```

不要把模板中的 X、年份或 URL 占位符保留为真实结论。

## 九、投稿策略

- 先按主题、方法、理论、样本和格式匹配，再参考指标；指标高不代表适配。
- 使用“首选 → 备选 → 保底”的顺序投稿方案，同一时间只投一本期刊。
- 每次转投前根据编辑或审稿意见修改论文、摘要、cover letter 与格式。
- 若关键指标未核验，在策略中披露，不把它作为“保底”或“低难度”的依据。
- “投稿难度”必须说明依据；没有官方录用率时使用定性证据并标记不确定性。

## 十、本文件来源记录

以下来源只证明检索口径和官方入口，不提供任何具体期刊在未来持续有效的数值：

1. [Clarivate Journal Citation Reports](https://clarivate.com/academia-government/scientific-and-academic-research/research-funding-analytics/journal-citation-reports/)：JCR 是给定时点的年度报告，JIF 不应单独使用。查询于 2026-08-29。
2. [Clarivate：JCR quartile rankings and other metrics](https://support.clarivate.com/ScientificandAcademicResearch/s/article/Journal-Citation-Reports-Quartile-rankings-and-other-metrics?language=en_US)：JCR 分区与排名口径入口。查询于 2026-08-29。
3. [中国科学院文献情报中心期刊分区表](https://www.fenqubiao.com/Default.aspx)：官方分区表入口；页面当前说明自 2026 年起不再更新与发布。查询于 2026-08-29。
4. [Elsevier：何时从编辑处得到决定](https://www.elsevier.support/zh-cn/publishing/answer/%E4%BD%95%E6%97%B6%E4%BB%8E%E7%BC%96%E8%BE%91%E5%A4%84%E5%BE%97%E5%88%B0%E7%A8%BF%E4%BB%B6%E6%9C%80%E7%BB%88%E5%86%B3%E5%AE%9A)：说明从期刊页面进入 Review Time/Journal Insights，并区分初步决定与最终决定。查询于 2026-08-29。
5. [SAGE：How can I find the time to decision for a journal?](https://solutions.sagepub.com/support/solutions/articles/7000044931-how-can-i-find-the-time-to-decision-for-a-journal-)：说明在具体期刊的 overview and metrics 页面查找 first decision。查询于 2026-08-29。
6. [UT Dallas 官方期刊列表](https://jsom.utdallas.edu/the-utd-top-100-business-school-research-rankings/list-of-journals)：用于核验 UTD 研究排名所列期刊。查询于 2026-08-29。
