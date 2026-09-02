# 全球法律数据源目录（按地区 → 国家/地区 → 数据类型）

> 数据来源：`legaldatahunter_sources_analysis.xlsx`（LegalDataHunter，抓取于 2026-05-21）。
> 收录口径：**置信级别=高 ∧ 可商用 ∧ 有 URL**，共 **845** 条，覆盖 **170** 个国家/地区。
> 本目录是离线快照；运行时国家代码与 Source ID 以 LDH 实时 discover 目录为准。
> 数据类型：法规=法律法规/规章，判例=判例/裁判文书，学说=学说/评论/指南。
> **援引规则**：URL 为官方候选入口；运行时须 WebFetch 核验可达 + 锚定法条号/案号后方可引用，
> 禁止凭训练数据编造法规与判例。详见 `verification-engine.md`。

## 地区速查

| 地区 | 国家/地区数 | 源数 |
|---|---|---|
| 国际/区域组织 | 4 | 52 |
| 欧洲 | 53 | 389 |
| 美洲 | 44 | 244 |
| 亚洲 | 34 | 92 |
| 大洋洲 | 12 | 29 |
| 非洲 | 23 | 39 |

---

# 地区：国际/区域组织

<a name="c-INTL"></a>
## 国际/跨国（INTL）— 19 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| INTL/ASEAN-Legal | ASEAN Legal Instruments Database | 法规 | https://agreement.asean.org/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| INTL/AU-Commission | African Union Legal Instruments | 法规 | https://au.int/en/treaties | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| INTL/ICRC-IHL | ICRC International Humanitarian Law Databases | 法规/判例/学说 | https://ihl-databases.icrc.org | 类案检索、裁判观点抽取、法院/法官趋势分析；法规检索、合规义务映射、法条版本/更新监测；法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| INTL/UNTreatyCollection | UN Treaty Collection | 法规 | https://treaties.un.org/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| INTL/UNIDROIT | UNIDROIT Instruments | 法规 | https://www.unidroit.org/instruments/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| INTL/WorldBankDocs | World Bank Documents & Reports | 法规 | https://documents.worldbank.org | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| INTL/ADBTribunal | ADB Administrative Tribunal Decisions | 判例 | https://www.adb.org/who-we-are/organization/administrative-tribunal | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| INTL/AfCHPR | African Court on Human and Peoples' Rights | 判例 | https://www.african-court.org/cpmt/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| INTL/IHRDA-AfricanCL | African Human Rights Case Law Analyser (IHRDA) | 判例 | https://caselaw.ihrda.org/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| INTL/CCJ | Caribbean Court of Justice Judgments | 判例 | https://ccj.org/judgments-proceedings/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| INTL/ECCC | Extraordinary Chambers in the Courts of Cambodia | 判例 | https://www.eccc.gov.kh/en | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| INTL/ICSIDAwards | ICSID Arbitration Awards (World Bank) | 判例 | https://icsid.worldbank.org/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| INTL/ICJDecisions | International Court of Justice Decisions | 判例 | https://icj-cij.org/decisions | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| INTL/Mercosur-TPR | MERCOSUR Permanent Review Tribunal | 判例 | https://www.tprmercosur.org/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| INTL/OpenLegalData | Open Legal Data Platform (DE/EU Case Law) | 判例 | https://de.openlegaldata.io/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| INTL/PCA | Permanent Court of Arbitration - Case Repository | 判例 | https://pca-cpa.org/en/cases/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| INTL/PCIJ | Permanent Court of International Justice (CD-PCIJ via Zenodo) | 判例 | https://zenodo.org/records/3840480 | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| INTL/UNCITRAL-CLOUT | UNCITRAL Case Law on Texts (CLOUT) | 判例 | https://www.uncitral.org/clout/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| INTL/WIPODecisions | WIPO Arbitration & Mediation Decisions | 判例 | https://www.wipo.int/amc/en/domains/decisionsx/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-CoE"></a>
## 欧洲委员会（CoE）— 6 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| CoE/TreatyOffice | Council of Europe Treaty Office | 法规 | https://www.coe.int/en/web/conventions/full-list | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CoE/HUDOC | HUDOC (European Court of Human Rights) | 判例 | https://hudoc.echr.coe.int | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| CoE/HUDOC-ESC | HUDOC-ESC - European Social Charter Decisions | 判例 | https://hudoc.esc.coe.int/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| CoE/HUDOCExec | HUDOC-EXEC (Execution Monitoring) | 判例 | https://hudoc.exec.coe.int/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| CoE/VeniceCommission | Venice Commission - CODICES Database | 学说/判例 | https://www.venice.coe.int/webforms/documents/default.aspx?ref=CODICES | 类案检索、裁判观点抽取、法院/法官趋势分析；法律研究综述、释义/指南检索、RAG 背景材料；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| CoE/CPTReports | CPT Visit Reports (Prevention of Torture) | 学说 | https://www.coe.int/en/web/cpt | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-EU"></a>
## 欧盟（EU）— 24 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| EU/EUR-Lex | EUR-Lex Portal | 法规/判例 | https://eur-lex.europa.eu | 类案检索、裁判观点抽取、法院/法官趋势分析；法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| EU/EBA | European Banking Authority (EBA) | 学说/法规 | https://www.eba.europa.eu | 法规检索、合规义务映射、法条版本/更新监测；法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| EU/EuroParl | European Parliament Adopted Texts | 法规 | https://data.europarl.europa.eu | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| EU/CPVO-Decisions | Community Plant Variety Office Board of Appeal | 判例 | https://cpvo.europa.eu/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| EU/CURIA | Court of Justice of the EU (CURIA) | 判例 | https://curia.europa.eu | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| EU/ECJ-Tax | ECJ Tax Cases | 判例 | https://curia.europa.eu | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| EU/ECLI | ECLI Search Engine - European Case Law | 判例 | https://e-justice.europa.eu/topics/legislation-and-case-law/european-case-law-identifier-ecli-search-engine_en | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| EU/ADR | EU Domain Dispute Resolution (.eu) | 判例 | https://eu.adr.eu | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| EU/EUIPO | EU Intellectual Property Office (EUIPO) | 判例 | https://euipo.europa.eu | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| EU/EDPB | European Data Protection Board Documents | 学说/判例 | https://www.edpb.europa.eu/our-work-tools/documents/our-documents_en | 类案检索、裁判观点抽取、法院/法官趋势分析；法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| EU/EDAL | European Database of Asylum Law | 判例 | https://www.asylumlawdatabase.eu/en | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| EU/Ombudsman | European Ombudsman | 判例 | https://www.ombudsman.europa.eu | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| EU/BEREC | Body of European Regulators for Electronic Communications (BEREC) | 学说 | https://www.berec.europa.eu | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| EU/ERA | EU Agency for Railways (ERA) | 学说 | https://www.era.europa.eu | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| EU/OLAF | EU Anti-Fraud Office (OLAF) | 学说 | https://anti-fraud.ec.europa.eu | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| EU/AMLA | EU Anti-Money Laundering Authority (AMLA) | 学说 | https://www.amla.europa.eu | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| EU/EASA | EU Aviation Safety Agency (EASA) | 学说 | https://ad.easa.europa.eu | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| EU/DGComp | EU Competition Directorate-General (DG COMP) | 学说 | https://competition-cases.ec.europa.eu | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| EU/CPCS | EU Consumer Protection Cooperation Network | 学说 | https://commission.europa.eu/live-work-travel-eu/consumer-rights-and-complaints/enforcement-consumer-protection/coordinated-actions_en | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| EU/ECB | European Central Bank (ECB) | 学说 | https://eur-lex.europa.eu/browse/institutions/bank.html | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| EU/EFSA | European Food Safety Authority (EFSA) | 学说 | https://www.efsa.europa.eu | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| EU/EMA | European Medicines Agency (EMA) | 学说 | https://www.ema.europa.eu | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| EU/ESMA | European Securities and Markets Authority (ESMA) | 学说 | https://www.esma.europa.eu | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| EU/SRB-Decisions | Single Resolution Board Decisions | 学说 | https://www.srb.europa.eu/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-UN"></a>
## 联合国（UN）— 3 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| UN/SCResolutions | Corpus of UN Security Council Resolutions (Zenodo/Fobbe) | 法规 | https://zenodo.org/records/15154519 | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| UN/ODS | UN Official Document System | 法规 | https://documents.un.org | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| UN/UHRI | Universal Human Rights Index | 学说 | https://uhri.ohchr.org/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

# 地区：欧洲

<a name="c-DK"></a>
## 丹麦（DK）— 8 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| DK/Lovdata | Danish Legislation Database (Retsinformation) | 法规 | https://www.retsinformation.dk | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| DK/Retsinformation | Denmark Retsinformation (Official Law Database) | 法规 | https://www.retsinformation.dk/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| DK/CourtOfAppeal | Danish Courts Database (Domsdatabasen) | 判例 | https://domsdatabasen.dk | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DK/KFST | Danish Competition Authority (KFST) | 学说 | https://www.kfst.dk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| DK/DTIL | Danish Data Protection Authority (Datatilsynet) | 学说 | https://www.datatilsynet.dk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| DK/Ankestyrelsen | Danish National Appeals Board (Ankestyrelsen Principmeddelelser) | 学说 | https://ast.dk/afgorelser/principafgorelser | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| DK/SKAT | Danish Tax Authority (Skattestyrelsen) | 学说 | https://www.retsinformation.dk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| DK/Skattestyrelsen-Vejledning | Danish Tax Legal Guidance (Den Juridiske Vejledning) | 学说 | https://info.skat.dk/data.aspx?oid=124 | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-UA"></a>
## 乌克兰（UA）— 5 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| UA/RadaLegislation | Legislation of Ukraine (Verkhovna Rada) | 法规 | https://data.rada.gov.ua/laws/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| UA/ConstitutionalCourt | Constitutional Court of Ukraine | 判例 | https://ccu.gov.ua | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| UA/SupremeCourt | Supreme Court of Ukraine | 判例 | https://supreme.court.gov.ua | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| UA/REYESTR-CourtDecisions | Ukraine Court Decisions Registry (REYESTR) | 判例 | https://reyestr.court.gov.ua/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| UA/EDRSR | Unified State Register of Court Decisions (ЄДРСР) | 判例 | https://reyestr.court.gov.ua | 类案检索、裁判观点抽取、法院/法官趋势分析；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |

<a name="c-AM"></a>
## 亚美尼亚（AM）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| AM/ARLIS | Armenian Legal Information System (ARLIS) | 法规 | https://www.arlis.am | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| AM/ConstitutionalCourt | Armenian Constitutional Court | 判例 | https://www.concourt.am | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |

<a name="c-RU"></a>
## 俄罗斯（RU）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| RU/PravoGovRu | Russia Official Legal Portal (pravo.gov.ru) | 法规 | https://pravo.gov.ru/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| RU/Sudact | Sudact.ru - Russian Court Decisions (General Jurisdiction, All Regions) | 判例 | https://sudact.ru/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-BG"></a>
## 保加利亚（BG）— 7 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| BG/StateGazette | Bulgarian State Gazette (Държавен вестник) | 法规 | https://dv.parliament.bg | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| BG/VAS-AdminCourt | Bulgaria Supreme Administrative Court (VAS) Retry | 判例 | https://ecase.justice.bg | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BG/ConstitutionalCourt | Bulgarian Constitutional Court | 判例 | https://www.constcourt.bg | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| BG/SupremeCourt | Bulgarian Supreme Court of Cassation | 判例 | https://www.vks.bg | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BG/CPDP | Bulgarian Data Protection Authority (CPDP) | 学说 | https://cpdp.bg | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| NAP-TaxDoctrine | Bulgarian National Revenue Agency Tax Opinions (Становища на НАП) | 学说 | https://nraapp02.nra.bg/cms5/apps/wqreg | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| BG/Parliament | Bulgarian Parliament (Народно събрание) | 学说 | https://www.parliament.bg | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-HR"></a>
## 克罗地亚（HR）— 8 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| HR/OfficialGazette | Croatian Official Gazette (Narodne novine) | 法规 | https://narodne-novine.nn.hr | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| HR/ConstitutionalCourt | Croatian Constitutional Court (Ustavni sud) | 判例 | https://sljeme.usud.hr | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| HR/AllCourts | Croatian Court Decisions (All Courts - odluke.sudovi.hr) | 判例 | https://odluke.sudovi.hr | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| HR/AdminCourt | Croatian High Administrative Court | 判例 | https://odluke.sudovi.hr | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| HR/SupremeCourt | Croatian Supreme Court | 判例 | https://odluke.sudovi.hr | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| HR/AZOP | Croatian Data Protection Authority (AZOP) | 学说 | https://azop.hr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| HR/Sabor | Croatian Parliament (Hrvatski sabor) | 学说 | https://edoc.sabor.hr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| HR/PoreznaUprava-Misljenja | Croatian Tax Authority Opinions (Mišljenja Središnjeg ureda) | 学说 | https://porezna-uprava.gov.hr/hr/misljenja-su/3951 | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-IS"></a>
## 冰岛（IS）— 3 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| IS/Lagasafn | Lagasafn - Icelandic Consolidated Legislation | 法规 | https://www.althingi.is/lagasafn/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| IS/SupremeCourt | Icelandic Supreme Court (Hæstiréttur) | 判例 | https://www.haestirettur.is | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| IS/Althingi | Althingi Parliamentary Proceedings | 立法过程 | https://www.althingi.is | 立法背景、政策意图、议会审议脉络分析 | ⭐⭐⭐⭐⭐ |

<a name="c-LI"></a>
## 列支敦士登（LI）— 4 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| LI/LILEX | LILEX - Liechtenstein Consolidated Legislation | 法规 | https://www.gesetze.li | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| LI/StGH | Liechtenstein Constitutional Court (Staatsgerichtshof) | 判例 | https://www.stgh.li | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| LI/Courts | Liechtenstein Courts Decisions (gerichtsentscheide.li) | 判例 | https://www.gerichtsentscheidungen.li/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| LI/FMA-Enforcement | Liechtenstein Financial Market Authority (FMA) Enforcement | 学说 | https://www.fma-li.li/en/supervision-regulation/enforcement | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-HU"></a>
## 匈牙利（HU）— 8 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| HU/NJT | Nemzeti Jogszabálytár - Hungarian National Legislation Database | 法规 | https://njt.hu | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| HU/AnonHatarozatok | Hungarian Anonymized Court Decisions | 判例 | https://eakta.birosag.hu/anonimizalt-hatarozatok | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| HU/GVH | Hungarian Competition Authority Resolutions (GVH) | 判例 | https://www.gvh.hu/dontesek/versenyhivatali_dontesek | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| HU/Constitutional | Hungarian Constitutional Court (Alkotmánybíróság) | 判例 | https://alkotmanybirosag.hu | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| HU/FelsoBirosag | Hungarian Supreme Court (Kúria) | 判例 | https://kuria-birosag.hu | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| HU/NAIH | Hungarian Data Protection Authority (NAIH) | 学说 | https://www.naih.hu | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| HU/NAV | Hungarian Tax Authority (NAV) | 学说 | https://nav.gov.hu | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| HU/NAV-TaxGuidance | Hungary NAV Tax Guidance (Adózási kérdés) | 学说 | https://nav.gov.hu/ado/adozasi_kerdes | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-MK"></a>
## 北马其顿（MK）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| MK/ConstitutionalCourt | North Macedonia Constitutional Court (Уставен суд) | 判例 | https://ustavensud.mk | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| MK/JudicialPortal | North Macedonia Supreme Court Practice (Судска пракса - Врховен суд) | 判例 | http://vrhoven.sud.mk | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-LU"></a>
## 卢森堡（LU）— 6 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| LU/LegalDatabase | Luxembourg Legal Database (Legilux) | 法规 | https://legilux.public.lu | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| LU/TribAdmin-TaxDecisions | Luxembourg Administrative Tribunal Tax Decisions | 判例 | https://ja.etat.lu | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| LU/SupremeCourt | Luxembourg Court of Cassation (Cour de Cassation) | 判例 | https://justice.public.lu | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| LU/Courts | Luxembourg Courts Decisions (justice.public.lu) | 判例 | https://justice.public.lu/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| LU/CNPD | Luxembourg Data Protection Authority (CNPD) | 学说 | https://cnpd.public.lu | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| LU/ACD | Luxembourg Tax Administration (ACD) | 学说 | https://impotsdirects.public.lu | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-TR"></a>
## 土耳其（TR）— 7 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| TR/MevzuatHF | Turkish Legislation (Hugging Face Dataset) | 法规 | https://huggingface.co/datasets/muhammetakkurt/mevzuat-gov-dataset | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| TR/ResmiGazete | Turkish Official Gazette (Resmi Gazete) | 法规 | https://www.resmigazete.gov.tr | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| TR/AnayasaMahkemesi | Turkish Constitutional Court (Anayasa Mahkemesi) | 判例 | https://www.anayasa.gov.tr | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| TR/Danistay | Turkish Council of State (Danistay) | 判例 | https://www.danistay.gov.tr | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| TR/Yargitay | Turkish Court of Cassation (Yargitay) | 判例 | https://www.yargitay.gov.tr | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| TR/GIB-Ozelgeler | Turkish Revenue Administration Tax Rulings (Özelgeler) | 学说 | https://gib.gov.tr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| TR/TBMM | Turkish Parliament (TBMM) | 立法过程 | https://www.tbmm.gov.tr/Tutanaklar/TutanakMetinleri | 立法背景、政策意图、议会审议脉络分析 | ⭐⭐⭐⭐⭐ |

