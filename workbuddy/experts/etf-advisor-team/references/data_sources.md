# ETF 专用数据源注册表

> **本文件定位**：ETF 投资顾问专家团共享的数据源清单，服务于 ETF/指数/宏观/行业/资金面数据采集。各成员按需查阅，采集时必须标注来源与时间。
>
> **范围界定**：本文件聚焦 ETF/LOF/指数层面数据，不含个股 F10/财报/股东等个股专属信源。个股层面的深度研究不在本团队职责范围内。

---

## 数据获取优先级

1. **第一优先：内置 westock-data skill**（v1.6.0 起，`npx -y westock-data-skillhub@1.0.5 <命令>`，无需鉴权）——ETF 详情/持仓/净值、K线、技术指标、资金流、宏观指标（cn_*/us_* 系列）、板块估值与行情榜、行业研报、个股财报。命令清单与能力边界见 `references/scripts_guide.md` 零节与 `skills/westock-data/`
2. **westock 不覆盖的场景用保留采集脚本**（逐只指数估值分位、期权 IV、期货持仓/基差、实时五档、REITs、细分行业高频、政策原文等，见 `references/scripts_guide.md`）
3. **再降级 WebSearch / WebFetch** 查询公开页面（中证指数公司、东方财富、天天基金、交易所官网等），**必须标注来源与数据时间**
4. **查不到的数据如实标注"[未获取]"**，严禁凭记忆编造规模、费率、份额等数字
5. 关键数据至少从 2 个信源交叉验证

> 注：若环境装有 NeoData 等其它金融 connector 可作补充（如基金产品/资讯自然语言检索），但非本包内置能力，不强依赖。

---

## 一、ETF 工具属性数据（持仓诊断师核心）

| 数据项 | 信源 | 获取方式 | 备注 |
|--------|------|---------|------|
| ETF 规模/净资产 | 东方财富天天基金 `fund.eastmoney.com` / 交易所官网 | WebFetch / connector | 清盘风险线：<2亿警惕、<5000万高危 |
| 日均成交额 | 东方财富行情 `quote.eastmoney.com` | connector / WebFetch | 流动性下限：日均<1000万警示、<500万高危 |
| 管理费+托管费 | 天天基金 ETF 详情页 / 基金合同 | WebFetch | 同指数下费率差异是确定性收益 |
| 跟踪误差/日跟踪偏离 | 天天基金 / 中证指数公司 | WebFetch | 年化跟踪误差越小越优 |
| 折溢价率（QDII/LOF） | 集思录 `jisilu.cn` / 东方财富 | WebFetch | QDII 溢价>3%警示追高、>5%高风险 |
| ETF 份额变动 | 东方财富 push2 / 交易所 ETF 申赎数据 | connector / WebFetch | 份额增长=资金流入背书 |
| 成立日期/跟踪指数 | 天天基金 / 交易所 | WebFetch | 成立<6个月规模异常警惕 |

## 二、指数估值数据（行情技术分析师核心）

| 数据项 | 信源 | 获取方式 | 备注 |
|--------|------|---------|------|
| 指数 PE/PB 当前值 | 中证指数公司 `csindex.com.cn` | WebFetch / connector | 宽基/行业指数估值权威源 |
| 指数 PE/PB 历史分位（近10年） | 中证指数公司 / 理杏仁 `lixinger.com` | WebFetch | 五档刻度：极度低估<10%/低估10-30%/合理30-70%/高估70-90%/极度高估>90% |
| 股债收益比 ERP | 1/沪深300PE - 10年国债收益率 | 计算 | 股债性价比核心指标 |
| 指数成分股盈利增速 | 中证指数公司 / 东方财富 DataCenter | WebFetch / connector | 指数基本面代理指标 |
| 港股/美股指数估值 | 恒生指数公司 `hsi.com.hk` / Bloomberg 公开页 | WebFetch | QDII 标的估值参照 |

## 三、宏观与政策数据（宏观行业研究员核心）

