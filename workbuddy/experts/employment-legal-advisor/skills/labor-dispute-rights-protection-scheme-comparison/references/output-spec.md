# 输出规格 | 劳动争议维权方案对比

> 版本: 3.1.0 | 风险等级: L2
> 格式严肃度: O1=C-Professional（客户/委托方受众），O2=I-Practical（律师内部使用）
> 交付物：双HTML报告——O1客户版 + O2律师版（含内部标注）

## 1. format_capabilities 声明

```json
{
  "format_capabilities": [
    {
      "format": "html_professional",
      "supports": ["interactive_comparison", "risk_color_spectrum", "collapsible_panels", "print_export", "email_attachment", "responsive_layout", "dual_version_client_lawyer"],
      "template": "templates/html/labor-remedy-compare-template.html",
      "css": "templates/css/labor-remedy-compare-C-Professional.css"
    }
  ],
  "default_output": {
    "o1_format": "html",
    "o1_audience": "当事人（终端客户）",
    "o1_seriousness": "C-Professional",
    "o1_description": "客户版——术语通俗化，无内部标注，受众适配语言",
    "o2_format": "html",
    "o2_audience": "律师（内部使用）",
    "o2_seriousness": "I-Practical",
    "o2_description": "律师版——含内部标注区块（置信度矩阵/假设条件/下游技能衔接/风险分级/路径切换触发），使用律师第三人称"
  }
}
```

### 1.1 双版本架构说明

| | O1 客户版 | O2 律师版 |
|---|---|---|
| 格式 | HTML | HTML |
| 受众 | 当事人（劳动者/企业方） | 执业律师 |
| 严肃度 | C-Professional | I-Practical |
| 语言 | 第二人称（"您"/"贵司"），术语通俗化 | 第三人称（"当事人"/"我方"/"对方"），可含专业术语 |
| 内部标注 | ❌ 无 | ✅ 含七、内部标注区块 |
| 置信度 | ❌ 无 | ✅ 含 |
| 假设条件 | ❌ 无（已融入分析） | ✅ 显式列出 |
| 下游技能衔接 | ❌ 无 | ✅ 含 |
| 风险分级标记 | ❌ 无（客户化表达） | ✅ 含L1/L2/L3 |
| 路径切换触发 | ❌ 无 | ✅ 含 |
| 信息充足度 | ❌ 无 | ✅ D1-D6评分 |

### 1.2 生成顺序

1. 先生成 O1 客户版（完整六段式HTML）
2. 在 O1 基础上，追加「七、内部标注」区块 → 生成 O2 律师版
3. 律师版对客户版正文做人称回退（"您"→"当事人"、"贵司"→"公司/企业方"）

## 2. 受众裁剪规则（客户版适用，8条）

> 以下规则对标 remedy-path-compare §2 受众版本裁剪规则，Phase 4 生成客户版时必须执行。

| # | 规则 | 说明 | 示例 |
|---|------|------|------|
| R1 | 移除内部标记 | 不出现L1/L2/L3、SOFT_DEGRADED、Phase编号、D1-D6等内部术语 | 删除"L2-中等风险"等 |
| R2 | 移除置信度标注 | 不暴露"置信度：高/中/低"等内部判断 | 删除置信度列/标签 |
| R3 | 移除下游技能建议 | 客户不需要知道技能名（如→labor-arbitration-defense） | 删除技能衔接区块 |
| R4 | 移除假设条件清单 | 假设已融入分析，不再单独标注 | 删除"假设条件"区块 |
| R5 | 术语通俗化 | 按terminology.md §2对照表替换律师术语为当事人语言 | "赔偿金2N"→"双倍补偿金（违法解除时的赔偿标准）" |
| R6 | 人称适配 | 劳动者用"您"、企业方用"贵司" | 按Phase 1的身份判定自动选择 |
| R7 | 免责措辞适配 | 客户版底部免责用客户化表述 | "供您决策参考"而非"内部参考" |
| R8 | 标题受众标识 | 报告标题区含受众标识 | 头部meta行显示"适用对象：劳动者/企业方" |

### 2.1 受众人称转换对照表（客户版←律师版）

