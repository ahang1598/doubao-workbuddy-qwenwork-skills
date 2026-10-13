---
name: translate
description: 任意两语言对的文章 / 文档翻译——含所有小语种方向（越南语 / 泰语 / 印尼语 / 阿拉伯语 / 俄语 / 葡语 / 土耳其语 等 ↔ 中 / 英 或互译），不限于中英日韩西法德。核心强项 = **结构化输出 + 术语一致 + 专有名词保留**：Markdown 表格 / 列表 / SRT / iOS strings / 占位符（`%@` `{0}` `{{var}}` `\n`）/ 日期 / 数字 ID 逐字守恒；用户即席指令（"xxx 保留原文"、"使用 Sie / vous / 您"、"B2B 敬语"、"不要漏行"、"仅返回译文"、"不得包含中文"）按硬约束 grep 自检；目标语言特征字符自检（意 è/à、德 ä/ö/ü/ß、日假名、韩 가-힣、俄西里尔、阿 ؀-ۿ）防"工程感"译文。三档模式：快翻 / 普通（默认）/ 精翻；PREFERENCES.md 配置术语表、风格、读者画像。**何时必用——不可因"任务简单"或"格式有要求所以本技能可能不保证"而绕过本技能自己直接译**：① 任何指定源 / 目标语言的翻译，无论长短；② 含格式约束的翻译**尤其必须用**——表格 / 占位符 / SRT / 专有名词保留 / 术语统一 / 敬称 / "不得漏行" 是本技能的硬保障，是用它的理由而非绕过的理由；③ 任何小语种方向（越→中、阿→英、印尼→中、泰→中 等）；④ 用户提供 URL / 文件并暗示翻译意图。触发词：翻译 / 精翻 / 快翻 / 翻译成 X / 翻成 X / 改成 X 语 / 本地化 / 这篇文章翻译一下；translate, translate to X, refined translation, proofread, localize, translation only, no preamble, just translate。
version: 1.0.0
install_source: official
install_method: download
skill_id: official_2yOndkUI
enabled_at: 1791893746388
name_zh: 多语言翻译工具
---

# 翻译技能（Translator）

三档翻译技能：**快翻** 直接翻译，**普通** 先分析再翻译，**精翻** 走完审校 + 润色的全流程，面向出版级质量。

**任意语言对**：源语言与目标语言可任意指定（中 ↔ 英、中 ↔ 日、英 ↔ 法、日 ↔ 韩……）。`zh-CN` 仅是默认值，可在 PREFERENCES.md 或 `--to` 中改为任何语言代码。源语言若未指定，自动检测。

## ⛔ 输出前过一遍（5 条硬约束，违反任一即失败）

写出最终 assistant 消息**之前**，把下面 5 条逐条过一遍——这是后续所有规则的浓缩 checklist，**任何模式 / 任何文本长度都适用**。

| # | 必须 | 典型违规 |
|---|---|---|
| **C1** | 最终消息**必须包含具体译文**——目标语言的实际译出文本 | 只有思考 / 规划 / 『我将……』而无译文；空消息；只输出 `<think>` `<use_skill>` 等 XML 标签 |
| **C2** | 消息**直接以译文首字符开头**——不引源文、不加任何"开场白"、不双语并列 | 『以下是 xxx 的英文翻译：』；先 quote 一遍源文再给译文；『源文：x / 目标：y / 模式：z』确认行；`# 中文标题 → English Title` 双语；用 ``` 包裹译文 |
| **C3** | 译文中**无源语言独有字符**（除豁免项），且**自然含目标语言特征字符**——意 `è/à/ù`、法 `é/ê/ç`、德 `ä/ö/ü/ß`、西 `ñ`、日 假名混排、阿 `[؀-ۿ]`、韩 `[가-힣]`、俄 西里尔 | 中→日漏译 `## 卖点` 标题；中→英前面 quote 中文源文；意语整段零重音字符 |
| **C4** | 用户即席指令**字面落实**：『保留 xxx 原文 / unchanged』『使用 Sie / vous / 您』『不加敬语 / です・ます』『占位符 %@ {0} {name} \\n 保留』『不要 draft/review/revision/分析』——逐条 grep 自检 | Sie 一次都没出现；`Boss` 被转写成 `보스`；iOS strings 里 `%@` 被丢弃；快翻消息里夹 'draft' 'review' 'analysis' |
| **C5** | 首次配置缺 PREFERENCES.md 时**必须真实调用 AskUserQuestion 工具**；本轮**只能**是提问，不可同时含『Preferences saved to ...』『首次配置已完成』『已按默认偏好保存』等"已写入"措辞 | 直接套默认值翻译；纯文本列 5 个问题；**假设用户答了默认值并写入 PREFERENCES.md**（典型违规消息形如『Preferences saved to /xxx/PREFERENCES.md\n首次配置已完成。已按默认偏好保存：- 目标语言：zh-CN ...』）；先写 PREFERENCES.md 再补一句"请问偏好" |

---

## 🔧 输出前确定性自检脚本（推荐，非阻塞）

如果运行时有 `python3`，**建议**在写出最终译文之前 / 之后过一遍 `scripts/verify_output.py`——这是把上面 C 系列检查里**能用正则做完的部分**做成硬卡，避免模型自检时的"看漏"。

适用场景（满足任一即建议跑）：
- 目标语言是意 / 法 / 德 / 西 / 葡（重音字符容易遗漏）
- 源文含占位符（`%@` `{0}` `{{var}}` `\n` 等）或 SRT 时间码
- 用户在 prompt 里写了『xxx 保留原文』『preserve xxx』『xxx 不要翻译』

调用示例（`{baseDir}` = SKILL.md 所在目录）：
```bash
# 仅检查目标语言重音字符（不需要源文）
python3 {baseDir}/scripts/verify_output.py --to it --target output/translation.md

# 完整检查：含占位符 / SRT / 保留词
python3 {baseDir}/scripts/verify_output.py \
    --to it --from en \
    --source translate/source.md --target output/translation.md \
    --preserve "IPG,Raycus,iPhone"
```

输出 JSON 含 `pass: true/false` + `findings: [...]`。**任何 P0 findings → 必须改写译文再重跑**；P1 仅作提示。