<a name="c-SM"></a>
## 圣马力诺（SM）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| SM/Legisammarino | San Marino Official Legislation (Bollettino Ufficiale) | 法规 | https://www.bollettinoufficiale.sm | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| SM/BCSM-Sanctions | San Marino Central Bank Sanctions | 学说 | https://www.bcsm.sm/en/functions/sanctions/sanctioning-measures | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-RS"></a>
## 塞尔维亚（RS）— 4 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| RS/PravnoInformacioniSistem | Serbia Legal Information System (Pravno-Informacioni Sistem) | 法规 | https://www.pravno-informacioni-sistem.rs/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| RS/SluzbenGlasnik | Službeni glasnik RS - Serbian Official Gazette | 法规 | https://www.paragraf.rs/propisi.html | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| RS/ConstitutionalCourt | Serbian Constitutional Court (Ustavni sud) | 判例 | https://ustavni.sud.rs | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| RS/SupremeCourt | Serbian Supreme Court (Vrhovni sud) | 判例 | https://vrh.sud.rs | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-CY"></a>
## 塞浦路斯（CY）— 4 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| CY/CYLAW | CY-Law - Cyprus Legislation Database | 法规 | https://www.cylaw.org | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CY/SupremeCourt | Cyprus Supreme Court | 判例 | http://www.cylaw.org/apofaseis/aad/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| CY/DATAPROTECTION | Cyprus Data Protection Authority | 学说 | https://www.dataprotection.gov.cy | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| CY/CySEC-Enforcement | Cyprus Securities & Exchange Commission Enforcement | 学说 | https://www.cysec.gov.cy/en-GB/public-info/enforcement-actions/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-AT"></a>
## 奥地利（AT）— 8 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| AT/Landesrecht | Austrian State Legislation (Landesrecht) | 法规 | https://www.ris.bka.gv.at | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| AT/RIS | Rechtsinformationssystem (RIS) | 法规/判例 | https://www.ris.bka.gv.at | 类案检索、裁判观点抽取、法院/法官趋势分析；法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| AT/VfGH | Austrian Constitutional Court (VfGH) | 判例 | https://www.vfgh.gv.at | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| AT/VwGH | Austrian Supreme Administrative Court (Verwaltungsgerichtshof) | 判例 | https://www.ris.bka.gv.at | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| AT/OGH | Austrian Supreme Court (Oberster Gerichtshof) | 判例 | https://www.ris.bka.gv.at/Jus/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| AT/E-Control | Austrian Energy Regulator (E-Control) | 学说 | https://www.e-control.at | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| AT/FMA | Austrian Financial Market Authority (FMA) | 学说 | https://www.fma.gv.at | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| AT/RTR | Austrian Regulatory Authority | 学说 | https://www.rtr.at | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-AD"></a>
## 安道尔（AD）— 4 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| AD/BOPA | Andorra Official Gazette (BOPA) | 法规 | https://www.bopa.ad | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| AD/PortalJuridic | Andorra Portal Juridic (Consolidated Law) | 法规 | https://www.portaljuridicandorra.ad/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| AD/TribunalConstitucional | Constitutional Court of Andorra (Tribunal Constitucional) | 判例 | https://www.tribunalconstitucional.ad | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| AD/AFA-Sanctions | Andorra Financial Authority Sanctions | 学说 | https://www.afa.ad/en/entitats-supervisades/sancions-a-entitats-supervisades | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-GR"></a>
## 希腊（GR）— 19 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| GR/GovernmentGazette | Greek Government Gazette (FEK) | 法规 | https://www.et.gr | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| GR/HellenicParliament | Hellenic Parliament - Raptarchis Greek Legal Code | 法规 | https://huggingface.co/datasets/AI-team-UoA/greek_legal_code | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| GR/SupremeCourt | Greek Supreme Court (Άρειος Πάγος) | 判例 | https://www.areiospagos.gr | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| GR/EPANT | Hellenic Competition Commission (EPANT) | 判例 | https://www.epant.gr | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| GR/CourtOfAudit | Hellenic Court of Audit (Ελεγκτικό Συνέδριο) | 判例 | https://www.elsyn.gr | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| GR/KHMDHS | Central Electronic Registry of Public Procurement (KHMDHS) | 学说 | https://cerpp.eprocurement.gov.gr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| GR/Diavgeia | Diavgeia - Greek Government Decisions | 学说 | https://diavgeia.gov.gr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| GR/RAAEY | Energy Regulatory Authority (RAAEY/RAE) | 学说 | https://www.raaey.gr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| GR/ConsumerOmbudsman | Greek Consumer Ombudsman (Synigoros Katanaloti) | 学说 | https://www.synigoroskatanaloti.gr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| GR/DPA | Greek Data Protection Authority (HDPA) | 学说 | https://www.dpa.gr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| GR/GNCHR | Greek National Commission for Human Rights | 学说 | https://www.nchr.gr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| GR/Ombudsman | Greek Ombudsman (Synigoros tou Politi) | 学说 | https://www.synigoros.gr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| GR/AADE | Greek Tax Authority (AADE) | 学说 | https://www.aade.gr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| GR/ADAE | Hellenic Authority for Communication Security and Privacy (ADAE) | 学说 | https://adae.gov.gr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| GR/HCMC | Hellenic Capital Market Commission (Epitropi Kefalaiagoras) | 学说 | http://www.hcmc.gr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| GR/EETT | Hellenic Telecommunications Commission (EETT) | 学说 | https://www.eett.gr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| GR/NSK | Legal Council of the State (NSK) | 学说 | https://www.nsk.gr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| GR/NCRTV | National Council for Radio and Television (ESR) | 学说 | http://repository-esr.ekt.gr/esr/handle/20.500.12039/20 | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| GR/NTA | National Transparency Authority (AEAD) | 学说 | https://aead.gr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-DE"></a>
## 德国（DE）— 41 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| DE/BadenWürttemberg | Baden-Württemberg Regional Legislation | 法规 | https://www.landesrecht-bw.de | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| DE/Brandenburg | Brandenburg State Law (BRAVORS) | 法规 | https://bravors.brandenburg.de | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| DE/Bremen | Bremen State Law (Transparenzportal) | 法规 | https://www.transparenz.bremen.de | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| DE/BGBl | German Federal Law (Gesetze im Internet) | 法规 | https://www.gesetze-im-internet.de | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| DE/NRW | North Rhine-Westphalia State Law (recht.nrw.de) | 法规 | https://recht.nrw.de | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| DE/OpenLegalData | Open Legal Data (openlegaldata.io) | 判例/法规 | https://de.openlegaldata.io | 类案检索、裁判观点抽取、法院/法官趋势分析；法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| DE/Sachsen | Saxony State Law (REVOSAX) | 法规 | https://www.revosax.sachsen.de | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| DE/Bayern | Bavaria State Law (BAYERN.RECHT) | 判例 | https://www.gesetze-bayern.de | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DE/BayernCaseLaw | Bayern State Court Decisions | 判例 | https://www.gesetze-bayern.de/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DE/BerlinCaseLaw | Berlin State Court Decisions | 判例 | https://gesetze.berlin.de/bsbe/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DE/BrandenburgCaseLaw | Brandenburg State Court Decisions | 判例 | https://gerichtsentscheidungen.brandenburg.de | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DE/BremenCaseLaw | Bremen State Court Decisions | 判例 | https://justiz.de/onlinedienste/rechtsprechung/Entscheidungen-Bremen/index.php | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DE/BKartG | German Cartel Court (Bundeskartellgericht) | 判例 | https://www.rechtsprechung-im-internet.de | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DE/BVerwG | German Federal Administrative Court (BVerwG) | 判例 | https://www.rechtsprechung-im-internet.de | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DE/BVerfG | German Federal Constitutional Court (BVerfG) | 判例 | https://www.rechtsprechung-im-internet.de | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| DE/BGH | German Federal Court of Justice (BGH) | 判例 | https://www.rechtsprechung-im-internet.de | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DE/BFH | German Federal Finance Court (Bundesfinanzhof) | 判例 | https://www.rechtsprechung-im-internet.de | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DE/BAG | German Federal Labor Court (Bundesarbeitsgericht) | 判例 | https://www.rechtsprechung-im-internet.de | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DE/BPatG | German Federal Patent Court (BPatG) | 判例 | https://www.rechtsprechung-im-internet.de | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DE/BSG | German Federal Social Court (BSG) | 判例 | https://www.rechtsprechung-im-internet.de | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DE/HessenCaseLaw | Hessen State Court Decisions (LaReDa) | 判例 | https://www.lareda.hessenrecht.hessen.de/bshe/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DE/MecklenburgVorpommernCaseLaw | Mecklenburg-Vorpommern State Court Decisions (MV Justiz) | 判例 | https://www.landesrecht-mv.de/bsmv/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DE/NiedersachsenCaseLaw | Niedersachsen State Court Decisions (Nds. Rechtsprechungsdatenbank) | 判例 | https://www.rechtsprechung.niedersachsen.de/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DE/NordrheinWestfalenCaseLaw | Nordrhein-Westfalen State Court Decisions | 判例 | https://nrwe.de/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DE/RheinlandPfalzCaseLaw | Rheinland-Pfalz State Court Decisions | 判例 | https://landesrecht.rlp.de/bsrp/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DE/SaarlandCaseLaw | Saarland State Court Decisions | 判例 | https://recht.saarland.de/bssl/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DE/SachsenCaseLaw | Sachsen State Court Decisions | 判例 | https://www.justiz.sachsen.de/ovgentschweb/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DE/SachsenAnhaltCaseLaw | Sachsen-Anhalt State Court Decisions | 判例 | https://landesrecht.sachsen-anhalt.de/bsst/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DE/SchleswigHolsteinCaseLaw | Schleswig-Holstein State Court Decisions | 判例 | https://gesetze-rechtsprechung.sh.juris.de/bssh/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DE/ThueringenCaseLaw | Thueringen State Court Decisions (Thueringer Rechtsprechungsdatenbank) | 判例 | https://landesrecht.thueringen.de/bsth/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DE/BMF | BMF-Schreiben (German Federal Ministry of Finance Tax Circulars) | 学说 | https://www.bundesfinanzministerium.de | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| DE/BKartA-Verbraucher | German Consumer Protection (vzbv) | 学说 | https://www.vzbv.de | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| DE/BRAK | German Federal Bar Association (BRAK) | 学说 | https://www.brak.de | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| DE/Bundeskartellamt | German Federal Cartel Office (Bundeskartellamt) | 学说 | https://www.bundeskartellamt.de | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| DE/BfDI | German Federal Data Protection Authority (BfDI) | 学说 | https://www.bfdi.bund.de | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| DE/UBA | German Federal Environment Agency (UBA) | 学说 | https://www.umweltbundesamt.de | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| DE/BfArM | German Federal Institute for Drugs (BfArM) - Rote-Hand-Briefe | 学说 | https://www.bfarm.de | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| DE/BVL | German Federal Office for Consumer Protection (BVL) - Plant Protection Products | 学说 | https://psm-api.bvl.bund.de/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| DE/BfJ | German Federal Office of Justice (BfJ) | 学说 | https://www.bundesjustizamt.de | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| DE/BaFin | German Financial Supervisory Authority (BaFin) | 学说 | https://www.bafin.de | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| DE/KEK | German Media Concentration Commission (KEK) | 学说 | https://www.kek-online.de | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-IT"></a>
## 意大利（IT）— 19 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| IT/EmiliaRomagna | Emilia-Romagna Regional Legislation (Demetra) | 法规 | https://demetra.regione.emilia-romagna.it | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| IT/GazzettaUfficiale | Gazzetta Ufficiale della Repubblica Italiana | 法规 | https://www.gazzettaufficiale.it | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| IT/Senato | Italian Senate (Senato della Repubblica) | 法规 | https://www.senato.it | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| IT/Lazio-Legislation | Lazio Regional Legislation (consiglio.regione.lazio.it) | 法规 | https://www.consiglio.regione.lazio.it/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| IT/Lombardia | Lombardia Regional Legislation | 法规 | https://www.dati.lombardia.it/government/CRL-Leggi-Regionali-della-Lombardia/abjw-hhay | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| IT/Normattiva | Normattiva - Italian Legal Database | 法规 | https://www.normattiva.it | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| IT/Piemonte | Piedmont Regional Legislation | 法规 | https://arianna.consiglioregionale.piemonte.it | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| IT/Toscana | Toscana Regional Legislation (Raccolta Normativa) | 法规 | https://raccoltanormativa.consiglio.regione.toscana.it | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| IT/Veneto | Veneto Regional Legislation (BUR) | 法规 | https://bur.regione.veneto.it | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| IT/ConsiglioDiStato | Council of State (Consiglio di Stato) | 判例 | https://www.giustizia-amministrativa.it | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| IT/CassazioneCivile | Court of Cassation (Corte di Cassazione) | 判例 | https://www.cortedicassazione.it | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| IT/CorteCostituzionale | Italian Constitutional Court (Corte Costituzionale) | 判例 | https://www.cortecostituzionale.it | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| IT/GarantePrivacy | Italian Data Protection Authority (Garante Privacy) | 判例/学说 | https://www.garanteprivacy.it | 类案检索、裁判观点抽取、法院/法官趋势分析；法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| IT/Banca | Bank of Italy - Supervision | 学说 | https://www.bancaditalia.it | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| IT/AGCOM | Italian Communications Authority (AGCOM) | 学说 | https://www.agcom.it | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| IT/AGCM | Italian Competition Authority (AGCM) | 学说 | https://www.agcm.it | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| IT/AgenziaDogane | Italian Customs Agency (Agenzia delle Dogane) | 学说 | https://www.adm.gov.it | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| IT/AgenziEntrate | Italian Revenue Agency (Agenzia delle Entrate) | 学说 | https://www.agenziaentrate.gov.it | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| IT/AgenziaEntrate | Italian Revenue Agency Tax Doctrine (Interpelli & Circolari) | 学说 | https://www.agenziaentrate.gov.it/portale/normativa-e-prassi/risposte-agli-interpelli | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-LV"></a>
## 拉脱维亚（LV）— 5 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| LV/LegislativeDatabase | Likumi.lv - Latvian Law Portal | 法规 | https://www.likumi.lv | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| LV/ConstitutionalCourt | Latvian Constitutional Court (Satversmes tiesa) | 判例 | https://www.satv.tiesa.gov.lv | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| LV/AllCourts | Latvian Courts Portal (elieta.lv) | 判例 | https://www.elieta.lv/web/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| LV/SupremeCourt | Latvian Supreme Court (Senāts) | 判例 | https://manas.tiesas.lv/eTiesasMvc | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| LV/Parliament | Latvian Parliament (Saeima) | 学说 | https://www.saeima.lv | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-NO"></a>
## 挪威（NO）— 4 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| NO/Lovdata | Lovdata - Norwegian Legislation | 法规 | https://lovdata.no | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| NO/Stortinget | Norwegian Parliament Data Service (Stortingets datatjeneste) | 法规/学说 | https://data.stortinget.no | 法规检索、合规义务映射、法条版本/更新监测；法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| NO/KFIR | KFIR (Norwegian Board of Appeal for Industrial Property Rights) | 判例 | https://kfir.no/avgjørelser | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| NO/Høyesterett | Norwegian Supreme Court (Høyesterett) | 判例 | https://lovdata.no/register/avgjørelser | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-CZ"></a>
## 捷克（CZ）— 5 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| CZ/ConstitutionalCourt | Czech Constitutional Court (Ústavní soud) | 判例 | https://www.usoud.cz | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| CZ/NSS | Czech Supreme Administrative Court (Nejvyssi spravni soud) | 判例 | https://sbirka.nssoud.cz | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| CZ/SupremeCourt | Czech Supreme Court (Nejvyšší soud) | 判例 | https://sbirka.nsoud.cz | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| CZ/UOOU | Czech Data Protection Authority (ÚOOÚ) | 学说 | https://uoou.gov.cz | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| CZ/MFCR | Czech Finance Ministry Tax Guidance | 学说 | https://mf.gov.cz | 法律研究综述、释义/指南检索、RAG 背景材料；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |

