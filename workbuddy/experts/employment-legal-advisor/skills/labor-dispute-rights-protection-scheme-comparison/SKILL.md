---
name: labor-dispute-rights-protection-scheme-comparison
name_en: labor-dispute-rights-protection-scheme-comparison
version: 1.0.0
description: 劳动争议多维权方案对比报告。触发：劳动仲裁/拖欠工资/违法解除/工伤待遇/未签合同/竞业限制等维权方案比较。不触发：民事案件维权（合同/侵权/借贷等非劳动关系纠纷）、具体文书起草、案件策略分析。
---

<!-- Copyright © 深圳市法大大网络科技有限公司 版权所有 | Author: 法大大法律AI产品线 -->

# 劳动争议维权方案对比

## 1. 法律合规声明

本技能生成的维权方案对比报告仅供当事人决策参考，不构成法律意见。方案选择须由执业律师结合案件具体情况判断。法条引用基于知识截止日前的现行文本，使用前须检索确认（§17.15 法条检索强制契约）。本技能不保证选择任何方案的结果。报告中的金额估算为基于法律规定的推算，实际结果可能因证据、裁判尺度等因素变化。

## 2. 快速开始

**最少输入**：当事人身份 + 核心诉求 + 争议基本事实

```
当事人：我被公司违法解除，工作3年，月工资8000元
诉求：要公司赔偿，越快越好
补充：公司还在经营，没有离职证明
```

技能将构建可行维权方案候选集，对每个方案进行六维对比，输出双版本HTML对比报告：O1客户版（C-Professional，术语通俗化）+ O2律师版（I-Practical，含内部标注）。

## 3. 执行管线（如何一步一步生成报告）

### Phase 1: 输入解析与九类分类 [L1]

**你要做的事**：
1. **读取输入**：从律师的自然语言/结构化输入中提取信息
2. **九类归类**：将信息按A-I九类分类（规格见 [references/input-spec.md](references/input-spec.md)）
3. **完整度评级**：按照四档给当前输入打分（★★★★/★★★☆/★★☆☆/★☆☆☆）
4. **缺口补全**：若★★☆☆或★☆☆☆ → 输出C+D+G最小骨架（见§3.7），不继续后续Phase；若★★★☆ → 交互补全缺失的A/B类（最多3轮），补完后继续
5. **输出**：`classified_input` = 九类归类结果 + 完整度评级

**门控**：P0项（身份/诉求/事实/工龄工资）齐全 → 进入Phase 2；否则 → SOFT_DEGRADED

### Phase 2: 方案候选集构建 [L2]

**你要做的事**——按以下五步顺序执行：

**第1步：确定争议类型**。从以下7种常见争议中识别匹配项：
1. 违法解除 → 赔偿金2N / 恢复劳动关系
2. 拖欠工资 → 追索工资+赔偿金 / 加付赔偿金（85条）
3. 未签书面合同 → 双倍工资差额（最长11个月）
4. 工伤待遇 → 工伤认定→鉴定→索赔（不走仲裁前置）
5. 经济补偿争议 → N或N+1经济补偿金
6. 竞业限制/保密 → 竞业补偿金 / 违约金追索
7. 确认劳动关系 → 身份确认→待遇附着

若争议跨越多个类型 → 合并标注，每个类型独立构建方案。

**第2步：映射方案组合**。基于争议类型，从方法论决策树 [references/methodology.md §2](references/methodology.md) 中提取标准方案组合。每组方案包含：主通道+备选通道+对应请求权族。

**第3步：五维标注**。为每个候选方案打上标签：
- 程序通道（1-9编号）
- 请求权族（1-5族）
- 策略类型（单兵/组合拳/分步推进/保全护航）
- 身份视角（劳动者/企业方）
- 时效状态（正常/临界/已超）

**第4步：时效过滤**。逐通道检查时效：
- 仲裁时效1年 → 超时 = 红色标注"不可行"，但仍列入矩阵供当事人知情
- 拖欠工资特殊规则 → 标注"在职期间不受1年限制"
- 15日起诉期限 → 超时标注
- 工伤认定1年 → 超时标注

**第5步：排序输出**。按"推荐优先级"排序：时效正常+证据充分 → 时效正常+证据不足 → 时效临界 → 超时效
- 输出 `scheme_candidates[N]`，N 通常为 **3-6 个方案**
- 最少2个，最多不超过8个（超过则合并相似方案）

**门控**：至少2个可行方案 → 进入Phase 3

### Phase 3: 六维对比矩阵构建 [L2]

**你要做的事**——对照 [references/methodology.md §3](references/methodology.md) 的推理框架，对每个方案逐维度对比：

**维度1: 法律依据** → 列出核心法条+构成要件满足情况+法律依据层级

