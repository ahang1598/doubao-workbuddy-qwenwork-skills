# attendance 报表接口

> **前置条件**:先阅读 [`../SKILL.md`](../SKILL.md) 了解全局能力与意图决策树。

报表接口。月度报表的创建、归档、重新计算,报表字段字典,报表可归档考勤组列表,以及报表导航、表头检索与导出。

## ⚠️ 业务约束

- **归档/新建考勤月报表需客户主动要求**(`createActiveArchive`, `archiveReportsByAttendanceGroups`, `archiveReports`):归档或新建考勤月报表(createActiveArchive 新建、archiveReportsByAttendanceGroups/archiveReports 归档)属高风险操作,除客户主动要求外不得擅自执行;执行前必须向用户确认意图及目标账套月份/考勤组范围。
- **归档方式二选一(按考勤组是否开启)**(`archiveReports`, `archiveReportsByAttendanceGroups`, `getReportAttendanceGroupList`):报表归档方式二选一,由公司是否开启考勤组决定,不可混用:已开启考勤组的公司用 `archiveReportsByAttendanceGroups`(需 yearmo + attendanceGroupIds,先 `archiveReportsByAttendanceGroupsPreview` 预览);未开启考勤组的公司用 `archiveReports`(无需入参,账套月由接口内部取活动账套)。通过 `getReportAttendanceGroupList` 判定:返回考勤组(非空)= 已开启(用考勤组归档);返回空 = 未开启(用普通归档)。

## 🔄 核心场景

#### 导出历史归档报表

导出历史归档考勤报表的完整组装链路:查归档列表取 yearmo/archiveId -> 查报表基础详情取 subReportId/activeFlag -> 查表头列定义生成 headers 掩码 -> 触发异步导出。

**方式1:导出历史归档报表**

**步骤 1**: `getArchiveReportList` - 入参 year(如 2026)查归档报表列表,取目标月份的 **yearmo**、activeStatus、archiveId(yearmo 已知可省略本步)
**步骤 2**: `getReportBaseDetail` - 入参 yearmo、source、archiveId,取 ReportBaseModel:**activeFlag**(直接取)、**yearmo**(直接取)、**subReportId**(遍历 reportNavList 匹配目标 type 取 ReportNavModel.subReportId)
**步骤 3**: `getHistoryReportHeader` - 入参 **subReportId** 查表头,返回值即 **headers** 结构,直接用于步骤④ `exportReports` 的 headers 入参(无需手动生成掩码)
**步骤 4**: `exportReports` - 触发导出:入参 type、**activeFlag**、**yearmo**、**subReportId**、**headers**、isExportFullData="1"
**步骤 5**: `getExportRecord` - 入参 **taskId**(来自步骤④ `exportReports` 返回)查询导出记录状态及下载地址;导出异步进行,需轮询直至完成再取下载地址

> 💡 接口② source 与导出 activeFlag 同义(ActiveFlagEnum);历史归档(yearmo<当前活动账套月)且 attGroupSwitch 开启时,archiveId 为空方法内部自动查 latest archiveId,不必前置获取。CLI 入参无 reportId/archiveId 字段(与 Web 端 ReportExportVO 不同),归档身份由 subReportId+activeFlag 承载,接口②拿到的 archiveId 组装导出入参时用不上。getHistoryReportHeader 返回值已与 exportReports 的 headers 入参结构对齐,直接透传即可(无需手动生成 1,1,... 掩码)。频率限制:同账号 5 分钟内最多 3 次,调试时节流。导出是异步的:`exportReports` 返回 taskId(导出记录ID),实际导出在线程池执行;用 `getExportRecord` 传 taskId 轮询导出状态,完成后取下载地址。

#### 新建账套(报表)

通过 getActiveArchive 获取当前活动账套后,直接调用 createActiveArchive 新建报表;yearmo 传当前活动账套的 yearmo(非新建后 yearmo)。

**方式1:新建账套**

**步骤 1**: `getActiveArchive` - 获取当前活动账套(无需入参),取 **yearmo**(data.activeArchive.yearmo)
**步骤 2**: `createActiveArchive` - 新建报表/账套;入参 **yearmo** 传步骤1 当前活动账套的 yearmo(**不是新建后的 yearmo**),可选 **isImmediatelyCreate**(是否立即创建);若存在考勤/报表重算任务、归档锁或新建报表任务则禁止创建

