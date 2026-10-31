# 切片器

## 配置字段

创建用 `+dashboard-block-create --type slicer --data-config '…'`，data_config 必填。公开字段：

| 字段 | 规则 |
|---|---|
| table_name | 创建必填，当前 Base 的表名 |
| group_by | 创建必填，恰好一个含 field_name 的对象；更新时整体替换，仍恰好一个 |
| group_by[0].mode | 可选，integrated / enumerated；更新 group_by 时不继承省略的子字段 |
| filter | 可省略（不筛选）；创建不接受 null |
| displayMode | dropdown（下拉面板）/ tiled（平铺）；用户明确要求时须显式设置，更新省略则保留 |
| selectMode | single / multiple |
| order | asc / desc |

## 创建默认值与示例

创建时 displayMode、selectMode、order 必须一起传或一起省略。全部省略时 CLI 补为 tiled + multiple + asc；只传部分或值非法会报错。更新不补默认值。order 在创建、更新、获取中都用小写，不接受 1/2 或 ASC/DESC。
最小配置只需 table_name 和含 field_name 的 group_by。示例：

```json
{"table_name":"订单表","group_by":[{"field_name":"地区"}],"displayMode":"dropdown","selectMode":"multiple","order":"asc"}
```

## 更新语义

用 `+dashboard-block-update --block-id <block_id> --data-config '…'`（照常传 --base-token、--dashboard-id，不传 --type，类型和字段由服务端校验）。displayMode、selectMode、order 可单独传，常用补丁：{"order":"desc"}、{"displayMode":"dropdown"}、{"selectMode":"single"}、{"filter":null}；换表和字段传 {"table_name":"客户表","group_by":[{"field_name":"客户地区"}]}。

- 同表更新时未传字段保留。filter 省略保留、null 清空；传对象则替换全部条件，不追加旧条件；conditions:[] 不能清空。普通图表更新也支持 filter:null。
- 传 {} 不修改配置；省略 --data-config 可只改名称、位置。data_config 为 null、数组或非对象时报错，--no-validate 也一样。
- 只有 table_name 解析到不同表 ID 才算换表，此时须同时传新表唯一的 group_by；未传 filter 会清除旧表筛选，传了则按新表校验。传回原表名按同表更新。
- 联动由服务端保留。表、字段或选择模式改变时清理默认选中项；只改排序、展示、筛选或同字段分组模式时保留。默认选中项、联动列表、字段类型元数据不属于可写 data_config。

## 能力与可写字段限制

- 不接受 `count_all`、`series`、顶层 `sort`、`group_by[].sort` 或内部快照字段；底层固定计数由服务端处理，无需先读再回传。
- 文本、日期、数字字段都可下拉或平铺。日期／数字范围组件或多字段映射的切片器不支持更新数据配置，但可改名称、位置；多数据源创建与更新按 [多数据源配置](dashboard-multi-source.md) 的适用条件执行。BaseApp 不支持 `type=slicer`。

## 返回结构

+dashboard-block-get 和创建、更新响应都返回服务端回读的当前配置，无筛选时省略 filter。范围模式或展示配置不全时可能只返回数据源配置（不代表可更新）；CLI 不补展示默认值。

## 输入文件与校验选项

--no-validate 跳过本地语义校验和默认值处理，原样交服务端校验；JSON 仍须是合法对象。`--data-config @file.json` 与内联 JSON 规则相同；dry-run 与执行用同一份解析后的配置。
