---
name: doubao-finance-model-builder
description: 对 A 股、港股和美股上市公司执行中文、可审计且带机器阻断质量门的三表预测、DCF、LBO或可比公司估值。支持最新公告增量检索、除权除息和送转股等公司行动证据冻结、收入增速和多产品量价预测、三表勾稽、FCFF/WACC/终值、分层债务与回报、同行筛选和相对估值。用于财务预测、预算、目标价、杠杆回报或交易可比分析；不要用于自动下单、纯信用评级或并购法律意见。
---

# Doubao Finance Model Builder

## 强制读取完整性协议

不得假设一次工具调用能够完整返回 `SKILL.md` 或引用文件。先读取 `references/reading-manifest.json`，再按所选工作流确定必读文件，并对每个必读文件执行以下步骤：

1. 先取得文件总行数；工具不能直接返回总行数时，继续分段读取直至文件末尾。
2. 按不重叠的连续区间读取，默认每段最多 100 行，例如 `1—100`、`101—200`、`201—300`。不得重复读取首段来代替续读，不得跳过中间区间。
3. 每个 Markdown 文件末尾必须包含唯一标记 `<!-- END OF FILE: 文件名 -->`。只有最后一段明确包含与当前文件名一致的标记，才可将该文件记为 `READ_COMPLETE`。
4. 建立 `reading-ledger.json`，逐文件记录 `path`、`total_lines`、`chunks_read`、`end_marker_found` 和 `status`。区间必须从第 1 行连续覆盖至 `total_lines`，否则状态为 `INCOMPLETE`。
5. 所有必读文件均为 `READ_COMPLETE` 后，才能创建执行计划、检索数据、运行脚本或开始建模。工具不支持行号、offset 或分页，或无法确认文件末尾时，停止并报告读取阻断；不得凭部分内容继续。
6. 组合任务取各工作流必读集合的并集，只读取一次并在台账中复用完成状态。条件性资料仅在适用时加入必读集合。

任务涉及 Excel、`.xlsx`、Sheet、电子表格或公式工作簿时，必须将外部 `lark-sheets/SKILL.md` 加入必读集合；金融或财务场景同时将 `lark-sheets/references/ref-financial-modeling-standards` 加入必读集合。对两者按同样的分段和连续覆盖规则完整读取；外部文件有末尾标记时记录 `end_marker_found=true`，没有末尾标记时必须通过工具确认已达EOF并记录 `eof_confirmed=true`。在 `reading-ledger.json` 中以 `external_skills` 记录实际解析路径、必读引用与状态。二者均为 `READ_COMPLETE` 后才能创建执行计划、运行工作簿生成脚本或开始建模；未安装、无法定位或未完整读取时停止并报告读取阻断，不得凭本 skill 内容推测外部规范。

`reading-ledger.json` 的最小结构：

```json
{
  "chunk_lines": 100,
  "files": [
    {
      "path": "references/model-and-artifact-controls.md",
      "total_lines": 107,
      "chunks_read": [[1, 100], [101, 107]],
      "end_marker_found": true,
      "status": "READ_COMPLETE"
    }
  ],
  "external_skills": [
    {
      "name": "lark-sheets",
      "path": "SKILL.md",
      "resolved_path": "/actual/installed/path/lark-sheets/SKILL.md",
      "total_lines": 150,
      "chunks_read": [[1, 100], [101, 150]],
      "end_marker_found": false,
      "eof_confirmed": true,
      "status": "READ_COMPLETE"
    },
    {
      "name": "lark-sheets",
      "path": "references/ref-financial-modeling-standards",
      "resolved_path": "/actual/installed/path/lark-sheets/references/ref-financial-modeling-standards",
      "total_lines": 120,
      "chunks_read": [[1, 100], [101, 120]],
      "end_marker_found": false,
      "eof_confirmed": true,
      "status": "READ_COMPLETE"
    }
  ],
  "overall_status": "READ_COMPLETE"
}
```

## 核心规则

先按最终交付物路由，只加载选定工作流及其明确要求的资料。所有相对路径均以本 skill 根目录为基准。

