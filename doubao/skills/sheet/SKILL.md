---
name: sheet
version: 3.6.0
description: "表格全场景（本地Excel/CSV与飞书/doubao在线表格）：创建、读写、分析、计算、财务建模、语义处理、可视化与美化。若用户上传附件、提供表格链接/token，或要求任何表格操作，必须加载。"
metadata:
  requires:
    bins: ["lark-cli", "python3"]
  cliHelp: "lark-cli sheets --help"
---
# 表格全场景处理技能（sheet）

覆盖本地 Excel 文件与飞书在线表格的全场景处理。**本技能不负责获取外部信息**（标准值、行情、法规参数），需要时先由其他途径取得。

## skill 入口指向 mode-speed-first 时，下一步只读它

`<system-reminder>` 给出的 skill 入口路径指向 `references/mode-speed-first.md` 时，动手前**只读它这一份**，读完按它的取舍执行：本文与各 reference 里写着「动手前必须完整 Read」「必须 / 才算完成」的步骤都以它为准，在它给出取舍之前不要并行加载其它 reference。入口没有指向它就是标准模式，按本文执行，也不自行去读那份文件。

## 一、通用流程（两套引擎都适用）

本章不分引擎，四步走完：**① 判运行环境 → ② 选引擎 → ③ 读交付契约 → ④ 按开工纪律做**。①②③动手前定完，③里的交付与自检在收尾时执行。

### 1. 运行环境（决定交付形态，也决定开工前的必读 reference）

1. SystemPrompt 的 `Computer OS` 字段：值为 `Windows` / `Mac` 判为**本地电脑**，值为其他判为云电脑。
2. 无 `Computer OS` 字段时看 `<system-reminder>`：出现 `Runtime: local_pc` 为本地电脑，`Runtime: cloud_vm` 为云电脑。

判为本地电脑、或两条都判不出时（判不出只放宽读 reference 的门槛，交付形态仍按上面两条判、判不出按云电脑），读完本 SKILL 后**必须先完整 Read `references/ref-local-compat.md`**；`Computer OS: Windows` 的会话，读完它**再完整 Read `references/ref-windows-compat.md`**——无论后续是否执行 lark-cli，跳过会大面积报错。

**本地电脑分支**：`<system-reminder>` 会注入 `file_status` / `token` 等 canvas 字段（没被打开过的文件不带），字段全表、失败判定与三态分支见 `references/ref-local-compat.md`。读它之前先记住一条：**Canvas 打开时**改动只落在工作目录的底层产物上，不写回用户真实本地文件、也不用 `lark-cli` 导出，交付用户提供的原文件路径并提醒自行保存；**Canvas 未打开时**（从未打开、或打开过又关闭）按第 2 节走 Excel 引擎，改动就地落在用户的真实文件上（打开过的按 `path` 定位）。

### 2. 选引擎（按数据在哪，与交付形态无关）

- **Excel 引擎**（Python + openpyxl + `scripts/`）：**本轮从零新建**（没有源表、没有在线表可改），或用户提供本地表格文件（上传附件或给出路径，`.xlsx` / `.xls` / `.csv`）且没有在线链接。按「开工纪律」的 Excel 引擎路径走，透视表 / 图表等对象能力仍走 Must-CLI 桥接。
- **飞书表格引擎**（`lark-cli sheets`）：用户给出 `/sheets/`、`/spreadsheets/`、或指向电子表格的 `/wiki/` 链接，或飞书表格 token。按 URL 路径 / token 判定，不看域名。

**例外**：本地电脑上被 Canvas 模式打开（`file_status` 为 `open`）的本地表格文件，编辑一律走飞书表格引擎，`lark-cli sheets` 以 `--spreadsheet-token <token>` 定位（不是 `--url`），可回滚、编辑状态实时可见。**本地电脑上**用 Excel 引擎编辑本地文件时 Python 改动不可回滚，动手前先**复制一份备份**；编辑落在原文件上，备份只做回滚快照——期间不更新、不交付，交付门禁拿它当基准。

两套引擎经 `+workbook-import` 打通：Excel 引擎的产物汇入飞书表格，交付形态按第 3 节判。

### 3. 交付契约（动手前先读完，它就是验收标准）

**产物载体**：先按下面两条定形态，再看例外。

