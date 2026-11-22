---
name: app-component-list-detail
description: App 详情列表的默认尺寸、扫描密度和内建详情交互。
---

# 详情列表 detail

必读 [列表协议](component-list.md)。type=list、sub-type=detail。默认容器宽×20，推荐W32～48、H≥16；显式宽fill，根组合决定高fill，不auto。

左侧默认1个标题字段及最多2个状态/负责人/时间/金额等辅助项，详情交右侧内建区域。默认不同时外露人员字段与标签字段（单选/多选/关联/流程），按业务识别价值二选一，另一项放右侧详情；用户点名直接展示的字段优先，不擅自隐藏。fields为名称数组，detail_config.image_field_name按真实附件选择；未设置保持无图片。原Builder默认large，CLI未公开模式键时不照搬；不能臆造title角色协议。

普通查看/编辑可用右侧语义匹配字段；已有Button/VirtualTrigger随内建详情展示，不为同一动作重复row_actions。明确独立详情入口才开allowViewDetail，新增/删除仍按授权。回读字段、图片、范围、交互与矩形。
