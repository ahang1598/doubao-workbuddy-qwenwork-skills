---
name: attendance
version: 2.0.0
description: "attendance 模块 CLI,通过 xrxs-cli attendance 调用。覆盖 6 大场景:公共接口(common)、报表接口(report)、考勤确认(confirm)、加班管理(overtime)、假期管理(holiday)、方案管理(settings)。执行前先 schema 查入参/出参,禁止猜测字段格式。"
metadata:
  requires:
    bins: ["xrxs-cli"]
  cliHelp: "xrxs-cli attendance --help"
---

# attendance (v2)

> 命令可用性以 xrxs-cli 二进制为准;参数格式以 `xrxs-cli schema attendance.<command>` 为准。若命令调用失败,先按错误提示确认参数与权限。

## 严格禁止 (NEVER DO)
- 不要用 xrxs-cli 以外的方式操作(禁止 curl、HTTP API、浏览器)
- 不要编造 ID(yearmo、attendanceGroupId、recordId、subReportId 等),必须从前置命令返回中提取;若某 ID 在前置调用返回中未出现,先补查确认来源再继续,禁止直接使用
- 不要凭印象直接执行命令或猜测参数名/取值:调用前必须先确认命令存在且参数正确--方式①当前 reference 命令段已列参数(含标「参数已说明,免 schema 查」的简单接口)可直接用;方式②`xrxs-cli schema attendance.<command>` 查契约。**严禁仅凭命令名语义自行编造 flag(如 `--keyword`、`--name` 等),必须以 reference 命令段或 schema 的参数为准。每个命令首次调用前都要查证(已查其他命令的 schema 不代表可跳过当前命令的查证);当前 reference 无该命令段时,直接查 `schema attendance.<command>`,不要单独额外读所属类目 reference**
- 不要猜测字段名/参数值,操作前必须先 `xrxs-cli schema attendance.<command>` 查询确认(复杂接口)
- **product 名统一为 `attendance`**:所有命令的 schema 查询都是 `xrxs-cli schema attendance.<command>`;reference 文件名(common/report/confirm 等)只是 5 类分类,不是 product 名,不要用 `schema common.<command>` 等错误 product
- 禁止联网查询法定节假日/调休(禁止 search_web、浏览器、外部检索、知识库检索节假日)。
- 通过姓名查找具体员工时,只调用 `searchEmployee`(按姓名/手机号搜索取 employeeId),不要调用 `getEmployeeDetail`;`getEmployeeDetail` 仅在已取得 employeeId 后用于查员工完整档案,不用于按姓名检索
- **所有考勤业务一律不走审批流**:任何业务操作(换班、调班、补卡、加班等)都不通过发起/驱动审批流来完成(不调用 `launchFlow` 等审批命令代替业务命令),一律以对应业务命令直接落地。审批流(如换班 flow46)与直接操作是两条互斥路径,本 skill 默认且仅走直接操作路径。
- 命令段标有「**参数已说明,免 schema 查**」的简单接口(入参 ≤5 个 query/path 参数、无嵌套 body,且出参 data 字段 ≤8 无深嵌套),reference 已列**完整入参+出参说明**,**无需再调 `xrxs-cli schema` 查入参/出参**;仅当命令段未列参数、或入参/出参为复杂嵌套结构时才查 schema。

## 严格要求 (MUST DO)
- 写入/删除操作前必须向用户确认意图;用户已明确说「请直接执行」「请完成」等授权语时视为已授权,直接执行不再二次确认,否则才需确认。**配有 `<PreviewCommand>` 的写入接口,preview + 用户确认即等同此处的确认(不二次确认,见「预览命令与权限校验」);无 preview 接口的写入命令才单独确认**
- 批量操作单次不超过合理上限,逐条收集返回 ID,不遗漏
- 严格遵循参数格式:query/path 参数用 kebab-case 字段级 flag(如 `--sub-report-id`、`--yearmo`);POST 请求体用 `--request-body '<JSON>'` 传整块 JSON
- 执行前先 `xrxs-cli schema attendance.<command>` 查入参/出参格式与字段说明

## 预览命令与权限校验 (Preview & Permission Check)

