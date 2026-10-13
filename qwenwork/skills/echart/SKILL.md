---
name: echart
version: 1.0.0
description: |
  生成数据可视化图表，支持词云、折线图、柱状图、饼图、面积图及混合图表。 输出自包含 HTML 文件（引入 ECharts CDN），用户点击即可查看高质量图表。 支持导出 PNG 图片。当用户提到"生成图表"、"画个图"、"数据可视化"、 "柱状图"、"折线图"、"饼图"、"词云"、"图表展示数据"时使用。 不用于非 ECharts 的图表库（如 D3、Chart.js），不用于纯数据分析（无图表需求）。
install_source: official
install_method: download
skill_id: official_v7pZeOCq
enabled_at: 1791893737298
name_zh: ECharts 图表生成
---

# ECharts 图表生成

根据用户数据生成可视化图表，输出自包含 HTML 文件（引入 ECharts CDN）。支持折线图、柱状图、饼图、词云、面积图及混合图表。

## 禁止事项

- 禁止在 JSON 中使用函数（`formatter: function(){}` 是最常见错误）
- 禁止尾逗号（`{"a": 1,}`）、注释（`// comment`）、单引号（`{'a': 1}`）、变量引用（`"data": myData`）
- 禁止自动生成雷达图、甘特图、热力图（除非用户明确要求）
- 默认使用单 grid；用户明确要求多图拼接时可用多 grid，但需确保每个 grid 独立配置 xAxisIndex/yAxisIndex
- 禁止在 tooltip.formatter 中获取颜色
- 禁止把数值转成带单位的字符串（单位写在轴名称中）
- 禁止使用 matplotlib 默认样式生成 PNG（必须使用与 ECharts 相同的色板、字体大小、网格风格）
- 禁止在代码块前加"XX 配置"等标题
- 禁止在对话中输出 echarts 代码块（渲染不可靠，只显示原始 JSON）

## 强制要求

- 主输出物为 **HTML 文件 + PNG 图片**，每次生成图表必须同时输出两个文件
- HTML 文件：自包含，引入 ECharts CDN，生成并保存到 QoderWork 工作文件夹（outputs 目录）
- PNG 图片：通过 `Bash` 工具执行 `python3` + matplotlib 生成，必须匹配 ECharts 配色风格
- ECharts option 必须是纯 JSON（无函数、无注释、无尾逗号）
- 一个 HTML 文件 = 一个图表
- 用户需求优先：用户明确要求的样式/配置优先于本 skill 默认规范
- 无特殊要求时严格遵循本 skill 的配置规范（grid、legend、颜色等）
- 数值最多 2 位小数，百分比加 `%`
- 长标签必须缩写，大数值必须换算（单位写在轴名称中）

## 工作流

```
用户数据/需求
      |
      v
  Phase 1 — 数据分析与图表决策
  -> 识别数据类型和特征
  -> 选择最佳图表类型
  -> 确定是否需要混合图表/双 Y 轴
      |
      v
  Phase 2 — 数据预处理
  -> 长标签缩写
  -> 大数值换算
  -> 格式化处理
      |
      v
  Phase 3 — JSON 生成与样式配置
  -> 构建 ECharts option JSON
  -> 配置颜色/布局/标签/图例
  -> 应用图表技巧（方向/缩放/参考线等）
      |
      v
  Phase 4 — 合法性验收
  -> 检查 JSON 语法合法性
  -> 检查禁止项
      |
      v
  Phase 5 — 输出与导出
  -> 生成自包含 HTML 文件（保存到 QoderWork 工作文件夹）
  -> 生成 PNG 图片（matplotlib）
      |
      v
  输出渲染就绪的图表
```

## Phase 1 — 数据分析与图表决策

### 图表类型选择

| 数据场景 | 推荐图表 |
|---------|---------|
| 时间序列趋势 | 折线图 |
| 分类比较 | 柱状图 |
| 占比（<= 5 类） | 饼图 |
| 占比（> 5 类） | 排序柱状图 |
| 文本频次 | 词云 |

### 多指标对比决策