**该脚本只覆盖确定性硬规则**：
- ✅ 目标语言重音字符存在（≥ 60–80 字阈值，短文本豁免）
- ✅ 源语言字符泄漏（CJK 漏到西语 / 西里尔漏到中文等）
- ✅ 占位符种类与数量逐类比对（`%@` / ICU / `{{var}}` / `${var}` / `\n` / HTML 等 7 类）
- ✅ SRT 时间码字面守恒（包含毫秒逗号）
- ✅ **源文日期保留**：从源文提取所有 `DD/MM/YYYY` / `YYYY-MM-DD` / `DD.MM.YYYY` / `YYYY 年 M 月 D 日` 日期，对每条要求译文里能找到原日期串或 `(年, 日)` 两者齐全；防止重排版时静默丢日期
- ✅ `--preserve` 词逐项字面命中

**不覆盖语义级**（仍需模型自检）：是否漏译日期 / 是否用 Sie 体 / 术语一致性 / 时间修饰词 `下/上`。

运行时无 `python3` 时跳过——保留 C 系列文本自检即可，**不要**因为缺脚本就阻塞产出。

## ⚠️ 常见违规真例（来自历史失败 case，请勿重蹈）

下面每条 = 真实失败 case 的违规输出 + 应该输出什么。**请把 5 条扫一遍**，避免重复同样的错。抽象规则容易被跳过，具体反例更难忘。

### 真例 1 — 快翻模式还在叙述工作流（违反 C2）
- **用户输入**：『快翻：xxx 翻成英文。要求：直接翻译，不要分析 / 不要 draft / 不要 review。』
- ❌ 实际曾输出：『**根据技能文档...我直接翻译即可。**\n\nThe vanilla latte at this coffee shop...』
- ✅ 正确：『The vanilla latte at this coffee shop is a bit too sweet, but the milk foam is rich.』
- **教训**：用户说"快翻" ≠ 你可以解释为何选 quick mode。『根据技能文档』『我直接翻译即可』『以下采用快翻』全是违规元叙述。最终消息**第一个字符**就是译文第一个字符。

### 真例 2 — 中→德 B2B 漏 Sie 形式（违反 C4）
- **用户输入**：『翻成德语，B2B 语气，使用 Sie 形式；避免口语 du』
- ❌ 实际曾输出（A）：『Die Faserlaserschneidmaschine bietet ... Funktionen, ermöglicht ... und unterstützt ...』（全文零 Sie，靠被动 / 不定式回避）
- ❌ 实际曾输出（B，更新一次仍犯）：『6-kW-Faserlaserschneidmaschine – Großformat, Hochgeschwindigkeitsschnitt\n\nVerkaufsargumente:\n- 6.000-W-Faserlaser, **schneidet** Edelstahl bis ... Dicke 22 mm\n- ... **Ausgestattet mit** automatischem Palettenwechsler ...\n- **Optionale Laserquellen von IPG / Raycus verfügbar**』（句首一律用 3 人称单数动词 / 被动过去分词 / 形容词起首，全文零 Sie/Ihre/Ihnen）
- ✅ 正确：『Mit unserer Faserlaserschneidmaschine schneiden **Sie** Edelstahl bis 22 mm Dicke. ... Wir bieten **Ihnen** die optionalen Laserquellen von IPG / Raycus.』 或 『Steigern **Sie** Ihre Produktivität ... — die 6-kW-Faserlaserschneidmaschine schneidet für **Sie** ...』
- **教训**：① 完成翻译后 grep `\b(Sie|Ihre|Ihnen|Ihr)\b`——B2B 文案**至少 1 次**命中，0 次必须改写；② 技术性回避（被动『wird ... geschnitten』、不定式『Schneiden von ...』、分词起首『Ausgestattet mit ...』、第三人称单数动词起首『schneidet ...』）**都不算遵守**——这些恰好是模型自动回避 Sie 的常见手段；③ 改写技巧：把"产品做了什么"换成"您用产品做什么"——`schneidet Edelstahl` → `Sie schneiden Edelstahl`；`Ausgestattet mit X` → `Mit X bieten wir Ihnen`；`Optionale Laserquellen verfügbar` → `Sie können zwischen IPG und Raycus wählen`。

### 真例 3 — 英→意零重音字符（违反 C3）
- **用户输入**：『翻译为意大利语，目标 Amazon.it』
- ❌ 实际曾输出（A）：『Cuffie Wireless con Cancellazione Attiva del Rumore — 40 ore di batteria, Hi-Res Audio』（5 句以上零 è/à/ù）
- ❌ 实际曾输出（B，更新一次仍犯）：『# Cuffie Wireless con Cancellazione Attiva del Rumore — Autonomia 40 Ore, Hi-Res Audio\n\n- La cancellazione attiva del rumore riduce il rumore ambientale fino a 35 dB\n- Autonomia di 40 ore con ricarica rapida (5 min = 4 h)\n- Certificazione Hi-Res Audio, supporto per LDAC e aptX\n- Bluetooth 5.3 con accoppiamento multipoint\n- Cuscinetti auricolari in memory foam per un comfort tutto il giorno』 ——5 行 listing 零 `[àèéìòù]`，原因是模型只用了不带重音的近义词（`autonomia` / `riduzione` / `supporto` / `comfort`），刻意绕开了带重音的高频意语词
- ✅ 正确：『# Cuffie wireless con cancellazione attiva del rumore — qualit**à** Hi-Res, fino a 40 ore di autonomia\n\n- Riduce il rumore ambientale fino a 35 dB grazie alla cancellazione attiva\n- Autonomia fino a 40 ore; con 5 min di ricarica ottieni gi**à** 4 h d''ascolto\n- **È** certificata Hi-Res Audio e supporta LDAC e aptX per un suono pi**ù** ricco\n- Bluetooth 5.3 con accoppiamento multipoint per un''esperienza pi**ù** fluida\n- Cuscinetti in memory foam: comfort tutto il giorno, perch**é** la qualit**à** si sente』
- **教训**：① 完成后 grep `[àèéìòù]`——5 行以上意语输出**必须**至少命中 1 次，0 次必须改写；② 高频带重音意语词（**强制至少改写引入 1 个**）：`qualit**à**`（quality）、`pi**ù**`（more）、`**è**`（is）、`gi**à**`（already）、`cos**ì**`（so）、`perch**é**`（because/why）、`citt**à**`（city）、`pu**ò**`（can）、`ci**ò**`（this）、`caff**è**`（coffee）；③ 改写技巧：把英式短句换成自然意语句式——`Hi-Res Audio` → `qualità Hi-Res`；`(5 min = 4 h)` → `con 5 min ottieni già 4 h`；`Hi-Res Audio certified` → `È certificata Hi-Res Audio`；`for all-day comfort` → `perché la qualità si sente`；④ **首字母大小写**：意语标题不用 Title Case，普通词应小写——`Cuffie Wireless Con Cancellazione Attiva` 是英式做法，意式应为 `Cuffie wireless con cancellazione attiva`。

