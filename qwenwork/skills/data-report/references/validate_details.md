# Step 3 VALIDATE 详细

> 8 项静态校验 + runtime 真渲染 + assistant_message 规则 + 数据嵌入 + JS 库白名单


```bash
python scripts/html_report.py --validate-html <output.html>
# 默认 runtime=best-effort:8 项静态 + 无头浏览器真渲染(检测到可用的 Chrome/Chromium 时自动跑,约 +7s)
# 不可用时自动降级为纯静态(仅 8 项);可用 --runtime off / required 显式控制
```

8 项静态校验:

| 检查 | 报错时怎么修 |
|---|---|
| `html` | 补 DOCTYPE / `</html>` / charset |
| `json` | 嵌入 JSON 不可解析或有 NaN/Infinity → 用 `df.replace([np.inf,-np.inf], np.nan).fillna(0)` 后再 `json.dumps` |
| `js` | `<script>` 块语法错 → 看报错位置单点修(常见: 多余 `]` / 末尾少 `)`) |
| `echarts` | 缺 ECharts script src 或用了 Chart.js/Plotly → 改用 ECharts CDN 或 inline |
| `dom_ids` | `echarts.init(getElementById('X'))` 用的 X 没对应 div → 加 `<div id="X">` 或改 init 的 id |
| `fstring` | HTML 含 `{var:.2f}` / `${var}` 残留 → 改 `.replace("__PLACEHOLDER__", value)`,不要 f-string 拼含 `{}` 的 JS/CSS |
| `numeric_literal` | HTML 文本有 `Infinity` / 裸 `NaN` → `df.replace([np.inf,-np.inf], np.nan).fillna(0)` 或显示 "—" |
| `echarts_empty_data` | ECharts `series.data=[]/null/undefined` → 数据准备失败,补数据或改用合理默认值 |

runtime 真渲染信号(无头浏览器真打开 HTML 跑):

| 信号 | 报错时怎么修 |
|---|---|
| `[pageerror]` | JS 运行时错(如 `ReferenceError: X is not defined`) → X 是哪里来的,检查模板变量是否真渲染到 HTML;Sankey DAG cycle → 数据里去掉循环路径 |
| `[console.error]` | 资源加载失败(CDN / 图片 404) → 改用本地 inline 或合法 CDN |
| `chart 容器尺寸 0x0` | CSS 让 chart div 高度为 0 → 给 `.chart-container` 设 `height: 400px`(或具体值) |
| `series.data=[]/null` | 真渲染下 ECharts 数据为空 → 数据查不出来,看 pandas 输出 |
| **`orphan_chart_div: N 个 chart 容器未渲染: [chart-X1, chart-X2, ...]`** | **HTML 写了 div 但没 init 它 → 给报错列出的每个 id 都补 `echarts.init(document.getElementById('<id>')).setOption({...})`**,不能保留空 div |
| **warnings**(不阻塞 ok) | `[no-chart-lib]` 用了 matplotlib png 替代 ECharts → 改用 ECharts;`[console.warn]` 版本过期类 → 多数可忽略 |

失败时输出详细错误(含位置)。**单点修就行,不要重写整张 HTML**(重写丢精确定位,易引入新错)。

### 交付时 assistant_message 怎么写

回复是给用户看的,**全中文,不要泄露开发术语**(禁止出现 `[SPOT CHECK]` / `pandas=` / `raw_stats=` / `data_traps` / `kpis['xxx']` / `fstring` 等内部标记或变量名)。

**原则(硬性)**:回复里的每个数字必须能在前面脚本 print 输出中找到同值,确保 HTML 与回复完全一致。

#### 实现方式(任选)

**方式 A:结构化模板(数字多 / 弱模型推荐)**

```
报告已生成:output/<path>.html

📊 核心数字
- 总销售额:¥13,650(同比 +12%)
- 销售冠军:华东区,贡献 ¥3,276,占比 24%
- (其他 KPI...)

🔍 关键洞察
- 华东 Q3 新开 12 家门店 + 618 促销转化率 18%,推动总盘增长
- (其他 2-3 条)

⚠️ 数据说明
- 已识别 1 处合并表头,按多级表头方式读取
- 12 行公式错误值(#DIV/0!)已剔除,不计入聚合
```

**方式 B:自由叙述(数字少 / 高级模型可用)**

```
2024 年总销售额 ¥13,650,华东区贡献 ¥3,276 排名第一(占 24%)。
增长主要来自 Q3 新开门店与 618 促销。
(其他 prose 叙述)

数据说明:已规避 1 处合并表头陷阱;12 行公式错误值已剔除。
```

> **自检(内部用,不出现在最终回复)**:回复里每个数字必须能在前面 transcript 的 print 输出中 grep 到同值。grep 不到 = 凭印象写 = 重做。
>
> **三处一致**:报告 HTML 顶部、报告中间表格、本回复,同一指标的取值必须完全一致(允许格式差异如千分位/小数位,值不能差)。

### 数据 inline 嵌入(硬要求)

数据**必须 inline 嵌入** HTML(如 `<script>const data = {...};</script>`),用户双击即可查看。**禁止** `fetch('data.json')` —— file:// 协议加载外部文件会失败。

### JS 库白名单(只允许 ECharts)

**唯一允许**:**ECharts** — `--validate-html` 校验 ① CDN script 存在 ② 加载顺序正确(src 在 init 之前)③ DOM id 一致 ④ 数据无裸 NaN/Infinity。

**禁用**:

| ❌ 禁 | 原因 |
|---|---|
| Chart.js / D3 / Plotly / Highcharts / Vega / Apexcharts | skill 没校验,出问题没 fallback |
| JSX / TypeScript / Vue SFC / Svelte | `node --check` 过不了 |
| React / Vue / Angular | hydration 复杂,validate 难校验 |
| 自定义 / 小众 / 私有 CDN | 沙箱内常加载失败,用户看到空白页 |
| 任何需要 `npm install` / build step 的 | 沙箱无构建链 |

ECharts option 模板片段见 `references/chart-reference.md`。

