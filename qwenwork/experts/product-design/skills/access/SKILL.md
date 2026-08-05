---
name: 无障碍检查
name_en: "access"
argument-hint: "输入要做 WCAG 审计的页面，如：登录页或表单提交流程"
description: >
  完整无障碍审计（WCAG 2.1 AA/AAA）。对设计稿 / 已实现页面做系统性无障碍合规检查——覆盖 4 个 principles（Perceivable / Operable / Understandable / Robust）×13 guidelines×50+ success criteria，每条 finding 标注 WCAG 编号 + 严重度 + 修复成本 + 法规依据。默认 AA 合规目标，可切换 AAA（政府 / 医疗 / 公共服务场景）。

  触发关键词：无障碍审计、WCAG、a11y、accessibility audit、/无障碍检查、合规检查、ADA / EAA / 残疾人保障法、对比度、屏幕阅读器、键盘可达、辅助技术。

  排除（反向）：基础无障碍体检（用 check.accessibility 4 项快查）、设计稿走查（用 /设计走查）、实现验收（用 /设计验收）、性能 / 兼容性测试（开发自测）。

description_en: >
  Full accessibility audit (WCAG 2.1 AA/AAA). Performs a systematic accessibility compliance check
  on design files or implemented pages — covering 4 principles (Perceivable / Operable /
  Understandable / Robust) × 13 guidelines × 50+ success criteria. Each finding is annotated with
  WCAG reference number, severity, remediation cost, and applicable regulations. Default target:
  AA compliance; switchable to AAA for government / healthcare / public service contexts.

  Triggers when a designer says: "accessibility audit", "WCAG", "a11y", "accessibility review",
  "compliance check", "ADA", "EAA", "contrast ratio", "screen reader", "keyboard accessibility",
  "assistive technology", "无障碍审计", "合规检查".

  Excludes: basic 4-item accessibility quick-check (use /check), design file review
  (use /check), implementation QA (use /qa), performance/compatibility testing
  (developer responsibility).

allowed-tools:
  - Read
  - Glob
  - Grep
  - WebFetch
  - AskUserQuestion
chain:
  protocol_version: "1.0"
  reads: [brief, flow-web, flow-mobile, sitemap, stories, check]
  writes: access
  schema:
    skill: string
    generated_at: string
    project_name: string
    target:
      type: enum [url, code, design-file, screenshots]
      reference: string
      scope: array<string>
    compliance_target: enum [A, AA, AAA]
    audit_mode: enum [auto, guided, checklist]
    findings:
      - id: string
        wcag_criterion: string
        principle: enum [perceivable, operable, understandable, robust]
        level: enum [A, AA, AAA]
        severity: enum [blocker, major, minor]
        description: string
        evidence: string
        suggestion: string
        fix_effort: enum [quick-win, medium, major-rework]
        regulatory_reference: array<string>
    compliance_summary:
      total_criteria_checked: number
      total_passed: number
      total_failed: number
      by_principle:
        perceivable: { passed: number, failed: number }
        operable: { passed: number, failed: number }
        understandable: { passed: number, failed: number }
        robust: { passed: number, failed: number }
      conformance_level_achieved: enum [none, A, AA, AAA, not-determined]
      conformance_gap: array<string>
    legal_risk_assessment:
      applicable_regulations: array<string>
      risk_level: enum [high, medium, low, none]
      notes: string
---

# 无障碍检查

> 你是无障碍审计专家。对设计稿 / 已实现页面做**完整 WCAG 2.1 合规检查**——覆盖 4 个 principles × 13 guidelines × 50+ success criteria，每条发现标注 WCAG 编号 + 法规依据。**默认 AA 合规**（行业标准），政府 / 医疗 / 教育 / 金融场景可切到 AAA。

**与 Check.accessibility 严格区分**：

| | Check.accessibility（4 项） | Access（50+ 项） |
| --- | --- | --- |
| 性质 | **基础体检**——常见无障碍快查 | **专科深度审计**——完整 WCAG 合规 |
| 触发 | 每个设计稿走查时附带跑 | **合规驱动 / 行业要求**专门启动 |
| 覆盖 | 对比度 / 辅助标识 / 键盘可达 / alt+aria | **WCAG 全部 13 guidelines** |
| 输出 | findings（pass/fail）| **findings + WCAG 编号 + 法规依据 + 合规等级达成判断** |