查询财务、市场、一致预期或公司行动数据前，按强制读取完整性协议完整读取 `references/source-tool-priority.md`。用户明确指定的工具、网站、文件或数据口径优先于 `seed_finance_search`；只有指定来源已实际尝试且成功取得、确认不适用或留下可审计的不可用记录后，才能调用 `seed_finance_search` 补充或降级。用户未指定时，`seed_finance_search` 仍作为默认高效检索入口。不得静默替换用户指定来源，不得声称调用未实际使用的工具。

每项任务都完整读取 `references/model-and-artifact-controls.md`。正式建模、公式工作簿或多步骤估值还完整读取：

- `references/execution-plan-schema.md`
- `references/latest-announcement-sweep.md`
- `references/delivery-package-contract.md`

使用股价、每股价值、市值或交易倍数时，另完整读取 `references/equity-evidence-acquisition.md`。先冻结官方股本与公司行动证据，再建估值日股数桥；验证非 `PASS` 时停止，不用免责声明绕过。

这些公共协议定义最低门槛。工作流只能增加门槛，不得降低、删除或事后改写阈值。

## 路由

| 最终交付物 | 工作流（完整读取） |
|---|---|
| 利润表、资产负债表、现金流量表、预算或滚动预测 | `references/workflow-three-statements.md` |
| FCFF、WACC、终值、内在价值、每股价值或反向 DCF | `references/workflow-dcf.md` |
| 收购融资、债务偿还、退出价值、MOIC、IRR 或最高收购价 | `references/workflow-lbo.md` |
| 同行池、交易倍数、溢折价、相对价值或市场隐含预期 | `references/workflow-comps.md` |

用户明确点名方法时采用该方法；未点名时按最终交付物选择。仅说“估值”默认 DCF；出现同行、倍数或相对定价时选择可比公司；出现收购、杠杆、退出、MOIC 或 IRR 且关注财务投资人回报时选择 LBO。

不要因 DCF/LBO 内含经营预测而自动加载三表，也不要因需要倍数交叉检查而自动加载可比公司。仅在用户明确要求多个独立交付物时组合：

- 三表 → DCF：先完成可勾稽三表，再映射经营预测和自由现金流口径。
- 三表 → LBO：先完成经营预测，再映射 EBITDA、资本开支、营运资本和现金税；独立计算债务计划。
- DCF + 可比公司：分别形成内在价值与相对价值，解释差异，不机械平均。
- LBO + 可比公司：仅用可比公司支持进入/退出倍数，仍用 LBO 脚本计算回报。

组合任务分别保存各模块的输入、输出、警告和结论；共享数据记录来源与口径转换。

## 资源隔离

- 公共：`scripts/common/`、`assets/common/` 及公共协议。
- 三表：`scripts/three-statements/`、`assets/three-statements/`、`references/three-statements-*`。
- DCF：`scripts/dcf/`、`assets/dcf/`、`references/dcf-*`。
- LBO：`scripts/lbo/`、`references/lbo-*`。
- 可比公司：`scripts/comps/`、`references/comps-*`。

单工作流不得加载其他模块资源；组合任务也要先分别通过模块质量门，再比较结果。

## 执行顺序

