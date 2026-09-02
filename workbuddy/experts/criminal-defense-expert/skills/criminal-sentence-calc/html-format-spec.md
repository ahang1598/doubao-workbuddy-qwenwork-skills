# HTML 排版规范

> format_seriousness: I-Practical
> 视觉方案: C 现代轻量
> 引用体系: base/rule/format-html/

---

## 引用声明

- 页面布局遵照 `core/page-layout.md` §1.3（I-Practical布局）
- 字体方案遵照 `core/font-scheme.md` §1.3（微软雅黑11pt）
- 色彩遵照 `color/legal-color-system.md` §5 方案C（现代轻量）
- HTML渲染遵照 `format/html-spec.md` §4.3（I-Practical元素样式）+ §16.2（金额分解表）
- 数字/金额格式遵照 `core/punctuation-and-digits.md`（阿拉伯数字+元/日）
- 类型参照 `QUICK-REFERENCE.md` §2.4 计算类

---

## 偏离声明

无偏离项。I-Practical 计算类按标准路径渲染。

---

## 专属组件

### 刑期计算交互表格
- 法定刑区间行（标注法条来源）
- 量刑情节调节行（从重/从轻/减轻→调节范围→调节后区间）
- 羁押折抵明细行（起止日期/天数/折抵比例/折抵天数）
- 最终宣告刑行

### 可视化时间轴
- 收押日期 → 判决日期 → 释放日期
- 标注关键节点（侦查终结/移送审查起诉/提起公诉/一审宣判）
- 使用 `format/html-spec.md` §16.1 案件时间轴组件

### 打印适配
- `@media print` 样式：隐藏交互按钮，保留表格+时间轴
- 页边距适配打印
- 单色打印兼容（灰度替代色）