| 情况 | 选择 |
|------|------|
| 同单位、量级相近（如各部门销售额） | 多线图 |
| 量 + 率（如销量 + 增长率） | 柱状 + 折线混合 |
| 量级差异大（如收入万元 + 占比%） | 双 Y 轴（谨慎）或拆成两图 |

## Phase 2 — 数据预处理

输出前必须简化数据，防止标签/数值过长导致显示失调：

| 问题 | 处理方式 | 示例 |
|------|---------|------|
| 标签过长 | 缩写关键信息 | "2024 财年 xx 电子公司 Q3 华东区域销售业绩" -> "Q3 华东" |
| 数值过大 | 换算并标注单位到轴名称 | `yAxis.name: "销售额(万)"`，数据用 `[10, 20]` |
| 百分比 | 加 `%` 后缀 | `"{d}%"` |
| 小数位 | 最多 2 位 | 3.1415 -> 3.14 |

## Phase 3 — JSON 生成与样式配置

### 输出格式

**主输出：HTML 文件**

生成自包含 HTML 文件并保存到 QoderWork 工作文件夹（outputs 目录），用户点击文件链接即可在 QoderWork 中查看高质量交互式图表。

HTML 模板结构：
```html
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>图表标题</title>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
</head>
<body>
  <div id="chart" style="width: 100%; height: 600px;"></div>
  <script>
    var chart = echarts.init(document.getElementById('chart'));
    var option = { /* ECharts option JSON */ };
    chart.setOption(option);
    window.addEventListener('resize', function() { chart.resize(); });
  </script>
</body>
</html>
```

文件命名：`<主题>_chart.html`（如 `sales_growth_chart.html`）。

**禁止**在对话中输出 echarts 代码块（渲染不可靠，只会显示原始 JSON 文本）。图表展示完全依赖 HTML 文件 + PNG 图片。

### 颜色配置

**在 series 层级设置颜色**，legend 自动继承：
```json
{
  "series": [{
    "name": "2024年",
    "type": "bar",
    "itemStyle": { "color": "#ee6666" },
    "data": [120, 230, 180]
  }]
}
```

**饼图**：每个扇区需不同颜色，在 data 项中指定：
```json
"data": [
  { "value": 100, "name": "A", "itemStyle": { "color": "#d97757" } },
  { "value": 80, "name": "B", "itemStyle": { "color": "#6a9bcc" } }
]
```

**按数据项区分颜色**（正负值、突出某项等）：在 data 项中指定
```json
"data": [
  { "value": -12, "itemStyle": { "color": "#ee6666" } },
  { "value": 5, "itemStyle": { "color": "#91cc75" } }
]
```

**词云**：在 data 项中用 `textStyle` 指定颜色。

**色板选择：**

| 场景 | 色板 |
|------|------|
| 默认（温暖简约） | `["#d97757", "#6a9bcc", "#788c5d", "#c4a35a", "#8b7cb6", "#c97b84", "#5d8c8c", "#a67c52", "#b0aea5"]` |
| 商务风格（备用） | `["#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de", "#3ba272", "#fc8452", "#9a60b4", "#ea7ccc"]` |
| 聚焦用色 | 其他数据用灰色 `#b0aea5`，关键数据用亮色 |

### 标题配置

标题应传达洞察而非仅描述数据：
- 避免："月度销售数据"
- 推荐："Q3 销售额增长 40%"

### 布局配置

**笛卡尔坐标系**（柱状图、折线图等）推荐 grid：
```json
{ "grid": { "left": "6%", "right": "6%", "bottom": "3%", "containLabel": true } }
```

**横向柱状图 / 有 Y 轴名称时**：`"grid": { "left": "8%", "right": "6%", "bottom": "3%", "containLabel": true }`

**双 Y 轴时**：`grid.right` 至少 `"8%"`，给右侧轴标签留空间。

**图例规则**：
- 单系列：`"legend": { "show": false }`
- 多系列（2-5）：`"legend": { "top": "top" }`
- 系列较多（> 5）：`"legend": { "type": "scroll", "top": "top" }`

**坐标轴颜色**：设置为深灰 `#666`：
```json
{
  "xAxis": { "axisLabel": { "color": "#666" }, "axisLine": { "lineStyle": { "color": "#666" } } },
  "yAxis": { "axisLabel": { "color": "#666" }, "axisLine": { "lineStyle": { "color": "#666" } } }
}
```