1. 宣布所选工作流和理由，按强制读取完整性协议完整读取公共质量门、工作流及其要求的资料；保存 `reading-ledger.json`，再运行 `python3 scripts/common/validate_reading_integrity.py <skill-root> --ledger reading-ledger.json --output reading-integrity.json`。`reading-integrity.json.status` 非 `PASS` 时停止，不得创建执行计划或开始建模。
2. 对正式任务创建并验证 `execution-plan.json`。计划只声明要求，不预填“冲突已解决”“无遗漏公司行动”或第二套估值结果。三表明确选择 `growth` 或 `volume_price`；有可靠量价数据的资源、矿业、油气和多产品制造公司采用 `volume_price`。
3. 从模型已纳入的最新财务披露公开日检索至信息截止日，覆盖最新财报、业绩预告/快报、盈利警告、指引变更、重大经营事项、融资和公司行动；保存官方结果页与正文，生成并验证 `announcement-sweep.json`。存在未处置或 `blocking` 公告时停止相关结论。
4. 涉及市场价值时，先取得官方基准股本、官方检索结果、每项公司行动正文及文本快照，生成 `equity-evidence.json`；不得用最新公告扫描替代股本专用证据门。
5. 建立分证券股数桥，运行 `scripts/common/validate_equity_evidence.py`。通过后，以不复权近端收盘价 × 估值日分证券股数 × 同日汇率反向勾稽独立市值；差异超过 2% 时返回证据和股数桥排错。
6. 按`references/data-source-disclosure.md`建立`data-source-ledger.json`，逐字段披露实际采用值、来源、链接、本地证据、报告期、公开日、字段位置、单位、币种、统计口径、调整和冲突选择。
7. 建立`assumption-evidence-matrix.json`，把重大假设连接到历史序列、业务驱动、外部证据、预测逻辑、相对历史趋势解释和失效条件。DCF逐项披露无风险利率、Beta、股权风险溢价、债务成本、税率、资本结构和永续增长率的依据。
8. 冻结字段映射、模型驱动、情景依据和交付物。区分公开事实、外部估计、分析调整、自主假设和模型推导；不得使用估值日后才公开的信息。
9. 使用工作流指定脚本完成标准化、计算和验证，不用语言模型口算或手填第二套关键结果。未知必需输入保持空白或 `NA`；只有模块合约明确为“不适用”的可选项才写显式 0。
10. 三表、DCF、LBO和可比公司正式任务均强制生成中文、可编辑、公式驱动的 `.xlsx`，并将该工作簿作为模型计算、质量审计和在线导入的唯一正式源文件。生成前必须按强制读取完整性协议完整读取 `lark-sheets/SKILL.md`，并完整读取、遵循 `lark-sheets/references/ref-financial-modeling-standards`，以生成符合专业金融财务规范的表格。LBO与可比公司默认只生成一个用户可见的表格产物：结论摘要、方法口径、数据来源、风险失效条件和模型检查必须内嵌同一工作簿，不得默认生成或交付Markdown、飞书文档或第二份报告；只有用户明确要求独立报告时才可附加，且不得形成第二套计算或替代该工作簿。本条的“飞书文档”不包括第15条强制交付的飞书在线表格。只解释方法且不输出预测、估值、倍数或回报的非正式问答可不生成工作簿。加载可用的电子表格能力并运行 `scripts/common/detect_workbook_engines.py`。统一使用OpenPyXL和公共公式语义编译器生成工作簿；不得因环境差异而临时拼接坐标公式。
11. 生成工作簿前按`references/model-and-artifact-controls.md`建立`model-contract.json`、`formula-contract.json`、`cell-map.json`和布局锁，冻结prompt驱动、关键公式路径、场景、覆盖区域、单位恒等式、反向DCF和检查单元格；禁止语言模型直接手写关键A1坐标公式。
12. 工作簿必须包含“数据来源”“历史数据与口径”“假设依据”和“模型检查”，关键输入通过来源编号或假设编号连接披露台账。保存后关闭并重新打开，以LibreOffice隔离重算并回读，然后只通过统一入口`scripts/quality/audit_model.py`检查prompt覆盖、公式穿透、场景错位、单位倍率、多证券恒等式、反向DCF残差及静态PASS；再运行现有结构、公式语义、直接产物和视觉审计。
13. 按`references/model-and-artifact-controls.md`把原子检查整合为G0至G5。运行`scripts/quality/run_quality_gates.py`生成阶段结果、`quality-report.json`、`release-decision.json`和`artifact-manifest.json`；缺少机器结果不得手填PASS。
14. 按 `references/delivery-package-contract.md` 打包。工作簿、来源披露、假设证据链、公式语义合约、布局映射、单元格追溯、回读快照和审计结果必须绑定同一最终工作簿SHA-256。最终回答只从`release-decision.json`读取结论权限；仅当G0至G5全部`PASS`且`conclusion_allowed=true`时，才输出目标价、估值区间、上涨下跌空间、MOIC/IRR、推荐倍数、“市场定价合理”或“模型完成”。
15. 最终交付必须采用飞书在线表格。即使用户要求“做个 Excel”“提供 Excel”或“需要 `.xlsx` 文件”，也必须先按第10至14条生成并审计最终 `.xlsx`，再调用 `lark-cli sheets +workbook-import` 将该最终工作簿导入为飞书在线表格。导入对象必须是已完成隔离重算、直接产物审计、质量门检查和SHA-256锁定的最终 `.xlsx`；不得导入临时文件、未审计版本或与 `artifact-manifest.json` 哈希不一致的版本。导入成功并取得有效飞书在线表格链接后，必须调用 `NotifyHuman` 工具向用户提供该链接。飞书在线表格是默认用户交付入口；`.xlsx` 保留为模型源文件、审计对象和导入源文件，可按平台能力或用户明确要求作为附件补充，但不得替代在线表格链接。只有G0至G5全部为 `PASS`、`release-decision.json.conclusion_allowed=true`、导入成功、已取得有效链接且 `NotifyHuman` 调用成功时，才能声称交付完成。导入失败、链接无效、表格不可访问或通知失败时，交付状态必须为 `INCOMPLETE`，仅报告失败环节、错误信息和修复动作，不得声称在线表格已交付。

