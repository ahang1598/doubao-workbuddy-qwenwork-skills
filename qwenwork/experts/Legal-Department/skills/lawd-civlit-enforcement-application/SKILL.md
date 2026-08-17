---
name: 强制执行申请书
name_en: lawd-civlit-enforcement-application
displayName: 强制执行申请书
description_en: "Compulsory enforcement application generator. From an effective legal instrument, property clues, and required attachments, it auto-calculates the enforcement amount (including double interest for delayed performance), classifies property clues, and generates a full document set of compulsory enforcement application, property preservation application, and calculation schedule. Triggered when users mention applying for compulsory enforcement, filing enforcement with the court, or calculating delayed-performance interest; supports six enforcement bases (judgments, rulings, mediation statements, arbitral awards, notarized debt documents, payment orders) and delivers a complete Word document set plus Markdown preview."
argument-hint: 生效判决书与执行线索
description: '强制执行申请书生成专家。根据生效法律文书+财产线索+必要附件，自动计算执行标的（含迟延履行利息），智能分类财产线索，生成强制执行申请书+财产保全申请书+计算明细表全套文书。支持六类执行依据：判决书、裁定书、调解书、仲裁裁决书、公证债权文书、支付令。TRIGGER when: (1) 用户提及"强制执行""执行申请""申请执行""执行立案""申请法院执行""强执"等，(2) 用户持有生效法律文书需要申请强制执行，(3) 用户需要计算迟延履行利息/加倍利息，(4) 用户需要整理财产线索申请执行。input/ 含 PDF/扫描件时须先或并行完成材料文字化（读 input/_text/；材料解析为独立技能，未安装时请用户先提供可读文本）。输出：Word 全套文书 + Markdown 预览版。NOT for: 追加/变更被执行人（后续单独技能）、执行异议/复议（后续单独技能）、起诉状/答辩状、代理词（代理词生成）、律师函（律师函撰写）、对内分析报告（案情法律分析报告）。'
---

# 强制执行申请书生成（全类型执行依据）

以**20 年资深执行律师**的水准，基于生效法律文书 + 财产线索材料，**自动计算执行标的、分类财产线索、生成可提交的全套文书**。

---

## 不适用场景

| 场景 | 应使用的技能 |
|------|-------------|
| 追加/变更被执行人 | 后续单独技能 |
| 执行异议/执行复议 | 后续单独技能 |
| 代理词/仲裁代理意见 | `代理词生成` |
| 律师函/催告函 | `律师函撰写` |
| 起诉状/答辩状/上诉状 | 独立起草或人工 |
| 对内法律分析报告 | `案情法律分析报告` |

---

## 执行依据路由（必须先判定）

启动后首先识别执行依据类型，确定管辖法院和附件要求。详见 [references/basis-routing.md](references/basis-routing.md)。

| 依据类型 | 管辖法院 | 附件要求 |
|----------|----------|----------|
| 法院判决书 | 一审法院 | 生效证明 |
| 法院裁定书 | 一审法院 | 生效证明 |
| 法院调解书 | 一审法院 | 无需生效证明 |
| 仲裁裁决书 | 被执行人住所地/财产所在地中院 | 裁决书 + 送达证明 |
| 公证债权文书 | 被执行人住所地/财产所在地法院 | 执行证书 + 公证书 |
| 支付令 | 签发法院 | 生效证明 |

---

## 输入信息收集

启动前按 [references/intake-checklist.md](references/intake-checklist.md) 核对材料。达到**最低启动条件**方可进入完整四阶段。

### 材料文字化（`input/` 含 PDF/扫描件时建议先做）

若材料在 `<workspace>/input/` 且含 **PDF、扫描图片、OFD 或版式复杂的 Office 附件**，在阶段一审阅**之前**应完成材料文字化（材料解析技能，独立安装；或请用户提供可读文本）：

