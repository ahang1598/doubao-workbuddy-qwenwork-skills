# 0-1 搭建：从需求到可用应用

**完整新建默认≥3有效Page，PageGroup/空页不计数；先完成真实首页T型。** 用户明确最终页数/闭合集合优先。开工按AppMode输出三行计划，交付逐项验收。

处理需要业务规划的新 App、现有 Base 转 App、页面集合重组，以及给定页面骨架后的业务内容补齐。明确组件集合的直接新增或明确仅操作页面树结构见 [简单搭建](simple.md)，已有对象局部修改见 [1-n](modify.md)。协议按 [AppMode 索引](../app-mode.md#协议索引) 命中读取；参数看精确命令 help。

## 第 1 步：按原话确定页面和操作

- 分清Page、PageGroup、组件及查看/统计/录入/处理目标，明确集合原样保留；仅限定树时在树内补内容。页数/组规则必读 [搭建规则](../../references/base-app/app-visual-quality.md#page-与-pagegroup)，小应用/首页描述不减页。
- 点名“三个页面组：总览首页、我的待办、客户档案”就建3个真实组并挂页，首页保留父组；强制组可单子页，组最多两层、不计页数。
- 每个录入/处理对象有独立真实入口，库存列表/销售按钮不代替进货入口。核心路径能进入→定位→详情→行动；完整日常App至少一个核心对象可查看、详情、新建、编辑，明确只读不开写。
- 不为辅助字典/中间表逐表造页，不用空页/重复分析凑数。

### 给定页面骨架时补齐业务内容

“先搭骨架”仅闭合Page/PageGroup及归属，仍按职责补可用内容；不默认增页，未封闭组件集合仍执行适用首页T型。

例：工单总览放真实汇总/主列表/导航；待处理、已完结页绑定工单表，按完整状态值域筛选并显示关键字段及详情/处理；客户、服务组、SLA页各承载对应实体，不能全复制无筛选工单。按原话/公开能力开操作，不凭页名开放删除或新增流程；缺源/关系交最小依赖并标未完成。

逐页核树、有效组件、源、筛选、字段、入口；仅标题/占位或复制全量列表不算完成，真实空结果可接受，不造数据。

## 第 2 步：准备来源和依赖

- 计量实体不变：任务按项目状态筛时用动态关系/Formula/Lookup，不能数项目或改任务状态；范围/时间/指标按 [数据协议](../../references/base-app/app-data-common.md)。
- 表、字段、关联和记录交 [Build-system](../build-system.md)，Form 交 [Form](../form.md)，状态流转和通知交 [Workflow](../workflow.md)。复用真实 ID，依赖完成后继续搭建 App，不把底表已建当成页面已完成。
- Form分享URL接指定页按钮，普通录入可用授权原生新增；跳转页须承载目标对象动作。
- 比率核分子/完整分母/资格/周期，总金额比不平均逐行比率；趋势用真实发生/观测日期及数值，不按对象名折线。
- App 角色按 [App 权限 Scene](../app-permission.md)确定范围，再读 [应用高级权限](../../references/lark-base-app-role-config.md)，不使用普通 Base 的 `+role-*`。已有 Base 不默认造数，也不新建平行应用。

## 第 3 步：创建 App 与页面

| 已有资源 | 操作 |
| --- | --- |
| Workspace + Base | 确认 Base 在同一 Workspace → `+app-create` |
| Workspace，无 Base | `+app-create` → `+base-create` → `+workspace-move-in` |
| 无 Workspace，有 Base | 先确认 Base 所属 Workspace；不能确定请用户提供 |
| 两者都没有 | `+workspace-create` → `+app-create` → `+base-create` → `+workspace-move-in` |

`+app-create` 后 `+app-get` 取默认Page，page-update设首页名称/图标/父组，只为其它页page-create；默认首页计1页，未限定完整App还须≥2不同用途页。按 [图标候选](../../references/base-app/app-icons.md) `+app-update --icon` 及新Page/组显式配图标，用户名称原样保留；缺默认ID读get/page-list，不另建替代。列表只引用同Workspace一个Base。

page-tree-list分页收齐核类型/父级/顺序；最多100Page，每页200组件、10列表（含容器），超限/无权限报告不删要求。名称≤8字默认、语义图标、≥7页分组、首页标题按搭建规则。

### 用户点名 PageGroup 时的创建顺序

先建组，再建子页，最后回读父子关系。名称与用户原话一致；Page 与 PageGroup 共用全局唯一命名空间，建前先查重。

```bash
# 1. 建组
lark-cli base +app-page-group-create --app-token <app> --name "<组名>" --as user
# 2. 建子页并直接挂到该组
lark-cli base +app-page-create --app-token <app> --name "<子页名>" --page-group-name "<组名>" --as user
# 3. 默认首页放进指定组（二选一）
lark-cli base +app-page-update --app-token <app> --page-id <home> --parent-id <group_id> --as user
lark-cli base +app-page-node-move --app-token <app> --node-name "<首页名>" --parent-page-group-name "<组名>" --as user
# 4. 回读父子关系
lark-cli base +app-page-tree-list --app-token <app> --page-size 100 --as user \
  --jq '((.data.items // .data.pages) // [])[] | {type, name, parent_id}'
```

回读：每个点名组type=page_group、子页parent_id正确，≤2层，无空组；默认≥2有效子页，强制组可1页。

“A/B两个页面”建2Page；“A/B两个页面组”建2组，仍默认≥3Page。先核类型再写组件。

## 第 4 步：逐页写入并回读

1. 读对应组件协议，同页串行创建并立即block-get核类型、源、字段、筛选、分组、聚合、排序、格式/动作，保存真实widget_id/chart_token。
2. 点名组件逐项完成，column柱状、bar条形、view表格/看板，不用list/文本抵扣；AI用ai_chart+ai-config专属协议。
3. 就绪后一次page-update --layout-config写每个根ID恰好一次；默认堆叠/创建顺序/text auto不算整页布局。必读 [布局](layout.md)，首页执行下例和T型骨架。
4. 完整structure核位置/模式/父级，计算组件用chart_token+真实源Base取数对账；本页完成再继续。

### T 型首页写法

标题按下例同时写H1、实际字号/粗体，回读text_runs；替换文案/ID。future/technology副文案用#FFFFFFB3，其它灰色，用户样式优先。

```bash
lark-cli base +app-block-create --app-token <app> --page-id <home> --name "首页标题" --type text --data-config '{"text":"# 经营概览\n查看本月经营数据与待办事项。","text_styles":[{"target":"经营概览","style":{"font_size":26,"bold":true}},{"target":"查看本月经营数据与待办事项。","style":{"font_size":16,"font_color":"#646A73"}}]}' --display-config '{"line_spacing":1.3,"background_color":"transparent","border_width":0}' --layout-config '{"position":{"x":0,"y":0,"w":48,"h":3},"size_mode":{"width":"fixed","height":"auto"}}' --as user
```

按 [首页 T 型](../../references/base-app/app-visual-quality.md#首页-t-型) 的适用/内容规则替换以下真实ID或唯一精确名；不足列缺口，不造指标/重复图。

```bash
lark-cli base +app-page-update --app-token <app> --page-id <home> --layout-config '{"exact":[
 {"name":"<标题ID>","x":0,"y":0,"w":48,"h":3},
 {"name":"<按钮1>","x":0,"y":3,"w":11,"h":4},{"name":"<按钮2>","x":11,"y":3,"w":10,"h":4},{"name":"<按钮3>","x":21,"y":3,"w":11,"h":4},
 {"name":"<指标1>","x":0,"y":7,"w":11,"h":6},{"name":"<指标2>","x":11,"y":7,"w":10,"h":6},{"name":"<指标3>","x":21,"y":7,"w":11,"h":6},
 {"name":"<主列表>","x":0,"y":13,"w":32,"h":24},
 {"name":"<进度>","x":32,"y":3,"w":16,"h":8},{"name":"<图表1>","x":32,"y":11,"w":16,"h":13},{"name":"<图表2>","x":32,"y":24,"w":16,"h":13}
],"on_missing":"strict"}' --as user
lark-cli base +app-block-update --app-token <app> --page-id <home> --block-id <标题ID> --layout-config '{"size_mode":{"width":"fixed","height":"auto"}}' --as user
```

根ID各一次，1～2按钮均分32，无按钮上移；插真实控制行同时后移左右区。按布局协议修底边/满宽/标题独行，完整structure重新核；标题样式按 [text](../../references/base-app/component-text.md)。

## 交付前结构门禁

先跑页数门禁（完整分页），再跑 [T 型自检](layout.md#t-型自检交付前必跑)，FAIL先修复重跑：

```bash
# Page 与 PageGroup 分开计数
lark-cli base +app-page-tree-list --app-token <app> --page-size 100 --as user \
  --jq '((.data.items // .data.pages) // []) as $n | {pages: ([$n[] | select(.type=="page")] | length), groups: ([$n[] | select(.type=="page_group")] | length)}'
```

| 门禁 | PASS 条件 |
| --- | --- |
| 页数 | 用户未明确限定页数时 `pages >= 3`；明确限定时 `pages` 等于指定数量。`groups` 不计入 `pages` |
| 页面组 | 用户点名的每个组与父子关系正确；无空组；默认无单页组，用户强制指定组例外；≥7页时已按业务分组而非全部平铺 |
| 名称与图标 | 用户明确指定的名称/图标优先保留；其余名称非空且不用默认文案，自拟名≤8字符；默认图标有业务语义，首位且名含“首页”的Page使用home |
| 首页主列表字段 | 按 [首页字段计数](../../references/base-app/app-visual-quality.md#首页主列表字段计数) 核同一主列表初始可见的≥5个不同业务字段及详情路径；用户明确覆盖按原话，真实不足/未验证须列缺口，不借详情或其他列表凑数 |
| T 型 | 首页满足 [T 型自检](layout.md#t-型自检交付前必跑) 的四项条件 |

第5步记 `pages=N, groups=M, T=PASS/FAIL`；不足/归属错先补建或移动重跑，不以改名/同名新页/答复代替。

## 第 5 步：核对原话并交付

必读并执行 [末次写后验收](../../references/base-app/app-checks.md#末次写后)，先记结构门禁，逐项核页/组、组件、字段、资格/周期/指标、入口、图标与首页T型；缺页/空页补有效内容，错误修复后重读受影响项。配置、计算、渲染/动作分验，标 `已验证 / 未完成 / 未验证`。

最终必须给可点击真实App链接，按需附页面/Form/目标页链接，不猜路径或只描述。失败先查状态仅续未成功部分，保留父组/源/完整条件/图型/周期/动作，按 [恢复表](../../references/base-app/app-commands.md#常见恢复) 处理，不放宽或建替代品。
