# Web/PC Sunburst 参考

## 目录

- [适用范围](#适用范围)
- [可复用要点](#可复用要点)
- [改写约束](#改写约束)
- [参考 option](#参考-option)

## 适用范围

仅在 system prompt 的 `Device platform` 明确为“电脑端”或“网页端”，且已经选择原生 ECharts `sunburst` 时读取本文件。先遵循 `echarts-web-pc-spec.md`，再把本文件作为约 `986×420` 扁平内联画布的正向参考。

本例展示“根节点 → 季节 → 节日 → 习俗”的四层结构。数据仅用于演示布局，不作为节日分类、日期或习俗的权威事实来源；生成真实内容时仍需依据用户材料或核验结果。

## 可复用要点

- 用 `title.top: 12`、`series.center: ['50%', 238]`、`radius: [0, 162]` 分开表头和圆环；圆环顶部约 `76px`、底部约 `400px`，适合带一行副标题的 420px 高画布。
- 副标题只解释阅读方法与交互，不塞入来源长文；放不下时移除图内副标题并将说明放到代码块外 Markdown。
- 使用一个显式根节点形成稳定中心；ECharts 还会创建不可见的虚拟根，因此 `levels[0]` 留空，四个可见数据层从 `levels[1]` 开始配置。
- 先计算数据最大深度，再逐层配置 `levels`；本例必须有五项：`levels[0]` 虚拟根、`levels[1]` 数据根、`levels[2]` 季节、`levels[3]` 节日、`levels[4]` 习俗。最深叶层也必须显式配置，不能回退到全局默认 label。
- 使用合法的 `nodeClick: 'rootToNode'` 下钻；保留 click，不能只依赖 hover。
- tooltip 用 `treePathInfo` 展示路径，并仅在存在时补充日期；callback 保持 ES5、判空和纯文本输出。
- 不删除数据节点来避免重叠。外圈使用短名、`label.minAngle` 与 `labelLayout.hideOverlap` 控制首屏标签，完整路径继续通过 tooltip 和下钻查看。
- 高密度最外层叶标签可使用 `9–10px`；`9px` 仅是 Sunburst 外圈短标签的例外，并应把文字描边控制在 `1px` 以内，避免小字因粗描边显得过大、相互挤压。内层标签和其他图表不得套用该例外。
- 各层根据环宽和扇区角度选择 `rotate: 0`、`'radial'` 或 `'tangential'`；不要机械复制旋转方式。所有可见文字必须完全位于自己的扇区内且不互相覆盖。
- 叶节点统一 `value: 1` 时，父扇区角度表示“本图列出的叶节点数量”，不表示文化重要性。若面积没有业务含义，应在图外说明口径，或为各父节点设计不误导的权重。

## 改写约束

- 直接输出 `{ ... }`，不得添加 `option =`。
- 不使用 `zoomToNode`；Sunburst 下钻使用 `rootToNode`。
- 不使用无效的 `colorMappingBy: 'fixed'` 或 `'linear'`；优先通过父节点 `itemStyle.color`、调色板或合法的 `colorBy` 控制颜色。
- 不把 `238`、`162` 当作所有 Sunburst 的固定答案。标题行数、环层数、外圈标签和最终容器宽度变化后，重新校验完整圆环包围盒。
- 不漏配任何可见数据层的 `levels[n].label`。每层分别根据环宽和扇区角度设置字号、旋转和溢出策略；所有显示文字必须完整落在自己的扇区内。
- 不限制数据节点数量来换取整洁。空间不足时先减少可见 label、缩短显示名、调整旋转和环宽，再使用 tooltip/下钻；不得擅自删掉用户数据。
- 外圈已经使用 `9px` 后仍然拥挤时，不得继续缩小字号；应提高 `label.minAngle`、使用 `labelLayout.hideOverlap` 隐藏次要首屏标签，并通过 tooltip 与下钻提供完整名称。
- 输出前检查初始状态、任一一级节点下钻状态和返回根节点状态；标题、副标题、中心文字、各层 label 与画布边界均不得重叠或裁切。

## 参考 option

```echarts
{
  backgroundColor: 'transparent',
  title: {
    text: '中国传统节日分类（按季节）',
    subtext: '由内向外：季节 → 节日 → 主要习俗；点击扇区可下钻，点击中心返回',
    top: 12,
    left: 'center',
    textStyle: { color: '#1A1B1C', fontSize: 16, fontWeight: 600 },
    subtextStyle: { color: '#6B7280', fontSize: 11 }
  },
  tooltip: {
    trigger: 'item',
    triggerOn: 'mousemove|click',
    renderMode: 'richText',
    confine: true,
    textStyle: { fontSize: 11, lineHeight: 16 },
    padding: [6, 8],
    formatter: function (params) {
      var info = params && params.treePathInfo ? params.treePathInfo : [];
      var names = [];
      for (var i = 1; i < info.length; i++) {
        if (info[i] && info[i].name) {
          names.push(info[i].name);
        }
      }
      var s = names.join(' › ');
      var d = params && params.data ? params.data : {};
      if (d.date) {
        s += String.fromCharCode(10) + d.date;
      }
      return s;
    }
  },
  series: [
    {
      name: '传统节日',
      type: 'sunburst',
      center: ['50%', 238],
      radius: [0, 162],
      sort: null,
      nodeClick: 'rootToNode',
      emphasis: { focus: 'ancestor' },
      label: {
        color: '#2B2F33',
        textBorderColor: 'rgba(255,255,255,0.6)',
        textBorderWidth: 2
      },
      levels: [
        {},
        {
          label: {
            rotate: 0,
            fontSize: 12,
            fontWeight: 'bold',
            color: '#5B4D2E',
            width: 66,
            overflow: 'truncate',
            formatter: '传统节日'
          },
          itemStyle: { borderWidth: 0 }
        },
        {
          label: {
            rotate: 0,
            fontSize: 13,
            fontWeight: 'bold',
            width: 34,
            overflow: 'truncate'
          },
          itemStyle: { borderWidth: 3, borderColor: '#ffffff' }
        },
        {
          label: {
            rotate: 'tangential',
            fontSize: 11,
            width: 42,
            overflow: 'truncate'
          },
          itemStyle: { borderWidth: 2, borderColor: '#ffffff' }
        },
        {
          label: {
            rotate: 'radial',
            fontSize: 9,
            minAngle: 6,
            width: 38,
            overflow: 'truncate',
            ellipsis: '…',
            textBorderWidth: 1
          },
          itemStyle: { borderWidth: 1, borderColor: '#ffffff', opacity: 0.92 }
        }
      ],
      labelLayout: { hideOverlap: true },
      data: [
        {
          name: '中国传统节日',
          itemStyle: { color: '#F6F2E7' },
          children: [
            {
              name: '春季',
              itemStyle: { color: '#6FB58C' },
              children: [
                {
                  name: '春节',
                  date: '农历正月初一',
                  children: [
                    { name: '贴春联', value: 1 },
                    { name: '拜年', value: 1 },
                    { name: '放爆竹', value: 1 },
                    { name: '压岁钱', value: 1 }
                  ]
                },
                {
                  name: '元宵节',
                  date: '农历正月十五',
                  children: [
                    { name: '吃元宵', value: 1 },
                    { name: '赏花灯', value: 1 },
                    { name: '猜灯谜', value: 1 },
                    { name: '舞龙狮', value: 1 }
                  ]
                },
                {
                  name: '清明节',
                  date: '公历4月5日前后',
                  children: [
                    { name: '扫墓祭祖', value: 1 },
                    { name: '踏青', value: 1 },
                    { name: '插柳', value: 1 }
                  ]
                }
              ]
            },
            {
              name: '夏季',
              itemStyle: { color: '#E39A5B' },
              children: [
                {
                  name: '端午节',
                  date: '农历五月初五',
                  children: [
                    { name: '吃粽子', value: 1 },
                    { name: '赛龙舟', value: 1 },
                    { name: '挂艾草', value: 1 },
                    { name: '佩香囊', value: 1 },
                    { name: '五彩绳', value: 1 }
                  ]
                }
              ]
            },
            {
              name: '秋季',
              itemStyle: { color: '#D4AC5E' },
              children: [
                {
                  name: '七夕节',
                  date: '农历七月初七',
                  children: [
                    { name: '穿针乞巧', value: 1 },
                    { name: '拜织女', value: 1 },
                    { name: '吃巧果', value: 1 }
                  ]
                },
                {
                  name: '中秋节',
                  date: '农历八月十五',
                  children: [
                    { name: '赏月', value: 1 },
                    { name: '吃月饼', value: 1 },
                    { name: '团圆饭', value: 1 },
                    { name: '赏桂花', value: 1 }
                  ]
                },
                {
                  name: '重阳节',
                  date: '农历九月初九',
                  children: [
                    { name: '登高', value: 1 },
                    { name: '赏菊', value: 1 },
                    { name: '插茱萸', value: 1 },
                    { name: '敬老', value: 1 }
                  ]
                }
              ]
            },
            {
              name: '冬季',
              itemStyle: { color: '#6E9CC4' },
              children: [
                {
                  name: '腊八节',
                  date: '农历腊月初八',
                  children: [
                    { name: '腊八粥', value: 1 },
                    { name: '腊八蒜', value: 1 }
                  ]
                },
                {
                  name: '小年',
                  date: '农历腊月廿三/廿四',
                  children: [
                    { name: '祭灶神', value: 1 },
                    { name: '扫尘', value: 1 }
                  ]
                },
                {
                  name: '除夕',
                  date: '农历腊月廿九/三十',
                  children: [
                    { name: '年夜饭', value: 1 },
                    { name: '守岁', value: 1 },
                    { name: '贴福字', value: 1 }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```