1. 产物落在 `input/_text/`（与源文件同相对路径的 `.md` + `.json`）
2. 本技能审阅时**优先 Read** 对应 `_text/*.md`
3. 若 `_text/` 不存在或明显落后于 `input/` 中新 PDF → 触发材料解析技能（独立技能；未安装时请用户上传可读文本或自行转文本）
4. **兜底降级（材料解析技能与用户可读文本均不可得时）**：用 pymupdf(fitz) 检测每页文字层，无文字页渲染 2x 图片后 Read 视觉读取（>20 页分批、可子代理并行），将识别文本按页写入 `input/_text/`；产物质量按"降级读取（OCR/视觉识别）"标注，关键金额/日期须与用户核对

⛔ 禁止对扫描件 PDF 仅用内置 Read 硬读二进制。

### 最低启动条件

**启动检查（进入四阶段前必须逐项执行，任一不满足即走「材料不足时的交付规范」）**：

| # | 检查项 | 不满足时 |
|---|--------|----------|
| 1 | 执行依据类型已判定（六类之一） | 输出缺口清单 → 停止 |
| 2 | 主文书至少一份，且含**完整判项/主文**（给付金额、履行期限等可提取） | 输出缺口清单 → 停止 |
| 3 | 申请执行人基本信息齐备（名称 + 身份标识） | 输出缺口清单 → 停止 |

检查结果须在对话中显式输出（逐项 ✅/❌）。**禁止在检查未通过时凭假设数据进入文书生成**（含"用户要求直接生成"的情形——此时按约束原则第 7 条假设场景模式处理，仍须先出口径说明）。

### 材料不足时的交付规范（强制）

未达最低启动条件时：
1. 输出**材料缺口清单**（按 [references/material-gap-checklist.md](references/material-gap-checklist.md) 模板）
2. **不生成** Word 文书、不编造信息

---

## 约束原则

### 1. 事实锚定
所有事实陈述必须来源于执行依据原文。金额数字必须与判决主文严格一致，不得编造或夸大。

### 2. 计算可复核
标的计算过程完整展示在明细表中，每一步均可人工验算。利率、天数、本金拆分透明呈现。

### 3. 法条引用准确
引用的诉讼法/仲裁法条文必须为现行有效版本。迟延履行利息的法律依据为民诉法第264条及法释〔2014〕8号。

### 4. 时效警示
自动核算申请执行时效（生效后2年内，民诉法第250条）。距到期≤30天或已超期时醒目警告。

### 5. 严禁编造
禁止编造法条、司法解释、财产线索信息。不确定的信息标注"待律师确认"。

### 6. 动态规则默认核验
涉及具体法条编号、利率数值、时效期间等内容，均应作为**待核验规则**处理。未完成核验时不得在正文中写死结论。

### 7. 假设场景模式（用户明确要求时启用）

**触发条件**：用户明确表示"假设胜诉""模拟生成""先出个模板"等，即无真实生效法律文书而要求基于假设判项生成。

**硬约束**（任一违反等同编造，按约束原则 1/5 论处）：
1. 文书封面与预览文首显著标注"**【假设场景·非正式文书】**"；
2. 所有非来源于真实文书的数据（判项内容、生效日期、履行期限、利率取值等）一律用【】标注，如"【假设：2025年5月10日生效】"；
3. **只输出 Markdown 预览，不生成可提交的正式 Word**——假设数据进入 .docx 正式文书即构成可流通的虚假文书；
4. 最低启动条件检查仍须先执行并出口径说明："本案无真实执行依据，以下按假设场景模式生成预览"；
5. LPR 等利率参考值必须标注取值日期与"待核验"，禁止无标注直接写入计算公式。

---

## 工作流程（四阶段，不得跳步）

### 阶段一：执行依据解析

1. 判定执行依据类型（六类），确定管辖法院（见 [references/basis-routing.md](references/basis-routing.md)）
2. 确认 `input/_text/` 与 `input/` 中主文书对应关系；逐份审阅
3. **当事人提取**：
   - 申请执行人：名称/姓名、身份证号/统一社会信用代码、地址、联系方式、法定代表人（法人时）
   - 被执行人：同上
