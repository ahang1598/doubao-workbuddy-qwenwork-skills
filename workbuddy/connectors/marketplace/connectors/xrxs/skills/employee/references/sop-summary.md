# 员工 SOP 摘要索引（sop-summary）

> **阅读规则（强制）：** 处理任何员工业务需求（**含查询类**，如「查本月入职人员」「查转正记录」「查离职记录」等）时，**第一步必须先读本文件**，用用户话术匹配下方场景索引。**不要因为问题"看起来简单"就直接去读 shortcut 文档自行摸索**——本文件的场景索引已覆盖绝大多数常见查询/操作。
> - **命中**某个场景 → 必须再读 [`sops/`](sops/) 下对应场景文件（`sop-sceneN.md`），**严格按其步骤执行**；通用约定见 [`sops/common.md`](sops/common.md)。
> - **未命中**任何场景 → 回退到 `SKILL.md` 通用规则，**不深挖 SOP 场景文件**，不自行套用相似场景。
> - 同时命中多个场景（如一句话含两个动作）→ 按场景索引顺序逐项执行，每个动作独立确认。
> - ⚠️ 命中场景后**禁止执行 `schema` 查参数**（场景文档已给完整请求体/命令），禁止反复试探接口（如不同 status 值分别查询）；场景文档指定了确切参数（如 `status=0` 在职），直接按文档执行。

---

## 场景索引

| # | 场景 | 触发话术 / 关键词 | 流程要点 | 读写 | 确认方式 | 详情 |
|---|------|-------------------|----------|------|----------|------|
| 一 | 员工转正记录查询与分析 | 「帮我查一下未来一周应转正的员工」「最近有哪些员工逾期转正了，帮我分析一下原因」「查一下已超期未转正的员工名单」等；转正、应转正、待转正、已转正、逾期、超期、转正记录、转正审批、转正方式、考核 | 筛选字段→`searchRegularRecord`（按用户给定窗口/状态/关键字过滤）→`getHumanRules`（必须考核通过才能转正开关）→根据返回的 `regularForm`（转正方式）、`regularApprovalStatus`（转正审批状态）、`appraisalStatus`（考核状态）与规则开关综合分析；到期自动转正则无需发起审批 | 只读 | 无 | [场景一](sops/sop-scene1.md) |
| 二 | 入职信息查询与资料补齐检查 | 「检查本月入职人员信息」「本月入职了哪些人」「检查本周入职人员资料补齐情况」等；入职、本月入职、本周入职、入职人员、资料、必填、补齐 | **已入职信息/名单**：`getEmployeeFilterFields`(filterBizType=1)→`searchEmployee`(entryDate 完整 filters + status=0，dateValues 用 yyyy/MM/dd 非毫秒时间戳)→需部门/工号时按人 `getEmployeeDetail` 补查；**待入职、已超期/资料补齐**：`getEmployeeFilterFields`(filterBizType=2, 日期字段为 pendingEntryDate)→`searchEntryRecord`(状态含待入职+已超期)→`getEntryPendingEmployeeForm`→筛 required 且为空的字段 | 只读 | 无 | [场景二](sops/sop-scene2.md) |
| 三 | 批量入职 | 「帮我批量入职XXX」；批量入职、待入职、入职 | **已知员工ID**: `permission check employee-entryPendingEmployee`(已授权直接提交/未授权先 preview)→`getEntryPendingEmployeeForm`→`entryPendingEmployeePreview`(带完整form)→用户确认→`entryPendingEmployee`；**按关键字查找员工**: 筛选字段→`searchEntryRecord`(入职记录，按状态过滤待入职+已超期)→入职表单→preview→用户确认→正式提交 | 写入 | 用户确认 | [场景三](sops/sop-scene3.md) |
| 四 | 扫描指定周期内离职办理阻塞清单 | 「扫描XX期间离职办理阻塞清单」；离职、阻塞、待处理、逾期 | `searchDismissRecord`(周期)→`getDismissPendingIssueTotal`→按 P0/P1/P2 分组输出 | 只读 | 无 | [场景四](sops/sop-scene4.md) |
| 五 | 批量操作 Excel（教育/工作/培训/证书/联系人/手机号/兼职/自定义分组/子女/员工/成长记录/期权/离职/待入职/奖惩等） | 「批量添加教育经历」「批量更新员工 Excel」「批量导入证书」等；批量、Excel、导入、添加、更新、上传 | `batchListBizTypes`→`batchInit`（取 headerName）→`download_file_for_cli`→`batchParseExcel`→`permission check employee-batchUploadBatch`（true 直接上传 / false 先 preview 再确认上传）→`batchQueryBatchResult` 轮询至 status=true；headerMap 按中文列名匹配，未匹配填 unselect | 写入 | 用户确认 | [场景五](sops/sop-scene5.md) |

---

## 易混淆场景区分

| 场景 | 关键区别 |
|------|----------|
| 一 vs 三 | 场景一=查询与分析转正记录（只读，基于 `searchRegularRecord` 返回字段）；场景三=执行批量入职（写入操作，针对待入职员工） |
| 三 vs 五 | 场景三=**批量入职**（针对待入职员工，直接调用 `getEntryPendingEmployeeForm`/`entryPendingEmployeePreview`/`entryPendingEmployee` 完成入职）；场景五=**批量操作 Excel**（支持教育/工作/培训/证书/联系人/手机号/兼职/自定义分组/子女/员工/成长记录/期权/离职/待入职/奖惩等多种类型，通过 `batchInit`/`batchParseExcel`/`batchUploadBatch` 等 Excel 流程完成添加/更新） |

## 通用要点（命中场景后同样适用）

- **命中场景后直接按场景文档（sops/sop-sceneN.md）执行，无需逐命令执行 schema**；仅在未命中场景（回退 SKILL.md 通用规则）、场景文档未覆盖的命令、或命令报错需确认参数时，才执行 `xrxs-cli schema employee.<command>` 看参数；同一命令最多检查一次，禁止批量轮询无关命令。
- 筛选字段（filters）必须先调 `getEmployeeFilterFields --filterBizType <N>` 获取配置并按规则填值回传，**不猜字段名**（filterBizType 枚举：1-员工搜索 2-入职记录 3-转正记录 4-调岗记录 5-离职记录）。⚠️ filters 必须**原样回传完整筛选条目**（含 fieldId/listGroupId/documentType/dicType/dataSource），仅填 `values`（选项类 `[{"key":".."}]`）或 `dateValues`（日期类 `yyyy/MM/dd` 字符串）；只传最小结构/毫秒时间戳 → 报 `111005000 未知错误`（实测，见 [sops/common.md](sops/common.md) 通用约定）。
- 同一请求体最多拉取一次；分页拉全遵循「分页停止条件」（某页条数 < pageSize 或为空即停）。
- `searchRegularRecord` 按状态/时间查询时**优先**用完整配置 filters 直接过滤（如 `regularRecordStatus`+values 一次查出已超期，实测可用，见[场景一](sops/sop-scene1.md)）；过滤报错或混入其他状态才回退 `filters:[]`+`pageSize:100` 全量拉取、结果内按 `regularRecordStatus`（1待转正/2已转正/3已超期/4未通过）/`regularDate` 本地过滤；禁止试探 pageSize、禁止未确认字段名就填 filters。
- 日期类筛选的 dateValues 用 `yyyy/MM/dd` 字符串（如 `["2026/08/01","2026/08/06"]`），**不是毫秒时间戳**。
- 写入操作（批量入职等）执行前必须向用户确认意图。
- 不要将执行的命令原样返回给用户。
