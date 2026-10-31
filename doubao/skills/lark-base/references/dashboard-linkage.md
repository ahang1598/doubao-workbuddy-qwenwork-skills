# 仪表盘图表联动 Reference

## 对象与入口

本期只支持同一 Base、同一仪表盘中数据源相同的组件联动。使用前检查 +dashboard-block-update --help 是否有 --linkage；没有时须升级到已发布的支持版本，Skill 更新不能替代 binary 更新。

## 配置位置

联动是源组件的顶层 linkage，与 data_config 平级。组件固定的 data_config.filter 可以并存，但不能代替点击交互。

## 支持范围与输入

- 源组件：支持 pie、column、bar、line、area、scatter、radar、funnel、combo、ranking、wordCloud；ring 不支持，pivot_table 受更新入口限制也不能发起。源须能由普通 Block Get/Update 定位。
- 目标组件：普通图表、透视表、表格视图、布局内符合条件的子组件可作目标；倒计时、AI 图表、切片器、富文本、按钮、布局容器和源自身不可。
- 同源：实际数据表 ID 集合完全一致，顺序无关；维度、指标、固定筛选可以不同。多数据源时逐个目标比较，集合相交、子集或所有目标的并集都不算。同名表、同名字段不能证明同源；数据源身份、组件存在性和类型由服务端验证。
- 输入：--linkage 支持内联 JSON 和 @file，文件内容就是联动对象，不再包一层 linkage。只允许 target_block_ids，值为数组，最多 100 个非空且不重复的 ID。field_mappings 即使为空也会被拒绝；--no-validate 不跳过这些约束。

## 更新与清空语义

| 请求 | 语义 |
|---|---|
| 省略 --linkage | 保留现有联动和映射 |
| 非空 target_block_ids | 整体替换该源的目标列表，本次无字段映射 |
| `{"target_block_ids":[]}` | 清除该源的联动和字段映射 |
| {}、null、缺目标列表、带 field_mappings | 参数错误 |

## 返回范围与技术限制

- Get 只返回当前图表发起的联动，不返回指向它的反向关系；目标在 data.block.linkage.target_block_ids，清除后通常省略 linkage。
- 历史配置可能带 field_mappings，本期写入不能保留或编辑映射；不能删掉它后把“追加目标”当作等价更新。
- 同时换表和配联动时，服务端按最终数据源校验。
- +dashboard-block-get-data 不模拟选择数据点，不能单独证明点击联动生效。

## 调用示例

```bash
lark-cli base +dashboard-block-update --base-token '<base_token>' --dashboard-id '<dashboard_id>' --block-id '<source_block_id>' --linkage '{"target_block_ids":["<target_block_id>"]}'
lark-cli base +dashboard-block-update --base-token '<base_token>' --dashboard-id '<dashboard_id>' --block-id '<source_block_id>' --linkage '{"target_block_ids":[]}'
```

读取用 +dashboard-block-get。占位 ID 须换成真实组件 ID。也可把对象存为 linkage.json，用 --linkage @linkage.json 提交。--dry-run 只验证和预览请求，不访问真实数据源，也不证明部署、权限或联动生效。

## 写入失败与部分成功

更新失败可能已部分写入。先 Get 源组件确认当前状态，再决定是否重试；不把一次错误当成全部未生效，也不盲目重试。