**核心使命**：回答 3 个问题：
1. 当前设计 / 实现达到了 WCAG 哪个 level（none / A / AA / AAA）？
2. 距离合规目标的 gap 有哪些？修复成本？
3. 在哪些地区 / 行业有法律风险？

**适用场景**：
- 🏛 **法规驱动**：欧洲 EAA（2025 年生效）/ 美国 ADA Title III / 英国 EQA / 中国《残疾人保障法》信息无障碍条款
- 🏥 **行业要求**：医疗、金融、政府、教育、ToG、ToB 公共服务
- ⚖️ **诉讼风险防范**：Domino's Pizza v. Robles 等无障碍诉讼后，AA 合规成为美国 ToC 产品的事实标准

---

## Chain Context

### 上游读取（Step 0 执行）

按以下顺序尝试读取上下文：

1. 扫描会话中的 `<!-- spark-context:brief -->` / `<!-- spark-context:flow-web -->` / `<!-- spark-context:flow-mobile -->` / `<!-- spark-context:sitemap -->` / `<!-- spark-context:stories -->` / `<!-- spark-context:check -->` marker
2. 读取项目目录 `spark-output/context/brief.json` 等
3. 都没有则进入 Step 1 询问审计目标

可复用字段映射：

- `brief.user` → 判断主用户群是否含残障 / 老年用户（影响 compliance_target 推荐：通常 AA，含残障用户主流场景推荐 AAA）
- `brief.constraints` → 法规约束（如"必须符合 EAA"自动锁定 compliance_target=AA）
- `flow-web.output_files` / `flow-mobile.output_files` → 实际审计的代码文件
- `sitemap.pages` → 审计范围；access=public 的页面**法律风险更高**
- `check.findings`（category=accessibility）→ 已识别的基础问题，Access 在其上做深度扩展
- `stories.design_touchpoints` → 影响哪些 success criteria 适用（如有 video → 1.2 时间媒体相关 criteria 必查）

读到上下文后告知用户："检测到 [项目名]，将基于 [N] 个屏 / [N] 个文件做 WCAG [AA/AAA] 完整审计。本次审计将检查 [估算] 个 success criteria。"

### 下游输出（Step 5 执行）

完成 Access 后，**同时**做两件事：

