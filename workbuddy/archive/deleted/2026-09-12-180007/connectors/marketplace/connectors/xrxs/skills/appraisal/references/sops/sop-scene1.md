# 场景一：绩效结果分析与岗位适配风险排查

> **阅读提示：** 本文档为场景一的详细步骤，通用约定见 [`common.md`](common.md)。命中本场景后严格按下列步骤执行，不得跳过、不得自行发明等价命令序列。**查询被考核对象前必须先读 [`../query-assessee-infos-guide.md`](../query-assessee-infos-guide.md)**（`searchMode`/`stage`/`filters`/分页/异常的唯一权威依据）。
>
> **接口约束（本场景强制）：** 本场景**只调用** `queryAssesseeInfos`（唯一数据查询接口）与**解析辅助接口**——`searchDepartment`/`searchJob`/`searchRank`（名称→ID）、`getPlanPeriodDefinitions`（周期概念→枚举值，仅用户提供周期时调用）。**禁止调用**方案定位（`batchQueryPlanInfos`）、档位设置（`batchQueryPlanResultSettings`）、补得分（`batchQueryAssesseeDimensionScores`/`batchQueryAssesseeTargetScores`）等其他接口——单方案需要 **planId 由用户直接提供**；档位**从查询返回的 `finalLevel` 推导**。

## 适用场景与触发话术

- 用户话术示例（含同义表达）：
  - 「帮我分析一下XX部门XX季度（年度）绩效结果，哪些人存在岗位适配风险」
  - 「XX部门这季度绩效出来了吗？帮我看下谁绩效垫底」
  - 「找出XX部门XX年Q3绩效最差的人」
  - 「分析下XX季度组织绩效结果，哪些部门垫底」
  - 「帮我看看试用期绩效结果，有没有风险人员」
- 关键词：部门、季度/年度/方案、绩效结果、岗位适配、风险、垫底、末位、组织绩效、试用期。

> **场景定位：** 本场景覆盖**三种绩效类型**——**个人绩效、组织绩效、试用期绩效**，核心链路为「**确认绩效类型 → 收集筛选条件并解析为 ID → 确定查询方式 → 收敛数据量 → `queryAssesseeInfos` 拉取结果 → 档位/风险分析**」。**只读**场景，无写入确认要求。用户只想要「名单/被考核对象」时走[场景六](sop-scene6.md)，不套用本场景的分析流程。

## 前置信息

| 信息 | 必填 | 说明 |
|------|------|------|
| 绩效类型 | 是 | **个人绩效（1）/ 组织绩效（3）/ 试用期绩效（2）**。用户话术未明确时，**先与用户核对分析哪种绩效**（见步骤 1），不猜测 |
| 筛选条件 | 至少一项 | 部门 / 岗位 / 职级 / 年度季度（周期）/ 分数档位等，用于**收敛数据量**；一项都没有时查询必然过大，先向用户收集（见步骤 4） |
| 方案 ID | 条件必填 | **组织绩效：必须提供方案 ID**（跨方案模式不支持组织绩效，只能单方案查询）；个人/试用期：可选——提供了方案 ID 走单方案，未提供直接跨方案查询（**不调用接口解析方案名**） |
| 方案状态偏好 | 否 | 默认已归档（结果已出的周期通常已归档）；个人/试用期跨方案查询时可结合 `planStatuses` 过滤 |

## 执行步骤

**步骤 1 — 确认绩效类型（先决步骤，不可跳过）**

- 三种绩效类型为固定枚举，无需调用接口：**1-个人绩效考核、2-试用期考核、3-组织绩效**。
- **用户话术未明确时，先与用户核对分析哪种绩效**（一句话确认并给出建议，不自行猜测）：
  - 「XX部门员工绩效 / 谁垫底 / 哪些人有风险」→ 默认**个人绩效**，与用户确认。
  - 「XX部门（组织）绩效结果」且语境是部门整体、或明确说「组织绩效」→ **组织绩效**，与用户确认。
  - 话术含「试用期 / 转正评估」→ **试用期绩效**。
