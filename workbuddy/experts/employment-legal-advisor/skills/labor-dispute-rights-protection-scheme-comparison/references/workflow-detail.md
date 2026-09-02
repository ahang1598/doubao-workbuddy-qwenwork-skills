# 劳动争议维权方案对比 - 工作流程详细说明

> 版本: 3.1.0 | 风险等级: L2

## Phase 1: 输入验证与九类分类 [L1]

**输入**：律师原始输入
**输出**：`classified_input` + `completeness_rating`

### 中间产物示例

```
classified_input = {
  class_A: { role: "劳动者", service_years: 3, monthly_wage: 8000, contract: "有书面合同", social_insurance: "正常缴纳" },
  class_B: { core_claim: "要求公司赔偿违法解除", priority: "尽快拿到赔偿金", bottom_line: "至少拿到N", time_requirement: "3个月内" },
  class_C: { budget: "承受律师费5000-10000", time_tolerance: "3-6个月", confidentiality: "无" },
  class_D: { entry_date: "2023-03-01", wage_standard: "8000元/月", dispute_date: "2026-05-10", termination_reason: "公司口头通知解除，未说明理由" },
  class_E: { contract: "有", wage_records: "银行流水齐全", communication: "微信记录（口头解除通知）", termination_letter: "无书面通知" },
  class_F: { lawyer_supplement: null },
  class_G: { company_status: "在经营", solvency: "正常经营，无执行信息", history_disputes: "无" },
  class_H: { current_stage: "争议发生后20天", limitation_status: "时效内（距1年到期还有345天）", arbitrated: false },
  class_I: { policy: "无特殊政策", industry: "互联网/IT", economy: "正常" }
}
completeness_rating = "★★★☆"  // 缺F类
```

### 处理步骤
1. 九类提取：从输入中自动归类到A-I九类
2. 完整度评级：★★★★（全部齐备）/★★★☆（缺1-2类）/★★☆☆（缺3-4类）/★☆☆☆（仅知诉求）
3. 缺口补全（≤3轮交互）
4. 门控判定

---

## Phase 2: 五维方案候选集构建 [L2]

**输入**：classified_input
**输出**：`scheme_candidates[N]`，N 通常为 **3-6个方案**（最少2个，最多8个）

### 中间产物示例（以"违法解除"为例）

```
scheme_candidates = [
  {
    scheme_id: "S1",
    scheme_name: "赔偿金2N仲裁",
    channel: [3],  // 劳动仲裁
    claim_family: "合同保护族",
    claim_basis: "赔偿金2N（劳动合同法第87条）",
    strategy: "单兵",
    perspective: "劳动者",
    limitation: { status: "正常", days_remaining: 345 },
    priority: 1,
    key_calc: "2N = 8000 × 3 × 2 = 48,000元（最佳）",
    feasibility: "高"
  },
  {
    scheme_id: "S2",
    scheme_name: "恢复劳动关系仲裁",
    channel: [3],
    claim_family: "身份确认族",
    claim_basis: "恢复劳动关系+补发工资（劳动合同法第48条）",
    strategy: "单兵",
    perspective: "劳动者",
    limitation: { status: "正常", days_remaining: 345 },
    priority: 2,
    key_calc: "补发工资 = 8000 × 争议期间月数",
    feasibility: "中（需当事人愿意回原单位）",
    exclusion_with: ["S1"]  // 与S1互斥
  },
  {
    scheme_id: "S3",
    scheme_name: "协商和解",
    channel: [1],  // 协商
    claim_family: "合同保护族",
    claim_basis: "协商金额",
    strategy: "单兵",
    perspective: "劳动者",
    limitation: { status: "正常" },
    priority: 3,
    key_calc: "谈判区间：最佳2N(48,000)/一般1.5N(36,000)/最差N(24,000)",
    feasibility: "中（需对方配合）"
  },
  {
    scheme_id: "S4",
    scheme_name: "仲裁+监察并行（如涉及欠薪/社保）",
    channel: [3, 6],
    claim_family: "合同保护族+工资债权族",
    claim_basis: "赔偿金2N + 欠薪/社保补缴",
    strategy: "组合拳",
    perspective: "劳动者",
    limitation: { status: "待补充欠薪信息后评估" },
    priority: 4,
    key_calc: "需补充欠薪信息",
    feasibility: "条件性（当前无欠薪信息，暂不可行）"
  }
]
// N=4，其中S4标记为条件性（待补信息）
```