1. **会话内输出**（marker 之间放裸 JSON，不要嵌套 ```json 代码块）：

   ```
   <!-- spark-context:access -->
   {...JSON（schema 见 frontmatter）...}
   <!-- /spark-context:access -->
   ```

2. **写入项目文件**：`spark-output/context/access.json`（目录不存在时先创建）

3. **额外保存 Markdown 报告**：`spark-output/access/[project-slug].md`，含 WCAG 合规报告（可作为对外合规证明的草稿）。

下游可消费 Skill：**QA**（实现层无障碍验证）/ **PRD**（合规章节直接引用）/ **Pitch**（合规风险 Ask）/ **Retro**（项目合规水平归档）。

### 字段流向下游

> 注：v0.5.1 起 **Retro** 已显式 reads access（合规等级 → Decision Validation）。其余 Skill（QA / PRD / Pitch）需手动引用：

- `access.findings[severity=blocker]` → 手动贴入 **QA** 的 review_mode（验收时增加 accessibility 维度）；**PRD** 的 Constraints & Risks（合规风险段）
- `access.compliance_summary` → 手动贴入 **Pitch** 的 Asks 候选（合规等级是否成为发布阻断器）
- `access.regulatory_reference[]` → 手动贴入 **PRD** 的工程交付段（合规法规引用）
- `access.findings[].suggestion` → 手动贴入 **Retro** 的 What Didn't（合规失分项）

v0.5.1 已让 retro.reads 加入 `access`；qa.reads 暂未加入（QA 关注实现还原度，access 是合规审计，性质不同——保持独立更清晰）。

---

### 更新链路面板（必做，失败不阻断）

> **协议依据**：chain-protocol.md §九「面板自动生成约定」。本步在 Handoff 之前执行；**告知用户的提示必须作为独立段落输出，禁止折叠进 Handoff 末尾、禁止静默跳过**。

1. **找模板**：定位 `_shared/dashboard-template.html`（依次：相对套件根 → `glob dashboard-template.html` 搜套件安装目录 → 三轮都失败时，**用独立段落醒目告知用户**：`⚠️ 链路面板模板未找到（套件安装可能不完整，建议重装）。本 Skill 已正常完成，下游链路不受影响。` 然后跳过本步、继续 Handoff，**不阻断 Skill 完成**）。
2. **聚合 STATE**：扫 `spark-output/context/*.json`，聚合为 `{"project":"<brief.project_name 或 frame.project_name 或目录名>","generated_at":"<ISO8601>","contexts":{"<skill-name>":{"done":true,"summary":"<≤ 40 字>","fields":{}}}}`，`contexts` 只列已完成的 Skill（`done` 字段总数即为面板进度计数）。
3. **克隆模板**到 `spark-output/dashboard.html`（覆盖），用正则 `/\/\*__SPARK_STATE_INJECT__\*\/null/` 替换为 `/*__SPARK_STATE_INJECT__*/<JSON.stringify(STATE)>`。
4. **独立段落告知用户**（强提示，单独成段，与 Handoff 之间空一行；根据 `Object.keys(STATE.contexts).length`（记作 `done`）选模板）：
   - **`done === 1`（本项目第一次生成 dashboard）输出长版**：
     ```
     📊 链路控制台已生成：spark-output/dashboard.html（双击在浏览器打开）

     这是本套件给你的「设计全链进度看板」——5 个阶段 × 27 个 Skill 节点，亮起的代表已完成的步骤，灰色的是后续可调用的节点。每跑完一个 Skill 都会自动更新，建议钉在浏览器一个标签页里随时回看，能看清「现在在哪一步、下游还差什么、链路是否健康」。
     ```
   - **`done > 1`（后续更新）输出短版**：
     ```
     📊 链路面板已更新 · 进度 [done]/27 · spark-output/dashboard.html
     ```
5. **红线**：步骤 4 必须以**独立段落直接发给用户**——不允许只写内部日志、不允许折叠进 Handoff 末尾一行小字、不允许在模板缺失时静默跳过（必须按步骤 1 的醒目提示告知）。

## 触发条件

- 用户说"无障碍审计 / WCAG / a11y check / Access / 完整无障碍检查"
- 用户说"需要合规 / 政府项目 / 医疗合规 / 银行金融合规"
- 用户使用 `/无障碍检查` 指令
- Brief 中 constraints 含"无障碍" / "WCAG" / "ADA" / "EAA" 等关键词时
- Check 跑完后用户说"无障碍部分需要更深入"

---

---

## 独立能力（无需连接器）

本 Skill 在完全离线、无任何连接器的场景下即可完整交付，所有方法论与输出形态不依赖外部系统：

- **WCAG 2.1 AA / AAA checklist**：完整方法论 + 法律风险评估本地完成
- **链式上下文双通道**：写入 `spark-output/context/access.json` + 会话内 marker block，下游 QA / Retro 可直接读取
- **Findings 按 Principle × Severity 排序**：含修复优先级
- **合规等级达成判定**：本地完成，无需第三方审计工具

> 红线：缺连接器时 **绝不 abort**，所有引导与输出路径必须照常完成。

## 增强能力（连接器加持）

接入以下连接器后，可减少手动粘贴、提高对齐效率。所有连接器均为可选，未装时按"降级路径"列的方式回落。

| 连接器 | 阶段 | 增强能力 | 降级路径 |
| --- | --- | --- | --- |
| **Figma** | 执行流程（视觉规格阶段） | 直接抓 frame 上的颜色 / 字号 / 间距 token，自动算对比度 / 触控目标尺寸 | 未装时让用户提供 token 文件或截图，工具用本地颜色采样 |
| **GitHub** | 执行流程（代码侧阶段） | 扫源码中的 aria-* / role / alt 标签覆盖率，识别代码层 a11y 缺失 | 未装时让用户粘贴关键页面代码片段 |

**接入触发**：用户首次调用 `/无障碍检查` 时，Skill 主动检测已认证的连接器并显示「已检测到：XXX，将自动启用增强模式」提示，用户可在该次会话中选择关闭。

**字段流向变化**：

- 启用 **Figma** → `chain.schema` 新增可选字段 `visual_audit: {contrast_pairs, target_sizes}`
- 启用 **GitHub** → `chain.schema` 新增可选字段 `code_audit: {aria_coverage, alt_coverage}`

> 所有新增字段都是 **可选**，未启用连接器时字段缺省，下游 Skill 必须能容忍缺省。

---

## 执行流程

按 Step 0 → 1 → 2 → 3 → 4 → 5 顺序执行。

### Step 0 — Chain Context 读取

按上文执行。

### Step 1 — 合规目标 + 审计范围确认

用 `AskUserQuestion` 询问：

1. **合规目标**：
   - **AA**（默认）—— 行业事实标准，覆盖大部分 ToC 场景
   - **A** —— 最低门槛，仅起步阶段使用
   - **AAA** —— 政府 / 医疗 / 公共服务 / 部分教育产品要求；商业产品通常无法全部达到
2. **法规适用范围**（多选）：
   - 美国 ADA Title III
   - 欧洲 EAA（2025-06 生效）
   - 英国 EQA
   - 中国《残疾人保障法》信息无障碍条款
   - 行业内部 / 公司内部要求
   - 仅自查无法规约束
3. **审计对象**：
   - 设计稿（Figma 描述 / 截图）
   - 已实现代码（路径 / URL）
   - 全部（推荐）
4. **审计范围**：完整产品 / 关键 flow / 单页

合规目标 + 法规组合影响后续 finding 的 severity 标注（如 EAA 适用时，AA 级失败 = blocker；纯自查时 AA 级失败 = major）。

### Step 2 — 审计模式选择

**模式 A — 自动审计（URL 或代码）** — 推荐

- URL：用 WebFetch + 模拟 axe-core / Lighthouse a11y 规则扫
- 代码：用 Read / Glob 扫 .tsx / .vue / .html，按 ARIA / 语义化标签 / 对比度规则
- 自动检测约 30-40 个 success criteria（不能完全替代真人 + 辅助技术测试）

**模式 B — 引导审计（截图 / 设计稿）**

- 用户提供截图，AI 视觉描述 + WCAG 对应
- 局限：动态交互 / 键盘可达需用户配合验证

**模式 C — 完整清单（适合 AAA 或法规审计）**

- 输出全 50+ success criteria 清单
- 用户 / 设计师 / 第三方审计师逐项答 Pass / Fail / N/A
- 适合外审 / 上线前最终合规审核

告知用户当前模式 + 局限性。

### Step 3 — 按 WCAG 4 Principles × 13 Guidelines 逐项审计

每条 finding 按七元组记录：`wcag_criterion` / `principle` / `level` / `severity` / `description` / `evidence` / `suggestion` / `fix_effort` / `regulatory_reference`。

---

#### Principle 1: Perceivable（可感知）

> 信息和 UI 组件必须以用户能感知的方式呈现

##### Guideline 1.1 — Text Alternatives（文本替代）

| WCAG | Level | 检查 |
| --- | --- | --- |
| **1.1.1** Non-text Content | A | 所有非文本内容（图片 / icon / 按钮）有等效文本替代（alt / aria-label） |

##### Guideline 1.2 — Time-based Media（时间媒体）

| WCAG | Level | 检查 |
| --- | --- | --- |
| **1.2.1** Audio-only and Video-only (Prerecorded) | A | 纯音频 / 纯视频有替代文本 |
| **1.2.2** Captions (Prerecorded) | A | 预录视频有字幕 |
| **1.2.3** Audio Description or Media Alternative | A | 预录视频有音频描述或文本替代 |
| **1.2.4** Captions (Live) | AA | 直播视频有实时字幕 |
| **1.2.5** Audio Description (Prerecorded) | AA | 预录视频有音频描述 |
| 1.2.6-1.2.9（AAA） | AAA | 手语 / 扩展音频描述 / 转录 |

##### Guideline 1.3 — Adaptable（可适应）

| WCAG | Level | 检查 |
| --- | --- | --- |
| **1.3.1** Info and Relationships | A | 信息 / 结构 / 关系可通过代码确定（用 h1-h6 / nav / main 等语义标签） |
| **1.3.2** Meaningful Sequence | A | 内容呈现顺序符合阅读逻辑（不依赖 CSS） |
| **1.3.3** Sensory Characteristics | A | 不仅靠形状 / 颜色 / 大小 / 位置 / 声音传达信息 |
| **1.3.4** Orientation | AA | 不限制屏幕方向（除必要场景） |
| **1.3.5** Identify Input Purpose | AA | 表单字段标注 autocomplete 属性 |
| 1.3.6 Identify Purpose | AAA | UI 组件 / icon 用 ARIA 标注用途 |

##### Guideline 1.4 — Distinguishable（可辨识）

| WCAG | Level | 检查 |
| --- | --- | --- |
| **1.4.1** Use of Color | A | 不仅靠颜色传达信息（错误用红色+图标+文字三重） |
| **1.4.2** Audio Control | A | 自动播放 > 3 秒的音频有暂停 / 停止 / 音量控制 |
| **1.4.3** Contrast (Minimum) | AA | 正文对比度 ≥ 4.5:1，大字 ≥ 3:1 |
| **1.4.4** Resize Text | AA | 文本可放大到 200% 不破坏功能 |
| **1.4.5** Images of Text | AA | 不用图片代替文本（除 logo / 装饰） |
| **1.4.10** Reflow | AA | 320px 宽度下不横向滚动 |
| **1.4.11** Non-text Contrast | AA | UI 组件 / 图形对比度 ≥ 3:1 |
| **1.4.12** Text Spacing | AA | 用户调整行距 / 字距 / 段间距不破坏布局 |
| **1.4.13** Content on Hover or Focus | AA | hover / focus 触发的内容可关闭 / hover 可达 / 持续显示 |
| 1.4.6-1.4.9（AAA） | AAA | 对比度 7:1 / 无背景音 / 视觉呈现可定制 |

---

#### Principle 2: Operable（可操作）

> UI 组件和导航必须可操作

##### Guideline 2.1 — Keyboard Accessible（键盘可访问）

| WCAG | Level | 检查 |
| --- | --- | --- |
| **2.1.1** Keyboard | A | 所有功能可通过键盘操作（不依赖鼠标） |
| **2.1.2** No Keyboard Trap | A | 键盘焦点不被困在某个 UI 内 |
| **2.1.4** Character Key Shortcuts | A | 单字符快捷键可关闭 / 重映射 |
| 2.1.3 Keyboard (No Exception) | AAA | 所有功能完全键盘可操作（含复杂交互） |

##### Guideline 2.2 — Enough Time（充足时间）

| WCAG | Level | 检查 |
| --- | --- | --- |
| **2.2.1** Timing Adjustable | A | 时间限制可关闭 / 延长 / 调整 |
| **2.2.2** Pause, Stop, Hide | A | 自动移动 / 闪烁 / 滚动内容可暂停 |
| 2.2.3-2.2.6（AAA） | AAA | 无时间限制 / 中断管理 / 重新认证 |

##### Guideline 2.3 — Seizures and Physical Reactions（癫痫安全）

| WCAG | Level | 检查 |
| --- | --- | --- |
| **2.3.1** Three Flashes or Below Threshold | A | 不出现 > 3 次/秒的闪烁 |

##### Guideline 2.4 — Navigable（可导航）

| WCAG | Level | 检查 |
| --- | --- | --- |
| **2.4.1** Bypass Blocks | A | 提供跳过重复内容的机制（skip-link） |
| **2.4.2** Page Titled | A | 每页有描述性 title |
| **2.4.3** Focus Order | A | 键盘焦点顺序符合内容逻辑 |
| **2.4.4** Link Purpose (In Context) | A | 链接文字 + 上下文能说明用途（不出现纯"点击这里"） |
| **2.4.5** Multiple Ways | AA | 多种方式找到页面（导航 + 搜索 + sitemap） |
| **2.4.6** Headings and Labels | AA | 标题 / 标签描述清晰 |
| **2.4.7** Focus Visible | AA | 键盘焦点可见（focus ring） |
| 2.4.8-2.4.10（AAA） | AAA | 位置信息 / 链接用途独立可见 / Section 标题 |

##### Guideline 2.5 — Input Modalities（输入模式）

| WCAG | Level | 检查 |
| --- | --- | --- |
| **2.5.1** Pointer Gestures | A | 多点 / 路径手势有单点替代 |
| **2.5.2** Pointer Cancellation | A | 单点动作可在抬起前取消 |
| **2.5.3** Label in Name | A | 可视标签包含在可访问名称中 |
| **2.5.4** Motion Actuation | A | 运动触发的功能（摇一摇）有 UI 替代 |

---

#### Principle 3: Understandable（可理解）

##### Guideline 3.1 — Readable（可读）

| WCAG | Level | 检查 |
| --- | --- | --- |
| **3.1.1** Language of Page | A | 页面声明语言（html lang="zh-CN"） |
| **3.1.2** Language of Parts | AA | 不同语言的段落声明语言 |

##### Guideline 3.2 — Predictable（可预测）

| WCAG | Level | 检查 |
| --- | --- | --- |
| **3.2.1** On Focus | A | 元素获得焦点不引发上下文变化 |
| **3.2.2** On Input | A | 表单输入不自动 submit / 跳页 |
| **3.2.3** Consistent Navigation | AA | 多页中导航位置一致 |
| **3.2.4** Consistent Identification | AA | 相同功能的组件标识一致 |

##### Guideline 3.3 — Input Assistance（输入辅助）

| WCAG | Level | 检查 |
| --- | --- | --- |
| **3.3.1** Error Identification | A | 错误明确标识（不仅靠颜色） |
| **3.3.2** Labels or Instructions | A | 表单字段有标签 / 说明 |
| **3.3.3** Error Suggestion | AA | 错误给出修正建议 |
| **3.3.4** Error Prevention (Legal, Financial, Data) | AA | 不可逆操作可撤销 / 检查 / 确认 |

---

#### Principle 4: Robust（健壮）

##### Guideline 4.1 — Compatible（兼容性）

| WCAG | Level | 检查 |
| --- | --- | --- |
| **4.1.1** Parsing | A | HTML 解析无错误（标签闭合 / id 唯一） |
| **4.1.2** Name, Role, Value | A | 所有 UI 组件可被辅助技术识别 name / role / value（用 ARIA 或语义标签） |
| **4.1.3** Status Messages | AA | 状态消息可被屏幕阅读器播报（aria-live） |

---

### Severity 判定规则

| Severity | 判定条件 |
| --- | --- |
| **blocker** | 适用 level 内任意 Level A 失败；或法规明确要求时任意 AA 失败 |
| **major** | 适用 level 内 AA 失败（无强制法规时） |
| **minor** | AAA 失败（仅当 compliance_target=AAA 时） |

### Regulatory Reference 自动填充

根据 Step 1 用户选的法规，每条 finding 自动附上对应条款：

- ADA Title III → 36 CFR Part 36 + WCAG 2.1 AA
- EAA → Directive 2019/882 + EN 301 549
- 中国 → GB/T 37668-2019《信息技术 互联网内容无障碍可访问性技术要求与测试方法》

### Step 4 — Compliance Summary + Conformance Level 判断

跑完全部检查后，自动判断 conformance level achieved：

| Level | 达成条件 |
| --- | --- |
| **none** | 任意 Level A 失败 |
| **A** | Level A 全 pass，AA 有失败 |
| **AA** | Level A + AA 全 pass，AAA 有失败 |
| **AAA** | Level A + AA + AAA 全 pass |
| **not-determined** | 自动审计不足以判断（如缺辅助技术测试） |

输出 conformance_gap：距离合规目标差什么。

### Step 5 — 输出

#### 5.1 Markdown 报告（输出到对话 + 保存到 `spark-output/access/[project-slug].md`）

```markdown
# 无障碍审计报告 — [项目名]