**维度2: 胜败概率** → 用"高（70%+）/中（40-70%）/低（<40%）"三级标注，附录影响概率的关键因素清单

**维度3: 预期金额** → **必须给出三区间**（最佳X元/一般X元/最差X元），计算示例：
- 赔偿金2N = 月均工资 × 工作年限 × 2
- 经济补偿金N = 月均工资 × 工作年限
- 双倍工资 = 月均工资 × 未签合同月数（上限11个月）
- 加班费 = 时薪 × 加班时长 × 倍数（1.5/2.0/3.0）

**维度4: 时间成本** → 按阶段估算（协商→调解→仲裁→一审→二审→执行），标注总周期范围

**维度5: 经济成本** → 全口径计算：律师费+仲裁费/诉讼费+保全费+鉴定费+交通费+时间机会成本

**维度6: 风险副作用** → 列出：举证不能/执行不能/反诉/关系破裂/声誉/群体效应风险

**输出**：`comparison_matrix[N][6]` = N个方案×6个维度的对比数据矩阵

**推荐推理**：基于五步推理链选出推荐方案——
争议类型→请求权基础→证据充分度→时效状态→当事人诉求优先级

### Phase 4: 受众适配与双版本HTML组装 [L2]

**你要做的事**——分三步生成两份HTML报告：

**第1步：生成 O1 客户版 HTML**。先生成客户版（后端数据一致，前端展示裁剪）：

1. **受众语言转换**——按 [rules/terminology.md §5](rules/terminology.md) 的三层适配规则：
   - 词级：按 §2 对照表替换法律术语为当事人语言
   - 段落级：将"法律分析段"改写为"当事人可理解的方案对比段"
   - 全文级：根据当事人身份选择语气（劳动者→"您"，企业方→"贵司"）

2. **客户版裁剪**——按 [references/output-spec.md §2](references/output-spec.md) 的8条规则执行：
   - R1 移除内部标记（L1/L2/L3/Phase编号/D1-D6）→ R2 移除置信度 → R3 移除下游技能 → R4 移除假设条件 → R5 术语通俗化 → R6 人称适配 → R7 免责措辞适配 → R8 标题受众标识

3. **HTML区块填充**——按模板六大占位符逐区块填充：
   - `{{CASE_SUMMARY}}` → 案情摘要卡片（2列网格）
   - `{{SCHEME_OVERVIEW}}` → 五维标签云 + 通道×请求权矩阵表
   - `{{COMPARISON_MATRIX}}` → 并排卡片（头部色标+六维对比表+金额柱状图+风险折叠详情）
   - `{{RECOMMENDATION}}` → 推荐方案高亮框 + 五步推理链 + 三种结果预期
   - `{{OPERATION_GUIDE}}` → 可折叠面板（受理机构+材料清单+步骤+时间+费用）
   - `{{LIMITATION_WARNING}}` → 红色时效警告框 + 执行风险 + 免责声明

   **风险色标规则**：方案卡片头部统一深蓝底色 #1B4F72，风险仅通过左侧 5px 窄色条传达——`risk-high`→砖红#C0392B / `risk-medium`→古铜金#D4A017 / `risk-low`→柔和绿#27AE60。整页主色为蓝，风险色仅精准点缀。

4. **O1 输出**：写入 `[案件简称]-维权方案对比报告-客户版.html`

**第2步：生成 O2 律师版 HTML**。以 O1 为基础，做以下变更：

1. **人称回退**：客户版"您"→"当事人"，"贵司"→"公司/企业方"（按 [references/output-spec.md §2.1](references/output-spec.md) 对照表逆向转换）
2. **恢复专业术语**：客户化表述回退为法律术语（如"双倍补偿金"→"赔偿金2N"）
3. **追加内部标注区块**：在 `{{LIMITATION_WARNING}}` 区块之后、footer 之前，插入 `{{LAWYER_INTERNAL_ANNOTATIONS}}` 占位符的内容（详见 [references/output-spec.md §3](references/output-spec.md)）：
   - 信息充足度 D1-D6 评分表
   - 置信度矩阵（六维 × N方案）
   - 假设条件清单
   - 方案切换触发条件表
   - 下游技能衔接建议表
   - 风险分级表（Phase级别 + 整体L2）
   - 底部免责用律师版措辞

4. **O2 输出**：写入 `[案件简称]-维权方案对比报告-律师版.html`

**第3步：简报确认**。向律师展示：
- ✅ O1 客户版已生成（路径：[文件路径]）
- ✅ O2 律师版已生成（路径：[文件路径]）
- 关键差异：O2 含信息充足度/置信度矩阵/假设条件/下游技能衔接/路径切换触发/风险分级
- 提醒：客户版请勿泄露给客户以外的第三方

