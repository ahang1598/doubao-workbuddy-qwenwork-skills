# attendance 公共接口

> **前置条件**:先阅读 [`../SKILL.md`](../SKILL.md) 了解全局能力与意图决策树。

通用查询接口,提供权限部门树、合同主体、城市信息、词典选项等跨业务复用的基础数据,常作为其他操作的入参数据源。

## 命令

### getAuthDepartment

根据权限获取权限内部门树 调用方传入部门树查询参数，返回当前用户权限范围内的部门树结构。

```bash
xrxs-cli attendance getAuthDepartment --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


### getContractList

获取合同主体列表 查询当前公司的合同主体列表，无需入参。

```bash
xrxs-cli attendance getContractList [flags]
```

- **参数已说明,免 schema 查**(该接口无需入参,出参说明如下):
- 出参:`data 为 array,每项含` `companyId`(string); `contractSubjectId`(string); `contractSubjectName`(string)。


### getActiveArchive

排班业务：获取活动账套月份信息 注意：管理员进行排班时，需要获取一下当前的账套月，该月份来自本接口

```bash
xrxs-cli attendance getActiveArchive [--date] ...
```

- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


### getDicOption

获取词典选项信息（CLI 版）

```bash
xrxs-cli attendance getDicOption [--dic-code] ...
```

- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


### getAreaV2tree

获取城市信息树（CLI 版）。

```bash
xrxs-cli attendance getAreaV2tree [flags]
```

- schema 未声明入参,可直接调用。


### searchCitys

根据关键字搜索城市

```bash
xrxs-cli attendance searchCitys [--name] ...
```

- **参数已说明,免 schema 查**(入参/出参结构简单,下方为完整说明):
- 入参:
  - `name`(name)[string] 可选:城市名称关键字，可为空
- 出参:`data 为 array,每项含` `id`(integer):城市 id; `name`(string):城市名称。


### searchDepartment

搜索部门

```bash
xrxs-cli attendance searchDepartment --keyword <keyword> [--limit] ...
```

- **参数已说明,免 schema 查**(入参/出参结构简单,下方为完整说明):
- 入参:
  - `keyword`(keyword)[string] 必填:搜索关键字（必填）
  - `limit`(limit)[string] 可选:返回结果最大条数，默认 50，最大 100（超过夹紧为 100）
- 出参:`data 为 array,每项含` `id`(string):部门id; `code`(string):部门code; `name`(string):部门名称; `path`(string):部门中文名路径（如：总公司/研发部/前端组）。


### searchJob

搜索岗位

```bash
xrxs-cli attendance searchJob --keyword <keyword> [--limit] ...
```

- **参数已说明,免 schema 查**(入参/出参结构简单,下方为完整说明):
- 入参:
  - `keyword`(keyword)[string] 必填:搜索关键字（必填）
  - `limit`(limit)[string] 可选:返回结果最大条数，默认 50，最大 100（超过夹紧为 100）
- 出参:`data 为 array,每项含` `code`(string):岗位编码; `name`(string):岗位名称; `type`(integer):岗位类型 <ul> <li>0: 岗位分类</li> <li>1: 岗位实体</li> </ul>; `jobId`(string):岗位id。


### searchRank

搜索职级

```bash
xrxs-cli attendance searchRank --keyword <keyword> [--limit] ...
```

- **参数已说明,免 schema 查**(入参/出参结构简单,下方为完整说明):
- 入参:
  - `keyword`(keyword)[string] 必填:搜索关键字（必填）
  - `limit`(limit)[string] 可选:返回结果最大条数，默认 50，最大 100（超过夹紧为 100）
- 出参:`data 为 array,每项含` `name`(string):职级名称; `rankId`(string):职级id; `levelId`(string):职级类别id（所属职级分类）。


### searchCostCenter

搜索成本中心

```bash
xrxs-cli attendance searchCostCenter --keyword <keyword> [--limit] ...
```

- **参数已说明,免 schema 查**(入参/出参结构简单,下方为完整说明):
- 入参:
  - `keyword`(keyword)[string] 必填:搜索关键字（必填）
  - `limit`(limit)[string] 可选:返回结果最大条数，默认 50，最大 100（超过夹紧为 100）
- 出参:`data 为 array,每项含` `code`(string):成本中心编码; `name`(string):成本中心名称; `costId`(string):成本中心id。


### getAllCountry

获取所有国家

```bash
xrxs-cli attendance getAllCountry [--keyword] ...
```

- **参数已说明,免 schema 查**(入参/出参结构简单,下方为完整说明):
- 入参:
  - `keyword`(keyword)[string] 可选:国家名关键字，为空返回全部
- 出参:`data 为 array,每项含` `id`(integer):国家id; `name`(string):国家名。


### getEmployeeFilterFields

获取员工数据搜索过滤条件字段返回的 FilterFieldModel 仅为筛选项「配置」(values/dateValues 为空)， 调用方按下方规则填值后，作为搜索接口(如 searchEmployee)的 filters 入参回传。 填值字段说明： values - List<DataSourceBO>，通用填值字段，value 放 DataSourceBO.key dateValues - List<String>，仅日期类型使用 按 fieldFilterType 填值规则(@see EEmployeeListFieldFilterType)： 1 日期 - 填 dateValues，2 个元素 [开始, 结束]，格式 yyyy/MM/dd 时间戳，单边留空用空串 "" 2 数字 - 填 values，1 个元素，key 格式 "min~max"，分隔符支持半角 ~ 或全角 ～，单边留空如 "25~" 3 文本 - 填 values，1 个元素，key 为关键词原文(模糊匹配) 4 选项 - 填 values，1 个或多个元素，key 取 dataSource 候选项的 key，多选取多个 6 地区(城市) - 填 values，key 为地区id 7 地区(县) - 填 values，key 为地区id 8 部门 - 填 values，key 为部门id，可多个 9 虚拟部门 - 填 values，key 为部门id，可多个 10 岗位 - 填 values，key 为岗位id，可多个 11 员工 - 填 values，key 为员工id，可多个 12 职级 - 填 values，key 为职级id，可多个 23 多选 - 填 values，多个元素，key 取 dataSource 候选项的 key 24 多级单选 - 填 values，1 个元素，key 为所选层级值 25 多级多选 - 填 values，多个元素，key 为所选层级值

```bash
xrxs-cli attendance getEmployeeFilterFields [--filter-biz-type --keyword] ...
```

- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


### searchEmployee

搜索员工

```bash
xrxs-cli attendance searchEmployee --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


