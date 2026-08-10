# ECharts、交互演示与几何证明规则

## 目录

- [九、ECharts 专项规范](#九echarts-专项规范)
- [十、交互式教育演示](#十交互式教育演示)
- [十一、几何证明专项](#十一几何证明专项)

## 九、ECharts 专项规范

在§七通用约束基础上，ECharts 额外要求：

1. 字符串 `+` 拼接确保完整，以 `;` 结尾，禁止截断。
2. 多系列 tooltip 用循环 `for (var i = 0; i < params.length; i++)` 处理。
3. 响应式：`window.addEventListener('resize', function(){ myChart.resize(); });`
4. 浅色适配：`backgroundColor: 'transparent'`；轴标签 `color: '#555'`；tooltip 背景 `rgba(255,255,255,0.95)` + 深色文字。
5. 字号：标题 15px/600、轴标签与图例 11px、数据标签 10px、提示框 11px。
6. **防文本重叠机制（强制）**：针对 scatter、graph、timeline 等密集标签场景，**可读性优先于信息完整性，禁止任何文本覆盖**：
   - **基础防叠**：强制启用 `labelLayout: { hideOverlap: true }` 或 `moveOverlap: 'shiftY/X'`。
   - **直线交错**：同一直线节点必须动态回调排布（如 `position: function(p){ return p.dataIndex % 2 === 0 ? 'top' : 'bottom'; }`）。
   - **长文本换行**：必须配置 `width`、`overflow: 'break'` 与 `lineHeight`。
   - **高密度降级**：节点 >8 个或均长 >8 字符时，禁止默认全显，须改用 tooltip 替代、emphasis 触发、局部隐藏或增加画布高度。
   - **时间轴特化**：当时间轴包含大量密集节点或长文本描述时，优先推荐放弃 ECharts 的 timeline 组件，**改用纯 HTML/CSS 结合 Flex 布局实现的垂直时间线卡片结构**（如左侧轴线圆点，右侧信息卡片），这样能获得最佳的自适应与防重叠体验。若必须使用 ECharts，则必须放弃自带 timeline 组件，改用普通的 category Y轴 + Scatter 散点图来实现等距时间线。
7. **防提示框溢出（Tooltip 防截断）**：对于包含长文本、多层级路径（如 Tree/Treemap）或复杂指标的 Tooltip，**强制配置** `confine: true`（限制在画布内），并建议通过 `extraCssText: 'white-space: normal; word-break: break-all; max-width: 300px;'` 允许文本自动换行，禁止因超长单行文本导致提示框超出屏幕或被截断。
8. **响应式自适应防挤压（强制）**：在使用 Flex 或 Grid 布局包裹 ECharts 容器时，**必须**在 ECharts 的直接父元素上添加 `min-width: 0` 或 `overflow: hidden`，以打破 Flex/Grid 的默认最小宽度限制，否则会导致图表在窗口缩放时被卡死无法缩小。图表容器必须设置明确的固定高度（如 `height: 280px`），严禁使用 `calc(100% - xx)` 等依赖父级动态高度的相对单位。
9. **轴标签防溢出（grid 强制配置）**：必须配置 `grid: { left, right, top, bottom, containLabel: true }`，让轴标签和单位自动纳入绘图区计算，防止长标签被画布边界裁剪。
10. **数值精度处理（强制）**：在计算坐标轴 `min/max`、tooltip、百分比、增长率、均值等涉及浮点数运算时，必须使用 `.toFixed()`、`Math.round()`、`parseFloat()` 或 `Intl.NumberFormat` 控制精度，禁止出现 `0.30000000004` 等异常展示。
11. **单位自适应与大数格式化（强制）**：绝对禁止在 axisLabel、tooltip、label 或任何文本中直接展示不符合常理的极端大数或极小单位（例如：猫咪体重展示为 `50000000000g`）。
    - 必须根据具体生活常识和数值量级，自动换算为最适合人类直观阅读的高阶单位（如 kg、吨、万、亿、万元、亿元、%、‰ 等）。
    - 大数应使用 `.toLocaleString()`、`Intl.NumberFormat` 或自定义格式化函数增加千分位/紧凑表达。
    - **tooltip 与 axisLabel 的单位口径必须一致**；若图表单位经过换算，应在图表附近说明原始单位和换算方式。
12. **地图组件禁止**：禁止使用 ECharts `geo`、`map`、地图注册数据、行政区划数据或任何地图渲染相关能力。

**安全模板**：

当任务是趋势/波动/占比/多指标对比时，优先用该模板快速交付；金融、医疗、公共数据等场景必须在图表附近说明数据来源、统计口径和更新时间，不能把推测当事实。

```html type="renderer"
<html style="margin:0;padding:0;">
<div style="background-color:transparent;box-sizing:border-box;">
  <div id="chart" style="width:100%;height:280px;min-width:0;box-sizing:border-box;"></div>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
  <script>
  (function() {
    try {
      var chartDom = document.getElementById('chart');
      if (!chartDom) return;
      if (typeof echarts === 'undefined') {
        chartDom.innerHTML = '<div style="padding:12px;color:#6B7280;font-size:13px;">图表库加载失败，已回退为文本说明。</div>';
        return;
      }
      var myChart = echarts.init(chartDom);
      var data = [32, 35, 38, 42];
      function fmt(v) {
        return parseFloat(Number(v).toFixed(1)).toLocaleString();
      }
      myChart.setOption({
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'axis',
          confine: true,
          backgroundColor: 'rgba(255,255,255,0.95)',
          borderColor: '#E4E3DD',
          textStyle: { color: '#333', fontSize: 11 },
          extraCssText: 'white-space:normal;word-break:break-all;max-width:300px;',
          formatter: function(params) {
            var r = params[0].axisValue + '<br/>';
            for (var i = 0; i < params.length; i++) {
              r += params[i].marker + params[i].seriesName + ': ' + fmt(params[i].value) + '<br/>';
            }
            return r;
          }
        },
        grid: { left: 36, right: 18, top: 24, bottom: 30, containLabel: true },
        xAxis: { type: 'category', data: ['Q1','Q2','Q3','Q4'], axisLabel: { color: '#555', fontSize: 11 } },
        yAxis: {
          type: 'value',
          axisLabel: { color: '#555', fontSize: 11, formatter: function(v) { return fmt(v); } },
          min: function(value) { return parseFloat((Math.floor(value.min) - 10).toFixed(1)); },
          max: function(value) { return parseFloat((Math.ceil(value.max) + 10).toFixed(1)); }
        },
        series: [{
          name: '系列1',
          type: 'line',
          data: data,
          smooth: true,
          itemStyle: { color: '#9EACEA' },
          lineStyle: { color: '#9EACEA', width: 2 },
          labelLayout: { hideOverlap: true }
        }]
      });
      window.addEventListener('resize', function() { myChart.resize(); });
    } catch (e) {
      console.error('ECharts error:', e);
    }
  })();
  </script>
</div>
</html>
```

---

## 十、交互式教育演示

### 核心原则

- **响应性**：操作即时引发视觉变化，因果关系直接可感。
- **色彩语义**：颜色区分变量/区域/状态。
- **实时反馈**：关键数值随交互同步更新。
- **控件克制**：控件数量尽量少，优先使用滑块、按钮、切换器，避免多控件叠加导致认知负担。
- **不遮挡核心**：控件不应覆盖核心信息区域，不得超出容器边界；必要时上下堆叠而非左右挤压。
- **可暂停可重置**：动画/动态演示必须可暂停、可重置，避免持续高频刷新拖累性能。

### 交互形态清单

| 形态 | 适用场景 | 实现方式 | 关键要求 |
|------|---------|---------|---------|
| ① 连续滑块 | 角度/频率/概率等连续参数 | `<input type="range">` | 显示当前值和单位 |
| ② 拖拽锚点 | 几何变换、函数变形、力向量 | SVG/Canvas pointer events | 给出边界和初始状态 |
| ③ 步进/时间线 | 算法执行、证明步骤 | "下一步"/"播放"按钮 | 提供重置按钮 |
| ④ 动画循环 | 物理模拟、粒子、生命游戏 | `requestAnimationFrame` + 暂停/继续 | 必须可暂停可重置 |
| ⑤ 点击/悬停揭示 | 分层解释、区域注释、热力图 | click/hover 事件 | 不依赖 hover 才能理解主结论 |
| ⑥ 下拉/切换 | 对比多种分布/算法/电路 | `<select>` 或按钮组 | 说明当前模式含义 |
| ⑦ 输入框计算 | 精确值计算（利率/矩阵/进制） | oninput 即时重算 | 输入校验与单位提示 |
| ⑧ 画布手绘 | 手写识别、贝塞尔、逼近拟合 | Canvas 绘制 | 提供清空按钮 |
| ⑨ 分屏对比 | 时域↔频域、加密前↔后 | 双视图联动 | 联动方向明确 |
| ⑩ 网格交互 | DP表、卷积核、自动机 | 单元格 click/hover | 高亮当前/相关单元格 |

可自由组合，选最适合当前概念的形式。

---

## 十一、几何证明专项

> 仅在触发条件 #6（几何构造与证明）命中时启用。

**输出顺序**：题意重述 → 已知/求证 → 构造步骤 → 证明主链 → 结论回收。

**过程规范**：
- 每步必须标注依据（定理名称），禁止只给结论。
- 可视化仅作辅助验证层，图中标记与文字变量一一对应。
- 优先用"可拖拽锚点 + 实时数值"验证不变量。
- 默认提供"易错点检查"小结。

**视觉准确性（强制）**：
- 几何关系必须准确：垂直、平行、相切、角平分、中点、共线、共圆等关系必须和题设完全一致，不能视觉上"差一点"。
- 标注必须防重叠：点名、角度、边长、辅助线说明不可遮挡关键结构。
- 若使用交互拖拽，必须保持题设约束；不能拖出后破坏几何条件。
- 若无法用脚本稳定保持几何约束，改用静态 SVG 示意图。
- 证明文本与图示一一对应，**不得让图示暗示未证明的结论**。

---
