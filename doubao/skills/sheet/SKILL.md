---
name: sheet
version: 3.8.0
description: "表格全场景（本地Excel/CSV与飞书/doubao在线表格）：创建、读写、分析、计算、财务建模、语义处理、可视化与美化。若用户上传附件、提供表格链接/token，或要求任何表格操作，必须加载。"
metadata:
  requires:
    bins: ["lark-cli", "python3"]
  cliHelp: "lark-cli sheets --help"
---
> ⚠️ **强制前置条件**：本文档共 236 行，指令与约束分散在各处。必须读到末行「全文完」再执行任何其它操作——即使已找到当前所需的指令也不得提前停止；未见该标记前不得调用 Bash、`--help` 或任何其它工具，被截断就调整 `offset` 续读。本技能所有文档末行均有该标记。

# 表格全场景处理技能（sheet）

覆盖本地 Excel 文件与飞书在线表格的全场景处理。**本技能不负责获取外部信息**（标准值、行情、法规参数），需要时先由其他途径取得。

## 0. 先确定模式，再读业务 reference

**按本轮完整需求分流，再加载业务 reference 或启动门禁。** 必要数据读取和环境兼容说明可先完成；用户要求的核验始终执行。

1. **确认入口**：本轮 `<system-reminder>` 的 `<current-state>` 直接指定 `references/mode-speed-first.md` 时，先读该文件，按“直接指定”执行；不再判断任务难度。从本 SKILL 进入时，继续下面的判断。
2. **自动分流时，既有产物编辑走标准**：在现有工作簿、模板或上一轮产物上继续写入、整理或修复，包括同一工作簿新增结果 sheet、另存编辑副本；不因只改少量单元格、规则明确或公式已给定而降级。仅把原表作为只读数据源、另建独立产物不属于编辑原表。
3. **以下任务也走标准，方法与公式已给定也适用**：用户要求复核、校验、审计或验收；统计推断（显著性检验、回归估计、预测区间等）；回测、跨期模拟、多指标时序风险分析或需先估计模型再预测；外部事实核查、开放式语义判断、口径推断、异常溯源、全面勾稽或影响不明的删改。
4. **排除上述标准任务后，其余任务同时满足以下条件才走速度优先**：

| 条件 | 判断标准 |
| --- | --- |
| 规则明确 | 输入结构、字段映射、口径与范围已确认；关联键的重复及未匹配项处理已知，不自行补设业务口径。 |
| 计算直接 | 新建独立产物中的逐行公式、普通公式串联、固定键关联、给定分组 / 分箱汇总、同构数据合并或常规图表；不包含对既有产物的编辑。 |
| 基础校验足够 | 一组覆盖各规则与受影响子表的样本，即可核对关键值、公式及数据完整性。 |

信息不足先做必要读取，仍不确定走标准。标准任务排除条件优先于三项快速条件；职业称谓、金融字段、文件格式、表数与步骤数不单独决定模式，不因当前只在填表而降低整题的核验要求。

**自动分流到速度优先后，立即读 [mode-speed-first.md](references/mode-speed-first.md)**，按“SKILL 自动分流”执行，不叠加后文标准模式的必读和门禁；只有触发该 reference 的升级条件才切换。环境兼容、数据保护、授权、保存和交付照常；后续轮次重新判断。

## 一、通用流程（两套引擎都适用）

本章不分引擎：**① 判运行环境 → ② 选引擎 → ③ 定交付形态 → ④ 执行与交付**。环境兼容、引擎、备份、保存与交付要求两种模式通用；reference 加载与校验步骤按所选模式执行。

### 1. 运行环境（决定交付形态，也决定开工前的必读 reference）

根据 `<system-reminder>`（下称SR） 注入内容判断运行环境，多轮会话时上下文可能存在多个 SR，只看最后一个包含 `Main project directory` 字段的 SR，更早的 SR 注入的字段不作为依据：

1. 存在 `Computer OS` 字段时：值为 `Windows` / `Mac` 判为**本地电脑**，值为其他判为云电脑。
2. 无 `Computer OS` 字段时看 `Main project directory` 字段：Linux 路径`/home/user/Doubao/…`判为云电脑；值为其他，如 Mac 路径`/Users/…`、Windows 路径 `C:\…` 判为**本地电脑**。

判为本地电脑、或两条都判不出时（判不出只放宽读 reference 的门槛，交付形态仍按上面两条判、判不出按云电脑），读完本 SKILL 后**必须先完整 Read `references/ref-local-compat.md`**；`Computer OS: Windows` 或者 `Main project directory` 为 Windows 路径的会话（依据上面同一个 SR），读完它**再完整 Read `references/ref-windows-compat.md`**——无论后续是否执行 lark-cli，跳过会大面积报错。

**本地电脑分支**：SR 会注入 `file_status` / `token` 等 canvas 字段（没被打开过的文件不带），字段全表、失败判定与三态分支见 `references/ref-local-compat.md`。读它之前先记住一条：**Canvas 打开时**改动只落在工作目录的底层产物上，不写回用户真实本地文件、也不用 `lark-cli` 导出，交付用户提供的原文件路径并提醒自行保存；**Canvas 未打开时**（从未打开、或打开过又关闭）按第 2 节走 Excel 引擎，改动就地落在用户的真实文件上（打开过的按 `path` 定位）。