- **审计时间**：[ISO8601]
- **合规目标**：WCAG 2.1 [A/AA/AAA]
- **适用法规**：[列表]
- **审计模式**：自动 / 引导 / 清单
- **审计范围**：[N] 屏 / [N] 文件

## 合规等级达成

🎯 **目标**：WCAG 2.1 AA
✅ **实际达成**：[level]
⚠️ **Gap**：[列出未达成的关键 criteria]

## 总览

| Principle | Passed | Failed | 通过率 |
| --- | --- | --- | --- |
| Perceivable | N | N | % |
| Operable | N | N | % |
| Understandable | N | N | % |
| Robust | N | N | % |
| **总计** | N | N | % |

## 法律风险评估

**风险等级**：[high/medium/low/none]

**适用法规与影响**：
- [法规 1]：[影响描述]

## Findings（按 Principle × Severity 排序）

### 🔴 Blocker（必修，影响合规等级）

#### [WCAG 1.4.3] 对比度（AA）
- **描述**：[description]
- **证据**：[evidence + 文件位置]
- **建议**：[suggestion]
- **修复成本**：quick-win / medium / major-rework
- **法规依据**：ADA / EAA / EN 301 549 / GB/T 37668

（每条 finding 同上格式）

### 🟠 Major
（同上）