### Phase 5: 合规红线检查 [L1]

**你要做的事**——逐条对照14条写作红线自检。检查清单见 [references/output-spec.md §5](references/output-spec.md)。发现红线违规 → 立即修正。

### Phase 6: 质量检查 [L1]

**你要做的事**——对照 [rules/quality-standards.md](rules/quality-standards.md) 逐项自检（35阻断+10警告+10格式），不通过项修正后重新检查。法条引用须联网核实原文。

### 3.7 SOFT_DEGRADED C+D+G

当输入不足（★☆☆☆或★★☆☆）时，输出最小骨架。完整规格见 [rules/risk-framework.md §4](rules/risk-framework.md)。

**C) Missing Facts Checklist**：

| 缺失项 | 影响程度 | 建议来源 |
|--------|---------|---------|
| 争议基本事实 | boundary | 当事人叙述/书面材料 |
| 证据情况 | evaluation | 合同/工资记录/聊天记录/通知书 |
| 时效状态 | boundary | 争议发生日期/仲裁申请日期 |
| 当事人身份 | boundary | 劳动者/企业方 |
| 对方信息 | evaluation | 企查查/天眼查/当事人了解 |
| 工龄与工资 | evaluation | 劳动合同/银行流水 |
| 诉求详细说明 | content_detail | 当事人明确诉求优先级/底线 |

**D) Governance & Non-Goals**：
- ban_boundary_items：保证胜诉、确定结果、推荐具体方案而不说明前提条件、跳过仲裁前置
- non_goal_items：教唆信访、煽动群体性事件、具体法律文书起草（用对应技能）、案件策略分析（用labor-dispute-strategy）

**G) Actionable Next Steps**：
- upgrade_actions：补充争议基本事实、收集关键证据（合同/工资记录/解除通知书）、确认时效状态、查询对方经营状况
- target_fields：dispute_facts / evidence / time_status / party_role / counterparty_info / seniority_and_wage

## 4. 写作红线（14条）

- ❌ 禁止推荐超出法定期限的方案而不加警告
- ❌ 禁止遗漏仲裁前置原则说明
- ❌ 禁止将仲裁时效称为"诉讼时效"
- ❌ 禁止方案推荐无完整推理链
- ❌ 禁止操作指引缺少受理机构或申请材料
- ❌ 禁止保证任何方案的胜诉概率或结果
- ❌ 禁止使用内部律师术语而不附通俗解释
- ❌ 禁止向当事人输出"建议信访"作为主要方案
- ❌ 禁止使用煽动性、情绪化、对立性语言
- ❌ 禁止遗漏时效倒计时提示
- ❌ 禁止遗漏执行可行性评估
- ❌ 禁止在金额估算中给出单一确定数字（须用区间）
- ❌ 禁止省略免责声明
- ❌ 禁止对劳动者和企业方使用同一套方案表述

## 5. 适用边界

### 5.1 适用范围
- 中国境内劳动争议的维权方案选择分析
- 劳动者方或用人单位方
- 争议发生后的维权路径决策

### 5.2 不适用
- 具体法律文书起草（用对应文书技能）
- 案件策略分析（用 labor-dispute-strategy）
- 非劳动争议的救济路径
- 工伤赔偿计算（用 workinj-comp-calc）

### 5.3 hard_reject_conditions
- 明确要求保证胜诉
- 非劳动争议
- 要求教唆群体性事件
- 要求策划违法/违规行为

---

> 📋 文档索引
> - 核心方法论：[references/methodology.md](references/methodology.md)
> - 输入规格：[references/input-spec.md](references/input-spec.md)
> - 输出规格：[references/output-spec.md](references/output-spec.md)
> - 工作流程：[references/workflow-detail.md](references/workflow-detail.md)
> - 法律依据：[references/legal-references.md](references/legal-references.md)
> - 质量标准：[rules/quality-standards.md](rules/quality-standards.md)
> - 风险框架：[rules/risk-framework.md](rules/risk-framework.md)
> - 术语规范：[rules/terminology.md](rules/terminology.md)
> - HTML模板：[templates/compare-template.html](templates/compare-template.html)
> - CSS样式：[templates/css/labor-remedy-compare-C-Professional.css](templates/css/labor-remedy-compare-C-Professional.css)
> - 依赖关系：[meta/dependencies.md](meta/dependencies.md)
> - 已知限制：[meta/known-limitations.md](meta/known-limitations.md)
> - 格式索引：[references/format-spec.md](references/format-spec.md)
> - 使用说明：[USAGE.md](USAGE.md)
> - 设计文档：[DESIGN.md](DESIGN.md)
