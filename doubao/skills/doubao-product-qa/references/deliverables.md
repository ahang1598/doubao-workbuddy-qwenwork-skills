# QA 交付物规范

## 目录

- [推荐目录](#推荐目录)
- [唯一数据源与输出等级](#唯一数据源与输出等级)
- [状态与统计口径](#状态与统计口径)
- [需求追踪](#需求追踪)
- [测试用例](#测试用例)
- [Bug](#bug)
- [测试报告](#测试报告)
- [最小交付策略](#最小交付策略)
- [外部载体投影](#外部载体投影)

## 推荐目录

```text
qa-results/<feature-slug>/
├── qa-run.json
├── 00-input-notes.md
├── 01-test-plan.md
├── 02-traceability.csv
├── 03-test-cases.csv
├── 04-acceptance-checklist.md
├── 05-risks.md
├── 06-bugs.md
├── 07-test-report.md
├── 08-device-matrix.json
├── 09-automation-summary.json
├── test-data-manifest.json
└── evidence/
    ├── screenshots/
    ├── traces/
    ├── console/
    └── network/
```

`qa-run.json` 是唯一**结果与计数**真相源：需求、风险机制、用例、执行、证据、Bug、变更、环境、覆盖、发布结论和测试数据的 ID、状态与关联只在这里维护。

**正文叙述不在这里，也不由 renderer 拼。** 报告、方案、Bug 单的行文由模型按体裁卡撰写（见 [report-shapes.md](report-shapes.md)）；`scripts/render_qa_artifacts.py` 只生成真正二维的附表（追踪矩阵、用例 CSV、设备摘要、测试数据清单）并回头核对正文里的数字。飞书文档、表格、Base 与 PPT 也只是带 `source_revision` 的外部投影。不要同时保留 `test-plan.md` 和 `01-test-plan.md` 之类重复文件。

每份 canonical 记录至少包含：

- `request_contract`：用户目标摘要/hash、允许的来源与轮次、证据政策、交付格式/文件名/章节/顺序；
- `phase_receipts`：当前 canonical 指纹下已通过的 baseline/design/execution/change/release 回执；
- `revision`：当前内容版本；
- `change_ledger`：增删改、恢复、替换与收缩范围的数量/集合台账；
- `open_questions`：最小确认问题、影响、状态与下一动作；
- `input.artifacts`：逐项记录材料定位、版本、读取状态和完整性核对；
- `risk_mechanisms`：失效机制、业务影响、oracle 与双向用例映射；
- `acceptance_checks`：关联用例的决策级验收项，状态只从执行派生；
- `delivery_manifest`：飞书或本地产物的真实定位、回读状态和来源 revision。

## 唯一数据源与输出等级

任务范围 profile：

| Profile | 必需生成产物 |
|---|---|
| `smoke` | `qa-run.json` + `07-test-report.md` |
| `plan` | `qa-run.json` + 计划 + RTM + 用例 + 风险 |
| `execution` | `qa-run.json` + 用例 + Bug + 报告；证据在 JSON 中登记 |
| `full` | `qa-run.json` + `00`–`07` 全部产物 |
| `hotfix` | `qa-run.json` + 输入 + 最小用例 + 验收 + 风险/Bug/报告 |
| `bug` | `qa-run.json` + Bug 报告 |
| `mobile` | 兼容入口，等价于 `full` + 设备矩阵 + 自动化摘要 |

平台和任务范围本质正交；移动端一次性冒烟仍可使用 `smoke`，并在 `qa-run.json` 记录平台和设备。`mobile` 只用于完整移动端交付兼容。

用例状态由最近一次 `execution` 派生：没有执行为“未执行”，`pending_confirmation` 为“待确认”，复测不会覆盖或删除历史执行和首次失败证据。不要在 `cases` 中重复维护状态。通过执行必须包含明确断言或证据引用；截图策略为 off 时可使用 DOM、日志、请求响应或结构化人工观察。

按任务裁剪文件。完整提测使用全部文件；只做 PRD 分析时可停在 `05-risks.md`；只分析单个 Bug 时仅产出 `06-bugs.md` 和证据。

涉及 iOS、Android 或小程序自动化时增加 `08-device-matrix.json` 和 `09-automation-summary.json`。前者保存计划运行的目标与命令，后者聚合命令级状态和产物路径；测试报告再把命令结果映射到 QA 用例与发布风险。

当宿主、设备、签名、工具或授权使目标自动化不可用时，不新增 profile；设置 `selected_path=manual_handoff`，并额外生成 `10-manual-test-guide.md` 与以下人工执行包：

```text
manual-handoff/
├── 01-manual-test-plan.md
├── 02-manual-test-cases.csv
├── 03-manual-acceptance-checklist.md
├── 04-evidence-guide.md
└── 05-risks-and-blockers.md
```

这些文件全部从根目录唯一的 `qa-run.json` 派生，不在人工目录复制第二份 JSON。人工 QA 只能填写 `02-manual-test-cases.csv` 的结果列；交回后运行：

```bash
python3 scripts/import_manual_results.py qa-results/<feature>/manual-handoff/02-manual-test-cases.csv
```

Windows PowerShell 使用当前可用的 `python` 或 `py -3`。导入器归档原始提交、追加人工执行和证据、保留首次失败，再重新生成下一轮执行表、Bug 和测试报告。

`00-input-notes.md` 记录输入来源、版本、环境、账号/角色、用户选择的截图策略、假设、冲突和待确认项。不要复制整个 PRD。

`input.artifacts` 每项至少包含：

```text
id,type,locator,version,access_status,coverage_note,completeness_checked
```

- `id` 使用 `SRC-NNN`。
- `access_status` 只用 `read/blocked/not_applicable`。
- `blocked` 必须写 `blocked_reason` 与 `minimal_unblock_action`。
- `spreadsheet/archive` 还要记录 `item_count` 与 `reviewed_item_count`；`read` 时两者必须相等。这里的 item 分别指 Sheet 与压缩包成员。
- 链接需要登录或无权限时记录为 `blocked`，不得根据标题、文件名或历史印象补写内容。

测试本地 Web 工程时还记录启动命令、工作目录、PID/会话、URL/端口、readiness、依赖与环境文件状态，以及结束时是否已清理。

## 状态与统计口径

用例状态仅使用：

- `未执行`：尚未运行；
- `通过`：已执行且所有预期满足；
- `失败`：已执行且产品结果不满足预期；
- `待确认`：有观察但证据、样本或产品规则不足，尚不能判通过、失败或正式 Bug；
- `阻塞`：因环境、数据、账号或上游缺陷无法完成；
- `不适用`：经确认不属于当前平台/版本/范围，并记录理由。

统计时排除 `不适用`：

```text
执行率 = (通过 + 失败 + 待确认 + 阻塞) / (总数 - 不适用)
通过率 = 通过 / (通过 + 失败)
需求覆盖率 = 有至少一个有效用例的需求数 / 有效需求总数
```

通过率不包含阻塞并不代表阻塞风险消失；报告必须单列阻塞。

## 需求追踪

`02-traceability.csv` 字段：

```text
requirement_id,requirement,source,risk,actor,trigger,rule,observable_result,impact_scope,risk_mechanism_ids,test_case_ids,status,notes
```

- `source` 使用文件名+章节、URL+页面区域或代码位置。
- `risk` 使用 `P0/P1/P2/P3`。
- 多个用例 ID 用英文分号 `;` 分隔。
- `status` 使用 `已覆盖/部分覆盖/未覆盖/阻塞/不适用`。
- `部分覆盖/未覆盖/阻塞` 必须在 `notes` 解释。
- P0/P1 的 canonical 需求必须包含 `behavior.actor/precondition/trigger/rule/state_change/observable_result/failure_behavior` 与非空 `impact_scope`。没有状态变化时写“无状态变化”，不允许删除该字段。

## 测试用例

`03-test-cases.csv` 字段：

```text
case_id,module,title,priority,type,preconditions,steps,test_data,expected_result,requirement_ids,risk_mechanism_ids,release_blocking_reason,automation_candidate,execution_mode,assigned_to,manual_reason,evidence_expected,status,notes
```

字段约束：

- `case_id`：`TC-<模块>-NNN`，稳定且唯一。
- `priority`：`P0/P1/P2/P3`。
- `type`：`功能/边界/异常/状态/权限/兼容/接口/回归/冒烟/可访问性/性能/安全/探索`。
- `steps`：在单元格内用 `1. ...\n2. ...`；不要把多步压成一句。
- `test_data`：写出具体值、构造规则或数据 fixture。
- `expected_result`：逐层写 UI、响应、数据和副作用中的适用项。
- `requirement_ids`：英文分号分隔；探索用例可填 `RISK-...`。
- `risk_mechanism_ids`：英文分号分隔；P0/P1 必填，并与 `risk_mechanisms.case_ids` 双向一致。
- `release_blocking_reason`：P0 必填，解释失败为何阻断发布；P1–P3 可空。
- `automation_candidate`：`是/否/部分`，在 `notes` 说明阻碍。
- `execution_mode`：`automated/manual/hybrid`；当前自动化不可运行且需要人操作时使用 `manual`，一部分可自动验证时使用 `hybrid`。
- `manual_reason`：人工或混合用例必填，明确是宿主平台、设备、签名、权限、验证码还是其他能力限制。
- `evidence_expected`：人工或混合用例必填，列出截图、录屏、日志、错误文案、版本号、时间点等回传要求。
- `assigned_to`：人工执行的计划负责人或角色；实际操作人记录在 execution 的 `operator`，不要混用。
- `status`：初始为 `未执行`，执行后按统一口径更新。

P0/P1 的 `test_data` 不接受“样例为准、正常数据、合理值、同上”；必须给固定值、边界构造式或可复现 fixture。预期不接受“功能正常、结果正确、符合预期”等不可观察表述。

CSV 使用 UTF-8，包含逗号或换行的单元格必须由标准 CSV writer 正确引用。

## 验收清单

`acceptance_checks` 是决策级清单，不重复维护结果。每项包含：

```text
id,title,type,case_ids,blocking,notes
```

- `id`：`AC-<模块>-NNN`，稳定且唯一。
- `type`：`core_flow/exception/permission_security/compatibility/data_consistency/analytics/performance/defect_blocker/release_config`。
- `case_ids`：至少关联一条用例；一个验收项可以综合多条相同决策目标的用例。
- `blocking`：该项未满足时是否阻断发布；所有 P0 用例必须至少进入一个阻断验收项。
- `status` 不写入 canonical，由关联用例最新执行派生：
  - 任一失败 → 未通过；
  - 无失败但任一阻塞 → 阻塞；
  - 无失败/阻塞但任一未执行 → 待验证；
  - 全部通过 → 通过；
  - 全部不适用 → 不适用。

验收清单通常控制在 15–30 项；小需求可更少。每次输出必须列出总数、通过、未通过、阻塞、待验证、不适用，并满足各状态之和等于总数。没有执行时统一显示“待验证”，不得把未执行写成“不适用”。

## Bug

每个 Bug 使用 `BUG-<模块>-NNN` 并包含：

```markdown
## BUG-模块-001：一句话标题

- 严重程度：S1/S2/S3/S4
- 优先级：P0/P1/P2/P3
- 类型：产品缺陷/需求问题/环境数据/自动化问题/待定
- 证据类别：static_ui/interaction/state/timing/api/crash/flaky/other
- 环境：构建、平台、浏览器/设备、账号角色、功能开关
- 关联：REQ-...；TC-...
- 模块与状态：module；open/in_progress/fixed/pending_retest/closed/rejected/deferred
- reproducibility：always/intermittent/once/not_reproduced
- repro_attempts：总尝试次数
- first_failure_preserved：true/false
- evidence_grade：与 Bug 类型匹配的证据等级
- severity_basis：严重程度的事实依据；证据不足时明确为推测
- confidence：high/medium/low/unknown

### 前置条件
### 复现步骤
### 实际结果
### 期望结果
### 影响范围
### 证据
### 初步分析
### 临时规避与复测建议
```

`analysis` 使用结构化字段：

```text
classification：前端/后端/接口/数据/兼容/性能等问题分类
trigger_hypothesis：数据、环境或操作顺序的触发条件假设
change_correlation：是否可能由近期变更引入；未知时写明需查发布记录
blast_radius：同一共享逻辑可能波及的其他入口、角色、平台或数据
confidence：high/medium/low/unknown
```

`change_correlation` 回答“何时、由哪次变化引入”，`blast_radius` 回答“除了当前入口还影响哪里”，不得用同一句话重复填充。推测必须使用不确定措辞；没有线索时写“证据不足及下一步”，不要伪造根因。

严重程度：

- `S1`：系统不可用、资金/安全/严重数据损坏等灾难影响；
- `S2`：核心功能不可用且无合理绕过；
- `S3`：非核心功能错误或存在可接受绕过；
- `S4`：轻微展示/体验问题，不影响主要任务。

对外只展示上述枚举与中文解释；不要混入 `High/Critical/Blocker` 形成第二套等级。

## 测试报告

报告的章节形状由体裁决定，见 [report-shapes.md](report-shapes.md)——不要套用固定一套。
无论哪种体裁，下列语义都不能缺失（可以合并进别的段，但不能没有）：

1. **执行摘要**：功能、构建、环境、时间和测试类型；
2. **覆盖情况**：需求、风险、平台和未覆盖范围；
3. **执行结果**：总数、通过、失败、待确认、阻塞、未执行、不适用；
4. **缺陷**：按严重程度和状态统计，列出阻断项；
5. **验收摘要**：验收项状态计数、阻断项与总数等式；
6. **风险与未验证项**：说明对上线判断的影响；
7. **发布结论**：建议上线/有条件上线/不建议上线/无法判断及依据；
8. **后续动作**：复测、监控、回滚或责任动作。

任何数字都应从 `qa-run.json` 派生并可复算。没有执行自动化时，不写“自动化通过”。未通过或未执行的 P0、未关闭的 S1/S2、失败的必要数据清理必须约束发布结论。

## 最小交付策略

- 用户只要测试计划：`01-test-plan.md` + 关键风险。
- 用户只要用例：`02-traceability.csv` + `03-test-cases.csv`，保证可追踪。
- 用户只要验收清单：`04-acceptance-checklist.md`，包含 P0/P1 与发布门禁。
- 用户只要 PRD 风险分析：`00-input-notes.md` + `05-risks.md`。
- 用户只要一次性页面冒烟：`qa-run.json` + `07-test-report.md`；`observed_surfaces` 建立可观察覆盖基线。
- 用户要可重复页面执行：`qa-run.json` + 用例 + Bug + 报告 + 证据索引。
- 用户只给一个 Bug：单个标准 Bug 条目，不制造空的计划/报告。
- 用户要求三端自动化：完整交付物 + 设备矩阵 + 自动化 summary + 每目标证据目录。
- 用户的宿主不支持目标平台自动化：正常范围交付物 + `10-manual-test-guide.md` + `manual-handoff/` 人工执行包；所有人工用例显式标记，未回传证据前保持未执行且发布结论无法判断。
- 用户要求紧急 hotfix：输入记录 + 最小用例 + hotfix 验收清单 + 风险/Bug/报告；所有推迟项必须有补测时限。

## 外部载体投影

用户指定的载体优先。豆包文档/表格/PPT 在运行时对应飞书在线对象；Markdown/Office/在线载体的请求契约、回读和唯一发布规则见 [request-delivery-contract.md](request-delivery-contract.md)。在线字段映射见 [lark-delivery.md](lark-delivery.md)：

- 计划、风险、Bug、报告 → 飞书文档；
- 追踪、用例、执行、设备矩阵 → 飞书表格；
- 长期协作状态与关系 → Base；
- go/no-go 评审 → PPT。

用户未指定载体时，叙述型 QA 内容默认豆包文档，二维用例/追踪/矩阵默认豆包表格，汇报演示默认豆包 PPT；方案/报告与用例并存时默认文档 + 表格。Markdown 不属于默认载体，只在用户明确要求时创建。最终交付只能通过 `qa_deliver.py`：它校验产物、必要时创建并回读在线载体，并给出唯一一条上屏调用；请求中的每个文件名都必须有回执。在线载体实际不可用时才交付真实本地替代文件并披露降级，不得编造链接、静默改成 Markdown 或用聊天内容冒充文件。
