# 仪表盘容器命令 Reference

本页维护仪表盘容器命令与返回边界。

## 命令范围

| 命令 | 对象与能力 |
|---|---|
| `+dashboard-list` | 列出 Base 内的仪表盘 |
| `+dashboard-create` | 创建仪表盘容器 |
| `+dashboard-get` | 获取仪表盘主题与组件清单；清单含组件 ID、名称和类型，不含坐标 |
| `+dashboard-update` | 修改仪表盘名称等容器配置 |
| `+dashboard-delete` | 删除仪表盘容器 |

组件的创建、修改、删除与详情使用 [组件命令](dashboard-block-commands.md)。坐标读取与写入见 [布局协议](dashboard-layout.md)，图表计算结果见 [结果协议](dashboard-chart-result.md)。容器 ID 与内部组件 ID 不可互换。

### 仪表盘主题映射与推荐风格

主题属于 Dashboard 容器，不是组件背景色或系列配色，只改图表颜色不等于设置容器主题。创建时传 `--theme-style`，已有看板用 `+dashboard-update --theme-style`。

| canonical 值（区分大小写） | 主题名称 | 精准风格词 | 推荐场景／模糊风格 | 底色／重点色参考 |
|---|---|---|---|---|
| `default` | 默认／默认主题 | 默认、常规、普通 | 经典、基础、初始、黑白对比、浅色系 | 浅灰／浅灰 |
| `SimpleBlue` | 明晰／简约蓝 | 明晰、清晰、清爽 | 商务、明亮、冷色调、干净、浅色系 | 白色／白色 |
| `DarkGreen` | 夜览／深绿 | 夜览、夜间模式 | 暗黑模式、深色系、高对比 | 黑色／灰色 |
| `summerBreeze` | 清新／夏日微风 | 清新、淡雅、治愈 | 护眼、自然、环保 | 浅蓝／白色 |
| `simplistic` | 简约／简洁／Simple | 简约、简单、极简 | 高级、中性、克制、浅色系 | 白色／灰色 |
| `energetic` | 活力 | 活力、活泼、热情 | 暖色调、高饱和、阳光 | 橙色或黄色／白色或橙色 |
| `deepDark` | 深邃／深色 | 深邃、深蓝系、暗黑 | 深色系、稳重、深沉 | 深蓝或深灰／黑色 |
| `futuristic` | 未来／未来感 | 未来、科技 | 暗黑模式、深色系、赛博朋克、紫色系 | 暗紫或黑色／紫色或深灰 |

用户给出主题名称或 canonical 值时优先采用；只有模糊风格时按推荐场景选择并说明所选主题，不把“商务”“浅色系”等多义词当唯一枚举。用户笼统说“颜色配得清爽点”且未限定组件时，推荐 `SimpleBlue`，显式落到容器主题，同时保留用户指定的局部配色；只要求某个组件配色时不改全局主题；没有风格要求时不必更换默认主题。底色／重点色只是选型参考，不是额外参数。

```bash
lark-cli base +dashboard-create --as user \
  --base-token '<base_token>' --name '销售看板' --theme-style SimpleBlue
lark-cli base +dashboard-update --as user \
  --base-token '<base_token>' --dashboard-id '<dashboard_id>' --theme-style SimpleBlue
lark-cli base +dashboard-get --as user \
  --base-token '<base_token>' --dashboard-id '<dashboard_id>'
```

写入后独立 Get，核对返回的主题配置与所选 canonical 值一致（字段路径以实际返回为准）；不凭创建成功、标题或组件颜色宣称主题已生效。

## 调用参数与创建示例

容器命令均以 `--base-token` 定位 Base；Get、Update 和 Delete 再用 `--dashboard-id` 定位容器。创建时必填 `--name`，可选 `--theme-style`；更新支持这两个配置参数，省略时保留现状。其他参数与确认要求按精确子命令 `--help`。

```bash
lark-cli base +dashboard-create \
  --base-token "<base_token>" --name "销售趋势与品类对比" --jq '.data.dashboard.dashboard_id'
```

后续组件命令使用创建返回的真实 `dashboard_id`。同名再建会报 `API error: [1]`；创建报错或取到 `null` 时先 `+dashboard-list` 查是否已建，不重建。
