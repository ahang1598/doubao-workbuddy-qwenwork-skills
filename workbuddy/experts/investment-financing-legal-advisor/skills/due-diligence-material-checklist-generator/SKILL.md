---
name: 尽调材料清单生成
name_en: due-diligence-material-checklist-generator
version: 1.0.0
description: 根据交易场景生成尽调材料索取清单（Excel格式），按M&A/PE/IPO/资产收购/跨境投资5种场景路由，覆盖12大模块，含风险驱动+交叉验证+动态迭代方法论。触发：尽调启动需向目标公司发函索取材料。不触发：尽调报告(→07)、合同审查(→06)、法律意见、陷阱对抗(→adversarial)、创始人责任(→founder-liability)、股权核验(→cap-table-verify)、权利设计(→special-rights-design)、多轮一致性(→multi-round)。
---

# 尽调材料清单生成 (v1.2.1)

## 一、技能定位与核心原则

本技能根据交易场景和目标公司类型，生成结构化的尽调材料索取清单（Excel 主格式 + Markdown 预览 + Cover Letter），覆盖 5 种交易场景路由和 12 大资料模块。

> 清单是尽调的起点——清单的质量决定尽调的全面性。v1.2.0 从"模块覆盖型"升级为"风险驱动+交叉验证型"。

**角色定位**：尽调材料索取清单的配置驱动生成器，不替代持证律师对材料必要性的专业判断。

### 核心原则

| # | 原则 | 说明 |
|---|------|------|
| P1 | 场景驱动差异化 | 清单内容由交易场景路由决定，5种场景的模块组成和深度各不相同 |
| P2 | 风险驱动设计 | 从风险假设出发设计验证材料（v1.2.0升级），非简单模块组合 |
| P3 | 交叉验证内置 | 材料项含交叉验证配对标注，A验证B提升尽调可靠性（v1.2.0新增） |
| P4 | 模块化组合 | 12 大模块可按场景灵活组合，配置 JSON 驱动，新增场景只需新增配置文件 |
| P5 | Excel 优先 | 主输出为 Excel 格式，利用条件格式（必需性色标/接收状态色标）/冻结表头/下拉框/打印设置 |
| P6 | 必需性分级 | 每项材料标注必须/推荐/可选三级必需性，支持场景必需性矩阵 |
| P7 | 阶段分配+部门分派 | 材料按提交批次+目标公司部门双维度分组 |
| P8 | 全流程管理 | 含接收状态跟踪/收件日期/提供形式/dashboard统计（v1.2.0新增） |
| P9 | 动态迭代 | 支持先发基本清单后发补充清单，根据已收材料发现新问题（v1.2.0新增） |
| P10 | 信息不足仍可交付 | SOFT_DEGRADED C+D+G 骨架保证最小可用输出，标注缺失信息及影响范围 |
| P11 | 不越界 | 仅生成索取清单+Cover Letter，不产出尽调报告/法律意见/交易风险评估 |
| P12 | 首次必交互 | Phase 1.5 场景确认门控，禁止跳过直接进入模块选择（v1.2.0新增） |
| P13 | 扩展点预留 | v1.0 预留 MCP 数据采集/自定义模块/多语言等扩展点 |

> **写作红线** → 见 `docs/output-spec.md` §1
> **清单构建方法论** → 见 `references/methodology.md`
> **排版规格** → 见 `docs/output-spec.md` Excel 排版规格专章

## 二、快速开始

### 触发条件

- 投资并购 / PE 投资 / IPO / 资产收购 / 跨境投资尽调启动阶段
- 需向目标公司发函索取材料前

### 最小输入

| 参数 | 必填 | 说明 |
|------|------|------|
| transaction_scenario | 是 | 交易场景：M&A / PE / IPO / ASSET_ACQUISITION / CROSSBORDER |
| target_company_name | 是 | 目标公司全称 |

### 可选增强输入

| 参数 | 说明 |
|------|------|
| target_company_industry | 目标公司行业（影响 M9/M10/M11 模块） |
| target_company_type | 公司类型（有限责任公司/股份有限公司/合伙企业/外商投资企业） |
| transaction_stage | 交易阶段（意向书/尽职调查/正式协议/交割前） |
| specific_concerns | 特定关注点（文本描述，追加到 M10 模块） |
| existing_materials | 已有材料清单（标注已有材料不重复索取） |
| dd_depth | 尽调深度：快速/标准/深入（默认标准） |
| generate_cover_letter | 是否生成尽调材料索取函（默认true, v1.2.0新增） |
| need_dept_grouping | 是否生成部门分派视图（默认true, v1.2.0新增） |