部分写入接口配有预览接口 `<PreviewCommand>`(命令名通常为 `xxxPreview`,与正式接口入参相同,返回操作摘要但不实际落库)。**本小节仅适用于配有 `<PreviewCommand>` 的写入接口:无论调用正式接口 `<command>` 还是预览接口 `<PreviewCommand>`,每次调用前都要先执行一次权限校验**(针对正式命令 `<command>`);**若 command 无对应的 preview 接口,则不调用 permission check**。**`permission check` 与 `<PreviewCommand>` 严禁并行调用**:`<PreviewCommand>` 的调用依赖于 `permission check` 的返回结果(false 才需要 preview),必须等 `permission check` 返回后再决定下一步,不得同时发起:

```bash
xrxs-cli permission check attendance-<command>
```

- 返回 `true`:用户已授权永久允许执行该命令,可直接调用 `<command>`。
- 返回 `false`:用户未授权,必须先调用 `<PreviewCommand>` 展示操作摘要,等用户确认后再调用 `<command>`;若用户希望永久授权本命令,可执行 `xrxs-cli permission save attendance-<command>` 保存授权,保存后下次 `xrxs-cli permission check attendance-<command>` 将返回 `true`,可直接执行而无需再次 preview。
- **每次调用 `<PreviewCommand>` 前,同样先执行一次上述 `permission check` 并等待其返回**,再调用预览(严禁与 `permission check` 并行)。
- **预览确认即写入确认(避免重复)**:对配有 `<PreviewCommand>` 的写入接口,`<PreviewCommand>` 展示摘要 + 用户确认后,即视为已满足「写入操作需确认」要求,直接调用正式 `<command>` 一次即可,**不要重复 preview、不要对正式命令二次确认**;仅当用户在 preview 后修改了入参,才重新 preview 一次再执行。无 preview 接口的写入命令,才按「严格要求」的写入确认口径单独确认。

## 命令结构

xrxs-cli 为三层命令:**程序 / 模块 / 命令**。

```bash
xrxs-cli schema attendance.<command>         # 调用前查参数结构,禁止猜测字段格式
xrxs-cli attendance <command> [flags]        # 调用接口
```

- 接口名即 `<command>`,如 `getReportAttendanceGroupList`、`searchEmployee`、`archiveReportsByAttendanceGroups`。
- 传参方式(先运行 `schema` 查看,由 `method` 与参数位置决定):
  - **query/path 参数**:见 `parameters`(类型/描述/必填)与 `flag_overlay`(flag 别名);用字段级 flag(kebab-case)。
  - **POST 请求体**:见 `request.requestBody.schema`;用 `--request-body '<JSON>'` 传整块 JSON。无 `parameters` 的纯 body 接口只能用此方式。

## 账套月 (Payroll Month)

`yearmo`(如 `202607`)标识**账套月(计薪月份)**,不一定是自然月;其对应的实际日期区间由公司计薪配置决定,存在以下对齐方式:

| 对齐方式 | 说明 | 示例 |
|---|---|---|
| 当月1日~当月31日(当月) | 计薪月份与自然月一一对应 | `202607` = 2026-07-01 ~ 2026-07-31 |
| 当月1日~当月31日(次月) | 计薪月份与自然月错月对应 | `202607` = 2026-06-01 ~ 2026-06-30 |
| 当月25日~次月24日(当月) | 从自然月当月开始至次月结束 | `202607` = 2026-07-25 ~ 2026-08-24 |
| 当月25日~次月24日(次月) | 从自然月上月开始至当月结束 | `202607` = 2026-06-25 ~ 2026-07-24 |

后两种情况不一定从 25 日开始,可以是任意一天开始。**使用规则**:

- `yearmo` 一律以 `getActiveArchive` 返回的 `data.activeArchive.yearmo` 为准,不要按自然月自行推导。
- 涉及账套月边界日期(排班、考勤确认、报表等按月范围)时,以 `getActiveArchive` 返回的 `startDate`/`endDate` 为准,不假设 1 日~月末。
- 对 `yearmo` 强依赖的接口(排班保存、考勤确认发放、报表、异常提醒等),传 `yearmo` 即账套月,非自然月。
- `getActiveArchive` **默认免传参**调用(不带 `date`)获取当前活动账套,绝大多数场景(排班/确认/报表/提醒取 yearmo)均如此;`date`(yyyy-MM-dd)仅**特殊场景**才传,如给未来/指定日期排班时用它计算该日期所属账套的 `yearmo`;返回均取 `data.activeArchive.yearmo`。

