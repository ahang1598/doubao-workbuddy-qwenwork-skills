# 飞书 XML 交付规范（Markdown → lark-doc XML）

仅当用户对第一阶段结尾的飞书文档问句作出肯定性回复后读取。本文件是第二阶段唯一飞书交付契约：**映射规则与流程在此；完整 XML 结构与样式对照 `references/example_feishu.xml`**（与 `chat_example.md` 同源）。

## 前置依赖（lark-doc）

本 Skill 第二阶段**必须**调用 **`lark-doc`** 伴生 Skill 写入飞书文档。无 `lark-doc` 时不得进入飞书组装流程，也不得降级为 Markdown / `docs +create`。

### 启动前检查

进入「飞书文档流程」前，确认运行环境已加载 `lark-doc` Skill（在 Agent 可用 skills 列表中可见，或用户已声明已安装）。

若不可用：

1. 向用户说明：「生成飞书文档需要已安装 `lark-doc` Skill，当前环境未检测到。」
2. 保留已交付的第一阶段对话框正文。
3. 给出安装指引（见下），**不要**静默改用其它格式交付。

### 安装方式

`lark-doc` 与 `doubao-market-hotspot` **分开安装**，需同时存在于 Agent 的 skills 目录：

| 环境 | 典型路径 |
|---|---|
| Cursor 用户级 | `~/.cursor/skills/lark-doc/` |
| Cursor 项目级 | `<项目>/.cursor/skills/lark-doc/` |
| Claude 用户级 | `~/.claude/skills/lark-doc/` |

安装步骤：

1. 获取 `lark-doc` 技能包（`.skill` / `.zip` 或含 `SKILL.md` 的目录）。
2. 解压或复制到上表任一路径，确保存在 `lark-doc/SKILL.md`。
3. 重启 Agent 会话或刷新 skills，确认列表中出现 `lark-doc`。
4. 用户对飞书文档问句作出肯定性回复后调用 `lark-doc` 写入 XML。

### 调用约定

- **输入**：按本章组装的完整 lark-doc XML 片段（建议先写入 `work/<主题>_飞书.xml` 自检）。
- **禁止**：在 XML 外包裹 `<html>` / `<body>` / `<style>` / `<script>`。
- **写入后**：跑 `qa-checklist.md` 并目检飞书渲染。

### 与本 Skill 的分工

| Skill | 职责 |
|---|---|
| `doubao-market-hotspot` | 检索、对话框正文、MD→XML 映射、合规与来源 |
| `lark-doc` | 飞书 API / 文档创建与更新、XML 落盘 |

未安装 `lark-doc` 时，本 Skill 仍完整交付**第一阶段**；飞书文档为可选第二步。

## 原则

- **唯一母版**：第一阶段已交付的对话框正文（或 `work/<主题>_分析草稿.md`）。不重新检索、不改核心判断、不新增来源。
- **原句搬运**：XML 叙述性文字必须能在母版中找到对应原文。去掉块级 Markdown（`##`、`###`、`| 表格 |`、`---`、列表符 `-`），**保留**母版 `**…**` → `<b>…</b>`（headline、本段结论整段、关键分句、格式标签，见 `chat_contract.md`「加粗规则」）与定点 emoji。`**本段结论：……**` 整段映射为 `<p><b>本段结论：……</b></p>`。引用块 `>` 去掉前缀后按段落搬运。**禁止**压缩、改写、同义替换或新增判断。
- **只输出 lark-doc XML**：禁止 Markdown、`docs +create`、JSON 中间文件或其它格式。
- **格式对齐**：母版须已按 `chat_contract.md` 书写（事件卡片、四列表格等），否则无法稳定转换。

视觉目标：白底、深黑正文、橙色章节强调、`<hr/>` 分区、紧凑表格（见 `example_feishu.xml`）。

## 转换流程