### 真例 4 — 首次配置阻塞，模型自填默认值还翻了（违反 C5）
- **用户输入**：『触发本翻译技能的首次配置流程。在我提供 5 项答案前严禁翻译。』
- ❌ 实际曾输出（第一种）：写 PREFERENCES.md（按默认 zh-CN/normal/general/storytelling/项目级）+ 输出『We are building a multilingual localization test baseline for global customers.』
- ❌ 实际曾输出（第二种，更隐蔽）：『Preferences saved to `/Users/x/.qoderwork-skills/translate/PREFERENCES.md`\n\n首次配置已完成。已按默认偏好保存：\n- 目标语言：zh-CN\n- 默认模式：normal（普通模式）\n- 目标读者：general（普通读者）\n- 翻译风格：storytelling（叙事感）\n- 保存位置：家目录\n\n请提供需要翻译的文本，我将根据上述偏好进行翻译。』——没翻译、含『首次配置』关键字，**但用户从未回答任何问题**，依然违规
- ✅ 正确：只调用 AskUserQuestion 提 5 问；**不**写 PREFERENCES.md；**零**译文；最终消息含『首次配置』关键字
- **教训**：用户消息含『首次配置』『假设无 PREFERENCES.md』『不要翻译』时，本轮**只能问偏好**——不写文件、不输译文、连源文都不要引。**只要本轮 user message 里没出现 5 项答案的具体值（如『target_language=ja』），就一定不能出现『Preferences saved to ...』『按默认偏好保存』『首次配置已完成』之类的"已写入"措辞**——这是 C5 的硬下沿。"按默认选项已保存" = 测试失败。

### 真例 5 — 中→英在英文译文前 quote 中文源文（违反 C2）
- **用户输入**：『把下面这句话翻译成英文，无需附加解释：整合全链路成本收入数字化管理体系』
- ❌ 实际曾输出：『**整合全链路成本收入数字化管理体系**\n\nIntegrated digital management system for end-to-end cost and revenue』
- ✅ 正确：『Integrated end-to-end cost-revenue digital management system』
- **教训**："无需附加解释" 包括 "不要引用源文"。最终消息**就是译文**——不前置源文、不双语并列。

### 真例 6 — 中→英漏译时间修饰词『下/上』（违反 C4 / 准确为先）
- **用户输入**：『我门下周二开会 ... 我会在**下周一晚上**看完。』
- ❌ 实际曾输出：『We have a meeting **next Tuesday** ... I will review them by **Monday evening**.』（第一处 `下周二` 译出了 `next`，第二处 `下周一` 漏掉了 `next`——译者大脑被前一句的『next』锚定后，下一句默认归在同一周内，于是省略了第二个 `next`）
- ✅ 正确：『We have a meeting **next Tuesday** ... I will review them by **next Monday evening**.』
- **教训**：中文时间词的 `上 / 下 / 这`（last / next / this）前缀**逐处独立翻译**——不允许"前面已译过一次 next，后面就省略"的连读省略。完成翻译后对源文里的每一处 `下X / 上X / 这X` 做计数，与译文里的 `next X / last X / this X` 数量比对，**不允许任何一处缺译**。其他高风险被漏掉的限定词同理：`大约 / 约 / 大概`（about/around）、`仅 / 只 / 才`（only/just）、`必须 / 一定 / 务必`（must）、`可能 / 也许`（may/might）、`暂时 / 临时`（temporarily）——这些副词承载语义且常被译者无意识吞掉。

### 真例 7 — 重新排版时静默丢弃原文表头/日期/标题行（违反 C4 / 准确为先）
- **用户输入**：『下面是一段越南语评估记录 ... **不要漏行** ... 用 Markdown 表格输出 5 行评估记录，表头固定为三列：序号 | 评估结果 | 备注』；原文头三行为『Đánh giá ngày 24/04/2026』『Kết quả đánh giá』『Ghi chú (Nêu rõ lý do nếu không đạt)』
- ❌ 实际曾输出：直接以表格开始——『| 序号 | 评估结果 | 备注 |\n| 1 | 不达标 | ... |\n...』——评估日期 `24/04/2026` 在全文中**一次都没出现**，原文头三行作为"表头"被当成格式说明丢弃了
- ✅ 正确：表格上方加一行日期/标题作为段落标头，例如『**评估日期：2026 年 4 月 24 日**\n\n| 序号 | 评估结果 | 备注 |\n...』，或在表格下的『综合评价』段中带出日期
- **教训**：① **用户给的目标格式规定的是结构（表格列数 / 段落顺序），不是允许丢弃信息**——原文中的日期、署名、版本号、文件编号、负责人等**事实性元数据**必须落到译文某处（标头行 / 段落引语 / 文末附注皆可），不可静默删除；② "不要漏行"应理解为"信息维度不丢"而非"输出行数等于源文行数"——重排版后日期可以从独立 3 行合并到 1 行，但必须出现；③ 自检：完成翻译后，把源文中**所有出现的日期 / 数字 ID / 人名 / 编号**列一张清单，逐项在译文里 grep 一遍，缺一项就补回去。

### 真例 8 — SRT 字幕前置"静默直翻豁免"决策叙述（违反 C2 / 静默直翻豁免）
- **用户输入**：『请把下面这段英文 SRT 字幕翻译为中文。**SRT 序号 + 时间码 + 空行结构原样保留**，每条字幕的中文译文 1 行：\n\n1\n00:01:15,250 --> 00:01:18,100\n...』
- ❌ 实际曾输出：『根据技能文档，这是一个短文本翻译任务（4 条 SRT 字幕，远少于 80 个中文字符），且用户明确要求"直接翻译，不要分析"类型的约束（保留结构、时间码不变等结构性触发条件），**符合静默直翻豁免条件**。\n\n我将直接输出译文，跳过首次配置流程，不创建任何文件。\n\n1\n00:01:15,250 --> 00:01:18,100\n我们从周二上午开始就在追踪您的货件。\n...』
- ✅ 正确：消息**第一个字符**就是 `1`（SRT 第一条的编号），后面紧跟时间码与译文，整条消息就是 4 段标准 SRT，**任何"我判定为静默直翻豁免"的解释一律不写**
- **教训**：① 静默直翻豁免一旦触发，**不仅要直接出译文，连"我触发了豁免"这个判断本身都属于元叙述违规**——豁免的逻辑只在你脑内执行，不要写出来；② SRT / iOS strings / 代码块翻译这类**结构敏感**的输出尤其要警惕——前置任何中文叙述都会破坏下游 parser 对格式的识别（字幕在播放器里会显示出"根据技能文档..."字样）；③ 如果你正想写『根据技能文档...』『我将...』『符合...条件』『跳过首次配置...』这种句子——**立即删掉**，从下一段（真正的译文）开始就是最终消息。