### 2. 选引擎（按数据在哪，与交付形态无关）

**AI 分流服从兼容与交付规则**：以下 AI 分流仅用于标准模式。本地电脑上编辑本地表格文件时，视为未命中 AI 分流，跳过下述「用户边界优先」「按结果区域分流」「必须先完成结果判断」「AI 分支先读再生成」四段，按下方引擎规则执行，不新增 `AI()`。AI 分流服从已选模式、用户边界、数据保护、保存和交付要求；AI 状态与失败处置按 `references/lark-sheets-ai-formula-monitoring.md` 执行。

**用户边界优先**：用户明确要求仅本地处理、不得上传或拒绝在线表格时，不转在线；禁用 AI 公式只排除 `AI()`，普通公式仍可用。

**按结果区域分流**：满足上述前提时，逐行独立的语义判断、翻译或生成用 `=AI(...)`，含已有空白列；其中同格覆盖、同格双语和原位置翻译先在独立计算区求值，验收后回写原格。混合任务将语义生成与清洗、行号映射、格式回写分别判断，不因分步处理、保留格式或业务委派而跳过语义区域。明确机械规则或用户完整映射可直接求解时用确定性方法；自行语义判断后制成答案表或词典不算此例外。

**必须先完成结果判断**：选引擎前按区域在现有计划或执行说明中记录：`结果判断：<结果区域>；需语义理解=<是/否>；用AI公式=<是/否>；需AI真值=<是/否>`。不用 AI 公式须注明适用边界或确定性规则的依据，历史 pending 不证明本轮能力不可用。原位回写、根据 AI 结果筛选汇总、导出真实值或用户明确要求核验 AI 结果时，需 AI 真值为是；仅交付动态公式为否，不因自行增加抽检、试点或产出而改判。信息不足先只读预检，补齐判断后才生成业务结果。业务委派须交接已有判断与本分流规则；尚未判断的由业务执行方先完成，写入与验收职责按监控 reference 执行。

**AI 分支先读再生成**：判为 AI 后，先完整 Read `references/lark-sheets-formula-translation.md` 和 `references/lark-sheets-ai-formula-monitoring.md`；可定口径、整理输入，不预生成整批答案。无在线 token 且交付契约允许导入的源表，按原流程预检、校验并导入。写后按监控 reference 分流：**无需 AI 真值时，不设出值试点，铺完全部目标、首检通过即保留公式交付，允许 pending，不再观察或据此降级；需 AI 真值时，监控完成后再读值及执行后续操作**。其他区域按下述数据位置选引擎。

- **Excel 引擎**（Python + openpyxl + `scripts/`）：未命中上述 AI 分流的区域，**本轮从零新建**（没有源表、没有在线表可改），或用户提供本地表格文件（上传附件或给出路径，`.xlsx` / `.xls` / `.csv`）且没有在线链接。按「开工纪律」的 Excel 引擎路径走；需在线原生透视 / 图表 / 条件格式时，导入后用对应 CLI 创建或维护所需对象，已有可用对象直接复用；导入成功不证明所需对象齐全。
- **飞书表格引擎**（`lark-cli sheets`）：用户给出 `/sheets/`、`/spreadsheets/`、或指向电子表格的 `/wiki/` 链接，或飞书表格 token。按 URL 路径 / token 判定，不看域名。

**例外**：本地电脑上被 Canvas 模式打开（`file_status` 为 `open`）的本地表格文件，编辑一律走飞书表格引擎，`lark-cli sheets` 以 `--spreadsheet-token <token>` 定位（不是 `--url`），可回滚、编辑状态实时可见。**本地电脑上**用 Excel 引擎编辑本地文件时 Python 改动不可回滚，动手前先**复制一份备份**；编辑落在原文件上，备份只做回滚快照——期间不更新、不交付，交付门禁拿它当基准。

两套引擎经 `+workbook-import` 打通：Excel 引擎的产物汇入飞书表格，交付形态按第 3 节判。

### 3. 交付契约（动手前先读完，它就是验收标准）

**产物载体**：先按下面两条定形态，再看例外。

- **交飞书表格**（云电脑的新建与编辑、本地电脑的新建；导入不支持元素按下文处理）：默认交**飞书表格**，校验按已选模式执行。用户说"做个 Excel""给我个表""整理成表格""输出 Excel 格式 / .xlsx""可下载的 Excel 文件""原表格 / 原文件"、引用已有表格文件或任何预期输出表格产物，都走这条——**本地 xlsx 默认只是中间产物，必须 `+workbook-import` 导入再交付**；导入重试一次仍失败时改交本地文件并写明原因。无需按下文保留 Excel 时，导入后只交飞书链接，不重复附带 xlsx；继续做完用户要求的全部操作，不可导入即停。
- **交本地文件路径**（本地电脑的编辑场景）：交付物与编辑对象同形态——改飞书表格就交飞书表格，**改本地文件就交本地文件路径，无需导入飞书**；交本地文件时**不得把 `token` 拼成在线链接**当产物给出。

> **例外（两条都适用）**：用户明确表态时按用户的来——**明确拒绝**在线表格（"不要飞书表格""不要在线链接""给我 .csv 就行"）就改交本地文件；本地电脑改本地文件时用户**明确要在线表格 / 飞书链接**，就导入后交在线表；明确说"两个都要"时两者都交。第一条枚举的那些说法只是要产物、不是拒绝在线，仍按默认规则处理；处理不支持元素时，也可按下文交完整 Excel 或双交。Canvas 打开时，须先由用户保存、取得已保存的真实文件再导入，不导出底层产物或导入未保存的旧文件。