<a name="c-MD"></a>
## 摩尔多瓦（MD）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| MD/InstanteJustice | Moldova National Courts Portal (Instanțe de judecată) | 判例 | https://instante.justice.md | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-MC"></a>
## 摩纳哥（MC）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| MC/LegiMonaco | LegiMonaco Legal Database | 判例/法规 | https://legimonaco.mc | 类案检索、裁判观点抽取、法院/法官趋势分析；法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| MC/JournalMonaco | Monaco Official Journal (Journal de Monaco) | 法规 | https://journaldemonaco.gouv.mc | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-SK"></a>
## 斯洛伐克（SK）— 3 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| SK/CollectionOfLaws | Slovak Collection of Laws (Zbierka zákonov) | 法规 | https://static.slov-lex.sk | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| SK/SupremeCourt | Slovak Supreme Court (Najvyšší súd) | 判例 | https://www.nsud.sk | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| SK/UOOU | Slovak Data Protection Authority (ÚOOÚ) | 学说 | https://dataprotection.gov.sk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-SI"></a>
## 斯洛文尼亚（SI）— 5 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| SI/LegislativeDatabase | Slovenian Legislation Database (PISRS) | 法规 | https://www.pisrs.si | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| SI/AdminCourt | Slovenian Administrative Court | 判例 | https://www.sodnapraksa.si | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| SI/SupremeCourt | Slovenian Case Law Database (sodnapraksa.si) | 判例 | https://www.sodnapraksa.si | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| SI/IPRS | Slovenian Data Protection Authority (IP RS) | 学说 | https://www.ip-rs.si | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| SI/DrzavniZbor | Slovenian National Assembly (Državni zbor) | 学说 | https://www.dz-rs.si | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-GG"></a>
## 根西岛（GG）— 3 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| GG/GCRA | Guernsey Competition & Regulatory Authority (GCRA) | 学说 | https://www.gcra.gg/cases | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| GG/GFSC-Enforcement | Guernsey Financial Services Commission Enforcement | 学说 | https://www.gfsc.gg/enforcement | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| GG/RevenueService-Guidance | Guernsey Revenue Service Tax Guidance | 学说 | https://www.gov.gg/taxationstatementsofpractice | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-VA"></a>
## 梵蒂冈（VA）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| VA/ActaApostolicae | Vatican Apostolic Documents | 法规 | https://www.vatican.va/ | 法规检索、合规义务映射、法条版本/更新监测；宪法条文检索 | ⭐⭐⭐⭐⭐ |

<a name="c-BE"></a>
## 比利时（BE）— 12 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| BE/MoniteurBelge | Moniteur Belge / Belgisch Staatsblad | 法规 | https://www.ejustice.just.fgov.be/eli | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| BE/VlaamseCodex | Vlaamse Codex - Flemish Consolidated Legislation | 法规 | https://codex.vlaanderen.be | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| BE/CourConstitutionnelle | Belgian Constitutional Court (Cour constitutionnelle) | 判例 | https://www.const-court.be | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| BE/ConseilEtat | Belgian Council of State (Conseil d'État) | 判例 | https://www.raadvst-consetat.be | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BE/CourCassation-Fiscal | Belgian Court of Cassation - Tax Cases | 判例 | https://juportal.be | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BE/APD | Belgian Data Protection Authority (APD/GBA) | 判例 | https://www.autoriteprotectiondonnees.be | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BE/CourTravail | Belgian Labour Courts | 判例 | https://juportal.be | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BE/CASS | Court of Cassation (Cour de Cassation) | 判例 | https://juportal.be | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BE/BCA | Belgian Competition Authority (BCA) | 学说 | https://www.belgiancompetition.be | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| BE/CREG | Belgian Energy Regulator (CREG) | 学说 | https://www.creg.be | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| BE/FISCONETplus-Doctrine | Belgian Tax Doctrine (FISCONETplus Circulars) | 学说 | https://eservices.minfin.fgov.be/myminfin-web/pages/fisconet | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| BE/BIPT | Belgian Telecom Regulator (BIPT) | 学说 | https://www.bipt.be | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-FR"></a>
## 法国（FR）— 28 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| FR/ANC | Autorité des Normes Comptables (ANC) | 法规/学说 | https://www.anc.gouv.fr | 法规检索、合规义务映射、法条版本/更新监测；法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| FR/LegifranceCodes | French Consolidated Legal Codes (PISTE API) | 法规 | https://api.piste.gouv.fr/dila/legifrance | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐ |
| FR/JournalOfficiel | Légifrance LEGI - French Consolidated Legislation | 法规 | https://echanges.dila.gouv.fr/OPENDATA/LEGI/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| FR/AMF_Sanctions | AMF Enforcement Committee Decisions (Commission des sanctions) | 判例 | https://www.amf-france.org/fr/sanctions-transactions/decisions-de-la-commission-des-sanctions | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| FR/ARCEP | ARCEP (Autorité de régulation des communications) | 判例/学说 | https://www.arcep.fr/la-regulation/avis-et-decisions-de-larcep.html | 类案检索、裁判观点抽取、法院/法官趋势分析；法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| FR/ADLC | Autorité de la Concurrence (French Competition Authority) | 判例 | https://www.autoritedelaconcurrence.fr/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| FR/CNIL | CNIL - Commission Nationale de l'Informatique et des Libertés | 判例/学说 | https://echanges.dila.gouv.fr/OPENDATA/CNIL/ | 类案检索、裁判观点抽取、法院/法官趋势分析；法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| FR/CRE | CRE (Commission de régulation de l'énergie) | 判例/学说 | https://www.cre.fr/documents | 类案检索、裁判观点抽取、法院/法官趋势分析；法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| FR/DefenseurDesDroits | Défenseur des Droits (French Ombudsman) | 判例/学说 | https://juridique.defenseurdesdroits.fr | 类案检索、裁判观点抽取、法院/法官趋势分析；法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| FR/CouncilState | French Administrative Courts (CE, CAA, TA) | 判例 | https://opendata.justice-administrative.fr | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| FR/ConseilConstitutionnel | French Constitutional Council (Conseil constitutionnel) | 判例 | https://www.conseil-constitutionnel.fr | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| FR/CE-Fiscal | French Council of State - Tax Chamber | 判例 | https://www.conseil-etat.fr | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| FR/CdesC | French Court of Auditors | 判例 | https://www.ccomptes.fr | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| FR/CASS | French Court of Cassation Case Law (CASS Database) | 判例 | https://echanges.dila.gouv.fr/OPENDATA/CASS/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| FR/CNDA | French National Asylum Court (CNDA) | 判例 | https://www.cnda.fr | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| FR/DefenseurDroits | French Rights Defender (Défenseur des droits) | 判例 | https://www.defenseurdesdroits.fr | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| FR/Judilibre | Judilibre - French Judicial Case Law | 判例 | https://api.piste.gouv.fr/cassation/judilibre | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐ |
| FR/CADA | CADA - Commission d'accès aux documents administratifs | 学说 | https://cada.data.gouv.fr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| FR/ConventionsCollectives | Conventions Collectives (Base KALI) | 学说 | https://echanges.dila.gouv.fr/OPENDATA/KALI/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| FR/ARPP | French Advertising Regulator (ARPP/JDP) | 学说 | https://www.jdp-pub.org | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| FR/Halde | French Anti-Discrimination Authority | 学说 | https://www.defenseurdesdroits.fr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| FR/DGAC | French Civil Aviation Authority | 学说 | https://www.bulletin-officiel.developpement-durable.gouv.fr/recherche | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| FR/DGCCRF | French Consumer Protection (DGCCRF) | 学说 | https://data.economie.gouv.fr/explore/dataset/rappelconso-v2-gtin-trie/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| FR/ANJ | French Gaming Authority (ANJ) | 学说 | https://anj.fr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| FR/INPI | French IP Office (INPI) | 学说 | https://www.inpi.fr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| FR/ASN | French Nuclear Safety Authority (ASN/ASNR) | 学说 | https://reglementation-controle.asnr.fr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| FR/BOAMP | French Public Procurement (BOAMP) | 学说 | https://www.boamp.fr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| FR/ServicePublic | Service-Public.fr (Fiches pratiques) | 学说 | https://www.service-public.fr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-FO"></a>
## 法罗群岛（FO）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| FO/Logting | Faroe Islands Parliament (Løgting) Legislation | 法规 | https://logir.fo/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-PL"></a>
## 波兰（PL）— 12 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| PL/DziennikUrzedowy | Dziennik Ustaw - Polish Official Journal | 法规 | https://www.dziennikustaw.gov.pl | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| PL/KIO | KIO Rulings (Krajowa Izba Odwoławcza) | 判例 | https://orzeczenia.uzp.gov.pl/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| PL/ConstitutionalCourt | Polish Constitutional Court (Trybunał Konstytucyjny) | 判例 | https://www.trybunal.gov.pl | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| PL/NSA-Tax | Polish Supreme Administrative Court - Tax | 判例 | https://orzeczenia.nsa.gov.pl | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| PL/SupremeCourt | Polish Supreme Court (Sąd Najwyższy) | 判例 | https://www.saos.org.pl | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| PL/UOKIK | Polish Competition Authority (UOKiK) | 学说 | https://decyzje.uokik.gov.pl | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| PL/UODO | Polish Data Protection Authority (UODO) | 学说 | https://orzeczenia.uodo.gov.pl | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| PL/URE | Polish Energy Regulatory Office | 学说 | https://bip.ure.gov.pl | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| PL/KNF | Polish Financial Supervision Authority (KNF) | 学说 | https://dziennikurzedowy.knf.gov.pl | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| PL/UKE | Polish Office of Electronic Communications | 学说 | https://www.uke.gov.pl | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| PL/Sejm | Polish Sejm (Parliament) | 学说 | https://www.sejm.gov.pl | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| PL/KIS-EUREKA | Polish Tax Interpretations (EUREKA System) | 学说 | https://eureka.mf.gov.pl/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-BA"></a>
## 波斯尼亚和黑塞哥维那（BA）— 6 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| BA/Brcko | Brčko District Official Gazette (Službeni glasnik Brčko) | 法规 | https://www.skupstinabd.ba | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| BA/FBiH | Federation of BiH Official Gazette (Službene novine FBiH) | 法规 | https://fbihvlada.gov.ba/bs/zakoni | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| BA/RS | Republika Srpska Legislation | 法规 | https://www.paragraf.ba/besplatni-propisi-republike-srpske.html | 法规检索、合规义务映射、法条版本/更新监测；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| BA/SluzbenGlasnik | Službeni glasnik BiH - Bosnia Official Gazette | 法规 | http://www.sluzbenilist.ba | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| BA/SudskaPrivada | BiH Judicial Practice Portal (Sudska praksa) | 判例 | https://sudskapraksa.pravosudje.ba | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BA/ConstitutionalCourt | Constitutional Court of Bosnia and Herzegovina | 判例 | https://www.ustavnisud.ba | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |

<a name="c-JE"></a>
## 泽西岛（JE）— 6 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| JE/JerseyLaw | Jersey Legal Information Board (JerseyLaw) | 法规/判例 | https://www.jerseylaw.je/ | 类案检索、裁判观点抽取、法院/法官趋势分析；法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| JE/TaxCommissioners | Jersey Commissioners of Appeal for Taxes Decisions | 判例 | https://www.gov.je/TaxesMoney/IncomeTax/Technical/CommissionerOfAppealTaxes/pages/aboutcommissionerofappealfortaxes.aspx | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| JE/EmploymentTribunal | Jersey Employment & Discrimination Tribunal | 判例 | https://www.jerseylaw.je/judgments/tribunal/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| JE/PlanningInspectorate | Jersey Planning & Environment Tribunal | 判例 | https://www.gov.je/Government/PlanningPerformance/Pages/MinisterialDecisions.aspx | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| JE/JCRA | Jersey Competition Regulatory Authority Decisions | 学说 | https://www.jcra.je/cases-documents/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| JE/RevenueJersey-TaxGuidance | Revenue Jersey Tax Technical Guidance | 学说 | https://www.gov.je/TaxesMoney/IncomeTax/TechnicalInformation/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-IE"></a>
## 爱尔兰（IE）— 7 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| IE/Acts | Irish Statute Database | 法规 | https://www.irishstatutebook.ie | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| IE/SupremeCourt | Irish Courts Service - Case Law | 判例 | https://www2.courts.ie/Judgments | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| IE/DPC | Irish Data Protection Commission (DPC) | 判例/学说 | https://www.dataprotection.ie | 类案检索、裁判观点抽取、法院/法官趋势分析；法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| IE/TaxAppealsCommission | Irish Tax Appeals Commission Determinations | 判例 | https://www.taxappeals.ie/en/determinations/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| IE/CCPC | Irish Competition Authority (CCPC) | 学说 | https://www.ccpc.ie | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| IE/Revenue | Irish Revenue Commissioners | 学说 | https://www.revenue.ie | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| IE/Revenue-TDM | Irish Revenue Tax and Duty Manuals | 学说 | https://www.revenue.ie/en/tax-professionals/tdm/index.aspx | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-EE"></a>
## 爱沙尼亚（EE）— 4 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| EE/RiigiTeatajaLoomal | Riigi Teataja - Estonian Legal Portal | 法规 | https://www.riigiteataja.ee | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| EE/SupremeCourt | Estonian Supreme Court (Riigikohus) | 判例 | https://www.riigikohus.ee | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| EE/EMTA-TaxGuidance | Estonia Tax and Customs Board (EMTA) Guidance | 学说 | https://www.emta.ee/en | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| EE/AKI | Estonian Data Protection Authority (AKI) | 学说 | https://www.aki.ee | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-SE"></a>
## 瑞典（SE）— 7 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| SE/RiksdagenDB | Riksdag - Swedish Parliament | 法规 | https://data.riksdagen.se | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| SE/SvenskaForfattningssamlingen | Svenska Forfattningssamlingen (SFS) - Swedish Legislation | 法规 | https://www.riksdagen.se | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| SE/Domstolverket | Swedish Courts (Domstolsverket) | 判例 | https://rattspraxis.etjanst.domstol.se | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| SE/SupremeAdministrativeCourt | Swedish Supreme Administrative Court (Högsta förvaltningsdomstolen) | 判例 | https://rattspraxis.etjanst.domstol.se | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| SE/SupremeCourt | Swedish Supreme Court (Högsta domstolen) | 判例 | https://rattspraxis.etjanst.domstol.se | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| SE/IMY | Swedish Data Protection Authority (IMY) | 学说 | https://www.imy.se | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| SE/SKV | Swedish Tax Agency (Skatteverket) | 学说 | https://lagen.nu/dataset/myndfs?rpubl_forfattningssamling=skvfs | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-CH"></a>
## 瑞士（CH）— 12 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| CH/VD-Legislation | Canton de Vaud - Recueil systématique (BLV) | 法规 | https://prestations.vd.ch/pub/blv-publication/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CH/Fedlex | Fedlex - Swiss Federal Legislation | 法规 | https://fedlex.data.admin.ch | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CH/BS-Legislation | Kanton Basel-Stadt Gesetzessammlung (SG) | 法规 | https://www.gesetzessammlung.bs.ch/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CH/BE-Legislation | Kanton Bern Gesetzessammlung (BSG) | 法规 | https://www.belex.sites.be.ch/app/de/systematic/texts_of_law | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CH/ZH-Legislation | Kanton Zürich - Zürcher Gesetzessammlung (LS) | 法规 | https://www.zh.ch/de/politik-staat/gesetze-beschluesse/gesetzessammlung.html | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CH/GE-Legislation | République et Canton de Genève - Recueil systématique | 法规 | https://silgeneve.ch/legis/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CH/Kantone | Swiss Cantonal Legislation (All 26 Cantons) | 法规 | https://huggingface.co/datasets/rcds/swiss_legislation | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CH/ZurichGesetzessammlung | Zurich Law Collection (TEI-XML) via opendata.swiss | 法规 | https://opendata.swiss/en/dataset/erlasse-der-zurcher-gesetzessammlung-seit-1803 | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CH/Entscheidsuche | Entscheidsuche - Swiss Court Decisions | 判例 | https://entscheidsuche.ch | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| CH/OpenCaseLaw | Swiss OpenCaseLaw (Entscheidsuche Bulk) | 判例 | https://entscheidsuche.ch/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| CH/Kantone-TaxCirculars | Swiss Cantonal Tax Circulars (Schwyz, Nidwalden) | 学说 | https://www.sz.ch/finanzdepartement/steuerverwaltung/rechtliche-grundlagen/schwyzer-steuerbuch.html | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| CH/ESTV | Swiss Federal Tax Administration (ESTV) | 学说 | https://www.estv.admin.ch | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-BY"></a>
## 白俄罗斯（BY）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| BY/PravoBy | Belarus National Legal Portal (Codes) | 法规 | https://etalonline.by | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-GI"></a>
## 直布罗陀（GI）— 3 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| GI/GibraltarLaws | Laws of Gibraltar (gibraltarlaws.gov.gi) | 法规/判例 | https://www.gibraltarlaws.gov.gi/ | 类案检索、裁判观点抽取、法院/法官趋势分析；法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| GI/SupremeCourt | Gibraltar Supreme Court Judgments | 判例 | https://www.gibraltarlaws.gov.gi/judgments | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| GI/IncomeTax-Guidance | Gibraltar Income Tax Office Practice Notes | 学说 | https://www.gibraltar.gov.gi/income-tax-office | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-XK"></a>
## 科索沃（XK）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| XK/GazetaZyrtare | Gazeta Zyrtare - Kosovo Official Gazette | 法规 | https://gzk.rks-gov.net | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| XK/ConstitutionalCourt | Kosovo Constitutional Court (Gjykata Kushtetuese) | 判例 | https://gjk-ks.org | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |

<a name="c-LT"></a>
## 立陶宛（LT）— 3 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| LT/LegalBase | Lithuanian Legal Database (TAR) | 法规 | https://data.gov.lt/datasets/2613/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| LT/Parliament | Lithuanian Parliament (Seimas) | 法规 | https://data.gov.lt/datasets/2609/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| LT/ConstitutionalCourt | Lithuanian Constitutional Court (Konstitucinis Teismas) | 判例 | https://www.lrkt.lt | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |

<a name="c-RO"></a>
## 罗马尼亚（RO）— 4 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| RO/LegislationDatabase | Portal Legislativ (Romanian Legislative Portal) | 法规 | https://legislatie.just.ro | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐ |
| RO/ANSPDCP | Romanian Data Protection Authority (ANSPDCP) | 判例 | https://www.dataprotection.ro | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| RO/ICCJ | Romanian High Court of Cassation and Justice (ICCJ) | 判例 | https://www.scj.ro | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| RO/ANAF | Romanian Tax Authority (ANAF) | 学说 | https://www.anaf.ro | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-FI"></a>
## 芬兰（FI）— 5 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| FI/FinlexOD | Finland Finlex Open Data (Linked Data) | 法规/判例 | https://www.finlex.fi/en/open-data | 类案检索、裁判观点抽取、法院/法官趋势分析；法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| FI/Finlex | Finlex - Finnish Legal Database | 法规/判例 | https://www.finlex.fi | 类案检索、裁判观点抽取、法院/法官趋势分析；法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| FI/SupremeAdministrativeCourt | Finnish Supreme Administrative Court | 判例 | https://www.kho.fi | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| FI/SupremeCourt | Finnish Supreme Court (Korkein oikeus) | 判例 | https://www.korkeinoikeus.fi | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| FI/Vero-Guidance | Finnish Tax Authority Detailed Guidance | 学说 | https://www.vero.fi/en/detailed-guidance/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-UK"></a>
## 英国（UK）— 38 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| UK/Legislation | UK Legislation (legislation.gov.uk) | 法规 | https://www.legislation.gov.uk | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| UK/JCPC-Crown | Judicial Committee of the Privy Council (Crown Dependencies) | 判例 | https://caselaw.nationalarchives.gov.uk | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| UK/CAT | UK Competition Appeal Tribunal | 判例 | https://www.catribunal.org.uk | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| UK/ET | UK Employment Tribunals | 判例 | https://www.gov.uk/employment-tribunal-decisions | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| UK/FindCaseLaw | UK Find Case Law (National Archives) | 判例 | https://caselaw.nationalarchives.gov.uk/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| UK/FTT-Tax | UK First-tier Tribunal - Tax Chamber | 判例 | https://www.gov.uk | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| UK/IAC | UK Immigration and Asylum Chamber | 判例 | https://www.gov.uk | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| UK/PHSO | UK Parliamentary and Health Service Ombudsman | 判例 | https://decisions.ombudsman.org.uk | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| UK/PlanningAppeals | UK Planning Appeal Decisions | 判例 | https://acp.planninginspectorate.gov.uk | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| UK/HMRC-Manuals | HMRC Tax Guidance Manuals | 学说 | https://www.gov.uk/government/collections/hmrc-manuals | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/ASA | UK Advertising Standards Authority (ASA) | 学说 | https://www.asa.org.uk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/CC | UK Charity Commission | 学说 | https://www.gov.uk/government/organisations/charity-commission | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/CAA | UK Civil Aviation Authority (CAA) | 学说 | https://www.caa.co.uk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/Ofcom | UK Communications Regulator (Ofcom) | 学说 | https://www.ofcom.org.uk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/CMA | UK Competition and Markets Authority (CMA) | 学说 | https://www.gov.uk/cma-cases | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/EC | UK Electoral Commission | 学说 | https://www.electoralcommission.org.uk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/EA | UK Environment Agency | 学说 | https://www.gov.uk/government/organisations/environment-agency | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/FCA | UK Financial Conduct Authority (FCA) | 学说 | https://www.fca.org.uk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/FSA | UK Food Standards Agency (FSA) | 学说 | https://www.food.gov.uk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/GC | UK Gambling Commission | 学说 | https://www.gamblingcommission.gov.uk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/Ofgem | UK Gas and Electricity Markets Authority (Ofgem) | 学说 | https://www.ofgem.gov.uk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/HMLR | UK HM Land Registry | 学说 | https://www.gov.uk/government/organisations/land-registry | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/HMRC-Excise | UK HMRC Excise Decisions | 学说 | https://www.gov.uk/government/organisations/hm-revenue-customs | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/HMRC | UK HMRC Tax Manuals | 学说 | https://www.gov.uk/hmrc-internal-manuals | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/ICO | UK Information Commissioner (ICO) | 学说 | https://ico.org.uk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/MCA | UK Maritime and Coastguard Agency | 学说 | https://www.gov.uk/government/organisations/maritime-and-coastguard-agency | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/MHRA | UK Medicines Agency (MHRA) | 学说 | https://www.gov.uk/government/organisations/medicines-and-healthcare-products-regulatory-agency | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/NAO | UK National Audit Office | 学说 | https://www.nao.org.uk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/NCA | UK National Crime Agency (AML Unit) | 学说 | https://www.nationalcrimeagency.gov.uk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/ONR | UK Office for Nuclear Regulation (ONR) | 学说 | https://www.onr.org.uk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/ORR | UK Office of Rail and Road | 学说 | https://www.orr.gov.uk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/TPR | UK Pensions Regulator | 学说 | https://www.thepensionsregulator.gov.uk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/IPSO | UK Press Standards Organisation | 学说 | https://www.ipso.co.uk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/PRA | UK Prudential Regulation Authority (PRA) | 学说 | https://www.bankofengland.co.uk/prudential-regulation | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/RPB | UK Recognised Professional Bodies (Insolvency) | 学说 | https://www.gov.uk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/SRA | UK Solicitors Regulation Authority | 学说 | https://www.sra.org.uk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/TRA | UK Trade Remedies Authority | 学说 | https://www.trade-remedies.service.gov.uk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| UK/Ofwat | UK Water Services Regulation (Ofwat) | 学说 | https://www.ofwat.gov.uk | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-NL"></a>
## 荷兰（NL）— 14 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| NL/wetten.overheid.nl | Dutch Legislation Portal (wetten.overheid.nl) | 法规 | https://www.wetten.overheid.nl | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| NL/Staatsblad | Staatsblad der Nederlanden - Dutch Official Gazette | 法规 | https://www.staatsblad.nl | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| NL/CRvB | Dutch Central Appeals Tribunal | 判例 | https://www.rechtspraak.nl | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| NL/Rechtspraak | Dutch Court Decisions (All Courts - rechtspraak.nl) | 判例 | https://www.rechtspraak.nl | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| NL/AP | Dutch Data Protection Authority (Autoriteit Persoonsgegevens) | 判例/学说 | https://www.autoriteitpersoonsgegevens.nl | 类案检索、裁判观点抽取、法院/法官趋势分析；法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| NL/SupremeCourt | Dutch Supreme Court (Hoge Raad) | 判例 | https://www.rechtspraak.nl | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| NL/HR-Belasting | Dutch Supreme Court - Tax Chamber | 判例 | https://www.rechtspraak.nl | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| NL/ACM-Telecom | Dutch ACM - Telecom/Energy | 学说 | https://www.acm.nl | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| NL/Belastingdienst-AdvanceTaxRulings | Dutch Advance Tax Rulings (ATR/APA) Policy | 学说 | https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/standaard_functies/prive/contact/rechten_en_plichten_bij_de_belastingdienst/ruling/atr | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| NL/DNB | Dutch Central Bank - Supervision (DNB) | 学说 | https://www.dnb.nl | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| NL/ACM | Dutch Competition Authority (ACM) | 学说 | https://www.acm.nl | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| NL/AFM | Dutch Financial Markets Authority (AFM) | 学说 | https://www.afm.nl | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| NL/TweedeKamer | Dutch House of Representatives (Tweede Kamer) | 学说 | https://opendata.tweedekamer.nl | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| NL/Belastingdienst | Dutch Tax Administration (Belastingdienst) | 学说 | https://www.belastingdienst.nl | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-PT"></a>
## 葡萄牙（PT）— 10 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| PT/DiarioRepublica | Diário da República - Portuguese Official Gazette | 法规 | https://www.dre.pt | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| PT/Parlamento | Portuguese Parliament Open Data (Assembleia da República) | 法规 | https://www.parlamento.pt/Cidadania/Paginas/DadosAbertos.aspx | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| PT/ConstitutionalCourt | Portuguese Constitutional Court (Tribunal Constitucional) | 判例 | https://www.tribunalconstitucional.pt | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| PT/TribunalContas | Portuguese Court of Auditors (Tribunal de Contas) | 判例 | https://tcjure.tcontas.pt | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| PT/DGSI | Portuguese Courts of Appeal (DGSI - all sub-databases) | 判例 | https://www.dgsi.pt | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| PT/STA | Portuguese Supreme Administrative Court (Supremo Tribunal Administrativo) | 判例 | https://www.dgsi.pt | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| PT/SupremeCourt | Portuguese Supreme Court (Supremo Tribunal de Justiça) | 判例 | https://juris.stj.pt | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| PT/CNPD | Portuguese Data Protection Authority (CNPD) | 学说 | https://www.cnpd.pt | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| PT/AT | Portuguese Tax Authority (AT) | 学说 | https://info.portaldasfinancas.gov.pt | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| PT/AT-InformacoesVinculativas | Portuguese Tax Authority Binding Information | 学说 | https://info.portaldasfinancas.gov.pt/pt/informacao_fiscal/informacoes_vinculativas/Pages/default.aspx | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-ES"></a>
## 西班牙（ES）— 10 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| ES/Andalusia | Andalusia Regional Legislation (BOJA) | 法规 | https://datos.juntadeandalucia.es | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| ES/BOE | BOE - Boletín Oficial del Estado | 法规 | https://www.boe.es | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| ES/BasqueCountry | Basque Country Regional Legislation (BOPV/EHAA) | 法规 | https://opendata.euskadi.eus | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| ES/Catalonia | Catalan Regional Legislation (DOGC) | 法规 | https://analisi.transparenciacatalunya.cat/d/n6hn-rmy7 | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| ES/Madrid | Madrid Regional Legislation | 法规 | https://www.bocm.es | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| ES/ConstitutionalCourt | Spanish Constitutional Court (Tribunal Constitucional) | 判例 | https://hj.tribunalconstitucional.es | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| ES/AEPD | Spanish Data Protection Authority (AEPD) | 判例 | https://www.aepd.es | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| ES/TEAC | Spanish Tax Administrative Tribunal (TEAC) | 判例 | https://www.tribunaleseconomico-administrativos.gob.es | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| ES/CNMV | Spanish Securities Commission (CNMV) | 学说 | https://www.cnmv.es | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| ES/DGT-Consultas | Spanish Tax Binding Rulings (Consultas Vinculantes DGT) | 学说 | https://petete.tributos.hacienda.gob.es/consultas | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-AL"></a>
## 阿尔巴尼亚（AL）— 3 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| AL/QBZ | Qendra e Botimeve Zyrtare - Albanian Official Gazette | 法规 | https://www.qbz.gov.al | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| AL/ConstitutionalCourt | Albanian Constitutional Court (Gjykata Kushtetuese) | 判例 | https://www.gjykatakushtetuese.gov.al | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| AL/SupremeCourt | Albanian Supreme Court (Gjykata e Lartë) | 判例 | https://www.gjykataelarte.gov.al | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-IM"></a>
## 马恩岛（IM）— 3 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| IM/Legislation | Isle of Man Legislation (Acts of Tynwald) | 法规 | https://legislation.gov.im/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| IM/JudgmentsOnline | Isle of Man Judgments Online | 判例 | https://www.judgments.im/content/home.mth | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| IM/IncomeTax-Guidance | Isle of Man Income Tax Division Practice Notes | 学说 | https://www.gov.im/categories/tax-vat-and-your-money/income-tax-and-national-insurance/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-MT"></a>
## 马耳他（MT）— 3 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| MT/GovernmentGazette | Malta Government Gazette | 法规 | https://legislation.mt | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| MT/OAFS | Malta Office of the Arbiter for Financial Services | 判例 | https://www.financialarbiter.org.mt/oafs/decisions | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| MT/MFSA-Enforcement | Malta Financial Services Authority Enforcement | 学说 | https://www.mfsa.mt/enforcement/administrative-penalties/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-ME"></a>
## 黑山（ME）— 3 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| ME/SluzbenList | Službeni list Crne Gore - Montenegro Official Gazette | 法规 | https://www.sluzbenilist.me | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| ME/ConstitutionalCourt | Montenegro Constitutional Court (Ustavni sud Crne Gore) | 判例 | http://www.ustavnisud.me | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| ME/Courts | Montenegro Court Decisions (Sudovi.me) | 判例 | https://sudovi.me | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

# 地区：美洲

<a name="c-UY"></a>
## 乌拉圭（UY）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| UY/IMPO | IMPO - Centro de Información Oficial | 法规 | https://parlamento.gub.uy/documentosyleyes/leyes | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| UY/IMPODatosAbiertos | Uruguay IMPO Open Data JSON API | 法规 | https://www.impo.com.uy/datos-abiertos/ | 法规检索、合规义务映射、法条版本/更新监测；宪法条文检索 | ⭐⭐⭐⭐⭐ |

