---
name: app-component-ranking
description: App 排行榜的纵向尺寸、单源指标排序和TopN。
---

# 排行榜 ranking

默认16×20，推荐W8～24、H12～24，优先W≤H；不默认fill/auto。组排版、T型与用户合法尺寸优先。

仅单一data_sources，1个group_by和1个series或count_all。先确定真实排行对象，再按指标排序；状态/地区范围不误作排行对象。sort固定type=value，高值/最多/热门显式desc，最低/最少才asc；limit_size默认10、1～500，只有明确N才改N并写TopN标题。主源view_name/filter互斥。

```json
{"base_token":"<base_token>","data_sources":[{"table_name":"订单","series":[{"field_name":"金额","rollup":"SUM"}],"group_by":[{"field_name":"销售员","mode":"integrated"}]}],"limit_size":10,"sort":{"type":"value","order":"desc"}}
```

更新只动点名槽位，数组整体替换，类型不变；格式只改展示，不改排序/原值。数字格式见 [标准格式](component-charts.md)。独立回读对象、指标、范围、sort、limit、模式并取实际结果，不靠输出顺序推断已配置。