**导入后必须检查 `data.extra`**：`+workbook-import` 返回成功仍可能有损。已确认导入或导出使用户要求保留的格式 / 功能发生变化时，同样按此分支处理，不以 `data.extra` 是否列出为条件。所有不支持元素按同一原则处理：有能满足需求且改动合理的方案时，尽量采用兼容替代，但不强制替换。选择替代时修改 Excel 副本，重新过本地门禁并导入，复查新回执与受影响内容，用最终新链接交付；无法满足需求或不适合替代时，可交付包含本轮全部成果、保留原元素的完整 Excel，也可双交并说明在线版差异。不得为消除提示删掉必需内容，也不得从有损在线表导出文件冒充完整 Excel。可参考 `references/lark-sheets-workbook.md` 的替代示例，按实际内容、功能和改动成本选择。

**分析类任务同样交表格产物**：用户只要文字结论（对比、排查、归因、建议）时，结论也要落进产物本身（结果 sheet 的摘要区或独立说明块），再按上面两条交付——只写在回复正文里等于没交付。HTML / 图片报告只能附加，替代不了表格产物。

**文件名**：用户点名文件名时沿用（工作簿标题去扩展名、附件名保留全名、`/` 换 `-`），不自拟；已有表不因此改名。

**每轮必交**：本轮只要对飞书表格写入 / 编辑 / 更新过就必须按上述载体规则交付——数据来自文件 / 聊天记录 / 搜索结果 / 口述都算，本地 Excel 处理后导入也算。**跨轮同样要交**：同一张表前序轮次已交付过、URL 没变，本轮再改动后仍要重新交付最终 URL，不以“用户已打开表格”或“没有新文件”为由省略，也不得复用旧卡片或只提示刷新。**交付渠道只有一条**：飞书链接和本地文件路径都通过宿主的**产物交付工具**交出去——当前宿主是 `present_files`，参数按它自己的工具说明填；工具列表里换了名字时，取那个自述用于把最终产物交给用户的工具。**判据是这次调用真的发生并成功**：回执会列出交付了哪些条目，没调用或调用失败就是没交付、重发一次；把 URL 写进回复正文、或在回复里写「已交付」都不算。**工具交付时不重复贴产物 URL**：产物 URL 只填工具参数，调用前后的回复文本（包括进度说明和最终回复）均不输出裸 URL 或 Markdown 超链接；用产物名称说明结果与必要提醒。用户说“返回链接”也通过产物卡片满足。宿主未提供该能力或调用明确报工具不存在时，在正文给出最终 URL / 路径。在线编辑任务交付后不导出验证。

**标准模式交付前跑自检拿到可交付信号**：`需AI真值=否` 的 AI 区域以首次状态检查为交付门禁，不追加自检或检查点；其他改动仍按本段执行。

**产物是飞书表格时：交付前跑单轮在线自检**。在最后一次写入后执行：

```bash
python3 scripts/lark_sheet_selfcheck.py "<url或token>"
```

以 stdout 结论为准，**退出码 0 不代表通过**：`CHECK_DEFECTS` 表示有确定性错误，在本轮允许改动的范围内修根因，每处错误都要在产物内追到错源改正；`CHECK_INCOMPLETE` 按输出补查或重试一次，仍未完成就写进交付说明；`CHECK_PASS` 只表示规则扫描未命中确定性错误。三种结果都要按输出清单核对计算结果、原表保护和用户点名的产出项，关键结果须回读并与用户给定值或独立复算值对账。若修复或核对过程中修改了产物，在最后一次写入后重新自检。修不完的非确定性问题、或修复会波及用户没点到的范围时，写进交付说明照常交付，不进入反复修复循环。

**产物是本地文件时**，按下方「开工纪律」的 xlsx / CSV 交付门禁校验，不跑在线自检；**编辑已有 xlsx 时带上 `--baseline <改前快照.xlsx> --scope '<允许改动的范围>'`**，比对范围外的值 / 公式；scope 写前固定，不从改后产物反推或放大。比对通过不代表样式、验证与结构保持，须按本轮保护要求另对源核验。编辑已有 CSV 时使用 `--baseline <改前快照.csv>`，不传 --scope。**标准模式本地文件把用户点名的数和产出项写成检查点，交给工具判**：校验脚本接 `--checkpoints`，条目给格址加期望值、必须由公式驱动的 xlsx 区域、或必须存在的 xlsx 子表名，工具回读产物逐条对，不符按确定性错误报出来。期望值从用户要求和原始输入独立推导，覆盖规则例外与边界；不得抄产物数值或复用生成逻辑充当独立预期。

### 4. 开工纪律（执行期）