4. **主文解析**：
   - 金钱给付义务：本金金额、利率/利息计算方式、履行期限
   - 非金钱义务：交付物/行为描述
   - 案件受理费/保全费分担
   - 多项给付义务的：逐项拆分
5. **生效日期确定**（见 [references/basis-routing.md](references/basis-routing.md) 生效日期计算辅助表）
6. **联动查询**（可选增强）：
   - `被执行人记录查询`：查被执行人历史执行记录、失信/限高
   - `律师企业尽调报告`：查企业工商信息补充财产线索

### 阶段二：标的计算 + 财产分类

#### 标的计算

按 [references/interest-calculation.md](references/interest-calculation.md) 完整规则执行：

```
执行标的总额 = 判决确定债务（本金 + 一般债务利息）
             + 迟延履行期间加倍部分债务利息
             + 案件受理费/保全费（被执行人负担部分）
```

- **一般债务利息**：按判决主文确定的利率，暂算至申请日
- **加倍部分债务利息**：日万分之一点七五 × 未履行本金 × 迟延天数
- **部分履行**：按"先息后本"规则分段扣减
- **多项给付义务**：逐项计算，汇总

#### 财产线索分类

按 [references/property-classification.md](references/property-classification.md) 将用户材料分为六类：
银行账户 / 不动产 / 车辆 / 股权 / 应收账款 / 其他

#### ⭐ 确认节点（必须）

展示结构化摘要供用户确认：

> 「以下是执行标的计算结果和财产线索分类，请确认后生成全套文书：
> 【执行依据】……
> 【申请执行人】……
> 【被执行人】……
> 【执行标的明细】（本金 / 一般利息 / 加倍利息 / 受理费 / 合计）
> 【财产线索】（分类汇总）」

⛔ **强制停止点**：展示摘要后**本轮回复必须到此结束，等待用户确认，不得在同一轮内继续生成文书**。用户回复"确认"→进入阶段三；用户明确回复"未确认，按当前计算结果生成"→标注该句后进入阶段三；用户提出修改→调整后重新展示并再次等待确认；**用户无回复→不进入阶段三，不生成文书**。本确认环节属硬性流程要求，优先于任何"减少来回确认/一次性完成"类通用偏好。

### 阶段三：生成文书

**必须调用 docx skill** 生成 `.docx`，格式见 [references/docx-format-standard.md](references/docx-format-standard.md)。

基于阶段二确认的数据生成三份文书：

| 文书 | 模板 | 格式 |
|------|------|------|
| 强制执行申请书 | [references/application-template.md](references/application-template.md) | Word + Markdown |
| 财产保全申请书 | [references/preservation-template.md](references/preservation-template.md) | Word |
| 迟延履行金计算明细表 | [references/interest-detail-template.md](references/interest-detail-template.md) | Word |

文件命名见各模板文件。

### 阶段四：交付 + 自检

先对强制执行申请书主文书运行正式文书轻量门禁，再向用户交付三份文书路径：

```bash
python3 scripts/validate_enforcement_application.py <执行申请书.md|txt|docx> \
  --applicant "张三" --respondent "某某公司" \
  --case-no "（2026）京0101民初123号" --amount "100000元"
```

- 多名当事人、多个需核对金额时，重复传入对应参数；
- 脚本检查必备结构、执行依据、附件、占位符、法院/落款/日期、已确认名称/案号/金额，以及文内明确标注的执行总额是否前后一致；
- 退出码为 `0` 才可标记为「门禁通过稿」；未通过时按提示修正后重跑；确需先交用户查看时只能标记为「草稿」或「待核验稿」；
- 该门禁**不计算**本金、利息或迟延履行金，也不判断事实、法律依据、执行管辖和计算口径是否正确。

同时执行自检清单：