- 确定类型后的分支规则：
  - **组织绩效（3）**：只能按**单个方案**查询，**必须由用户提供方案 ID**（步骤 3），无法直接跨方案检索，也不调用接口搜索方案。
  - **个人绩效（1）/ 试用期绩效（2）**：**可直接查询**——用户提供方案 ID 走单方案（步骤 6-A），未提供方案 ID 直接按筛选条件跨方案检索（步骤 6-B）。

**步骤 2 — 收集筛选条件并解析为 ID**

凡用户提供的实体类筛选，**必须先解析为业务 ID 再放进 `filters`**（禁止把名称字符串当 ID 用）：

| 用户提供 | 解析命令 | 取 ID / 值 |
|----------|----------|------------|
| 部门名 | `xrxs-cli appraisal searchDepartment --keyword "<部门名>" --limit 50` | `departmentId` |
| 岗位名 | `xrxs-cli appraisal searchJob --keyword "<岗位名>" --limit 50` | `jobId` |
| 职级名 | `xrxs-cli appraisal searchRank --keyword "<职级名>" --limit 50` | `rankId` |
| 周期概念（季度/月度/半年度/年度等） | **枚举已内联，直接查下表**（禁止调用 `getPlanPeriodDefinitions`） | `planPeriods` 真实枚举值 |

- 返回字段名以实际结果为准（取精确匹配项的 id）；命中多个近似项时**列出候选让用户确认**，不自行取第一个。
- **岗位/职级筛选仅个人绩效、试用期绩效支持**（`filters.jobIds` / `filters.rankIds`）；**组织绩效传岗位/职级会报错**——删除不适用条件并说明组织对象不支持。
- **周期枚举表（已内联，禁止调用 `getPlanPeriodDefinitions` 接口）**：

| planPeriod 枚举值 | 含义 | planPeriod 枚举值 | 含义 |
|---|---|---|---|
| -1 | 试用期 | 14 | 七月八月 |
| 1 | 年度 | 15 | 八月九月 |
| 2 | 上半年 | 16 | 九月十月 |
| 3 | 下半年 | 17 | 十月十一月 |
| 4 | 第一季度 | 18 | 十一月十二月 |
| 5 | 第二季度 | 19 | 十二月一月 |
| 6 | 第三季度 | 20 | 一月 |
| 7 | 第四季度 | 21 | 二月 |
| 8 | 一月二月 | 22 | 三月 |
| 9 | 二月三月 | 23 | 四月 |
| 10 | 三月四月 | 24 | 五月 |
| 11 | 四月五月 | 25 | 六月 |
| 12 | 五月六月 | 26 | 七月 |
| 13 | 六月七月 | 27~31 | 八月~十二月（27=八月 … 31=十二月） |

- **周期解析（用户提供周期概念时）**：按上表将用户说法映射为枚举值（如「2026年三季度」「Q3」→ `planPeriods:[6]`；「月度」需用户明确哪个月 → `planPeriods:[<对应月份值>]`；「上半年」→ `[2]`；「年度」→ `[1]`；「双月」→ `[8~19]`），与年份一起放进 `filters.planPeriods` / `filters.planYear`（如「2026年三季度」→ `planYear:2026` + `planPeriods:[6]`）。**禁止调用 `getPlanPeriodDefinitions` 接口、禁止把月份数字当枚举、禁止猜测枚举值**（见 guide 第 6 节）。周期解析主要用于**跨方案直接查询**（单方案已由 planId 确定，无需再传周期）。
- **其他筛选（`finalScore` / `finalLevels` / `planStatuses` 等）直接使用用户提供或明确确认的值，不需要也不允许调用其他接口解析**；`finalLevels` 用步骤 6 从返回结果中确认的真实档位名。
- 更多 `filters` 字段及其取值规则见 [`../query-assessee-infos-guide.md`](../query-assessee-infos-guide.md) 第 6 节；**拿不准真实取值的枚举（如 `hireTypes`/`employeeStatuses`）不猜编号、不传，改用已确认的筛选**。

**步骤 3 — 确定查询方式（按绩效类型与用户提供的信息）**