<a name="c-CA"></a>
## 加拿大（CA）— 20 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| CA/AB-QP | Alberta Queens Printer Legislation | 法规 | https://www.kings-printer.alberta.ca/legislation.aspx | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CA/BCLaws | British Columbia Laws (Official XML API) | 法规 | https://www.bclaws.gov.bc.ca | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CA/BC-Laws | British Columbia Laws (bclaws.gov.bc.ca) | 法规 | https://www.bclaws.gov.bc.ca/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CA/CanadaGazette | Canada Gazette (Official Gazette) | 法规 | https://gazette.gc.ca | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| CA/FederalLegislation | Federal Laws and Regulations (Justice Laws Website) | 法规 | https://laws-lois.justice.gc.ca | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CA/LegisQuebec | LegisQuebec (Quebec Provincial Legislation) | 法规 | https://www.legisquebec.gouv.qc.ca/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CA/MB-Legislation | Manitoba Laws (web2.gov.mb.ca/laws) | 法规 | https://web2.gov.mb.ca/laws/statutes/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CA/NWTLaws | Northwest Territories Legislation | 法规 | https://www.justice.gov.nt.ca/en/legislation/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CA/NS-Legislation | Nova Scotia Legislature (nslegislature.ca) | 法规 | https://www.nslegislature.ca/legislative-business/bills-statutes | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CA/NunavutLegislation | Nunavut Consolidated Legislation | 法规 | https://www.nunavutlegislation.ca/en | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CA/OntarioLaws | Ontario e-Laws (Provincial Legislation) | 法规 | https://www.ontario.ca/laws | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CA/PEILegislation | Prince Edward Island Legislation | 法规 | https://www.princeedwardisland.ca/en/legislation | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CA/YukonLaws | Yukon Consolidated Laws | 法规 | https://laws.yukon.ca/cms/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CA/A2AJ | A2AJ Canadian Legal Data (Multi-Court Case Law) | 判例 | https://a2aj.ca/canadian-legal-data/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| CA/SupremeCourt | Supreme Court of Canada Decisions | 判例 | https://decisions.scc-csc.ca | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| CA/TCC | Tax Court of Canada Decisions | 判例 | https://decision.tcc-cci.gc.ca/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| CA/CompetitionBureau | Canada Competition Bureau | 学说 | https://competition-bureau.canada.ca/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| CA/CRA-TaxDoctrine | Canada Revenue Agency Tax Doctrine | 学说 | https://www.canada.ca/en/revenue-agency/services/tax/technical-information/income-tax.html | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| CA/PrivacyCommissioners | Office of the Privacy Commissioner of Canada — Investigation Findings | 学说 | https://www.priv.gc.ca/en/opc-actions-and-decisions/investigations/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| CA/OpenParliament | OpenParliament (Hansard, Bills, Votes) | 学说 | https://openparliament.ca | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-GT"></a>
## 危地马拉（GT）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| GT/CC | Guatemala Corte de Constitucionalidad | 判例 | https://cc.gob.gt/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-EC"></a>
## 厄瓜多尔（EC）— 3 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| EC/AsambleaNacional | Ecuador Legislation (oficial.ec) | 法规 | https://www.oficial.ec/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| EC/CorteConstitucional | Ecuador Constitutional Court Case Law | 判例 | https://buscador.corteconstitucional.gob.ec | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| EC/Contraloria | Ecuador Contraloria General - Audit Resolutions | 学说 | https://www.contraloria.gob.ec/Portal/24287 | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-CU"></a>
## 古巴（CU）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| CU/GacetaOficialDigital | Cuba Official Gazette Digital Archive | 法规 | https://www.gacetaoficial.gob.cu/ | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |

<a name="c-CO"></a>
## 哥伦比亚（CO）— 9 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| CO/SecretariaSenado | Colombia Secretaria del Senado Laws | 法规 | http://www.secretariasenado.gov.co/leyes-de-la-republica | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CO/SUINJuriscol | SUIN-Juriscol (Normative Information System) | 法规 | https://www.suin-juriscol.gov.co/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CO/ConsejoDeEstado | Colombia Council of State Jurisprudence | 判例 | https://relatoria.consejodeestado.gov.co/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| CO/DatosGovCo | Colombia Datos Abiertos - Constitutional Court Rulings | 判例 | https://www.datos.gov.co/Justicia-y-Derecho/Sentencias-proferidas-por-la-Corte-Constitucional/v2k4-2t8s | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| CO/Procuraduria | Colombia Procuraduria - Disciplinary Decisions (Relatoria) | 判例 | https://www.datos.gov.co/Organismos-de-Control/Datos-abiertos-de-la-Relator-a-de-la-Procuradur-a-/rhun-uf37 | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| CO/SIC | Colombia SIC - Competition & Consumer Protection Authority | 判例 | https://www.sic.gov.co | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| CO/CorteConstitucional | Colombian Constitutional Court (Socrata API) | 判例 | https://www.datos.gov.co/resource/v2k4-2t8s.json | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| CO/CorteSuprema | Colombian Supreme Court Jurisprudence | 判例 | https://consultaprovidencias.cortesuprema.gov.co/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| CO/DIAN-DoctrinaTributaria | Colombian DIAN Tax Doctrine - Conceptos y Oficios (normograma.dian.gov.co) | 学说 | https://normograma.dian.gov.co/dian/compilacion/t_2_doctrina_tributaria.html | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-CR"></a>
## 哥斯达黎加（CR）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| CR/SCIJ | SCIJ - Sistema Costarricense de Información Jurídica | 法规 | http://www.pgrweb.go.cr/scij/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CR/PoderJudicial | Costa Rica Poder Judicial - Jurisprudencia | 判例 | https://nexuspj.poder-judicial.go.cr/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-LC"></a>
## 圣卢西亚（LC）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| LC/Legislation | Saint Lucia Revised Laws (Attorney General) | 法规 | https://attorneygeneralchambers.com/laws-of-saint-lucia | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-KN"></a>
## 圣基茨和尼维斯（KN）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| KN/LawCommission | St Kitts & Nevis Law Commission | 法规 | https://lawcommission.gov.kn/laws/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-BL"></a>
## 圣巴泰勒米（BL）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| BL/Codes | Saint-Barthelemy Codes & Regulations | 法规 | https://www.comstbarth.fr/votre-collectivite/codes-et-reglements | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-VC"></a>
## 圣文森特和格林纳丁斯（VC）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| VC/FSA | St Vincent & Grenadines Financial Services Authority | 学说 | https://fsasvg.com/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-PM"></a>
## 圣皮埃尔和密克隆群岛（PM）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| PM/JOSPM | Journal Officiel de Saint-Pierre-et-Miquelon | 法规 | https://www.jo-spm.fr/ | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |

<a name="c-MX"></a>
## 墨西哥（MX）— 8 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| MX/CDMX-Legislation | Ciudad de México Legislation (congresocdmx.gob.mx) | 法规 | https://www.congresocdmx.gob.mx/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| MX/DOF | Diario Oficial de la Federacion (DOF) | 法规 | https://www.dof.gob.mx/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| MX/Jalisco-Legislation | Jalisco State Legislation (congresojal.gob.mx) | 法规 | https://congresoweb.congresojal.gob.mx/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| MX/OrdenJuridicoEstatal | Mexico Orden Juridico Nacional - State Legislation | 法规 | https://www.ordenjuridico.gob.mx/leyes | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| MX/Puebla-Legislation | Puebla State Legislation (congresopuebla.gob.mx) | 法规 | https://www.congresopuebla.gob.mx/index.php?option=com_docman&Itemid=485 | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| MX/SCJNDatosAbiertosAPI | Mexico SCJN Open Data Platform (JSON API) | 判例 | https://sjf.scjn.gob.mx/SJFHome/home | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| MX/PoderJudicialJalisco | Poder Judicial del Estado de Jalisco | 判例 | https://publicacionsentencias.stjjalisco.gob.mx/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| MX/SAT-Criterios | SAT Tax Criteria (Criterios Normativos y No Vinculativos) | 学说 | https://wwwmat.sat.gob.mx/normatividad/68264/leyes | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-DM"></a>
## 多米尼克（DM）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| DM/Legislation | Laws of Dominica | 法规 | https://dominica.gov.dm/laws-of-dominica | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-DO"></a>
## 多米尼加共和国（DO）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| DO/CongresoRD | Dominican Republic Legislation (Consultoría Jurídica) | 法规 | https://www.consultoria.gov.do/consulta/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| DO/CorteSuprema | Dominican Republic Suprema Corte de Justicia | 判例 | https://www.poderjudicial.gob.do/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-VE"></a>
## 委内瑞拉（VE）— 3 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| VE/AsambaleaNacional | Venezuela Asamblea Nacional - Gaceta Oficial Digital | 法规 | https://www.asambleanacional.gob.ve/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| VE/TSJGaceta | Venezuela Legislation (via Justia) | 法规 | https://venezuela.justia.com/federales/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| VE/TSJDecisiones | Venezuela Supreme Court Decisions (TSJ) | 判例 | https://www.tsj.gob.ve/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-AG"></a>
## 安提瓜和巴布达（AG）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| AG/Legislation | Antigua & Barbuda Laws (OECS) | 法规 | https://laws.gov.ag/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-NI"></a>
## 尼加拉瓜（NI）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| NI/Legislacion | Nicaragua National Assembly Legislation | 法规 | http://legislacion.asamblea.gob.ni/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-BS"></a>
## 巴哈马（BS）— 6 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| BS/Legislation | Bahamas Consolidated Legislation | 法规 | https://laws.bahamas.gov.bs/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| BS/BahamasLegislation | Bahamas Legislation | 法规 | https://laws.bahamas.gov.bs/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| BS/CourtOfAppeal | Bahamas Court of Appeal Judgments | 判例 | https://www.courtofappeal.org.bs/judgments.php | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BS/SupremeCourt | Bahamas Supreme Court Judgments | 判例 | https://courts.bs/judgments/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BS/DIR-TaxGuidance | Bahamas Department of Inland Revenue VAT Guidance | 学说 | https://inlandrevenue.finance.gov.bs | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| BS/SCB | Securities Commission of the Bahamas Enforcement | 学说 | https://www.scb.gov.bs/enforcement-actions/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-BB"></a>
## 巴巴多斯（BB）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| BB/Statutes | Statutes of Barbados (Attorney General) | 法规 | https://oag.gov.bb/Laws/Consolidated-Laws/Statutes-of-Barbados/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-PY"></a>
## 巴拉圭（PY）— 4 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| PY/LeyesParaguayas | Paraguay - Leyes Paraguayas | 法规 | https://www.bacn.gov.py/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| PY/BACN | Paraguay Congressional Law Library (BACN) | 法规 | https://www.bacn.gov.py/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| PY/TSJE | Paraguay Electoral Justice Tribunal (TSJE) | 判例 | https://www.tsje.gov.py/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| PY/CSJJurisprudencia | Paraguay Supreme Court Jurisprudence | 判例 | https://www.csj.gov.py/jurisprudencia/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-PA"></a>
## 巴拿马（PA）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| PA/CorteSuprema | Panama Corte Suprema de Justicia - Jurisprudencia | 判例 | https://www.organojudicial.gob.pa/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| PA/DGI-TaxGuidance | Panama DGI Tax Resolutions and Guidance | 学说 | https://dgi.mef.gob.pa | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-BR"></a>
## 巴西（BR）— 17 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| BR/ANATEL | ANATEL - Brazilian Telecom Regulatory Agency | 法规 | https://informacoes.anatel.gov.br/legislacao/resolucoes | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| BR/Planalto | Brazil Planalto Federal Legislation (REFLEGIS) | 法规 | https://legislacao.presidencia.gov.br/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| BR/CamaraDeputados | Chamber of Deputies Open Data API | 法规 | https://dadosabertos.camara.leg.br/swagger/api.html | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| BR/QueridoDiario | Querido Diário - Brazilian Municipal Official Gazettes | 法规 | https://queridodiario.ok.org.br | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| BR/TCU | Brazil Federal Audit Court (TCU) Decisions | 判例/学说 | https://sites.tcu.gov.br/dados-abertos/jurisprudencia/ | 类案检索、裁判观点抽取、法院/法官趋势分析；法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| BR/TRF1 | Brazil TRF-1 Federal Regional Court (1st Region) | 判例 | https://www.trf1.jus.br/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BR/TRF2 | Brazil TRF-2 Federal Regional Court (2nd Region - RJ/ES) | 判例 | https://www.trf2.jus.br/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BR/TRF4 | Brazil TRF-4 Federal Regional Court (4th Region - RS/PR/SC) | 判例 | https://jurisprudencia.trf4.jus.br/eproc2trf4/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BR/BrazilianCourtDecisionsHF | Brazilian Court Decisions (HuggingFace) | 判例 | https://huggingface.co/datasets/joelniklaus/brazilian_court_decisions | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BR/CVM | CVM - Brazilian Securities Commission Open Data | 判例 | https://dados.cvm.gov.br/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BR/STJDadosAbertos | STJ Open Data Portal (Superior Court of Justice) | 判例 | https://dadosabertos.web.stj.jus.br/dataset/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BR/TJBA | TJBA - Bahia State Court (GraphQL API) | 判例 | https://jurisprudencia.tjba.jus.br/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BR/TJDFT | TJDFT - Federal District Court Open Data API | 判例 | https://www.tjdft.jus.br/transparencia/dados-abertos/webservice-ou-api | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BR/TJPR | TJPR - Parana State Court Jurisprudence | 判例 | https://portal.tjpr.jus.br/jurisprudencia/publico/pesquisa.do | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BR/TST | TST - Tribunal Superior do Trabalho (Labor Supreme Court) | 判例 | https://jurisprudencia.tst.jus.br/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BR/RFB-SolucoesConsulta | Brazilian Federal Revenue Tax Rulings (Soluções de Consulta) | 学说 | http://normas.receita.fazenda.gov.br/sijut2consulta/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| BR/CARF | Brazilian Tax Appeals Council (CARF - Conselho Administrativo de Recursos Fiscais) | 学说 | https://carf.fazenda.gov.br/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-CW"></a>
## 库拉索（CW）— 3 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| CW/Legislation | Curacao Government Legislation (Regelingen) | 法规 | https://gobiernu.cw/nl/regelingen/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CW/Courts | Curaçao Court Decisions (Gemeenschappelijk Hof) | 判例 | https://uitspraken.rechtspraak.nl/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| CW/Belastingdienst-Guidance | Curaçao Tax Administration Guidance | 学说 | https://www.belastingdienst.cw | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-KY"></a>
## 开曼群岛（KY）— 4 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| KY/Legislation | Cayman Islands Legislation | 法规 | https://legislation.gov.ky/cms/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| KY/OfficialGazette | Cayman Islands Official Gazette | 法规 | https://legislation.gov.ky/cms/legislation/current/by-title.html | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| KY/Judgments | Cayman Islands Court Judgments (judicial.ky) | 判例 | https://judicial.ky/judgments/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| KY/DITC-TaxGuidance | Cayman Islands Dept of International Tax Cooperation Guidance | 学说 | https://www.ditc.ky | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-CL"></a>
## 智利（CL）— 6 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| CL/BCNLeyChile | BCN Ley Chile (Biblioteca del Congreso Nacional) | 法规 | https://datos.bcn.cl/es/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CL/BCNLinkedData | Chile BCN Linked Open Data (SPARQL) | 法规 | https://datos.bcn.cl/es/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CL/TDLC | Chile TDLC - Competition Tribunal (Tribunal de Libre Competencia) | 判例 | https://www.tdlc.cl/sentencia/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| CL/TribunalConstitucional | Chilean Constitutional Court | 判例 | https://tcchile.cl/busqueda/busqueda.php | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| CL/Contraloria | Chile Contraloria General - Administrative Jurisprudence | 学说 | https://www.contraloria.cl/web/cgr/buscar-jurisprudencia | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| CL/SII-TaxDoctrine | Chilean Internal Revenue Service Tax Circulars (SII Circulares) | 学说 | https://www.sii.cl/normativa_legislacion/index_normativa_legislacion.html | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-GD"></a>
## 格林纳达（GD）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| GD/Laws | Laws of Grenada | 法规 | https://laws.gov.gd/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-GL"></a>
## 格陵兰（GL）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| GL/Lovgivning | Greenland Legislation (Nalunaarutit) | 法规 | https://nalunaarutit.gl/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-MF"></a>
## 法属圣马丁（MF）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| MF/Deliberations | Saint-Martin Territorial Council Deliberations | 法规 | https://www.com-saint-martin.fr/deliberations_actes/deliberations | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-JM"></a>
## 牙买加（JM）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| JM/SupremeCourt | Jamaica Supreme Court Judgments (supremecourt.gov.jm) | 判例 | https://supremecourt.gov.jm/content/judgments | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-TC"></a>
## 特克斯和凯科斯群岛（TC）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| TC/RevisedLaws | Turks and Caicos Revised Laws (Attorney General) | 法规 | https://gov.tc/agc/laws/revised | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| TC/Courts | Turks & Caicos Islands Court Decisions | 判例 | https://tcilii.org/judgments/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-BO"></a>
## 玻利维亚（BO）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| BO/GacetaOficial | Bolivia Official Gazette (Gaceta Oficial) | 法规 | https://www.lexivox.org | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| BO/TribunalAgroambiental | Bolivia Tribunal Agroambiental - Environmental/Agrarian Court | 判例 | https://arbol.tribunalagroambiental.bo/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-BM"></a>
## 百慕大（BM）— 5 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| BM/Legislation | Bermuda Laws Online | 法规 | https://www.bermudalaws.bm/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| BM/CourtJudgments | Bermuda Court Judgments (gov.bm) | 判例 | https://www.gov.bm/court-judgments | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BM/SupremeCourt | Bermuda Supreme Court Judgments | 判例 | https://www.gov.bm/supreme-court | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BM/BMA-Guidance | Bermuda Monetary Authority Regulatory Guidance | 学说 | https://www.bma.bm/guidance-notes | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| BM/OTC-TaxGuidance | Bermuda Office of Tax Commissioner Guidance | 学说 | https://www.gov.bm/department/office-tax-commissioner | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-FK"></a>
## 福克兰群岛（FK）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| FK/Legislation | Falkland Islands Legislation | 法规 | https://www.legislation.gov.fk/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-PE"></a>
## 秘鲁（PE）— 4 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| PE/INDECOPI | Peru INDECOPI - Competition & IP Tribunal Resolutions | 判例 | https://repositorio.indecopi.gob.pe/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| PE/OSCE | Peru OSCE - Public Procurement Tribunal Resolutions | 判例 | https://www.gob.pe/institucion/oece/colecciones/716-resoluciones-del-tribunal-de-contrataciones-del-estado | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| PE/TribunalConstitucional | Peruvian Constitutional Court | 判例 | https://tc.gob.pe/jurisprudencia/ | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| PE/SUNAT-Informes | Peru SUNAT Tax Authority Guidance (Informes) | 学说 | https://www.sunat.gob.pe/legislacion/oficios/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-US"></a>
## 美国（US）— 103 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| US/AL-Legislation | Alabama Code of 1975 (ALISON GraphQL) | 法规 | https://alison.legislature.state.al.us/code-of-alabama | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/AK-Legislation | Alaska Statutes (akleg.gov) | 法规 | https://www.akleg.gov/basis/statutes.asp | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/AZ-Legislation | Arizona Revised Statutes (azleg.gov) | 法规 | https://www.azleg.gov/arstitle/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/CA-AdminCode | California Code of Regulations (CCR) | 法规 | https://www.law.cornell.edu/regulations/california | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/CA-Legislation | California Legislative Information (LegInfo FTP/MySQL) | 法规 | https://leginfo.legislature.ca.gov/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/CT-Legislation | Connecticut General Statutes (cga.ct.gov) | 法规 | https://www.cga.ct.gov/current/pub/titles.htm | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/CornellLII | Cornell Legal Information Institute | 法规 | https://www.law.cornell.edu/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/DE-Legislation | Delaware Code (delcode.delaware.gov) | 法规 | https://delcode.delaware.gov/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/DC-Legislation | District of Columbia Code (code.dccouncil.gov) | 法规 | https://code.dccouncil.gov/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/FederalRegister | Federal Register | 法规 | https://www.federalregister.gov | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| US/FL-Statutes | Florida Statutes Download (Online Sunshine) | 法规 | https://www.leg.state.fl.us/Statutes/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/GovInfo | GovInfo (US Federal Legislation) | 法规 | https://www.govinfo.gov | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/HI-Legislation | Hawaii Revised Statutes (HRS) | 法规 | https://github.com/OpenHRS/openhrs-data | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/IA-Legislation | Iowa Code | 法规 | https://www.legis.iowa.gov/law/iowaCode | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/KS-Legislation | Kansas Statutes Annotated (kslegislature.gov) | 法规 | https://www.kslegislature.gov/li/b2025_26/statute/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/KY-Legislation | Kentucky Revised Statutes (legislature.ky.gov) | 法规 | https://apps.legislature.ky.gov/law/statutes/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/LA-Legislation | Louisiana Revised Statutes (legis.la.gov) | 法规 | https://legis.la.gov/legis/LawSearch.aspx | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/ME-Legislation | Maine Revised Statutes (legislature.maine.gov) | 法规 | https://legislature.maine.gov/statutes/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/MD-Legislation | Maryland Code and Statutes (mgaleg.maryland.gov) | 法规 | https://mgaleg.maryland.gov/mgawebsite/Laws/Statutes | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/MA-Legislation | Massachusetts General Laws (malegislature.gov) | 法规 | https://malegislature.gov/Laws/GeneralLaws | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/MN-Legislation | Minnesota Revisor of Statutes | 法规 | https://www.revisor.mn.gov/statutes/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/MO-Legislation | Missouri Revised Statutes (revisor.mo.gov) | 法规 | https://revisor.mo.gov/main/Home.aspx | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/MT-Legislation | Montana Code Annotated (leg.mt.gov) | 法规 | https://mca.legmt.gov/bills/mca/index.html | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/NE-Legislation | Nebraska Revised Statutes (nebraskalegislature.gov) | 法规 | https://nebraskalegislature.gov/laws/browse-statutes.php | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/NV-Legislation | Nevada Revised Statutes (leg.state.nv.us) | 法规 | https://www.leg.state.nv.us/nrs/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/NM-Legislation | New Mexico Statutes (nmonesource.com) | 法规 | https://nmonesource.com/nmos/nmsa/en/nav.do | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/NY-AdminCode | New York Codes Rules and Regulations (NYCRR) | 法规 | https://www.law.cornell.edu/regulations/new-york | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/NC-Legislation | North Carolina General Statutes (ncleg.gov) | 法规 | https://www.ncleg.gov/Laws/GeneralStatutes | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/ND-Legislation | North Dakota Century Code (ndlegis.gov) | 法规 | https://www.ndlegis.gov/general-information/north-dakota-century-code | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/GA-Legislation | Official Code of Georgia Annotated (O.C.G.A.) | 法规 | https://archive.org/details/gov.ga.ocga.2018 | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/OH-Legislation | Ohio Revised Code (LAWriter) | 法规 | https://codes.ohio.gov/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/OK-Legislation | Oklahoma Statutes (oklegislature.gov) | 法规 | https://www.oklegislature.gov/osStatuesTitle.aspx | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/PresidentialDocuments | Presidential Documents (Executive Orders, Proclamations) | 法规 | https://www.federalregister.gov | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| US/SC-Legislation | South Carolina Code of Laws (scstatehouse.gov) | 法规 | https://www.scstatehouse.gov/code/statmast.php | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/SD-Legislation | South Dakota Codified Laws (sdlegislature.gov) | 法规 | https://sdlegislature.gov/Statutes/Codified_Laws | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/TN-Legislation | Tennessee Code Annotated | 法规 | https://www.capitol.tn.gov/legislation/laws.html | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/TX-AdminCode | Texas Administrative Code (eLaws mirror) | 法规 | https://www.law.cornell.edu/regulations/texas | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/TX-Legislation | Texas Legislature Online (TLO) + Capitol Data Portal | 法规 | https://data.capitol.texas.gov/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/UT-Legislation | Utah Code (le.utah.gov) | 法规 | https://le.utah.gov/xcode/code.html | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/VA-Law | Virginia Law Portal (Code of Virginia + Admin Code) REST API | 法规 | https://law.lis.virginia.gov/developers/ | 法规检索、合规义务映射、法条版本/更新监测；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| US/WA-Legislation | Washington State Legislative Web Services (SOAP API) | 法规 | https://wslwebservices.leg.wa.gov/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/WV-Legislation | West Virginia Code (wvlegislature.gov) | 法规 | https://code.wvlegislature.gov/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/WY-Legislation | Wyoming Statutes (wyoleg.gov) | 法规 | https://wyoleg.gov/StateStatutes | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/eCFR | eCFR - Electronic Code of Federal Regulations | 法规 | https://www.ecfr.gov/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| US/AL-Courts | Alabama State Courts | 判例 | https://judicial.alabama.gov/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/AR-Courts | Arkansas State Courts | 判例 | https://arcourts.gov/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/CA-Courts | California State Courts | 判例 | https://courts.ca.gov/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/CaselawAccessProject | Caselaw Access Project (Harvard/HuggingFace) | 判例 | https://huggingface.co/datasets/common-pile/caselaw_access_project | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/CO-Courts | Colorado State Courts | 判例 | https://courts.state.co.us/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/CourtListenerBulk | CourtListener Bulk Data (Free Law Project) | 判例 | https://www.courtlistener.com/help/api/bulk-data/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/DE-Courts | Delaware State Courts | 判例 | https://courts.delaware.gov/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/FL-Courts | Florida State Courts | 判例 | https://flcourts.org/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/GovInfoUSCourts | GovInfo Federal Court Opinions (USCOURTS) | 判例 | https://www.govinfo.gov/app/collection/uscourts | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐ |
| US/GovInfoUSReports | GovInfo Supreme Court Opinions (US Reports) | 判例 | https://api.govinfo.gov | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐ |
| US/HI-Courts | Hawaii State Courts | 判例 | https://courts.state.hi.us/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/ID-Courts | Idaho State Courts | 判例 | https://isc.idaho.gov/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/IL-Courts | Illinois Courts Appellate Decisions | 判例 | https://www.illinoiscourts.gov/top-level-opinions/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/IN-Courts | Indiana Supreme Court & Court of Appeals | 判例 | https://www.in.gov/courts/opinions/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/IA-Courts | Iowa State Courts | 判例 | https://iowacourts.gov/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/JuriscraperUpdater | Juriscraper US Court Opinions (Daily Updates) | 判例 | https://github.com/freelawproject/juriscraper | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/KY-Courts | Kentucky Supreme Court & Court of Appeals | 判例 | https://appellatepublic.kycourts.net/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/LA-Courts | Louisiana Supreme Court & Courts of Appeal | 判例 | https://www.lasc.org/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/ME-Courts | Maine State Courts | 判例 | https://courts.maine.gov/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/MD-Courts | Maryland Court of Appeals & Special Appeals | 判例 | https://www.courts.state.md.us/appellate/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/MA-Courts | Massachusetts Supreme Judicial Court & Appeals Court | 判例 | https://www.mass.gov/orgs/supreme-judicial-court | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/MI-Courts | Michigan Supreme Court & Court of Appeals Opinions | 判例 | https://www.courts.michigan.gov/opinions/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/MN-Courts | Minnesota Supreme Court & Court of Appeals | 判例 | https://mn.gov/law-library/archive/supct/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/MS-Courts | Mississippi State Courts | 判例 | https://courts.ms.gov/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/MT-Courts | Montana State Courts | 判例 | https://courts.mt.gov/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/NV-Courts | Nevada Supreme Court & Court of Appeals | 判例 | https://nvcourts.gov/Supreme/Decisions/Advance_Opinions/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/NJ-Courts | New Jersey State Courts | 判例 | https://njcourts.gov/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/NY-Courts | New York State Courts | 判例 | https://nycourts.gov/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/NC-Courts | North Carolina Appellate Courts Opinions | 判例 | https://appellate.nccourts.org/opinions/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/OK-Courts | Oklahoma Supreme Court & Court of Civil/Criminal Appeals | 判例 | https://www.oscn.net/applications/oscn/Index.asp | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/PA-Courts | Pennsylvania State Courts | 判例 | https://pacourts.us/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/SC-Courts | South Carolina Supreme Court & Court of Appeals | 判例 | https://www.sccourts.org/opinions/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/TX-Courts | Texas State Courts | 判例 | https://txcourts.gov/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/BIA | US Board of Immigration Appeals Decisions | 判例 | https://www.justice.gov/eoir/board-of-immigration-appeals-decisions | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/EyeciteCitations | US Case Law Citation Index (Eyecite + CourtListener) | 判例 | https://free.law/projects/eyecite | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/CFTC | US Commodity Futures Trading Commission Orders | 判例/学说 | https://www.cftc.gov/LawRegulation/index.htm | 类案检索、裁判观点抽取、法院/法官趋势分析；法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| US/CFPB | US Consumer Financial Protection Bureau Enforcement | 判例/学说 | https://www.consumerfinance.gov/enforcement/actions/ | 类案检索、裁判观点抽取、法院/法官趋势分析；法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| US/DOL | US Department of Labor Administrative Decisions (OALJ) | 判例 | https://www.oalj.dol.gov/PUBLIC/DECISIONS/Main.htm | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/EEOC | US Equal Employment Opportunity Commission Appellate Decisions | 判例 | https://www.eeoc.gov/federal-sector/appellate-decisions | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/FederalCourts | US Federal Courts (SCOTUS + Circuits) | 判例 | https://www.courtlistener.com | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/FederalDistrictCourts | US Federal District Courts | 判例 | https://www.courtlistener.com | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/FederalReserve | US Federal Reserve Board Enforcement Actions | 判例/学说 | https://www.federalreserve.gov/supervisionreg/enforcementactions.htm | 类案检索、裁判观点抽取、法院/法官趋势分析；法律研究综述、释义/指南检索、RAG 背景材料；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| US/FederalSpecialtyCourts | US Federal Specialty & Bankruptcy Courts | 判例 | https://www.courtlistener.com | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/FTC | US Federal Trade Commission Decisions and Orders | 判例/学说 | https://www.ftc.gov/legal-library/browse/cases-proceedings | 类案检索、裁判观点抽取、法院/法官趋势分析；法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| US/OCC | US Office of Comptroller of Currency Enforcement | 判例/学说 | https://www.occ.treas.gov/topics/laws-and-regulations/index-enforcement-actions.html | 类案检索、裁判观点抽取、法院/法官趋势分析；法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| US/TaxCourt | US Tax Court Published Opinions | 判例 | https://www.ustaxcourt.gov | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/TTAB | US Trademark Trial and Appeal Board (TTAB) Decisions | 判例 | https://ttabvue.uspto.gov/ttabvue/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/VA-Courts | Virginia State Courts | 判例 | https://vacourts.gov/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/WA-Courts | Washington State Courts | 判例 | https://courts.wa.gov/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| US/CA-FTB | California Franchise Tax Board Legal Rulings | 学说 | https://www.ftb.ca.gov/tax-pros/law/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| US/EveryCRSReport | Congressional Research Service Reports | 学说 | https://www.everycrsreport.com | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| US/OLCOpinions | DOJ Office of Legal Counsel Opinions | 学说 | https://www.justice.gov/olc/opinions | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| US/GAOReports | GAO Reports and Comptroller General Decisions | 学说 | https://www.govinfo.gov/app/collection/gaoreports | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐ |
| US/IRS-IRB | IRS Internal Revenue Bulletins (Tax Doctrine) | 学说 | https://www.irs.gov/irb/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| US/IRS_IRB | Internal Revenue Bulletins (Revenue Rulings, Procedures) | 学说 | https://www.irs.gov/irb | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| US/NY-DTF | New York Department of Taxation and Finance Advisory Opinions | 学说 | https://www.tax.ny.gov/pubs_and_bulls/advisory_opinions/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| US/FCC | US Federal Communications Commission Orders and Rulings | 学说 | https://www.fcc.gov/edocs | 法律研究综述、释义/指南检索、RAG 背景材料；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| US/FERC | US Federal Energy Regulatory Commission Orders | 学说 | https://www.ferc.gov/media/documents/orders | 法律研究综述、释义/指南检索、RAG 背景材料；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| US/IRS-PrivateLetterRulings | US IRS Private Letter Rulings and Revenue Rulings | 学说 | https://www.irs.gov/privacy-disclosure/irs-written-determinations | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-VI"></a>
## 美属维尔京群岛（VI）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| VI/SupremeCourt | USVI Supreme Court Opinions | 判例 | https://supreme.vicourts.org/court_opinions/published_opinions | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-SR"></a>
## 苏里南（SR）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| SR/WettenSR | Suriname Wetten.sr Legislation | 法规 | https://wetten.sr/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| SR/SupremeCourt | Suriname Supreme Court (Hof van Justitie) | 判例 | https://rechtspraak.sr/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-VG"></a>
## 英属维尔京群岛（VG）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| VG/CommercialCourt | BVI Commercial Court Judgments | 判例 | https://www.eccourts.org/category/judgments/bvi/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| VG/ITA-TaxGuidance | BVI International Tax Authority Guidance | 学说 | https://bviita.vg | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-BQ"></a>
## 荷属加勒比区（BQ）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| BQ/WettenBES | Caribbean Netherlands BES Legislation | 法规 | https://wetten.overheid.nl/BWBR0028142/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-SX"></a>
## 荷属圣马丁（SX）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| SX/Legislation | Sint Maarten Government Legislation | 法规 | https://www.sintmaartengov.org/Government/Pages/Official-Publications.aspx | 法规检索、合规义务映射、法条版本/更新监测；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| SX/GemHof | Joint Court of Justice (Gemeenschappelijk Hof) - Sint Maarten | 判例 | https://uitspraken.rechtspraak.nl/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-SV"></a>
## 萨尔瓦多（SV）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| SV/CorteSuprema | El Salvador Corte Suprema de Justicia - Centro de Jurisprudencia | 判例 | https://www.csj.gob.sv/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-AR"></a>
## 阿根廷（AR）— 9 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| AR/NormasGBA | Buenos Aires Province Normative System (SIND) | 法规 | https://normas.gba.gob.ar/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| AR/InfoLEG | InfoLEG - Sistema de Información Legislativa | 法规 | https://datos.jus.gob.ar/dataset/base-de-datos-legislativos-infoleg | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| AR/CNAT | Argentina Cámara Nacional de Apelaciones del Trabajo | 判例 | https://www.pjn.gov.ar/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| AR/CNACAF | Argentina Cámara Nacional de Apelaciones en lo Contencioso Administrativo Federal | 判例 | https://www.pjn.gov.ar/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| AR/CNDC | Argentina National Competition Commission (CNDC) | 判例 | https://cndc.produccion.gob.ar/buscador | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| AR/SCBA | Argentina Suprema Corte Buenos Aires - JUBA | 判例 | https://juba.scba.gov.ar/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| AR/CSJNDatosAbiertos | Argentina Supreme Court Open Data | 判例 | https://sjconsulta.csjn.gov.ar/sjconsulta/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| AR/Cordoba-TSJ | Córdoba Tribunal Superior de Justicia | 判例 | https://www.saij.gob.ar | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| AR/SAIJ | SAIJ - Sistema Argentino de Información Jurídica | 判例 | https://www.saij.gob.ar | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-AW"></a>
## 阿鲁巴（AW）— 3 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| AW/Courts | Aruba Court Decisions (Gemeenschappelijk Hof) | 判例 | https://data.rechtspraak.nl/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| AW/DIMP-TaxGuidance | Aruba Tax Authority Guidance (Departamento di Impuesto) | 学说 | https://www.impuesto.aw | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| AW/CBA-Regulations | Central Bank of Aruba Regulations | 学说 | https://www.cbaruba.org/cba/do/en/regulations.html | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