### 快速路径

场景类型明确 + 目标公司信息完备 → 跳过 Phase 1 交互追问（但 Phase 1.5 场景确认不可跳过）。

### 输出

- **Excel 主文件**：`尽调材料清单_{场景标识}_{公司名}_{日期}.xlsx`
  - Sheet1 尽调材料清单（11列：序号/模块/资料名称/类型/必需性/提交阶段/存档部门/接收状态/收件日期/提供形式/备注）
  - Sheet2 场景说明与填写指引
  - Sheet3 提交阶段分配（材料项>30时）
  - Sheet4 部门分派视图（材料项>30时, v1.2.0新增）
- **Markdown 预览**：会话窗口即时预览，按模块分节
- **Cover Letter**：尽调材料索取函（v1.2.0新增）

## 三、工作流概览

| Phase | 名称 | 风险 | 核心动作 | 输出 |
|-------|------|------|---------|------|
| 1 | 场景识别与输入校验 | L1 | 识别场景类型（含5种v1.2.0），校验目标公司信息 | scenario_id + company_profile |
| 1.5 | [重要] 场景确认门控 | L2 | 暂停等用户确认场景类型（v1.2.0新增） | 用户确认 |
| 2 | 场景路由与模块选择 | L2 | 加载场景配置 JSON，选模块+优先级 | module_selection |
| 3 | 清单内容生成 | L2 | 查表→增删→填充三段式精准操作 | checklist_data (JSON) |
| 4 | Excel + Cover Letter | L2 | [SCRIPT CALL] excel_generator.py v1.2.0 | Excel + Markdown + Cover Letter |
| 5 | 质量检查与输出 | L1 | 22项质检（含5项场景增强检查） | 最终交付物 + 质量摘要 |

### 场景路由表

| 场景 | 标识 | 重点模块 | 预计材料项 |
|------|------|---------|-----------|
| 投资并购 | S-MNA | M2股权/M3治理/M6合同/M12保险 | 80-120 |
| PE/VC投资 | S-PE | M2股权(含投资者权利)/M5资产IP/M7人事 | 65-95 |
| IPO | S-IPO | 全12模块（最深入，M3/M4/M9/M11/M12） | 100-150 |
| 资产收购 | S-ASSET | M5资产/M6债权债务 | 50-75 |
| 跨境投资 | S-CROSSBORDER | M2穿透/M4转移定价/M10 FDI-ODI/M11数据出境 | 70-100 |

> **详细工作流** → 见 `docs/workflow-detail.md`
> **场景路由配置** → 见 `references/scenario-routing.md`
> **模块库定义** → 见 `references/checklist-modules.md`

## 四、输入输出概要

### 输入字段

| 字段 | 类型 | 必填 | 校验规则 | 缺失处理 |
|------|------|------|---------|---------|
| transaction_scenario | enum | 是 | ∈ {M&A, PE, IPO, ASSET_ACQUISITION, CROSSBORDER} | 展示5选项追问 |
| target_company_name | string | 是 | 非空 AND 长度≥2 | 追问补充 |
| target_company_industry | string | 否 | — | 使用默认值 |
| target_company_type | enum | 否 | — | 默认"有限责任公司" |
| transaction_stage | enum | 否 | — | 默认"尽职调查" |
| specific_concerns | text | 否 | — | 追加到M10 |
| existing_materials | text | 否 | — | 标注已有 |
| dd_depth | enum | 否 | ∈ {快速,标准,深入} | 默认"标准" |
| generate_cover_letter | boolean | 否 | — | 默认true |
| need_dept_grouping | boolean | 否 | — | 默认true |

### 输出块

| 块 | 类型 | 内容 | 触发条件 |
|------|------|------|---------|
| O1 | Excel主文件 | 12大模块×N项，11列结构 | 始终产出 |
| O2 | Markdown预览 | 按模块分节表格 | 始终产出 |
| O3 | Cover Letter | 尽调材料索取函 | generate_cover_letter=true |
| C1 | 场景特定补充 | 行业匹配追加材料 | 场景+行业匹配 |
| C2 | 提交阶段分配表 | 独立Sheet | 材料项>30 |
| C3 | 部门分派视图 | 独立Sheet | 材料项>30 |

### Excel 列结构（v1.2.0）

