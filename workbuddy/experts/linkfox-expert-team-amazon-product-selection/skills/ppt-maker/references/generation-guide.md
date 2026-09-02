# PPT/演示稿生成指南

## 生成流程

### Step 1: 确定参数
从用户输入中提取或询问：
- **内容**：用户提供的讲稿/大纲/要点（必须）
- **风格**：entrepreneur（默认） | corporate | creative | consultant | minimal
- **主题色**：black-fire（默认） | ember-orange | slate-dark | ocean-blue | forest-green | royal-purple | trust-navy
- **布局**：fullscreen（默认，1920x1080 满屏滚动）| slides（翻页模式）

### Step 2: 提炼内容
1. 读取用户原始内容
2. 按章节拆分，每节提炼核心要点
3. 为每章生成标题（≤12字，对比式/问题式/断言式/数字式）

### Step 3: 设计页面结构
选择合适的页面类型组合：

| 页面类型 | 用途 | 特征 |
|---------|------|------|
| hero | 封面 | 大标题 + 副标题 + 动态光斑 |
| big-number | 数据展示 | 超大数字 + 说明 |
| two-col | 对比/并列 | 左右两栏布局 |
| cards-grid | 多项并列 | 2×2 或 3×N 卡片网格 |
| feature-list | 列表展示 | 图标 + 标题 + 描述 |
| code-block | 代码/配置 | 等宽字体 + 语法高亮 |
| highlight-box | 引用/金句 | 左边框 + 大字引用 |
| modules-list | 编号列表 | 序号 + 图标 + 名称 |
| tools-grid | 工具展示 | N列图标卡片 |
| rules-grid | 规则/要点 | 图标 + 文字卡片 |
| footer | 结尾 | 总结 + 行动号召 |

### Step 4: 生成 HTML
- 读取 [assets/proposal-template.html](../assets/proposal-template.html) 了解基础结构
- 读取对应主题 CSS（如 [themes/black-fire.css](../themes/black-fire.css)）
- 生成单个完整 HTML 文件（内联所有 CSS + JS）
- 使用 Google Fonts CDN（Inter + Noto Sans SC + JetBrains Mono）

### Step 5: 输出
- 保存到 `output/` 目录
- 用 `open` 命令在浏览器中预览
- 通过 `message` 工具发送文件给用户

## 视觉规范

### black-fire 主题（默认）
| 项目 | 值 |
|------|-----|
| 背景 | #000000 |
| 主文字 | #ffffff |
| 强调色1 | #ff6b35（橙） |
| 强调色2 | #ef4444（红） |
| 辅助文字 | #d4d4d4 |
| 弱化文字 | #737373 |
| 卡片背景 | #111111 |
| 边框 | #262626 |
| 渐变 | linear-gradient(135deg, #ff6b35, #ef4444) |

### 图表/多色标签辅助色（chart colors）

当页面里出现**折线图/柱状图/热力图/多色 badge/多角色对比**等需要 2 种以上颜色区分的场景时，
每个主题 CSS 都额外定义了 4 个辅助色变量，不要自己现编颜色，直接读取对应主题的这 4 个值：

```css
--theme-chart-blue    /* 中性/信息类 */
--theme-chart-green   /* 正向/成功类 */
--theme-chart-purple  /* 次要强调/特殊类 */
--theme-chart-yellow  /* 警告/待定类 */
```

生成输出 HTML 时，和 `--theme-primary → --primary` 一样，把这 4 个变量去掉 `theme-` 前缀、
按语义重命名成 `--blue` / `--green` / `--purple` / `--yellow` 写进输出文件的 `:root`：

```css
:root {
  --primary: #ff6b35;
  --accent: #ef4444;
  --bg: #000000;
  --bg-card: #111111;
  --border: #262626;
  --gradient: linear-gradient(135deg,#ff6b35 0%,#ef4444 100%);
  /* 图表辅助色，从对应主题的 --theme-chart-* 抄值 */
  --blue: #60a5fa;
  --green: #22c55e;
  --purple: #a78bfa;
  --yellow: #fbbf24;
}
```

各主题取值不同（浅色背景主题用中高饱和度深色系保对比度，深色背景主题用亮色系），
以对应主题 CSS 文件里的 `--theme-chart-*` 为准，不要跨主题混用。

### 排版
- 标题：3-5rem，font-weight: 900
- 正文：1.1-1.25rem，font-weight: 400
- 代码：JetBrains Mono
- 中文：Noto Sans SC
- 英文：Inter
- 行高：1.7

### 交互
- 右侧导航圆点（滚动定位）
- 卡片 hover 上浮 + 边框变色
- 动态光斑背景（header + footer）
- 平滑滚动 scroll-behavior: smooth

## 严禁行为
- ❌ 堆字/密集排版
- ❌ 亮色背景（除非用户指定）
- ❌ 小字体（最小 0.85rem）
- ❌ 外部图片依赖（纯 CSS + emoji）
- ❌ 需要构建工具（必须双击即用）

## 输出要求
- 单个 HTML 文件，内联所有样式和脚本
- 1920x1080 满屏优化
- 移动端响应式
- 双击可直接打开