---

## Phase 3: 六维对比矩阵构建 [L2]

**输入**：scheme_candidates
**输出**：`comparison_matrix[N][6]`

### comparison_matrix 结构定义

```
comparison_matrix = [
  {
    scheme_id: "S1",
    scheme_name: "赔偿金2N仲裁",
    dimensions: {
      legal_basis: {
        articles: ["劳动合同法第87条", "第47条"],
        elements: {
          "存在劳动关系": { satisfied: true, evidence: "书面合同" },
          "公司单方解除": { satisfied: true, evidence: "微信通知" },
          "解除违法": { satisfied: true, evidence: "无合法事由" },
          "工作年限": { satisfied: true, evidence: "合同+工资流水(3年)" }
        },
        level: "法律"
      },
      win_probability: {
        level: "高",  // 高/中/低
        percentage_range: "70%+",
        positive_factors: ["书面合同", "银行流水", "微信解除通知"],
        negative_factors: ["解除通知未书面化"]
      },
      expected_amount: {
        best: { amount: 48000, formula: "8000×3×2", condition: "月工资8000被认可+违法解除成立" },
        average: { amount: 36000, formula: "参考类案", condition: "月工资计算基数可能有争议" },
        worst: { amount: 24000, formula: "8000×3×1", condition: "若认定为协商解除仅获N" },
        uncertainty: "月工资是否含奖金/补贴存在争议空间"
      },
      time_cost: {
        stages: [
          { stage: "仲裁", duration: "45-60天" },
          { stage: "一审(若起诉)", duration: "3-6个月", conditional: true },
          { stage: "执行", duration: "1-3个月", conditional: true }
        ],
        total: { best: "2-3个月", average: "4-6个月", worst: "12-15个月" }
      },
      economic_cost: {
        items: [
          { item: "律师费(仲裁阶段)", amount: "5000-10000" },
          { item: "仲裁费", amount: "0" },
          { item: "诉讼费(若起诉)", amount: "10", conditional: true },
          { item: "时间机会成本", amount: "10000-20000" }
        ],
        total: "15000-30010"
      },
      risks: {
        evidence_risk: { level: "中", detail: "解除理由需准备反证" },
        enforcement_risk: { level: "低", detail: "公司在正常经营" },
        counterclaim_risk: { level: "低", detail: "不构成独立反请求" },
        relationship_risk: { level: "高", detail: "仲裁后关系彻底破裂" },
        reputation_risk: { level: "低", detail: "仲裁非公开审理" }
      }
    }
  },
  // ... S2, S3, S4 同结构
]
```

### 推荐方案推理链示例

```
推荐方案：S1 赔偿金2N仲裁

推理链：
①争议类型：违法解除 → 请求权基础为赔偿金2N（劳动合同法第87条）
②构成要件全部满足（4/4项有证据支撑）
③核心证据充分（书面合同+工资流水+解除通知，3/3）
④时效充裕（距1年到期还有345天）
⑤当事人诉求优先级：尽快拿到赔偿金 → 仲裁45-60天最快
→ 综合推荐S1（赔偿金2N仲裁），概率高、金额确定、时效最快
```

---

## Phase 4: 受众适配与双版本HTML组装 [L2]

**输入**：comparison_matrix
**输出**：`o1_html_report`（客户版） + `o2_html_report`（律师版，含内部标注）

### 4.1 受众语言转换（三层适配）

详见 [rules/terminology.md §5](../rules/terminology.md)

### 4.2 O1 客户版 HTML 区块填充规则