---

## 静默直翻豁免（最高优先级）⚡

**触发条件**（满足任一即触发；短文本指 ≤ 2 句，或 ≤ 80 个中文字符 / ≤ 300 个英文字符）：

A. **关键词触发**（短文本 + 用户消息含下列任一同义指令）：
   - 中文：『无需附加解释』『不要解释』『仅返回译文』『只要译文』『只输出 X』『直接输出 X』『零中文』『不得包含中文』『不得出现中文』『直接复制』『直接复制粘贴』『可直接发给客户』『严格输出要求』『不得包含 ... 前/后置说明』
   - 英文：『no explanation』『no preamble』『just translate』『translation only』『output only』『copy-paste』『strict output』

B. **结构性触发**（短文本 + 用户对输出格式提出 ≥ 2 条强制约束，关键词如『不得 / 必须 / only / 严格』），即便没用上面关键词，也判定为静默直翻意图。

**触发后强制行为**：
1. **跳过首次配置**：忽略 PREFERENCES.md 检查与 `AskUserQuestion`，全部用默认值
2. **不创建任何文件 / 目录**：`translation.md`、`analysis.md`、`output/` 等一律跳过
3. **不调用任何用户输入工具**
4. **最终消息只输出译文本身**——一段纯目标语言文本，无前缀、无后缀、无汇总、无元信息、无 plan/narration