**数值显示**：
- 数据点 <= 6：用 `"label": { "show": true }` 直接显示
- 数据点较多：用 `"tooltip": { "trigger": "axis" }` 悬浮显示（饼图用 `"trigger": "item"`）

**label.position 参考**：纵向柱状 `"top"` | 横向柱状 `"right"` | 堆积图 `"inside"` | 折线图 `"top"` | 饼图省略（自动）

### 格式化模板

- `{a}` 系列名、`{b}` 类别、`{c}` 值、`{d}` 百分比（仅饼图）
- 使用 `{b}` 时 data 每项必须有 `name` 字段
- 模板占位符用 `: ` 分隔，禁止 `\n`（如 `"{b}: {d}%"`）
- 多系列使用 `"trigger": "axis"`，ECharts 自动列出各系列值，无需手动拼接
- 单位后缀在 label.formatter 中添加（如 `"{c}%"`），不要在 tooltip.formatter 中用函数

### 图表技巧

**柱状图方向：**
- 类别 <= 6 个或时间序列 -> 纵向
- 类别 > 6 个或标签较长 -> 横向（数据预排序 + `yAxis.inverse: true` 实现降序）

**饼图：**
- 必须独占 series，不能与其他类型混合
- 默认实心饼图：`"radius": "70%"`
- 环形图（用户要求时）：`"radius": ["40%", "70%"]`

**双 Y 轴：**
- yAxis 写为数组，第二个轴加 `"splitLine": { "show": false }` 防网格线重叠
- 每个 series 通过 `"yAxisIndex": 0` 或 `"yAxisIndex": 1` 绑定对应轴
- 率类（增长率/占比）的轴使用 `"scale": true`
- `grid.right` 至少 `"8%"` 给右侧轴标签留空间
- legend 必须显示，帮助用户区分系列与轴的对应关系

**混合图表：**
- 折线 + 柱状图时，`xAxis.boundaryGap` 保持默认 `true`

**堆积图：**
- 同类 series 设置相同 `"stack": "总量"` 值即可堆积
- 堆积柱状图加 `"label": { "show": true, "position": "inside" }`
- 堆积面积图用 `"areaStyle": {}` 搭配 `"stack"`

**X 轴标签过多（> 8 个）：**
- 旋转标签：`"axisLabel": { "rotate": 45 }`

**时间轴数据：**
- 数据点 > 15 个时，考虑按时段聚合或使用 `"xAxis": { "type": "time" }`
- time 类型需完整时间格式：`["2024-12-11 09:30", 27]`

**数据点较多（> 20）：**
- 添加缩放条：`{ "dataZoom": [{ "type": "slider" }] }`

**参考线：**
```json
{ "markLine": { "data": [{ "type": "average", "name": "平均" }] } }
```

**面积图渐变：**
```json
"areaStyle": {
  "color": { "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
    "colorStops": [{ "offset": 0, "color": "rgba(84,112,198,0.5)" }, { "offset": 1, "color": "rgba(84,112,198,0)" }]
  }
}
```

**词云：**
```json
{
  "type": "wordCloud",
  "width": "100%", "height": "100%",
  "gridSize": 8, "sizeRange": [14, 60],
  "rotationRange": [0, 0], "drawOutOfBound": false
}
```

## Phase 4 — 合法性验收

生成后逐项检查：

| 检查项 | 合法 | 非法 |
|--------|------|------|
| formatter | `"{b}: {c}"` | `function(params) { return ... }` |
| 词云颜色 | 每项 `"textStyle": { "color": "#xxx" }` | `function() { return colors[...] }` |
| 尾逗号 | `{"a": 1}` | `{"a": 1,}` |
| 注释 | 无 | `// comment` 或 `/* */` |
| 引号 | `"a"` | `'a'` |
| 变量 | 内联数据 | `"data": myData` |
| 多 grid | 单 grid（默认） | 无理由的多 grid 拼接 |

## Phase 5 — 输出与导出

每次生成图表必须**同时输出 HTML + PNG 两个文件**。

