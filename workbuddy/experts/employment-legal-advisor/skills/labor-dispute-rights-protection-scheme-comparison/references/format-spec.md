# 格式规范 | 劳动争议维权方案对比

> 版本: 3.1.0 | 输出格式: 双HTML（O1客户版 + O2律师版） | 格式严肃度: C-Professional / I-Practical
> 权威参照: common/visual-spec 视觉规范体系

**v3.0.x 重大变更**：格式规范已从本文件迁移至具体的 HTML 模板和 CSS 样式表。本文件保留为格式能力索引。

## 1. 格式能力索引

| 格式能力 | 实现位置 | 说明 |
|---------|---------|------|
| HTML报告结构 | `templates/html/labor-remedy-compare-template.html` | 六大区块+占位符系统 |
| 视觉样式 | `templates/css/labor-remedy-compare-C-Professional.css` | CSS变量系统+风险色谱+布局 |
| 输出规格 | `references/output-spec.md` | 六段式报告结构+C-Professional排版参数 |
| 打印适配 | HTML模板内嵌 `@media print` + CSS样式表 | A4纸打印+折叠展开+去交互 |

## 2. 渲染组件清单（v3.1.0）

- **并排方案对比卡片**：CSS Grid auto-fit，每卡片一张方案×六维对比
- **风险色谱**：砖红（#C0392B）/古铜金（#D4A017）/柔和绿（#27AE60），仅作卡片左侧5px窄色条点缀
- **金额柱状图**：CSS bar-chart，最佳/一般/最差三区间
- **可折叠操作指引**：`<details><summary>`，每方案独立的受理机构+材料+步骤+时间
- **推荐方案高亮**：蓝色边框+背景高亮
- **时效红色警告框**：红色背景+倒计时天数
- **免责声明**：头部灰蓝色+底部灰蓝色，双位置确保阅读
