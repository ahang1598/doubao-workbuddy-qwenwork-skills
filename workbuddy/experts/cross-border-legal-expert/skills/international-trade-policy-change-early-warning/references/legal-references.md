# 法律参考 — regulatory-change-monitoring

## 版本：v2.0.0

## 1. 美国法规制定与发布机制

### 1.1 Federal Register Act
- **法规**：44 USC Chapter 15（Federal Register Act）[✅已核实]
- **要点**：
  - 44 USC §1505：规定须在Federal Register发布的文件类别
  - Federal Register为美国联邦法规官方发布平台
  - 所有行政法规须在Federal Register发布后方可生效
  - 每日更新，可在线检索（www.federalregister.gov）
  - 与Administrative Procedure Act (5 USC §553)共同构成法规发布程序
- **用途**：法规变更信息来源+权威数据源

### 1.2 Administrative Procedure Act (APA)
- **法规**：5 USC §553 [✅已核实]
- **要点**：
  - 规定行政法规制定程序：提议→评论→发布→生效
  - proposed rule须有公众评论期（通常30-60天）
  - final rule须回应公众评论并说明采纳/拒绝理由
  - interim final rule可立即生效但须接受评论
- **用途**：Phase 1法规状态判定+Phase 2解读程序依据

## 2. 美国出口管制法规（EAR）

### 2.1 EAR整体框架——Part结构表

> 以下结构依据BIS官方目录（2026年6月版，来源：https://media.bis.gov/regulations/ear/table-of-contents）

| Part | 标题 | 内容概要 |
|------|------|---------|
| **Part 730** | General Information（一般信息） | EAR定义、适用范围声明、公共指导 |
| **Part 732** | Steps for Using the EAR（使用EAR的步骤） | 出口商自查流程、合规步骤指引 |
| **Part 734** | Scope of the EAR（EAR的范围） | EAR管辖范围界定、De minimis规则（§734.4）、FDP规则（§734.9） |
| **Part 736** | General Prohibitions（一般禁止事项） | 十项一般禁止（§736.2），禁止未经许可出口/再出口/转移 |
| **Part 738** | Commerce Control List Overview and Country Chart（CCL概述与国家图表） | CCL使用方法、管制原因编码、国家图表 |
| **Part 740** | License Exceptions（许可证例外） | TSR/LVS/GOV/CIV/TMP/RPL/ENC/ACC等许可证例外条件 |
| **Part 742** | Control Policy – CCL Based Controls（管制政策——基于CCL） | 各管制原因（NS/MT/NP/CB/CC等）的许可证政策 |
| **Part 743** | Special Reporting and Notification（特殊报告与通知） | BIS特别报告要求、_END-USE_监控报告 |
| **Part 744** | Control Policy: End-user and End-use Based（管制政策——基于最终用户/用途） | Entity List（Supp.4）、军事最终用途/用户、WMD相关 |
| **Part 745** | Chemical Weapons Convention Requirements（CWC要求） | 化学武器公约声明与报告 |
| **Part 746** | Embargoes and Other Special Controls（禁运与特殊管制） | 对特定国家（古巴/伊朗/朝鲜/叙利亚/俄等）的禁运 |
| **Part 747** | [Reserved]（保留） | — |
| **Part 748** | Applications and Documentation（申请与文档） | 分类请求/咨询意见/许可证申请程序 |
| **Part 750** | Application Processing, Issuance, and Denial（申请处理） | 许可证审查/签发/拒绝程序 |
| **Part 752** | [Reserved]（保留） | — |
| **Part 754** | Short Supply Controls（短缺供应管制） | 短缺物资出口限制 |
| **Part 756** | Appeals and Judicial Review（申诉与司法审查） | BIS决定申诉程序 |
| **Part 758** | Export Clearance Requirements and Authorities（出口清关） | SED/ECCN申报要求 |
| **Part 760** | Restrictive Trade Practices or Boycotts（限制性贸易做法/抵制） | 反抵制报告要求 |
| **Part 762** | Recordkeeping（记录保存） | 出口记录保存义务 |
| **Part 764** | Enforcement and Protective Measures（执法与防护措施） | BIS执法权力、处罚、VSD |
| **Part 766** | Administrative Enforcement Proceedings（行政执法程序） | 行政处罚程序、警告信/处罚令 |
| **Part 768** | Foreign Availability Determination（外国可用性判定） | 外国可用性判定程序与标准 |
| **Part 770** | Interpretations（解释） | BIS官方解释性文件 |
| **Part 772** | Definitions of Terms（术语定义） | EAR核心术语定义 |
| **Part 774** | The Commerce Control List（商业管制清单） | CCL正文（Supp.1含全部ECCN） |
| **Parts 775-780** | [Reserved]（保留） | — |