| 数据项 | 信源 | 获取方式 | 更新频率 |
|--------|------|---------|---------|
| PMI（制造业/非制造业） | 国家统计局 `stats.gov.cn` | WebFetch / connector | 月度 |
| CPI/PPI | 国家统计局 | WebFetch / connector | 月度 |
| 社融/M2 增速 | 人民银行 `pbc.gov.cn` | WebFetch / connector | 月度 |
| LPR/MLF/DR007 | 中国货币网 `chinamoney.com.cn` / 人民银行 | WebFetch / connector | LPR 月度/DR007 日频 |
| 10年国债收益率 | 中国债券信息网 `chinabond.com.cn` | WebFetch / connector | 日频 |
| 美债10Y/美元指数 | 美联储 `federalreserve.gov` / 英为财情 | WebFetch | 日频 |
| 美联储政策表态 | 美联储官网 FOMC 声明 | WebFetch | 事件驱动 |
| 产业政策 | 发改委 `ndrc.gov.cn` / 工信部 `miit.gov.cn` / 财政部 `mof.gov.cn` | WebFetch | 事件驱动 |

## 四、资金面数据（行情技术分析师+宏观行业研究员）

| 数据项 | 信源 | 获取方式 | 备注 |
|--------|------|---------|------|
| ETF 整体申赎流向 | 东方财富 ETF 板块 / 交易所 | connector / WebFetch | 判断被动资金态度 |
| 北向资金流向 | 东方财富 / 沪深交易所 | connector / WebFetch | 2024-08后改为盘后公布总成交+十大活跃股 |
| 两融余额 | 东方财富 / 沪深交易所 | connector / WebFetch | 杠杆资金风向 |
| ETF 期权 PCR/IV | 东方财富期权 T 型报价 | connector / WebFetch | 宽基 ETF 适用，情绪指标 |
| 股指期货基差/升贴水 | 中金所 `cffex.com.cn` | WebFetch | 大盘择时辅助 |

## 五、行业景气度数据（宏观行业研究员核心）

| 数据项 | 信源 | 获取方式 | 适用行业 |
|--------|------|---------|---------|
| 行业研报 | 东方财富研报中心 `data.eastmoney.com/report/` | connector / WebFetch | 全行业 |
| 行业高频数据 | 乘联会 CPCA / Mysteel / 卓创资讯 / 生意社 等 | WebFetch | 汽车/钢铁/化工/有色 |
| 行业协会数据 | 工信部 / 国家能源局 / 药监局 等 | WebFetch | 各行业官方 |
| 产业政策跟踪 | 发改委 / 工信部 / 科技部 | WebFetch | 全行业 |

> **行业专属信源**：详见 `references/industry_sources/README.md`（5 大类 × 23 行业的细粒度专属信源库，每行业一份完整信源文件，各大类另有总览）。

---

## 数据时效要求

| 数据类型 | 时效上限 | 违反处置 |
|---------|---------|---------|
| 实时行情/净值 | ≤1 个交易日（休市日 ≤3 自然日） | 标注并降级为"近期数据" |
| 估值分位 | ≤7 天 | 标注数据日期 |
| 资金流/份额 | ≤3 天 | 标注数据日期 |
| 宏观数据 | 使用当前可得的最新一期 | 必须注明年月 |
| 行业高频数据 | ≤30 天 | 标注数据日期 |

---

## 信源诚信原则

1. **只引可达信源**：引用的 URL 必须是公开可访问的（http/https），严禁引用付费终端内部路径（Wind/Bloomberg/iFinD 等）作为信源名称
2. **事实型数据禁 AI 估算**：已发生的规模/费率/份额/净值等事实数据必须有可查证信源，严禁凭记忆编造
3. **预测/推导要标注**：战术偏离建议、目标仓位、止损位等推导值必须写明推导依据，与事实数据区分
4. **冲突以落盘为准**：若 connector 数据与公开页面冲突，以公开页面为准并标注差异

---

## 与其他参考文档的衔接

| 我需要查 | 应该读 |
|---------|--------|
| ETF 怎么筛选/替换 | `etf_selection_criteria.md` |
| 宏观周期怎么定位/政策怎么打分 | `macro_analysis_framework.md` |
| 市场顶部/底部怎么判断 | `market_regime_signals.md` |
| 行业景气度怎么排序 | `sector_rotation_framework.md` |
| 报告怎么写/怎么交付 | `delivery_spec.md` + `output_template.md` |
| 质量门禁怎么跑 | `quality_gate.md` |
| 有哪些脚本可调用 | `scripts_guide.md` |
| 某个行业的专属信源 | `industry_sources/`（先查 README 索引再进大类目录） |