### Step 1：生成 HTML 文件

生成自包含 HTML 文件并保存到 QoderWork 工作文件夹（outputs 目录）：
1. 使用上述 HTML 模板，将 ECharts option JSON 嵌入 `<script>` 中
2. option 中的 JSON 必须合法（无函数、无注释、无尾逗号）
3. 文件命名：`<主题>_chart.html`（如 `sales_growth_chart.html`）

### Step 2：生成 PNG 图片

通过 `Bash` 工具执行 `python3` + matplotlib 生成配色一致的 PNG：

**依赖检查**（生成 PNG 前必须执行）：
```bash
python3 -c "import matplotlib" 2>/dev/null || { echo "缺少依赖：matplotlib，请先安装：pip3 install matplotlib"; exit 1; }
```

PNG 生成步骤：
1. **必须使用与 ECharts 相同的色板**（默认 `["#d97757", "#6a9bcc", "#788c5d", ...]`）
2. 图片尺寸 `figsize=(12, 7)`，`dpi=150`
3. 文件命名与 HTML 对应：`<主题>_chart.png`
4. 禁止使用 matplotlib 默认配色和默认样式

matplotlib 风格初始化模板：
```python
import matplotlib.pyplot as plt
plt.rcParams.update({
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'axes.edgecolor': '#666',
    'axes.labelcolor': '#666',
    'xtick.color': '#666',
    'ytick.color': '#666',
    'grid.color': '#eee',
    'grid.linestyle': '-',
    'font.size': 12
})
# 使用与 ECharts 一致的色板
colors = ["#d97757", "#6a9bcc", "#788c5d", "#c4a35a", "#8b7cb6", "#c97b84"]
```

### Step 3：交付

向用户展示：
1. 告知 HTML 文件路径，引导点击在 QoderWork 中查看交互式图表
2. 告知 PNG 文件路径，可直接下载分享
3. 简要描述图表的设计要点（配色、布局、数据洞察）

## 迭代修改指南

用户生成图表后常要求微调。处理规则：

| 用户请求 | 修改目标 |
|---------|---------|
| 改颜色 | series.itemStyle.color（饼图改 data[].itemStyle.color） |
| 加/去数据标签 | series.label.show |
| 换图表类型 | series.type + 同步调整轴配置（饼图需移除 xAxis/yAxis） |
| 加平均线/参考线 | series.markLine |
| 改标题 | title.text |
| 加/改图例 | legend 配置 |
| 改 tooltip 格式 | tooltip.formatter 模板字符串 |

**核心原则**：
- 每次修改后重新输出 **HTML + PNG 两个文件**（完整覆盖），不输出 diff 片段
- 未涉及的配置保持上一版本不变

## 意图映射

| 用户意图 | Agent 行为 |
|---------|-----------|
| 明确指定图表类型 | 跳过类型决策，直接生成 |
| "用什么图好" | Phase 1 重点做类型决策 |
| 有数据 + 有可视化需求 | Phase 1-5 全流程 |

## 易混淆场景（不要用本 Skill）

- D3 / Chart.js 图表 → 对应图表技能
- 纯数据分析（无图表需求）→ 数据分析技能
- PPT / Excel 图表 → 对应技能
- 流程图 / 架构图 → Mermaid 技能

## 使用示例

### 示例 1：简单柱状图
**输入**："用柱状图展示 Q1-Q4 销售额：120, 230, 180, 350"

**输出**：
```echarts
{
  "title": { "text": "Q4销售额飙升至350万" },
  "grid": { "left": "6%", "right": "6%", "bottom": "3%", "containLabel": true },
  "xAxis": { "type": "category", "data": ["Q1", "Q2", "Q3", "Q4"], "axisLabel": { "color": "#666" }, "axisLine": { "lineStyle": { "color": "#666" } } },
  "yAxis": { "type": "value", "name": "销售额(万)", "axisLabel": { "color": "#666" }, "axisLine": { "lineStyle": { "color": "#666" } } },
  "series": [{ "type": "bar", "data": [120, 230, 180, 350], "itemStyle": { "color": "#d97757" }, "label": { "show": true } }]
}
```