## 意图判断决策树

按用户提到的关键词路由到对应类目(命令详情见各 `references/attendance-<cat>.md`):

- 用户提到「报表/月度报表/归档/自定义报表/导出报表/报表重算」 -> `report`(报表接口)
- 用户提到「考勤确认/发放/催办/撤回确认/确认方案」 -> `confirm`(考勤确认)
- 用户提到「加班/加班记录/有效时长/调休时长/加班有效期」 -> `overtime`(加班管理)
- 用户提到「假期/年假/余额/过期日/司龄年假/工龄年假」 -> `holiday`(假期管理)
- 用户提到「排班方案/自动排班/出勤方案」 -> `settings`(方案管理)
- 用户提到「部门树/合同主体/城市/词典/员工搜索/岗位/职级/成本中心」 -> `common`(公共接口)

关键区分:报表 `report`(月度报表归档/重算/导出)。

## 核心场景

| # | 场景 | 文档 | 说明 |
|---|------|----------|------|
| 1 | 公共接口 | [``attendance-common.md``](references/`attendance-common.md`) | 通用查询:权限部门树、合同主体、城市信息、词典选项 |
| 2 | 报表接口 | [``attendance-report.md``](references/`attendance-report.md`) | 报表创建/归档/重算、自定义报表、可归档考勤组列表、导出 |
| 3 | 考勤确认 | [``attendance-confirm.md``](references/`attendance-confirm.md`) | 发放、明细、撤回、提醒及前置数据 |
| 4 | 加班管理 | [``attendance-overtime.md``](references/`attendance-overtime.md`) | 加班记录查询、计算过程、删除与调整 |
| 5 | 假期管理 | [``attendance-holiday.md``](references/`attendance-holiday.md`) | 余额方案、年假统计、余额/过期日调整 |
| 6 | 方案管理 | [``attendance-settings.md``](references/`attendance-settings.md`) | 排班方案查询、自动排班开关 |

各场景接口的参数与用法、核心场景流程详见对应 `references/` 文档(场景流程在各 reference 的 `## 🔄 核心场景` 小节)。

## 命令发现(schema 渐进查询)

`xrxs-cli schema` 查询命令契约(参数/必填/约束),不查业务数据。已知命令路径可直接查 leaf:

```bash
xrxs-cli schema attendance                       # 模块概览(全部 command)
xrxs-cli schema attendance.<command>             # leaf:参数类型/必填/描述/枚举
```

- 命令是否存在、接受哪些 flag 以 `xrxs-cli attendance <command> --help` 为准;参数映射/必填/约束以 `schema` 为准。
- 注意:`schema` 只查命令契约,不查考勤业务数据;完成命令发现后必须执行真实命令(如 `xrxs-cli attendance getReportAttendanceGroupList`)获取业务数据。
- **跨类目命令查证**:场景流程常跨类目引用命令(如 status 场景用 common 的 `searchEmployee` 取 employeeId、scheduling 场景用 shift 的 `getShiftList`、common 的 `getActiveArchive`)。**调用任一命令前,若当前所在 reference 无该命令段,直接查 `xrxs-cli schema attendance.<command>` 确认参数,不要单独额外读取该命令所属类目的 reference,也不要凭命令名语义猜 flag**。

## 错误处理

- 接口调用遇网络异常、超时、服务端 5xx 等**瞬时错误**,最多重试 2 次(共 3 次尝试),重试间稍作等待。
- 参数非法、权限不足、数据不存在、约束冲突等**业务校验报错不重试**(重试结果不变)。
- 重试达上限仍失败、或遇业务校验报错时,**停止本次操作**且不再继续后续步骤;向用户报告操作失败,并附最后一次的错误信息(执行的命令、状态码、报错内容)。
- 上述重试上限对 `schema` 查询同样适用。
- 接口返回内容可能较大(如整月报表明细),工具返回可能被截断(约 20000 字符,表现为 JSON 不完整);**不要基于不完整数据下结论**,改用更聚焦的查询(分页/关键字/更小日期范围)或查看完整返回后再继续。
- 关键信息缺失(如查询结果被截断、缺少考勤组 ID/账套月/子表 ID 等)时,**停止**并向用户报告缺失项,不要猜测、不要继续后续步骤。