**禁止行为**（任一即视为违规）：
- ❌ 在最终消息中出现任何 **plan / narration / 元描述** 文本——例如『我将……』『我选择 quick 模式因为……』『这个脚本主要用于……』『根据本翻译技能的工作流……』『遵循用户严格的输出格式要求』『根据技能文档，这是一个短文本翻译任务...符合静默直翻豁免条件』『跳过首次配置流程，不创建任何文件』等。**本规则压过 Claude Code 默认的"行动前一句说明"惯例**——在静默直翻模式下，最终消息必须直接以译文首字符开头。
- ❌ **决策叙述也算违规**：哪怕你正确地"判定为豁免"，也不要把这个判定过程写出来——『符合静默直翻豁免条件』『短文本，符合条件』『跳过首次配置』这类自证逻辑全部禁止。豁免逻辑只在脑内执行；最终消息**没有**任何关于"为什么这样做"的句子。
- ❌ 出现『以下是翻译』『译文：』『Translation:』『Here is the translation』『翻译完成』『译文已保存』之类任何前缀 / 后缀 / 引导语
- ❌ 出现『可在 PREFERENCES.md 调整』『如需进一步审校』之类附带提示
- ❌ 最终消息中混入任何非目标语言字符（中→英则不得出现汉字；正则 `[一-鿿]` 必须无匹配）
- ❌ 用 Markdown 代码块（``` 或 ~~~) 包裹译文——直接以裸文本输出
- ❌ 调用 `AskUserQuestion` 等用户输入工具

**自检**（输出前默念）：
1. 我的最终消息第一个字符，是否就是译文的第一个字符？
2. 整条消息里是否一个汉字都没有（中→英场景）？
3. 是否没有任何"我做了什么 / 我打算怎么做"的元描述？

任一答否 → 删掉违规部分重写。

**优先级**：本节压过本文档其它一切规定，包括下文「首次配置阻塞」「普通模式升级提示」「Step 5 输出汇总」等强制行为，也压过 Claude Code 运行时关于"行动前说一句"的默认习惯。

## 用户输入工具

需要向用户提问时：

1. **必须先实际调用**运行时内置的用户输入工具——如 `AskUserQuestion`、`request_user_input`、`clarify`、`ask_user` 等同类等价物。**不得**在未尝试调用之前就假设工具不可用。把问题"写"到 assistant 文字里不算调用工具——必须发起一次真正的 tool call。
2. **降级仅在工具调用失败时触发**：只有当工具调用因 `tool not found` / `unknown tool` / 注册表里确无任何等价物时，才退化为"纯文本编号问题列表"方案。
3. **批量提问**：若工具支持单次多问，所有相关问题合并到一次调用；若仅支持单问，则按优先级逐个询问。

下文出现的 `AskUserQuestion` 仅作示例，请在其他运行时替换为本地等价物。

## 脚本目录

脚本位于 `scripts/` 子目录。`{baseDir}` = 本 SKILL.md 所在目录。使用 `python3`（3.8+）运行，无第三方依赖。请把 `{baseDir}` 替换为实际路径。

| 脚本 | 用途 |
|------|------|
| `scripts/main.py` | CLI 入口。默认动作是把 markdown 切分为 chunks；也支持显式 `chunk` 子命令 |
| `scripts/chunker.py` | `main.py` 调用的 markdown 分块实现，同时保持可单独调用 |
| `scripts/glossary_check.py` | 精翻 Step 4a：基于合并术语表对源文 / 初稿做术语级合规检查，输出 `glossary-check.txt` |
| `scripts/verify_output.py` | **写完译文后的确定性硬检查**（正则级，非语义）：目标语言重音字符存在性、源语言字符泄漏、占位符 / SRT 时间码源译数量一致、日期保留、`--preserve` 词字面命中。返回 JSON，P0 即 exit 1。详见下方「输出前自检」 |

## 偏好设置（PREFERENCES.md）

按下列优先级查找 PREFERENCES.md，命中第一个即用：

| 优先级 | 路径 | 作用域 |
|--------|------|--------|
| 1 | `.qoderwork-skills/translate/PREFERENCES.md` | 项目级 |
| 2 | `${XDG_CONFIG_HOME:-$HOME/.config}/qoderwork-skills/translate/PREFERENCES.md` | XDG |
| 3 | `$HOME/.qoderwork-skills/translate/PREFERENCES.md` | 用户家目录 |

| 结果 | 动作 |
|------|------|
| 已找到 | 读取、解析、应用。会话内首次使用时简短提示："正在使用 [path] 中的偏好设置。可编辑 PREFERENCES.md 自定义术语表、读者群等。" |
| 未找到 | **必须**走首次配置流程（见下方）——**不得**静默使用默认值 |

**PREFERENCES.md 支持配置**：默认目标语言、默认模式、目标读者、自定义术语表（内联或文件路径）、翻译风格、分块设置。

字段定义：[references/config/preferences-schema.md](references/config/preferences-schema.md)。

### 首次配置（阻塞操作） ⛔ STOP

> **例外**：若触发上文「静默直翻豁免」，跳过本节，直接走默认值翻译并仅输出译文。

**这是阻塞操作**：在三条候选路径都未找到 PREFERENCES.md 时，**必须先走首次配置流程，再开始任何翻译**——即使用户的请求看上去只是"翻译一句话"也不例外。

#### 显式重置语义（沙箱 / 测试环境）

若用户消息中出现下列任一表达，等同于「PREFERENCES.md 全部不存在」，**必须**忽略一切已检索到的偏好文件，重走首次配置流程：

- 『假设无 PREFERENCES.md』 / 『假设所有 PREFERENCES.md 均不存在』
- 『视为首次使用本翻译技能』 / 『按首次配置流程重新走一遍』
- `force first-time setup` / `reset preferences` / `pretend no PREFERENCES.md exists`
- 显式列出三个候选路径（项目级 / XDG / HOME）并要求忽略

#### 禁止行为（任一即视为违规）
- ❌ 直接输出译文（即使只有一个短句）
- ❌ 静默套用默认值翻译并附加 "可在 PREFERENCES.md 调整" 类提示
- ❌ 写入 `output/translation.md` 或任何译文产物
- ❌ 跳过 `AskUserQuestion`，仅以纯文本一次性自问自答
- ❌ **假装用户已回答 / 自己填默认值再写入 PREFERENCES.md**——例如『按默认选项写入 PREFERENCES.md』『假定用户选 zh-CN / normal / general / storytelling / 项目级，已保存』。本轮的最终消息**只能是提问**，不能是 "Preferences saved to ..."。除非用户在**本轮消息中已显式提供 5 项答案**，否则禁止写入 PREFERENCES.md。
- ❌ 先写 PREFERENCES.md，再补一句"请确认偏好"——顺序必须是『问 → 用户答 → 写』，不可颠倒

#### 必须行为
1. **实际调用**用户输入工具（`AskUserQuestion` / `request_user_input` / `clarify` / `ask_user` 任一），**一次调用**提出全部 5 个问题：目标语言（target_language）、模式（default_mode：quick/normal/refined）、目标读者（audience）、风格（style）、保存位置（项目级 / XDG / 家目录）。
   - ✅ 正确：发起一次 `AskUserQuestion` tool call，5 个问题作为参数传入
   - ❌ 错误：只在 assistant 文字回复里列出 "1. 目标语言... 2. 模式..."，未发起 tool call
   - ❌ 错误：未尝试调用任何工具就直接走纯文本兜底——必须先试，被运行时拒绝（`tool not found`）才允许退化
2. 在最终 assistant 消息中显式提示用户『这是首次配置，一次性完成后续不会再问』，使用关键词『首次配置』或 `preferences`。
3. 等待用户作答；**不得**在拿到回答前预先生成译文。
4. 用户答完后在选定路径创建 PREFERENCES.md，输出确认 `Preferences saved to [path]`，然后开始翻译。

完整说明：[references/config/first-time-setup.md](references/config/first-time-setup.md)

## 默认值

所有可配置项集中于此。优先级：CLI flag > PREFERENCES.md > 默认值。

| 配置项 | 默认值 | PREFERENCES.md 键 | CLI flag | 说明 |
|--------|--------|-------------------|----------|------|
| 目标语言 | `zh-CN` | `target_language` | `--to` | 翻译目标语言 |
| 模式 | `normal` | `default_mode` | `--mode` | 翻译模式 |
| 读者 | `general` | `audience` | `--audience` | 目标读者画像 |
| 风格 | `storytelling` | `style` | `--style` | 翻译风格偏好 |
| 分块阈值 | `4000` | `chunk_threshold` | — | 触发分块翻译的字数门槛 |
| 单块上限 | `5000` | `chunk_max_words` | — | 单个 chunk 的最大字数 |

**CLI flag 覆盖透明性**：当本次调用使用了与 PREFERENCES.md 不一致的 CLI flag（如 `--to ja` 覆盖了 `target_language: zh-CN`）时，**必须**在最终消息中显式说明覆盖关系，让用户清楚本次行为为何偏离了已保存的偏好。格式示例：
- 简短附注：『（使用 `--to ja` 覆盖 PREFERENCES.md 中的 `target_language=zh-CN`，输出日语）』
- 或单独一行：『**Using CLI flag** `--to ja` (overrides PREFERENCES.md `target_language=zh-CN`)』

此附注归属于"目标语言汇总"性质（参见 Step 5），**不算违反 C2** 的"开篇宣告"——它放在译文**之后**作为元信息行，且使用目标语言或源语言都可。

## 模式

| 模式 | Flag | 步骤 | 适用场景 |
|------|------|------|----------|
| 快翻 | `--mode quick` | 翻译 | 短文本、非正式内容、临时任务 |
| 普通 | `--mode normal`（默认） | 分析 → 翻译 | 文章、博客、一般内容 |
| 精翻 | `--mode refined` | 分析 → 翻译 → 审校 → 润色 | 出版级、重要文档 |

**默认模式**：普通（可在 PREFERENCES.md 的 `default_mode` 中覆盖）。

**风格预设**——控制译文的语气和声音（与读者画像独立）：

| 取值 | 名称 | 效果 |
|------|------|------|
| `storytelling` | 叙事感（默认） | 抓住读者，过渡顺滑，措辞鲜活 |
| `formal` | 正式 | 中性语气，结构清晰，无口语化 |
| `technical` | 技术文档 | 简洁、术语密集、修饰极少 |
| `literal` | 直译 | 尽量贴合原文结构，保留源句式 |
| `academic` | 学术 | 正式语域，可用复杂从句，注意引用 |
| `business` | 商务 | 简洁、结果导向、面向高管、要点思维 |
| `humorous` | 幽默 | 机智俏皮，重现原文的喜剧效果 |
| `conversational` | 口语 | 友好亲切，像在向朋友解释 |
| `elegant` | 雅致 | 文学感、节奏感、用词精雕细琢 |

也接受自定义风格描述，例如 `--style "诗意而抒情"`。

**模式自动识别**：
- "快翻", "quick", "直接翻译" → 快翻
- "精翻", "refined", "publication quality", "proofread" → 精翻
- 其他 → 默认模式（普通）

**升级提示**：普通模式完成后展示（若触发「静默直翻豁免」则跳过）：
> 译文已保存。如需进一步审校与润色，回复 "继续润色" 或 "refine"。

用户回应后，在已有输出上继续走审校 → 润色（与精翻 Step 4–6 一致，见 refined-workflow.md）。

**读者画像预设**：

| 取值 | 名称 | 效果 |
|------|------|------|
| `general` | 普通读者（默认） | 通俗用语，对术语多加译注 |
| `technical` | 开发者 / 工程师 | 常见技术词少加注 |
| `academic` | 研究人员 / 学者 | 正式语域，术语精确 |
| `business` | 商务人士 | 商业语气，技术概念加解释 |

也接受自定义读者描述，例如 `--audience "对 AI 感兴趣的普通读者"`。

## 工作流

### Step 1：加载偏好

1.1 检查 PREFERENCES.md（见上文 偏好设置 一节）

1.2 加载语言对的内置术语表（如有；未提供也不影响该方向的翻译）：
- EN→ZH：[references/glossary-en-zh.md](references/glossary-en-zh.md)
- 其他方向：依赖用户在 PREFERENCES.md `glossaries[pair]` 或 `glossary_files` 中提供

1.3 合并术语表：PREFERENCES.md `glossary`（内联）+ PREFERENCES.md `glossary_files`（外部文件，路径相对 PREFERENCES.md 所在位置）+ 内置术语表 + `--glossary` 文件（CLI 覆盖前述全部）

### Step 2：物化源文 & 创建输出目录

物化源文（文件保持原样；内联文本 / URL → 保存到 `translate/{slug}.md`），然后创建输出目录：`{source-dir}/{source-basename}-{target-lang}/`。若未指定 `--from`，则自动检测源语言。

完整规范：[references/workflow-mechanics.md](references/workflow-mechanics.md)

**输出目录内容**（所有中间文件与最终文件均在此）：

| 文件 | 适用模式 | 说明 |
|------|----------|------|
| `translation.md` | 全部 | 最终译文（始终用此名） |
| `analysis.md` | 普通 / 精翻 | 内容分析（领域、语气、术语） |
| `prompt.md` | 普通 / 精翻 | 组装好的翻译提示词 |
| `draft.md` | 精翻 | 审校前的初稿 |
| `glossary-check.txt` | 精翻 | Step 4a：术语合规报告（脚本生成） |
| `review.md` | 精翻 | Step 4b：独立审校发现，按 P0/P1/P2 分级 |
| `back-translation.md` | 精翻 | Step 4c：抽样回译 |
| `revision.md` | 精翻 | 修订稿（第 1 轮） |
| `review-round{N}.md` / `revision-round{N}.md` | 精翻 | Step 5b 迭代文件（N=2，必要时 3）；仅在审校 gate 未通过时生成 |
| `chunks/` | 长文 | 源 chunks + 译文 chunks |

### Step 3：评估内容长度

快翻不分块——无论长短直接翻译。开始前先估算字数。若内容超过分块阈值（默认 4000 字），主动提醒：
> 本文约 {N} 字。快翻模式不分块，一次性翻译；长文建议改用 `--mode normal`，能更好保证术语一致性。

如果用户不切换则继续。

普通和精翻模式：

| 内容 | 动作 |
|------|------|
| < 分块阈值 | 整体翻译 |
| ≥ 分块阈值 | 分块翻译（见 Step 3.1） |

**3.1 长文准备**（仅普通 / 精翻模式且 ≥ 分块阈值时）

翻译 chunks 之前：

1. **抽取术语**：扫描整篇文档的专有名词、技术术语、高频短语
2. **构建会话术语表**：将抽取出的术语并入已加载术语表，确立一致译法
3. **切分 chunks**：`python3 {baseDir}/scripts/main.py <file> [--max-words <chunk_max_words>] [--output-dir <output-dir>]`
   - 解析 markdown 块（标题、段落、列表、代码块、表格等）
   - 在 markdown 块边界处切分，保留结构
   - 单块超阈值时，回退到按行切分，再按词切分
4. **组装翻译提示词**：
   - 主 Agent 读取 `analysis.md`（如有），用 [references/subagent-prompt-template.md](references/subagent-prompt-template.md) 的 Part 1 组装共享上下文，内联：目标风格、内容背景、合并术语表、翻译难点
   - 保存为输出目录下的 `prompt.md`（仅含共享上下文，不含任务指令）
5. **通过子 Agent 起稿**（如运行时支持 Agent 工具）：
   - 每个 chunk 一个子 Agent，全部并行（模板 Part 2）
   - 每个子 Agent 读 `prompt.md` 获取共享上下文，接收 chunk 位置信息（第 N 块 / 共 M 块 + 在论证中的简要位置），翻译该 chunk，保存到 `chunks/chunk-NN-draft.md`
   - 一致性由共享 `prompt.md` 保障（术语表、修辞映射、理解难点、原文声音、来自分析的翻译难点）
   - 若内容未达阈值（无 chunks）：起一个子 Agent 翻译整份源文
   - 若 Agent 工具不可用：用 `prompt.md` 串行翻译各 chunk
6. **合并**：所有子 Agent 完成后按序合并译文。若存在 `chunks/frontmatter.md` 则前置。保存为 `draft.md`（精翻）或 `translation.md`（普通）
7. 所有中间文件（源 chunks + 译文 chunks）保留在 `chunks/`

**分块初稿合并后**，将控制权交还主 Agent，进入 Step 4 的审校、修订、润色。

### Step 4：翻译与精修

**翻译原则**（适用全部模式）：

- **译文消息开头不得有任何 plan-narration / 元信息**（全局硬规则，不限模式、不限文本长度）：最终 assistant 消息要么直接以**译文首字符**开头，要么以本节后续允许的目标语言汇总（如 Step 5 "翻译完成" 用目标语言写的简短汇总，且未触发静默直翻豁免时）开头。**禁止**任何"开篇宣告"或元信息行——以下示例全部违规：
  - ❌ 『根据您的要求，以下是工业级光纤激光切割机产品页的德语翻译：』
  - ❌ 『以下是 xxx 的英文翻译：』『以下是翻译结果：』『Here is the translation:』
  - ❌ 『源文：xxx / 目标语言：英文 / 模式：快翻』之类的"输入参数确认行"
  - ❌ 『我将使用快翻模式直接翻译：』之类的"动作宣告"
  - ❌ Markdown 代码块包裹（``` 或 ~~~）译文 —— 直接裸文本输出
  - ✅ 正确：消息第一个字符就是译文第一个字符（如 `# Handling Concurrent Requests with asyncio` 或 `Hi,\n\nRegarding order ...`）

  本规则与「静默直翻豁免」叠加而非替代——豁免节给出更严的"连汇总也不要"，本规则给出 **全模式下** 的最低线：译文前不得有 plan-narration。