| 律师版表述 | 客户版（劳动者） | 客户版（企业方） |
|-----------|----------------|-----------------|
| 当事人 | 您 | 贵司 |
| 我方 | 您 | 贵司 |
| 对方/用人单位 | 公司 | 该员工 |
| 该案 | 您的案子 | 贵司案件 |
| 建议当事人 | 建议您 | 建议贵司 |
| 劳动者 | 您 | 该员工 |
| 本报告仅供内部参考 | 本报告供您决策参考 | 本报告供贵司决策参考 |
| 成本区间 | 您需要准备约 | 贵司需准备约 |

### 2.2 免责措辞对照表

| 场景 | 律师版 | 客户版 |
|------|--------|--------|
| 报告尾部声明 | "本报告为律师工作辅助产物，不构成正式法律意见" | "本报告供您/贵司决策参考，不构成正式法律意见" |
| 信息边界 | "本报告基于以下信息" | "本报告基于您/贵司提供的信息" |
| 结果免责 | "所有评估均为定性判断，不承诺维权结果" | "所有评估为定性判断，具体结果取决于案件实际情况" |
| 专业提示 | "建议由专业律师根据案件具体情况确定最终方案" | "建议您与律师进一步沟通后确定最终方案" |

## 3. O2 律师版专属：内部标注区块规格

> 律师版 = 客户版全文 + 以下「七、内部标注」区块。使用HTML注释 `<!-- 律师版额外内容 -->` 分隔。

### 3.1 内部标注区块骨架

```html
<!-- 律师版额外内容 -->
<section id="internal-annotations" class="lawyer-only">
  <h2 class="section-title">七、内部标注 <span class="audience-tag">仅律师版</span></h2>

  <!-- 3.2 信息充足度 -->
  <div class="annotation-block">
    <h3>信息充足度</h3>
    <table>
      <tr><td>D1 争议事实</td><td>[X]%</td><td>[评估]</td></tr>
      <tr><td>D2 证据材料</td><td>[X]%</td><td>[评估]</td></tr>
      <tr><td>D3 时效状态</td><td>[X]%</td><td>[评估]</td></tr>
      <tr><td>D4 当事人身份</td><td>[X]%</td><td>[评估]</td></tr>
      <tr><td>D5 对方信息</td><td>[X]%</td><td>[评估]</td></tr>
      <tr><td>D6 诉求明确度</td><td>[X]%</td><td>[评估]</td></tr>
      <tr class="total-row"><td>总充足度</td><td colspan="2">[X]%</td></tr>
    </table>
  </div>

  <!-- 3.3 置信度矩阵 -->
  <div class="annotation-block">
    <h3>置信度矩阵（六维 × N方案）</h3>
    <table>
      <tr><th>维度</th><th>S1 [方案名]</th><th>S2 [方案名]</th><th>…</th></tr>
      <tr><td>法律依据</td><td>高</td><td>中</td><td>…</td></tr>
      <tr><td>胜败概率</td><td>高</td><td>中</td><td>…</td></tr>
      <tr><td>预期金额</td><td>中</td><td>低</td><td>…</td></tr>
      <tr><td>时间成本</td><td>高</td><td>中</td><td>…</td></tr>
      <tr><td>经济成本</td><td>高</td><td>中</td><td>…</td></tr>
      <tr><td>风险副作用</td><td>中</td><td>高</td><td>…</td></tr>
    </table>
    <p class="confidence-note">置信度定义：高=信息充分可直接判断 / 中=部分信息需假设 / 低=信息不足判断不可靠</p>
  </div>

  <!-- 3.4 假设条件清单 -->
  <div class="annotation-block">
    <h3>假设条件</h3>
    <ol>
      <li>[假设1]：[说明]</li>
      <li>[假设2]：[说明]</li>
      <li>…</li>
    </ol>
  </div>

  <!-- 3.5 方案切换触发条件 -->
  <div class="annotation-block">
    <h3>方案切换触发条件</h3>
    <table>
      <tr><th>当前方案</th><th>触发条件</th><th>切换到</th><th>时限</th></tr>
      <tr><td>S1 [方案名]</td><td>[条件]</td><td>S3 [方案名]</td><td>[时限]</td></tr>
      <tr><td>…</td><td>…</td><td>…</td><td>…</td></tr>
    </table>
  </div>

  <!-- 3.6 下游技能衔接 -->
  <div class="annotation-block">
    <h3>下游技能衔接</h3>
    <table>
      <tr><th>推荐方案</th><th>下一步需要</th><th>推荐技能</th></tr>
      <tr><td>S1 赔偿金2N仲裁</td><td>仲裁申请书</td><td>labor-arbitration-application</td></tr>
      <tr><td>S3 协商和解</td><td>和解协议</td><td>settlement-agreement-draft</td></tr>
      <tr><td>S2 恢复劳动关系</td><td>仲裁申请书（恢复劳动关系）</td><td>labor-arbitration-application</td></tr>
      <tr><td>全部方案</td><td>证据整理分析</td><td>labor-evidence-guide</td></tr>
      <tr><td>全部方案</td><td>时效精确计算</td><td>labor-limitation-analysis</td></tr>
    </table>
  </div>

  <!-- 3.7 风险分级 -->
  <div class="annotation-block">
    <h3>风险分级</h3>
    <table>
      <tr><th>Phase</th><th>风险等级</th><th>说明</th></tr>
      <tr><td>Phase 3 六维对比矩阵构建</td><td>L2（整体）</td><td>方案对比整体为L2风险</td></tr>
      <tr><td>Phase 3 · 胜败概率评估子步骤</td><td>L3</td><td>概率评估直接关联当事人决策，属Phase 3内高敏感子步骤</td></tr>
      <tr><td>Phase 4（报告组装）</td><td>L2</td><td>受众语言转换影响信息传达准确性</td></tr>
      <tr><td>整体</td><td>L2</td><td>方案推荐影响权益，但不替代律师判断</td></tr>
    </table>
  </div>
</section>
```

