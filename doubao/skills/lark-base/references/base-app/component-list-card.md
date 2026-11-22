---
name: app-component-list-card
description: App 卡片列表的默认尺寸、标题封面与字段展示密度。
---

# 卡片列表 card

必读 [列表协议](component-list.md)。type=list、sub-type=card。默认容器宽×20，推荐W12～48、H≥16；显式宽fill，根组合决定高fill，不auto。

data_config.card_config按真实schema选择title_field_name/image_field_name。标题外默认2～4项，字段不足可1项、最多6项；fields是正文名数组，标题、图片角色不重复入正文。

展开模式和字段排布不属于 data_config。标题外外露字段≤2时默认单列，显式 `showMode=single`；单列字段名用左右布局 `fieldShowMode=horizontal`：
`--display-config '{"card_config":{"showMode":"single","fieldShowMode":"horizontal"}}'`；
外露字段≥3时默认显示字段名；不从字段数量反推必须多列，列数按可用宽度和用户要求。showMode 为 single/multiple，fieldShowMode 为 horizontal/vertical；未确认独立字段名显隐参数时不造键，回读/渲染不能证明时报告缺口。写后从原生 Block
独立回读 display_config.card_config，不用请求回显或设置面板是否有同名开关作为生效证明。

用户要求照片时真实附件字段须承担封面角色，只有正文列出“照片”不算。未设时Builder默认multiple不是美观度方案；更新未点名样式保留。回读标题、封面、正文、展示模式与尺寸，真实渲染另验。
