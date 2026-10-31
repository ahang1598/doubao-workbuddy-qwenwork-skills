# 视图筛选配置命令

## 适用范围与前置条件

支持 `filter` 的视图类型：`grid`、`kanban`、`gallery`、`calendar`、`gantt`。

## 筛选输入协议

`--json` 是 `{logic?, conditions?}` 条件对象；`conditions` 里的 `field` 写表字段名或字段 id。完整结构、operator 和各类型的 value 写法见[共享筛选条件协议](shared-filter-tuple.md)。

## 更新与回读规则

- 把用户原话的时间、主体、状态等限定逐项写成条件，用 AND 组合并回读；缺一个条件或回读记录越界就不通过。
- 更新沿用[公共配置约定](view-display.md#更新与回读规则)。`logic` 和 `conditions` 共同决定组合语义，不能只提交本次新增的条件而丢掉原有组合。
- 字段优先用真实 id；类型和实际取值以字段定义和记录证据为准。保存结果和记录按[配置回读](view-display.md#配置回读与记录读取)读取。

## 设置示例

```bash
lark-cli base +view-set-filter --base-token "<base_token>" --table-id "<table_id>" --view-id "<view_id>" \
  --json '{"logic":"and","conditions":[["状态","intersects",["Doing"]],["负责人","intersects",[{"id":"ou_xxx"}]],["截止时间","empty"]]}'
lark-cli base +view-set-sort --base-token "<base_token>" --table-id "<table_id>" --view-id "<view_id>" \
  --json '{"sort_config":[{"field":"Priority","desc":true}]}'
```

Record 读取时手动参数与视图配置的覆盖关系见[使用视图配置](record-read.md#使用视图配置)。

## 清空筛选

提交 `{"conditions":[]}`。

## 类型约束与易错点

- 请求结构被拒时，按[条件结构与默认值](shared-filter-tuple.md#条件结构与默认值)核对 tuple，不混用 `+data-query` 的对象协议。
- 操作符或值类型被拒时，按共享协议的[操作符](shared-filter-tuple.md#运算符operator)、[条件值](shared-filter-tuple.md#条件值value)、[易错点](shared-filter-tuple.md#易错点)核对。
- `formula`、`lookup` 按实际结果类型处理，不按字段名猜值，也不照抄其他字段类型的写法。