## API Resources

按场景聚合的全部接口(command 即 `<command>` 名,调用前用 `schema` 查参数):

### common (公共接口)

- `getAuthDepartment` - 根据权限获取权限内部门树 调用方传入部门树查询参数，返回当前用户权限范围内的部门树结构
- `getContractList` - 获取合同主体列表 查询当前公司的合同主体列表，无需入参
- `getActiveArchive` - 排班业务：获取活动账套月份信息 注意：管理员进行排班时，需要获取一下当前的账套月，该月份来自本接口
- `getDicOption` - 获取词典选项信息（CLI 版）
- `getAreaV2tree` - 获取城市信息树（CLI 版）
- `searchCitys` - 根据关键字搜索城市
- `searchDepartment` - 搜索部门
- `searchJob` - 搜索岗位
- `searchRank` - 搜索职级
- `searchCostCenter` - 搜索成本中心
- `getAllCountry` - 获取所有国家
- `getEmployeeFilterFields` - 获取员工数据搜索过滤条件字段返回的 FilterFieldModel 仅为筛选项「配置」(values/dateValues 为空)， 调用方按下方规则填值后，作为搜索接口(如 searchEmployee)的 filters 入参回传
- `searchEmployee` - 搜索员工
- `getEmployeeDetail` - 获取员工详情
- `getFlowTypes` - CLI 获取公司审批类型列表(含 settingId/isOld)
- `getFlowList` - CLI 获取审批列表(ES 查询)
- `getFlowDetail` - CLI 获取审批详情
- `getFlowPath` - CLI 获取审批流进度
- `getFlowFormSetting` - CLI 获取审批表单设置, 返回三段: basicInfoGroup + fixedGroups + customGroups
- `launchFlow` - CLI 发起审批
- `launchFlowPreview` - CLI 发起审批预览(不落库)

### report (报表接口)

- `getReportAttendanceGroupList` - 获取报表可归档考勤组列表 查询当前公司可用于报表归档的考勤组列表
- `getArchiveReportList` - 月度报表：根据年份检索归档报表
- `getReportBaseDetail` - 月度报表：基础报表导航 检索：活动报表 & 归档报表的基础报表的导航列表数据
- `getHistoryReportHeader` - 月度报表：历史归档报表Header 根据 月度报表：基础报表导航 返回的 子表ID 检索历史归档报表表头列数，生成完整导出的 headers 结构（按列数生成 "1,1,1,...,1"，全 1 表示完整导出）
- `exportReports` - 根据月度报表：基础报表导航返回的子表ID
- `refreshReport` - 报表重新计算接口 备注：触发月报表异步重新计算任务，若已有管理员正在重算则直接返回失败
- `getAttendanceApproveCount` - 活动账套范围内待审批的考勤审批数量 备注：查询当前公司在活动账套范围内待审批的考勤审批数量，并返回报表归档校验开关
- `getReportArchiveStatus` - 获取报表状态 查询是否正在计算/是否正在归档/上次归档状态 备注：查询当前公司的归档状态、是否可归档、不可归档员工列表及相关任务执行状态
- `getCustomReportFieldDictNew` - 获取自定义报表可选的和已选的字段选项 备注：查询自定义报表字段字典
- `getActiveReportBaseDetailList` - 获取活动报表的报表列表 备注：查询当前活动账套月份对应的活动报表基础导航信息
- `createActiveArchive` - 新建报表 备注：创建当前公司的报表
- `getEmployeeErrorMessageByArchive` - 检查不能归档的异常员工信息 备注：查询当前管理员权限范围内不能归档的异常员工列表，返回员工ID、员工姓名和异常原因
- `archiveReportsByAttendanceGroups` - 归档考勤组报表 备注：按指定账套月份和考勤组集合执行考勤组归档，归档前会校验固化任务、归档锁和考勤组有效性
- `archiveReportsByAttendanceGroupsPreview` - 是否确认归档报表 查询指定账套月份的考勤组归档预览数据，包含汇总信息（考勤组数、员工总数）和明细列表（每个考勤组的归档状态、人数、操作人、归档时间）
- `getExportRecord` - 月度报表：查询导出记录信息 根据提交导出时返回的 taskId(导出记录ID) 查询导出记录状态及下载地址
- `archiveReports` - 归档非考勤组报表 备注：归档活动账套月的报表（活动账套归档），归档前会校验固化任务和归档锁

