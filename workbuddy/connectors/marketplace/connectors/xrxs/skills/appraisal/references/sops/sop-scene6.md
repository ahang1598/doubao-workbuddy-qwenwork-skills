# 场景六：查询考核方案的被考核对象/名单

> **阅读提示：** 本文档为场景六的详细步骤，通用约定见 [`common.md`](common.md)。命中本场景后严格按下列步骤执行，不得跳过、不得自行发明等价命令序列。

## 适用场景与触发话术

- 用户话术示例（含同义表达）：
  - 「查询下这个方案都有哪些被考核对象：20260622【招聘事业部】2025年9月绩效考核方案-plz（4）」
  - 「XX方案有哪些被考核人/名单」
  - 「XX方案都考核了哪些人，帮我列一下」
- 关键词：被考核对象、被考核人、名单、考核了哪些人、方案人员、方案有哪些人。

> **场景定位：** 这是**只读查询**，仅输出方案下的被考核人名单（人数 + 姓名 + 部门 + 所在环节 + 考核组），**不做档位/风险/分数分析**（那是[场景一](sop-scene1.md)）。用户只要「名单/被考核对象」时走本场景，不要套用场景一的部门/档位流程。

## 前置信息

| 信息 | 必填 | 说明 |
|------|------|------|
| 方案名称（或方案 ID） | 是 | 用于定位方案；**任意状态**（未开始/进行中/终止/已归档均可查） |

## 执行步骤

**步骤 1 — 定位方案（任意状态，最多 2 次搜索）**

```bash
xrxs-cli appraisal batchQueryPlanInfos --request-body '{"planType":1,"planStatus":1,"planName":"<方案名关键词>"}'
```

- `planStatus` 必填，枚举（`getPlanStatusDefinitions` 输出为准）：0-未开始，1-进行中，3-终止考核，4-已归档；`planType`：1-绩效考核。
- **搜索策略（关键）：** 用户未给状态时默认先搜 `planStatus:1`（进行中，最常见）；搜不到再以 `planStatus:4`（已归档）**重试 1 次**；仍搜不到或返回多个候选 → 列出候选让用户确认。
- **禁止用多个 planStatus 值轮询搜索**（如 0/1/3/4 挨个搜），合计最多搜 2 次。
- 用用户给的完整方案名做 `planName` 模糊检索；命中后确认返回列表中唯一对应方案，取 `planId`。

**步骤 2 — 获取方案流程（拿 flowId，仅按具体环节查询时执行）**

```bash
xrxs-cli appraisal getPlanFlowList --request-body '{"planId":"<planId>"}'
```

- 从返回的环节列表中取各环节的 `flowId` 与环节名（如指标制定/员工自评/考核评定等）。
- **仅当需要按具体环节查询**（如"只查员工自评环节的被考核人"）时才执行本步骤，取该环节 `flowId` 用于 `stage.mode:"FLOW"`；**按状态查询（步骤 3，默认）直接跳过本步骤**。

**步骤 3 — 查询被考核人名单（新范式，分页拉全）**

```bash
xrxs-cli appraisal queryAssesseeInfos --fields "planId,planName,planType,assessBizId,employeeId,employeeName,jobNumber,department,flowName,inspectionStatus,assesseeStatus" --request-body '{"searchMode":"PLAN_SUBJECTS","planId":"<planId>","stage":{"mode":"ALL"},"pageNum":1,"pageSize":100}'
```

- **新范式核心：`searchMode:"PLAN_SUBJECTS"` + `planId`，用 `stage.mode` 表达状态**（完整规则见 [`query-assessee-infos-guide.md`](../query-assessee-infos-guide.md)）：
  - `"stage":{"mode":"ALL"}` → 查询**全部**被考核对象（默认推荐，一次拿全方案名单）
  - `"stage":{"mode":"COMPLETED"}` → 查询**已完成**对象
  - `"stage":{"mode":"TERMINATED"}` → 查询**已终止**对象
- **组织绩效方案同样走本模式**（`searchMode:"PLAN_SUBJECTS"` + `planId`），服务端会根据 `planId` 自动识别方案类型；`--fields` 改用组织字段（`assessBizId,departmentId,department,departmentPathNameList,departmentAdminName`）。
- **必须带 `--fields` 压缩**：`queryAssesseeInfos` 全字段返回极大（实测 37 人 ≈ 110KB），不带 `--fields` 会触发工具层 50KB 截断，模型会把截断误判为「接口服务内部错误」。
- 递增 `pageNum` 拉全（遵守「分页停止条件」：某页条数 < pageSize 或为空即停）；**同一请求体只完整拉一次**。
- 汇总结果得到方案全部被考核人；`--fields` 模式下返回为**平铺列表**，可直接本地提取字段，例如：

```bash
--jq 'map({employeeId,employeeName,department,flowName,inspectionStatus})'
```

> 说明：默认按状态查询不需要步骤 2；仅当用户要求"按环节维度（如只查员工自评环节）"时，才用 `stage.mode:"FLOW"` + 步骤 2 拿到的真实 `flowId`。

**步骤 4 — 输出名单**

- 直接向用户输出：**总人数** + 按人列出（姓名、部门、所在环节、考核组），可附各环节人数分布。
- 只读查询，无需用户确认；不返回命令本身。

## 异常分支

| 异常情况 | 处理方式 |
|----------|----------|
| 方案搜不到 | 已按 2 次搜索上限仍无结果 → 如实反馈，列出近似候选方案让用户确认（如去掉名称中编号后缀再搜一次由用户判断），不反复重试 |
| 多个同名/近似方案 | 列出候选（名称+状态+周期）让用户选择目标方案，不自行猜测 |
| 某环节被考核人为空 | 正常跳过该环节，继续其他环节；最终名单为空时如实告知 |
| 执行报错（如 325001002 参数校验失败） | 如实反馈报错信息；先自查请求体是否完整：`searchMode` + `planId` + `stage.mode` 是否齐全（见步骤 3），修正后重试 1 次；按环节查询则确认 `stage.mode:"FLOW"` 的 `flowId` 是否来自 `getPlanFlowList`，修正后重试 1 次，仍失败如实反馈 |

## 输出模板

```markdown
## 方案被考核对象 — <方案名称>（<方案ID>）

共 **N 人**（<环节名> X 人 / <环节名> Y 人）

- 张三（XX部，<环节名>，<考核组>）
- 李四（XX部，<环节名>，<考核组>）
- …
```
