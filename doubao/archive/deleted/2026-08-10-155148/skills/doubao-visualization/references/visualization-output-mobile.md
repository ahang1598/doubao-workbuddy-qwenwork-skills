# 输出结构示例与移动端适配规则

## 目录

- [十二、输出结构示例](#十二输出结构示例)
- [十三、移动端适配](#十三移动端适配)

## 十二、输出结构示例

Markdown 文本与 HTML 可视化模块交替：

> 这是常规 Markdown 文本，解释或补充信息。以下展示 2024 年各季度收入趋势（示例数据，仅用于展示结构）：

```html type="renderer"
<html style="margin:0;padding:0;">
<div style="background-color:transparent;box-sizing:border-box;">
  <div id="revenue-chart" style="width:100%;height:280px;min-width:0;box-sizing:border-box;"></div>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
  <script>
  (function() {
    try {
      var c = document.getElementById('revenue-chart');
      if (!c) return;
      if (typeof echarts === 'undefined') {
        c.innerHTML = '<div style="padding:12px;color:#6B7280;font-size:13px;">图表库加载失败，已回退为文本说明。</div>';
        return;
      }
      var m = echarts.init(c);
      function fmt(v) { return parseFloat(Number(v).toFixed(1)).toLocaleString(); }
      m.setOption({
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'axis',
          confine: true,
          backgroundColor: 'rgba(255,255,255,0.95)',
          textStyle: { color: '#333', fontSize: 11 },
          formatter: function(params) {
            var r = params[0].axisValue + '<br/>';
            for (var i = 0; i < params.length; i++) {
              r += params[i].marker + params[i].seriesName + ': ' + fmt(params[i].value) + ' 万元<br/>';
            }
            return r;
          }
        },
        grid: { left: 40, right: 18, top: 24, bottom: 30, containLabel: true },
        xAxis: { type: 'category', data: ['Q1','Q2','Q3','Q4'], axisLabel: { color: '#555', fontSize: 11 } },
        yAxis: { type: 'value', name: '收入（万元）', axisLabel: { color: '#555', fontSize: 11, formatter: function(v){ return fmt(v); } } },
        series: [{
          type: 'bar',
          data: [320,410,380,520],
          itemStyle: { color: '#8BC8EA', borderRadius: [6,6,0,0] },
          label: { show: true, position: 'top', fontSize: 10, color: '#555', formatter: function(p){ return fmt(p.value); } },
          labelLayout: { hideOverlap: true }
        }]
      });
      window.addEventListener('resize', function() { m.resize(); });
    } catch (e) { console.error(e); }
  })();
  </script>
</div>
</html>
```

> Q4 收入达 520 万元，环比增长 36.8%，全年最高。数据口径：示例数据，仅用于展示结构，不代表真实业务结果。

```html type="renderer"
<html style="margin:0;padding:0;">
<div style="background-color:transparent;box-sizing:border-box;">
  <div style="padding:12px;display:flex;gap:16px;flex-wrap:wrap;box-sizing:border-box;">

    <!-- 卡片1 -->
    <div style="flex:1 1 120px;min-width:0;padding:12px;
                background:linear-gradient(135deg, rgba(139,200,234,0.15), rgba(139,200,234,0.3));
                border-radius:12px;box-sizing:border-box;">
      <div style="font-size:12px;color:#6B7280;">全年总收入</div>
      <div style="font-size:20px;font-weight:600;color:#1A1B1C;margin-top:4px;">
        1,630 <span style="font-size:12px;color:#6B7280;font-weight:400;">万元</span>
      </div>
    </div>

    <!-- 卡片2 -->
    <div style="flex:1 1 120px;min-width:0;padding:12px;
                background:linear-gradient(135deg, rgba(139,200,234,0.15), rgba(139,200,234,0.3));
                border-radius:12px;box-sizing:border-box;">
      <div style="font-size:12px;color:#6B7280;">平均季度</div>
      <div style="font-size:20px;font-weight:600;color:#1A1B1C;margin-top:4px;">
        407.5 <span style="font-size:12px;color:#6B7280;font-weight:400;">万元</span>
      </div>
    </div>

    <!-- 卡片3 -->
    <div style="flex:1 1 120px;min-width:0;padding:12px;
                background:linear-gradient(135deg, rgba(82,196,26,0.1), rgba(82,196,26,0.2));
                border-radius:12px;box-sizing:border-box;">
      <div style="font-size:12px;color:#6B7280;">最高增长率</div>
      <div style="font-size:20px;font-weight:600;color:#52C41A;margin-top:4px;">
        +36.8%
      </div>
    </div>

  </div>
</div>
</html>
```
---
## 十三、移动端适配

- **响应式布局**：容器 `width:100%; box-sizing:border-box;`，内部元素用相对单位，图片/SVG 设 `max-width:100%; height:auto;`。
- **禁止固定列数**：**严禁写死固定列数**（如 `grid-template-columns: 1fr 1fr` 或 `repeat(5, 1fr)`），优先单列垂直流式。
- **多列自适应**：多列布局必须使用 Flex 加 `flex-wrap: wrap` 配合子元素 `flex: 1 1 {基础宽度}px`，或使用 Grid 加 `grid-template-columns: repeat(auto-fit, minmax({基础宽度}px, 1fr))`，确保在窄屏下能自动换行。
- **触控友好**：交互元素点击区域不小于 `44×44px`（对齐 iOS HIG / Material Design 标准），避免依赖 hover，改用 tap 触发。
- **文本可读**：移动端正文不低于 14px，图表轴标签不低于 12px。
- **内容密度**：移动端优先展示核心数据，复杂图表拆分或提供滚动，列表默认折叠。
- **内容可见性**：交互时不影响/不覆盖信息展示的核心区域，确保重点信息始终可见；交互元素不能超出可见范围（容器内），必要时上下堆叠而非左右挤压。
- **垂直优先**：图表标题、图例、控件置于上方/下方而非侧边。
- **性能约束**：移动端避免大规模粒子、复杂 3D、持续高频动画；控制 SVG 复杂度，优先 SVG/Canvas 简化实现，考虑设备性能和网络条件。
