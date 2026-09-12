# 场景八：查询考核方案列表（按状态筛选）

> **阅读提示：** 本文档为场景八的详细步骤，通用约定见 [`common.md`](common.md)。命中本场景后严格按下列步骤执行，不得跳过、不得自行发明等价命令序列。

## 适用场景与触发话术

- 用户话术示例（含同义表达）：
  - 「现在有哪些进行中的方案」
  - 「帮我列一下有哪些考核方案（进行中/未开始/已终止/已归档）」
  - 「这季度有哪些绩效考核方案？」
  - 「有哪些已归档的方案可以查」
- 关键词：有哪些方案、方案列表、进行中、未开始、已归档、已终止、方案状态、列一下方案。

> **场景定位：** 这是**只读查询**，输出的是**方案本身**（方案名 + 状态 + 周期/时间等），**不做被考核人明细**（那是[场景六](sop-scene6.md)）。用户问「XX方案有哪些被考核人/名单」走场景六，不要在本场景里展开每个方案的名单。

## 前置信息

| 信息 | 必填 | 说明 |
|------|------|------|
| 方案状态 `planStatus` | 否 | 用户指定时按枚举映射；**未指定时默认 1-进行中**。枚举：0-未开始，1-进行中，3-终止考核，4-已归档 |
| 方案类型 `planType` | 否 | 用户未指定时默认 1-绩效考核（`batchQueryPlanInfos` 要求 planStatus+planType 必填，缺任一报参数校验异常） |

- 用户只问「有哪些方案」没给状态 → 默认按 `planStatus:1`（进行中）查，输出后顺带提示可查其他状态。
- 用户给了明确状态（如「未开始的」「已归档的」）→ 直接映射对应枚举值。
- 用户说「全部方案/所有方案」→ 按 0/1/3/4 各查一次并合并汇总（每次请求体不同，这是需求本身，不是轮询探测；与「定位单个方案禁止多状态轮询」的场景六/七策略不同）。

## 执行步骤

**步骤 1 — 查询方案列表（直接复制命令，禁止先探测）**

按用户需求的状态 `planStatus` 与类型 `planType`，**对每个涉及的类型各执行一次**（默认场景 = 三个类型都查）：

```bash
xrxs-cli appraisal batchQueryPlanInfos --request-body '{"planType":1,"planStatus":1,"pageNum":1}' --fields "planId,planName,planStatusDesc,planTypeDesc,planYear,planPeriodDesc,assessStartTime,assessEndTime"
xrxs-cli appraisal batchQueryPlanInfos --request-body '{"planType":2,"planStatus":1,"pageNum":1}' --fields "planId,planName,planStatusDesc,planTypeDesc,planYear,planPeriodDesc,assessStartTime,assessEndTime"
xrxs-cli appraisal batchQueryPlanInfos --request-body '{"planType":3,"planStatus":1,"pageNum":1}' --fields "planId,planName,planStatusDesc,planTypeDesc,planYear,planPeriodDesc,assessStartTime,assessEndTime"
```

（三个类型相互独立，可并行。）

**关键行为约束（违反即视为回退）：**

- **命令原样复制执行**：上面的命令（含 `--fields` 参数）已实测有效，直接使用；**禁止**先跑不带 `--fields` 的版本"看结构"，**禁止**自行改用 `--jq` 探测（如 `--jq '.data | length'`），**禁止**先裸查再逐步试参数——一次调用到位。
- **分页拉全**：`--fields` 版返回的 `recordsTotal` 是该类型方案总数。若该类型返回条数 < `recordsTotal`（说明超 100 条、有下一页），递增 `pageNum` 补拉下一页，直到拉全；**同一页只拉一次**。多个类型的补页可并行。
- **禁止 `getPlanBasicInfo`**：本场景只需要方案列表字段，不要对单个方案查基础信息（那是别的场景的事）。
- **禁止 `planName` 关键词连环补查**：数据拉全是靠分页（pageNum），不是靠关键词分段搜索。
- **禁止用 `run_python_code` 处理 CLI 返回数据**：`batchQueryPlanInfos` 返回自带 `recordsTotal` 字段，直接读取该字段统计各类型方案总数即可，**严禁**把 CLI 返回的 JSON 复制进 python 脚本去 count/解析/清洗（这既慢又多余）。汇总分页时：各类型总数 = 该类型 `recordsTotal`；需列出方案明细时直接引用 CLI 返回的方案字段，不要再过一遍 python。
- 用户给了方案名关键词时可加 `"planName":"<关键词>"` 过滤；没有则不带。
- 不要对每个方案再调 `getPlanFlowList` / `queryAssesseeInfos` / `getPlanFlowPeopleCount`（除非用户明确要求每个方案的人数/环节明细）。

**步骤 2 — 输出方案列表**

- 汇总**所有页**的结果（总数以各类型 `recordsTotal` 之和为准，不要漏页），按类型分组列出：**方案名称、状态、周期（planPeriodDesc）、考核时间（assessStartTime - assessEndTime）**；返回里有多少字段就展示多少，字段缺失不编造。
- 方案数量多时给总数；数量少时逐个列出。
- 只读查询，无需用户确认；不返回命令本身。

## 异常分支

| 异常情况 | 处理方式 |
|----------|----------|
| 返回为空 | 如实告知「当前没有 <状态> 的方案」，可提示用户是否需要查其他状态 |
| 参数校验异常 | 自查 `planStatus`/`planType` 是否缺失或枚举值不对（缺失必报参数校验异常），修正后重试 1 次，仍失败如实反馈 |
| 用户意图其实是查名单 | 用户问「XX方案考核了哪些人」时转入[场景六](sop-scene6.md)，不按本场景只列方案 |

## 输出模板

```markdown
## 考核方案列表（<状态中文名>）

共 **N** 个方案（<类型1> X 个 / <类型2> Y 个）：

### <类型中文名>
- <方案名称>｜状态：<状态>｜周期：<planPeriodDesc>｜考核时间：<assessStartTime> - <assessEndTime>
- …
```
