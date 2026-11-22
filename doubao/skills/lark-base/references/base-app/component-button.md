---
name: app-component-button
description: App 页面按钮的默认尺寸、真实目标、Form入口和图标。
---

# 页面按钮 button

默认横向组均分×4、纵向组均分×5；单横向12×4，推荐W4～16、H3～6，不默认fill，允许合法auto。组通常同行等宽等高、首尾相接铺满；T型/用户合法尺寸与实际目标数量优先。

页面级可见按钮直属Page根，不放Tabs/组合容器。home核心入口：真实其它Page/匹配Form目标≥3至少3个，1～2全做，0跳过；非首页须明确要求或流程必要，可选组不足3不生成。不造目标、重复目标或跳当前页凑数。

新建默认按同组实际按钮数选样式：1～4个用 `data_config.direction=horizontal`、显示箭头、居左；≥5个用 `direction=vertical`、隐藏箭头、居中。单按钮不使用上下布局。方向可公开写入；箭头、对齐及圆角/图标底色未确认公开设置键时保留具体能力缺口，不将icon_visible当箭头开关。

action只允许HTTP(S)URL或当前App真实Page（不是PageGroup）；clear_action=true与action互斥，省略保留。icon/icon_visible/direction按正式协议；每个新按钮显式选择支持图标或隐藏；跳转类默认使用目标页图标，须在Button候选中确认同名或语义等价的映射，不猜枚举。目标图标无法映射时报告缺口，不静默宣称已一致。同组有无图标、emoji/图标风格、圆角与底色配置一致，用户明确要求优先。见 [图标](app-icons.md#button-图标)。

```bash
lark-cli base +app-block-create --app-token <app_token> --page-id <page_id> \
  --name "填写报名表" --type button \
  --data-config '{"action":{"type":"url","url":"<share_url>"},"icon":"form","icon_visible":true,"direction":"horizontal"}' --as user
```

下面示例假设目标页使用 `base` 图标，实际按目标页已确认图标替换。

```bash
lark-cli base +app-block-create --app-token <app_token> --page-id <page_id> \
  --name "查看订单" --type button \
  --data-config '{"action":{"type":"app_page","page_id":"<target_page_id>"},"icon":"base","icon_visible":true,"direction":"horizontal"}' --as user
```

本轮要求的匹配Form（已有或新建）由 [Form](../../scenes/form.md) 核实表、题目与分享状态，[分享读取](../form-share.md)返回真实share_url。逐个核对base_token/table_id/form_id与原需求，再在指定Page绑定入口；不只做第一个，不以表单已创建、同名或底表URL代替目标核对。按实际要求选示例入口，不同时机械创建；未要求的Form不自动增加入口。

App 内要求填写/提报时，逐项记录「原话 → 承载 Page → 可见入口 → 真实目标动作 → 独立回读」。匹配 Form 已建好不等于入口已建好，text 中放分享链接也不提供可回读的动作配置。先检查现有入口；用户点名Form时按 [Form根入口](component-list.md#记录详情新增与动作) 复用或补齐匹配Form的页面根按钮，row_actions不替代该入口。未点名Form的普通录入/处理任务，已有按钮或row_actions能满足要求时，验证其公开能力、真实目标与位置后复用，不机械增加按钮或另建Form。row_actions 只引用底表现有 Button 字段，不能猜其动作或用字段名证明能打开目标 Form。

缺入口时按上方公开 `action` schema 绑定真实目标；写失败仍修复原入口，不退成富文本链接。独立 block-get 核对按钮 action 的 URL/Page，或列表 row_actions 引用及对应 Button 字段的真实动作；structure 核对承载 Page。目标动作不可回读或依赖未就绪时标 blocked，入口配置、真实访问和实际提交分别报告。button 不能触发未公开的 Workflow 动作；本节不改变 Form、Workflow 或权限协议。

block-get核对action/icon/icon_visible，structure核对所在Page/根级及布局，真实访问/提交另验。button不支持get-data；图标或文案不代表保存/刷新/删除动作。列表专属顶部入口见 [列表](component-list.md#列表顶部页面按钮)。

“每日记进货/提交/处理”等操作要求须有App内实际可达的录入或处理入口，不能仅创建底表或金额指标卡。逐个用真实入口连接到能处理该业务对象的页面或表单，再回读目标；这不代表只列底表名称的需求也必须机械为每表增加入口。参数或权限受阻时保留动作缺口，不能把数据已存在当成动作可用。