**区块1: CASE_SUMMARY**

填充结构（替换 `{{CASE_SUMMARY}}` 占位符）：
```html
<div class="case-summary-grid">
  <div class="summary-card">
    <div class="label">当事人身份</div>
    <div class="value">劳动者，工作3年，月均工资8,000元</div>
  </div>
  <div class="summary-card">
    <div class="label">争议焦点</div>
    <div class="value">公司在无合法事由情况下口头通知解除劳动合同</div>
  </div>
  <div class="summary-card">
    <div class="label">核心诉求</div>
    <div class="value">要求公司支付违法解除赔偿金，尽快解决（期望3个月内）</div>
  </div>
  <div class="summary-card">
    <div class="label">时效状态</div>
    <div class="value" style="color:#27AE60;">时效正常（距到期还有345天）</div>
  </div>
  <div class="summary-card">
    <div class="label">对方情况</div>
    <div class="value">公司在正常经营，具备偿付能力，无涉诉记录</div>
  </div>
</div>
```

**区块3: COMPARISON_MATRIX**

每张方案卡片的HTML结构（替换 `{{COMPARISON_MATRIX}}` 占位符）：
```html
<div class="comparison-grid">
  <!-- 方案S1卡片 -->
  <div class="scheme-card recommended">
    <div class="scheme-card-header risk-low">  <!-- risk-low=绿色风险低 -->
      <span>S1 赔偿金2N仲裁</span>
      <span class="badge">推荐方案</span>
    </div>
    <div class="scheme-card-body">
      <table>
        <tr><td>法律依据</td><td>《劳动合同法》第87条（赔偿金2N）<br>构成要件全部满足</td></tr>
        <tr><td>胜诉把握</td><td><span style="color:#27AE60; font-weight:600;">把握较大</span><br>书面合同+工资流水+微信解除通知，3项核心证据齐全</td></tr>
        <tr><td>可获金额</td><td>
          <div class="amount-bar-wrap">
            <div class="amount-bar"><span>最佳</span><span class="bar-fill best" style="width:100%;"></span><span>48,000元</span></div>
            <div class="amount-bar"><span>一般</span><span class="bar-fill average" style="width:75%;"></span><span>36,000元</span></div>
            <div class="amount-bar"><span>最差</span><span class="bar-fill worst" style="width:50%;"></span><span>24,000元</span></div>
          </div>
        </td></tr>
        <tr><td>所需时间</td><td>一般4-6个月（仲裁45-60天+执行1-3个月）</td></tr>
        <tr><td>花费</td><td>约15,000-30,010元（律师费+时间成本）</td></tr>
      </table>
      <details style="margin-top:10px;"><summary>查看风险详情</summary>
        <div style="padding:10px; font-size:12px; color:#616161;">
          <p>🟡 举证风险（中）：解除理由争议，需准备微信记录等证据</p>
          <p>🟢 执行风险（低）：公司在正常经营，有财产可执行</p>
          <p>🟢 反诉风险（低）：本次争议不构成对方独立反请求</p>
        </div>
      </details>
    </div>
  </div>
  <!-- ... 其余方案卡片同结构 ... -->
</div>
```

**金额柱状图宽度计算规则**：
- 以所有方案中"最佳金额最大值"为100%基准
- 各方案的bar宽度 = 该方案金额 / 最大金额 × 100%

**风险色标映射**：
- `scheme-card-header` 的 class 按综合风险等级：`risk-high`(红)/`risk-medium`(琥珀)/`risk-low`(绿)
- 综合风险等级 = 六维风险中最高的那项（举证/执行/反诉/关系/声誉取max）

### 4.3 O2 律师版 HTML 生成步骤

**步骤1：以 O1 客户版 HTML 为基础**

**步骤2：人称回退**
- 全文替换："您"→"当事人"、"贵司"→"公司/企业方"
- 参考 [output-spec.md §2.1 对照表](../references/output-spec.md) 的逆向转换