### 🟡 Minor（仅 AAA 目标时显示）
（同上）

## 修复优先级建议

- **必修（Blocker）**：N 项 → 合规上线门槛
- **应修（Major）**：N 项 → 达成 AA 目标
- **可延后（Minor）**：N 项 → 追求 AAA 时考虑
```

#### 5.2 双通道 Context 输出

按 [chain-protocol.md](../../chain-protocol.md) 第 2.1 节执行。

按 [chain-protocol.md](../../chain-protocol.md) §2.1 v1.1 智能适配规则：

**Step 1 — 写盘到 `spark-output/context/access.json`**（必做，主持久化通道；目录不存在先创建）。写入以下完整 JSON：

```
{
  "skill": "access",
  "generated_at": "<ISO8601>",
  "project_name": "...",
  "target": {
    "type": "url|code|design-file|screenshots",
    "reference": "...",
    "scope": ["..."]
  },
  "compliance_target": "AA",
  "audit_mode": "auto|guided|checklist",
  "findings": [
    {
      "id": "access-1",
      "wcag_criterion": "1.4.3 Contrast (Minimum)",
      "principle": "perceivable",
      "level": "AA",
      "severity": "blocker",
      "description": "...",
      "evidence": "...",
      "suggestion": "...",
      "fix_effort": "quick-win",
      "regulatory_reference": ["ADA Title III", "EAA (Directive 2019/882)"]
    }
  ],
  "compliance_summary": {
    "total_criteria_checked": 0,
    "total_passed": 0,
    "total_failed": 0,
    "by_principle": {
      "perceivable": { "passed": 0, "failed": 0 },
      "operable": { "passed": 0, "failed": 0 },
      "understandable": { "passed": 0, "failed": 0 },
      "robust": { "passed": 0, "failed": 0 }
    },
    "conformance_level_achieved": "AA|A|none|not-determined",
    "conformance_gap": ["..."]
  },
  "legal_risk_assessment": {
    "applicable_regulations": ["..."],
    "risk_level": "high|medium|low|none",
    "notes": "..."
  }
}
```

**Step 2 — chat 输出紧凑 marker**（必做，⛔ **不要在 chat 内重复输出 Step 1 的完整 JSON**）：

```
<!-- spark-context:access ref="spark-output/context/access.json" -->
Access 已保存：project=[project_name]，target=WCAG 2.1 [AA/AAA]，实际达成 [level]，[N] findings（blocker [n] / major [n] / minor [n]），风险等级 [high/medium/low]
<!-- /spark-context:access -->
```

**降级 fallback**：若 Step 1 写盘失败（chat-only 平台），输出完整 JSON marker（无 ref 属性，marker 之间放裸 JSON）作为唯一持久化通道。

### Handoff 提示（必输出）

> **协议**：按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出；前 5 候选由 `_shared/skill-graph.json` 的依赖图算法实时算（done ⊆ ready，按 next_hint.preferred → alternatives → 同阶段 → anchor → fan-out 排序），优先建议从 `_shared/skill-graph.json#skills[id="access"].next_hint` 读取。

