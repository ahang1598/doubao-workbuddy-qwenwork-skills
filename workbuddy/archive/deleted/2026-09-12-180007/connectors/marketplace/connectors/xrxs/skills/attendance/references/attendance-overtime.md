# attendance 加班管理

> **前置条件**:先阅读 [`../SKILL.md`](../SKILL.md) 了解全局能力与意图决策树。

加班管理。加班记录报表的枚举选项与列表查询、有效时长计算过程。

## 命令

### getOvertimeRecordFilterOptions

返回加班记录报表支持的打卡校验、补偿方式、加班类型、计算规则、在职类型、 数据来源和时长异常等枚举选项，用于构造 ajax-get-overtime-record-list.json 的 filterKey。 部门筛选选项需另行通过 /attendance/service/cli/common/ajax-get-auth-department.json 获取。

```bash
xrxs-cli attendance getOvertimeRecordFilterOptions [flags]
```

- schema 未声明入参,可直接调用。


### getOvertimeRecordList

按日期范围、员工关键字、异常状态、动态筛选条件和排序规则分页查询加班记录。 返回动态表头、记录数据、分页信息及上次导出字段；filterKey 的枚举值应先通过 ajax-get-overtime-record-filter-options.json 获取。 reportData 每行以 reportHeader.field 为 KEY，常用字段包括： overtimeRecordId（加班记录 ID）、name（员工姓名）、mobile（手机号）、 jobNumber（工号）、department（部门）、approvalDate（审批日期）、 overtimeRange（加班时段）、attendanceDate（考勤日期）、workType（加班类型）、 overtimeHour（申请/计算时长）、isMatchClock（打卡校验结果）、 calculationRule（计算规则）、overtimeRealHour（实际加班时长）、 compensationWay（补偿方式）、allowOffHour（有效调休时长）、 offUsedHour（已使用调休时长）、convertedHour（已结转时长）、 limitDate（有效期）、source（来源）和 planName（加班方案名称）。

```bash
xrxs-cli attendance getOvertimeRecordList --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


### getOvertimeCalculationProcess

根据加班记录 ID 查询系统计算有效加班时长的完整过程，并翻译工作日类型等展示字段。 overtimeRecordId 应从 ajax-get-overtime-record-list.json 的报表记录中获取； content 是结构化对象，Agent 可直接读取计算规则、要求的打卡范围、实际打卡、 校验结果、实际时长和最终有效时长，无需再次解析 JSON 字符串。

```bash
xrxs-cli attendance getOvertimeCalculationProcess --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


