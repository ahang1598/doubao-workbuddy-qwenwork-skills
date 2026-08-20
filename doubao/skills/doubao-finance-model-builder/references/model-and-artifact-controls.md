# 模型与Excel审计总协议

## 适用范围与状态

本协议是三表、DCF、LBO和可比公司正式任务的全程必读控制文件，合并质量门、模型合约、布局冻结、公式语义、工作簿重算、直接产物和发布审计要求。模块工作流可以增加检查，不得降低本协议。

只使用：

- `PASS`：必需机器检查全部通过，关键结果可从证据、输入、公式追溯到输出。
- `INCOMPLETE`：没有已知错误，但证据、重算环境、模型或交付不完整；只能交付底稿、限制和补充清单。
- `FAIL`：存在时点污染、公式/依赖/单位错误、报表或价值桥不平、计算不一致或哈希失配；禁止结论。
- `NOT_APPLICABLE`：仅由检查注册表确认不适用，不得人工替代必需检查。

不得使用总体`WARN`，不得把免责声明、缓存值、静态`PASS`或“用户打开后会刷新”用于恢复被阻断结论。

## 单一真相与证据

每个关键输入只保留一个正式JSON字段或Excel输入单元格；摘要、模型、情景、敏感性和可选报告必须引用同一来源。至少统一估值日、币种、单位、证券身份、股价、股数、汇率、税率、WACC、终值/退出倍数、企业价值、股权价值、每股价值、MOIC和IRR。

正式任务必须：

1. 完成最新公告扫描，覆盖模型最新已纳入披露公开日至信息截止日；发现项必须纳入、判定不重大或标记阻断。
2. 关键字段逐项保存使用值、原始值、单位、期间、公开日、来源ID、URL/文件、字段位置、标签、调整和冲突选择。
3. 禁止使用估值日后公开的信息回填历史模型；市场字段分别记录自己的日期。
4. 涉及市场价值时冻结官方股本、官方检索结果、公司行动正文和文本快照，再建立估值日分证券股数桥。
5. 分证券以不复权近端收盘价×估值日股数×同日汇率计算市值，并与独立市值反查；默认差异容差2%。
6. 显式处理现金、债务、租赁、优先股、少数股东、投资、养老金和其他索取权，避免重复或遗漏。

## 模型合约

生成Excel前建立：

- `model-contract.json`：用户要求、驱动、关键输出、场景映射、公式覆盖区域、维度恒等式、反向DCF和检查单元格。
- `formula-contract.json`：稳定ASCII字段ID、字段类型、单位、公式模板、必需/允许/禁止依赖、期间、证券和Python基准。
- `cell-map.json`：字段ID到最终单元格或定义名称的一对一映射。
- `layout-lock.json`：工作表顺序、关键区域、合并单元格、定义名称和布局哈希。
- `workbook-contract.json`：必需工作表、公式区、关键输出、确定性期望值、容差和公式化总状态。

关键派生字段必须为`formula`或`output_formula`。公式模板使用`{field_id}`，不得以中文标签、当前活动单元格、临时行号、`INDIRECT`、`OFFSET`或文本拼接隐藏关键依赖。金额、股数、单价、百分比、倍数、期间和币种转换必须显式声明单位与转换字段。

至少验证：

1. prompt每项重大驱动进入`drivers`并沿实际公式依赖到关键输出。
2. 公式实际依赖包含全部必需字段，且不超出允许集合或触发禁止集合。
3. 场景摘要按稳定场景ID映射源单元格，不依赖固定列偏移。
4. 公式区达到合约覆盖率，敏感性和情景重新调用底层模型，不静态调整最终价值。
5. `sum`、`per_share`、`fx`和`linear`恒等式成立；汇率不能转换股数。
6. 反向DCF把隐含变量代回正向模型，市场价值残差在容差内。
7. Excel代表性中间节点和关键输出与确定性Python结果一致。

## 布局与生成

先冻结业务字段和布局，后编译公式。`cell-map.json`生成后禁止插删关键行列、移动区块、重命名或重排被引用工作表、合并公式单元格、覆盖公式区。产品、分部、期间或债务层变化时更新结构化输入和合约，从受控模板完整再生成。

正式工作簿最低包含：

- 三表：封面、假设、经营驱动、明细预测、三张报表、检查、来源。
- DCF：封面、股本与市值桥、历史财务、估值假设、经营预测、DCF、敏感性、检查、来源。
- LBO：封面、交易摘要、假设、Sources & Uses、经营预测、分层债务、现金与利息、退出回报、投资人现金流、回报归因、敏感性、风险、检查、来源。
- 可比公司：封面、结论摘要、目标公司、同行筛选、历史与口径、调整、EV桥、倍数、核心样本、统计、隐含估值、敏感性、风险、检查、来源。

OpenPyXL是正式生成引擎，只负责读写，不能冒充计算。先运行：

```bash
python3 scripts/common/detect_workbook_engines.py
```

没有OpenPyXL时停止；没有独立重算引擎时只能生成`INCOMPLETE`草稿。

## 工作簿验证闭环

最终工作簿按同一路径执行：

1. 只读结构快照：

