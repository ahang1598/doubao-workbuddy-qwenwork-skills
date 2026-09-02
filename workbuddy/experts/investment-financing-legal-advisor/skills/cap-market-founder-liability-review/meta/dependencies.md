# 上下游技能依赖

## 上游技能

| 技能 | 依赖程度 | 说明 |
|------|----------|------|
| 06-投资协议审查（investment-agreement-review） | 推荐 | 协议解析能力可复用 |

## 下游技能

| 技能 | 依赖程度 | 说明 |
|------|----------|------|
| post-holder-protection（股东权益保护） | 推荐 | 责任清单→创始人/股东权益保护条款谈判方案 |
| investment-exit-dispute-resolution（投融资退出争议解决） | 推荐 | 责任触发→退出路径选择与争议解决 |

## 对比技能

| 技能 | 区分点 |
|------|--------|
| investment-agreement-review（06） | 条款合规性全量审查 vs 创始人个人责任提取归集 |
| draft-and-review-investment-intent（01） | 正式协议 vs 意向书 |
| cap-market-adversarial-clause-analysis | 责任归集量化 vs 条款对抗性识别（详见 §双向联动） |

## 双向联动说明

- **↔ adversarial（对抗性审查）**：本技能负责"责任归集与量化"（识别创始人承担的所有个人责任 + 计算总敞口）；`cap-market-adversarial-clause-analysis` 负责"条款对抗性识别"（T1-T12 陷阱、市场惯例偏离度、修改建议）。分工互补：本技能输出责任清单+总敞口 → adversarial 据以做对抗性专项；或 adversarial 先识别陷阱 → 本技能归集量化。两者不重复：对抗性识别由 adversarial 主导，责任归集由本技能主导。
- **→ cap-table-verify（对赌减资量化）**：含对赌(VAM)现金回购时，其 Cap Table 变动量化由 `cap-market-cap-table-verify`（§十）完成；本技能只归集回购责任并提示减资程序（新公司法第224/162条，有限公司另见第89条），不重复做量化。
- **→ post-holder-protection（权益保护）**：责任清单与谈判建议可作为创始人/股东权益保护方案输入。

## 弱引用声明

本技能为独立分析工具，不强制依赖上游技能输出。与其他资本市场技能的关系为推荐协作而非硬依赖。
