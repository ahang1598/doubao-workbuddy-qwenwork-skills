# HTML 研报输出规范

分析 / 对比 / 研报型回答产出 HTML 文件时遵循本规范。简短 Q&A、单数字查询、Yes-No 判断仍用 Markdown，不必出 HTML。

> **前置自检（产出 HTML 前必须执行）**：本规范只负责输出格式，不能替代任何方法论 reference。产出 HTML 前必须确认：(1) 所有主场景的核心方法论 reference 均已加载；(2) 方法论内容已实际体现在分析中而非仅完成文件读取。若存在缺失，先加载对应 reference 再产出 HTML。

## 0. 交付前必做：JS 语法自检（最高优先级）

HTML 里手写的内联 `<script>`（尤其 ECharts `option`）**极易出现括号 / 引号配对错误**——多层嵌套对象、箭头函数 `s=>({...})`、字符串字面量跨行，自己读一遍看不出来，但只要有一处失配，整个 `<script>` 块就 `SyntaxError`，该页**所有图表全部不渲染**（不是一个图空，是全空）。这是 HTML 报告最高频的致命缺陷。

所以 **HTML 写完、交付给用户之前，必须对内联 JS 做一次语法校验**：

```bash
# 把 HTML 里的内联 <script> 体抽出来存成 .js，再校验；任意一种等价方式均可
node --check /tmp/_check.js          # 通过则静默，报错会精确指出行列
```

- 报错 → 按提示定位那一行，修正括号 / 引号 / 逗号，**改到 `node --check` 通过为止**，再交付。
- 没有 node 时，用 `python3 -c "import esprima"` 之类亦可；实在无工具，就**人工逐个 `setOption({...})` 数括号配平**，重点查箭头函数返回对象 `=>({...})` 和多层 `series:[{...}]`。
- 不要把"生成了 HTML 文件"当作完成——**图表能渲染才算完成**。

高发错误形态（写之前先警惕）：
- `data:arr.map(s=>({value:s.a,itemStyle:{color:s.c}}))` —— `=>({` 配 `}))`，少一个 `)` 或多一个 `}` 都废
- `formatter:'{b}: {c}%'` —— 字符串别跨行写，跨行会断裂
- `series:[{...}}, {...}]` —— 嵌套对象结尾多一个 `}`
- `legend:{data:['日K','量'], '日K'}` —— 对象里别混入游离裸值

## 1. ECharts option 骨架（填 data，别从零手敲嵌套）

复杂图（一页多图、雷达多 series、双轴、K 线）是括号失配重灾区。**优先套用下面骨架，只替换 data / 标签，不要从空白手写整个嵌套结构。** 套骨架能把失配率压到接近 0。

引库（CDN 引入，放 `<head>`）：
```html
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
```

柱 / 折线（含双轴）：
```javascript
echarts.init(document.getElementById('chart1')).setOption({
  tooltip: { trigger: 'axis' },
  legend: { data: ['营收', '净利'] },
  xAxis: { type: 'category', data: ['2023', '2024', '2025'] },
  yAxis: [
    { type: 'value', name: '营收(亿)' },
    { type: 'value', name: '净利(亿)' }          // 量级差大时用第二根轴
  ],
  series: [
    { name: '营收', type: 'bar',  data: [100, 120, 150] },
    { name: '净利', type: 'line', yAxisIndex: 1, data: [10, 14, 20] }
  ]
});
```

饼 / 占比：
```javascript
echarts.init(document.getElementById('chart2')).setOption({
  tooltip: { trigger: 'item', formatter: '{b}: {d}%' },
  series: [{
    type: 'pie', radius: ['40%', '70%'],
    data: [
      { name: '主业', value: 60 },
      { name: '副业', value: 40 }
    ]
  }]
});
```

雷达（多 series 注意每个对象单独闭合）：
```javascript
echarts.init(document.getElementById('chart3')).setOption({
  legend: { data: ['公司A', '公司B'] },
  radar: { indicator: [
    { name: '盈利', max: 5 }, { name: '成长', max: 5 }, { name: '估值', max: 5 }
  ]},
  series: [{
    type: 'radar',
    data: [
      { name: '公司A', value: [4.5, 3.5, 3.0] },
      { name: '公司B', value: [4.0, 2.0, 4.5] }
    ]
  }]
});
```

K 线：
```javascript
echarts.init(document.getElementById('kline')).setOption({
  tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
  legend: { data: ['日K', '成交量'] },          // legend.data 只放名字数组，别混入裸字符串
  xAxis: { type: 'category', data: dates },
  yAxis: [{ scale: true }, { scale: true }],
  series: [
    { name: '日K', type: 'candlestick', data: ohlc },                 // ohlc: [[open,close,low,high],...]
    { name: '成交量', type: 'bar', yAxisIndex: 1, data: vols }
  ]
});
```

每个图容器：`<div id="chart1" style="width:100%;height:360px;"></div>`。多图时 id 别重名。

## 2. 整体风格

- **浅底深字的研报风**，避免暗色仪表盘风或开篇大段文字。
- **首屏结论先行**：放 TL;DR / 结论卡 / 关键数字模块，先给判断再展开论证。
- A 股语境用红涨绿跌。

## 3. 图表分工

- 趋势 / 对比 / 占比 / 分布等**有数值轴的数据图用 ECharts**，别堆一长串趋势型表格。
- 产业链图谱 / 传导链 / 股权结构等**关系拓扑图用 SVG 或 HTML+CSS 盒子**（规整结构用 CSS 盒子、复杂拓扑用 SVG，自行判断）。SVG/CSS 不依赖 JS，天然规避括号失配。
- 查阅 / 多维对照型数据仍用表格。

## 4. 图表质量细则

- **图表可切换**：数字密集的趋势数据块做成"图 / 表可切换"（默认看图看趋势，一键切表查精确值），别让图取代了精确数字——机构网页通行做法。
- **取数多取一个完整周期消除空值**：做同比 / 环比趋势图前，优先让数据源多取一年（如算 8 个季度同比就取 12 个季度），让 model 不必自己算同比且图上不出现前段空值；数据源确实受限时，以信息完整为先，宁可有少数空点也要把能展示的信息展全。
- **双轴注意量级差**：同一图里量级差很大的两个序列（如营收数千亿 vs 净利数百亿）不要共用一根轴（小的会被压成贴地条），用双轴或把小序列改折线。
- **空值不入图**：某段完全没有数据的区间（如缺同比基数的早期季度）不要硬塞进图占位，让 x 轴从有数据处起，或改用该段本就有值的绝对值口径。