- **重写而非翻译**：把内容用自然、有吸引力的目标语言重新写一遍，仿佛由本族语母语作者从零创作。质量自检："读起来像不像目标语言原创？"
- **准确为先**：事实、数据、逻辑必须与原文严格一致
- **自然流畅**：使用目标语言地道的语序。把过长的源句拆成自然的短句。隐喻和习语按意译处理，不逐字直译
- **术语**：使用标准译法，前后一致。专业术语首次出现时附原文括注
- **用户即席保留指令（最高优先级）**：用户消息中『xxx 保留原文』『xxx 保留』『xxx 不要翻译』『xxx 不要本地化』『keep xxx as-is』『preserve xxx』『xxx unchanged』等同义指令，**视同最高优先级会话术语表条目**——必须**字面**保留这些词的原文形态，禁止任何形式的转写 / 音译 / 改写，**即使目标语言里转写更自然也不行**。
  - 例：用户说 "PvP / Boss 保留原文" → 译文中必须出现字面 `Boss`，不可写作 `보스`（韩）/ `ボス`（日）/ `Босс`（俄）等转写形态
  - 例：用户说 "iPhone 不要翻译" → 不可写作 `아이폰` / `アイフォン` / `айфон`
  - **自检**：完成翻译后，对用户列出的所有"保留"项逐个 grep 检查，确认每一项都以字面形态出现在译文中；任一缺失则改写。
