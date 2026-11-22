---
name: app-component-list-grouped
description: App 聚合列表的原子尺寸、组合列密度和分组边界。
---

# 聚合列表 grouped

必读 [列表协议](component-list.md)。type=list、sub-type=grouped；渲染类型与group_by分别配置，不互相替代。默认容器宽×20，推荐W24～48、H≥16；显式宽fill，根组合决定高fill，不auto。

默认每个组合列最多3项，优先外露1～2项核心信息，combined仅组合同记录字段。用户点名组合优先；不因聚合列表名字新增数值series或假设只能一个group_by。回读组合、分组、排序、范围及模式。