### confirm (考勤确认)

- `sendConfirmNotify` - 按账套月份和考勤确认方案创建发放记录，并向方案覆盖的员工发送确认通知
- `sendConfirmNotifyPreview` - 是否确认发放考勤确认使用与正式发放接口相同的请求参数，返回发放月份、方案数量以及所选方案明细
- `getConfirmRecordList` - 查询指定账套月份下的全部考勤确认发放批次，用于获取 recordId、发放状态和发放信息
- `getConfirmRecordDetailList` - 按发放记录 ID 分页查询员工级发放明细，支持员工关键字和已读、确认、发放失败等状态筛选
- `withdrawAllConfirmRecords` - 撤回指定发放记录下的全部员工考勤确认
- `withdrawOneConfirmRecord` - 仅撤回指定员工发放明细，不影响同一发放批次中的其他员工
- `getConfirmRecordDetail` - 根据员工发放明细 ID 查询该员工收到的考勤确认内容、字段和值
- `sendConfirmRemind` - 对指定发放记录中的未确认员工手动发送提醒，并按 distributeTypeList 选择通知渠道
- `sendConfirmRemindPreview` - 是否确认提醒员工进行考勤确认使用与正式提醒接口相同的参数，汇总展示月份、方案数和待确认人数， 明细展示报表月份、考勤方案、确认单名称、待确认人数及提醒渠道
- `getConfirmAvailableMonthList` - 返回当前公司已有考勤归档的账套月份
- `getConfirmSendPlanList` - 返回当前公司可用的考勤确认方案、方案字段中文名称、公告配置和方案版本
- `getConfirmRemindChannelList` - 根据发放记录关联的确认方案，返回该记录已启用的员工端、钉钉、企业微信等通知渠道

### overtime (加班管理)

- `getOvertimeRecordFilterOptions` - 返回加班记录报表支持的打卡校验、补偿方式、加班类型、计算规则、在职类型、 数据来源和时长异常等枚举选项，用于构造 ajax-get-overtime-record-list.json 的 filterKey
- `getOvertimeRecordList` - 按日期范围、员工关键字、异常状态、动态筛选条件和排序规则分页查询加班记录
- `getOvertimeCalculationProcess` - 根据加班记录 ID 查询系统计算有效加班时长的完整过程，并翻译工作日类型等展示字段

### holiday (假期管理)

- `getBalanceEnabledHolidayTypeList` - 返回当前公司配置为“开启余额”的假期类型及名称
- `getHolidayBalanceReport` - 按相对活动年、假期类型、员工关键字和组织条件分页查询员工假期余额， 返回动态表头、员工余额数据、分页信息和上次导出字段

### settings (方案管理)

- `getSchedulingAttendancePlanList` - 方案管理：获取排班方案列表
- `getEmployeeAttendancePlanData` - 注意：返回员工与方案之间的对应关系，结果集返回示例：HashMap → Key:员工ID, Value:方案ID

## 详细参考

- [references/](references/) - 6 类命令详细参考(命令 / bash 样例 / 参数说明 / 参数要点 / ⚠️ 写入标注 / 业务约束 / 核心场景)
  - [公共接口](references/attendance-common.md) / [报表接口](references/attendance-report.md)
  - [考勤确认](references/attendance-confirm.md) / [加班管理](references/attendance-overtime.md) / [假期管理](references/attendance-holiday.md) / [方案管理](references/attendance-settings.md)