> **⚠️常见误解纠正**：§735不存在（EAR无Part 735）；Part 736是"General Prohibitions（一般禁止事项）"，不是"豁免+例外"——许可证例外在Part 740。

### 2.2 EAR域外适用核心条款

#### 2.2.1 De minimis规则（§734.4）
- **法规**：15 CFR §734.4 — De minimis U.S. content [✅已核实]
- **要点**：
  - 规定含美国原产受控物项的外国制造商品在何种条件下因美国成分占比过低而不受EAR管辖
  - **一般标准（10%）**：外国制造产品中美国原产受控内容≤10%→不受EAR管辖
  - **0%容忍度**：特定加密物项、针对古巴/伊朗/朝鲜/叙利亚等E:1/E:2国家组→无De minimis豁免，任何美国受控成分均触发EAR管辖
  - **25%标准**：特定军用物项或较高管制级别物项，上限为25%
  - 计算基于公平市场价值，条款详细规定计入/排除项目
- **用途**：Phase 2域外适用解读+Phase 4管辖权冲突标注

#### 2.2.2 Foreign-Direct Product (FDP)规则（§734.9）
- **法规**：15 CFR §734.9 — Foreign-Direct Product (FDP) Rules [✅已核实]
- **要点**：
  - 外国制造产品如系利用受EAR管制的美国原产技术/软件/设备之"直接产品"，在特定条件下仍受EAR管辖
  - **6项子规则**：
    1. **National Security FDP (NS FDP)**：针对NS管控原因的技术/软件生产的直接产品，适用于D:1/E:1/E:2国家组目的地+实体清单特定实体
    2. **9x515 FDP**：针对9类半导体及电子物项（特定ECCN），为早期最常引用的FDP规则
    3. **Supercomputer FDP**：针对用于设计/开发/生产超级计算机的直接产品，适用于D:1/D:3/D:4国家组
    4. **Advanced Computing FDP (AC FDP)**：2022年新增，针对先进计算IC及含此类IC的外国产品，主要限制向中国(D:5)+实体清单特定实体
    5. **Semiconductor Manufacturing Equipment FDP (SME FDP)**：2022年新增，针对利用特定美国技术开发的SME，限制向中国(D:5)+实体清单实体
    6. **Entity List Footnote 4 FDP**：针对实体清单脚注4标识实体，任何利用受EAR管制美国技术/软件生产的直接产品均受管制
  - BIS可通过个别通知或EAR修订告知特定外国产品受§734.9管辖
- **用途**：Phase 2域外适用解读+Phase 4管辖权冲突标注（中美+多法域冲突核心条款之一）

### 2.3 CCL（Commerce Control List）
- **法规**：15 CFR §774 Supplement No.1 [✅已核实]
- **要点**：
  - ECCN分类体系（0-9大类）
  - 每个ECCN含控制原因+许可证要求+例外条件
  - ECCN修订影响分类+许可证+出口路径
- **用途**：eccn_revision类变更解读

### 2.4 Entity List
- **法规**：15 CFR §744 Supplement No.4 [✅已核实]
- **要点**：
  - 列出须额外许可证的实体
  - 每个实体含许可要求+许可政策+适用ECCN
  - 新增/移除须在Federal Register发布
- **用途**：list_update类变更解读

## 3. OFAC制裁法规

### 3.1 OFAC Regulations整体框架
- **法规**：31 CFR Chapter V [✅已核实]
- **要点**：
  - §500-599：各制裁项目法规
  - SDN名单（Specially Designated Nationals）
  - Sectoral Sanctions（行业制裁）
  - General Licenses（通用许可证）
  - Specific Licenses（特定许可证）
- **用途**：OFAC法规变更解读框架

### 3.2 OFAC制裁名单更新机制
- **来源**：OFAC官网更新通知 [✅已核实]
- **要点**：
  - SDN名单新增/修改/移除
  - 通过Federal Register+OFAC官网同步发布
  - 生效通常即时或次日
- **用途**：list_update类变更解读

## 4. 中国相关法规