### 3.2 律师版 CSS 补充（非客户版展示）

```css
/* 律师版专属样式 */
.lawyer-only {
  border-top: 2px dashed #1A5276;
  padding-top: 24px;
  margin-top: 20px;
}
.lawyer-only .section-title {
  color: #7B1FA2; /* 紫色区分律师版 */
}
.lawyer-only .audience-tag {
  font-size: 12px;
  color: #7B1FA2;
  font-weight: normal;
  background: #F3E5F5;
  padding: 2px 8px;
  border-radius: 10px;
  margin-left: 8px;
}
.annotation-block {
  background: #FAFAFA;
  border: 1px solid #E0E0E0;
  border-radius: 6px;
  padding: 14px;
  margin-bottom: 14px;
}
.annotation-block h3 {
  font-size: 14px;
  color: #7B1FA2;
  margin-bottom: 8px;
  border-bottom: 1px solid #F3E5F5;
  padding-bottom: 6px;
}
.annotation-block table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.annotation-block td, .annotation-block th {
  border: 1px solid #E0E0E0;
  padding: 6px 10px;
}
.annotation-block th {
  background: #F5F5F5;
  font-weight: 500;
}
.annotation-block .total-row {
  font-weight: 600;
  background: #FFF8E1;
}
.confidence-note {
  font-size: 12px;
  color: #616161;
  margin-top: 8px;
  font-style: italic;
}
.annotation-block ol {
  padding-left: 20px;
  font-size: 13px;
  line-height: 1.8;
}
```

## 4. O1/O2 共有：HTML报告六段式结构

### 4.1 案情摘要与当事人画像

**占位符**：`{{CASE_SUMMARY}}`

- 一句话案情概况（谁/何时/发生了什么/争议焦点）
- 当事人关键事实要素（身份/工龄/工资标准/合同状态/特殊身份）
- 对方画像摘要（经营状况/偿付能力/涉诉情况）
- 程序状态标注（当前阶段/时效倒计时）

### 4.2 维权方案全景概览

**占位符**：`{{SCHEME_OVERVIEW}}`

- 五维体系可视化卡片（程序通道/请求权类型/策略组合/身份视角/时效状态）
- 适用通道×可行请求权矩阵表
- 方案候选集一览表（方案编号/名称/核心诉求/策略类型/优先级排序）

### 4.3 方案对比矩阵

**占位符**：`{{COMPARISON_MATRIX}}`

并排卡片布局，每个方案一张卡片，内含：

| 对比维度 | 呈现方式 | 说明 |
|---------|---------|------|
| 法律依据 | 法条编号+性质标注 | 核心请求权基础 |
| 胜败概率 | 三级色标（红/琥珀/绿）+关键因素 | 基于证据+时效评估 |
| 预期金额 | 三区间柱状图CSS | 最佳/一般/最差结果 |
| 时间成本 | 进度条+阶段标注 | 各阶段耗时预估 |
| 经济成本 | 明细列举 | 律师费+仲裁费+其他 |
| 风险副作用 | 色标+折叠详情 | 举证/执行/关系/声誉风险 |