**语义结果质量**：默认保留源文本及行列对应，同格修改按用户要求；内部保留来源映射，未要求的溯源列不强加到结果表。清理前明确字符集合与位置，逐字匹配时不自动 trim 或删改字符，保留要求的换行；按本轮任务区分转换与保留；需保留的结构标签、链接和占位符复用原串；术语按给定来源统一，另核译文含义，不以“回读等于待写入文本”替代语义校对。字段缺失按约定处理，不丢整条记录或把未知数值自动补 0。原文提取仅取指定同行源格的连续片段，未限定数量时列全匹配项，确认无目标才留空；结果可读后全量核对提取来源、实体边界与含义完整性，不用随机抽样代替；未声明穷举的示例不作类别白名单，不擅设长度上限截短名称。跨列取材仅在任务允许时使用。分类先统一标签、同义标签和未知项口径，各行复用；实体、数字或日期参与分类定义时不归一化掉。记录匹配按任务约定的键核验，不用主题相似度覆盖属性冲突；检查各类结果及边界、歧义、未匹配项。翻译、总结和改写按用户格式及业务要求验收，核对含义和事实与来源一致，不套连续片段判据。上述结果验收不适用于 `需AI真值=否` 的 AI 区域。

**图表标签（两套引擎都适用）**：折线图及组合图中的折线系列默认关闭整系列的逐点标签，仅用户明确要求时开启；末点、峰值、关键点等单点标签可按展示需要单独设置。

**附件读取**：下载后验字节数与魔数，失败重试后用导入兜底；未读入的事实不得用常识或别的文件替代，缺口留空说明。中间文件走 workspace 相对路径。

**Excel 引擎路径**：聚合前确认并剔除汇总行，避免重复统计。**标准模式**按“预检 → 处理 → 交付门禁 → 导入（如需）与交付”执行：源文件读取、保护及本地 xlsx 校验 / 重算按 `references/guide-execution-flow.md`；涉及格式 / 布局时读 `references/ref-excel-visual-standards.md`。**速度优先模式**按 `references/mode-speed-first.md` 决定读取与校验。文件打不开、必交项缺失，或已执行的校验发现确定性错误，都不能声称完成。

**LibreOffice 只经脚本调用，两种模式都适用**：不直接执行 `soffice` / `libreoffice` / `unoconv`，也不 `pkill soffice`——裸命令落在共享 profile，一次中断后续启动全失败。核对公式算出的值用 `excel_formula_verify.py --checkpoints`，要拿值另作他用加 `--recalc-output`；转 PDF / PNG / CSV / xlsx 用 `python3 scripts/excel_lo_convert.py <文件> <格式> --outdir <目录>`（png 只渲染一个子表的首页、csv 只导出一个子表，默认第一个可见子表，`--sheet` 选子表，产物路径以 stdout JSON 的 `output` 为准）。退出 4 时按 stderr 处置（转换脚本的 4 即没有 LibreOffice）。速度优先模式默认不做本地重算与渲染预览，用户明确要求验证时除外。

**以下 Excel / CSV 交付门禁仅在标准模式下默认执行**：一条命令查完公式重算、新函数前缀、数组形状、静态值嫌疑和源表是否被改写。

```bash
python3 scripts/excel_formula_verify.py ./output.xlsx 60   # 从零新建：没有源可比
python3 scripts/excel_formula_verify.py ./output.xlsx 60 --baseline ./改前快照.xlsx --scope '明细!G:I'   # 编辑已有：范围动手前定下
python3 scripts/excel_csv_verify.py ./output.csv --baseline ./改前快照.csv   # 产物是 CSV：换这道，上面那个读不了 csv
```

改前快照是动手前那份没被改动的工作簿：结果另存新文件时它就是源文件本身，就地改原文件时它是动手前复制的那份备份。

退出 0 表示校验通过；**退出 3 是确定性错误**，修完重跑；**退出 4 是重算未完成或诊断信号**，按 stderr 处理并说明，不反复重跑。**本地电脑缺少 LibreOffice 时按 `references/ref-local-compat.md` 降级**：保留静态检查，计算结果用现有引擎核验或标为未验证；不为校验安装 LibreOffice 或改变交付载体。用户明确要求的验收缺项仍须说明，不用同源复算或公式计数冒充验证。**编辑已有工作簿在源工作簿上改**，不要新建空工作簿覆盖源表。

**标准模式的 CSV 产物改用 `excel_csv_verify.py`**：CSV 没有公式也没有子表，上面那道门禁连文件都读不开。它查编码与 BOM、逐行字段数、表头与行数、长数字被转成科学计数或前导零被吃掉；`--expect-rows` / `--expect-headers` 写用户点名的结构，`--checkpoints` 协议相同。退出码同一套分档。

**Must-CLI 桥接**：产物交飞书表格时，透视表 / 图表 / 单元格图片 / 迷你图先导入（有附件用 `+workbook-import`，无附件用 `+workbook-create`）再用 `lark-cli sheets` 就地创建。走「本地 Python 生成 xlsx → 导入」会让透视表退化成普通数据区、单元格图片变浮动图、图表变静态图——都不随源数据更新、也没有交互；判据是最终对象能被 `+pivot-list` / `+chart-list` 这类列举命令返回，返回不了就是没做出来。速查表没列的子选项（中位数汇总 / 计算字段 / 面积图 / 胜负迷你图等）多数原生支持，先查对应 reference，别凭「没列」判不支持就绕路。

## 二、标准模式动手前必读的 References

> **仅标准模式执行本节的强制预读**：按当前动作读完所有命中行的 reference，再执行对应操作。**速度优先模式跳过本表的强制预读，按 `references/mode-speed-first.md` 决定需要读什么**；不要先加载本表文档再回头分流。环境兼容说明仍按第一节读取。所有 reference 都在 `references/` 下；对象操作按「三」速查表查命令。

