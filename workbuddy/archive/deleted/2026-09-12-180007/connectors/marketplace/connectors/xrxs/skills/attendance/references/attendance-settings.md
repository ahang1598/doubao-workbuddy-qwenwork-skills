# attendance 方案管理

> **前置条件**:先阅读 [`../SKILL.md`](../SKILL.md) 了解全局能力与意图决策树。

方案管理。排班方案查询与员工方案归属查询。

## 命令

### getSchedulingAttendancePlanList

方案管理：获取排班方案列表

```bash
xrxs-cli attendance getSchedulingAttendancePlanList [--keyword] ...
```

- **参数已说明,免 schema 查**(入参/出参结构简单,下方为完整说明):
- 入参:
  - `keyword`(keyword)[string] 可选:检索关键词
- 出参:`data 为 array,每项含` `planId`(integer):方案ID; `planName`(string):方案名称。


### getEmployeeAttendancePlanData

注意：返回员工与方案之间的对应关系，结果集返回示例：HashMap → Key:员工ID, Value:方案ID

```bash
xrxs-cli attendance getEmployeeAttendancePlanData --request-body '<JSON>'
```

- 入参含 JSON 请求体,须用 `--request-body` 传参(详见 SKILL.md)。
- 入参/出参为复杂结构,调用前查 `xrxs-cli schema attendance.<command>`。


## 参考
- [attendance](../SKILL.md) - 全部命令
