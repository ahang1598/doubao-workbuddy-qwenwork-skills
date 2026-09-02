# PDF Runtime · 附录 03：模板完整性守卫 + rich_text 过滤器 + base_template 骨架

> **触发阅读条件**：编写/修改业务 `report_template.html`、ctx 字段设计、出现未渲染 Jinja 残留、`<b>` 被字面输出时。

## 1. 模板渲染完整性守卫（2026-04-29 强制）

> **背景**：2026-04-29 skill3 出现 PDF 正文里散落着 `{{ ctx.kpi_cards }}` / `{% for ... %}` 等未渲染 Jinja2 源码。根因是业务脚本没走 `env.get_template().render()`，而是把模板源码字符串直接拼接进 HTML。

### 防护点 1：渲染后 HTML 扫描（已实现于 `html_to_pdf.py`）

`render_html()` 在写盘前调用 `_detect_jinja_residuals()` 扫描整段 HTML，检测到 `{{ ... }}` 或 `{% ... %}`（排除 `{# ... #}` 注释）即 raise，**不产出 PDF**。错误消息指向常见三种原因：

1. ctx 字段名与业务模板不匹配
2. 业务模板把 base_template 的内容拼接在 `{% extends %}` 之外
3. 使用字符串拼接写 HTML 而未走 `env.get_template().render()`

**业务 Skill 绝对不要 bypass 这个守卫**。如果想输出占位 PDF，应该在 ctx 里放正确的占位值（如 `None`、空 list），而不是绕过 Jinja 渲染。

### 防护点 2：业务模板编写规约

所有业务模板（`skill3/4/5/assets/report_template.html`）**必须**：

- 以 `{% extends "base_template.html" %}` 开头
- 业务变量统一从 `ctx.*` 读取，不使用顶层别名
- `{% macro %}` 必须在 `{% block content %}` 内部定义
- 不得出现 `{{ html_content }}` 这类"把别处已渲染片段再拼进来"的模式

## 2. `rich_text` 过滤器（2026-04-29 强制）

> **背景**：2026-04-29 业务 ctx 中用于关键词高亮的 `<b>…</b>` / `<strong>…</strong>` 被 Jinja2 `autoescape` 转义，PDF 里变成字面的 `<b>核心判断</b>` 字样。

### 机制

运行时 `html_to_pdf.py` 已在 Jinja2 Environment 上注册名为 `rich_text` 的过滤器：

- 默认继续保持 `autoescape=True`（杜绝注入）
- **白名单**放行这些 inline 标签：`<b>` / `<strong>` / `<em>` / `<i>` / `<u>` / `<br>` / `<sub>` / `<sup>` / `<code>`
- 白名单之外的所有标签保持转义，安全性不降级
- `None` → 空字符串；非 str 输入会先 `str()`

### 使用约定

| 字段类型 | 用法 | 说明 |
|---|---|---|
| 自然语言文本（可能含 `<b>`） | `{{ ctx.insight.description \| rich_text }}` | 首选 |
| 明确无 HTML 的标量（银行名、百分比、日期等） | `{{ x }}` | 无需过滤 |
| 完整 HTML 片段（如 `leader_timeline_html`） | `{{ ctx.xxx \| safe }}` | 保持 `| safe` |
| 整型 / 枚举 / 状态词 | `{{ x }}` | 无需过滤 |

**禁止**在业务模板里把 `| rich_text` 和 `| safe` 同时作用在同一字段。

### 覆盖检查

新增业务字段时，评审标准：**"该字段的数据源是否有可能出现 `<b>` 或 `<br>`？"**

- 是 → 用 `| rich_text`
- 否 → 保持裸 `{{ }}`
- 字段本身就是完整 HTML 片段 → 用 `| safe`

## 3. Jinja2 骨架模板（`assets/base_template.html`）

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{{ meta.title }}</title>
<style>
/* 1. 基础样式 */
{{ base_css | safe }}
/* 2. 业务覆盖 */
{{ override_css | default('') | safe }}
/* 3. palette.json 注入 */
:root {
{% for key, val in palette.items() %}
    --{{ key }}: {{ val }};
{% endfor %}
}
</style>
</head>
<body>

<!-- 封面 -->
<section class="cover">
    <div class="cover-hero">
        <img class="cover-logo-big" src="data:image/png;base64,{{ logo_base64 }}" alt="LOGO">
    </div>
    <div class="cover-title-block">
        <div class="tag">{{ meta.kicker }}</div>
        <h1 class="cover-title">{{ meta.title }}</h1>
        <p class="cover-subtitle">{{ meta.subtitle }}</p>
    </div>
    <div class="cover-meta">
        {% for item in meta.cover_meta %}
        <div><span class="label">{{ item.label }}</span>{{ item.value }}</div>
        {% endfor %}
    </div>
</section>

<!-- 目录页 -->
<section class="page forced toc">
    <div class="toc">
        <h2>目 录</h2>
        {% for num, title, page in toc_items %}
        <div class="toc-item">
            <span class="toc-num">{{ num }}</span>
            <span class="toc-title">{{ title }}</span>
            <span class="toc-dots"></span>
            <span class="toc-page">{{ page }}</span>
        </div>
        {% endfor %}
    </div>
</section>

<!-- 内容页（业务 Skill 覆盖此 block） -->
{% block content %}{% endblock %}

<!-- 免责声明（可覆盖） -->
{% block disclaimer %}
<div class="disclaimer">本报告仅作研究参考，不构成任何投资建议</div>
{% endblock %}

</body>
</html>
```

业务 Skill 的 `report_template.html` 使用：

```html
{% extends "base_template.html" %}
{% block content %}
<!-- 业务专属内容 -->
{% endblock %}
```

## 4. 基础样式体系（`assets/style_guide.css`）

`style_guide.css` 统一提供：

- **CSS 变量**：`--primary` / `--accent` / `--primary-light` / `--growth-green` / `--risk-red` / `--efficiency-blue` / `--bg-light` / `--border` 等
- **全局排版**：字体（PingFang SC / Noto Sans SC / Noto Serif SC — 均为免费可用字体，无商业付费依赖）、字号、行高、orphans/widows
- **页面结构**：`.page` / `.page.forced` / `.page.content` / `.page.first-content`
- **封面**：`.cover` / `.cover-hero` / `.cover-logo-big` / `.cover-title-block` / `.cover-meta`
- **页眉页脚**：`.page-header` / `.page-footer`
- **目录**：`.toc` / `.toc-item`
- **章节标题**：`.section-title` / `.section-kicker` / `.subsection-title`
- **通用组件**：`.executive-summary` / `.insight-card` / `.evidence-table` / `.landscape-table` / `.two-col` / `.col-card` / `.radar-card` / `.appendix-box` / `.artifact-table` / `.disclaimer` / `.kpi-row` / `.kpi-card`
- **打印调整**：`@page` / `@media print`

业务覆盖样式写在 `{skill_dir}/assets/style_overrides.css`（仅业务专属组件，如 `insight-card` 变体）。
