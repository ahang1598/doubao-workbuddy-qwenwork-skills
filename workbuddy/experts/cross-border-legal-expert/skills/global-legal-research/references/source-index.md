# 数据源匹配总索引（双轴：业务领域 × 国家/地区）

> 本文件是技能运行时的**路由入口**。先读本文件，按 (国家/地区, 业务领域) 定位源目录，
> 再经 LDH 实时 discover 目录（权威）或 `resources.md`（L2 指南 + Section 12 L1 官方源）取候选 URL。
> 目标：让用户问题**尽可能多地匹配到可核验数据源**。
>
> **援引铁律**：本索引及下游目录给出的 URL 均为**候选入口**，须经 `verification-engine.md`
> 的实时核验（WebFetch 可达 + 锚定法条号/案号）后方可引用；禁止凭训练数据直接产出法规或判例。

## 路由规则（三步）

> **Step 0（LDH 实时检索，延迟初始化）**：纯中国大陆法场景跳过、不跑 health，直接走法大大法律法规检索 + 法大大类案检索。**本会话首次遇到外国法/跨境问题时**，由 SKILL.md §4 Step 0 跑一次
> `health` 并缓存；LDH 可用时该类问题**默认优先**经 LDH `search`/`resolve` 检索——其 `source` 字段与本索引
> 及下游目录的 **Source ID 一一对应**，命中可直接回链官方源。LDH 不可用/限流/空 → 自动降级回下方三步。详见 `ldh-integration.md`。

1. **抽取**用户问题中的 `国家/地区` + `业务领域`（业务领域对照下方表 A 的 18 主题）。
2. **选目录**：
   - 中国大陆 / 港澳台 / 涉外 → 走法大大法律法规检索 + 法大大类案检索（一手中文法源）。
   - 其他法域 → 用 LDH 实时 `discover-sources` 取国家目录，或按**表 A** 的"数据类型"过滤候选源。
   - 任何法域都**叠加** `resources.md` 的 L2 权威指南 + Section 12 L1 官方源。
3. **覆盖不足时**降级：薄覆盖法域（中亚、撒哈拉以南非洲小国、部分东南亚）按 `resources.md` §9
   的区域库 + ILO NATLEX / WIPO Lex / 当地律师指引处理，绝不用训练数据补全。

---

## 表 A：18 业务领域 → 数据类型 + 关键来源 hint

> "关键官方源 hint"为常见 L1 入口（仍需核验）；中国法源走法大大检索，境外法源经 LDH 实时目录核验。

| # | 业务领域 | 主要数据类型 | 中国法源分节 | 关键官方源 hint |
|---|---|---|---|---|
| 1 | 公司/商事 | 法规·判例 | 法律规定与标准 / 主体信息查询 | 各国公司法典；国家企业信用公示系统(CN) |
| 2 | 外商投资 | 法规·学说 | 涉外港澳台相关 | UNCTAD IPH；商务部国别指南；EU FDI screening |
| 3 | 企业税 | 法规 | 法律规定与标准 | 各国税法典；Chambers Corporate Tax |
| 4 | 银行金融 | 法规·学说 | 资本市场 / 行业政府部门 | EUR-Lex(CRR/CRD)；DE/BaFin；UK/FCA；FR/AMF |
| 5 | 并购 | 判例·学说 | 资本市场 / 争议解决 | EU/DGComp；ICLG Merger Control |
| 6 | 劳动/雇佣 | 法规·判例 | 法律规定与标准 / 争议解决 | ILO NATLEX；FR/Code du travail；DE/Gesetze |
| 7 | 移民/签证 | 法规 | 涉外港澳台相关 | EUR-Lex(Blue Card)；ICLG Global Mobility |
| 8 | 知识产权 | 法规·判例 | 知识产权 / 司法案例 | WIPO Lex；EU/EUIPO；CNIPA(CN) |
| 9 | 数据隐私/保护 | 法规·学说 | 行业政府部门 | DLA Piper DPLW；EUR-Lex(GDPR)；FR/CNIL |
| 10 | 竞争/反垄断 | 判例·学说 | 行业政府部门 | EU/DGComp；DE/Bundeskartellamt；FR/ADLC |
| 11 | 环境/ESG | 法规·学说 | 行业政府部门 | EUR-Lex(CSRD/SFDR/Taxonomy) |
| 12 | 仲裁/争议解决 | 判例 | 争议解决 / 司法案例 | EU/CURIA；CoE/HUDOC；各国法院判例库 |
| 13 | 房地产 | 法规 | 法律规定与标准 | 各国民法典土地编；ICLG Real Estate |
| 14 | 破产/重组 | 法规·判例 | 争议解决 | EUR-Lex(Insolvency Reg.)；ICLG Insolvency |
| 15 | 保险法 | 法规·学说 | 资本市场 / 行业政府部门 | EUR-Lex(Solvency II)；DE/BaFin |
| 16 | 海事/航空 | 法规·学说 | 行业政府部门 | EUR-Lex(航空/海事)；BIMCO clauses |
| 17 | 能源/自然资源 | 法规·学说 | 行业政府部门 | EUR-Lex(Green Deal)；EBRD；ICLG Energy/Mining |
| 18 | 欧盟法 | 法规·判例 | —（境外） | EUR-Lex；EU/CURIA；EU/DGComp；EU/EUIPO |
| 19 | 行政合规/语言法 | 法规·学说 | — | 各国官方语言法/行政程序法；法律法规数据库（含多语言版本）

> 司法案例（中国）、主体信息查询（中国企业/信用）为中国特有强项分节，跨多个业务领域复用。

---

## 业务合规展开模式（Business Compliance Expansion）

> 当用户问题不是"某国某法律领域的规定"而是"在某国运营某业务需要满足哪些合规条件"时，
> 不直接走 §路由规则 三步，而是先判断是否有匹配的业务合规域展开表。

**判断逻辑**：
1. 提取用户问题中的 `法域` + `业务/产品类型`
2. 匹配 `references/business-compliance-maps.md` 中的**匹配关键词** → 命中则进入展开模式
3. 展开模式下：取该业务的全量合规域展开表 → 对每一行逐域执行 §路由规则 三步 → 汇总输出
4. 未命中任何业务类型 → 走原有的 §路由规则 三步（法律学科路径）

**展开模式与原有路径的对比**：

| 维度 | 原路径（法律学科） | 展开模式（业务合规） |
|------|:----------------:|:-----------------:|
| 入口 | 法域 + 法律主题(18选1) | 法域 + 业务类型 |
| 检索范围 | 单主题 → 深层穿透 | 多域并行 → 逐域穿透 |
| 输出格式 | output-formats.md 路径A/B/C | output-formats.md 路径D |
| 适用场景 | 法律信息检索 | 合规准入规划 |

---

## 国家/地区覆盖

> 详细离线源目录（`sources-global.md` 845 条 / `sources-china.md` 672 条）为满足
> 单技能 ≤200KB 体积约束已移除；运行时以 LDH 实时 `discover-sources` 目录为权威国家源目录，
> 叠加 `resources.md` 的 L2 指南与 Section 12 L1 官方源（EUR-Lex / legislation.gov.uk / WIPO Lex 等）。

## 覆盖盲区（明确告知用户，不得编造补全）

- **中亚**（哈/乌/土/吉/塔）、撒哈拉以南非洲多数小国、部分太平洋岛国：全球库覆盖薄。
- 处理方式：`resources.md` §9 区域库（AfricanLII / PacLII / SICE-OAS）+ ILO NATLEX / WIPO Lex
  + 商务部国别指南 + **当地律师**。这些法域几乎总是需要当地律师确认。