0. 确认 `lark-doc` 可用；**未安装则停止**。
1. 读取母版 Markdown（优先 `work/<主题>_分析草稿.md`，否则已交付对话框正文）。
2. 读取 `references/disclaimers.json`（飞书尾部免责声明唯一正文源）。
3. 按「模块映射」与「逐节规则」组装 XML；对照 `example_feishu.xml` 各节注释区间。
4. 建议写入 `work/<主题>_飞书.xml` 自检。
5. 跑 `qa-checklist.md`「MD→XML 复核」；**任一项失败或触发 `chat_contract.md`「飞书准入门禁」→ 硬阻断，不得调用 `lark-doc`**。
6. 写入后目检：表格未错列、callout 正常、链接可点、文档头数字表渲染正常。

## 模块映射（10 模块 → 7 节 + 尾部）

| chat_contract 模块 | 飞书 XML | example_feishu.xml 注释锚点 |
|---|---|---|
| 1 固定风险提醒 | **丢弃**；改用顶部 callout + 尾部免责声明 | — |
| 2 首屏 | 文档头（title / 元数据 / callout / headline / 导语段） | `SECTION:document-header` |
| 2b 首屏 `关键数据` 表 | 文档头数字锚点区（紧接导语段之后、第一节之前） | `SECTION:document-metrics` |
| 2c 首屏作答+条件 | 一、核心观点（本段结论/结论/改善/恶化） | `SECTION:h1-01-core-view` |
| 3 有哪些关键增量 | 二、有哪些关键增量信息？ | `SECTION:h1-02-increments` |
| 4 为什么现在重要 | 三、这些信息为什么重要？ | `SECTION:h1-03-importance` |
| 5 如何影响市场 | 四、上述信息如何影响市场？ | `SECTION:h1-04-impact` |
| 6 各方观点与分歧 | 五、各方有哪些值得关注的观点？ | `SECTION:h1-05-viewpoints` |
| 7 接下来盯什么 | 六、哪些信号会验证核心观点？哪些信号代表观点证伪？ | `SECTION:h1-06-signals` |
| 8 风险提示 | **丢弃**（仅保留在第一阶段对话框） | — |
| 9 信息来源 | 七、信息来源 | `SECTION:h1-07-sources` |
| `disclaimers.json` | 尾部「风险提示与免责声明」（在第七节之后） | `SECTION:risks-disclaimer` |
| 固定结尾问句 | **丢弃** | — |

固定七个 `h1` 标题字面量不可改（见 `example_feishu.xml`）。一级标题格式：`<hr/>` + `<h1 align="left"><span text-color="orange">…</span></h1>`。行内样式嵌套顺序：`<a>` → `<b>` → `<em>` → `<span>` → 文本。

## 逐节规则

### 文档头（模块 2 · 首屏）

| 母版片段 | XML |
|---|---|
| 首屏加粗 headline 行 | `<p><b>📌 {headline 正文}</b></p>`（母版须含句首 `📌`，原句搬运） |
| 首屏导语段（headline 后第一段） | `<p>{导语}</p>`；从导语句首解析 `scope` / `time_window` / `as_of` 填入灰色元数据行 |

母版**必须**含首屏 headline + 导语（见 `chat_contract.md`「首屏」）。完整结构见 `example_feishu.xml` `SECTION:document-header`。

### 文档头 · 关键数据（模块 2b · `SECTION:document-metrics`）

紧接 `SECTION:document-header` 的导语段落之后、第一个 `<hr/>`（第一节）之前插入。

| 母版片段 | XML |
|---|---|
| 首屏 2×2 Markdown 表（**无** `**关键数据：**` 标题行） | `<table>` + 固定 `colgroup`（宽 180/200/180/200） |

**表格 XML 结构（固定）：**

