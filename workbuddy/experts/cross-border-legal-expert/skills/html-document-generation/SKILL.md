---
name: html-document-generation
description: "Markdown转HTML文档生成。基于Pandoc + Richee设计系统，6模板（报告/意见/简报/函件/法定文书/法定表格），支持目录、内联CSS单文件、图片题注、有序列表文本序号。适用于法律研究报告、意见书、律师函、起诉状、申请表等。"
version: "2.1.0"
tags:
  - 文档生成
  - html
  - pandoc
  - markdown
---

# HTML 文档生成

> 基于 Pandoc + Richee 设计系统将 Markdown 转换为专业 HTML 报告  
> 6 模板覆盖法律行业全场景：报告/意见/简报/函件/法定文书/法定表格

---

## 文件结构

```
html-document-generation/
├── SKILL.md                          # 本文件
└── scripts/
    ├── md2html.py                    # 转换入口（pandoc + 模板 + Lua 过滤器）
    ├── markdown-to-html.lua          # Lua 过滤器聚合
    ├── disable-ordered-list-numbering.lua   # 有序列表文本序号
    ├── image-title-to-caption.lua            # 图片题注
    ├── shared.css               # 共享 CSS（设计令牌 + 全部组件类）
    ├── template-report.html      # 全面报告
    ├── template-opinion.html     # 意见书/备忘录
    ├── template-brief.html       # 简报/快讯
    ├── template-letter.html      # 律师函/催告函
    ├── template-pleading.html   # 法定文书（起诉状/申请书）
    └── template-form.html       # 法定表格（官方表格填充）
```

---

## 目录