风险色谱标准：
- 🔴 砖红（#C0392B）：高风险——时效临界/证据严重不足/对方无偿付能力
- 🟡 古铜金（#D4A017）：中风险——部分证据缺失/存在法律争议
- 🟢 柔和绿（#27AE60）：低风险——法律依据清晰/证据充分/时效充裕

**风险色标的呈现方式**：方案卡片头部统一为深蓝底色（#1B4F72），风险等级仅通过卡片左侧5px窄色条+名称旁文字标签传达，不做整片着色。原则：蓝为主色传递专业感，风险色仅做精准点缀。

### 4.4 推荐方案与理由

**占位符**：`{{RECOMMENDATION}}`

- 推荐方案高亮卡片（浅蓝底蓝边框）
- 五步推理链：争议类型→请求权基础→证据充分度→时效状态→当事人诉求优先级
- 推荐方案的最佳/一般/最差三种结果预期
- 备选方案简述

### 4.5 各方案操作指引

**占位符**：`{{OPERATION_GUIDE}}`

可折叠面板（`<details><summary>`），每方案含：
- 受理机构（全称+地址查找方式）
- 申请材料清单
- 程序步骤（编号列举）
- 时间预估（各阶段耗时）
- 费用预估

### 4.6 时效提醒与风险提示

**占位符**：`{{LIMITATION_WARNING}}`

- 关键时效倒计时提醒（白底砖红边框框）
- 执行风险提示（对方偿付能力评估）
- 受众适配声明："本报告为律师基于您提供的情况所作的分析参考，不构成法律意见。维权方案的具体选择，请与您的律师充分讨论后决定。"
- 底部免责声明

## 5. 排版参数（C-Professional）

| 参数 | 值 | 说明 |
|------|------|------|
| 字体 | PingFang SC / Microsoft YaHei | 正文 |
| 正文字号 | 14px | 主体内容 |
| 标题字号 | 24px/16px | 一级/二级标题 |
| 页边距 | 2.5/2.0/2.8/2.6cm | 上/下/左/右 |
| 色系 | 深蓝#1A5276（主色）+ 砖红#C0392B/古铜金#D4A017/柔和绿#27AE60（风险点缀） | 专业感+风险仅点缀 |
| 行间距 | 1.6 | 阅读舒适 |
| 卡片间距 | 16px | 方案对比卡片 |

## 6. 打印适配

```css
@media print {
  details { display: block; }
  .interactive-only { display: none; }
  .scheme-card { break-inside: avoid; }
  @page { margin: 25mm 20mm; size: A4; }
}
```

## 7. 写作红线

> 规范源：SKILL.md §4。以下为快速检查清单，完整红线规则以 SKILL.md 为准。

- ❌ 禁止推荐超出法定期限的方案而不加警告
- ❌ 禁止遗漏仲裁前置原则说明
- ❌ 禁止将仲裁时效称为"诉讼时效"
- ❌ 禁止方案推荐无完整五步推理链
- ❌ 禁止操作指引缺少受理机构或申请材料
- ❌ 禁止保证任何方案的胜诉概率或结果
- ❌ 禁止使用内部律师术语而不附通俗解释
- ❌ 禁止向当事人输出"建议信访"作为主要方案
- ❌ 禁止使用煽动性/情绪化/对立性语言
- ❌ 禁止遗漏时效倒计时提示
- ❌ 禁止遗漏执行可行性评估
- ❌ 禁止金额估算给出单一确定数字
- ❌ 禁止省略免责声明
- ❌ 禁止对劳动者和企业方使用同一套方案表述

## 8. 质量自检清单（与 rules/quality-standards.md 对齐）

| 维度 | 检查项数 | 阻断/警告 |
|------|---------|----------|
| 方案覆盖完整性 | 5 | 5阻断 |
| 对比维度充分性 | 4 | 4阻断 |
| 时效风险提示 | 4 | 4阻断 |
| 受众适配 | 4 | 4阻断 |
| HTML质量 | 4 | 4阻断 |
| 双版本完整性 | 12 | 12阻断 |
| 合规 | 2 | 2阻断 |
| **阻断合计** | **35** | **35阻断** |
| 警告项 | 10 | 10警告 |
| 格式项 | 10 | 10格式 |
