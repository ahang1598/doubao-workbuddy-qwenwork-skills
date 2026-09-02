---
name: pdf-report-builder-runtime
description: 共享 PDF Runtime。为 skill3/4/5 提供统一的 HTML→PDF 渲染引擎、VIS 资产构建、封面/目录骨架、样式体系与校验流程。该运行时不单独作为 Skill 发布，而是在 pack/publish 前被注入到业务 Skill 中。
triggers:
  - PDF 生成
  - 报告渲染
  - HTML 转 PDF
  - 视觉资产构建
  - 年报 LOGO 提取
  - 封面生成
  - 页眉页脚
  - pypdf 合并
  - PDF 校验
---

# 共享 PDF Runtime · RUNTIME.md

> **⚠️ 阅读契约（给 Agent）**
>
> 本文件是 skill3 / skill4 / skill5 生成 PDF 交付物时的**唯一权威规约**。
>
> **每次执行 PDF 生成流程前，Agent 必须 `read_file` 本 RUNTIME.md**，
> 然后在调用 `build_report(...)` 时传入 `runtime_acknowledged=True` 表示已确认。
> 业务 SKILL.md 里的 PDF 小节只是链接指向这里。
>
> 本文件的加载路径：
> - 源码态开发：`shared/pdf-report-builder-runtime/RUNTIME.md`
> - 业务 Skill 执行态（推荐）：`{skill_dir}/_vendor/pdf_report_builder_runtime/RUNTIME.md`
>
> 若 Agent 发现自己即将生成 PDF 但未读过本文件，**立即停下读它**。

## 📚 渐进式加载索引（按需阅读）

| 触发条件 | 阅读文件 |
|---|---|
| 首次生成 PDF / 配置基准行 / `assets_ready()` 为 False / 自动下载 / 质量核验 | `references/01_base_bank_and_assets.md` |
| `build_by_bank_vis.py --auto-download` 失败 / `grade=F` / 需要补下载 LOGO | `references/02_logo_fetch_fallback.md` |
| 编写/修改业务模板 / ctx 字段设计 / 出现未渲染 Jinja 残留 / `<b>` 被字面输出 | `references/03_template_and_filters.md` |
| 首次构建 VIS 资产 / P0 验收失败 / PDF 分页/LOGO/承接页异常 | `references/04_p0_vis_and_validation.md` |
| 调用 `build_report` 等接口 / 改造业务 Skill / 排查 vendor 注入 / 临时脚本 | `references/05_interfaces_and_params.md` |

> **默认工作流**：Agent 读本 RUNTIME.md 后按触发条件决定是否继续加载 references，避免一次性全量加载。

## 🧭 PDF 生成速查（Agent 必看）

| 步骤 | 动作 | 依赖附录 |
|---|---|---|
| 1 | 解析基准行（显式参数 > 环境变量 > query；**无默认值，必须指定**） | `references/01_*` |
| 2 | 确认 `BankContext.assets_ready()`；若否跑 `build_by_bank_vis.py --bank <short> --auto-download` 或 `--manual-logo <path>` | `references/01_*` |
| 3 | 跑 skill 主流程产出 `ctx` 数据 | 业务 SKILL.md |
| 4 | 调 `build_report(ctx=..., base_bank=<short>, runtime_acknowledged=True, ...)` | `references/03_*` + `references/05_*` |
| 5 | 产物落 `~/RetailAnalysis/output/<bank_short>/` | `references/05_*` |
| 6 | （可选）跑 `pdf_validator.validate_pdf(...)` 做 5 项校验 | `references/04_*` |

> **不可绕过的硬规则**：
> - 模板必须 `{% extends "base_template.html" %}`，不得字符串拼接
> - 业务变量一律从 `ctx.*` 读取；不得既有 `ctx.x` 又有顶层 `x`
> - 所有渲染走 `env.get_template().render()`，不得手写 HTML 字符串
> - `html_to_pdf.render_html` 的「Jinja2 残留扫描」不允许跳过
> - VIS 资产未固化时严禁生成 PDF
> - LOGO 必须通过 10 项 audit；严禁自行绘制 / AI 生成
> - 所有 PDF 产物写 `~/RetailAnalysis/output/<bank_short>/`，不得写到 output/ 根目录

## 定位

本运行时是 skill3（同业对标）、skill4（战略洞察）、skill5（战略与治理）在 PDF 交付物上的**共享基础设施**。它本身**不单独作为 Skill 发布**；需要输出 PDF 的业务 Skill，会在 pack/publish 前由 `scripts/release.py` 把本运行时注入到自身目录中。

**设计原则**：

- 一次实现，多处复用
- 业务 Skill 只负责准备 `ctx`（数据上下文）和选择模板扩展
- 本运行时负责 HTML 渲染、分两次导出、pypdf 合并、5 项校验
- **构建时注入 / vendor**：运行时不跨 Skill 读取文件；由 `scripts/release.py` 在打包前把 `shared/pdf-report-builder-runtime/` 注入到 skill3/4/5 自己的 `_vendor/pdf_report_builder_runtime/` 下

## 核心接口签名

> **完整参数与调用示例见 `references/05_interfaces_and_params.md`。**

```python
from html_to_pdf import build_report
from bank_context import resolve

ctx = resolve(base_bank=base_bank_param, query=user_query)
build_report(
    ctx=report_ctx,
    template_path=str(skill_dir / "assets" / "report_template.html"),
    output_html=str(ctx.output_path("<name>.html")),
    output_pdf=str(ctx.output_path("<name>.pdf")),
    style_overrides_path=str(skill_dir / "assets" / "style_overrides.css"),
    base_bank=ctx.short_name,          # 触发 per-bank logo / palette 自动选取
    header_text="...",
    runtime_acknowledged=True,         # 必填：表明已阅读本 RUNTIME.md
)
```

`build_report` 在渲染前会：
- 从 `by_bank/<bank>/vis/palette.json` 加载 palette（变量驱动 CSS）
- 从 `by_bank/<bank>/logo/logo_base64.txt` 加载封面 LOGO 与页眉 LOGO
- 如 per-bank 资产缺失，自动降级到 `banks.yaml::brand_identity` 合成的官方色 palette
- 对渲染后 HTML 执行 `_detect_jinja_residuals()` 扫描，发现未渲染 Jinja 即 raise

## 产物结构速查

```
~/RetailAnalysis/report_assets/
├── annual_report/<bank>_<year>_annual_report.pdf
├── by_bank/<bank_short>/               # 按行隔离（唯一允许使用的视觉资产）
│   ├── logo/{logo.png, logo_base64.txt, logo_source.txt}
│   ├── vis/{cover,toc,finance}-*.png, palette.json
│   └── brand.yaml
└── legacy/                             # 历史共享资产（向后兼容）

~/RetailAnalysis/output/<bank_short>/   # 按行产物目录
├── <report_name>.html
├── <output_name>.pdf
└── pdf_check/skill<N>-*.png
```

## 依赖

- Python 3.10+
- jinja2
- playwright
- pypdf（或 PyPDF2）
- Pillow（PDF 校验与 VIS 资产构建）

## 参数化差异（skill3 vs skill4 vs skill5 的默认值）

> **详细参数表见 `references/04_p0_vis_and_validation.md` 第 3 节。**

主要差异集中在 `margin_top` / `margin_bottom` / `cover_height` / `logo_height` / `logo_width` / `page_range`。三个业务 Skill 调用 `build_report` 时通过关键字参数覆盖。
