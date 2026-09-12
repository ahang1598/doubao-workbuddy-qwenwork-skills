# 投行交易准备（ib-deal-prep）

> **何时参考**：用户问"尽调清单 / 投委会备忘录 / 数据包 / pitch deck / 路演材料 / NDA / 信息备忘录 / 融资摘要 / teaser / 流程函"。

## 核心目标

**融资 / 并购交易准备的标准化文档与流程**——从尽调到投委会到路演的完整链路。

## 主要文档与流程

### 1. 尽调清单体系化
- **法律尽调**：合规 / 诉讼 / 知识产权
- **财务尽调**：审计 / 应收应付 / 往来关系核实
- **商业尽调**：市场规模 / 客户集中度 / 供应链 / 竞争格局
- **运营尽调**：IT 系统 / 生产能力 / 人员结构
- 每一层都需要 list of documents + follow-up questions 清单 + deadline + responsible person

### 2. 尽调会议准备
- 先发"Long Form"数据清单（50-100 页 Q&A）
- 目标企业提供：完整财务报表、合同库、组织结构、政策合规证明
- 多轮 session meeting（财务 / 法律 / 商业 / 运营分开）
- 控制信息流并记录 session minutes
- 通常整个过程 4-8 周

### 3. 投委会备忘录写作框架
- **Executive Summary（1 页）**：投资金额 / 股权% / IRR / MoIC 目标 / investment thesis
- **Company Overview（2 页）**：历史 / 股东 / 主营 / 财务快照
- **Investment Opportunity（3 页）**：市场规模 / 增长驱动 / competitive advantage
- **Investment Risks（2 页）**：市场 / 竞争 / 运营 / 财务风险与 mitigation
- **Use of Proceeds（1 页）**：融资金额用途拆解
- **Financial Highlights & Valuation（2 页）**：历史 / 预测 / 估值倍数 / exit 假设
- **Terms & Governance（1 页）**：融资条款 / 董事会权利

### 4. 投委会数据包（IM）要素
- Executive summary & key metrics
- Company description
- Market analysis（TAM / SAM / SOM / CAGR / 竞争对标）
- Business model & value proposition
- Financial analysis（3 年历史 + 5-7 年 forecast + DCF）
- Management team & organization
- Risk analysis & mitigation
- Competitive positioning
- Use of funds
- Valuation summary
- 通常 30-50 页、design 精美、数据严谨

### 5. 匿名 Teaser
- 大型交易先发"不暴露名字"的简版（2-4 页）
- 勾勒：business model / market size / growth trajectory / profitability path / management quality
- 吸引潜在投资者签 NDA 后看 full memorandum
- 此阶段 focus on story & numbers appeal，不涉及 operational details

### 6. 路演 Pitch Deck
- 通常 15-25 页
- 结构：market opportunity → company overview → product / service → traction → business model & unit economics → financial projections → competitive advantage → team → ask（融资金额）
- 需要 visual appeal，数据用图表而非表格，每页一个 clear message

### 7. 保密协议（NDA）与备忘录构建
- **NDA**：明确"confidential information"定义、保密期 2-3 年、permitted uses（due diligence purposes only）、回函与销毁条款
- **IM**：包含 forward-looking statements 免责声明 / no representation/warranty / permitted uses

### 8. 融资摘要与流程函
- **融资摘要**：transaction overview → use of proceeds → financial highlights → valuation → key terms & conditions → transaction timeline
- **流程函（Process Letter）**：由融资顾问 / IB 发出，说明融资路演时间表 / investor meeting schedule / term sheet 反馈截止日 / exclusivity 期限

## 建议骨架（不强制）

- 尽调清单（按法律 / 财务 / 商业 / 运营分类，逐项 tracking）
- 会议议程与 participants list
- 投委会备忘录（executive summary / business overview / opportunity / risks / valuation）
- 数据包大纲（30-50 页 IM 完整结构）
- 路演 Pitch Deck（15-25 页）
- NDA & IM template
- 融资时间表与流程规划

## 避坑

- 尽调遗漏常导致后期 disputes（客户合同风险 / 应收坏账 / 环保违规）——systemic checklist 而非 case-by-case
- 数据包中财务预测过度乐观（growth rate / margin expansion）是投资者反感的首要原因——与 historical 匹配、与 industry benchmark 对标、conservative 为上
- 路演 ppt 中**千万不要用 fake 数据**或过度美化——投资者一查就知道，失信成本很高
- IM 中如发现后期与 actual 不符（隐瞒 risk / 夸大 revenue stability）——会导致投资者回购权行使、甚至法律诉讼
- 匿名 teaser 看似 harmless——但若后期被多个 investor 同时 reveal，造成 auction pressure 导致交易价格虚高

## 可执行工具

⚠️ **数据 skill 边界**：写 IM / teaser / 投委会备忘录的**内容素材**来自 westock / neodata（公司财务、行业空间、可比对标），但**写完后的数字一致性检查是文本算法任务，数据 skill 不做**。

`scripts/ib/extract_ib_numbers.py` — 投行材料数字提取与一致性校验。**写完 IM / 数据包 / 投委会备忘录 / teaser 后必跑**：

```bash
python3 scripts/ib/extract_ib_numbers.py <path/to/material.txt>
```

自动提取并按类别归类（财务、估值、协同效应、时间线、规模），输出疑似不一致项（如同份材料 EBITDA $50M / $52M 出现两次），避免投资者发现矛盾。输入是纯文本 / Markdown（不是 PDF——若是 PDF 自行先转文本）。

**Setup**：纯标准库实现，无需 `pip install`，python3 直接跑。
