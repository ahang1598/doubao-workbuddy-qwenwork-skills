---
name: app-component-slicer
description: App 切片器的原子尺寸、字段类型、布局前置和联动对象。
---

# 切片器 slicer

默认同行均分/容器宽×3，推荐W12～48、H3～4，不默认fill/auto。一行≤4、同行等宽等高，每行含尾行按实际数量均分铺满所属区域；末行单项也满宽，不为跨行固定列宽留下侧洞，避免下方组件向上补位，见[画布补洞约束](../../scenes/app-mode/layout.md#画布会向上补洞不能用空位占行)。单字段一个组件，不拆选项凑数量。用户指定优先；具体排布见[布局正例](../../scenes/app-mode/layout.md#消除留白的正向示例)。

base_token/table_name/field_name必填，可选display_mode/select_mode/order/filter/additional_data_sources/apply_to_block_ids。按字段有效输出类型：enum用dropdown/tiled，datetime用date_component，number用number_component；Formula/Lookup先Base输出类型再实际App field_type，不按名称猜。

真实离散选项≤4且宽度足够优先tiled，>4、长文本或宽不足dropdown，数量未知不能当少量。select_mode/order只对枚举有可见意义；副源输出类型必须兼容，固定filter限制选项而非用户已选条件。

```json
{"base_token":"<base_token>","table_name":"订单","field_name":"地区","display_mode":"dropdown","select_mode":"multiple","order":"asc"}
```

apply_to_block_ids只用同页已存在真实ID，保留用户作用范围；省略/清空按当前协议，不照搬SDK名称数组。get只读顶层field_type为enum/datetime/number，源于实际快照，历史可省略，不放data_config。

创建/改联动须完成 [位置闭环](../../scenes/app-mode/layout.md)：无明确相对位置时，每个切片器y小于全部同源受作用组件y；明确旁边/同行/左/右或数据顶部优先。独立回读字段类型、显示、范围、目标和坐标，实际联动另验，命令成功不能证明全页联动。