1. [技术栈](#1-技术栈)
2. [模板选型](#2-模板选型)
3. [创建 HTML 文档](#3-创建-html-文档)
4. [Richee 设计系统](#4-richee-设计系统)
5. [Lua 过滤器](#5-lua-过滤器)
6. [Markdown 编写规范](#6-markdown-编写规范)
7. [输出规范](#7-输出规范)
8. [Do / Don't](#8-do--dont)

---

## 1. 技术栈

| 技术 | 用途 | 成本 |
|------|------|------|
| Pandoc + HTML 模板 | Markdown → HTML 转换 | `md2html.py` 一行命令 |
| Lua 过滤器 | 有序列表文本序号、图片题注 | 自动加载 |
| CSS（共享 `shared.css`） | 6 模板共享设计令牌 + 组件类 | `--include-in-header` 注入 |

---

## 2. 模板选型

| 模板别名 | 文件 | 场景 | 典型文档 | 结构特点 |
|---------|------|------|---------|---------|
| `report` | `template-report.html` | **全面报告** | 法律研究/尽调/案件分析/合规审查 | topbar + hero + 左侧导航目录 + 组件丰富 + footer |
| `opinion` | `template-opinion.html` | **意见/备忘录** | 法律意见书/法律备忘录 | 单栏 + 致/事由/编号表头 + 署名区 |
| `brief` | `template-brief.html` | **简报/快讯** | 新法速递/合规提醒/政策解读 | 极简单栏 + 1-3 屏 + 无导航 |
| `letter` | `template-letter.html` | **正式函件** | 律师函/催告函/法律告知函 | 信函格式（收件人/正文/落款）+ 正式编号 |
| `pleading` | `template-pleading.html` | **法定文书** | 起诉状/申请书/答辩状/反诉状 | 居中标题（上下双线）+ 当事人信息 + 正文首行缩进 + 此致法院 + 具状人 |
| `form` | `template-form.html` | **法定表格** | 登记申请表/申报表/备案表 | 标题 + 官方表格（固定字段填空）+ 填表说明 + 签章区 |

6 个模板共享 `shared.css`（同一套设计令牌和组件类），只是页面骨架不同。

---

## 3. 创建 HTML 文档

### 一行命令

```bash
# 全面报告（默认）
python scripts/md2html.py report.md -o output.html --toc --title "供应商风险评估报告"

# 法律意见书
python scripts/md2html.py opinion.md --template opinion --title "法律意见书" \
  --addressee "XX科技有限公司" --firm "XX律师事务所" --lawyer "张三" --disclaimer

# 简报/快讯
python scripts/md2html.py brief.md --template brief --title "《数据安全法》修订要点" \
  --date "2026-07-28" --disclaimer

# 律师函
python scripts/md2html.py letter.md --template letter --title "关于XX合同违约的律师函" \
  --addressee "XX贸易有限公司" --firm "XX律师事务所" --date "2026-07-28"

# 民事起诉状
python scripts/md2html.py pleading.md --template pleading --title "民事起诉状" \
  --court "杭州市中级人民法院" --signer "张三" --date "2026-07-28"

# 企业登记申请表
python scripts/md2html.py form.md --template form --title "企业登记申请表" \
  --signer "李四" --date "2026-07-28" --form-no "DJ-2026-001"
```

### 参数说明

#### 通用参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-o output.html` | 输出路径 | 同输入文件名 .html |
| `--template` | 模板：report/opinion/brief/letter/pleading/form 或自定义路径 | report |
| `--title` | 文档标题 | 输入文件名 |
| `--report-no` | 报告编号 | 空 |
| `--date` | 日期 | 空 |
| `--disclaimer` | 追加 AI 免责声明 | 关 |
| `--standalone` | 内联 CSS/图片为单文件 | 关 |
| `--filter none` | 跳过 Lua 过滤器 | 启用 |

#### report 专用

| 参数 | 说明 |
|------|------|
| `--subtitle` | Hero 副标题 |
| `--status` | 顶栏状态文字 |
| `--pills` | 元数据标签（HTML 片段） |
| `--footer` | 页脚文字 |
| `--toc` | 生成左侧目录导航 |

#### opinion/letter 专用

| 参数 | 说明 |
|------|------|
| `--addressee` | 致/收件人 |
| `--firm` | 律所名称 |
| `--lawyer` | 经办律师（opinion） |
| `--cc` | 抄送（letter） |

#### brief 专用

| 参数 | 说明 |
|------|------|
| `--author` | 作者 |

#### pleading 专用

| 参数 | 说明 |
|------|------|
| `--court` | 受理法院（此致 XX人民法院） |
| `--signer` | 具状人 |
| `--parties` | 当事人信息 HTML 片段 |

#### form 专用

| 参数 | 说明 |
|------|------|
| `--signer` | 填表人/申请人 |
| `--form-no` | 表格编号 |
| `--form-note` | 填表说明 |

---

## 4. Richee 设计系统

> 配色纪律：黑白灰承载 90% 信息；绿色仅用于强调；红/琥珀/绿/蓝只用于标签与风险等级。

### 设计令牌

| 类别 | 关键令牌 | 值 |
|------|---------|-----|
| 底/纸 | `--bg` / `--white` | `#f7f7f7` / `#ffffff` |
| 主黑/正文 | `--black` / `--text` | `#1a1a1a` |
| 次要文字 | `--muted` | `#6b7280` |
| 分割线 | `--line` | `#e2e5ea` |
| 强调（单绿） | `--accent` / `--accent-dark` | `#32d583` / `#029856` |
| 危险/警告/成功/信息 | `--red`/`--amber`/`--green`/`--blue-text` | `#d92d20`/`#b54708`/`#029856`/`#175cd3` |
| 字体 | `--font-sans` | `'PingFang SC','Segoe UI',-apple-system,sans-serif` |

### 组件映射（Markdown 内嵌 HTML 用法）

基础内容（标题/段落/表格/列表）用 Markdown 语法。特殊组件在 Markdown 中内嵌 HTML 片段。

| 组件 | 类名 | 用法示例 |
|------|------|---------|
| 结论卡 | `.conclusion` | `<div class="conclusion"><div class="head"><strong>综合结论</strong><span class="tag high">高风险</span></div><div class="body">结论文字</div></div>` |
| 指标卡 | `.grid-4` + `.kpi` | `<div class="grid-4"><div class="kpi"><div class="name">罚款上限</div><div class="value">20倍</div><div class="note">违法经营额</div></div></div>` |
| 风险标签 | `.tag.high/.mid/.low` | `<span class="tag high">高风险</span>` |
| 置信度条 | `.confidence` | `<div class="confidence"><span class="stars">⭐⭐⭐⭐☆ 88%</span><div class="track"><div class="fill" style="width:88%"></div></div></div>` |
| 时间轴 | `.timeline` + `.t-item` | `<div class="timeline"><div class="t-item"><div class="t-title">2025.11.8</div><div class="t-text">公告生效</div></div></div>` |
| 热度条 | `.bar-row` | `<div class="bar-row"><span>支持强度</span><div class="track"><div class="fill" style="width:85%"></div></div><span>85%</span></div>` |
| 风险矩阵 | `.matrix` + `.box` | `<div class="matrix"><div class="box h">表头</div><div class="box r">高风险</div></div>` |
| 表格滚动 | `.table-scroll` | `<div class="table-scroll"><table>...</table></div>` |
| 网格布局 | `.grid-2/.grid-3/.grid-4` | `<div class="grid-2">两个卡片</div>` |

### opinion/letter 专用类

| 组件 | 类名 | 说明 |
|------|------|------|
| 意见书表头 | `.opinion-header` | 致/事由/编号/日期两列表格 |
| 署名区 | `.signature-block` | 律所/律师/日期/印章位 |
| 函件标题 | `.letter-header h1` | 上下双线居中标题 |
| 函件收件人 | `.letter-recipient` | 致/抄送 |
| 函件正文 | `.letter-body p` | 首行缩进 2em |
| 函件落款 | `.letter-signoff` | 律所/日期右对齐 |

### pleading/form 专用类

| 组件 | 类名 | 说明 |
|------|------|------|
| 文书标题 | `.pleading-title` | 居中、上下双线 |
| 当事人信息 | `.pleading-parties` | 原告/被告/第三人 |
| 文书正文 | `.pleading-body p` | 首行缩进 2em |
| 此致法院 | `.pleading-court` | 左对齐 |
| 具状人 | `.pleading-signoff` | 具状人 + 日期右对齐 |
| 印章位 | `.pleading-seal` | 虚线圆框 |
| 表格标题 | `.form-title` | 居中加粗 |
| 表格副标题 | `.form-subtitle` | 编号/版次 |
| 官方表格 | `.form-table` | 实线边框、无圆角 |
| 字段标签 | `.form-label` | 灰底加粗居中 |
| 字段值 | `.form-value` | 左对齐 |
| 分区标题 | `.form-section` | 黑底白字跨行 |
| 填表说明 | `.form-note` | 灰色小字 |
| 签章区 | `.form-signoff` | 三栏（填表人/日期/签章） |

### 响应式与打印

| 断点 | 行为 |
|------|------|
| ≤1023px | 导航目录从侧栏变顶部横排 |
| ≤767px | 顶栏竖排、网格变单列、表格横向滚动 |
| `@media print` | A4 + 隐藏导航 + 表格不跨页 + 保留背景色 |

---

## 5. Lua 过滤器

| 过滤器 | 功能 | 为什么需要 |
|--------|------|-----------|
| `disable-ordered-list-numbering.lua` | 禁用有序列表自动编号，保留 MD 原文序号 | Pandoc 默认剥离 `1.` 前缀改用原生编号，与 MD 文本序号重复 |
| `image-title-to-caption.lua` | 图片 title 转为 `<figcaption>` 题注 | Pandoc 默认用 alt 做标题，不符合题注语义 |

---

## 6. Markdown 编写规范

### 标题编号

```
# 文档标题（不加序号）
## 一、一级标题            ← 中文数字 + 、
### （一）二级标题          ← 中文数字 + 括号
#### 1. 三级标题            ← 阿拉伯数字 + .
##### （1）四级标题          ← 阿拉伯数字 + 括号
```

> 序号由 Markdown 内容控制，不在模板里设自动编号，避免双份序号。

### 其他

- 优先使用 Markdown 而非内嵌 HTML
- 仅在复杂表格（`colspan`）、特殊组件时使用 HTML 片段
- **正文不得使用 emoji**，用 `[已核验]`、`[注意]`、`[高]`、`[中]`、`[低]` 等文字标签

---

## 7. 输出规范

### 通用

- 正式交付物必须包含 AI 免责声明（`--disclaimer`）
- 禁止"保证胜诉""绝无风险""完全合规""一定合法"等绝对化法律结论
- 风险、状态、优先级不得只靠颜色表达，必须同时有文字标签
- 依据标签限定为：`[已核]` `[待核]` `[用规]` `[事实]` `[推定]` `[用户提供]` `[公开来源]`；不得自创或混用
- 文件名不得含 emoji；下载件采用可识别的主题和日期命名

### HTML 专属

- 独立分发的 HTML 必须用 `--standalone` 内联所有 CSS/图片，不依赖外部资源
- CSS 不得含 `</style>` 闭合标签字面量，避免样式块提前终止
- 页面必须支持窄屏阅读，表格允许横向滚动，布局不得溢出容器

---

## 8. Do / Don't

| ✅ Do | ❌ Don't |
|------|---------|
| 按场景选模板（report/opinion/brief/letter/pleading/form） | 所有文档都用默认 report |
| 正式文档加 `--disclaimer` | 忘记加免责声明 |
| 独立分发用 `--standalone` | 输出依赖外部 CSS |
| 序号在 Markdown 中手写 | 依赖模板自动编号 |
| 风险等级用文字标签 `[高]` | 只用颜色表示 |
| 特殊组件内嵌 HTML 片段 | 全文手写 HTML |
