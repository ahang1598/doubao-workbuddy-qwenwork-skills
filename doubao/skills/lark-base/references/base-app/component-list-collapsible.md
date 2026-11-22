---
name: app-component-list-collapsible
description: App 折叠列表的默认尺寸、主区与展开区密度及协议缺口。
---

# 折叠列表 collapsible

必读 [列表协议](component-list.md)。type=list、sub-type=collapsible。默认容器宽×20，推荐W24～48、H≥16；显式宽fill，根组合决定高fill，不auto。

主区选核心识别字段；真实字段充足时展开区至少3项，承载较低频辅助信息，并与主区互斥。Builder回退前5/其后至前20字段不是业务优先级。当前CLI只有columns等公开键，未确认独立展开区字段协议时记录适配缺口，不能编expanded_fields或内部visibility。用户字段与尺寸优先，回读实际主区/展开区能证明的范围。