| 绩效类型 | 用户提供 | 查询方式 | 说明 |
|----------|----------|----------|------|
| 个人/试用期 | 方案 ID | 单方案（`PLAN_SUBJECTS`） | 直接使用该 planId，**不搜索方案** |
| 个人/试用期 | 未提供方案 ID | 跨方案（`PERSONAL_PERFORMANCE_RECORDS`） | 按筛选条件直接检索 |
| 组织绩效 | **必须提供方案 ID** | 单方案（`PLAN_SUBJECTS`） | **未提供方案 ID 时请用户提供**，不搜索方案、不猜测 |

- 用户给出的是**方案名称而非 ID**：不调用接口解析；个人/试用期改为跨方案按条件查询，组织绩效请用户提供方案 ID。

**步骤 4 — 数据量宽泛度检查（本场景尽量不分页）**

**查询前（必须）**：当前条件能收敛数据量吗？

- **无方案 + 无部门 + 无年度/季度 + 无任何其他筛选 → 数据量必然过大**，先向用户收集过滤条件（部门 / 岗位 / 职级 / 年度季度 / 分数或档位范围，**任选其一即可**），收集到再查询；**禁止空条件查全公司**。
- 组织绩效方案通常覆盖全公司组织对象：**必须至少提供部门筛选，或由用户明确「分析方案内全部对象」**，避免一次拉取过大。

**查询后（必须）**：结果是否触及分页边界？

- 首查一律 `pageNum:1, pageSize:100`（上限）。若返回条数 = 100 且仍存在下一页（`totalPageNum > 1` / `recordsTotal > 100`）→ **停止翻页**，告知用户当前范围结果超过 100 条，请其**补充过滤条件**（部门 / 岗位 / 职级 / 分数档位 / 年度周期）后重查。
- **本场景尽量不要分页拉全**；仅当用户**明确要求全量分析**该范围时，才按 guide 第 10 节分页拉全。

**步骤 5 — 查询被考核人明细（`queryAssesseeInfos`，尽量单次请求）**

**A. 单方案（个人/试用期/组织绩效统一走 `PLAN_SUBJECTS`，需用户提供 planId）**

个人/试用期绩效：

```bash
xrxs-cli appraisal queryAssesseeInfos --fields "planId,planName,planType,assessBizId,employeeId,employeeName,jobNumber,department,departmentPathIdList,departmentPathNameList,jobName,rank,flowName,inspectionStatus,finalScore,finalLevel,finalCoefficient,selfScore,systemScore,confirmScore,confirmLevel,rusultConfirmAdjust,examRejected,resultConfirmSignStatus" --request-body '{"searchMode":"PLAN_SUBJECTS","planId":"<planId>","stage":{"mode":"ALL"},"filters":{"departmentIds":["<部门id>"],"jobIds":["<岗位id>"],"rankIds":["<职级id>"]},"pageNum":1,"pageSize":100}'
```

组织绩效（`--fields` 换组织字段，`filters` 只能含组织适用项）：

```bash
xrxs-cli appraisal queryAssesseeInfos --fields "planId,planName,planType,assessBizId,departmentId,department,departmentPathNameList,departmentAdminName,flowName,inspectionStatus,finalScore,finalLevel,assesseeStatus" --request-body '{"searchMode":"PLAN_SUBJECTS","planId":"<组织绩效planId>","stage":{"mode":"ALL"},"filters":{"departmentIds":["<部门id>"]},"pageNum":1,"pageSize":100}'
```

**B. 跨方案（个人/试用期直接查询，未提供方案 ID 时）**

```bash
xrxs-cli appraisal queryAssesseeInfos --fields "planId,planName,planType,planStatus,planPeriod,assessBizId,employeeId,employeeName,jobNumber,department,jobName,rank,finalScore,finalLevel" --request-body '{"searchMode":"PERSONAL_PERFORMANCE_RECORDS","planTypes":[1],"stage":{"mode":"ALL"},"filters":{"departmentIds":["<部门id>"],"jobIds":["<岗位id>"],"rankIds":["<职级id>"],"planYear":2026,"planPeriods":[<周期枚举值>]},"sortOrders":[{"field":"planStartTime","order":"desc"}],"pageNum":1,"pageSize":100}'
```

- `planTypes` 按类型传：个人绩效 `[1]`、试用期绩效 `[2]`；跨方案模式仅支持这两类。
- 试用期绩效直接查询同理（`planTypes:[2]`）。
- **周期与年份**：用户提供周期概念（如「2026年三季度」）时，`filters` 同时带 `planYear` 与 `planPeriods`（枚举值来自步骤 2 的 `getPlanPeriodDefinitions`）；用户未提供周期就不传。
- 跨方案默认按 `planStartTime desc` 排序（最新在前），便于分析最近一期结果。

