# 招聘 SOP — 通用约定（common）

> **阅读规则：** 本文档定义各 SOP 场景共享的**通用约定**。处理「场景型」需求时，**必须先读 [`../sop-summary.md`](../sop-summary.md) 匹配场景**；命中后，读取 [`sops/`](sops/) 下对应的场景文件（`sop-sceneN.md`），**严格按其步骤序列执行**。不得跳过步骤、不得自行发明等价命令序列。
>
> **与 SKILL.md 的关系：** `SKILL.md` 定义通用能力、命令用法与安全规则（如：命令执行前先读文档、写入操作需确认意图等）；本文件及 `sops/` 下场景文件定义「场景 → 步骤」的编排逻辑。对于已覆盖的场景，以场景文件为准；未覆盖的需求，回退到 `SKILL.md` 的通用规则。

---

## 通用约定

### 1. 参数收集

- 执行任何场景前，先确认场景所需的「前置信息」是否齐全（见各场景章节）。缺失的向用户追问，**不猜测、不编造**。
- 用户话语中的枚举值（状态码、阶段类型、字段枚举等），如需确认含义，先调用 `getResumeFilterFields`、`getProcessSettingList` 等字段定义类命令查看，再作映射。

### 2. 命令使用前检查

- **命中 SOP 场景时**：场景文档（`sop-sceneN.md`）已给出每条命令的完整调用与请求体格式，**直接按文档执行，无需再执行 `xrxs-cli schema recruitment.<command>`**；场景文档已注明的参数/格式即为执行依据。
- 仅以下情况才执行 `xrxs-cli schema recruitment.<command>` 查看参数与请求体格式：
  - 未命中任何场景，回退到 `SKILL.md` 通用规则时；
  - 场景文档未覆盖的命令（如异常分支中需要的新命令、文档外的补充查询）；
  - 命令执行报错，需确认参数/请求体格式排错时。
- **同一命令最多检查一次**；禁止为排查字段而批量轮询多个无关命令的 schema（字段定义用一次 `getResumeFilterFields` 即可确认）。
- 请求体为 `application/json` 的接口，使用 `--request-body json` 或 `--request-body` 传 JSON 字符串；参数型接口用 `--<name> <value>` 传参。
- 分页接口必须循环拉全数据，禁止只取第一页就下结论。
- **同一请求体（同参数组合）最多拉取一次**；需要不同视角的数据时，基于已拉取的结果本地变换，禁止重复请求相同数据。
- **分页停止条件**：递增 `pageNum` 逐页拉取，当某页返回条数 < `pageSize` 或返回为空时停止；禁止 `pageNum` 不递增的重复请求，同一分页序列最多完整拉一次。
- **不要将执行的命令原样返回给用户**，只呈现分析结果。

### 3. `filters` 构造规则（重要）

构造 `getResumeList` / `getTalentResumeList` 的 `filters` 时，必须先调用 `xrxs-cli recruitment getResumeFilterFields` 获取字段定义，**以返回的 `field` 为准，不猜字段名**。

`filters` 中每个条目的结构如下：

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | integer | `1` 单选，`2` 多选，`3` 范围，`4` 多个范围 |
| `field` | string | 筛选字段 key，引用 `getResumeFilterFields` 结果中的 `data.field` |
| `value` | any | `type=1` 时使用，单选值 |
| `values` | array | `type=2` 时使用，多选值数组 |
| `minValue` / `maxValue` | any | `type=3` 时使用，范围起始/结束值（日期为秒级时间戳） |
| `ranges` | object[] | `type=4` 时使用，多个范围（或关系），每项含 `minValue`/`maxValue` |

示例：

```json
[
  {"type": 1, "field": "videoResumeMark", "value": 1},
  {"type": 2, "field": "sex", "values": [1]},
  {"type": 3, "field": "applyTime", "minValue": 1704038400, "maxValue": 1719705600},
  {"type": 4, "field": "age", "ranges": [{"minValue": 25, "maxValue": 30}]}
]
```

**按职位筛选（多职位，或关系）**：`field="applyJobIds"`，`type=2`，`values` 传多个职位 ID。

```json
[{"type": 2, "field": "applyJobIds", "values": ["职位ID1", "职位ID2", "职位ID3"]}]
```

### 4. 数据可信度

- 所有数据以 `xrxs-cli` 实际返回为准。返回字段缺失时，先判断是否为字段名不同（可调用字段定义类命令确认），确认缺失后再走对应场景的「异常分支」，**禁止用编造数据填充**。
- ID 类字段（`jobId`、`resumeId`、`customProcessId`、`customStageId` 等）必须引用已有接口返回的真实数据，禁止凭空构造。

### 5. 查询效率与冗余调用提示

- 回答用户问题时，应优先判断已返回的数据是否足够。若一次查询已能提供用户所需的关键信息，则无需为了补充非必要字段而对每条记录发起级联详情调用。
- 场景一（人岗推荐）中，先通过 `getResumeList` 列表字段做粗略匹配，再对筛选后的候选集调用 `getResumeDetail`，避免对海量简历逐一查询详情。
- 面试相关问题优先使用面试接口，不要习惯性地调用 `getResumeList`、`getTalentResumeList`、`getResumeDetail` 等简历接口补充信息，除非确实需要。
