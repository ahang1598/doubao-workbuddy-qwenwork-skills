# LBO回报分析

## 总原则

用中文完成研究、计算说明和结论。先保证证据与计算可审计，再给出投资判断。将所有输入分为“公开事实、口径调整、模型假设、模型推导”四类；禁止把假设写成事实。

第一次出现专业术语时给出简短中文解释，并保留常用英文缩写。遵循 references/lbo-chinese-output-style.md。

## 执行顺序

正式LBO先建立并验证 `execution-plan.json`。计划必须在计算前列明 EBITDA增长、折旧摊销、资本开支、营运资本变动、所得税率、交易费用、分层债务、现金来源、退出年份和退出倍数依据；同时预设经营改善对比与回报归因，不得在看到IRR后补写有利假设。

### 1. 识别目标与适用性

确认公司全称、代码、上市地、报告币种、估值基准日和用户目标。默认分析第3、4、5、6、7年退出。

先读取 references/lbo-sector-gates.md。银行、保险、券商、地产开发、早期生物科技、持股平台、长期负EBITDA或现金流无法合理预测的企业，不得直接套用标准LBO；说明限制并改用适合的分析框架或停止精确回报测算。

### 2. 查询并核验公开资料

先按强制读取完整性协议完整读取 `references/source-tool-priority.md`。对公司身份、价格、股份数、财务报表、债务、现金、资本开支和前瞻数据分别识别用户指定来源并优先实际调用。用户未指定的项目才检查并优先调用 `seed_finance_search`。指定来源或默认工具不可用、无覆盖或数据冲突时，记录实际尝试与降级原因，再使用监管申报、交易所公告和公司投资者关系资料等权威来源；不得静默换源。

`seed_finance_search` 是检索工具而非最终审计凭证。关键估值和现金流数据必须尽可能回查原始监管文件。读取 references/lbo-data-source-policy.md，并按上市地读取对应市场文件：

- A股：references/lbo-market-a-share.md
- 港股：references/lbo-market-hong-kong.md
- 美股：references/lbo-market-us.md

所有关键数据记录来源、发布日期、财务期间、币种、单位和页码或表名。无法取得时明确列入数据缺口。

在输入JSON中使用 `provenance.sources` 保存唯一来源ID，并用 `provenance.field_sources` 至少映射进入估值、经营情景、债务条款和退出假设。来源台账非空但字段映射为空时不得视为完成。

### 3. 统一会计与估值口径

读取 references/lbo-accounting-normalization.md。至少统一：

- 完全稀释股份数与股权价值；
- 现金、债务、租赁、优先股、少数股东和其他类债务项目；
- 报告EBITDA、LTM EBITDA与调整后EBITDA；
- 资本开支、营运资本、现金税和自由现金流；
- PRC GAAP、IFRS及US GAAP之间影响LBO的差异。

每项EBITDA调整逐项列示，不得加入无证据协同效应。租赁负债与租赁费用的处理必须前后一致。

### 4. 建立假设账本

用表格列示字段、数值、单位、期间、分类、来源和解释。最低包括：

- 收购股权价值、收购溢价和进入企业价值；
- 进入EBITDA及进入倍数；
- 各层债务金额、利率、PIK、摊还、期限与现金清偿规则；
- 最低现金、交易费、融资费和管理层滚存；
- 收入、利润率、资本开支、营运资本、税率；
- 退出年份、退出EBITDA、退出倍数和退出费用。

显式列出隐含假设，包括折旧摊销、折旧税盾、资本开支与折旧关系、现金税、营运资本、最低现金、利息计提时点、债务到期未偿处理和再融资假设。任何在计算中默认为零的项目也必须列示，不能让读者自行推断。

设置Downside、Base、Upside三种经营情景。Base默认不得依赖退出倍数扩张、无依据协同、无限再融资或激进营运资本释放。

当Base回报低于1.0x、IRR为负或接近股权归零临界点时，必须增加一个可实现的经营改善情景，并量化投后管理能否抵销倍数压缩。可在输入JSON提供 `management_case` 的完整年度经营路径和指定退出年份/倍数，由引擎输出与Base的企业价值、股权价值、MOIC和XIRR对比。

为每种经营情景保存独立JSON并完整重跑债务计划；不要只对最终EBITDA做比例调整。进入价格敏感性也应重跑Sources & Uses、持股比例与股权现金流。

### 5. 运行确定性计算

读取 references/lbo-calculation-rules.md 和 references/lbo-output-schema.md。将结构化输入保存为JSON，先运行：

    python3 scripts/lbo/validate_case.py case.json

验证通过后运行：

    python3 scripts/lbo/lbo_engine.py case.json --output result.json

不得用语言模型口算替代脚本结果。若交易结构超出脚本能力，扩展并测试脚本，或清楚标注简化及其影响。
只有 `result.json` 的 `model_status_code` 为 `PASS` 才能输出利润、MOIC和XIRR结论；`INCOMPLETE` 仅展示假设、债务底稿、阻断事项和修复动作。

### 6. 复核与压力测试

检查Sources & Uses、债务滚动、现金、利息、PIK、循环额度、最低现金、退出净债务、股权现金流、MOIC和XIRR。至少输出：