### 示例 2：多线折线图
**输入**："对比产品 A 和 B 月活趋势（1-6月）：A [820,932,901,1034,1290,1330]，B [620,732,791,834,1090,1230]"

**输出**：
```echarts
{
  "title": { "text": "产品A月活持续领先，双方Q2起加速增长" },
  "legend": { "top": "top" },
  "tooltip": { "trigger": "axis" },
  "grid": { "left": "6%", "right": "6%", "bottom": "3%", "containLabel": true },
  "xAxis": { "type": "category", "data": ["1月", "2月", "3月", "4月", "5月", "6月"], "axisLabel": { "color": "#666" }, "axisLine": { "lineStyle": { "color": "#666" } } },
  "yAxis": { "type": "value", "name": "月活(人)", "axisLabel": { "color": "#666" }, "axisLine": { "lineStyle": { "color": "#666" } } },
  "series": [
    { "name": "产品A", "type": "line", "data": [820, 932, 901, 1034, 1290, 1330], "itemStyle": { "color": "#d97757" }, "label": { "show": true } },
    { "name": "产品B", "type": "line", "data": [620, 732, 791, 834, 1090, 1230], "itemStyle": { "color": "#6a9bcc" }, "label": { "show": true } }
  ]
}
```

### 示例 3：饼图
**输入**："展示市场份额：A 公司 35%，B 公司 25%，C 公司 20%，其他 20%"

**输出**：
```echarts
{
  "title": { "text": "A公司以35%份额领跑" },
  "tooltip": { "trigger": "item", "formatter": "{b}: {d}%" },
  "series": [{
    "type": "pie", "radius": "70%",
    "data": [
      { "value": 35, "name": "A公司", "itemStyle": { "color": "#d97757" } },
      { "value": 25, "name": "B公司", "itemStyle": { "color": "#6a9bcc" } },
      { "value": 20, "name": "C公司", "itemStyle": { "color": "#788c5d" } },
      { "value": 20, "name": "其他", "itemStyle": { "color": "#b0aea5" } }
    ]
  }]
}
```

### 示例 4：柱状+折线混合（双 Y 轴）
**输入**："展示1-6月销售额和环比增长率：销售额 [120,150,180,160,210,280] 万，增长率 [null,25,20,-11,31,33]%"

**输出**：
```echarts
{
  "title": { "text": "销售额逐季攀升，6月环比增长33%" },
  "legend": { "top": "top" },
  "tooltip": { "trigger": "axis" },
  "grid": { "left": "6%", "right": "8%", "bottom": "3%", "containLabel": true },
  "xAxis": { "type": "category", "data": ["1月", "2月", "3月", "4月", "5月", "6月"], "axisLabel": { "color": "#666" }, "axisLine": { "lineStyle": { "color": "#666" } } },
  "yAxis": [
    { "type": "value", "name": "销售额(万)", "axisLabel": { "color": "#666" }, "axisLine": { "lineStyle": { "color": "#666" } } },
    { "type": "value", "name": "增长率(%)", "scale": true, "splitLine": { "show": false }, "axisLabel": { "color": "#666" }, "axisLine": { "lineStyle": { "color": "#666" } } }
  ],
  "series": [
    { "name": "销售额", "type": "bar", "yAxisIndex": 0, "data": [120, 150, 180, 160, 210, 280], "itemStyle": { "color": "#d97757" }, "label": { "show": true } },
    { "name": "增长率", "type": "line", "yAxisIndex": 1, "data": [null, 25, 20, -11, 31, 33], "itemStyle": { "color": "#6a9bcc" }, "label": { "show": true, "formatter": "{c}%" } }
  ]
}
```

## 错误处理

| 错误 | 处理方式 |
|------|---------|
| 用户未提供数据 | 询问用户提供具体数据 |
| 数据格式异常（缺失值、非数值） | 标注异常项，询问用户如何处理 |
| 类别过多（> 20）建议换图表类型 | 建议使用横向柱状图或 Top N 截取 |
| 用户要求的图表类型不适合数据 | 说明原因，推荐更合适的类型 |
| 生成的 JSON 过于复杂 | 拆分为多个独立图表 |