- **交飞书表格**（云电脑的新建与编辑、本地电脑的新建）：默认交**经过检查的飞书表格**。用户说"做个 Excel""给我个表""整理成表格""输出 Excel 格式 / .xlsx""可下载的 Excel 文件""原表格 / 原文件"、引用已有表格文件或任何预期输出表格产物，都走这条——**本地 xlsx 只是中间产物，必须 `+workbook-import` 导入再交付，停在本地文件就是没交付**（唯一降级：导入重试一次仍失败，才改交本地文件并在交付说明写明原因）；导入后**只交飞书链接，不重复附带 xlsx**，并继续做完用户要求的全部操作，不可导入即停。
- **交本地文件路径**（本地电脑的编辑场景）：交付物与编辑对象同形态——改飞书表格就交飞书表格，**改本地文件就交本地文件路径，无需导入飞书**；交本地文件时**不得把 `token` 拼成在线链接**当产物给出。

> **例外（两条都适用）**：用户明确表态时按用户的来——**明确拒绝**在线表格（"不要飞书表格""不要在线链接""给我 .csv 就行"）就改交本地文件；本地电脑改本地文件时用户**明确要在线表格 / 飞书链接**，就导入后交在线表；明确说"两个都要"才两者都交。第一条枚举的那些说法只是要产物、不是拒绝在线，仍交飞书表格。

**分析类任务同样交表格产物**：用户只要文字结论（对比、排查、归因、建议）时，结论也要落进产物本身（结果 sheet 的摘要区或独立说明块），再按上面两条交付——只写在回复正文里等于没交付。HTML / 图片报告只能附加，替代不了表格产物。

**文件名**：用户点名文件名时沿用（工作簿标题去扩展名、附件名保留全名、`/` 换 `-`），不自拟；已有表不因此改名。

**每轮必交**：本轮只要对飞书表格写入 / 编辑 / 更新过就必须交付——数据来自文件 / 聊天记录 / 搜索结果 / 口述都算，本地 Excel 处理后导入也算。**跨轮同样要交**：同一张表前序轮次已交付过、URL 没变，本轮再改动后仍要重新交付一次，不得复用上一轮的产物卡片，也不得只提示用户刷新。**交付渠道只有一条**：飞书链接和本地文件路径都通过宿主的**产物交付工具**交出去——当前宿主是 `present_files`，参数按它自己的工具说明填；工具列表里换了名字时，取那个自述用于把最终产物交给用户的工具。**判据是这次调用真的发生并成功**：回执会列出交付了哪些条目，没调用或调用失败就是没交付、重发一次；把 URL 写进回复正文、或在回复里写「已交付」都不算。只有调用过该工具并明确报出「工具不存在」，才退回正文给出 URL 或路径。在线编辑任务交付后不导出验证。

**交付前跑自检拿到可交付信号**：**产物是飞书表格时**，跑 `python3 scripts/lark_sheet_selfcheck.py "<url>"` 逐项核对并修复——问题不能只写在回复里，每处差异都要在产物内追到错源改正；再按脚本清单把结论写进 `--confirm` 重跑，拿到可交付信号才算完成（`CHECK_INCOMPLETE` 按脚本说明处理）。修不完的——非确定性问题、或改了会波及用户没点到的范围——写进交付说明照常交付，不要进入反复修复循环。交本地文件时不跑这条（脚本兼容性待验证），本地产物由「开工纪律」的交付门禁把关，xlsx 与 csv 各一道。**编辑已有表时再带上 `--baseline <改前快照.xlsx> --scope '<允许改动的范围>'`**：没有改前基准就判不出哪些格本不该长这样，带上之后工具会比出范围外被改写的原值和退化成静态值的原公式。范围动手前就定下，写成 `子表名!G:I`。源表只在线上、本地没有文件时，动手前先 `+workbook-export` 导一份改前快照当基准。

**用户点名的数和产出项写成检查点，交给工具判**：三个校验脚本都接 `--checkpoints`，条目给格址加期望值、必须由公式驱动的区域、或必须存在的子表名，工具回读产物逐条对，不符按确定性错误报出来。期望值只写用户给出的数或你独立复算出来的数，把产物里读到的数抄进去等于没判。

```bash
python3 scripts/lark_sheet_selfcheck.py "<url>" --checkpoints '[{"cell":"汇总!B12","expect":1234.56,"tolerance":0.01},{"range":"明细!G2:G200","all_formula":true},{"sheets":["明细","汇总"]}]'
```