**通用约束（两个分支都适用）：**

- **必须带 `--fields` 压缩**：`queryAssesseeInfos` 全字段返回极大（实测 37 人 ≈ 110KB），不带会触发工具层 50KB 截断，模型会把截断误判为「接口服务内部错误」。
- **新范式核心：`searchMode:"PLAN_SUBJECTS"` + `planId`（或 `PERSONAL_PERFORMANCE_RECORDS` + `planTypes`）+ `stage.mode:"ALL"` + `filters`（业务化筛选）**。
- **组织绩效 `employeeId`/`employeeName` 为空是正常现象**，用 `assessBizId`（组织对象 ID）+ `departmentId`/`department`/`departmentPathNameList`/`departmentAdminName` 展示，**不得因员工字段为空丢弃记录**。
- `filters` 中只放步骤 2 解析出的 ID；无对应条件就不传（不传 null）。
- 返回为**平铺列表**，本地提炼用 `--jq`（不带 `.data` 前缀），例如：

```bash
--jq 'map({employeeId,employeeName,department,jobName,rank,flowName,inspectionStatus,finalScore,finalLevel})'
```

- **兜底（`filters.departmentIds` 过滤失败，或需「仅本部门、不含下级子部门」时）**：去掉 `filters` 拉取后按部门路径本地过滤（`departmentIds` 默认按路径匹配**含下级部门**；用户要求仅本部门时用以下方式）：

```bash
xrxs-cli appraisal queryAssesseeInfos --fields "planId,planName,planType,assessBizId,employeeId,employeeName,jobNumber,department,departmentPathIdList,departmentPathNameList,jobName,rank,flowName,inspectionStatus,finalScore,finalLevel,finalCoefficient,rusultConfirmAdjust" --request-body '{"searchMode":"PLAN_SUBJECTS","planId":"<planId>","stage":{"mode":"ALL"},"pageNum":1,"pageSize":100}' --jq '[.data[] | select((.departmentPathIdList // []) | index("<部门id>"))] | {count:length, list: map({employeeId,employeeName,department,departmentPathNameList,jobName,rank,flowName,inspectionStatus,finalScore,finalLevel,finalCoefficient,rusultConfirmAdjust})}'
```

- 数据量仍超 100 条时回到步骤 4 的「查询后」规则（停止翻页、让用户收敛），不自行翻页。

**步骤 6 — 判定与分档（基于返回结果推导，不调用其他接口）**

- 筛选：只保留本次分析范围内的人员/组织（以明细返回的部门/岗位/职级字段为准）。
- **档位推导**：收集返回结果中的 `finalLevel` 值集合（如 S/A/B/C/D、优秀/良好/合格/不合格），按已知档位顺序确定**最末档**与**倒数第二档**；顺序无法确定时结合 `finalScore` 排序辅助判断，仍不确定则**询问用户档位排序**。
- **判定**：档位为**最末档 → 高风险**；**倒数第二档 → 中风险**；其余 → 无风险（不列入风险名单，如需可附观察名单）。
- **无档位**（如试用期「通过/不通过」，或返回无 `finalLevel`）→ 退回分数阈值：基于返回的 `finalScore` 向用户确认阈值（如总分低于 60 分视为高风险），或按范围内排名末位 10% 判定。
- **返回既无 `finalLevel` 也无 `finalScore`** → 如实说明该方案结果数据缺失，无法做分档分析（**不调用其他接口补查**），基于已有字段给出名单与提示。
- **组织绩效**：对象为**组织（部门）**，风险名单按组织对象输出，不套员工字段。

**步骤 7 — 汇总与输出**

- 按下方「输出模板」拼装结果：范围说明 + 结果汇总 + 风险名单表格 + 模板化行动建议。
- 行动建议为模板话术，不额外拉取员工详情：
  - **高风险**：建议启动绩效改进计划（PIP），或安排岗位适配性评估 / 调岗沟通（组织绩效为负责人绩效面谈 / 组织架构评估）。
  - **中风险**：建议进行目标对齐与定期辅导，下期绩效重点跟进。