| 引擎 | 触发条件（命中就先读） | 读这份 |
| --- | --- | --- |
| **通用** | 打开已有表格（附件 / 飞书链接）做任何操作——编辑、整理、补齐、分析、汇总、生成结果表都算 | `references/guide-execution-flow.md`——用户没点落点时结果写新 sheet、原 sheet 一张不删，已有表 + 新数据 = **追加**、原有行一行不丢；用户点名要就地改 / 补齐 / 替换 / 删除时，按其授权在原表改 |
| 通用 | 表内承载财务数据（营收 / 成本 / 利润 / 损益 / 现金流 / 估值 / DCF / 三张表 / 预算 / 税务 / 纳税 / 发票 / 审计 / 折旧 / 资产 / 负债 / 固定资产 / 无形资产 / 贷款 / 债券 / 利率 / 投资 / 薪酬 / 研发费用 / 招待费 / 捐赠 / EBITDA / IRR / NPV / LBO 等） | `references/ref-financial-modeling-standards.md` |
| 通用 | 文本语义抽取 / 归类 / 打标 / 汇总 | 按「用户边界优先」「按结果区域分流」判断执行方式；按「语义结果质量」验收 |
| 通用 | 要输出数据分析报告 | `references/template-report.md` |
| **飞书** | 写飞书公式之前 / 公式落表后 | `references/lark-sheets-formula-translation.md`（飞书函数与 Excel 有差异）/ `references/lark-sheets-formula-verify.md` |
| 通用 | 使用 AI 公式 | 先读 `references/lark-sheets-ai-formula-monitoring.md`，按是否需要 AI 结果选择交付或监控 |
| 飞书 | 动作涉样式 / 美化 / 行高列宽 / 数字格式 | `references/lark-sheets-visual-standards.md`——⚠️ 其美化标准只适用于**从零新建的表**和**用户点名要美化的范围**；改已有表时**样式守恒**，原表行高 / 列宽 / 对齐 / 颜色 / 字体是基线，未被要求调整的一项不动，套用即破坏原格式 |
| **Excel** | 新建或修改区域的样式、行高列宽、合并布局，或制作报表 / 打印预览；仅补内容保留原格式 | `references/ref-excel-visual-standards.md`——样式继承、布局与格式转换 |
| **Excel** | 执行本地 xlsx 校验或重算取值前；仅读取源数据不触发 | `references/guide-execution-flow.md` §7——校验命令、编辑基准、检查点与重算结果处置 |

## 三、飞书表格引擎（`lark-cli sheets`）——本章飞书专属，Excel 引擎任务不需读

### 场景 → 命令速查

> **标准模式**：按当前动作选行；下一步必须 Read 该行 reference，读取完成前不得执行命令。只读命中的文档；含公式 / 样式等横切动作时再读对应规范，禁止用目录枚举代替 Read。

> **速度优先模式**：本表用于查命令，reference 按 `references/mode-speed-first.md` 的规则按需读取。本表中的写后核对也按所选模式执行，不另加一套标准验收。