| 列 | 列名 | 示例 |
|----|------|------|
| A | 序号 | M1-001 |
| B | 模块 | 公司基本信息与历史沿革 |
| C | 资料名称 | 营业执照副本 |
| D | 资料类型 | 证照 |
| E | 必需性 | 必须 |
| F | 提交阶段 | 第一阶段 |
| G | 存档部门 | 行政部 |
| H | 接收状态 | 未收（下拉框:已收/未收/部分提供/拒绝提供） |
| I | 收件日期 | （待填写） |
| J | 提供形式 | （待填写） |
| K | 备注 | 需提供最新年检版本 |

### 降级机制（SOFT_DEGRADED C+D+G）

信息不足时仍输出最小可用清单：
- **[C]** 待补充事实清单：标注缺失信息+影响范围
- **[D]** 治理声明：申明基于不完整信息生成的局限
- **[G]** 可执行下一步：告知用户可补充的信息和操作

## 五、常见问题·文档索引

### 适用边界与下游路由

本技能仅生成索取清单，不产尽调报告/法律意见。清单回收后的深度分析须路由至专项技能：

- **全面尽调报告** → `company-equity-due-diligence`（07）
- **PE 场景回收的投资者权利文件**（对赌/反稀释/优先清算/回购）→ 条款对抗性分析 `cap-market-adversarial-clause-analysis`、创始人个人责任提取 `cap-market-founder-liability-review`、股权结构核验 `cap-market-cap-table-verify`、特殊权利条款设计 `cap-market-special-rights-design`、多轮融资一致性 `cap-market-multi-round-consistency`
- **股权/治理类材料红旗** → `02-股东确权` / `03-公司治理诊断`

> 建议在清单 Cover Letter 与 M2 模块备注中提示：回收材料将用于上述专项分析，提升客户配合度。

### FAQ

**Q: 支持哪些交易场景？**
A: v1.2.0 支持 5 种：投资并购(M&A)、PE/VC投资、IPO、资产收购、跨境投资（FDI/ODI）。其他场景（如破产重整投资/国企混改）将在 v2.0 支持。

**Q: PE 场景下会对赌协议吗？**
A: v1.2.0 强制 PE 场景包含投资者权利文件（对赌协议/反稀释条款/优先清算权/回购权），这是顶级律所 PE 尽调的核心。详见 M2 模块。

**Q: 科技类公司会查数据合规吗？**
A: v1.2.0 强制软件/互联网/金融/医疗行业启用 M11 数据安全模块（15+项），覆盖PIA评估/数据出境/等保/隐私政策等。

**Q: 跨境投资场景支持哪些材料？**
A: v1.2.0 新增 S-CROSSBORDER 场景，自动包含 FDI备案/ODI核准/安全审查/反垄断审查/数据出境等跨境专项材料。

**Q: Excel 能追踪材料接收状态吗？**
A: v1.2.0 新增"接收状态"下拉框列（已收/未收/部分提供/拒绝提供）+收件日期+提供形式+状态统计仪表盘。清单从"一次性工具"升级为"全流程管理工具"。

**Q: 有 Cover Letter 吗？**
A: v1.2.0 新增尽调材料索取函（律所抬头/收件人/索取依据/回复期限）。

**Q: 如何与 company-equity-due-diligence 配合使用？**
A: 本技能生成索取清单（事前），company-equity-due-diligence 生成尽调报告（事后）。清单数据可通过 output-interface.md 定义的 JSON Schema 流入尽调报告流程。

### 文档索引

| 文件 | 职责 | 位置 |
|------|------|------|
| input-spec.md | 输入规格 | docs/ |
| output-spec.md | 输出规格（含Excel排版+写作红线+Cover Letter模板） | docs/ |
| legal-references.md | 法规引用（含法条三标注+材料项-法条映射） | docs/ |
| workflow-detail.md | 工作流详情（含Phase 3三段式+交互门控） | docs/ |
| scenario-routing.md | 场景路由配置（含5场景+12模块矩阵） | references/ |
| checklist-modules.md | 12大模块定义（含PE权利/数据安全/保险） | references/ |
| references/methodology.md | 清单构建方法论（风险驱动+交叉验证+动态迭代） | references/ |
| references/quality-standards.md | 质量标准（22项质检含5项场景增强） | references/ |
| output-interface.md | 输出数据格式（供下游,含状态回填协议） | references/ |
| meta/dependencies.md | 上下游技能依赖（07+5个P0技能联动） | meta/ |
| scenario-*.json | 场景配置文件（5个） | templates/ |
| excel_generator.py | Excel生成器 v1.2.0 | scripts/ |

<!-- Copyright © 深圳市法大大网络科技有限公司 版权所有 | Author: 法大大法律AI产品线 -->