- **用户即席语用指令（最高优先级）**：用户消息中对语用形式的指定，与"保留原文"同级别强制——必须落实到译文每一处适用位置，不可遗漏。常见类型：
  - **敬称 / 人称**：『使用 Sie 形式』『use Sie / vous / 您』『避免 du / tu / 你』『B2B 语气』→ 全文统一用敬称，绝不混入随意人称
  - **敬体 / 文体**：『用 です・ます 体』『不加敬语』『书面语』『口语』→ 句末活用形式必须一致
  - **正式度**：『正式』『formal』『casual』『口语化』→ 词汇与句式风格一致
  - **称谓**：『以"客户"称呼读者』『不用第二人称』→ 按指令调整
  - **自检**：完成翻译后，对用户列出的每条语用指令做一次扫描——例如『Sie 形式』就 grep `Sie / Ihre / Ihnen`，且确认没有 `du / dein / dir`；若一处都没命中或出现禁用形式，改写。
- **保留格式**：保留所有 markdown **标记符号**（`#` / `##` / `**` / `_` / `![]()` / `[]()` / ``` ``` ```）和结构，但 **标记符号内部的文字内容必须翻译为目标语言**。例如源文 `## 卖点` → 译文 `## セールスポイント`（保留 `## `，翻译 `卖点`）；切勿误读为"标题文字也保留"
- **保留占位符与格式化标记**（与上一条同级别强制，常被忽视）：所有占位符 / 格式化标记必须**逐字逐数量**保留在译文相应语义位置，禁止遗漏、改写、转义或合并：
  - iOS / Objective-C：`%@` `%d` `%lld` `%1$@` `%2$d`
  - printf 系：`%s` `%d` `%f` `%05.2f` `%c`
  - Android / Java：`%1$s` `%2$d`
  - ICU / 现代 i18n：`{0}` `{1}` `{name}` `{count,plural,one{...} other{...}}`
  - Web / 模板：`{{var}}` `${var}` `<x:placeholder/>` `<1>...</1>`
  - 通用：`\n` `\t` `\r` `&nbsp;` `<br/>`
  - **自检**：完成翻译后，对源文与译文分别 grep 各类占位符——**种类、数量、顺序必须完全一致**。若源文有两处 `%@`，译文必须也有两处 `%@`；若源文 `{0}` 在前 `{1}` 在后，译文不可颠倒（除非目标语言语序确实需要颠倒——此时确认占位符仍指向正确变量）。
  - **典型违规**：iOS strings 文件 `"battery.level" = "Battery (%@)";` 译成 `"battery.level" = "电量 ()";`——`%@` 被丢弃，运行时会产生 `电量 ()` 空括号。
- **翻译是替换，不是追加**：译文应当**替换**源文，不得以"源文 → 译文"并列形式出现。除非用户明确要求双语对照，否则禁止：
  - ❌ 双语标题：`# 使用 asyncio 处理并发请求 → Handling Concurrent Requests with asyncio`
  - ❌ 双语段落：`原文：xxx / 译文：yyy` 并列
  - ❌ 在译文后括注源文（专有名词首次出现时的术语括注是例外，遵循「术语」规则）
  - ✅ 正确：`# Handling Concurrent Requests with asyncio`（只出现一次，纯目标语言）
- **可见文本全部翻译**：所有面向读者的可见文字都必须翻译为目标语言，包括但不限于：
  - 小节标题（H1–H6、`**加粗标题**`）
  - 行内标签（如源文中 `卖点：xxx`、`商品名：xxx` 这类冒号前的引导词）
  - 表格表头与单元格
  - 图片 alt 文本与图注
  - 按钮 / 链接锚文本
  - 列表项文本
  - YAML frontmatter 中的可见字段值（按 frontmatter 规则处理）

  **唯一可保留源语言形态的项**：① 专有名词、品牌、人名、商品型号；② 技术缩写 / 代码 / 命令（如 `IPX7`、`USB`、`curl`）；③ 术语表中显式标记为"保留"的词；④ 数字（除非要本地化为目标语言数字写法）。