- 第3至第7年退出结果；
- 进入价格与退出倍数二维敏感性；
- EBITDA或利润率与退出倍数二维敏感性；
- 杠杆与利率压力；
- 达到目标IRR时可支付的最高收购价；
- 达到目标IRR所需的最低退出EBITDA或退出倍数；
- 回报来源及回报失效条件。

计算异常时先修复输入或模型，不要用文字掩盖不平衡。

### 7. 写入Excel结论与说明页

按 references/lbo-output-schema.md 的顺序把结论、依据和限制写入同一个公式工作簿。结论先回答“几年退出能赚多少”，然后解释：

1. 核心回报结果和推荐关注的退出窗口；
2. 回报来自EBITDA增长、债务偿还、倍数变化还是分红；
3. 哪些结果属于事实、假设和推导；
4. 最敏感的三个变量；
5. 什么证据出现时Base Case失效。

结论必须包含量化回报归因，至少展示EBITDA增长、倍数变化、净债务偿还、债务类调整和退出费用对股权价值变化的金额及占比。只做定性解释不算完成。存在 `management_case_comparison` 时，在风险分析之后展示经营改善前后对比。

使用条件化语言。信息不足时给出区间、置信度和待核验清单，不生成伪精确结论。

按`references/delivery-package-contract.md`保存主要公式工作簿、结构化输入、计算结果、验证结果、运行记录和文件清单。默认只把工作簿作为用户可见交付物；审计附件不得覆盖或手填IRR、MOIC和回报归因。

只有用户明确要求独立Markdown或飞书报告时，才可在工作簿通过审计后运行可选渲染器和报告审计：

```bash
python3 scripts/lbo/render_lbo_report.py result.json --output report.md --exit-year 5 --exit-multiple <Base退出倍数>
python3 scripts/common/audit_report_artifact.py report.md result.json --workflow lbo --output artifact-audit.json
```

正式任务必须生成公式工作簿，并将其作为唯一默认用户交付物。工作簿至少包含封面、交易摘要、交易与融资假设、假设依据、历史数据与口径、Sources & Uses、经营预测、分层债务、现金与利息、退出回报、投资人现金流、MOIC/IRR/XIRR、回报归因、情景与敏感性、目标回报反推、风险与失效条件、模型检查和数据来源。关键历史值和交易、经营、融资及退出假设分别关联来源编号与假设编号。先建立公式语义合约与冻结布局，覆盖Sources & Uses、债务滚动、现金、利息、退出股权价值、MOIC、XIRR、回报归因和敏感性；保存后运行语义审计及`scripts/common/audit_formula_workbook.py --recalculate required`。任一关键依赖、单位、中间节点、直接产物审计或最终哈希复核失败时，不得输出回报结论。

不得由语言模型自行拼装LBO工作簿。完成`lbo_engine.py`确定性计算后，必须从同一标准化case运行固定生成器和专属审计器：

```bash
python3 scripts/lbo/build_lbo_workbook.py case.json lbo-model.xlsx --contract lbo-workbook-contract.json
python3 scripts/lbo/audit_lbo_workbook.py lbo-model.xlsx lbo-workbook-contract.json artifact-audit.json
```

生成器固定物化Sources & Uses、逐年经营现金流、分层债务期初/利息/PIK/强制摊还/现金扫款/期末余额、退出企业价值与股权桥、MOIC/IRR及模型检查。专属审计器读取生成时冻结且绑定工作簿SHA-256的完整公式单元格清单；任一必需单元格变成静态值、公式失去输入或计算链引用、工作表缺失或哈希变化均为`FAIL`。不得缩小、重写或用模型自报的`formula_ranges`替代该固定清单。

`assets/lbo/`提供一套可直接复测的参考资产：

- `example-case.json`：符合生成器输入结构的示例交易与融资假设；
- `lbo-model-template.xlsx`：由固定生成器从示例输入生成的公式工作簿；
- `workbook-contract-example.json`：与示例工作簿SHA-256及完整公式清单绑定的审计契约。

参考资产只用于理解结构、回归测试和失败注入，不得将示例公司、交易条款或计算值用于正式任务。正式任务必须使用本次证据与假设生成新的`case.json`、工作簿和审计契约，并重新运行专属审计器；不得复制示例工作簿后仅替换展示数值。

## 质量底线

完成原子验证后按`references/model-and-artifact-controls.md`运行统一质量门，工作流参数为`lbo`。G3必须纳入Sources & Uses、分层债务、现金循环、利息、到期偿付、退出桥、MOIC/XIRR和回报归因；G5的`release-decision.json`未允许结论时，不得显示MOIC、IRR、最高收购价或回报判断。

- 不混用市值、股权价值和企业价值。
- 不混用报告期、LTM和预测年度。
- 不混用人民币、港元、美元或元、万元、百万元、亿元。
- 不把MOIC解释为年化收益率。
- 有中期分红、追加投资或非规则日期时必须使用XIRR。
- 不允许债务无理由为负、循环额度超限或现金低于最低现金而不报警。
- Base Case不默认倍数扩张。
- 聚合数据与原始申报冲突时，以口径正确、日期匹配的原始申报为主并解释差异。

## 维护与测试

修改计算规则后运行：

    python3 scripts/lbo/test_lbo_engine.py
    python3 scripts/lbo/test_lbo_workbook.py
    python3 scripts/lbo/validate_case.py --self-test

只有测试通过后才使用新结果。

<!-- END OF FILE: workflow-lbo.md -->