### getEmployeeDetail

获取员工详情

```bash
xrxs-cli attendance getEmployeeDetail --employee-id <employeeId>
```

- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


### getFlowTypes

CLI 获取公司审批类型列表(含 settingId/isOld)。传 employeeId 时按该员工可发起范围过滤(getFlowInitiateScopeByEmployee); 不传则返回权限过滤的新表审批全集。isOld=1 为旧表审批, 调 form-setting/launch 需据此传 isOld。

```bash
xrxs-cli attendance getFlowTypes [--employee-id] ...
```

- **参数已说明,免 schema 查**(入参/出参结构简单,下方为完整说明):
- 入参:
  - `employee-id`(employeeId)[string] 可选:员工ID(选填), 传入则按该员工可发起范围过滤
- 出参:`data 为 array,每项含` `isOld`(integer):是否旧审批: 0否(新表)/1是(旧表); 调 form-setting/launch 需据此传 isOld; `flowName`(string):审批类型名称; `flowType`(integer):审批类型(标准 1-49; 自定义=settingId大数) EFlowType: 1转正/2调岗/3调薪/4请假/5外出/6补卡/7销假/8销外出/9加班/10外勤/11离职/12招聘/13录用/14证明/15工资审批/16出差/17销出差/18员工信息审核/19员工类证明/20工资类证明/21离职交接/22调店/23入职/24电子合同/25批量调薪/26上传工资明细/27上传社保公积金明细/28批量转正/29调班/30奖金包/31更新卡/32待入职员工信息审核/33管理员权限/34编外人员劳务费/35计算平台审批/36居家办公/37销居家办公/39跨公司调入/40跨公司调出/41转正式/42调整编制/43外部出勤打卡/44销加班/45导入工资表/46换班/47绩效申诉/48组织架构调整/49批量调岗;自定义审批类型=settingId(大数); `settingId`(integer):审批设置id(form-setting/launch 的 settingId)。


### getFlowList

CLI 获取审批列表(ES 查询)。groupId 缺省时默认 -1 满足权限校验。所有过滤字段纯结构化(无搜索词)。

```bash
xrxs-cli attendance getFlowList --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


### getFlowDetail

CLI 获取审批详情。sid 与 flowNumber 二选一, sid 优先; flowNumber 走 ES 解析。

```bash
xrxs-cli attendance getFlowDetail --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


### getFlowPath

CLI 获取审批流进度。sid 与 flowNumber 二选一, sid 优先。

```bash
xrxs-cli attendance getFlowPath --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


### getFlowFormSetting

CLI 获取审批表单设置, 返回三段: basicInfoGroup + fixedGroups + customGroups。三段独立容错。

```bash
xrxs-cli attendance getFlowFormSetting --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


### launchFlow

CLI 发起审批。入参=client LaunchFlowParam(全字段已同步)。编排: 身份装配 → 关联字段收敛 → 必填预校验 → getFirstApprover → launchFlowProcessNew 落库。必填缺失返回 code=-2 + data=缺失字段明细(非 fail-fast); 其他业务错误 code=-1。

```bash
xrxs-cli attendance launchFlow --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。

> ⚠️ **写入操作**:会修改数据,执行前须确认用户意图;用户已明确说「请直接执行」「请完成」等授权语时视为已授权,直接执行不再二次确认。


### launchFlowPreview

CLI 发起审批预览(不落库)。入参同 launch(client LaunchFlowParam)。编排: 身份装配 → 关联收敛 → department 推导 → getLaunchFlowPreview 流程图预览。返回路径节点 stepStatus 统一置 -1。

```bash
xrxs-cli attendance launchFlowPreview --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


## 参考
- [attendance](../SKILL.md) - 全部命令