## 异常分支

| 异常情况 | 处理方式 |
|----------|----------|
| 绩效类型不明确 | 与用户核对分析哪种绩效（个人/组织/试用期），给出建议，不猜测 |
| 组织绩效未提供方案 ID | 请用户提供组织绩效方案 ID（不调用接口搜索方案）；提供前不查询 |
| 用户只给方案名称（非 ID） | 不解析方案名；个人/试用期改为跨方案按条件查询，组织绩效请用户提供方案 ID |
| 查询条件过宽（无方案/无部门/无年度等） | 禁止空条件查询；先向用户收集至少一项过滤条件（部门/岗位/职级/年度季度/分数档位） |
| 结果超 100 条触及分页边界 | 停止翻页，请用户补充过滤条件后重查；仅用户明确要求全量时才分页拉全 |
| 部门/岗位/职级搜不到 | 提示用户确认全称或上级层级；若返回多个近似项，列出让用户确认 |
| 用户提供的周期无法映射为枚举（如「上旬」「每周」） | 不猜测周期值；说明支持周期粒度（季度/月度/半年度/年度）或请用户提供方案 ID |
| 组织绩效传了岗位/职级等不适用筛选 | 删除不适用条件并说明组织对象不支持；若该条件为用户核心意图则与用户说明 |
| 档位顺序无法确定 | 结合 `finalScore` 排序辅助判断；仍不确定则询问用户档位排序 |
| 返回无 `finalLevel`/`finalScore` | 退回分数阈值（基于返回分数）或按排名末位 10% 判定；两者都缺则如实说明数据缺失，不调用其他接口补查 |
| 明细查询为空 | 先确认参数（planId、filters 字段）无误，再如实报告该范围无被考核记录 |
| 风险名单为空 | 如实报告：该范围无低绩效人员，无需干预，正常结束 |

## 输出模板

### 个人 / 试用期绩效

```markdown
## XX部门 2026年三季度 个人绩效结果与岗位适配风险分析

**绩效类型**：个人绩效（试用期绩效则标注试用期考核）｜ **范围**：<部门全称>（含下级部门/仅本部门）<岗位/职级筛选，无则省略>｜ **方案**：<方案ID>（跨方案查询时列命中方案及数量）

### 结果汇总
- 被考核总人数：N 人
- 高风险（最末档 <D>）：N 人，占比 X%
- 中风险（倒数第二档 <C>）：N 人，占比 X%

### 风险名单

| 姓名 | 部门 | 岗位 | 职级 | 档位 | 评分 | 风险等级 |
|------|------|------|------|------|------|----------|
| 张三 | XX部 | — | — | D | 52 | 高风险 |
| 李四 | XX部 | — | — | C | 68 | 中风险 |

> 岗位/职级列以被考核人明细返回为准，未返回则留「—」，不额外拉取。

### 行动建议
- **高风险（建议优先处理）**：建议启动绩效改进计划（PIP），或安排岗位适配性评估 / 调岗沟通。涉及人员：张三…
- **中风险（持续关注）**：建议目标对齐与定期辅导，下期绩效重点跟进。涉及人员：李四…
```

### 组织绩效

```markdown
## 2026年三季度 组织绩效结果与风险分析

**绩效类型**：组织绩效｜ **方案**：<方案ID>｜ **范围**：<部门筛选，未过滤则为方案内全部组织对象>

### 结果汇总
- 被考核组织（部门）总数：N 个
- 高风险（最末档 <D>）：N 个，占比 X%
- 中风险（倒数第二档 <C>）：N 个，占比 X%

### 风险名单

| 组织（部门） | 负责人 | 档位 | 评分 | 风险等级 |
|--------------|--------|------|------|----------|
| XX事业部 | — | D | 52 | 高风险 |
| YY中心 | — | C | 68 | 中风险 |

### 行动建议
- **高风险（建议优先处理）**：建议启动组织绩效改进计划（PIP），或安排负责人绩效面谈 / 组织架构评估。涉及：XX事业部…
- **中风险（持续关注）**：建议目标对齐与定期辅导，下期绩效重点跟进。涉及：YY中心…
```