**首行模板**：`✅ 无障碍检查 已完成，WCAG 2.1 AA checklist 通过率已沉淀。`

**本 Skill 的 `next_hint`**（来自 skill-graph.json，**不可在此 SKILL.md 内硬编码覆盖**）：

- **preferred**：`/qa`
- **优先理由**：WCAG 合规已确认，进 QA 做交付前整体还原度验收。
- **alternatives**：`/check` (回到全局走查做整体一致性核查)
- **emoji**：♿

**红线**：
- ❌ 禁止在本段硬编码候选清单（如「进入 X / Y / Z」）——所有候选必须由算法实时生成
- ❌ 禁止按「文档类 / 视觉类 / 决策类」再分类候选（v0.5.5 起，分类已折叠进 next_hint.alternatives）
- ❌ 禁止与「更新链路面板」段合并——两段必须各自独立成段，中间空一行
- ❌ 禁止漏第 2 行候选清单——即使候选只有 1 个、或为空（终端节点）也要写出来

---

## 实操注意事项

### 自动审计的真实局限

- **不能完全替代真人 + 辅助技术测试**：自动工具能覆盖约 30-40% WCAG 检查项，剩余需人工 + 屏幕阅读器（NVDA / JAWS / VoiceOver）验证
- **动态内容难检测**：异步加载 / 单页应用的状态变化对自动工具是黑盒
- **语义化判断有主观性**：alt 文本"对不对"AI 能判断但不一定准

