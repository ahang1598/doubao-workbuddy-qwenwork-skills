# App 逐组件 Skill 索引

组件类型未定时读本页；已定类型直接读 [AppMode 索引](../../scenes/app-mode.md#协议索引) 中对应文件。标准图按一个图表族维护，其它组件独立维护；本页只做选型。

用户要求完整日常业务应用时，按同一规划检查支撑主任务的核心对象与阶段是否可达，再选真实组件、已验证详情/关联入口或动作承载；例如在现有项目总览 Page 安排交付里程碑区域。自行补充的设计说明依据，不伪称用户点名组件；不按底表清单逐表铺组件，也不扩充用户限定的 Page/组或给局部修改补建未要求内容。

每个组件分别核对「原话 → Page → 精确 type/subtype → 来源粒度与计算 → 范围/格式 → 动作 → 独立回读」。点名 N 项保留 N 项，展示与入口分开；底表字段不自动成为 App 展示义务。计量和资格按 [数据语义](app-data-common.md)，不足记录最小依赖与 blocked，不换代理指标。只需新增记录且原生新增动作足够时复用入口；点名 Form 则核指定 Page 的真实 Form 目标。

每个点名组件都逐个落实：按 [业务语义查重](../../scenes/app-mode/modify.md#添加组件先按业务语义查重) 核目标 Page/Tab、精确类型、数据源、字段/聚合、筛选与用途；已有匹配组件复用真实 widget ID，仅创建缺项，用户明确要相同副本则按数量新增。写后按该 ID 检查本项配置，而非统计整个 App 是否已有该类型。柱状/柱形图用 `column`，条形/横向条形图用 `bar`；点名进度条用 `progress` 且 `shape=bar`，即使指标叫“回款完成率”也不改成 statistics。看板视图、标签页沿用 view/kanban、tabs 协议，不用近似标题或其它现成组件抵扣。类型已定直接读对应文件，不额外通读选型目录。

| 业务表达 / CLI类型 | 组件Skill |
| --- | --- |
| 分类比较、趋势、占比、数值关系、阶段、文本频次、多维雷达：column/bar/line/area/combo/pie/ring/scatter/funnel/wordCloud/radar | [标准图表](component-charts.md)，含类型与展示差异 |
| 单个聚合值 statistics | [指标卡](component-statistics.md) |
| 指标排行 ranking | [排行榜](component-ranking.md) |
| 当前/目标 progress | [进度](component-progress.md) |
| 真实日期目标 countdown | [倒计时](component-countdown.md) |
| Rating样本 nps | [NPS](component-nps.md) |
| 行列交叉汇总 pivotTable | [透视表](component-pivot-table.md) |
| 未指定形态的记录清单 list/standard（≠表格视图组件，边界见 [视图](component-view.md)） | [普通列表](component-list-standard.md) |
| 同记录字段组合 list/grouped | [聚合列表](component-list-grouped.md) |
| 主区/展开区 list/collapsible | [折叠列表](component-list-collapsible.md) |
| 卡片记录 list/card | [卡片列表](component-list-card.md) |
| 内建记录详情 list/detail | [详情列表](component-list-detail.md) |
| 点名表格视图/视图组件，或明确网格/看板/画册/甘特/日历 view | [视图](component-view.md) |
| 页面交互筛选 slicer | [切片器](component-slicer.md) |
| 真实跳转入口 button | [按钮](component-button.md) |
| 独立文案 text | [富文本](component-text.md) |
| 现有素材展示 image | [图片](component-image.md) |
| 同时可见分区 comboLayout | [组合布局](component-combo-layout.md) |
| 同位置切换 tabs | [Tabs](component-tabs.md) |
| AI图宿主 ai_chart（AI 独有图型见下节） | [AI图](component-ai-chart.md) |

### 普通图表与 AI Block

- 普通图表已覆盖的 column/bar/line/area/combo/pie/ring/scatter/funnel/wordCloud/radar 默认用标准图表，不因视觉偏好改用 AI。
- 明确要求 AI Block，或桑基、玫瑰、热力、仪表、水波、瀑布、旭日、矩形树、气泡、嵌套圆、马赛克及标准图表未覆盖的 subtype，即使没说“AI”也必须建 `ai_chart`；选型、单表单源限制和源 Base 选择见 [AI Block](../ai-block.md)。AI 表达不了原话要求时标 blocked 并说明限制，不降级标准图表、text 或空图。

用户指定组件优先，不用近似组件静默替换。记录清单未指定形态默认List；用户点名“表格视图/视图组件”或其他视图形态时必须建 view，不能用 list/standard 静默替代；仅说“表格/清单/列表”等模糊词时默认 List，两种理解都成立且影响交付时先澄清，用户确认要视图组件后才用 view。多个列表默认Tabs分pane，明确同时可见/并排/连续分区时按要求。缺数据、公开能力或真实资源时记录缺口，不拿text、空图或新替代组件补失败。

索引覆盖30种CLI组件形态（含5种List subtype），标准图表统一加载一份Skill。组件文件统一使用component前缀；列表共享 [列表协议](component-list.md)，指标、筛选与来源共享 [数据语义](app-data-common.md)。
