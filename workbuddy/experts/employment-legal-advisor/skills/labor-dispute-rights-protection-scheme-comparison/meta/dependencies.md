# 依赖关系 | 劳动争议维权方案对比

> 版本: 3.1.0

## 1. 上游技能依赖

| 技能 | 必需程度 | 用途 | 触发条件 |
|------|---------|------|---------|
| 通用法律检索 | 必需 | 联网核实法条原文（§17.15） | 引用任何法条时 |
| labor-dispute-strategy | 可选 | 已经过策略分析时直接使用 | 用户使用该技能后再用本技能 |

## 2. 下游技能协同

| 技能 | 关系 | 说明 |
|------|------|------|
| labor-arbitration-application | 下游 | 确定仲裁方案后可调用生成仲裁申请书 |
| labor-lawsuit-complaint | 下游 | 确定诉讼方案后可调用生成起诉状 |
| settlement-agreement-draft | 下游 | 确定协商和解方案后可调用生成和解协议 |
| labor-evidence-guide | 协同 | 证据缺口时推荐使用 |
| labor-limitation-analysis | 协同 | 时效存疑时推荐使用 |
| labor-contract-review | 协同 | 涉及合同条款争议时推荐使用 |
| labor-wage-arrears-calc | 协同 | 涉及工资/加班费计算时推荐使用 |
| workinj-comp-calc | 协同 | 涉及工伤赔偿金额估算时推荐使用 |

## 3. 格式/视觉依赖

| 依赖 | 用途 | 路径 |
|------|------|------|
| HTML报告模板 | 报告结构框架 | templates/html/labor-remedy-compare-template.html |
| CSS样式表 | 报告视觉渲染 | templates/css/labor-remedy-compare-C-Professional.css |
| common/视觉规范体系 | 风险色谱/排版参数/免责声明 | common/visual-spec |
