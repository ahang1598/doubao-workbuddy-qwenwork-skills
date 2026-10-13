# ECharts 配置模板

SKILL.md 规定可视化**只允许用 ECharts**（唯一被 `--validate-html` 全面
校验的库）。这份文件给一些常见图表类型的最小可工作 option 片段，省去
查 API 的时间。

> **画什么图（柱/线/饼/双轴...）由你（模型）自己判断**——本文不做图表选型
> 建议，只给"假设你选了 X 图，对应的 ECharts option 大致长这样"的代码参考。

---

## 折线图（趋势）
```javascript
{
  tooltip: { trigger: 'axis' },
  legend: { bottom: 0 },
  grid: { left: '3%', right: '4%', bottom: '12%', containLabel: true },
  xAxis: { type: 'category', data: ['1月','2月','3月'] },
  yAxis: { type: 'value', name: '<度量名>' },
  series: [{
    name: '<系列名>', type: 'line', smooth: true,
    data: [820, 932, 901],
    itemStyle: { color: '#667eea' },
    areaStyle: { color: 'rgba(102,126,234,0.1)' }
  }]
}
```

## 柱状图（分类对比）
```javascript
{
  tooltip: { trigger: 'axis' },
  grid: { left: '3%', right: '4%', bottom: '8%', containLabel: true },
  xAxis: { type: 'category', data: ['<类别1>','<类别2>','<类别3>'] },
  yAxis: { type: 'value', name: '<度量名>' },
  series: [{
    type: 'bar', data: [1523, 1089, 876],
    barWidth: '50%',
    label: { show: true, position: 'top' }
  }]
}
```

## 饼图 / 环形图（占比）
```javascript
{
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  legend: { bottom: 0, type: 'scroll' },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],   // 环形图；改 ['0%', '70%'] 为实心
    center: ['50%', '45%'],
    data: [
      { value: 1523, name: '<类别1>' },
      { value: 1089, name: '<类别2>' },
      { value: 876,  name: '<类别3>' }
    ]
  }]
}
```

## 双轴组合图（量 + 率）
```javascript
{
  tooltip: { trigger: 'axis' },
  legend: { bottom: 0 },
  xAxis: { type: 'category', data: ['Q1','Q2','Q3','Q4'] },
  yAxis: [
    { type: 'value', name: '<左轴度量>', position: 'left' },
    { type: 'value', name: '<右轴度量>', position: 'right',
      axisLabel: { formatter: '{value}%' } }
  ],
  series: [
    { name: '<左轴系列>', type: 'bar',  yAxisIndex: 0, data: [2300, 2800, 3100, 3500] },
    { name: '<右轴系列>', type: 'line', yAxisIndex: 1, data: [12, 21.7, 10.7, 12.9] }
  ]
}
```

## 横向条形图（Top N）
```javascript
{
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: '20%', right: '8%', bottom: '4%', containLabel: true },
  xAxis: { type: 'value' },
  yAxis: { type: 'category', data: ['E','D','C','B','A'], inverse: true },
  series: [{
    type: 'bar', data: [234, 456, 678, 890, 1234],
    label: { show: true, position: 'right' }
  }]
}
```

---

**使用提示**：直接把上面任一片段嵌入 HTML：

```html
<div id="chart1" style="width:100%; height:400px;"></div>
<script src="https://registry.npmmirror.com/echarts/5.5.0/files/dist/echarts.min.js"></script>
<script>
  const opt = { /* 上面任一 option */ };
  echarts.init(document.getElementById('chart1')).setOption(opt);
</script>
```

## ⚠️ ECharts CDN 选择（在中国使用注意）

**默认用国内 CDN**（在中国可稳定加载）— **优先用 npmmirror (淘宝官方镜像, 最稳定)**:

```html
<script src="https://registry.npmmirror.com/echarts/5.5.0/files/dist/echarts.min.js"></script>
```

| CDN 白名单（任选一个，validate-html 校验需在此白名单内） | 说明 |
|---|---|
| `registry.npmmirror.com/echarts/5.5.0/files/dist/echarts.min.js` ⭐ | **淘宝 npm 镜像 (最稳定, 默认用这个)** |
| `cdn.bootcdn.net/ajax/libs/echarts/5.5.0/echarts.min.js` | BootCDN（国内备选） |
| `lib.baomitu.com/echarts/5.5.0/echarts.min.js` | 360 baomitu（国内备选） |
| `echarts.apache.org/zh/dist/echarts.min.js` | Apache 官方 |

**慎用 / 避免**（在中国不稳定，用户可能加载失败看到白图）:

| ❌ 慎用 CDN | 风险 |
|---|---|
| `cdn.jsdelivr.net/npm/echarts/...` | 国内时段性不可用，用户高概率白屏 |
| `unpkg.com/echarts/...` | 同上 |
| `cdnjs.cloudflare.com/ajax/libs/echarts/...` | Cloudflare 节点国内偶发不稳 |

**验证**: `html_report.py --validate-html` 的 `echarts` 检查只允许白名单内的 CDN，用非白名单 CDN 直接报错.

## validate-html 会校验
- `<script src=...>` 在 `echarts.init(...)` 之前
- `init(document.getElementById('chart1'))` 的 `'chart1'` 在 HTML 中确实存在
- option 中数据值不能含裸 `NaN` / `Infinity`（用 `null` 或具体数字代替）
- 使用的 CDN 在白名单内（**不在白名单的非合法 CDN 报错**）