**步骤3：恢复专业术语**
- 客户化表述回退为法律术语，如"双倍补偿金"→"赔偿金2N"

**步骤4：追加「七、内部标注」区块**
- 在 `</section>`（区块六 LIMITATION_WARNING 的封闭标签）之后、`<footer>` 之前插入
- 完整 HTML 骨架参考 [output-spec.md §3.1](../references/output-spec.md)

### 4.4 律师版内部标注中间产物示例

```json
internal_annotations = {
  "information_sufficiency": {
    "D1_dispute_facts": { "score": 85, "note": "基本事实清晰，解除理由需进一步核实" },
    "D2_evidence": { "score": 70, "note": "有合同+工资流水+微信记录，缺少书面解除通知" },
    "D3_limitation": { "score": 95, "note": "距1年仲裁时效到期还有345天，充裕" },
    "D4_party_identity": { "score": 90, "note": "劳动者身份/工龄/工资标准已确认" },
    "D5_counterparty": { "score": 60, "note": "公司基本情况已知，但财务细节/涉诉记录待补充" },
    "D6_claims": { "score": 85, "note": "诉求明确但底线金额未确认" },
    "total": 81
  },
  "confidence_matrix": {
    "S1_赔偿金2N仲裁": {
      "legal_basis": "高", "win_probability": "高", "expected_amount": "中",
      "time_cost": "高", "economic_cost": "高", "risks": "中"
    },
    "S2_恢复劳动关系": {
      "legal_basis": "高", "win_probability": "中", "expected_amount": "低",
      "time_cost": "中", "economic_cost": "中", "risks": "高"
    },
    "S3_协商和解": {
      "legal_basis": "中", "win_probability": "中", "expected_amount": "低",
      "time_cost": "高", "economic_cost": "高", "risks": "中"
    },
    "S4_仲裁监察并行": {
      "legal_basis": "中", "win_probability": "低", "expected_amount": "低",
      "time_cost": "中", "economic_cost": "中", "risks": "高"
    }
  },
  "assumptions": [
    "月工资8,000元为税前应发工资（含奖金/补贴需确认）",
    "公司口头通知解除符合'用人单位单方解除'构成要件",
    "公司经营状况正常（基于当事人描述，未查工商/企查查验证）",
    "无竞业限制/保密协议等特殊约束"
  ],
  "path_switch_triggers": [
    { "current": "S1", "trigger": "证据不足导致裁决不利", "switch_to": "S3", "deadline": "裁决前" },
    { "current": "S3", "trigger": "协商破裂（对方拒绝或金额过低）", "switch_to": "S1", "deadline": "仲裁时效内" }
  ],
  "downstream_skills": [
    { "recommended_path": "S1", "skill": "labor-arbitration-application", "reason": "仲裁申请书" },
    { "recommended_path": "S3", "skill": "settlement-agreement-draft", "reason": "和解协议" },
    { "recommended_path": "all", "skill": "labor-evidence-guide", "reason": "证据整理分析" },
    { "recommended_path": "all", "skill": "labor-limitation-analysis", "reason": "时效精确计算" }
  ],
  "risk_levels": {
    "phase3_overall": "L2",
    "phase3_win_probability_substep": "L3",
    "phase4_report_assembly": "L2",
    "overall": "L2"
  }
}
```

### 4.5 文件命名规则

| 版本 | 文件名格式 | 示例 |
|------|-----------|------|
| O1 客户版 | `[案件简称]-维权方案对比报告-客户版.html` | `张三违法解除-维权方案对比报告-客户版.html` |
| O2 律师版 | `[案件简称]-维权方案对比报告-律师版.html` | `张三违法解除-维权方案对比报告-律师版.html` |

---

## Phase 5: 合规红线检查 [L1]

逐条检查14条写作红线（同SKILL.md §4），发现违规立即修正。

---

## Phase 6: 质量检查 [L1]

对照 [../rules/quality-standards.md](../rules/quality-standards.md) 执行35+10+10项自检，法条须联网核实。
