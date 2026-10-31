# 视图展示配置命令

筛选条件见[筛选协议](view-filter.md)；创建、重命名和删除见[生命周期命令](view-commands.md)。

## 配置命令索引

需要目标表权限。

| 配置 | 设置 | 读取 | 读取结果 |
|---|---|---|---|
| 筛选 | +view-set-filter | +view-get-filter | data.filter |
| 排序 | +view-set-sort | +view-get-sort | data.sort |
| 分组 | +view-set-group | +view-get-group | data.group |
| 可见字段 | +view-set-visible-fields | +view-get-visible-fields | data.visible_fields |
| 卡片 | +view-set-card | +view-get-card | data.card |
| 时间轴 | +view-set-timebar | +view-get-timebar | data.timebar |

筛选按筛选协议；其余 JSON 形状查对应命令的 `--help`。

## 更新与回读规则

修改已有配置时，先用对应 get 读现状，保留未改字段，只替换要求变更的项，再整体提交。

## 配置回读与记录读取

- 单项配置按上表的 get 读取。整体验收视图时读筛选、分组和排序；`calendar`、`gantt` 再读时间轴；卡片和可见字段按本次目标读取。
- 按上表的 `data` 子字段核对实际字段、操作符和值、排序方向和数组顺序；不能只看非空，也不能把创建请求或写入响应当作保存后的结果。
- 实际记录用同一 Base、表和视图 ID 调 `+record-list --view-id`；参数覆盖和分页见 [Record 读取](record-read.md#使用视图配置)。

## 看板视图分组

`kanban` 用 `+view-set-group --json '{"group_config":[{"field":"<分组字段>","desc":false}]}'`，只放 1 个字段。

- 只接受单选、多选、复选框、人员、评分、关联字段。
- 公式、文本、数字、日期、查找引用、创建人等字段会被拒；报错会列出本表可用字段。
- `grid`、`gantt` 分组没有这些限制。

先确定可用分组字段再命名；换分组后同步修正本轮自定名称，并回读核对名称与实际分组一致。

## 分组与汇总边界

`+view-set-group` 只配置分组字段和方向，`+view-get-group` 只证明分组。当前视图命令没有底部或分组 SUM 等聚合的设置和回读命令；分组成功不能证明金额合计已配置。不得猜命令或用未授权 raw API。交付缺口按 [View 决策](../scenes/view.md#将用户要求和名称映射到目标配置) 处理。

## 日历与甘特的时间轴

`calendar`、`gantt` 用 `+view-set-timebar --json '{"start_time":"<开始字段>","end_time":"<结束字段>","title":"<标题字段>"}'`，三个字段都必填。

- 起止只接受日期字段或创建时间；公式日期、更新时间会被拒。

## 配置校验与恢复

字段类型或结构被拒时，按本页限制和命令 `--help` 修正字段引用或请求形状。保存结果异常时重新读取；结果未知按[生命周期恢复](view-commands.md#结果未知时的读取)处理。