| 你要做的事 | ✅ 正确写法 | 操作参考（标准模式动手前读） |
| --- | --- | --- |
| 读数据 | `+csv-get`（纯值/CSV）、`+cells-get`（公式/样式/批注）<br>**默认读全量**，不必分页；结果过大时自动落盘，按回执的 `output_path` 读文件 | 读 `references/lark-sheets-read-data.md` |
| 写入数据 | `+csv-put`（无类型歧义纯文本）、`+table-put`（typed；量值/真日期；标签/编号/前导零/文本数字用 object，禁裸 csv-put）、`+cells-set`（公式/富写入）、`+cells-set-style`（样式）、`+cells-set-image`（单元格图片） | 读 `references/lark-sheets-write-cells.md` |
| 格式继承（新列/新行） | 物理插行 / 插列用 `+dim-insert --inherit-style before\|after`；新区域用 `+range-copy --paste-type formats` 先铺样式再写值；已有格仅补内容时保留原样式，用户要求复制格式时才套模板 | 读 `references/lark-sheets-range-operations.md`；插行插列再读 `references/lark-sheets-sheet-structure.md` |
| 工作簿操作 | `+workbook-create`、`+workbook-info`、`+workbook-import`、`+sheet-copy`、`+revision-get`、`+workbook-export`；导入后检查 `data.extra`，有合适方案时优先考虑替代，不强制替换；可交完整 Excel 或双交并说明差异 | 读 `references/lark-sheets-workbook.md` |
| 行列操作 | 排序用 `+range-sort` 原子移动整行；合并 / 取消合并用 `+cells-merge` / `+cells-unmerge`；清空内容才用 `+cells-clear`；尺寸用 `+cols-resize` / `+rows-resize` | 读 `references/lark-sheets-range-operations.md`；涉结构布局再读 `references/lark-sheets-sheet-structure.md` |
| 美化收尾 | `+styles-put`：样式 / 合并 / 行高列宽 / 冻结**一份规格一次交付**，不要拆成多次 `+cells-set-style` / `+cells-merge` / `+cols-resize`（十几次往返换同一个结果）；只冻结表头用 `+dim-freeze --rows 1`——**没有 `+sheet-freeze` 这个命令** | 读 `references/lark-sheets-styles-put.md` |
| 子表结构 | `+sheet-info`、`+dim-insert`；删整行 / 列用 `+dim-delete`，不能用 clear 代替 | 读 `references/lark-sheets-sheet-structure.md` |
| 画图表 / 可视化 / 柱状图 / 折线图 / 饼图 / 趋势 / 占比 | 单图用 `+chart-create-basic`，多图用扁平输入的 `+batch-chart-create`；改已有图的数据源用 `+chart-data-update`、配置用 `+chart-config-update`；只有语义 shortcut 表达不了的单系列 / 单数据点 / 高级字段才用 `+chart-create` / `+chart-update`，且只提交必要的局部 properties。动手前先断言每张图的类型、横轴字段、分组字段和目标张数，画完 `+chart-list` 逐项核；图片迁移成真图表后删除并复查原浮动图片 | 读 `references/lark-sheets-chart.md`；含透视 / 分组汇总再读 `references/lark-sheets-pivot-table.md` |
| 分组汇总 / 透视 | `+pivot-create` | 读 `references/lark-sheets-pivot-table.md` |
| 筛选 / 只看符合条件的行 | `+filter-create` | 读 `references/lark-sheets-filter.md` |
| 查找 / 替换文本 | `+cells-search`、`+cells-replace` | 读 `references/lark-sheets-search-replace.md` |
| 条件格式 / 条件高亮 / 数据条 / 色阶 | 随数据变化的标色用 `+cond-format-create`；固定刷色只用于用户点名要静态着色 | 读 `references/lark-sheets-conditional-format.md` |
| 插图：自由摆放的装饰 | `+float-image-create` | 读 `references/lark-sheets-float-image.md` |
| 迷你图 / 单元格内趋势线 | `+sparkline-create` | 读 `references/lark-sheets-sparkline.md` |
| 批量清除多区域 | `+cells-batch-clear` | 读 `references/lark-sheets-batch-update.md`（high-risk） |
| 复核编辑变更 / 取版本间差异 | `+changeset-get` | 读 `references/lark-sheets-changeset.md` |
| 保存多份筛选状态 / 命名筛选视图 | `+filter-view-create`；视图与 `+filter-create` 相互独立、可在同一子表共存 | 读 `references/lark-sheets-filter-view.md` |
| 查编辑历史 / 回滚到历史版本 | `+history-list` 取版本，`+history-revert`（high-risk，异步）回滚后用 `+history-revert-status` 轮询 | 读 `references/lark-sheets-history.md` |

> ⚠️ 金额 / 百分比 / 比率 / 计数及参与运算的真日期写数字（百分比传 `0.4` + `number_format`）；日期标签、编号、前导零、身份证 / 单据号写文本。`--range` 只写 `A1:B2`，子表另传 `--sheet-id` / `--sheet-name`。

### 飞书表格编辑准则