> 💡 新建账套的关键:`createActiveArchive` 的 yearmo 必须传当前活动账套的 yearmo(getActiveArchive 返回),而非新建后的账套月(反直觉)。新建报表属高风险操作,除客户主动要求外不得擅自执行,执行前须确认意图与目标账套月份(见业务约束『归档/新建考勤月报表需客户主动要求』);创建后异步触发清理历史考勤数据任务。

## 命令

### getReportAttendanceGroupList

获取报表可归档考勤组列表 查询当前公司可用于报表归档的考勤组列表；若开启考勤组且为自管管理员，则仅返回权限范围内的考勤组。

```bash
xrxs-cli attendance getReportAttendanceGroupList [flags]
```

- **参数已说明,免 schema 查**(该接口无需入参,出参说明如下):
- 出参:`data 为 array,每项含` `num`(integer); `accountName`(string); `archiveStatus`(integer):0 未归档； 1已归档；2进行中; `lastArchiveTime`(string); `attendanceGroupId`(string); `attendanceGroupName`(string)。


### getArchiveReportList

月度报表：根据年份检索归档报表

```bash
xrxs-cli attendance getArchiveReportList [--year] ...
```

- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


### getReportBaseDetail

月度报表：基础报表导航 检索：活动报表 & 归档报表的基础报表的导航列表数据

```bash
xrxs-cli attendance getReportBaseDetail [--yearmo --source --archive-id] ...
```

- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


### getHistoryReportHeader

月度报表：历史归档报表Header 根据 月度报表：基础报表导航 返回的 子表ID 检索历史归档报表表头列数，生成完整导出的 headers 结构（按列数生成 "1,1,1,...,1"，全 1 表示完整导出）

```bash
xrxs-cli attendance getHistoryReportHeader [--sub-report-id] ...
```

- **参数已说明,免 schema 查**(入参/出参结构简单,下方为完整说明):
- 入参:
  - `sub-report-id`(subReportId)[string] 可选:子报表ID
- 出参:`data`(string):返回结果集


### exportReports

根据月度报表：基础报表导航返回的子表ID；检索历史归档报表Header；进行报表导出