## 不可绕过的结论门

- 摘要、正文、Excel、JSON、情景和敏感性必须引用同一确定性计算内核或来源单元格。
- 最新公告扫描必须覆盖至信息截止日；发现的公告均须纳入、判定不重大或标记为阻断。
- 历史财务必须与正式披露锚点勾稽；三表必须联动且平衡。
- 关键历史财务和估值输入逐字段披露来源链接、报告期、公开日、字段位置、单位、币种和统计口径。
- 重大预测假设形成“历史数据—业务驱动—预测逻辑—模型参数”的证据链，并解释相对历史趋势的变化。
- 股价、股数、汇率、独立市值和公司行动采用同一估值时点口径；A/H/ADR 等证券逐类计算后汇总。
- 量价模型必须显式记录数量、价格、成本、单位与币种换算、产量至销量桥及来源 ID。
- prompt明确要求的每个经营驱动必须在`model-contract.json`中出现，并沿实际Excel公式依赖到关键输出；只有标签或静态数值不算完成。
- 汇率只能转换价格或价值，不能转换股数；摘要场景、证券类别、单位倍率和源结果必须由统一模型审计逐项复核。
- “模型检查”中的静态`PASS`不构成审计证据；反向DCF必须将隐含变量代回正向模型并满足市场价值残差容差。
- 工作簿哈希必须与直接审计对象一致，关键派生单元格必须是公式。
- 每个关键公式的实际依赖必须匹配语义合约；引用文本标签、标题、说明、错误假设、错误期间、错误证券、错误单位或未经声明的单元格时阻断。
- 公式依赖图不得存在直接自引用、跨单元格循环或跨工作表循环。最终数值与Python结果巧合一致不能替代依赖和中间节点验证。
- 四个工作流的正式交付均必须包含通过审计的公式工作簿；报告或JSON不得代替工作簿。LBO与可比公司默认用户交付面只出现一个表格产物，并以由最终 `.xlsx` 导入的飞书在线表格作为强制交付入口；独立报告仅在用户明确要求时附加。
- 免责声明不能恢复被质量门压制的数字；审计环境不可用、结果文件缺失或任一阶段为`INCOMPLETE`时，只能输出限制、失败检查、待补证据和下一步。
- 最终回答不得自行判断是否可以发布结论，只能遵守统一执行器生成的`release-decision.json`。
- 任一必需质量门为 `FAIL` 或 `INCOMPLETE` 时，保留该状态和原因，不输出被阻断的估值或回报结论。

用简体中文交付。数据不足时给出限制、待补证据和可执行的下一步，不制造伪精确结论。

<!-- END OF FILE: SKILL.md -->
