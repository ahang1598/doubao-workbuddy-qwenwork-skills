# attendance 假期管理

> **前置条件**:先阅读 [`../SKILL.md`](../SKILL.md) 了解全局能力与意图决策树。

假期管理。假期余额方案查询、年假余额统计。

## 命令

### getBalanceEnabledHolidayTypeList

返回当前公司配置为“开启余额”的假期类型及名称。 返回的假期类型值用于年假报表查询和员工假期余额调整，是这些接口的 holidayType 数据源。 data 数组每项包含 holidayName（假期名称）和 holidayType（假期类型枚举值）。

```bash
xrxs-cli attendance getBalanceEnabledHolidayTypeList [flags]
```

- **参数已说明,免 schema 查**(该接口无需入参,出参说明如下):
- 出参:`data 为 array,每项含` `holidayName`(string):假期类型的展示名称，例如“年假”“育儿假”。; `holidayType`(integer):假期类型枚举值，作为后续接口的 holidayType 参数。。


### getHolidayBalanceReport

按相对活动年、假期类型、员工关键字和组织条件分页查询员工假期余额， 返回动态表头、员工余额数据、分页信息和上次导出字段；育儿假会额外返回子表头。 holidayType 应先通过 ajax-get-balance-enabled-holiday-type-list.json 获取； year 是相对活动周期， 0 表示当前周期、正数表示未来周期、负数表示历史周期。 reportData 每行以 reportHeader.field 为 KEY；convertHoliday、lastYearHolidays、 childcareData 及育儿假明细中的 usedInfoMap 均返回数组或对象，而不是 JSON 字符串。 返回的 isModifySurplus、isModifyAdjust、isModifyGiveAnnual 均为 0/1 操作权限标识； report 包含分页信息、动态表头 reportHeader、行数据 reportData 和育儿假子表头 childHeaderList。

```bash
xrxs-cli attendance getHolidayBalanceReport --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


