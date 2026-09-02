# PDF Runtime · 附录 05：脚本接口、目录约定、业务 Skill 改造、临时脚本规约

> **触发阅读条件**：调用 `build_report` / `validate_pdf` / `build_vis_assets` 接口、改造业务 Skill、排查 vendor 注入、临时脚本命名清理时。

## 1. 脚本接口

### `scripts/html_to_pdf.py::build_report()`

```python
def build_report(
    ctx: dict,                           # 数据上下文
    template_path: str,                  # 业务模板路径（继承 base_template）
    output_html: str,                    # 输出 HTML 路径
    output_pdf: str,                     # 输出 PDF 路径
    *,
    style_overrides_path: str | None = None,  # 可选覆盖 CSS
    margin_top: str = "22mm",
    margin_bottom: str = "15mm",
    cover_height: str = "297mm",
    header_text: str = "",
    footer_text: str = "本报告仅作研究参考，不构成任何投资建议",
    base_bank: str | None = None,        # 触发按行 logo/palette 自动选取
    runtime_acknowledged: bool = False,  # 必填：表明已阅读 RUNTIME.md
) -> str:
    """渲染 HTML 并生成 PDF，返回 PDF 路径。"""
```

### `scripts/pdf_validator.py::validate_pdf()`

```python
def validate_pdf(
    pdf_path: str,
    *,
    logo_base64: str,
    min_pages: int = 8,
    max_pages: int = 30,
    output_check_dir: str | None = None,
) -> dict:
    """执行 5 项校验，返回 {"passed": bool, "checks": [...]}。"""
```

### `scripts/vis_asset_builder.py`

```python
def build_vis_assets(
    annual_report_pdf: str,
    output_dir: str,
    *,
    bank_name: str = "",
) -> dict:
    """执行 P0-1 ~ P0-4，返回 {"logo_path": ..., "palette_path": ..., "status": "ok|degraded"}。"""

def verify_vis_assets(assets_dir: str) -> dict:
    """P0-5 验收门禁，返回 {"passed": bool, "details": [...]}。"""
```

## 2. 典型调用链

```
skill4 → 生成 insight_result.json
      → release.py 在打包前把共享 PDF Runtime 注入 skill4/_vendor/pdf_report_builder_runtime/
      → skill4 从本地 vendored runtime 调用 build_report(
            ctx=insight_result.json,
            template_path="<当前 skill 根目录>/assets/report_template.html",
            style_overrides_path="<当前 skill 根目录>/assets/style_overrides.css",
            base_bank=ctx.short_name,
            runtime_acknowledged=True,
            meta={
              "kicker": "SKILL 3 · STRATEGIC INSIGHT",
              "title": "同业战略洞察报告",
              "output_name": "同业战略洞察报告.pdf",
              "margin_top": "25mm",
              "margin_bottom": "16mm",
            }
         )
```

## 3. 目录约定

### 源码态（仓库内共享）

```
shared/pdf-report-builder-runtime/
├── RUNTIME.md                             # 主规约
├── references/                            # 分册附录（渐进式加载）
├── assets/
│   ├── style_guide.css                    # 基础 CSS 变量 + 排版规则
│   ├── base_template.html                 # Jinja2 骨架模板
│   └── header_footer.html                 # Playwright 页眉页脚片段
├── config/
│   └── p0_vis_checklist.yaml              # P0 VIS 资产验收清单
└── scripts/
    ├── paths.py                           # 共享路径模块
    ├── bank_context.py                    # 基准行解析
    ├── build_by_bank_vis.py               # 按行 VIS 构建 CLI
    ├── asset_quality.py                   # 10 项质量审计
    ├── llm_subagent_logo_fetcher.py       # LOGO ingest 工具
    ├── vis_asset_builder.py               # P0 自动化
    ├── html_to_pdf.py                     # 核心渲染引擎
    └── pdf_validator.py                   # 5 项 PDF 校验
```

### 执行态（vendor 注入到业务 Skill）

```
skills/skill4-strategic-insight/
├── assets/
│   ├── report_template.html               # 继承 base_template.html
│   └── style_overrides.css                # 业务专属组件
├── _vendor/
│   └── pdf_report_builder_runtime/        # pack/publish 前由 release.py 自动注入
│       ├── RUNTIME.md
│       ├── references/                    # 附录（vendor 时一并注入）
│       ├── assets/
│       ├── config/
│       └── scripts/
└── config/                                # pack/publish 前由 shared/config-sources 生成
```

### 产物

```
~/RetailAnalysis/report_assets/              # VIS 资产（与 skill3/4/5 共享）
├── annual_report/<bank>_<year>_annual_report.pdf
├── by_bank/<bank_short>/                    # 按行隔离
│   ├── logo/{logo.png, logo_base64.txt, logo_source.txt}
│   ├── vis/{cover,toc,finance}-*.png, palette.json
│   └── brand.yaml                           # 采集来源与交叉校验记录
└── legacy/                                  # 历史共享资产（向后兼容）

~/RetailAnalysis/output/<bank_short>/        # 按行产物
├── <report_name>.html
├── <output_name>.pdf
└── pdf_check/skill<N>-*.png
```

## 4. 业务 Skill 的改造要求

skill3/4/5 的 SKILL.md 中：

1. **删除** P0 流程详细描述（保留一句话引用本 Runtime）
2. **删除** 分两次导出 + pypdf 合并的详细流程
3. **删除** 5 项校验的详细规则
4. **保留** 报告结构（章节数、内容描述）
5. **保留** 封面 kicker、文件名、业务专属组件说明
6. **新增** 引用本 Runtime 的调用示例
7. **调用路径改为当前 Skill 自身目录**：`template_path` / `style_overrides_path` 一律指向当前业务 Skill 的 `assets/`
8. **禁止运行时跨 Skill 互读文件**：skill3/4/5 不得在运行时直接访问共享源码目录；公共运行时代码由 `release.py` 在打包前注入 `_vendor/pdf_report_builder_runtime/`

## 5. 依赖

- Python 3.10+
- jinja2
- playwright
- pypdf（或 PyPDF2）
- Pillow（PDF 校验与 VIS 资产构建）

## 6. 运行时临时脚本命名与清理约束

> **详细规范见 `skills/skill1-standard-data-extraction/references/01_directory_and_runtime.md` → 第 4 节。此处仅列本 Runtime 的强制要点。**

1. Agent/SubAgent 为单次任务临时撰写的 Python/Shell 脚本，**必须**命名为 `_runtime_generate_<用途>_<时间戳>.py`
2. 落盘位置优先：`~/RetailAnalysis/work/` 或 `~/RetailAnalysis/data/partial/`，**严禁**放入 `shared/pdf-report-builder-runtime/scripts/`
3. 任务完成（HTML/PDF 产物写入 `~/RetailAnalysis/output/` 并经用户验收）后，**立即删除**该临时脚本
4. 本 Runtime 已沉淀的**正式脚本**不在此列：`html_to_pdf.py`、`pdf_validator.py`、`vis_asset_builder.py`、`paths.py`、`bank_context.py`、`build_by_bank_vis.py`、`asset_quality.py`、`llm_subagent_logo_fetcher.py`
5. 兜底：`_runtime_generate_*` 已写入 `.gitignore`；`scripts/cleanup_runtime_scripts.py` 可批量清理
