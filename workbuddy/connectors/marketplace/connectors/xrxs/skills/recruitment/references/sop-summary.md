# 招聘 SOP 摘要索引（sop-summary）

> **阅读规则（强制）：** 处理任何招聘业务需求（**含查询类**，如「帮我推荐候选人」「根据职位推荐简历」等）时，**第一步必须先读本文件**，用用户话术匹配下方场景索引。**不要因为问题"看起来简单"就直接去读 shortcut 文档自行摸索**——本文件的场景索引已覆盖招聘中的常见场景化需求。
> - **命中**某个场景 → 必须再读 [`sops/`](sops/) 下对应场景文件（`sop-sceneN.md`），**严格按其步骤执行**；通用约定见 [`sops/common.md`](sops/common.md)。
> - **未命中**任何场景 → 回退到 `SKILL.md` 通用规则，**不深挖 SOP 场景文件**，不自行套用相似场景。
> - 同时命中多个场景（如一句话含两个动作）→ 按场景索引顺序逐项执行，每个动作独立确认。
> - ⚠️ 命中场景后**禁止执行 `schema` 查参数**（场景文档已给完整请求体/命令），禁止反复试探接口（如不同 `status` 值分别查询）；场景文档指定了确切参数，直接按文档执行。

---

## 场景索引

| # | 场景 | 触发话术 / 关键词 | 流程要点 | 读写 | 确认方式 | 详情 |
|---|------|-------------------|----------|------|----------|------|
| 一 | 人岗推荐 | 「帮我推荐几个合适的候选人」「根据这个职位推荐几份简历」「给我推荐匹配度高的候选人」等；推荐、人岗匹配、合适候选人、匹配度 | `getMyJobList`/`getJobDetail` 确认职位 → `getResumeFilterFields` 获取筛选字段 → `getResumeList`（`source=0`、`pageSize=100`、最多 3 页）按职位筛选 → 基于列表字段粗略匹配 → `getResumeDetail` 精准匹配 → 输出推荐清单 | 只读 | 无 | [场景一](sops/sop-scene1.md) |
| 二 | 推荐简历给用人部门 | 「把张三的简历推荐给李经理」「推荐这份简历给用人部门」「把候选人推荐给面试官」等；推荐简历、推荐给人、推荐给用人部门、推荐给面试官、转发简历、把 xx 推荐给 xx | 识别简历/接收人 → `getResumeDetailOperations` 预判能否推荐 → 用户确认 → `permission check recruitment-recommendResume` → 未授权则 `permission save` 或 `recommendResumePreview` → `recommendResume` | 写入 | 用户确认 | [场景二](sops/sop-scene2.md) |
| 三 | 安排面试 | 「给张三安排面试」「帮李四约一面」「修改王五的面试时间」等；安排面试、约面试、安排一面、预约面试、修改面试、调整面试时间、改面试、换面试官 | 识别简历/面试官 → `getResumeDetailOperations` 预判 → 判断 add/update → 查询面试配置/条件信息/面试官日程 → 收集必填项 → 用户确认 → `permission check` → 未授权则 `permission save` 或 preview → `addInterview`/`updateInterview` | 写入 | 用户确认 | [场景三](sops/sop-scene3.md) |
| 四 | 获取面试官日程 | 「查一下张经理的面试日程」「看看李总下周有没有空」「王面试官最近忙吗」等；面试官日程、面试日程、查日程、有没有空、最近忙吗 | `searchEmployee` 定位面试官 → `getInterviewerScheduleCalendar` 查询日程 → 总结分析并输出，无日程时提示「无日程安排」 | 只读 | 无 | [场景四](sops/sop-scene4.md) |

---

## 通用要点（命中场景后同样适用）

- **命中场景后直接按场景文档（`sops/sop-sceneN.md`）执行，无需逐命令执行 `schema`**；仅在未命中场景（回退 `SKILL.md` 通用规则）、场景文档未覆盖的命令、或命令报错需确认参数时，才执行 `xrxs-cli schema recruitment.<command>` 看参数；同一命令最多检查一次，禁止批量轮询无关命令。
- 构造 `getResumeList` / `getTalentResumeList` 的 `filters` 前，必须先调 `getResumeFilterFields` 获取字段定义，按 [`common.md`](sops/common.md) 中的 `filters` 规则填充，**不猜字段名**。
- 分页拉全遵循「分页停止条件」：某页条数 < `pageSize` 或为空即停。
- **场景一最多拉取 3 页**（即最多 300 条简历），达到上限后停止，不再继续拉取。
- 同一请求体最多拉取一次。
- **不要将执行的命令原样返回给用户**，只呈现分析结果。