> 数据、公式、样式和原生对象的正确性要求，两种模式都遵守。以下默认的回读、自检和验收步骤仅限标准模式；速度优先模式按 `references/mode-speed-first.md` 执行校验。用户明确要求的核验不能省略。
1. **最小改动**：按坐标和属性界定授权；补值不重刷原格式，美化不清理原文本或改写公式。用户没点名要删 / 改名 / 隐藏时，已有 Sheet 一张不动；补齐只写空格，已有空格的底色 / 边框 / 验证也保留。填写模板保留行标签与字段列序，不为说明来源擅自扩列或合并待填区。
2. **目标子表与回读断言**：先确认真实末行与目标区域；未点名子表时只从 `resource_type=sheet && is_hidden=false` 的可见网格候选里选，唯一才自动使用，多张不得按 index 猜。涉及"所有 / 每个 sheet"（跨表汇总、批量清洗、合并多张子表）时先 `+workbook-info` 列全再逐个处理，别只做前几张。普通值 / 普通公式写后用 `+csv-get` / `+cells-get` 验首、中、末及用户点名项，普通公式同时核对 `formula`；AI 区域按 `references/lark-sheets-ai-formula-monitoring.md`，不套本条值与公式回读。对象用 `+<对象>-list` 核对——返回 `ok` 只表示请求成功。回写要按行号定位时取 `row_indices`（或加 `--include-row-prefix` 读 `[row=N]`），`cells-get` 的样式字段与值分开处理。**样式同样要回读**：写过边框 / 底色 / 字体色 / 数字格式 / 行高列宽 / 冻结的，收尾用 `+cells-get --include style` 或 `+sheet-info` 抽查目标区域首、中、末格确认属性真的在——写入返回 `ok` 不代表样式落上了；缺项只补目标格的对应属性，不扩大到整列或其他原区域。**标准模式的图表最终交付门禁：最后一次修图后按 `references/lark-sheets-chart.md` 运行统一质检，读完全部 `read_required[].path` 图片并分别确认数据语义、静态质量与视觉结果；横轴标签倾斜时调整图表尺寸使其水平、完整且不重叠；折线图及组合图中的折线系列默认关闭整系列的逐点标签，仅用户明确要求时开启；末点、峰值、关键点等单点标签可按展示需要单独设置。覆盖不全、图片不可验或仍存在重叠 / 截断 / 遮挡时不得声称完成。**
3. **公式闭环**：可推导值写落格公式，数值计算引用源格，不将Python计算值硬编码回填。写前确认字段、阈值边界（以上/至少=`>=`，超过/大于=`>`）、单位/时区与完整源范围，以一条可手算记录及边界、例外独立推导预期；写后对照实际结果，不用生成函数给自己作证。标准模式下，普通公式逐段 `+formula-verify --exit-on-error`，各段success且业务哨兵正确才算完成；未完成不据此静态化，用户明确接受固定数值结果时才降级并说明。AI 公式按 `references/lark-sheets-ai-formula-monitoring.md` 分流：无需 AI 真值时首检通过必须立即交付，允许 pending；需 AI 真值时监控完成再验收，原位编辑回写验收后的 AI 值；pending、超时和占位不计入失败，不据此静态回退。
4. **完整继承样式**：新增行列时禁止只读值只写值——原表字体、对齐、底色（含奇偶行交替）、四边框都延续到新区域。**物理插入行 / 列**用 `+dim-insert --inherit-style before|after`（原生继承，比补刷可靠）；**新区域或用户要求复制格式时**用 `+range-copy --paste-type formats`；已有格仅补内容时保留原样式。非规则样式继承用 `+cells-get --include style` 读源区样式随值写回。无论走哪条路径，插入后都另查行高列宽（行高不随样式继承，插行填长文本前补 `+rows-resize`）、合并与跨列标题并补齐。详见 `references/lark-sheets-write-cells.md`。
5. **原子操作**：排序用 `+range-sort`，`--range` 覆盖完整记录宽度，先按表头确定业务主键及优先级，再写入 `--sort-keys`，排后按相同业务层级核对分组连续性和行对应；删除记录用 `+dim-delete`，清空内容 / 格式才用 `+cells-clear`；禁止读值后用 `+csv-put` 覆盖来模拟排序 / 删除。仅跨类型且有顺序依赖时才用 high-risk `+batch-update`。
6. **标色分流**：数据变化后应自动重算的高亮 / 标红用条件格式——凡按值 / 规则决定哪些格上色的都算，哪怕只标一次；静态样式只用于用户逐个点名的单元格或人工判断的结果，装饰性美化按视觉规范。两条路径取色字段用同一判据：用户中文语境下的"标红 / 染色 / 标记"指**单元格背景色**，"文字红 / 字体红 / 把字变红"才用字体色，默认无说明时选背景色。条件格式建完先 `+cond-format-list` 验规则与范围，再 `+cond-format-result-get` 抽查哨兵格命中样式。
7. **产物可核对**：用户点名的 sheet 名与数量、表头、标题、图例、文件名、口径逐字保留；匹配先明确相等 / 包含及允许的归一化，不用相似项补缺，不用明细行数代替唯一对象数；聚合先核业务粒度和键集合，总额相等不能代替分组正确。回复中每项“已完成”都能定位到产物，缺口逐项声明。
8. **替换与新增**：批量替换 / 删除后搜索确认无残留；新增列要有表头，单位 / 口径另置，不占原表头或数据格。
9. **不编造**：表外数据须有可核验来源，不用常识或名称推断伪造公司、标准值、行情或法规参数；**没有来源就留空**——凭记忆填的数值大概率与真实值对不上，比留空更糟。留空的格在交付说明里逐项列出格址与缺的来源，不要只写一句"部分数据缺失"。非数值评价可据给定事实概括，不得扩写成未经提供的职责、经历或成果。确需推断的描述须标明是推断及依据，不把推断写成既有事实。

> **逐行语义任务使用 AI 公式**：仅限标准模式下按「用户边界优先」「按结果区域分流」命中的区域。每个目标格只依赖同行输入，就用原生 `=AI(prompt, range)`；数据量、分批和判断复杂度不改变该路由。Python 只做清洗、行号映射和公式批次构造，不生成目标语义值或答案词典；大批量按 `references/lark-sheets-formula-translation.md` 串行铺设。计算状态用 `+formula-verify --ai-only --range <整个写入区间>` 检查，不用 `+cells-get` / `+csv-get` 轮询；目标覆盖、交付或监控按 `references/lark-sheets-ai-formula-monitoring.md` 执行。

> ⏬ 未完——继续调整 offset 续读，直到末行「全文完」标记。

> 流程：了解结构 →（未点名时先按 visible_grid selection 定位）→ 读数据 → 原生工具写入 → 按用户点名项回读验证 → 在线交付。整理 / 美化 / 加汇总行这类会改变表长或版式的任务，收尾把表头行冻住（原表已有冻结设置的不动）。xlsx 验收只在处理本地 xlsx、或用户点名要本地 xlsx / 下载 / 打印时跑。

### 公共 flag 速查

各 reference 的 shortcut 标题下用一行徽章标注支持的公共 / 系统 flag（如 `_公共四件套 · 系统：--dry-run_`）。type / 必填 / 描述在本段统一声明：

#### 公共 flag（定位资源）

**公共四件套** = `--url` / `--spreadsheet-token` / `--sheet-id` / `--sheet-name`，分成两组 XOR，**每组都必须给且只能给一个**（XOR = 二选一必填，不是"可选"）——`spreadsheet` 指工作簿、`sheet` 指子表；条件格式 / 图表 / 筛选视图 / 透视表 / 迷你图 / 浮动图片这类对象在四件套之外另用各自的 `--*-id` 定位：

