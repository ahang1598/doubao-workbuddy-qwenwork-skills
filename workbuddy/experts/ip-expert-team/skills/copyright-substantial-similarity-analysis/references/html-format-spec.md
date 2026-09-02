# HTML 排版规范 — 著作权侵权"实质性相似+接触可能性"分析

> 版本：v3.0.0 | 格式严肃度：C-Professional | 样式策略：纯内联+Richee 组件
> 遵循 base/rule/format-html/format/html-spec.md §1.3 范式唯一性条款

---

## 一、样式策略声明

| 项目 | 值 | 依据 |
|------|-----|------|
| 格式严肃度 | C-Professional | 客户/律师交付级专业报告 |
| 样式策略 | 纯内联+Richee 组件 | html-spec.md §1.3 范式唯一性条款 |
| 视觉权威 | Richee Design Token | base/rule/format-html/core/design-tokens.md |
| 字体栈 | `'PingFang SC','Inter',-apple-system,sans-serif` | design-tokens.md §6 |
| 输出格式 | HTML（始终输出） | 浏览器打开即渲染，支持打印/PDF |

### 禁止范式

| ❌ 禁止 | 原因 |
|---------|------|
| HARD_BLOCK 集中 CSS | 元素与样式分离，破坏自包含性（§1.3） |
| 外部 CSS 文件引用 | 依赖外部资源，复制粘贴丢失排版 |
| 元素级 CSS class 体系 | 同 HARD_BLOCK，元素与样式分离 |
| 自创色值 | 必须取自 Richee Design Token |

> **@media print class 白名单**：`<style>` 块内 `@media print` 中允许使用以下 class 选择器控制打印行为（属§1.2例外）：`.side-nav` / `.toolbar` / `.no-print` / `.screen-only` / `.source-section` / `.main-content` / `.page-break-before` / `.mermaid-wrap` / `.print-table` / `.template-version-watermark` / `.page-footer`。这些 class 仅用于 `@media print` 中的 `display:none` / `margin` / `opacity` 控制，不用于元素级样式控制。

---

## 二、页面参数（C-Professional）

| 参数 | 值 | 来源 |
|------|-----|------|
| @page margin | 2.5cm 2.6cm 2.0cm 2.8cm | html-spec.md §2.2 |
| body font-family | `'PingFang SC','Inter',-apple-system,sans-serif` | design-tokens.md §6 |
| body font-size | 12pt | html-spec.md §2.2 |
| body line-height | 1.8 | html-spec.md §2.2 |
| article max-width | 156mm | html-spec.md §2.2 |
| 页眉 | 文档标题+律所/技能名 | html-spec.md §2.2 |

---

## 三、Richee 组件引用清单

```yaml
richee_components: [c01, c04, c05, c06, c09, c12, c15]
```

| 组件 | 名称 | 用途 | 使用位置 |
|------|------|------|----------|
| c01 | 基础表格 | 案件概况信息 | 案件概况区 |
| c04 | 证据目录表 | 独创性三层剥离清单 | 模块一 |
| c05 | 风险清单表 | 剥离理由/抗辩预判清单 | 模块一（附）/模块五 |
| c06 | 结论卡 | 综合分析结论 | 模块四 |
| c09 | 时间轴 | 发表时间线/接触因果链 | 模块三 |
| c12 | 风险矩阵 | 相似度×独创性强度×相似性质矩阵 | 模块二 |
| c15 | 证据链图 | 接触传播链（Mermaid） | 模块三（如适用） |

> 组件模板详见 base/rule/format-html/components/ 对应 .md 文件

---

## 四、色值速查（Richee Design Token）

| 用途 | 色值 | 来源 Token |
|------|------|-----------|
| 标题/正文文字 | `#0a0d12` | `--text` |
| 注释/次要文字 | `#6b7280` | `--muted` |
| 分隔线/边框 | `#e2e5ea` | `--line` |
| 页面背景 | `#f6f7f9` | `--bg` |
| 卡片/表格背景 | `#ffffff` | `--white` |
| 高风险/红 | 文字 `#d92d20` / 浅底 `#fef3f2` | `--red` / `--redbg` |
| 中风险/琥珀 | 文字 `#b54708` / 浅底 `#fffaeb` | `--amber` / `--amberbg` |
| 低风险/绿 | 文字 `#039855` / 浅底 `#ecfdf3` | `--green` / `--greenbg` |
| 信息/蓝 | 文字 `#175cd3` / 浅底 `#eff8ff` | `--info` |
| 高度强调/反转标记 | 深底 `#d92d20` / 白字 `#ffffff` | `--red` / `--white` |

### 三层剥离色值映射

| 剥离层级 | 标签样式 |
|----------|----------|
| 🟢 公共领域 | `background:#ecfdf3;color:#039855;` |
| 🟡 Scenes à faire | `background:#fffaeb;color:#b54708;` |
| 🔴 独创性表达 | `background:#fef3f2;color:#d92d20;` |

### 三性分类色值映射【新增】

| 相似性质 | 标签样式 |
|----------|----------|
| 共通表达（⭐⭐） | `background:#f6f7f9;color:#6b7280;` |
| 共同选择（⭐⭐⭐） | `background:#fffaeb;color:#b54708;` |
| 共同错误（⭐⭐⭐⭐⭐） | `background:#fef3f2;color:#d92d20;` |