### 4.1 中国出口管制法
- **法规**：中华人民共和国出口管制法（2020年）[✅已核实]
- **要点**：
  - 管制物项清单+管制措施
  - 最终用户和最终用途管理
  - 与美国EAR的清单差异
  - 双重合规义务
- **用途**：多法域冲突点标注（中美清单冲突为核心）

### 4.2 两用物项出口管制条例
- **法规**：《中华人民共和国两用物项出口管制条例》（国务院令，2024年12月1日施行）[✅已核实]
- **要点**：
  - 国务院第41次常务会议通过（2024年9月18日），自2024年12月1日起施行
  - 共6章50条，补充出口管制法的两用物项管制实施细则
  - 建立两用物项出口管制清单制度+许可制度
  - 规定最终用户和最终用途管理+管控物项跨境转移
  - 与美国EAR CCL/ECCN体系存在清单交叉与差异，企业须双轨合规
- **用途**：多法域冲突点标注（清单交叉+双轨合规义务）

### 4.3 阻断外国法律与措施不当域外适用办法
- **法规**：商务部令2021年第1号 [✅已核实]
- **要点**：
  - 30天报告义务：中国公民/法人发现外国法律不当域外适用须30日内报告
  - 禁止遵守令：商务部可发布禁令禁止遵守该外国法律
  - 损害赔偿：因外国法律域外适用受损可在中国法院起诉求偿
- **用途**：管辖权冲突点标注

### 4.3a 阻断法首个禁令
- **法规**：商务部公告2026年第21号（2026年5月2日）[✅已核实]
- **要点**：
  - 阻断法施行以来首次正式启用
  - 针对美国以"参与伊朗石油交易"为由对5家中国石化企业的SDN制裁措施
  - 明确要求境内主体：不得承认、不得执行、不得遵守美方相关制裁措施
  - 依据：《国家安全法》《对外关系法》《反外国制裁法》及其实施规定+《阻断办法》
- **用途**：管辖权冲突点标注（阻断法实操里程碑案例）

### 4.4 反外国制裁法
- **法规**：中华人民共和国反外国制裁法 [✅已核实]
- **要点**：
  - 反制清单+反制措施
  - 查封扣押冻结财产
  - 禁止交易合作
  - 间接适用：组织/个人协助执行外国歧视性措施也可能被反制
- **用途**：制裁对象冲突点标注

### 4.4a 反外国制裁法实施规定
- **法规**：国令第803号——《实施〈中华人民共和国反外国制裁法〉的规定》（2025年3月21日国务院第55次常务会议通过，2025年3月23日公布，自公布之日起施行）[✅已核实]
- **要点**：
  - 根据《对外关系法》《反外国制裁法》等制定，细化反制裁法的实操规则
  - 明确反制措施的具体执行程序和适用范围
  - 规定协助执行外国歧视性措施的组织/个人的连带反制机制
  - 与阻断法形成"阻断+反制"双轨法律工具
- **用途**：制裁对象冲突点标注（反制措施实操细化）

### 4.5 不可靠实体清单规定
- **法规**：商务部令2020年第4号 [✅已核实]
- **要点**：
  - 不可靠实体清单纳入标准
  - 限制措施：进出口限制+投资限制+入境限制
  - 与美国Entity List/SDN的对冲关系
- **用途**：制裁对象冲突点标注

## 5. 权威数据源与更新频率（v2.0.0扩展——7大领域）

> **v2.0.0变更**：数据源从12个扩展到7大领域，覆盖涉外律师全业务场景。Phase 0 根据 `regulation_category` 动态选择对应领域的数据源子集检索。
>
> **技能定位声明**：本技能 Phase 0 可执行检索（Mode B/C/D），也可接受用户主动获取的变更信息（Mode A）。以下权威数据源供 Phase 0 检索或用户主动获取使用。

### 5.1 领域一：出口管制/制裁（regulation_category: sanctions_list / export_control_rule）

#### 美方数据源

| 数据源 | URL | 更新频率 | 适用范围 | 检索置信度 |
|--------|-----|---------|---------|-----------|
| Federal Register | https://www.federalregister.gov | 每日 | 全部行政法规发布 | 🟡中（网页非结构化） |
| BIS Rulemaking | https://www.bis.doc.gov/index.php/policy-guidance/rulemaking | 每月+突发 | EAR修订/CCL更新/Entity List | 🟡中 |
| OFAC Sanctions List | https://ofac.treasury.gov/sanctions-programs-and-information | 实时 | SDN/SSI/非SDN清单 | 🟢高（API结构化） |
| OFAC Recent Actions | https://ofac.treasury.gov/recent-actions | 实时 | 制裁名单变更/通用许可证 | 🟢高 |
| eCFR (EAR) | https://www.ecfr.gov/current/title-15/subtitle-B/chapter-VII/subchapter-C | 持续更新 | EAR官方电子版 | 🟢高 |
| BIS Entity List | https://www.bis.doc.gov/index.php/policy-guidance/lists-of-parties-of-concern/entity-list | 随Federal Register更新 | Entity List全文 | 🟢高 |