### 4. 开工纪律（执行期）

**附件读取**：下载后验字节数与魔数，失败重试后用导入兜底；未读入的事实不得用常识或别的文件替代，缺口留空说明。中间文件走 workspace 相对路径。

**Excel 引擎路径**：①预检 → ②处理（聚合前剔除合计 / 总计 / 小计 / 累计行）→ ③过交付门禁 → ④交付（产物交飞书表格时，门禁通过后先导入）。打不开、必交项缺失、门禁报出确定性错误都算未完成。**只要涉及 xlsx 读写，动手前就读 `references/ref-xlsx-workflow.md`、`references/ref-excel-visual-standards.md`**——四步的具体做法与判据在里面。

**交付前先过 Excel 交付门禁**：一条命令查完公式重算、新函数前缀、数组形状、静态值嫌疑和源表是否被改写。

```bash
python3 scripts/excel_formula_verify.py ./output.xlsx 60   # 从零新建：没有源可比
python3 scripts/excel_formula_verify.py ./output.xlsx 60 --baseline ./改前快照.xlsx --scope '明细!G:I'   # 编辑已有：范围动手前定下
python3 scripts/excel_csv_verify.py ./output.csv --baseline ./改前快照.csv   # 产物是 CSV：换这道，上面那个读不了 csv
```

改前快照是动手前那份没被改动的工作簿：结果另存新文件时它就是源文件本身，就地改原文件时它是动手前复制的那份备份。

退出 0 才算过；**退出 3 是确定性错误**（公式错误值、缺 `_xlfn.` 前缀、区域不同形、源表被改写、检查点不符），修完重跑；**退出 4 是重算未完成或诊断信号**，按 stderr 提示处置并写进交付说明，不反复重跑——宿主没装 LibreOffice 时 4 就是正常终态。哪一档都不得改用 Python 同源复算或公式计数冒充验证。**编辑已有工作簿要在源工作簿上改**，不要新建空工作簿再把结果写进去，那样源表整张消失。

**产物是 CSV 时换 `excel_csv_verify.py`**：CSV 没有公式也没有子表，上面那道门禁连文件都读不开。它查编码与 BOM、逐行字段数、表头与行数、长数字被转成科学计数或前导零被吃掉；`--expect-rows` / `--expect-headers` 写用户点名的结构，`--checkpoints` 协议相同。退出码同一套分档。

**Must-CLI 桥接**：透视表 / 图表 / 单元格图片 / 迷你图先导入（有附件用 `+workbook-import`，无附件用 `+workbook-create`）再用 `lark-cli sheets` 就地创建。走「本地 Python 生成 xlsx → 导入」会让透视表退化成普通数据区、单元格图片变浮动图、图表变静态图——都不随源数据更新、也没有交互；判据是最终对象能被 `+pivot-list` / `+chart-list` 这类列举命令返回，返回不了就是没做出来。速查表没列的子选项（中位数汇总 / 计算字段 / 面积图 / 胜负迷你图等）多数原生支持，先查对应 reference，别凭「没列」判不支持就绕路。

## 二、动手前必读的 References（命中即读，按动作判定）

> 动手前必须读完本节所有命中行的 reference——前置条件不是建议，未读不得执行对应操作，跨行命中就全读完再动手。所有 reference 都在 `references/` 下；对象操作按「三」速查表读。