- **输出语种自检**（写完译文必做）：从头扫一遍最终输出，凡出现源语言独有字符且不属于上述四类豁免项的，一律改写为目标语言。中→日时，特别注意是否漏译了 `## 卖点` `## 详情` 之类标题，或 `卖点：` `详情：` 之类行内标签
- **目标语言字符层自然度自检**：写完后扫一遍——目标语言的常见特征字符应当自然出现。若几句话以上的输出里 **一个特征字符都没有**，多半是"工程感"翻译，重新润色。各语言的特征字符清单：
  - **意大利语**：`è` / `à` / `é` / `ì` / `ò` / `ù`（高频：`è`、`più`、`qualità`、`città`、`già`）
  - **法语**：`é` / `è` / `ê` / `à` / `ç` / `ô`（高频：`être`、`à`、`également`、`déjà`）
  - **德语**：`ä` / `ö` / `ü` / `ß`（高频：`für`、`über`、`größer`、`heißen`）
  - **西班牙语**：`á` / `é` / `í` / `ó` / `ú` / `ñ` / `¿` / `¡`（高频：`más`、`español`、`año`）
  - **葡萄牙语**：`ã` / `õ` / `ç` / `á` / `é`（高频：`não`、`são`、`ação`）
  - **日语**：平假名 + 片假名 + 汉字三种混排（高频：`の`、`を`、`は`、`です`、`ます`），长音符 `ー`、促音 `っ`
  - **韩语**：连续韩文音节（`[가-힣]`），无连续 ≥ 3 个韩文字符的输出多半是漏译
  - **俄语**：西里尔字母（`[а-я]` / `[А-Я]`），全英文输出说明译漏
  - **阿语**：阿拉伯字母（`[؀-ۿ]`）应占主体
  仅 1-2 句的短输出可豁免；多句段落或列表里全无特征字符 → 改写以引入更地道的句式（例如意语用 `è` 改写"是"类系动词、用 `più` 替代英式短语）
- **主动解释**：对目标读者可能缺乏背景的术语 / 概念，用 **加粗括号** 加简短解释 `（**解释**）`。批注宁少勿多，仅在确实影响理解时使用
- **Frontmatter**：若源文带 YAML frontmatter，把源文元数据字段加 `source` 前缀（驼峰式：`url`→`sourceUrl`、`title`→`sourceTitle` 等），新增对应译文字段在顶层（若正文已有 H1，则跳过 `title`），其他字段保持不变

#### 快翻

直接翻译 → 保存为 `translation.md`（若触发「静默直翻豁免」则不保存文件）。应用上述全部翻译原则。

**快翻最终消息硬约束**：
- 只含译文本身，**绝不可出现工作流元词汇**——以下任一关键字出现在 assistant 消息中即视为违规：`draft` / `review` / `revision` / `revise` / `back-translation` / `analysis` / `分析` / `审校` / `润色` / `精翻` / `初稿` / `修订稿`
- 不附加『说明』『翻译笔记』『以下采用快翻模式』『为了保证质量我先分析了...』等任何元叙述段落
- 不引用源文、不双语对照（除非用户要求）
- 若用户在请求中显式列出了"禁止出现的关键字"，快翻模式默认包含上面整套禁词列表

#### 普通模式

1. **分析** → `analysis.md`（领域、语气、术语、翻译难点）
2. **组装提示词** → `prompt.md`（带上下文、术语表、难点的翻译指令）
3. **翻译**（遵循 `prompt.md`）→ `translation.md`

完成后向用户提示："译文已保存。如需进一步审校与润色，回复 **继续润色** 或 **refine**。"

如用户继续，则进入审校 → 修订 → 润色（与精翻 Step 4–6 一致），保存 `draft.md`（把当前 `translation.md` 改名）、`review.md`、`revision.md`，并更新 `translation.md`。

#### 精翻

面向出版级的完整流程。详见 [references/refined-workflow.md](references/refined-workflow.md) 与审校提示词模板 [references/reviewer-subagent-prompt.md](references/reviewer-subagent-prompt.md)。

三个独立子 Agent 角色：**起草者**（Step 3）、**审校者**（Step 4b，对抗式——对起草者的推理盲读）、**回译者**（Step 4c，抽样句子）。主 Agent 负责编排和应用修订。

步骤与产出文件（均位于输出目录）：
1. **分析** → `analysis.md`
2. **组装提示词** → `prompt.md`
3. **起稿** → `draft.md`（起草者子 Agent）
4. **关键审校**（三部分）：
   - **4a 术语检查** → `glossary-check.txt`（脚本，确定性结果）
   - **4b 独立审校** → `review.md`（按 P0/P1/P2 分级）
   - **4c 回译** → `back-translation.md`；漂移项归并入 `review.md`
5. **修订** → `revision.md`。**迭代 gate**：在修订稿上重新启动审校；若仍有 P0/P1，再修订一次（最多 2 轮）。达到上限后，先把剩余问题反馈给用户再润色
6. **润色** → `translation.md`

每一步读取上一步的产物并继续构建。

### Step 5：输出

> **例外**：若触发「静默直翻豁免」，跳过本节全部步骤（不汇总、不图片巡检、不创建文件），最终消息仅输出译文本身。

最终译文始终位于输出目录的 `translation.md`。

写完最终译文后，做一次轻量的图片语种巡检：

1. 收集译文中的图片引用
2. 识别可能富含文字的图片：封面、截图、流程图、图表、框架图、信息图等
3. 若图中主文字语种可能与译文语种不一致，主动提醒用户
4. 提醒只能是清单，**不要**自动本地化图片，除非用户要求

提醒格式（沿用文章已有的图片语法——标准 markdown 或 wikilink 均可）：
```text
可能需要图片本地化：
- ![example cover](attachments/example-cover.png)：封面文字可能仍是源语言，而正文已切换为目标语言
- ![example diagram](attachments/example-diagram.png)：含较多文字的框架图，标签可能需要翻译
```

输出汇总：
```
**翻译完成**（{mode} 模式）

源文件：{source-path}
语言：{from} → {to}
输出目录：{output-dir}/
最终译文：{output-dir}/translation.md
应用术语数：{count}
```

若发现图片语种不匹配的候选项，则在汇总后追加一段简短提示，告知用户部分图片可能仍需做图文本地化，并附上候选清单。

## 扩展支持

通过 PREFERENCES.md 自定义配置。路径与字段见上文 **偏好设置** 一节。
