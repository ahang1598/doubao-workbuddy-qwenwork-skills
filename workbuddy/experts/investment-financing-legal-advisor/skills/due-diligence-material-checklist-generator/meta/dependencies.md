# 上下游技能依赖

## 下游技能（本技能产物被其消费）

| 技能 | 依赖程度 | 说明 |
|------|----------|------|
| company-equity-due-diligence（07） | 必需 | 本技能生成索取清单（事前），07生成尽调报告（事后）；清单数据经 output-interface.md 定义的 JSON Schema 流入尽调报告流程 |
| cap-market-cap-table-verify | 推荐 | PE场景回收的股权/融资材料→股权结构核验与稀释模拟 |
| cap-market-founder-liability-review | 推荐 | PE场景回收的回购/连带/担保文件→创始人个人责任提取 |
| cap-market-adversarial-clause-analysis | 推荐 | 回收的投资者权利文件→条款对抗性/陷阱识别 |
| cap-market-special-rights-design | 推荐 | 投资者权利文件→特殊权利条款设计参考 |
| cap-market-multi-round-consistency | 推荐 | 多轮融资材料→跨轮一致性比对 |
| 02-股东确权与代持风险处置 | 推荐 | 股权类材料红旗→确权与代持分析 |
| 03-公司治理诊断与合规审查 | 推荐 | 治理类材料红旗→治理诊断 |

## 对比技能

| 技能 | 区分点 |
|------|--------|
| company-equity-due-diligence（07） | 清单生成（事前）vs 尽调报告（事后） |
| 01-起草和审查投资意向书 | 投前合规快筛 vs 材料索取 |