#### 中方数据源

| 数据源 | URL | 更新频率 | 适用范围 | 检索置信度 |
|--------|-----|---------|---------|-----------|
| 中国政府网-法规 | https://www.gov.cn/zhengce/zhengceku/ | 随发布 | 国务院/部委法规 | 🟡中 |
| 商务部-政策发布 | https://www.mofcom.gov.cn/zwgk/zcfb/ | 随发布 | 出口管制/阻断法/不可靠实体清单 | 🟡中 |
| 商务部-产业安全 | https://www.mofcom.gov.cn/xglj/ | 随发布 | 出口管制清单调整 | 🟡中 |

#### EU/UK/UN数据源

| 数据源 | URL | 更新频率 | 适用范围 | 检索置信度 |
|--------|-----|---------|---------|-----------|
| EU Council Sanctions | https://www.consilium.europa.eu/en/policies/sanctions/ | 随决议 | EU制裁名单/措施 | 🟡中 |
| UK OFSI | https://www.gov.uk/government/collections/financial-sanctions | 实时 | UK金融制裁名单 | 🟢高（API可用） |
| UN SC Sanctions | https://www.un.org/securitycouncil/sanctions/information | 随决议 | UN安理会制裁名单 | 🟡中 |

### 5.2 领域二：跨境投资审查（regulation_category: investment_review）（v2.0.0新增）

| 数据源 | URL | 更新频率 | 适用范围 | 检索置信度 |
|--------|-----|---------|---------|-----------|
| CFIUS公告 | https://home.treasury.gov/policy-issues/international/the-committee-on-foreign-investment-in-the-united-states-cfius | 随公告 | 美国外资投资审查 | 🟡中 |
| EU FDI Screening | https://finance.ec.europa.eu/capital-markets-union-and-financial-markets/company-law-and-corporate-governance/eu-screening-foreign-direct-investments_en | 随发布 | EU外资审查框架 | 🟡中 |
| 中国境外投资敏感行业 | https://www.ndrc.gov.cn/xxgk/zcfb/ | 随发布 | 中国境外投资敏感行业目录 | 🟡中 |
| 国家发改委-境外投资 | https://www.ndrc.gov.cn/xxgk/zcfb/fzggwl/ | 随发布 | 境外投资核准/备案 | 🟡中 |

### 5.3 领域三：数据跨境（regulation_category: data_cross_border）（v2.0.0新增）

| 数据源 | URL | 更新频率 | 适用范围 | 检索置信度 |
|--------|-----|---------|---------|-----------|
| GDPR执法动态 | https://edpb.europa.eu/our-work-tools/our-documents_en | 随发布 | GDPR执法决定/指南 | 🟡中 |
| 中国数据出境评估 | https://www.cac.gov.cn/ | 随发布 | 数据出境安全评估/标准合同 | 🟡中 |
| EU SCC更新 | https://ec.europa.eu/info/law/law-topic/data-protection_en | 随发布 | 标准合同条款更新 | 🟡中 |
| 国家网信办 | https://www.cac.gov.cn/ | 随发布 | 网络安全/数据安全法规 | 🟡中 |

### 5.4 领域四：贸易救济（regulation_category: trade_remedy）（v2.0.0新增）

| 数据源 | URL | 更新频率 | 适用范围 | 检索置信度 |
|--------|-----|---------|---------|-----------|
| WTO贸易政策审议 | https://www.wto.org/english/tratop_e/tpr_e/tpr_e.htm | 随审议 | WTO成员国贸易政策 | 🟡中 |
| 中国贸易救济信息网 | https://www.mofcom.gov.cn/article/zhongyts/ | 随发布 | 反倾销/反补贴公告 | 🟡中 |
| EU Trade Defence | https://policy.trade.ec.europa.eu/enforcement-and-protection/trade-defence_en | 随发布 | EU反倾销/反补贴 | 🟡中 |
| US ITA | https://www.trade.gov/ | 随发布 | 美国反倾销/反补贴 | 🟡中 |