### 与 Check.accessibility 的协同

- 项目早期跑 Check（4 项快查）—— 发现基础问题
- 上线前 / 合规驱动场景跑 Access（50+ 完整）—— 达到合规等级
- 两者 finding 可能有重复，**Access 输出会自动标注 "已被 check 发现"**，避免重复修复

### Compliance Level 实际达成的"现实"

- **A 级**：基础门槛，多数小项目能达到
- **AA 级**：行业标准，**约 60-70% 商业产品实际达不到全部 AA**（最常失败：1.4.3 对比度 / 1.3.1 语义化 / 2.4.7 focus 可见）
- **AAA 级**：政府 / 公共服务标准，**商业产品基本无法全 AAA**（许多 AAA 要求与商业可用性冲突）

WCAG 官方表态："**AAA 不应作为通用商业产品的目标**"。

### 法规更新提示

- 欧洲 EAA：2025-06-28 强制生效，覆盖银行 / 电商 / 旅游 / 媒体等
- 美国 ADA：判例法持续扩展，2026 年 DOJ 发布 Title II rule（公共部门必须 AA）
- 中国：2024 年《无障碍环境建设法》生效，政府 / 公共服务部门必须无障碍

如项目跨多地区，**取最严要求**。

---

## 已知限制

- 不替代正式第三方无障碍审计（如 Deque / Level Access 等）
- 不替代真人用户 + 辅助技术测试
- AAA 检查的部分 criteria（如手语视频）AI 无法判断
- 中文环境某些 WCAG 适用性需人工判断（如汉字字间距）
- 法律解释最终需法务确认，本 Skill 输出仅作技术参考

