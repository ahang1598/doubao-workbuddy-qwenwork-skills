---
name: app-component-tabs
description: App Tabs的默认样式、pane密度、嵌套列表和结构安全编辑。
---

# Tabs tabs

用于同位置多内容切换，同时可见分区用comboLayout。无数据源，默认容器宽×pane内容高，推荐W16～48、H≥16，不默认宽高fill，不从内容自适应推导auto参数。pane子组件按各自规则，用户合法尺寸优先。

新建/明确调整展示默认 `--structure-config '{"tabs_type":"line","tab_align":"left"}'`；当前CLI支持line/card/tag，三者都是标签栏样式枚举，按用户明确要求选择，未指定时使用line。未指定标签/内容时保留默认pane，不臆造分类。

单pane默认1个大型组件；多个列表/视图/透视表按对象、状态、阶段拆pane，普通说明或轻量图可以共存。嵌套列表隐藏重复标题 `--custom-info '{"shouldShowName":false}'`，`--display-config '{"background_color":"transparent","border_width":0}'`；原Agent默认新增入口只在本业务对象已授权时落实 [列表新增](component-list.md#记录详情新增与动作)，有匹配Form保留根入口。

CLI结构为 `{"panes":[{"pane_id":"<已有paneID>","name":"当前记录","children":["<已有子组件ID>"]}]}`，新pane省略pane_id，子项先创建并回读真实ID。更新显式panes为最终集合，遗漏旧pane会被移除且其中子项移回Page根；显式children也将遗漏子项移回根。追加/改名/改序保留完整未点名pane与子项，不把SDK增量factory照搬。只改样式省略panes，原子移动按命令协议；结构变化后再配受影响根布局并回读。精确形状可本地print-schema查看。

Page根布局仅引用Tabs容器，不跨pane编排子项。页面级按钮放根并与Tabs邻接。structure独立回读tabs_type/tab_align、pane树、子项稳定ID、样式及rect；不同pane不判重叠，同pane子项不能都落(0,0)。保存配置不能证明真实切换或新增动作已运行。

复制前递归核全部 pane 子树；任意后代含 View 时不支持直接 block-copy，也不承诺整树无损重建。单个 View 可按 [公开配置重建](component-view.md#复制单个-view按公开配置新建) 单独处理，不能由此推导整个 Tabs 可无损复制；不含 View 的普通容器仍按 [命令边界](app-commands.md#创建与更新边界) 复制。