| 引擎 | 触发条件（命中就先读） | 读这份 |
| --- | --- | --- |
| **通用** | 打开已有表格（附件 / 飞书链接）做任何操作——编辑、整理、补齐、分析、汇总、生成结果表都算 | `references/guide-execution-flow.md`——用户没点落点时结果写新 sheet、原 sheet 一张不删，已有表 + 新数据 = **追加**、原有行一行不丢；用户点名要就地改 / 补齐 / 替换 / 删除时，按其授权在原表改 |
| 通用 | 表内承载财务数据（营收 / 成本 / 利润 / 损益 / 现金流 / 估值 / DCF / 三张表 / 预算 / 税务 / 纳税 / 发票 / 审计 / 折旧 / 资产 / 负债 / 固定资产 / 无形资产 / 贷款 / 债券 / 利率 / 投资 / 薪酬 / 研发费用 / 招待费 / 捐赠 / EBITDA / IRR / NPV / LBO 等） | `references/ref-financial-modeling-standards.md` |
| 通用 | 文本语义抽取 / 归类 / 打标 / 汇总 | `references/guide-semantic-analysis.md` |
| 通用 | 要输出数据分析报告 | `references/template-report.md` |
| **飞书** | 写飞书公式之前 / 公式落表后 | `references/lark-sheets-formula-translation.md`（飞书函数与 Excel 有差异）/ `references/lark-sheets-formula-verify.md` |
| 飞书 | 动作涉样式 / 美化 / 行高列宽 / 数字格式 | `references/lark-sheets-visual-standards.md`——⚠️ 其美化标准只适用于**从零新建的表**和**用户点名要美化的范围**；改已有表时**样式守恒**，原表行高 / 列宽 / 对齐 / 颜色 / 字体是基线，未被要求调整的一项不动，套用即破坏原格式 |
| **Excel** | 用 Python/openpyxl 生成 xlsx、读附件数据处理——只要涉及 xlsx 读写就命中 | `references/ref-xlsx-workflow.md`、`references/ref-excel-visual-standards.md`——预检、处理、公式验证、导入全流程 |

## 三、飞书表格引擎（`lark-cli sheets`）——本章飞书专属，Excel 引擎任务不需读

### 场景 → 命令速查

> 按当前动作选行；下一步必须 Read 该行 reference，读取完成前不得执行命令。只读命中的文档；含公式 / 样式等横切动作时再读对应规范，禁止用目录枚举代替 Read。

| 你要做的事 | ✅ 正确写法 | 动手前读（先 Read 再动手） |
| --- | --- | --- |
| 读数据 | `+csv-get`（纯值/CSV）、`+cells-get`（公式/样式/批注） | 读 `references/lark-sheets-read-data.md` |
| 写入数据 | `+csv-put`（无类型歧义纯文本）、`+table-put`（typed；量值/真日期；标签/编号/前导零/文本数字用 object，禁裸 csv-put）、`+cells-set`（公式/富写入）、`+cells-set-style`（样式）、`+cells-set-image`（单元格图片） | 读 `references/lark-sheets-write-cells.md` |
| 格式继承（新列/新行） | 物理插行 / 插列用 `+dim-insert --inherit-style before\|after`；往已有空白区域扩写用 `+range-copy --paste-type formats` 先铺样式再写值 | 读 `references/lark-sheets-range-operations.md`；插行插列再读 `references/lark-sheets-sheet-structure.md` |
| 工作簿操作 | `+workbook-create`、`+workbook-info`、`+workbook-import`、`+sheet-copy`、`+revision-get`、`+workbook-export` | 读 `references/lark-sheets-workbook.md` |
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

