# Web/PC Gauge 参考

## 目录

- [适用范围](#适用范围)
- [可复用要点](#可复用要点)
- [刻度文字几何](#刻度文字几何)
- [改写约束](#改写约束)
- [参考 option](#参考-option)

## 适用范围

仅在 system prompt 的 `Device platform` 明确为“电脑端”或“网页端”，且已经选择原生 ECharts `gauge` 时读取本文件。先遵循 `echarts-web-pc-spec.md`，再把本文件作为约 `986×420` 扁平内联画布中单指标完成率仪表盘的正向参考。

## 可复用要点

- 用 `title.top: 12` 和 `series.center: ['50%', 258]` 分离表头与完整表盘外接范围；不能只避开圆弧，还要避开顶部刻度文字。
- 单指标完成率使用进度弧与中央 `detail` 已足够表达数值，默认隐藏 `pointer` 与 `anchor`，避免穿过中央文字。
- `progress.width` 与 `axisLine.lineStyle.width` 保持一致，使进度弧和背景弧形成一条稳定轨道。
- `axisTick.show: false` 时仅保留主要分隔线和刻度文字，降低视觉噪声。
- `detail` 显示主数值，series `title` 显示简短状态名；两者必须位于进度弧内侧空白区且互不覆盖。
- tooltip 说明当前值与距目标差值；formatter 保持 ES5、判空和纯文本输出。

## 刻度文字几何

ECharts Gauge 的刻度文字锚点沿半径方向位于：

```text
labelRadius = radius - splitLine.length - axisLabel.distance - splitLine.distance
```

本例中：

```text
圆弧内边缘 = 158 - 16 = 142
文字锚点半径 = 158 - 8 - 20 - 0 = 130
```

文字锚点位于圆弧内边缘以内约 12px，给 11px 字体留下清晰间隔。该计算只用于解释本例，不能把 `axisLabel.distance: 20` 当成所有 Gauge 的固定答案；更改半径、弧宽、字体、刻度长度或角度后必须重新检查文字包围盒。

## 改写约束

- 直接输出 `{ ... }`，不得添加 `option =`。
- 不把 `center: ['50%', 258]`、`radius: 158` 或 `axisLabel.distance: 20` 机械复制到其他画布。
- 任一 `axisLabel` 的完整包围盒不得与进度弧、背景弧、分隔线、指针、锚点、中央 detail 或标题相交；必须检查顶部、两端以及 `0 / 50 / 100`。
- 若调整 `splitNumber`、`axisLine.lineStyle.width` 或 `splitLine.length`，必须重新计算并视觉检查 `axisLabel.distance`；不能只改一个数字便假设安全。
- 空间不足时依次调整 label 位置、减少 `splitNumber`、缩短 formatter、减小弧宽或调整 `center/radius`，不得把文字叠在弧带上或缩小到不可读。
- 有指针时不能照抄本例的 detail 位置；必须检查最小值、最大值、当前值和常见中间值下指针均不穿过文字。

## 参考 option

```echarts
{
  backgroundColor: 'transparent',
  title: {
    text: '本周阅读目标完成率',
    subtext: '目标满值 100%，当前已完成 68%',
    left: 'center',
    top: 12,
    itemGap: 6,
    textStyle: { color: '#1A1B1C', fontSize: 15, fontWeight: 600 },
    subtextStyle: { color: '#6B7280', fontSize: 11 }
  },
  tooltip: {
    trigger: 'item',
    triggerOn: 'mousemove|click',
    renderMode: 'richText',
    confine: true,
    textStyle: { fontSize: 11, lineHeight: 15 },
    padding: [6, 8],
    formatter: function (params) {
      if (!params) {
        return '';
      }
      return '本周阅读目标'
        + String.fromCharCode(10)
        + '已完成：' + params.value + '%'
        + String.fromCharCode(10)
        + '距目标还差：' + (100 - params.value) + '%';
    }
  },
  series: [
    {
      name: '阅读完成率',
      type: 'gauge',
      center: ['50%', 258],
      radius: 158,
      startAngle: 210,
      endAngle: -30,
      min: 0,
      max: 100,
      splitNumber: 10,
      progress: {
        show: true,
        width: 16,
        roundCap: true,
        itemStyle: { color: '#4E9CB5' }
      },
      axisLine: {
        roundCap: true,
        lineStyle: { width: 16, color: [[1, '#EDF1F5']] }
      },
      pointer: { show: false },
      anchor: { show: false },
      axisTick: { show: false },
      splitLine: {
        length: 8,
        distance: 0,
        lineStyle: { color: '#FFFFFF', width: 2 }
      },
      axisLabel: {
        distance: 20,
        color: '#8A919B',
        fontSize: 11
      },
      title: {
        show: true,
        offsetCenter: [0, '34%'],
        color: '#8A919B',
        fontSize: 12
      },
      detail: {
        valueAnimation: true,
        offsetCenter: [0, '-6%'],
        fontSize: 36,
        fontWeight: 600,
        color: '#1A1B1C',
        formatter: '{value}%'
      },
      data: [{ value: 68, name: '已完成' }]
    }
  ]
}
```