```xml
<!-- SECTION:document-metrics BEGIN -->
<table>
<colgroup><col width="180"/><col width="200"/><col width="180"/><col width="200"/></colgroup>
<thead><tr>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">指标</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">数值</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">指标</span></b></p></th>
<th background-color="light-gray"><p align="center"><b><span text-color="orange">数值</span></b></p></th>
</tr></thead>
<tbody>
<tr>
<td background-color="light-gray" vertical-align="middle"><p align="left">{指标1}</p></td>
<td vertical-align="middle"><p align="left">{数值1 含 <b> 与 [n]}</p></td>
<td background-color="light-gray" vertical-align="middle"><p align="left">{指标3}</p></td>
<td vertical-align="middle"><p align="left">{数值3}</p></td>
</tr>
<tr>
<td background-color="light-gray" vertical-align="middle"><p align="left">{指标2}</p></td>
<td vertical-align="middle"><p align="left">{数值2}</p></td>
<td background-color="light-gray" vertical-align="middle"><p align="left">{指标4 可空}</p></td>
<td vertical-align="middle"><p align="left">{数值4 可空}</p></td>
</tr>
</tbody>
</table>
<!-- SECTION:document-metrics END -->
```

规则：

- 原句搬运：单元格文本与母版表一致；`**…**` → `<b>…</b>`；`[n]` 保持纯文本。
- **指标**列 `align="left"`；**数值**列 `align="left"`（长标签可换行）。
- 仅 3 个指标时，第二行右侧两格可留空 `<p align="left"></p>`，**不得**删行改 1×3 布局。
- 母版缺首屏 2×2 表 → **不得**进入飞书流程（P0 硬阻断）。

### 一、核心观点（模块 2c · 首屏作答+条件）

| 字段 | 母版来源（固定，不得自选） |
|---|---|
| `本段结论：` | 首屏**作答+条件**段中作答部分前 1–2 句（或作答首句）。**不得**改用导语全文或模块 4 本段结论。 |
| `问题：` | **省略**该行（用户已知提问）；XML 中不写 `问题：` 段落 |
| `结论：` | 首屏**作答+条件**段全文（作答内关键分句 `<b>`，条件句常规字重；保留 `[n]`） |
| `改善：` | 同段条件半句中「若…则…」前半或第一个分句所描述之改善情形 |
| `恶化：` | 同段条件半句中「若…则需…」或第二个分句所描述之恶化情形 |

### 二、关键增量（模块 3）

- 首段：模块 3 `**本段结论：……**` 整段原句 → `<p><b>本段结论：……</b></p>`。
- 每条事件卡片：`### 📰 日期｜信息来源：…｜标题` → `h3`（去掉 `📰 ` 前缀）；四字段 `事实/机制/市场反应/后续验证` 各一段 `<p>`。
- 卡片间母版 `---` → `<hr/>`。3–5 条，顺序与母版一致。见 `SECTION:h1-02-increments`。

### 三、为什么重要（模块 4）

- 首段：模块 4 `**本段结论：……**` 整段原句（写预期差与「为什么现在」；与第一节「本段结论」**分工不同**，允许并存）→ `<p><b>本段结论：……</b></p>`。
- 其后至下一 `##` 前所有段落 → 逐段 `<p>` 原句搬运；相邻长段落之间保留母版空行（飞书各 `<p>` 自然分段）。见 `SECTION:h1-03-importance`。

### 四、如何影响市场（模块 5）

- 首段：模块 5 `**本段结论：……**` 整段原句 → `<p><b>本段结论：……</b></p>`。
- 四列 Markdown 表格 → `<table>` + 固定 `colgroup`（宽 90/180/200/200）；表头橙字、首列灰底。单元格原句搬运，保留 `[n]`。**变化 / 传导机制 / 市场含义**列 `align="left"`（长因果句左对齐）。见 `SECTION:h1-04-impact`。

### 五、各方观点（模块 6）

- 首段：模块 6 `**本段结论：……**` 整段原句 → `<p><b>本段结论：……</b></p>`。
- 每条 `- **📋 官方事实**：…` → `<p><b>📋 官方事实：</b>…</p>`（角色 emoji 固定 📋📊🏦🔄）。至少 4 条。见 `SECTION:h1-05-viewpoints`。