---

## 五、占位符清单

HTML 模板 (`templates/html-template.html`) 使用 CONTENT_SLOT 占位符路由：

| 占位符 | 说明 | 填充内容 |
|--------|------|----------|
| `<!-- CONTENT_SLOT:PAGE_TITLE -->` | 页面标题 | "著作权侵权实质性相似分析报告" |
| `<!-- CONTENT_SLOT:SUBTITLE -->` | 副标题 | 案件名称 |
| `<!-- CONTENT_SLOT:PAGE_META -->` | 元信息 | 分析日期+技能版本+分析视角 |
| `<!-- CONTENT_SLOT:GENERATED_AT -->` | 生成时间 | YYYY-MM-DD HH:MM |
| `<!-- CONTENT_SLOT:CASE_OVERVIEW -->` | 案件概况 | c01 基础表格（案件名称/作品类型/涉诉权利等） |
| `<!-- CONTENT_SLOT:MODULE_1 -->` | 独创性剥离对比清单 | c04 三层标注表 + c05 剥离理由表 |
| `<!-- CONTENT_SLOT:MODULE_2 -->` | 逐层比对结果 | 整体观感锚定+三层比对叙述+三性分类+错误复制+c12 风险矩阵 |
| `<!-- CONTENT_SLOT:MODULE_3 -->` | 接触可能性评估 | 因果链四阶分析 + c09 时间轴 + 接触等级 |
| `<!-- CONTENT_SLOT:MODULE_4 -->` | 综合分析结论 | 三阶交互矩阵 + c06 结论卡 + 分权论证 |
| `<!-- CONTENT_SLOT:MODULE_5 -->` | 被告抗辩路径预判 | c05 风险清单表（四类抗辩+可能性+应对要点） |
| `<!-- CONTENT_SLOT:DOWNGRADE_NOTE -->` | 降级说明 | C+D+G 最小骨架（如适用） |

---

## 六、LLM 生成职责

| 职责 | 说明 |
|------|------|
| ✅ 填充 CONTENT_SLOT | 用真实分析内容替换占位符 |
| ✅ 内联样式 | 所有元素使用 `style="..."`，色值取自 Richee Token |
| ✅ Richee 组件 | 复制 components/ 对应组件模板，替换数据 |
| ✅ 三性分类标注 | 每个相似点标注共通表达/共同选择/共同错误 |
| ✅ 三阶交互矩阵 | 综合结论区呈现三阶交互判定矩阵 |
| ❌ 修改 `<style>` 块 | `<style>` 仅含 @page/@media print/页码计数器/Mermaid 初始化（§1.2 例外） |
| ❌ 自创 HTML 布局 | 按模板结构填充，不自由发挥 |
| ❌ 在 CONTENT_SLOT 中创建 `<style>` | 禁止元素级 CSS class |
| ❌ 使用"鉴定"字眼 | 应为"分析"（术语合规） |

---

## 七、打印/PDF 适配

| 规则 | 说明 |
|------|------|
| `@media print` 隐藏 | 侧栏导航/工具栏/版本水印/三性图例 |
| `@media print` 展开 | 折叠区（`details`）打印时展开 |
| 打印颜色保留 | `table th/td` 设置 `print-color-adjust:exact` |
| 页码 | CSS 计数器自动页码，首页无页眉页脚 |
| Mermaid 图表 | 打印时隐藏 Mermaid 容器，显示降级表格 |

---

## 八、Mermaid 图表集成

接触传播链（c15 证据链图）使用 Mermaid 渲染：

```javascript
mermaid.initialize({
  startOnLoad: true,
  theme: 'base',
  themeVariables: {
    primaryColor: '#eff8ff',
    primaryTextColor: '#0a0d12',
    primaryBorderColor: '#e2e5ea',
    lineColor: '#6b7280',
    fontSize: '12px'
  }
});
```

**降级机制**：
- Mermaid CDN 加载失败 → 显示 `<noscript>` 提示
- 渲染失败 → 显示降级表格（`print-table`）
- 离线环境 → 提示复制源码到 mermaid.live 在线渲染

---

## 九、质量检查清单

| 检查项 | 标准 | 级别 |
|--------|------|------|
| 内联样式铁律 | 所有元素 `style="..."`，无 CSS class 控制 | 🔴阻断 |
| 色值合规 | 色值取自 Richee Design Token | 🔴阻断 |
| 字体栈合规 | `'PingFang SC','Inter',-apple-system,sans-serif` | ⚠️警告 |
| 占位符已填充 | 无残留 `CONTENT_SLOT` 占位符 | 🔴阻断 |
| 免责声明已附 | 固定红色左边框警示样式 | 🔴阻断 |
| 打印适配 | `@media print` 规则完整 | ⚠️警告 |
| 侧栏导航 | 七模块+免责声明导航链接 | 💡建议 |
| Mermaid 降级 | `<noscript>` + 降级表格 | 💡建议 |
| 三性分类标注 | 每个相似点标注三性+对应色值 | 🔴阻断 |
| 三阶交互矩阵 | 综合结论区呈现三阶交互判定矩阵 | 🔴阻断 |
| 术语合规 | 无"鉴定"字眼 | 🔴阻断 |

---

<!-- Copyright © 深圳市法大大网络科技有限公司 版权所有 | Author: 法大大法律AI产品线 -->