1. **spreadsheet 定位（必填）**：`--url`（解析 `/sheets/`、`/spreadsheets/`、`/wiki/` 三种链接；wiki 链接自动定位背后的电子表格）与 `--spreadsheet-token`（裸 token）二选一。**例外**：`+workbook-create` / `+workbook-import` 产出**还不存在**的表，不接受任何定位 flag。
2. **sheet 定位（公共四件套 shortcut 必填）**：`--sheet-id` 与 `--sheet-name` 二选一。
   - ⚠️ **不确定 sheet 名时禁止猜 `Sheet1`**：除非对话或上下文已出现具体值，第一步先 `+workbook-info` 拿 `sheets[].sheet_id/title` 再选——中文表的子表常叫"数据"/"工作表 1"/业务名，猜名大概率撞 `sheet not found`。
   - ⚠️ **`--range` 里的 `Sheet1!` 前缀不能替代 sheet 定位**：仍必须传 `--sheet-id` / `--sheet-name`。
   - ⚠️ **A1 引用含 `!` 时整段用单引号包裹**（`--range 'Sheet1!A1:B2'`，挡 bash history expansion；别用 `set +H`，sh/dash 下非法）。sheet 名要在 A1 里内层再包单引号时用 `'\''` 转义。
   - **例外**：徽章标 `_公共：URL/token（无 sheet 定位）…_` 的 shortcut 不接受 sheet 定位——工作簿级（`+workbook-info` / `+sheet-list` / `+sheet-create` / `+revision-get` / `+changeset-get` / `+history-list|revert|revert-status`）、批量与整表级（`+batch-update` / `+batch-chart-create|update` / `+cells-batch-clear` / `+styles-put` / `+dropdown-update|delete`），以及子表名写在 payload 里的 `+table-put`。`+workbook-export` 只接 `--sheet-id`（无 `--sheet-name`），`+pivot-create` 用 `--target-sheet-id/name`（XOR，可都不传）。徽章是判据，本行只是速记。

```bash
# 统一调用范式：两组定位缺一不可（占位符别原样填；表名先 +workbook-info 查）
lark-cli sheets +csv-get --url "https://.../sheets/shtXXX" --sheet-name "<真实表名>" --range "A1:F30"
```

#### 系统 flag

| Flag | Type | 必填 | 说明 |
| --- | --- | --- | --- |
| `--dry-run` | bool | 否 | 零副作用：仅打印请求路径与参数模板，不发起调用 |
| `--yes` | bool | 是（仅 `high-risk-write`） | 二次确认；不带时退出码 10。 |
| `--print-schema` | bool | 否 | 写复合 JSON flag 前结构不确定就先跑它：本地打印 Schema 并退出（不发起调用、不需要其它 required flag），搭配 `--flag-name` 指定查哪个 flag，省略时列出该 shortcut 可查的 flag。只有含复合 JSON flag 的 shortcut 支持。 |
| `--flag-name` | string | 否 | 配合 `--print-schema`：flag 名不带 `--` 前缀（`cells` / `properties`）。**支持点分路径切片**：`--flag-name properties.snapshot.plotArea.axes` 只打印该子树，大 schema（chart 的 properties 约 1700 行）按需取，别整篇翻页。 |

> **bool flag 语法**：开启可用裸 `--flag`；显式值只用 `--flag=true` 或 `--flag=false`，不得用空格分隔。

> ⚠️ **high-risk-write 命令清单（exit 10 强确认门禁）**：`+batch-update`、`+cells-clear`、`+cells-batch-clear`、`+sheet-delete`、`+dim-delete`、`+dropdown-delete`、`+history-revert`（整表回滚到历史版本），以及各对象删除 `+chart-delete` / `+pivot-delete` / `+cond-format-delete` / `+filter-delete` / `+filter-view-delete` / `+sparkline-delete` / `+float-image-delete`。
>
> **审批协议**：先 `--dry-run` 预览、向用户展示将执行的操作与影响范围，**获得用户明确同意后**再在原命令追加 `--yes` 执行。未经用户同意不得带 `--yes`，也不得在 exit 10 后静默补 `--yes` 重试——那等于禁用门禁。

**Schema 的边界**：`--print-schema` 打印的是 flag 值的内部结构，flag 描述要求外层信封时（如 `--sheets` 的 `{"sheets":[…]}`）schema 里看不到那层，按描述补上；reference 的 `## Schemas` 段也只给一层。图表直接 `+chart-create --print-example <type>` 拿最小可用模板改参。

#### flag 内容类型与输出约定（术语速记）

- JSON 类入参分三类：**复合 JSON** = 深层嵌套对象（`--print-schema` 可查）；**简单 JSON** = 一二维标量数组；**非 JSON 文本** = 原样文本（如 CSV）。
- **envelope**：所有 shortcut 返回统一外层 `{ok, identity, data, ...}`；写操作不会自动回读，校验自行调用 `+*-list` / `+*-get` / `+cells-get`。
- **大 payload 走文件 / stdin，不在命令行内联**：Type 标 `File + Stdin` 的 flag 支持 `--flag "@./x.json"`（`@file` 只接受 cwd 下相对路径，绝对路径被拒）与 `--flag -`（stdin）；payload 含换行 / 引号或体量大时一律落文件。**stdin 每次调用只能给一个 flag**——`+table-put` 的 `--sheets` 与 `--styles` 都是大 JSON 时，一个走 `-`、另一个走 `@./x.json`。临时文件不要落进用户项目目录。

===== 全文完（共 236 行）=====