1. **最小改动**：用户没点名要删 / 改名 / 隐藏时，已有 Sheet 一张不动；补齐只写空格，未要求调整的值 / 结构 / 格式不动。
2. **目标子表与回读断言**：先确认真实末行与目标区域；未点名子表时只从 `resource_type=sheet && is_hidden=false` 的可见网格候选里选，唯一才自动使用，多张不得按 index 猜。涉及"所有 / 每个 sheet"（跨表汇总、批量清洗、合并多张子表）时先 `+workbook-info` 列全再逐个处理，别只做前几张。写后用 `+csv-get` / `+cells-get` / `+<对象>-list` 验首、中、末及用户点名项——返回 `ok` 只表示请求成功。纯 CSV 回写前去掉 `annotated_csv` 的 `[row=N] ` 前缀，`cells-get` 的样式字段与值分开处理，公式必须回读 `formula`。**样式同样要回读**：写过边框 / 底色 / 字体色 / 数字格式 / 行高列宽 / 冻结的，收尾用 `+cells-get --include style` 或 `+sheet-info` 抽查目标区域首、中、末格确认属性真的在——写入返回 `ok` 不代表样式落上了；缺的整份重发（样式是幂等盖章，重发无副作用）。
3. **公式闭环**：可推导值写落格公式，不用静态值代替——用 Python 算好数值再写进单元格，交付的是改输入不重算的死表；Python 只用于推导和验证，落进单元格的必须是引用其他格的公式。写前确认字段语义、阈值边界（以上/至少=`>=`，超过/大于=`>`）、单位/时区和完整源范围，选首中末、空值、边界及一条可手算记录作哨兵；写后逐段 `+formula-verify --exit-on-error`，各段 `status='success'` 且哨兵值正确才算完成（AI 公式例外：异步计算，改用 `+formula-verify --ai-only` 对整个写入区间做一次异步状态检查，不用 `+cells-get` 轮询结果，`failed` 清零后即使仍有 pending 也可交付并说明）；试错 3 次仍失败可降级静态值，交付说明写明「静态值 + 失败原因 + 不随源数据更新」。
4. **完整继承样式**：新增行列时禁止只读值只写值——原表字体、对齐、底色（含奇偶行交替）、四边框都延续到新区域。**物理插入行 / 列**用 `+dim-insert --inherit-style before|after`（原生继承，比补刷可靠）；**往已有空白区域扩写**（如在数据右侧加新列）用 `+range-copy --paste-type formats` 先铺样式再写值；两者都表达不了的非规则样式，才用 `+cells-get --include style` 读源区样式随值写回。无论走哪条路径，插入后都另查行高列宽（行高不随样式继承，插行填长文本前补 `+rows-resize`）、合并与跨列标题并补齐。详见 `references/lark-sheets-write-cells.md`。
5. **原子操作**：排序用 `+range-sort`，`--range` 覆盖完整记录宽度，排序列只写进 `--sort-keys`；删除记录用 `+dim-delete`，清空内容 / 格式才用 `+cells-clear`；禁止读值后用 `+csv-put` 覆盖来模拟排序 / 删除。仅跨类型且有顺序依赖时才用 high-risk `+batch-update`。
6. **标色分流**：数据变化后应自动重算的高亮 / 标红用条件格式，已确定结果的固定标注用静态样式，装饰性美化按视觉规范。两条路径取色字段用同一判据：用户中文语境下的"标红 / 染色 / 标记"指**单元格背景色**，"文字红 / 字体红 / 把字变红"才用字体色，默认无说明时选背景色。条件格式建完先 `+cond-format-list` 验规则与范围，再 `+cond-format-result-get` 抽查哨兵格命中样式。
7. **产物可核对**：用户点名的 sheet 名与数量、表头、标题、图例、文件名、口径逐字保留；回复中每项“已完成”都能定位到产物，缺口逐项声明。
8. **替换与新增**：批量替换 / 删除后搜索确认无残留；新增列要有表头，单位 / 口径另置，不占原表头或数据格。
9. **不编造**：表外数据须有可核验来源，不用常识或名称推断伪造公司、标准值、行情或法规参数；**没有来源就留空**——凭记忆填的数值大概率与真实值对不上，比留空更糟。留空的格在交付说明里逐项列出格址与缺的来源，不要只写一句"部分数据缺失"。

> 🤖 **文本类 NLP 任务首选 AI 公式，别默认退回手工 / Python**：只要对文本列做**翻译 / 情感 / 分类打标签 / 信息提取 / 总结 / 润色**等 NLP，飞书在线表格上优先用原生 `=AI(prompt, range)` 逐列铺开（写法与普通公式一致，见 `references/lark-sheets-formula-translation.md`），一次落表随行自动计算，比逐条读 → 手工判断 → 回写 / Python 调模型再写静态值都更省事。**判定标准是「逐行独立」**：每个目标单元格只依赖同一行输入即为逐行独立，**数据量（哪怕 1 万 +）、分批、判断复杂度都不改变该判定**——大数据量下 AI 公式仍是首选，分批只改公式铺设的批次大小（行数很多时按批串行，量级参考每批几百到一千行），不得改为「用 Python 或规则脚本生成语义结果后静态写回」；Python 只能做清洗 / 行号映射 / 构造公式批次，不得读源文本生成目标语义值。只有单个结果依赖多行输入的跨行任务才走非公式路线。AI 公式异步计算，写完先对种子格 / 首格做**一次** `+cells-get --include formula` 核对文本，随后**第一校验入口必须是** `+formula-verify --ai-only --range <整个写入区间>`，禁止用 `+cells-get` 轮询计算结果；判据为 `ai_formula_failed_count == 0`（`--range` 只透传给后端、不保证收窄汇总口径，按返回的单元格定位核对本次区间，别拿总数对预期条数），满足后即使仍有 pending 也可交付，并告知用户"AI 公式仍在后台运行"。

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

===== 全文完（共 187 行）=====