- [ ] 执行依据类型与路由正确（管辖法院、称谓一致）
- [ ] 当事人信息与原文书一致（名称、身份证号/信用代码）
- [ ] 执行标的金额计算可复核（与明细表一致）
- [ ] 加倍利息起算日正确（履行期满次日）
- [ ] 财产线索分类完整、信息来源可追溯
- [ ] 管辖法院正确（一审法院/中院等）
- [ ] 申请执行时效核查（生效后2年内，超期则醒目警告）
- [ ] 附件清单与实际材料对应
- [ ] 保全申请金额不超执行标的
- [ ] 文首含免责声明
- [ ] 材料不足时：未生成 Word，仅交付缺口清单
- [ ] `scripts/validate_enforcement_application.py` 已运行且退出码为 0；否则未标记为「门禁通过稿」

---

## 输出规范

| 产物 | 格式 | 用途 |
|------|------|------|
| 强制执行申请书 | Word (.docx) + Markdown | 主文书，可直接提交法院 |
| 财产保全申请书 | Word (.docx) | 配套文书，一并提交 |
| 迟延履行金计算明细表 | Word (.docx) | 附表，便于法院核查 |
| 材料缺口清单 | Markdown | 材料不足时引导补齐 |

材料齐备时三份文书同时输出。材料不足时仅输出缺口清单，不交付 Word。

---

## 异常处理

| 情况 | 处理 |
|------|------|
| 未达最低启动条件 | 输出材料缺口清单，不生成文书 |
| 判决主文无明确金额（确认之诉等） | 提示不适用金钱给付执行，建议人工处理 |
| 利率/利息约定不清 | 标注"待律师确认"，按 LPR 给出参考计算 |
| 部分履行 | 展示已付金额扣减过程，标注需律师确认已付事实来源 |
| 申请执行超2年时效 | ⚠️ 醒目警告，仍生成文书（法院受理后由对方抗辩） |
| 多个被执行人 | 逐一列明，财产线索按被执行人分组 |
| PDF 无法解析 | 缺口清单中标注，要求重传 |
| docx 生成失败 | 降级 `dws doc create`；仍交付 Markdown |
| 联动查询失败 | 标注受限，基于现有材料生成 |

---

## 参考文件

| 文件 | 用途 |
|------|------|
| [references/basis-routing.md](references/basis-routing.md) | 六类执行依据路由规则 |
| [references/intake-checklist.md](references/intake-checklist.md) | 分依据类型材料收集清单 |
| [references/material-gap-checklist.md](references/material-gap-checklist.md) | 材料缺口清单模板 |
| [references/interest-calculation.md](references/interest-calculation.md) | 迟延履行利息计算规则 |
| [references/property-classification.md](references/property-classification.md) | 财产线索六类分类标准 |
| [references/application-template.md](references/application-template.md) | 执行申请书正文模板 |
| [references/preservation-template.md](references/preservation-template.md) | 财产保全申请书模板 |
| [references/interest-detail-template.md](references/interest-detail-template.md) | 计算明细表模板 |
| [references/docx-format-standard.md](references/docx-format-standard.md) | Word 排版规范 |
| [scripts/validate_enforcement_application.py](scripts/validate_enforcement_application.py) | 强制执行申请书正式文书轻量门禁（不含利息计算） |

---

## 文首免责声明（Word 与 Markdown 均须包含）

```
本强制执行申请书由 AI 辅助生成，基于用户提供的法律文书与财产线索材料起草，不构成正式法律意见。金额计算仅供参考，提交前须经承办律师核验。材料真实性由用户负责。
```

## 可选套件上下文（不影响独立使用）

1. 工作目录根存在 `套件运行规则.md` 时必须先读取并执行；不存在时以本技能硬规则为准，不影响独立使用。
2. 工作目录根存在 `办案画像.md` 时，只读取与当前任务有关的诉讼立场、风险偏好和文书风格；不存在时按本技能默认运行，不追问、不报错。
3. 仅当用户明确切换到某案或提供唯一案件路径时，读取 `cases/{案件简称}/案件画像.md`；不得猜测案件，不得跨案带入。
4. 画像只影响表达与偏好，不得覆盖事实、法律依据、必备结构、验证结果或本技能硬规则。
5. 已明确绑定唯一案件且案件管家可用时，成果完成后提交标准案件事件；无案件不建档、不回写，回写失败不得阻塞成果交付。