---

## 与兄弟 Skill 的边界（v0.4.0 补充）

| 场景 | 用谁 | 不用谁 |
| --- | --- | --- |
| 完整 WCAG 2.1 AA/AAA 合规审计（50+ 项） | **Access** | Check（基础走查含可访问性一项粗筛） |
| 设计稿基础走查（10 类维度） | Check | Access（Check 不深入到 50+ 项 WCAG） |
| 实现还原度（前端做出来对不对） | QA | Access（Access 是设计阶段定标准） |
| 启发式专家走查 | Audit（含可访问性 1 项） | Access（Audit 不是 WCAG 全审计） |
| 屏幕阅读器 / 键盘可达性专项 | Access | Edge（Edge 处理异常状态本身） |
| 法律合规场景（如政府 / 医疗 / 教育） | Access（强制） | 任何其他 Skill（无法替代法律证据） |

**Access 不可替代性**：50+ 项 WCAG 2.1 AA/AAA 完整审计 + 法律风险评估 + 修复优先级矩阵，是「合规场景必须用、非合规场景强烈推荐」的设计师专项 Skill——其他 Skill 的可访问性都是粗筛。

## 质量标准

1. **覆盖 WCAG 4 原则**：Perceivable（可感知）/ Operable（可操作）/ Understandable（可理解）/ Robust（健壮）——4 原则必须各覆盖
2. **AA 必查 + AAA 标记**：AA 级 50+ 项强制覆盖，AAA 级标「推荐」并标本项目是否需要
3. **每项标准带证据**：每项检查含「通过 / 不通过 / 不适用」+ 证据（截图 / 代码 / 数值，如对比度 4.5:1）
4. **修复优先级矩阵**：法律风险 × 影响人群 × 修复成本 三维打分，给修复 Top 10
5. **法律风险评估段**：明确本产品是否落入 ADA / 欧盟 EAA / 国内信息无障碍条例范围，标风险等级
6. **键盘 / 屏幕阅读器双路径**：Tab 序 / Focus 可见 / 屏幕阅读器朗读顺序——必须双路径独立检查

## 红线规则

1. **不替代真实辅助技术测试**：Access 是设计稿审计，真实 NVDA / JAWS / VoiceOver 测试必须工程后做，Access 不是终点
2. **不忽略颜色对比**：所有文本 / 图标 / 状态指示必须计算对比度，标「视觉上看着够」即视为红线
3. **不替代法律咨询**：法律风险段是设计视角警示，真正合规判定需要法务——出具「本产品 WCAG 合规」结论 = 越权红线
