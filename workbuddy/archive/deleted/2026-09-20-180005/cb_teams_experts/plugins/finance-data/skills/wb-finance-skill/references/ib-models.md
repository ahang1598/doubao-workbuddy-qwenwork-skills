# 投行估值建模（ib-models）

> **何时参考**：用户问"DCF 估值 / LBO 模型 / 可比公司分析 comps / 三表模型 / 并购模型 / WACC 怎么算 / 投行估值"。
>
> **输出形式**：本场景结论以 HTML 文件呈现（用 `Write` 工具落盘到当前工作目录，文件名形如 `<topic>-<YYYYMMDD>.html`），对话正文里附 200-300 字摘要 + 文件路径让用户自行打开。

## 核心目标

**搭建企业级估值模型**——多方法交叉验证，避免单一模型陷阱。

## 主要内容

### 1. 三表（财务报表）集成建模
- 收入 → 毛利 → EBITDA → EBIT → 税后净利
- 实际所得税率 15-25%
- 同时跟踪营运资本变化（应收 / 存货 / 应付）与自由现金流
- **FCF = EBIT × (1-tax) + D&A - CapEx - 营运资本变化**
- 三表相互勾稽，缺一不可

### 2. 可比公司分析（Comps）
- 选 5-10 家同行企业
- 计算 EV/EBITDA、EV/Revenue、P/E、P/B 倍数的中位数 + 四分位数
- 观察倍数与增长 / 盈利质量 / 风险的相关
- 对标的公司按增长 / 盈利率 / 风险调整后的倍数反推目标企业的合理估值
- 注意规模差异（大公司 vs 中小企业倍数差 3-5 倍）

### 3. DCF 核心参数
- **WACC = (E/(E+D))×Re + (D/(E+D))×Rd×(1-Tc)**
- **Re（权益成本）= Rf + β×(Rm - Rf)**
  - Rf 通常 3-4%（国债收益率）
  - Rm - Rf 通常 6-8%（历史市场风险溢价）
  - β 通常 0.8-1.2
- Rd（债务成本）依据信用等级 3-10%
- Tc（税率）实际 15-25%
- **WACC 通常 8-10%（制造业）到 15-20%（高风险创业）**
- **永续增长率 1.5-2.5%**（不超过 GDP 增速）

### 4. LBO（杠杆收购）模型
- 杠杆倍数（Debt/EBITDA）通常 3-5x 初始，最终降至 2-3x
- 债务成本：高于产业平均 100-200bp
- IRR 目标：25%-35%
- 构建 5-7 年的还债计划（debt paydown schedule）
- 计算 terminal value（最后一年企业价值），反推 entry & exit 的股权回报率

### 5. 单元经济学（Unit Economics）
- 适合消费 / SaaS 等模式清晰的企业
- 先做单个客户 / 产品的贡献，再通过增长假设推导整体盈利路径
- **LTV / CAC > 3 为健康模式**（SaaS 通常 > 5）
- 初期 < 1 需评估持续性

### 6. 并购模型（M&A）
- 在目标企业 DCF 基础上加入协同效应
- 收入协同（cross-selling / 市场扩展）通常 1-3 年兑现
- 成本协同（SG&A 削减 / 采购协议）较快（6-12 个月）
- 计算目标企业的 enterprise value，再减去 net debt → equity purchase price

### 7. 情景分析（Sensitivity）
- 构建悲观 / 基础 / 乐观三个情景
- 变化关键假设（收入增速 / 毛利率 / 税率 / WACC / 永续增长率）
- 表格呈现（行 = WACC 6%-14%、列 = 永续增长率 0.5%-3%）
- **一眼看出价值范围**

### 8. 融资与资本结构优化
- 融资方式改变会改变 tax shield 的价值（债务利息可税前抵扣）
- 杠杆增加可降低 WACC 但增加破产风险——找最优资本结构

## 建议骨架（不强制）

- 财务预测表（5-7 年收入 / EBITDA / 利润 / FCF）
- WACC 计算（Re / Rd / 权重 / 加权成本）
- DCF 估值（terminal value / 折现 / 企业价值）
- 可比公司对标表（倍数范围 / 对标选择理由 / 目标倍数判断）
- Sensitivity 分析表（WACC × 永续增长率矩阵）
- 并购协同评估（收入 / 成本协同 / 兑现时间 / 对价计算）

## 避坑

- 不要过度信任 DCF 的 terminal value——常占估值 50-70%，微小假设变化导致剧烈变化；多方法交叉验证
- Comps 倍数需调整不可比因素（增长率 / 风险 / 规模 / 会计政策）——直接用中位数倍数太机械
- WACC 中的 β 不稳定（行业周期 / 杠杆率变化都会改变）——定期更新；不同来源 β 差异 3-5%
- LBO 模型中协同效应常被高估——实际成本削减只有计划的 60-70%，收入协同更难（往往 0% 兑现）
- 并购整合失败率很高（特别是跨国并购）——sensitivity 中留 20-30% discount
- 初创企业 DCF 完全无用——用 VC 模式（target return × investment period 反推 entry valuation）

## 可执行工具

⚠️ **数据 skill 边界**：westock / neodata 提供 DCF / LBO 建模的**输入数据**（财务三表多期、行业可比 EV/EBITDA 倍数、Beta 等），但**模型搭建、Excel 公式校验、投行材料数字一致性检查这些算法/工程任务数据 skill 不做**——必须用 script。

| 文件 | 用途 | 额外依赖 |
|---|---|---|
| `scripts/ib/validate_dcf.py` | DCF Excel 模型自动校验（公式错误 / WACC 合理性 / 永续增长率边界 / terminal value 占比 / 敏感性分析完整性） | `pip install openpyxl` |
| `scripts/ib/extract_ib_numbers.py` | 投行材料数字提取与一致性校验（财务亮点 / 估值倍数 / 协同效应 / 时间线，自动检测前后矛盾） | — |

```bash
# 校验 DCF 模型（先 pip install openpyxl）
python3 scripts/ib/validate_dcf.py <path/to/model.xlsx>

# 检查投行材料数字一致性（纯文本/Markdown 输入，无需额外依赖）
python3 scripts/ib/extract_ib_numbers.py <path/to/material.txt>
```

**Setup**：`pip install openpyxl`（仅 validate_dcf 需要；extract_ib_numbers 是纯标准库实现）。

DCF / LBO 建模产出后**用上面工具自动审一遍**，避免手工漏检。