# 地区：亚洲

<a name="c-TL"></a>
## 东帝汶（TL）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| TL/JornalRepublica | Timor-Leste Jornal da Republica | 法规 | https://www.mj.gov.tl/jornal/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-CN"></a>
## 中国（CN）— 3 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| CN/NPC | China National Laws Database (国家法律法规数据库) | 法规 | https://flk.npc.gov.cn/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CN/STA-Announcements | China State Taxation Administration Announcements and Circulars (fgk.chinatax.gov.cn) | 法规 | https://fgk.chinatax.gov.cn/eng/home.html | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| CN/SupremeCourt | China Supreme People's Court Guiding Cases & Judicial Interpretations | 判例/法规 | https://www.court.gov.cn/ | 类案检索、裁判观点抽取、法院/法官趋势分析；法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-MO"></a>
## 中国澳门特别行政区（MO）— 3 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| MO/PortalJuridico | Macau Legal Portal (Portal Jurídico / 法律資料庫) | 法规 | https://www.bo.dsaj.gov.mo/pt/portaljur/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| MO/BoletimOficial | Macau Official Gazette (Boletim Oficial) | 法规 | https://bo.io.gov.mo/ | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| MO/Courts | Macau Court Decisions (法院裁判) | 判例 | https://www.court.gov.mo/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-HK"></a>
## 中国香港特别行政区（HK）— 3 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| HK/eLegislation | Hong Kong e-Legislation | 法规 | https://www.elegislation.gov.hk/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| HK/IRD-AdvanceRulings | Hong Kong IRD Advance Rulings | 学说 | https://www.ird.gov.hk/eng/ppr/arc.htm | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| HK/IRD-TaxDoctrine | Hong Kong IRD Tax Guidance (DIPNs, SOIPNs & Advance Rulings) | 学说 | https://www.ird.gov.hk/eng/ppr/dip.htm | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-UZ"></a>
## 乌兹别克斯坦（UZ）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| UZ/LexUz | Lex.uz Uzbekistan National Legislation | 法规 | https://lex.uz/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| UZ/LexUzCaseLaw | Uzbekistan Criminal Court Decisions (publication.sud.uz) | 判例 | https://publication.sud.uz/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-QA"></a>
## 卡塔尔（QA）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| QA/AlMeezan | Qatar Al Meezan Legislation | 法规 | https://www.almeezan.qa/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| QA/AlMeezanCaseLaw | Qatar Al Meezan Case Law Database | 判例 | https://www.almeezan.qa/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-IN"></a>
## 印度（IN）— 7 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| IN/eGazette | Gazette of India (egazette.gov.in) | 法规 | https://egazette.gov.in/ | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| IN/IndiaCode | India Code - Digital Repository of Acts | 法规 | https://www.indiacode.nic.in/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| IN/SEBI | India Securities and Exchange Board (SEBI) Orders & Circulars | 判例/学说 | https://www.sebi.gov.in/ | 类案检索、裁判观点抽取、法院/法官趋势分析；法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| IN/HighCourtAWS | Indian High Court Judgments (AWS Open Data) | 判例 | https://registry.opendata.aws/indian-high-court-judgments/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| IN/SCJudgments | Indian Supreme Court Judgments (AWS Open Data) | 判例 | https://registry.opendata.aws/indian-supreme-court-judgments/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| IN/RBI | India Reserve Bank (RBI) Circulars and Master Directions | 学说 | https://www.rbi.org.in/Scripts/BS_CircularIndexDisplay.aspx | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| IN/TRAI | India Telecom Regulatory Authority (TRAI) Orders | 学说 | https://www.trai.gov.in/release-publication/orders-trai | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-ID"></a>
## 印度尼西亚（ID）— 8 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| ID/PeraturanGO | Database Peraturan Indonesia (DITJEN PP) | 法规 | https://peraturan.go.id/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| ID/JDIHN | Indonesia JDIHN National Legal Network | 法规 | https://jdihn.go.id/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| ID/MahkamahKonstitusi | Indonesia Constitutional Court | 判例 | https://en.mkri.id/court/decision | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| ID/DJP-TaxCirculars | Indonesia Directorate General of Taxes Regulations and Circulars (pajak.go.id) | 学说 | https://www.pajak.go.id/en/peraturan | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| ID/OJK | Otoritas Jasa Keuangan (OJK) — 金融服务监管局  | 监管 | https://www.ojk.go.id/id/regulasi/ | 金融法规检索（银行/保险/证券/P2P/金融科技/消费金融），POJK全文 | ⭐⭐⭐⭐⭐ |
| ID/PPATK | Pusat Pelaporan dan Analisis Transaksi Keuangan (PPATK) — 金融交易报告与分析中心 | 监管 | https://www.ppatk.go.id/ | AML/CFT合规检索 | ⭐⭐⭐⭐⭐ |
| ID/BSSN | Badan Siber dan Sandi Negara (BSSN) — 国家网络与密码局 | 监管 | https://bssn.go.id/ | 网络安全法规检索，事件响应指南 | ⭐⭐⭐⭐⭐ |
| ID/OSS | Online Single Submission (OSS) — 一站式营商许可 | 监管 | https://oss.go.id/ | 外商投资、营业许可登记，负面清单查询 | ⭐⭐⭐⭐⭐ |

<a name="c-SY"></a>
## 叙利亚（SY）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| SY/Legislation | Syrian Presidential Decrees (SANA) | 法规 | https://sana.sy/presidency/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-TW"></a>
## 台湾（TW）— 4 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| TW/MOJ | National Laws Database (全國法規資料庫) | 法规 | https://law.moj.gov.tw | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| TW/LawMOJ | Taiwan Laws & Regulations Database (MOJ) | 法规 | https://law.moj.gov.tw/Eng/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| TW/ConstitutionalCourt | Constitutional Court of Taiwan (R.O.C.) | 判例 | https://cons.judicial.gov.tw/en/ | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| TW/JudicialYuanCaseLaw | Taiwan Judicial Yuan Judgment Search | 判例 | https://judgment.judicial.gov.tw/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-KG"></a>
## 吉尔吉斯斯坦（KG）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| KG/SupremeCourt | Kyrgyzstan Supreme Court Decisions (portal.sot.kg) | 判例 | https://portal.sot.kg | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-KZ"></a>
## 哈萨克斯坦（KZ）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| KZ/Adilet | Adilet Legal Information System (Kazakhstan) | 法规 | https://adilet.zan.kz/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-BD"></a>
## 孟加拉国（BD）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| BD/SupremeCourt-Judgments | Bangladesh Supreme Court Judgments | 判例 | https://www.supremecourt.gov.bd/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BD/SupremeCourt | Bangladesh Supreme Court Judgments | 判例 | https://www.supremecourt.gov.bd/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-PK"></a>
## 巴基斯坦（PK）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| PK/SupremeCourt-HuggingFace | Pakistan Supreme Court Judgments (HuggingFace) | 判例 | https://huggingface.co/datasets/Ibtehaj10/supreme-court-of-pak-judgments | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-BH"></a>
## 巴林（BH）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| BH/NBR-TaxGuidance | Bahrain National Bureau for Revenue VAT Guidance | 学说 | https://www.nbr.gov.bh/tax_guide | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-BN"></a>
## 文莱（BN）— 4 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| BN/AGCLaws | Brunei Attorney General's Chambers Laws | 法规 | https://www.agc.gov.bn/AGC%20Images/LAWS/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| BN/AGC-Legislation | Brunei Attorney Generals Chambers Legislation | 法规 | https://www.agc.gov.bn/AGC%20Site%20Pages/Laws%20of%20Brunei.aspx | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| BN/Courts | Brunei Court Decisions | 判例 | https://www.judiciary.gov.bn/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| BN/MOF-TaxGuidance | Brunei Ministry of Finance Tax Guidance | 学说 | https://www.mofe.gov.bn | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-LK"></a>
## 斯里兰卡（LK）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| LK/LawNet | LawNet Sri Lanka (Ministry of Justice) | 法规/判例 | https://www.lawnet.gov.lk/ | 类案检索、裁判观点抽取、法院/法官趋势分析；法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-SG"></a>
## 新加坡（SG）— 5 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| SG/SSOStatutes | Singapore Statutes Online (SSO) | 法规 | https://sso.agc.gov.sg/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| SG/SLW | Singapore Law Watch Judgments | 判例 | https://www.singaporelawwatch.sg/Judgments | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| SG/eLitigation | Singapore eLitigation Court Judgments | 判例 | https://www.elitigation.sg/gd/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| SG/IRAS-AdvanceRulings | Singapore IRAS Advance Rulings (Summaries) | 学说 | https://www.iras.gov.sg/taxes/corporate-tax/specific-topics/advance-ruling-system | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| SG/IRAS-TaxDoctrine | Singapore IRAS e-Tax Guides | 学说 | https://www.iras.gov.sg/quick-links/e-tax-guides | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-JP"></a>
## 日本（JP）— 9 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| JP/eLawsAPI | Japan e-Gov Laws API v2 | 法规 | https://laws.e-gov.go.jp/api/2/swagger-ui/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| JP/eLaws | Japan e-Laws (e-Gov法令検索) | 法规 | https://laws.e-gov.go.jp/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| JP/JLTrans | Japanese Law Translation (MOJ) | 法规 | https://www.japaneselawtranslation.go.jp/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| JP/eGovLawsAPI | e-Gov Laws API (Version 2) | 法规 | https://laws.e-gov.go.jp/api/2/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| JP/FTC | Japan Fair Trade Commission (JFTC) Decisions | 判例/学说 | https://www.jftc.go.jp/en/policy_enforcement/ | 类案检索、裁判观点抽取、法院/法官趋势分析；法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| JP/CourtsGoJp | Japanese Courts Case Law Database | 判例 | https://www.courts.go.jp/app/hanrei_jp/search1 | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| JP/FSA | Japan Financial Services Agency (FSA) Administrative Actions | 学说 | https://www.fsa.go.jp/sesc/english/news/reco.html | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| JP/NTA-QA | Japan NTA Tax Q&A Cases (質疑応答事例) | 学说 | https://www.nta.go.jp/law/shitsugi/01.htm | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| JP/NTA-Circulars | Japanese National Tax Agency Circulars | 学说 | https://www.nta.go.jp/law/tsutatsu/menu.htm | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-KH"></a>
## 柬埔寨（KH）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| KH/OpenDevCambodia | Cambodia Laws via Open Development Cambodia CKAN | 法规 | https://data.opendevelopmentcambodia.net/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| KH/Courts | Extraordinary Chambers in the Courts of Cambodia (ECCC) | 判例 | https://archive.eccc.gov.kh | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-GE"></a>
## 格鲁吉亚（GE）— 6 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| GE/Parliament | Georgia Parliament | 法规 | https://parliament.ge | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| GE/Matsne | Georgian Legislation Database (Matsne) | 法规 | https://matsne.gov.ge | 法规检索、合规义务映射、法条版本/更新监测；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| GE/SupremeCourt-Decisions | Georgia Supreme Court Decisions | 判例 | https://www.supremecourt.ge/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| GE/ConstitutionalCourt | Georgian Constitutional Court | 判例 | https://www.constcourt.ge | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| GE/SupremeCourt | Georgian Supreme Court | 判例 | https://www.supremecourt.ge | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| GE/RS-TaxAppeals | Georgia Revenue Service Tax Dispute Decisions | 学说 | https://infohub.rs.ge | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-TH"></a>
## 泰国（TH）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| TH/OpenLawData | Open Law Data Thailand (Royal Gazette) | 法规 | https://www.openlawdatathailand.org/ | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| TH/HuggingFaceRG | Thailand Royal Gazette OCR Dataset (HuggingFace) | 法规 | https://huggingface.co/datasets/obbzung/soc-ratchakitcha | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |

<a name="c-KW"></a>
## 科威特（KW）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| KW/MOF-TaxGuidance | Kuwait Ministry of Finance Tax Circulars | 学说 | https://www.mof.gov.kw | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-JO"></a>
## 约旦（JO）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| JO/LOBLegislation | Jordan Legislation & Opinion Bureau | 法规 | https://www.lob.gov.jo/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-MM"></a>
## 缅甸（MM）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| MM/OpenDevMyanmar | Myanmar Laws via Open Development Mekong CKAN | 法规 | https://data.opendevelopmentmekong.net/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-PH"></a>
## 菲律宾（PH）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| PH/LawPhil | LawPhil Project (Arellano Law Foundation) | 判例/法规 | https://lawphil.net/ | 类案检索、裁判观点抽取、法院/法官趋势分析；法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| PH/SCELibrary | Philippines Supreme Court E-Library (Philippine Reports) | 判例 | https://elibrary.judiciary.gov.ph/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-MN"></a>
## 蒙古（MN）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| MN/LegalInfo | Mongolia Unified Legal Information System | 法规/判例 | https://legalinfo.mn/ | 类案检索、裁判观点抽取、法院/法官趋势分析；法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-VN"></a>
## 越南（VN）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| VN/ThuVienPhapLuat | Thu Vien Phap Luat (Legal Library) | 法规 | https://thuvienphapluat.vn/en/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| VN/PhapLuatGov | Vietnam National Legal Document Database (VBPL) | 法规 | https://vbpl.vn/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-AZ"></a>
## 阿塞拜疆（AZ）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| AZ/Qanun | Azerbaijan Legislation (e-Qanun) | 法规 | https://e-qanun.az | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| AZ/ConstitutionalCourt | Azerbaijan Constitutional Court | 判例 | https://www.constcourt.gov.az | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |

<a name="c-AE"></a>
## 阿拉伯联合酋长国（AE）— 5 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| AE/ADGM-Legislation | ADGM Legal Framework | 法规 | https://www.adgm.com/legal-framework | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| AE/DIFC-Legislation | DIFC Legal Database | 法规 | https://www.difc.com/business/laws-and-regulations/legal-database | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| AE/ADGM-Courts | ADGM Courts Judgments | 判例 | https://www.adgm.com/adgm-courts/judgments | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| AE/DIFC | DIFC Courts Judgments and Orders | 判例 | https://www.difccourts.ae/rules-decisions/judgments-orders | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| AE/FSRA-Enforcement | ADGM FSRA Regulatory Actions | 学说 | https://www.adgm.com/operating-in-adgm/additional-obligations-of-financial-services-entities/enforcement/regulatory-actions | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-OM"></a>
## 阿曼（OM）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| OM/DecreeOm | Oman Decrees Portal (decree.om) | 法规 | https://decree.om/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| OM/Legislation | Oman Legal Database (qanoon.om) | 法规 | https://qanoon.om/ | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |

<a name="c-KR"></a>
## 韩国（KR）— 5 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| KR/KLRI | Korea Legislation Research Institute Open API | 法规 | https://open.law.go.kr/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| KR/LawGoKr | Korean Law Information Center (KLIC) Open API | 法规 | https://open.law.go.kr/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| KR/CourtCLIS | Comprehensive Legal Information System (CLIS) | 判例 | https://www.law.go.kr/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| KR/KorLeg | KorLeg South Korean Legal Judgments Dataset (Zenodo) | 判例 | https://zenodo.org/records/14542443 | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| KR/FTC | Korea Fair Trade Commission (KFTC) Decisions | 判例/学说 | https://www.ftc.go.kr/ | 类案检索、裁判观点抽取、法院/法官趋势分析；法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-MV"></a>
## 马尔代夫（MV）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| MV/Gazette | Maldives Government Gazette | 法规 | https://www.gazette.gov.mv/ | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |

<a name="c-MY"></a>
## 马来西亚（MY）— 4 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| MY/LFSA-Legislation | Labuan FSA Legislation & Guidelines | 法规/学说 | https://www.labuanfsa.gov.my/regulations/legislation/act | 法规检索、合规义务映射、法条版本/更新监测；法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |
| MY/FederalLegislation | Laws of Malaysia Online (Attorney General's Chambers) | 法规 | https://lom.agc.gov.my/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| MY/AGCLaws | Malaysia Laws of Malaysia (AGC Official) | 法规 | https://lom.agc.gov.my/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| MY/LHDN-TaxRulings | Malaysia LHDN Public Rulings and Tax Guidelines | 学说 | https://www.hasil.gov.my/en/legislation/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

# 地区：大洋洲

<a name="c-GU"></a>
## 关岛（GU）— 4 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| GU/CompilerOfLaws | Guam Code Annotated & Administrative Rules | 法规 | https://guamcourts.gov/CompilerofLaws/index.html | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| GU/Legislature | Guam Legislature Public Laws | 法规 | https://guamlegislature.gov/public-laws/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| GU/SuperiorCourt | Guam Superior Court Decisions | 判例 | https://guamcourts.gov/Superior-Court-Decision-and-Orders/Superior-Court-Decision-and-Orders.asp | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| GU/SupremeCourt | Supreme Court of Guam Opinions | 判例 | https://guamcourts.gov/Supreme-Court-Opinions/Supreme-Court-Opinions.asp | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-MP"></a>
## 北马里亚纳群岛（MP）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| MP/CNMILRC | CNMI Law Revision Commission | 法规/判例 | https://www.cnmilaw.org/ | 类案检索、裁判观点抽取、法院/法官趋势分析；法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-CK"></a>
## 库克群岛（CK）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| CK/FSC | Cook Islands Financial Supervisory Commission | 学说 | https://www.fsc.gov.ck/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-SB"></a>
## 所罗门群岛（SB）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| SB/AGLegislation | Solomon Islands Attorney General Legislation Portal | 法规 | https://attorneygenerals.gov.sb/legislation/legislation-portal/ | 法规检索、合规义务映射、法条版本/更新监测；宪法条文检索 | ⭐⭐⭐⭐⭐ |

<a name="c-FJ"></a>
## 斐济（FJ）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| FJ/Laws | Laws of Fiji (laws.gov.fj) | 法规 | https://www.laws.gov.fj/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| FJ/SupremeCourt | Fiji Courts Online Decisions (judiciary.gov.fj) | 判例 | https://judiciary.gov.fj | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-NZ"></a>
## 新西兰（NZ）— 3 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| NZ/Legislation | New Zealand Legislation | 法规 | https://www.legislation.govt.nz | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| NZ/CourtsOfNZ | Courts of New Zealand Official Judgments | 判例 | https://www.courtsofnz.govt.nz/judgments | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| NZ/IRD-TaxRulings | New Zealand Inland Revenue Tax Rulings | 学说 | https://www.taxtechnical.ird.govt.nz | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-TO"></a>
## 汤加（TO）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| TO/AGO | Tonga Attorney General Legislation & Judgments | 判例/法规 | https://ago.gov.to/ | 类案检索、裁判观点抽取、法院/法官趋势分析；法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |

<a name="c-PF"></a>
## 法属波利尼西亚（PF）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| PF/JOPF | French Polynesia Official Journal (JOPF) | 法规 | https://lexpol.cloud.pf/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-AU"></a>
## 澳大利亚（AU）— 12 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| AU/ACTLegislation | ACT Legislation Register (legislation.act.gov.au) | 法规 | https://www.legislation.act.gov.au/ | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| AU/FederalRegister | Federal Register of Legislation (Australia) | 法规 | https://www.legislation.gov.au | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| AU/NTLegislation | Northern Territory Legislation (legislation.nt.gov.au) | 法规 | https://legislation.nt.gov.au/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| AU/OpenAusLegalCorpus | Open Australian Legal Corpus (HuggingFace) | 法规/判例 | https://huggingface.co/datasets/umarbutler/open-australian-legal-corpus | 类案检索、裁判观点抽取、法院/法官趋势分析；法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| AU/QLD-Legislation | Queensland Legislation (legislation.qld.gov.au) | 法规 | https://www.legislation.qld.gov.au/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| AU/SA-Legislation | South Australia Legislation (data.sa.gov.au) | 法规 | https://data.sa.gov.au/data/dataset/database-update-package-xml | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| AU/TAS-Legislation | Tasmania Legislation (legislation.tas.gov.au) | 法规 | https://www.legislation.tas.gov.au/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| AU/VIC-Legislation | Victoria Legislation (legislation.vic.gov.au) | 法规 | https://www.legislation.vic.gov.au/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| AU/WA-Legislation | Western Australia Legislation (legislation.wa.gov.au) | 法规 | https://www.legislation.wa.gov.au/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| AU/FedCourt | Federal Court of Australia Judgments | 判例 | https://www.fedcourt.gov.au/digital-law-library/judgments | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| AU/ACCC | Australian Competition and Consumer Commission (ACCC) | 学说 | https://www.accc.gov.au/ | 法律研究综述、释义/指南检索、RAG 背景材料；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| AU/ATO-TaxDoctrine | Australian Tax Office Rulings & Determinations | 学说 | https://www.austlii.edu.au/cgi-bin/viewdb/au/other/rulings/ato/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-NR"></a>
## 瑙鲁（NR）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| NR/RONLAW | RONLAW - Nauru Online Legal Database | 判例/法规 | https://ronlaw.gov.nr/ | 类案检索、裁判观点抽取、法院/法官趋势分析；法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |

<a name="c-WF"></a>
## 瓦利斯和富图纳（WF）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| WF/JOWF | Journal Officiel de Wallis-et-Futuna | 法规 | https://www.wallis-et-futuna.gouv.fr/Publications/Publications-administratives | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |

<a name="c-MH"></a>
## 马绍尔群岛（MH）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| MH/RMICourts | Republic of Marshall Islands Judiciary | 判例/法规 | https://rmicourts.org/ | 类案检索、裁判观点抽取、法院/法官趋势分析；法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

# 地区：非洲

<a name="c-CV"></a>
## 佛得角（CV）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| CV/BoletimOficial | Cabo Verde Official Gazette | 法规 | https://boe.incv.cv/ | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |

<a name="c-GM"></a>
## 冈比亚（GM）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| GM/LawHubGambia | Law Hub Gambia | 判例/法规 | https://www.lawhubgambia.com/ | 类案检索、裁判观点抽取、法院/法官趋势分析；法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-GN"></a>
## 几内亚（GN）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| GN/JournalOfficiel | Guinea Journal Officiel | 法规 | https://journal-officiel.sgg.gov.gn/ | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |

<a name="c-CD"></a>
## 刚果（金）（CD）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| CD/Leganet | DRC (Congo) Legislation Portal | 法规 | https://www.leganet.cd/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-LY"></a>
## 利比亚（LY）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| LY/DCAF | Libya DCAF Security Sector Legal Database | 法规 | https://security-legislation.ly/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-ZA"></a>
## 南非（ZA）— 3 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| ZA/OpenBylaws | South Africa Open By-laws (Laws.Africa) | 法规 | https://openbylaws.org.za | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| ZA/ConstitutionalCourt | South Africa Constitutional Court Judgments | 判例 | https://collections.concourt.org.za/ | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| ZA/SARS-Interpretations | South Africa Revenue Service Tax Interpretations | 学说 | https://www.sars.gov.za/legal-counsel/interpretation-rulings/ | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-RW"></a>
## 卢旺达（RW）— 3 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| RW/Amategeko | Rwanda Official Laws Portal (amategeko.gov.rw) | 法规 | https://www.amategeko.gov.rw/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| RW/RwandaLII | RwandaLII Legislation | 法规 | https://rwandalii.org/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| RW/Courts | Rwanda Courts Decisions | 判例 | https://www.amategeko.gov.rw/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-DJ"></a>
## 吉布提（DJ）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| DJ/JournalOfficiel | Djibouti Journal Officiel | 法规 | https://www.journalofficiel.dj/ | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |

<a name="c-SH"></a>
## 圣赫勒拿（SH）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| SH/Legislation | Saint Helena, Ascension & Tristan da Cunha Legislation | 法规 | https://www.sainthelena.gov.sh/government/legislation/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-EG"></a>
## 埃及（EG）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| EG/LegalCorpus | Egyptian Legal Corpus (Hugging Face) | 法规 | https://huggingface.co/datasets/dataflare/egypt-legal-corpus | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-ET"></a>
## 埃塞俄比亚（ET）— 3 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| ET/FederalNegaritGazetta | Ethiopia Federal Negarit Gazetta (Official Gazette) | 法规 | https://www.hopr.gov.et/ | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| ET/FSC | Ethiopian Federal Supreme Court - Digital Law Library | 法规/判例 | https://www.fsc.gov.et/Digital-Law-Library/Federal-Laws | 类案检索、裁判观点抽取、法院/法官趋势分析；法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| ET/CassationDecisions | Ethiopia Federal Supreme Court Cassation Decisions | 判例 | https://www.lawethiopia.com/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-SN"></a>
## 塞内加尔（SN）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| SN/CourSupreme | Senegal Supreme Court (Cour suprême) | 判例 | https://juricaf.org | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-SC"></a>
## 塞舌尔（SC）— 3 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| SC/SeyLII | Seychelles Legal Information Institute (SeyLII) | 判例/法规 | https://seylii.org/ | 类案检索、裁判观点抽取、法院/法官趋势分析；法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| SC/OfficialGazette | Seychelles Official Gazette | 法规 | https://www.gazette.sc/ | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |
| SC/SRC-TaxGuidance | Seychelles Revenue Commission Tax Guidance | 学说 | https://src.gov.sc | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-TG"></a>
## 多哥（TG）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| TG/JournalOfficiel | Togo Journal Officiel | 法规 | https://jo.gouv.tg/ | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |

<a name="c-MA"></a>
## 摩洛哥（MA）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| MA/AdalaJustice | Morocco Adala Justice Portal | 法规 | https://adala.justice.gov.ma/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| MA/SGG-BulletinOfficiel | Morocco Official Bulletin (Bulletin Officiel) | 法规 | https://www.sgg.gov.ma/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-SZ"></a>
## 斯威士兰（SZ）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| SZ/EswatiniLII | EswatiniLII Legislation | 法规 | https://eswatinilii.org/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-MR"></a>
## 毛里塔尼亚（MR）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| MR/JournalOfficiel | Mauritania Journal Officiel | 法规 | https://www.msgg.gov.mr/fr/droit-mauritanien/le-journal-officiel.html | 法规检索、合规义务映射、法条版本/更新监测；官方公报/监管公告追踪 | ⭐⭐⭐⭐⭐ |

<a name="c-MU"></a>
## 毛里求斯（MU）— 4 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| MU/CompetitionCommission | Mauritius Competition Commission Decisions | 判例 | https://competitioncommission.mu/commission-decision/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| MU/ICACDecisions | Mauritius FCC Court Decisions | 判例 | https://fcc.mu/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| MU/SupremeCourt | Mauritius Supreme Court Judgments | 判例 | https://supremecourt.govmu.org/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| MU/BankOfMauritius | Bank of Mauritius Guidelines & Circulars | 学说 | https://www.bom.mu/financial-stability/supervision/guideline | 法律研究综述、释义/指南检索、RAG 背景材料 | ⭐⭐⭐⭐⭐ |

<a name="c-CI"></a>
## 科特迪瓦（CI）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| CI/CourSupreme | Côte d'Ivoire Supreme Court Decisions | 判例 | https://juricaf.org | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-TN"></a>
## 突尼斯（TN）— 2 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| TN/JORT-Legislation | Tunisia JORT Legislation (DCAF) | 法规 | https://legislation-securite.tn/ | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| TN/CourDeCassation | Tunisia Court of Cassation Jurisprudence | 判例 | https://juricaf.org/recherche/+/facet_pays:Tunisie | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |

<a name="c-KE"></a>
## 肯尼亚（KE）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| KE/KenyaLaw | Kenya Law (National Council for Law Reporting) | 判例/法规 | https://new.kenyalaw.org/ | 类案检索、裁判观点抽取、法院/法官趋势分析；法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-BJ"></a>
## 贝宁（BJ）— 1 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| BJ/LEGIS | Benin LEGIS Legal Database | 法规 | https://legis.cdij.bj | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |

<a name="c-DZ"></a>
## 阿尔及利亚（DZ）— 4 源

| Source ID | 名称 | 类型 | 链接（核验入口） | 场景用途 | 质量 |
|---|---|---|---|---|---|
| DZ/JORADP | Algerian Official Journal (JORADP) | 法规 | https://www.joradp.dz | 法规检索、合规义务映射、法条版本/更新监测 | ⭐⭐⭐⭐⭐ |
| DZ/ConseilConstitutionnel | Algeria Constitutional Court (Cour constitutionnelle) | 判例 | https://cour-constitutionnelle.dz/ | 类案检索、裁判观点抽取、法院/法官趋势分析；宪法条文检索 | ⭐⭐⭐⭐⭐ |
| DZ/CourSupreme | Algeria Supreme Court (Cour suprême) Decisions | 判例 | https://coursupreme.dz/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
| DZ/SupremeCourt-Decisions | Algeria Supreme Court Decisions | 判例 | https://www.coursupreme.dz/ | 类案检索、裁判观点抽取、法院/法官趋势分析 | ⭐⭐⭐⭐⭐ |
