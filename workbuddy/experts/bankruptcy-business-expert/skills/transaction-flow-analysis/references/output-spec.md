# 输出规格

## 目录

- [1. 输出模型概述](#1-输出模型概述)
- [2. HTML报告完整结构](#2-html报告完整结构)
- [3. 各区块详细规格](#3-各区块详细规格)
- [3.1 报告头区](#31-报告头区)
- [3.2 结论摘要区](#32-结论摘要区)
- [3.3 数据快照区](#33-数据快照区)
- [3.4 核心发现区](#34-核心发现区)
- [3.5 资金流向拓扑区](#35-资金流向拓扑区)
- [3.6 对手方分析区](#36-对手方分析区)
- [3.7 异常信号登记区](#37-异常信号登记区)
- [3.8 证据附件区](#38-证据附件区)
- [3.9 分析限制与敏感度区](#39-分析限制与敏感度区)
- [3.10 页脚与治理区](#310-页脚与治理区)
- [4. 发现撰写规范（v3.0 六要素）](#4-发现撰写规范v30-六要素)
- [5. 置信度与风险标注](#5-置信度与风险标注)
- [6. 案件类型核心发现撰写规范](#6-案件类型核心发现撰写规范)
- [7. 写作红线](#7-写作红线)
- [8. SOFT_DEGRADED降级变体](#8-soft_degraded降级变体)
- [9. 聚焦/简化报告变体](#9-聚焦简化报告变体)

---

## 1. 输出模型概述

### v3.0 核心变更（breaking change）

- **仅HTML输出**：移除O1 Markdown输出通道，所有报告统一为HTML格式（C-Professional级）
- **六要素发现模型**：核心发现从四要素（事实概括+数据支撑+法律意义+行动建议）升级为六要素（+对方可能抗辩+策略影响评分）
- **金字塔结论模型**：结论摘要从一段话升级为一句话核心结论+3条关键发现（impact-tagged）+策略级行动建议
- **对抗性思维内置**：每个核心发现必须包含对方可能抗辩及应对
- **策略影响分级**：每个发现附带 CRITICAL / SIGNIFICANT / NOTEWORTHY 影响标签
- **法条分析深化**：从"编号+要旨"升级为"编号+要旨+本案适用分析"

### 格式声明

```yaml
format_capabilities:
  default_output: "html"
  supported_formats:
    - id: "html"
      name: "HTML可视化分析报告"
      seriousness: "C-Professional"
      description: "顶级律所交付级，含结论摘要金字塔/六要素发现卡片/资金流向拓扑图/打印适配/页码/机密标记"
      is_default: true
  format_switching:
    method: "不再支持切换——仅HTML输出"
```

### HTML设计原则（v3.0）

1. **即视即用**——打开即专业级排版，无需额外调格式，可直接打印或导出PDF
2. **信息层级驱动**——6级标题尺度（28/22/18/16/14/13px）+ 4px基准间距网格
3. **配色即语义**——深海军蓝主色系 + 影响三级色（CRITICAL红/ SIGNIFICANT琥珀 / NOTEWORTHY蓝）
4. **对抗性可见**——每个发现卡片内置"对方可能抗辩"区，视觉上与事实叙事区分
5. **证据可追溯**——核心发现的数据支撑引用证据附件的具体行号范围
6. **打印即交付**——A4精确布局 + 分页控制 + 页眉页脚 + 自动页码

---

## 2. HTML报告完整结构

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>交易流水分析报告 — {case_type_name} — {report_date}</title>
  <!-- ⚠ LLM生成规范：CSS必须内联嵌入<style>标签，不能使用外部引用。以下href仅为设计参考，运行时不可用。 -->
  <!-- <link rel="stylesheet" href="templates/css/transaction-report-style.css"> -->
  <!-- ⚠ Mermaid CDN：生成时嵌入此CDN引用，但应同时添加离线降级提示（S9 分析限制区） -->
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
</head>
<body>

  <!-- ====== 第1页：执行概览 ====== -->

  <!-- S1 报告头 -->
  <header class="report-header">
    <div class="confidential-badge">CONFIDENTIAL · 律师工作底稿</div>
    <h1>交易流水分析报告</h1>
    <div class="header-meta">
      <span>案件类型：{case_type_name}</span>
      <span>分析日期：{date}</span>
      <span>报告编号：TFA-{YYYYMMDD}-{seq}</span>
    </div>
  </header>

  <!-- S2 结论摘要（金字塔模型） -->
  <section class="executive-summary">
    <h2>核心结论</h2>

    <div class="conclusion-headline">
      {一句话核心结论，30pt，结论即标题}
    </div>

    <div class="key-findings-brief">
      <div class="kf-item impact-critical">
        <span class="impact-tag">CRITICAL</span>
        <span>{关键发现1，≤2行}</span>
      </div>
      <div class="kf-item impact-significant">
        <span class="impact-tag">SIGNIFICANT</span>
        <span>{关键发现2，≤2行}</span>
      </div>
      <div class="kf-item impact-noteworthy">
        <span class="impact-tag">NOTEWORTHY</span>
        <span>{关键发现3，≤2行}</span>
      </div>
    </div>

    <div class="strategic-recommendation">
      <strong>策略建议：</strong>{1-2句行动级建议}
    </div>
  </section>

  <!-- S3 数据快照 -->
  <section class="data-snapshot">
    <div class="stat-cards">
      <div class="stat-card">
        <div class="stat-label">交易总笔数</div>
        <div class="stat-value">{count}</div>
      </div>
      <div class="stat-card inflow">
        <div class="stat-label">累计入账</div>
        <div class="stat-value">{total_income}</div>
      </div>
      <div class="stat-card outflow">
        <div class="stat-label">累计出账</div>
        <div class="stat-value">{total_expense}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">对手方数量</div>
        <div class="stat-value">{counterparty_count}</div>
      </div>
    </div>

    <div class="snapshot-meta-row">
      <div class="meta-item">
        <span class="meta-label">分析区间</span>
        <span class="meta-value">{date_range_start} — {date_range_end}</span>
      </div>
      <div class="meta-item">
        <span class="meta-label">数据来源</span>
        <span class="meta-value">{channels_list}</span>
      </div>
      <div class="meta-item">
        <span class="meta-label">风险等级</span>
        <span class="risk-badge risk-{risk_level}">{risk_level_label}</span>
      </div>
    </div>
  </section>

  <!-- ====== 第2页起：详细发现 ====== -->

  <!-- S4 核心发现（六要素） -->
  <section class="core-findings page-break-before">
    <h2>核心发现</h2>

    <!-- 发现1：CRITICAL -->
    <div class="finding-card impact-critical">
      <div class="finding-header">
        <span class="impact-badge">CRITICAL · 策略影响评分：高</span>
        <h3>{发现1标题 = 一句话法律结论}</h3>
      </div>

      <div class="finding-body">
        <!-- 要素1：事实概括 -->
        <div class="finding-narrative">
          <h4>事实叙事</h4>
          <p>{3-5句事实概括，按时间或逻辑顺序，含关键时间节点}</p>
        </div>

        <!-- 要素2：数据锚点 -->
        <div class="finding-data-points">
          <h4>数据锚点</h4>
          <div class="data-points-grid">
            <div class="dp-item">
              <span class="dp-value">{amount}</span>
              <span class="dp-label">涉及金额</span>
            </div>
            <div class="dp-item">
              <span class="dp-value">{count}</span>
              <span class="dp-label">涉及笔数</span>
            </div>
            <div class="dp-item">
              <span class="dp-value">{date_range}</span>
              <span class="dp-label">时间窗口</span>
            </div>
          </div>
          <p class="evidence-ref">📎 证据锚点：附1 第{row_start}-{row_end}行 / 附3 第{a_row}行</p>
        </div>

        <!-- 要素3：法律分析 -->
        <div class="finding-legal">
          <h4>法律分析</h4>
          <div class="legal-citation">
            <span class="law-ref">《{法律名称}》第{X}条</span>
            <span class="law-gist">条文要旨：{要旨}</span>
          </div>
          <div class="legal-application">
            <strong>本案适用：</strong>{条文如何适用于本案具体事实，2-3句分析}
          </div>
        </div>

        <!-- 要素4：对方可能抗辩（v3.0新增） -->
        <div class="finding-counter">
          <h4>对方可能抗辩</h4>
          <p>{对方可能提出的反驳论点}</p>
          <p class="counter-response"><strong>应对：</strong>{1-2句反驳策略}</p>
        </div>

        <!-- 要素5：策略影响评分（v3.0新增） -->
        <div class="finding-impact-assessment">
          <h4>策略影响评估</h4>
          <table class="impact-table">
            <tr><td>对诉讼请求的影响</td><td>{描述}</td></tr>
            <tr><td>对举证责任的影响</td><td>{描述}</td></tr>
            <tr><td>对和解谈判的影响</td><td>{描述}</td></tr>
          </table>
        </div>

        <!-- 要素6：诉讼策略建议 -->
        <div class="finding-action">
          <h4>诉讼策略建议</h4>
          <p>{操作级建议，含具体法院/文书类型/调取对象/时间窗口}</p>
        </div>
      </div>
    </div>

    <!-- 发现2：SIGNIFICANT -->
    <div class="finding-card impact-significant">
      <!-- 同上结构，impact-badge 为 SIGNIFICANT -->
    </div>

    <!-- 发现3+：NOTEWORTHY -->
    <div class="finding-card impact-noteworthy">
      <!-- 同上结构 -->
    </div>
  </section>

  <!-- S5 资金流向拓扑 -->
  <section class="flow-topology page-break-before">
    <h2>资金流向拓扑</h2>
    <div class="flow-diagram-container">
      <div class="mermaid">
        {mermaid_code}
      </div>
    </div>
    <div class="flow-analysis">
      <h4>流向分析</h4>
      <ul>
        <li><strong>主要流入来源：</strong>{分析}</li>
        <li><strong>主要流出方向：</strong>{分析}</li>
        <li><strong>资金闭环检测：</strong>{是否存在A→B→C→A回路}</li>
        <li><strong>净流量特征：</strong>{分析}</li>
      </ul>
    </div>
  </section>

  <!-- S6 对手方分析 -->
  <section class="counterparty-analysis">
    <h2>对手方分析</h2>
    <table class="counterparty-table">
      <thead>
        <tr>
          <th style="width:18%">对手方</th>
          <th style="width:8%">笔数</th>
          <th style="width:14%">累计金额</th>
          <th style="width:12%">关系推断</th>
          <th style="width:12%">推断依据</th>
          <th style="width:8%">置信度</th>
          <th style="width:12%">风险信号</th>
          <th style="width:16%">关联发现</th>
        </tr>
      </thead>
      <tbody>
        <tr class="risk-row-high">
          <td>{name}</td>
          <td>{count}</td>
          <td class="amount">{amount}</td>
          <td>{relationship}</td>
          <td>{basis}</td>
          <td><span class="confidence confidence-{level}">{level_label}</span></td>
          <td><span class="risk-signal risk-{severity}">{signal}</span></td>
          <td><a href="#finding-1">发现1</a></td>
        </tr>
      </tbody>
    </table>
  </section>

  <!-- S7 异常信号登记 -->
  <section class="anomaly-register">
    <h2>异常信号登记</h2>
    <table class="anomaly-table">
      <thead>
        <tr>
          <th style="width:5%">#</th>
          <th style="width:14%">异常类型</th>
          <th style="width:10%">严重程度</th>
          <th style="width:18%">涉及交易</th>
          <th style="width:15%">触发规则</th>
          <th style="width:22%">法律含义</th>
          <th style="width:16%">核实建议</th>
        </tr>
      </thead>
      <tbody>
        <tr class="anomaly-severity-critical">
          <td>1</td>
          <td>{type}</td>
          <td><span class="severity-badge severity-l3">L3 严重</span></td>
          <td>#{tx_ids}</td>
          <td>{rule}</td>
          <td>{legal_implication}</td>
          <td>{verification_action}</td>
        </tr>
      </tbody>
    </table>
  </section>

  <!-- S8 证据附件 -->
  <section class="evidence-appendix page-break-before">
    <h2>证据附件</h2>

    <details class="appendix-section" open>
      <summary>附1 逐笔交易分类明细表（{total_count}笔）</summary>
      <div class="table-container">
        <table class="evidence-table">
          <thead>
            <tr>
              <th style="width:4%">#</th>
              <th style="width:10%">日期</th>
              <th style="width:8%">渠道</th>
              <th style="width:6%">方向</th>
              <th style="width:11%">金额(元)</th>
              <th style="width:12%">对手方</th>
              <th style="width:14%">备注</th>
              <th style="width:12%">分类标签</th>
              <th style="width:10%">法律要件</th>
              <th style="width:7%">置信度</th>
              <th style="width:6%">关联</th>
            </tr>
          </thead>
          <tbody>
            <tr class="tx-row-{confidence}">
              <td class="row-num">{n}</td>
              <td>{date}</td>
              <td>{channel}</td>
              <td class="direction-{in_out}">{direction}</td>
              <td class="amount">{amount}</td>
              <td>{counterparty}</td>
              <td class="remark">{remark}</td>
              <td><span class="tag tag-{category}">{label}</span></td>
              <td class="legal-element">{legal_element}</td>
              <td><span class="confidence confidence-{level}">{level_label}</span></td>
              <td><a href="#finding-{n}">F{n}</a></td>
            </tr>
          </tbody>
        </table>
      </div>
    </details>

    <details class="appendix-section">
      <summary>附2 对手方排行表</summary>
      <!-- 表格同 S6 -->
    </details>

    <details class="appendix-section">
      <summary>附3 异常信号明细表</summary>
      <!-- 表格同 S7 -->
    </details>
  </section>

  <!-- S9 分析限制与敏感度 -->
  <section class="limitations page-break-before">
    <h2>分析限制与敏感度评估</h2>

    <div class="data-completeness">
      <h3>数据完整性</h3>
      <div class="completeness-bar">
        <div class="bar-fill" style="width:{completeness_pct}%"></div>
        <span class="bar-label">{completeness_pct}%</span>
      </div>
      <ul class="missing-items">
        <li>{缺失信息1}</li>
        <li>{缺失信息2}</li>
      </ul>
    </div>

    <div class="key-assumptions">
      <h3>关键假设</h3>
      <ol>
        <li>{假设1} — 若此假设不成立，则{影响分析}</li>
        <li>{假设2} — 若此假设不成立，则{影响分析}</li>
      </ol>
    </div>

    <div class="sensitivity">
      <h3>敏感度分析</h3>
      <p>{如果XX信息被证明错误，以下发现将受影响：发现1的金额认定需下调至区间，发现2的分类结论需重新评估...}</p>
    </div>

    <div class="lawyer-review-checklist">
      <h3>律师复核清单</h3>
      <table class="checklist-table">
        <tr><td><input type="checkbox"> 结论摘要中的金额认定是否准确</td></tr>
        <tr><td><input type="checkbox"> 核心发现的分类标签是否与案件策略一致</td></tr>
        <tr><td><input type="checkbox"> 异常信号是否已全部核实</td></tr>
        <tr><td><input type="checkbox"> 法条引用是否现行有效</td></tr>
        <tr><td><input type="checkbox"> 对方可能抗辩是否充分覆盖</td></tr>
        <tr><td><input type="checkbox"> 证据附件中的交易记录是否完整无误</td></tr>
      </table>
    </div>
  </section>

  <!-- S10 页脚与治理 -->
  <footer class="report-footer">
    <div class="disclaimer">
      <strong>⚠ 免责声明</strong><br>
      本交易流水分析报告由AI辅助生成，<strong>不构成审计意见、鉴定结论或法律意见</strong>。
      律师应结合案件整体情况独立判断，关键金额认定需主办律师核实。
      本报告为律师工作底稿（中间产品），非法院提交物。
    </div>
    <div class="footer-meta">
      <span>报告编号：TFA-{YYYYMMDD}-{seq}</span>
      <span>生成时间：{timestamp}</span>
      <span>数据置信度：{confidence_level}</span>
    </div>
  </footer>

</body>
</html>
```

---

## 3. 各区块详细规格

### 3.1 报告头区

| 元素 | 规格 |
|------|------|
| 机密标记 | 顶部居中，`CONFIDENTIAL · 律师工作底稿`，红色文字+浅红底 |
| 主标题 | "交易流水分析报告"，28px，居中，深海军蓝 |
| 元数据行 | 案件类型 / 分析日期 / 报告编号，13px灰色，居中 |

### 3.2 结论摘要区

| 元素 | 规格 |
|------|------|
| 核心结论标题 | 22px，全宽，底部3px双色底线 |
| 结论正文 | 18px，加粗，一行原则（可延伸至两行），深海军蓝。必须是对案件走向有直接影响的结论性表述。示例格式："当事人在起诉前4个月内通过3个账户向关联方集中转出约86万元，该行为模式高度符合民法典第1092条转移夫妻共同财产特征，可主张少分或不分" |
| 关键发现简要 | 3条，每条≤2行，impact-tagged（红/琥珀/蓝）。格式：`[标签] 一句话结论` |
| 策略建议 | 1-2句操作级建议。14px，左侧竖线强调 |

### 3.3 数据快照区

| 元素 | 规格 |
|------|------|
| 4个统计卡片 | 等宽网格，交易总笔数（深海军蓝）/ 累计入账（绿色）/ 累计出账（红色）/ 对手方数量（深海军蓝）。卡片含label(12px灰色) + value(24px加粗) |
| 元数据行 | 分析区间 / 数据来源渠道 / 风险等级标签，13px |

### 3.4 核心发现区

**六要素发现卡片规范**：

| 要素 | CSS Class | 必含内容 | 禁止 |
|------|-----------|----------|------|
| 事实叙事 | `finding-narrative` | 3-5句日常生活语言，含时间/人物/金额/行为链条 | 堆砌数字，贴分类表 |
| 数据锚点 | `finding-data-points` | 3个数字卡片（涉及金额/笔数/时间窗口）+ 证据表行号引用 | 仅"详见附件"无具体行号 |
| 法律分析 | `finding-legal` | 法条编号+条文要旨+本案适用分析（2-3句） | 仅列法条编号无适用分析 |
| 对方可能抗辩 | `finding-counter` | 对方可能提出的反驳+应对策略 | 只写"对方可能抗辩"无应对 |
| 策略影响评估 | `finding-impact-assessment` | 3行表格（对诉讼请求/举证责任/和解谈判的影响） | 笼统写"有利于己方" |
| 诉讼策略建议 | `finding-action` | 操作级建议（含具体法院/文书类型/调取对象/时间窗口） | "建议进一步调查"等模糊表述 |

**影响标签视觉**：
- `CRITICAL`：左侧5px红色竖线 + 红色标签 + 浅红顶条
- `SIGNIFICANT`：左侧5px琥珀色竖线 + 琥珀色标签 + 浅琥珀顶条
- `NOTEWORTHY`：左侧5px蓝色竖线 + 蓝色标签 + 浅蓝顶条

### 3.5 资金流向拓扑区

| 元素 | 规格 |
|------|------|
| Mermaid图 | 居中，浅灰底卡片内，`graph LR` 方向 |
| 流向分析 | 4条项目符号列表（主要流入/主要流出/闭环检测/净流量特征） |

### 3.6 对手方分析区

8列表格（对手方/笔数/累计金额/关系推断/推断依据/置信度/风险信号/关联发现）。高风险行背景浅红。

### 3.7 异常信号登记区

7列表格（#/异常类型/严重程度/涉及交易/触发规则/法律含义/核实建议）。严重程度分L1/L2/L3。

### 3.8 证据附件区

3个 `<details>` 折叠区：
- **附1** 逐笔交易分类明细表（11列，默认展开）
- **附2** 对手方排行表（默认折叠）
- **附3** 异常信号明细表（默认折叠）

每条交易行含"关联发现"列，可直接跳转到对应的核心发现卡片。

### 3.9 分析限制与敏感度区

4个子区块：
1. **数据完整性**：进度条可视化 + 缺失项清单
2. **关键假设**：编号列表，每条含"若假设不成立则…"影响分析
3. **敏感度分析**：段落说明关键疑点的连锁影响
4. **律师复核清单**：6项checkbox清单

### 3.10 页脚与治理区

| 元素 | 规格 |
|------|------|
| 免责声明 | 黄色警告卡片，强调"不构成审计/鉴定/法律意见" |
| 元数据 | 报告编号 / 生成时间 / 数据置信度，灰色12px |

---

## 4. 核心发现撰写规范（v3.0 六要素）

每个核心发现必须包含以下六个要素，缺一不可：

| # | 要素 | 位置 | 要求 | 禁止 |
|---|------|------|------|------|
| 1 | **事实叙事** | 首段 | 3-5句，日常生活语言，含时间/人物/金额/行为链条。叙事驱动，非数据驱动 | 堆砌数字、贴分类汇总表、超5句 |
| 2 | **数据锚点** | 叙事之后 | 3个关键数字（涉及金额/笔数/时间窗口）+ 证据附件行号引用。数字须可复核 | 仅"详见附件"无具体行号、"大量""多次"等模糊表述 |
| 3 | **法律分析** | 数据锚点之后 | 法条编号+条文要旨（一句话）+ 本案适用分析（2-3句：为何该条文适用于本案事实，引用事实叙事中的关键点） | 仅列法条无适用分析、编造法条、给予"必然构成XXX"等确定性判断 |
| 4 | **对方可能抗辩** | 法律分析之后 | 站在对方视角提出1-2个可能的反驳论点+应对策略。必须写具体论点，不是"对方可能不认可" | 空泛写"对方可能提出异议"、只写抗辩无应对 |
| 5 | **策略影响评估** | 抗辩之后 | 3行表格：对诉讼请求/举证责任/和解谈判的具体影响。每项≤2句，直指要害 | 笼统写"有利于己方"、虚构影响 |
| 6 | **诉讼策略建议** | 末段 | 操作级建议：含具体法院名称/文书类型（如调查令申请书）/调取对象（含账号）/时间窗口。行为动词开头 | "建议进一步调查""需注意""可能涉及"等无操作指引的表述 |

### 撰写铁律（v3.0 强化）

1. ❌ 禁止把分类汇总表直接贴入核心发现
2. ❌ 禁止核心发现不含法条编号和本案适用分析
3. ❌ 禁止遗漏对方可能抗辩及应对
4. ❌ 禁止行动建议不含操作级细节
5. ❌ 禁止事实叙事超过5句话
6. ❌ 禁止把多个不相关的发现合并为一个
7. ❌ 禁止使用"综上所述""总体而言"等无信息量开头
8. ❌ 禁止策略影响评估笼统化
9. ❌ 禁止证据锚点无具体行号
10. ❌ 禁止遗漏影响标签（每个发现必须有CRITICAL/SIGNIFICANT/NOTEWORTHY之一）

---

## 5. 置信度与风险标注

### 数据置信度（输入层）

| 等级 | CSS Class | 触发场景 | 色彩 |
|------|-----------|----------|------|
| 高 | `confidence-high` | IM1结构化输入 | 绿色 #1E8449 |
| 中 | `confidence-medium` | IM2半结构化输入 | 琥珀色 #B9770E |
| 低 | `confidence-low` | IM3自然语言输入 | 红色 #922B21 |

### 分类置信度（分析层）

| 等级 | CSS Class | 触发场景 | 证据表行样式 |
|------|-----------|----------|-------------|
| 高 | `confidence-high` | 备注明确+交易模式匹配 | 正常行 |
| 中 | `confidence-medium` | 备注模糊或多解释 | 浅琥珀背景 |
| 低 | `confidence-low` | 无备注+模式不典型 | 浅红背景 |

### 风险等级

| 等级 | CSS Class | 含义 | 视觉 |
|------|-----------|------|------|
| L1 | `risk-l1` | 辅助参考 | 绿色标签 |
| L2 | `risk-l2` | 专业底稿 | 琥珀色标签 |
| L3 | `risk-l3` | 高敏感 | 红色标签 |

### 影响等级（v3.0新增）

| 等级 | CSS Class | 含义 | 视觉 |
|------|-----------|------|------|
| CRITICAL | `impact-critical` | 直接影响诉讼成败 | 左侧5px红竖线 + 红色标签 + 浅红顶条 |
| SIGNIFICANT | `impact-significant` | 显著影响策略选择 | 左侧5px琥珀竖线 + 琥珀色标签 |
| NOTEWORTHY | `impact-noteworthy` | 值得关注但不直接决定胜负 | 左侧5px蓝竖线 + 蓝色标签 |

---

## 6. 案件类型核心发现撰写规范

> **分工边界说明**：本节定义各案型在报告中呈现的"核心发现"撰写方向与叙事框架——回答"这个案型下律师最关心什么、报告应该怎么讲故事"。`templates/case-types/` 下的 CaseTypeSpec 文件定义各案型的分类标签体系、异常检测规则、置信度阈值——回答"这个案型下如何逐笔分类、如何判定异常"。二者分工：**§6 = 报告叙事层（写什么）**，**CaseTypeSpec = 分析引擎层（怎么算）**。生成报告时本节指导叙事，CaseTypeSpec 驱动分析，不可互相替代。

以下定义每种案件类型在"核心发现"段落中最可能出现的3-5个**典型发现方向**及撰写指引。注意：这些是方向指引，不是模板填空——实际生成时必须基于具体的交易数据，且每个发现须包含六要素（v3.0）。

### CT1 婚姻家事

| # | 典型发现方向 | 核心叙事 | 法条引用 | 对方可能抗辩 | 行动建议 |
|---|-------------|----------|----------|-------------|----------|
| 1 | 异常转移行为 | 起诉前N个月内向特定关系人转出X元，均为整数大额，同期日常消费未见异常 | 民法典第1092条（转移夫妻共同财产可少分或不分） | "正常家庭支出/赠与/归还借款" | 申请法院调取关联方账户流水追查资金去向 |
| 2 | 关联方交易分析 | 与{父母/兄弟姐妹/新配偶}共X笔累计Y元，集中在{时间段} | 民法典第1062-1063条（共同/个人财产范围） | "父母代持/子女教育/家庭共同决定" | 核实交易性质是否为赠与/借贷/代持 |
| 3 | 取现后去向不明 | 取现X笔累计Y元，后续流水无对应大额消费记录 | 民法典第1092条 | "日常现金消费" | 需当事人说明资金用途或提供消费凭证 |
| 4 | 共同财产支出合理性 | 共同财产支出X笔Y元，占比Z%，是否与家庭正常消费水平匹配 | 民法典第1062条 | "家庭正常开支" | 对比家庭收入水平和当地物价水平 |

### CT2 劳动争议

| # | 典型发现方向 | 核心叙事 | 法条引用 | 对方可能抗辩 | 行动建议 |
|---|-------------|----------|----------|-------------|----------|
| 1 | 工资断发/降档 | {入职后/离职前}连续N个月工资{断发/降档}，累计欠付X元 | 劳动法第50条（按月足额支付） | "绩效未达标/业务调整/已协商一致" | 主张拖欠工资+经济补偿金（劳动合同法第85条） |
| 2 | 非工资收入冒充 | 备注"劳务费"的入账共X笔Y元，发放规律与工资一致 | 劳动合同法第7条（用工之日起建立劳动关系） | "独立劳务关系/兼职" | 举证证明实质为工资，而非劳务报酬 |
| 3 | 加班费未付 | 非工作日入账X笔Y元，明显低于约定加班费标准 | 劳动法第44条（加班费计算标准） | "已调休/未加班" | 核算应发加班费与实际发放的差额 |
| 4 | 低于最低工资 | 某月工资X元低于当地最低工资标准Y元 | 劳动法第48条（最低工资保障） | "扣除社保后" | 主张补足差额 |

### CT3 民间借贷

| # | 典型发现方向 | 核心叙事 | 法条引用 | 对方可能抗辩 | 行动建议 |
|---|-------------|----------|----------|-------------|----------|
| 1 | 本息拆分结果 | 出借本金X元，累计还款Y元，其中认定利息Z元，尚欠本金A元+利息B元 | 民法典第561条（先息后本冲抵顺序） | "已全部还清/还款性质不同" | 作为诉讼请求金额的计算依据，需律师最终确认 |
| 2 | 利率推算与合规 | 推算年化利率X%，同期LPR4倍为Y%。{合规/超出} | 民间借贷司法解释第25条（LPR4倍上限） | "自愿约定/已变更利率" | 超出LPR4倍部分作为超额利息抗辩 |
| 3 | 砍头息识别 | 借款当日/次日即转回X元，应从本金扣除 | 民法典第670条（借款利息不得预先扣除） | "手续费/居间费" | 本金应以实际交付金额为准 |
| 4 | 部分还款冲抵 | 多笔还款累计X元，按先息后本顺序冲抵 | 民法典第561条 | "先还本金" | 制作还款冲抵明细表作为证据 |

### CT4 合同纠纷

| # | 典型发现方向 | 核心叙事 | 法条引用 | 对方可能抗辩 | 行动建议 |
|---|-------------|----------|----------|-------------|----------|
| 1 | 履约验证结果 | 约定N个付款节点中，M个按期、K个逾期、J个未付 | 民法典第509条（全面履行） | "付款条件未成就/质量异议" | 计算逾期天数+逾期金额作为违约赔偿计算依据 |
| 2 | 逾期违约金计算 | N笔逾期合计Y天，逾期金额Z元 | 民法典第585条（违约金） | "违约金过高请求调减" | 按约定违约金条款计算，并注明法院可能调减 |
| 3 | 部分付款法律效果 | N笔部分付款，差额合计X元，不免除剩余付款义务 | 民法典第577条（违约责任） | "已部分履行" | 主张继续履行+逾期赔偿 |
| 4 | 付款进度对比 | 约定应付款X元，实际付款Y元，进度差距Z% | 民法典第490条（事实合同） | "无书面合同不成立" | 若无书面合同，主张事实合同成立 |

### CT5 刑事辩护

> ⚠️ C类高风险：以下均为初步分析，**所有金额认证必须标注"需律师结合案情确认"**，禁止给出确定性金额认定。

| # | 典型发现方向 | 核心叙事 | 法条引用 | 对方可能抗辩 | 行动建议 |
|---|-------------|----------|----------|-------------|----------|
| 1 | 涉案金额区间 | 从交易记录推算涉案金额为X-Y元区间，与指控金额Z元{一致/差异N%} | 刑法第64条（违法所得追缴） | "与案件无关/合法收入" | 差异>20%时需核实指控金额的计算依据 |
| 2 | 资金回流路径 | 当事人→A→B→当事人的回流路径，涉及X元 | 刑法第191条（洗钱罪）/第312条（掩饰隐瞒犯罪所得） | "正常业务周转" | 需律师判断是否影响定性 |
| 3 | 主观明知推定依据 | 基于交易模式的N个可推定明知的行为特征 | 案件涉及的罪名条文 | "不知情/被蒙蔽" | 仅为辅助分析，不替代证据——需律师最终判断 |
| 4 | 资金多层追踪 | N层资金追踪结果，资金最终去向 | — | "资金用途合法" | 建议向侦查机关申请进一步追踪 |

### CT6 执行追索

| # | 典型发现方向 | 核心叙事 | 法条引用 | 对方可能抗辩 | 行动建议 |
|---|-------------|----------|----------|-------------|----------|
| 1 | 消费与财产申报矛盾 | 月均消费X元，超出执行依据金额Y元的Z%，与财产申报表矛盾 | 民诉法第248条（被执行人财产报告义务） | "基本生活需要" | 提交法院作为拒不申报/虚假申报的证据 |
| 2 | 财产线索发现 | 发现N条财产线索：房产（月供X元）/车辆（保险Y元）/投资（定投Z元） | 民诉法第249条（执行措施） | "非本人财产/已处置" | 申请法院对该财产线索进行调查核实 |
| 3 | 收入能力评估 | 月均收入X元，年还款能力Y元 | — | "收入不稳定" | 评估分期履行可行性，作为执行和解谈判依据 |
| 4 | 执行后财产转移 | 执行立案后向特定关系人转出X笔Y元 | 民诉法第248条 | "正常消费/归还借款" | 可能构成拒不执行判决裁定罪线索 |

---

## 7. 写作红线

1. ❌ 编造交易记录或推断不存在的交易
2. ❌ 对交易性质作出确定性法律判断（使用"可能构成""疑似""高度吻合"等限定词）
3. ❌ 声称分析结果可替代审计意见或鉴定结论
4. ❌ 基于备注推断的分类不标注置信度
5. ❌ 遗漏异常信号的标注
6. ❌ 在法律依据不确定时不标注需核实
7. ❌ 将跨渠道的重复交易重复计入统计
8. ❌ 金额汇总不列出计算过程
9. ❌ 核心发现不含法条编号+条文要旨+本案适用分析
10. ❌ 核心发现只是一张分类表（必须为法律叙事+法条+行动建议六要素）
11. ❌ 结论摘要超过200字（核心结论一行+3条关键发现+策略建议，总计不超过120字正文内容）
12. ❌ 行动建议模糊或超出律师职权范围
13. ❌ C类案件（CT5）给出确定性金额认定
14. ❌ 将银行记账方向直接作为用户视角方向
15. ❌ **v3.0** 核心发现遗漏对方可能抗辩及应对
16. ❌ **v3.0** 核心发现遗漏策略影响评估表
17. ❌ **v3.0** 核心发现无影响标签（CRITICAL/SIGNIFICANT/NOTEWORTHY）
18. ❌ **v3.0** 证据锚点无具体行号引用

---

## 8. SOFT_DEGRADED降级变体

降级时报告仍为HTML格式，但结构精简：

### S1降级（<3笔有效交易）

HTML结构简化为：
```html
<body class="degraded-s1">
  <header class="report-header"><!-- 同标准 --></header>
  <section class="degraded-core">
    <h2>降级分析（数据不足）</h2>
    <div class="degraded-notice">{降级原因说明}</div>
    <table class="evidence-table"><!-- 已识别交易 --></table>
  </section>
  <section class="degraded-guidance">
    <h3>待补充信息</h3>
    <ul><li>...</li></ul>
    <h3>建议行动</h3>
    <p>...</p>
  </section>
  <footer><!-- 免责声明 + 强烈建议补充数据 --></footer>
</body>
```

### S3降级（部分交易无法分类）

接近完整HTML，但以下区块标注"待核实"：
- 结论摘要增加"⚠ 以下结论基于可识别交易，部分交易待补充信息"
- 核心发现中金额/分类用区间表述
- 证据附件中待定交易行标注红色背景

---

## 9. 聚焦/简化报告变体

### 聚焦报告（I1指定方向）

HTML结构不变，但核心发现区仅含选定方向的发现，其他区块正常输出。

### 简化报告（I1只看概览）

HTML简化为：
```html
<body class="simplified">
  <!-- S2 结论摘要 → S3 数据快照 → S8 证据附件（仅附1） → S9 分析限制 → S10 页脚 -->
  <!-- 无 S4/S5/S6/S7 -->
</body>
```