### 5.5 领域五：反腐败（regulation_category: anti_bribery）（v2.0.0新增）

| 数据源 | URL | 更新频率 | 适用范围 | 检索置信度 |
|--------|-----|---------|---------|-----------|
| FCPA执法动态 | https://www.justice.gov/criminal/criminal-fcpa | 随发布 | FCPA执法案件/指南 | 🟡中 |
| UK Bribery Act | https://www.sfo.gov.uk/ | 随发布 | UK严重欺诈办公室执法 | 🟡中 |
| 中国反不正当竞争 | https://www.samr.gov.cn/ | 随发布 | 反不正当竞争/商业贿赂 | 🟡中 |
| OECD Anti-Bribery | https://www.oecd.org/corruption/oecdanti-briberyconvention.htm | 随发布 | OECD反贿赂公约动态 | 🟡中 |

### 5.6 领域六：供应链合规（regulation_category: supply_chain）（v2.0.0新增）

| 数据源 | URL | 更新频率 | 适用范围 | 检索置信度 |
|--------|-----|---------|---------|-----------|
| UFLPA执法 | https://www.dhs.gov/uflpa | 随发布 | 维吾尔强迫劳动预防法执法 | 🟡中 |
| EU供应链法 | https://commission.europa.eu/strategy-and-policy/policies/justice-and-fundamental-rights/company-law-and-corporate-governance/sustainable-corporate-governance_en | 随发布 | EU企业可持续尽职调查 | 🟡中 |
| 冲突矿产 | https://www.sec.gov/spotlight/conflict-minerals.shtml | 随发布 | 冲突矿产报告要求 | 🟡中 |
| 美国海关CBP | https://www.cbp.gov/ | 随发布 | CBP扣留/ seizure公告 | 🟡中 |

### 5.7 领域七：国际仲裁（regulation_category: intl_arbitration）（v2.0.0新增）

| 数据源 | URL | 更新频率 | 适用范围 | 检索置信度 |
|--------|-----|---------|---------|-----------|
| ICC仲裁规则 | https://iccwbo.org/dispute-resolution/ | 随更新 | ICC仲裁规则/实践指南 | 🟢高 |
| SIAC | https://www.siac.org.sg/ | 随更新 | 新加坡国际仲裁中心规则 | 🟢高 |
| HKIAC | https://www.hkiac.org/ | 随更新 | 香港国际仲裁中心规则 | 🟢高 |
| NY Convention | https://www.newyorkconvention.org/ | 随更新 | 纽约公约缔约国动态 | 🟢高 |

### 5.8 更新频率标注体系

| 标注 | 含义 | 适用 |
|------|------|------|
| 🔄实时 | 变更发布后立即更新 | OFAC SDN/UK OFSI |
| 📅每日 | 每工作日更新 | Federal Register |
| 📅每月 | 每月或突发时更新 | BIS Rulemaking |
| 📅随发布 | 法规发布后同步更新 | 中方/EU/UN |
| 📅随更新 | 规则修订时更新 | ICC/SIAC/HKIAC |

### 5.9 检索置信度标注体系（v2.0.0新增）

| 标注 | 含义 | 适用 | 可追溯性要求 |
|------|------|------|-------------|
| 🟢高 | API结构化数据检索 | OFAC List API/eCFR/ICC规则 | 源URL+API响应时间戳+原文快照 |
| 🟡中 | 网页非结构化检索 | Federal Register网页/商务部公告 | 源URL+访问时间戳+原文关键段落 |
| 🔴低 | 基于摘要/二手来源推断 | 新闻报道/法律数据库摘要 | 来源标注+建议补充原始来源 |

> **检索完整性声明（v2.0.0强制）**：本技能 Phase 0 检索为辅助发现手段，不替代专业合规监控服务，可能存在遗漏。漏检风险等级见 input-spec.md 差异化处置矩阵。对于 🔴极高风险（sanctions_list类）法规，强烈建议使用专业合规监控服务交叉验证。

## 6. 法条三标注说明

| 标注 | 含义 | 使用规则 |
|------|------|---------|
| ✅已核实 | 已联网核实法条编号与内容 | 可直接引用 |
| 📋需核实 | 需联网核实或内容不确定 | 引用时须标注 |
| ⚠️存疑 | 法条内容可能已变更或有争议 | 仅作参考，须律师确认 |