```bash
xrxs-cli attendance exportReports --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


### refreshReport

报表重新计算接口 备注：触发月报表异步重新计算任务，若已有管理员正在重算则直接返回失败。

```bash
xrxs-cli attendance refreshReport [--yearmo --source] ...
```

- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。

> ⚠️ **写入操作**:会修改数据,执行前须确认用户意图;用户已明确说「请直接执行」「请完成」等授权语时视为已授权,直接执行不再二次确认。


### getAttendanceApproveCount

活动账套范围内待审批的考勤审批数量 备注：查询当前公司在活动账套范围内待审批的考勤审批数量，并返回报表归档校验开关。

```bash
xrxs-cli attendance getAttendanceApproveCount [--attendance-group-ids] ...
```

- **参数已说明,免 schema 查**(入参/出参结构简单,下方为完整说明):
- 入参:
  - `attendance-group-ids`(attendanceGroupIds)[string] 可选:考勤组ID集合，多个逗号分隔，可不传 xrxs-cli attendance getReportAttendanceGroupList 通过这个接口获取可选择的考勤组列表
- 出参:`data 为 object,含` `count`(integer):待审批数量; `switchValue`(integer):报表归档校验开关，1-开启，0-关闭。


### getReportArchiveStatus

获取报表状态 查询是否正在计算/是否正在归档/上次归档状态 备注：查询当前公司的归档状态、是否可归档、不可归档员工列表及相关任务执行状态。

```bash
xrxs-cli attendance getReportArchiveStatus [--attendance-group-ids] ...
```

- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


### getCustomReportFieldDictNew

获取自定义报表可选的和已选的字段选项 备注：查询自定义报表字段字典；不传id时返回所有字段选项，传id时返回编辑页选项，并固定将姓名字段加入 useHeader。

```bash
xrxs-cli attendance getCustomReportFieldDictNew [--id] ...
```

- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


### getActiveReportBaseDetailList

获取活动报表的报表列表 备注：查询当前活动账套月份对应的活动报表基础导航信息；先获取活动账套月份，再将 source 固定为 1（活动账套月），其余逻辑与报表导航一致。

```bash
xrxs-cli attendance getActiveReportBaseDetailList [flags]
```

- schema 未声明入参,可直接调用。


### createActiveArchive

新建报表 备注：创建当前公司的报表；若存在考勤/报表重算任务、归档锁或新建报表任务则禁止创建；创建后会异步触发清理历史考勤数据任务。

```bash
xrxs-cli attendance createActiveArchive [--yearmo --is-immediately-create] ...
```

- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。

> ⚠️ **写入操作**:会修改数据,执行前须确认用户意图;用户已明确说「请直接执行」「请完成」等授权语时视为已授权,直接执行不再二次确认。


### getEmployeeErrorMessageByArchive

检查不能归档的异常员工信息 备注：查询当前管理员权限范围内不能归档的异常员工列表，返回员工ID、员工姓名和异常原因。

```bash
xrxs-cli attendance getEmployeeErrorMessageByArchive [flags]
```

- **参数已说明,免 schema 查**(该接口无需入参,出参说明如下):
- 出参:`data 为 array,每项含` `employeeId`(string); `employeeName`(string); `errorMessage`(string)。


### archiveReportsByAttendanceGroups

归档考勤组报表 备注：按指定账套月份和考勤组集合执行考勤组归档，归档前会校验固化任务、归档锁和考勤组有效性。（调用前需要先调用 xrxs-cli attendance getAttendanceApproveCount和 xrxs-cli attendance getReportArchiveStatus接口获取审批流数量和归档状态，若审批流数量大于0则需要提醒用户处理审批，也可不处理审批继续归档，若归档状态接口返回 status为 false则提醒用户报错信息 并且禁止归档，若公司开启考勤组了，则需要调用 xrxs-cli attendance getReportAttendanceGroupList查询考勤组列表）

```bash
xrxs-cli attendance archiveReportsByAttendanceGroups [--yearmo --attendance-group-ids] ...
```

- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。

> ⚠️ **写入操作**:会修改数据,执行前须确认用户意图;用户已明确说「请直接执行」「请完成」等授权语时视为已授权,直接执行不再二次确认。


### archiveReportsByAttendanceGroupsPreview

是否确认归档报表 查询指定账套月份的考勤组归档预览数据，包含汇总信息（考勤组数、员工总数）和明细列表（每个考勤组的归档状态、人数、操作人、归档时间）。

```bash
xrxs-cli attendance archiveReportsByAttendanceGroupsPreview --yearmo <yearmo> [--attendance-group-ids] ...
```

- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


### getExportRecord

月度报表：查询导出记录信息 根据提交导出时返回的 taskId(导出记录ID) 查询导出记录状态及下载地址

```bash
xrxs-cli attendance getExportRecord [--task-id] ...
```

- **参数已说明,免 schema 查**(入参/出参结构简单,下方为完整说明):
- 入参:
  - `task-id`(taskId)[string] 可选:导出记录ID（/ajax-export-reports.json 返回的 recordId）
- 出参:`data 为 object,含` `status`(integer):状态 0导出中 1导出完成 2导出失败 3过期; `addDate`(string):添加时间; `fileUrl`(string):下载链接（永久）; `fileName`(string):文件名; `taskType`(integer):任务类型; `totalNum`(integer):任务总长度; `accountName`(string):管理员名称; `completeNum`(integer):任务完成数。


### archiveReports

归档非考勤组报表 备注：归档活动账套月的报表（活动账套归档），归档前会校验固化任务和归档锁。账套月份由接口内部通过活动账套查询获取，无需入参。（调用前需要先调用 xrxs-cli attendance getAttendanceApproveCount和 xrxs-cli attendance getReportArchiveStatus接口获取审批流数量和归档状态，若审批流数量大于0则需要提醒用户处理审批，也可不处理审批继续归档，若归档状态接口返回 status为 false则提醒用户报错信息 并且禁止归档）

```bash
xrxs-cli attendance archiveReports [flags]
```

- schema 未声明入参,可直接调用。

> ⚠️ **写入操作**:会修改数据,执行前须确认用户意图;用户已明确说「请直接执行」「请完成」等授权语时视为已授权,直接执行不再二次确认。


## 参考
- [attendance](../SKILL.md) - 全部命令