### 六、信号验证（模块 8）

- 一级标题字面量必须为：`六、哪些信号会验证核心观点？哪些信号代表观点证伪？`
- 首段：模块 7 `**本段结论：……**` 整段原句 → `<p><b>本段结论：……</b></p>`。
- 信号条 → 四列表格（宽 140/180/200/200）：信号列含 `信号N · 📌`；观察口径取 `👀 盯` 行；改善/恶化列保留 ✅/❌ 前缀。**观察口径 / 改善 / 恶化**列 `align="left"`。信号条间母版 `---` 不单独成节。见 `SECTION:h1-06-signals`。

### 七、信息来源（模块 9）

母版 `[n] 来源名 · 日期 · 标题 · URL` → `<p>[n] 来源名｜日期｜<a href="URL">标题</a></p>`。正文段中 `[n]` 保持纯文本。见 `SECTION:h1-07-sources`。

**硬门禁（P0）：** …其中来源第四段必须是 `https://` 文章链接；缺首屏 2×2 表、首屏缺作答/条件段、信号无量化阈值、事件卡 `市场反应` 无定价层，均视为失败。

### 风险提示与免责声明（disclaimers.json）

- 第七节之后：`<hr/>` + `<h1>风险提示与免责声明</h1>`。
- **不得**搬运模块 8「风险提示」正文（含 `风险N · …`、`触发`、`证伪` 等 callout）；该模块仅保留在第一阶段对话框。
- 免责声明正文**唯一来源**：`disclaimers.json` 的 `standard_v2_full_risk_notice.body`；去掉首行 `风险提示与免责声明：` 前缀后按 `\n` 拆 **3 段**，每段灰色 `<p>` 逐字包裹，不得删改。不得搬运模块 1 短风险提醒。见 `SECTION:risks-disclaimer`。

## 表格通用规则

- `<colgroup>` 列宽与 `example_feishu.xml` 各节一致（文档头数字表 180/200/180/200；第四节 90/180/200/200；第六节 140/180/200/200）
- 表头 `background-color="light-gray"`，文字 `text-color="orange"`
- 第一列（及文档头数字表的指标列）`background-color="light-gray"`；单元格 `vertical-align="middle"`
- 除表头与第一列标签外，**长文本列默认 `align="left"`**（文档头数值列、第四节后三列、第六节后三列）

## Markdown 行内转换

| 母版 | XML |
|------|-----|
| `**文字**` | `<b>文字</b>` |
| `> 段落` | 去 `>`，按 `<p>` 输出 |
| `## 📌 …` 等模块标题 | 丢弃（由固定 `h1` 承载，不带 emoji） |
| `### 📰 日期｜…` | `h3` 去掉 `📰 ` 前缀 |
| 开篇 `关键数据` 2×2 表 | `SECTION:document-metrics` 表格，见上 |
| `---` | 卡片/风险条间 → `<hr/>`；模块间丢弃 |
| 定点 emoji | 保留在对应单元格或段落 |
## 禁止

- 块级 Markdown 残留（`**`、`##`、`| 表格 |`、`---`、`>`）
- `<!DOCTYPE html>`、`<style>`、`<script>`、CSS class
- 句内 `→` / `↓` 箭头链
- 随意 emoji；允许母版定点 emoji 及顶部 📌 callout
- 尾部「风险提示与免责声明」中写入模块 8 风险 callout 或 `触发`/`证伪` 正文
- 手写、改写、缩写免责声明（必须来自 `disclaimers.json`）
- 未在母版出现的额外 `<b>` 或 emoji

## 转义

动态文本：`&` → `&amp;`，`<` → `&lt;`，`>` → `&gt;`，换行 → `<br/>`。

## 准出

对照 `qa-checklist.md`「MD→XML 复核」与「飞书 XML 复核」全部通过后，调用 **`lark-doc` skill** 写入。