```bash
python3 scripts/common/inspect_finance_workbook.py model.xlsx workbook-inspect.json
```

记录哈希、工作表状态、区域、公式地址、合并/隐藏、验证、表格、图表、批注、冻结窗格、打印区域、定义名称、外链、计算模式和缓存错误。

2. 公式语义审计：

```bash
python3 scripts/common/audit_formula_semantics.py \
  model.xlsx formula-contract.json formula-semantic-audit.json
```

阻断文本标签引用、错期间/证券/单位、依赖缺失或越界、重复映射、自引用和跨表循环。

3. 隔离重算和直接审计：

```bash
python3 scripts/common/audit_formula_workbook.py \
  model.xlsx workbook-contract.json artifact-audit.json \
  --recalculate required
```

三表使用专属审计器。审计器必须复制最终文件到唯一临时目录，使用唯一LibreOffice配置重算副本，不修改交付文件。超时、非零退出、无输出、重算前后公式地址变化、外链、循环、公式丢失、硬编码、全簿错误值、关键输出超容差或总状态非PASS均为`FAIL`。

4. 统一模型审计：

```bash
python3 scripts/quality/audit_model.py \
  model.xlsx model-contract.json model-audit.json
```

检查prompt覆盖、公式穿透、场景映射、公式覆盖、维度恒等式、反向DCF和检查页防伪。

5. 对所有用户可见工作表执行视觉检查，保存`visual-audit.json`；检查截断、溢出、不可读列宽、异常空白、错误格式、单位和核心结论可读性。

所有审计JSON必须绑定同一最终工作簿SHA-256。修复或补充文字后全部重跑，不得沿用旧哈希。

## 模块专用检查

- 三表：历史锚点、收入与成本驱动、固定资产、债务、现金、权益滚动、三表勾稽、量价单位链和异常数量级。
- DCF：WACC组成、FCFF、折现因子、终值、EV到股权桥、完全稀释每股价值、三情景、5×5敏感性和反向DCF。
- LBO：Sources & Uses、分层债务、利息/PIK、强制摊还、现金扫款、循环额度、最低现金、退出桥、MOIC/XIRR、回报归因和敏感性。
- 可比公司：同行角色、分证券市值、租赁与跨币种、EV桥、核心样本统计、倍数、隐含价值、市场隐含预期和敏感性。

通用审计只能增加模块检查，不能替代模块确定性验证。

## 六阶段质量门与发布

运行：

```bash
python3 scripts/quality/run_quality_gates.py \
  --root task-directory \
  --workflow dcf \
  --hero outputs/model.xlsx \
  --output-dir quality
```

阶段：

| 门 | 必需内容 |
|---|---|
| G0 | 路由、范围、日期、读取完整性、执行计划 |
| G1 | 公告、股本/公司行动、来源、时点和市值反查 |
| G2 | 方法、场景、单位、租赁/WACC/同行、公式与布局合约 |
| G3 | 模块确定性计算和财务勾稽 |
| G4 | 模型审计、公式语义、隔离重算、错误扫描、视觉和哈希 |
| G5 | 跨产物一致性、主要交付物、哈希和发布权限 |

聚合采用失败关闭：任一必需`FAIL`则阶段`FAIL`；无失败但存在缺失/不完整则`INCOMPLETE`；其余均为`PASS`或注册表确认的`NOT_APPLICABLE`才通过。整合器只接受机器结果，不接受手填PASS。

输出`g0-task.json`至`g5-delivery.json`、`quality-report.json`、`release-decision.json`和`artifact-manifest.json`。`release-decision.json`是目标价、估值区间、推荐倍数、上涨下跌空间、MOIC、IRR和“模型完成”的唯一发布权限来源；仅G0至G5全部`PASS`且`conclusion_allowed=true`时允许发布。

## 在线表格交付、可选报告与打包

G0至G5通过后，只将与 `artifact-manifest.json` 哈希一致的最终 `.xlsx` 通过 `lark-cli sheets +workbook-import` 导入为飞书在线表格。取得有效且可访问的链接后，调用当前环境可用的交付工具向用户实际提供链接，并将源文件哈希、导入状态、链接可访问性、实际工具名称、交付状态和交付验证结果记录到 `lark-sheet-delivery.json`。不得因当前环境缺少某个特定名称的工具就跳过交付；应使用环境实际提供的等效交付能力。不存在任何可用交付工具、工具调用失败或用户无法获得有效链接时，将交付状态保持为 `INCOMPLETE`。

LBO和可比公司默认只生成一个用户可见的表格产物。只有用户明确要求独立Markdown或飞书报告时才运行渲染器；本处的飞书报告不包括强制交付的飞书在线表格。报告必须写入`CALCULATED_SHA256:<确定性计算文件SHA-256>`并通过：

```bash
python3 scripts/common/audit_report_artifact.py \
  report.md calculated.json --workflow comps --output report-artifact-audit.json
```

报告不得形成第二套数值。最终打包由`finalize_delivery_package.py`重新核对主要交付物、审计对象、工作流和SHA-256；哈希变化或审计非PASS时强制失败。

<!-- END OF FILE: model-and-artifact-controls.md -->
