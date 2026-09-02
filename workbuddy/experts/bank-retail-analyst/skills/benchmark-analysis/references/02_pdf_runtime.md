# Skill 3 · 附录 02：PDF 生成、基准行解析与 LOGO 校验

> **触发阅读条件**：任何 PDF 生成任务、LOGO 验证、按行视觉资产调整、`build_report` 调用前必读。

## 1. 生成 PDF 前必读：RUNTIME.md（2026-04-29 强制）

> **Agent 必须在首次触发 PDF 生成前完整 `read_file` 以下文件**，否则可能违反模板渲染完整性守卫、rich_text 过滤器、按行视觉资产等规约，导致 PDF 事故。

**必读路径**（按加载优先级）：

1. **执行态（当前 vendor 环境，优先）**：`skills/skill3-benchmark-analysis/_vendor/pdf_report_builder_runtime/RUNTIME.md`
2. **源码态（开发仓库）**：`shared/pdf-report-builder-runtime/RUNTIME.md`

RUNTIME.md 覆盖以下**本 SKILL.md 不再重复**的主题（单一本源）：

- 模板渲染完整性守卫（拒绝裸 Jinja 残留）
- `rich_text` 过滤器白名单
- 基准行（base_bank）解析与按行视觉资产隔离
- 自动下载 + 多级质量核验（grade A/B/C/F 分级）
- P0 VIS 资产验收 / 5 项 PDF 校验
- 分两次导出 + pypdf 合并 / margin / cover_height / header_template

**调用约定**：Agent 读完 RUNTIME.md 后，调用 `build_report(..., runtime_acknowledged=True)` 表明已确认遵守规范；否则运行时会在 stderr 打印警示（不阻断）。

## 2. 基准行（base_bank）解析规则

> **目的**：skill3/4/5 均支持**任意基准行**，不再默认只为基准行生成。每次运行必须显式确定基准行，并把产物和视觉资产按行隔离，避免互相覆盖。

### 2.1 解析优先级（高 → 低）

1. **显式调用参数**：`build_report(base_bank="某某")` / CLI `--base-bank 某某`
2. **环境变量**：`RETAIL_ANALYSIS_BASE_BANK=某某`
3. **用户自然语言 query**：Agent 从用户提问中抽取银行名（支持"光大银行"、"CEB"、"601818"等别名，见 `shared/config-sources/common/banks.yaml::banks[*].aliases`）
4. **无默认值**：三者均未命中时抛出 `ValueError`，Agent 必须主动询问用户指定基准银行

解析在 `shared/pdf-report-builder-runtime/scripts/bank_context.py` 中统一实现：

```python
from bank_context import resolve

ctx = resolve(base_bank=None, query="某某银行 2025 年财报数据分析")
# ctx.short_name == "某某"
# ctx.output_dir  == ~/RetailAnalysis/output/某某
# ctx.palette_json == ~/RetailAnalysis/report_assets/by_bank/某某/vis/palette.json
# ctx.primary_color == "#7F2987"（官方紫色，来自 banks.yaml）
```

### 2.2 按行产物目录（强制）

所有产物**必须**写到 `~/RetailAnalysis/output/<bank_short>/`：

| 基准行 | 目录 |
|---|---|
| 基准行 | `~/RetailAnalysis/output/基准行/同业财报数据分析.pdf` |
| 某某 | `~/RetailAnalysis/output/某某/同业财报数据分析.pdf` |
| 某甲 | `~/RetailAnalysis/output/招商/同业财报数据分析.pdf` |

**历史产物迁移**：旧的根目录报告应依据报告内 `base_bank` 迁移到 `~/RetailAnalysis/output/<bank_short>/`；新产物**禁止**直接写到 `output/` 根目录。

### 2.3 按行视觉资产（强制）

`report_assets/by_bank/<bank>/`（由 `build_by_bank_vis.py` 维护）是 PDF 生成时**唯一允许**使用的视觉资产目录：

```
~/RetailAnalysis/report_assets/by_bank/某某/
├── logo/logo.png, logo_base64.txt, logo_source.txt
├── vis/palette.json, cover-*.png, toc-*.png, finance-*.png
└── brand.yaml    # 采集来源、交叉校验记录（ΔE、身份校验）
```

资产就绪度由 `bank_context.BankContext.assets_ready()` 判定。PDF 生成前 Agent 必须先运行：

```bash
python3 _vendor/pdf_report_builder_runtime/scripts/build_by_bank_vis.py --bank 某某
```

构建逻辑（按优先级）：
1. **自动提取**：若 `report_assets/annual_report/<bank>_<year>_annual_report.pdf` 存在，从封面提取 LOGO，从多页像素分析提取 palette，并与 `banks.yaml::brand_identity.primary_official` 做 CIE76 **ΔE 交叉校验**
2. **身份校验后的 legacy 克隆**：legacy 全局资产同时满足 ΔE<15 且 `logo_source.txt` 包含该行识别词时，才克隆过来
3. **合成兜底**：上述均不可用时，用 `banks.yaml` 的官方 primary/accent 合成 palette.json，**LOGO 留空**，base_template 自动降级为"官方名称文字替代"。**严禁**自行绘制 / AI 生成 / 搜索引擎拉图

## 3. `build_report` 调用约定

```python
from html_to_pdf import build_report
from bank_context import resolve

ctx = resolve(base_bank=base_bank_param, query=user_query)
build_report(
    ctx=report_ctx,
    template_path=str(skill_dir / "assets" / "report_template.html"),
    output_html=str(ctx.output_path("benchmark_analysis_report.html")),
    output_pdf=str(ctx.output_path("同业财报数据分析.pdf")),
    style_overrides_path=str(skill_dir / "assets" / "style_overrides.css"),
    base_bank=ctx.short_name,          # 触发 per-bank logo / palette 自动选取
    header_text=f"{ctx.full_name}视角 · 同业财报数据分析",
    runtime_acknowledged=True,         # 必填：表明已阅读 _vendor/.../RUNTIME.md
)
```

`build_report` 在渲染前会：
- 从 `by_bank/<bank>/vis/palette.json` 加载 palette（变量驱动 CSS）
- 从 `by_bank/<bank>/logo/logo_base64.txt` 加载封面 LOGO 与页眉 LOGO
- 如 per-bank 资产缺失，自动降级到 `banks.yaml::brand_identity` 合成的官方色 palette
- **禁止**使用 legacy 全局资产与当前基准行不匹配时的资产混用

## 4. 面向 Agent 的工作流速查

1. 从用户 query 或显式参数解析基准行 → `bank_context.resolve()`
2. 确认 `ctx.assets_ready()`；若否则先跑 `build_by_bank_vis.py --bank <short>`
3. 进入 skill3 正常分析流程，所有中间产物照旧写 `data/partial/`
4. 最终报告 md / result.json / html / pdf 全部写入 `ctx.output_dir`（= `output/<bank>/`）
5. 向用户汇报时带上绝对路径（`~/RetailAnalysis/output/<bank>/...`）

## 5. LOGO 校验与修正（2026-04-30 强制）

> **背景**：2026-04-30 故障——招商银行 PDF 封面使用了 wikipedia infobox SVG（归一化后 1622×400，含 64% 透明区域）的非官方 LOGO。根因是 `brand.yaml.logo_source == "fallback"` 却未阻止 PDF 使用它。

### PDF 生成前 LOGO 必检 3 项

```python
from pathlib import Path
from PIL import Image
import yaml

def validate_bank_logo(bank_short: str) -> list[str]:
    """返回违规清单；空列表表示通过。"""
    issues = []
    base = Path.home() / "RetailAnalysis" / "report_assets" / "by_bank" / bank_short
    brand_yaml = base / "brand.yaml"
    logo_png = base / "logo" / "logo.png"
    logo_source_txt = base / "logo" / "logo_source.txt"

    # 1) brand.yaml 必须存在且 logo_source ≠ fallback / main_agent_direct
    if not brand_yaml.exists():
        issues.append(f"brand.yaml 缺失：{brand_yaml}")
    else:
        meta = yaml.safe_load(brand_yaml.read_text()) or {}
        src = meta.get("logo_source")
        if src in (None, "fallback", ""):
            issues.append(f"logo_source={src!r} 属 fallback，PDF 封面不应使用此 LOGO")

    # 2) logo_source.txt 必须包含该行的 identity token
    tokens = {
        "招商": ["招商", "CMB", "600036", "China Merchants"],
        "基准行": ["基准行", "CITIC", "601998"],
        "平安": ["平安", "Ping An", "000001"],
        "兴业": ["兴业", "Industrial", "601166", "CIB"],
        "浦发": ["浦发", "SPDB", "600000", "Pudong"],
        "光大": ["光大", "CEB", "601818", "Everbright"],
        "民生": ["民生", "CMBC", "600016", "Minsheng"],
    }.get(bank_short, [bank_short])
    if logo_source_txt.exists():
        txt = logo_source_txt.read_text()
        if not any(t in txt for t in tokens):
            issues.append(f"logo_source.txt 中未出现 {bank_short} 任何 identity token")

    # 3) LOGO 像素基本特征：不得几乎全透明、宽高比需合理
    if not logo_png.exists():
        issues.append(f"logo.png 不存在：{logo_png}")
    else:
        img = Image.open(logo_png)
        w, h = img.size
        if img.mode == "RGBA":
            alpha = img.split()[-1]
            non_transparent = sum(1 for px in alpha.getdata() if px > 16) / (w * h)
            if non_transparent < 0.10:
                issues.append(f"LOGO 非透明像素仅 {non_transparent:.1%}，视觉太弱")
        ratio = w / h
        if not (1.5 <= ratio <= 8.0):
            issues.append(f"LOGO 宽高比异常 {ratio:.2f}（建议 2~6 之间）")

    return issues
```

### 触发时机

- **每次 `build_report(...)` 调用前**，必须先 `validate_bank_logo(base_bank)`：
  - 返回空列表 → 继续生成
  - 返回非空违规 → **先 `log.warning` 记录全部违规**，然后：
    - 若 `logo_source == "fallback"` 或"非透明像素 <10%" → 走 `base_template` 的"官方名称文字替代"降级（让 `load_logo_base64` 返回空串），**禁止**用问题 LOGO 直接上 PDF
    - 若仅是 identity token 缺失但像素正常 → 记录警告，允许继续

### 修复 LOGO 的正确流程

当校验失败且当前只有 fallback LOGO 时：

1. 从 **`shared/config-sources/common/banks.yaml::banks[*].logo_url`**（如有配置）或该行**官网**直接拉取官方高清 LOGO（不接受 wikipedia / 搜索引擎拼图）
2. 通过 `_vendor/pdf_report_builder_runtime/scripts/build_by_bank_vis.py --bank <short>` 重建 `report_assets/by_bank/<bank>/`
3. 重跑 `validate_bank_logo`，确保通过
4. 若确实找不到合规 LOGO，**主动走文字替代降级**，并在日志中记录原因，**不要**硬塞不合规素材

## 6. PDF 交付物章节结构（固定 10 节）

1. **封面页**：大 LOGO + 标题"同业财报数据分析"+ 副标题 + meta 信息
2. **目录页**
3. **执行摘要**：5 条核心结论 + 4 张 KPI 卡片
4. **第一部分 维度一：零售业务分部营收分析**
5. **第二部分 维度二：零售信用减值损失分析**
6. **第三部分 维度三：零售营业支出分析**
7. **第四部分 维度四：零售存贷利差分析**
8. **第五部分 维度五：同业排名与变化追踪（基准行视角）**
9. **第六部分 关键发现（基准行视角）**
10. **收尾 · 数据与免责声明**

## 7. 样式规范

- **基础样式**：由共享 PDF Runtime 的 `style_guide.css` 统一提供
- **业务覆盖**：当前 Skill 的 `assets/style_overrides.css`
- **配色**：由 `~/RetailAnalysis/report_assets/vis/palette.json` 驱动
- **LOGO 尺寸**：305 × 94 px（与 skill5 一致）
- **排名变化标签**：绿色=差距缩小 / 红色=差距扩大 / 灰色=未变

## 8. 报告用字规范

- 标题固定为 **"同业财报数据分析"**
- 免责声明统一为 **"本报告由 AI 基于上市银行公开披露信息生成，仅供研究参考，不构成任何投资建议，亦不构成对任何个股的推荐"**
- 所有引用数据必须可溯源
- **以中文为主**：银行名称、章节标题、页眉、页脚一律中文
- 数值精度：金额"百万元"、百分比 2 位小数、同比 `+X.XX%` / `-X.XX%`

## 9. 产物结构

```
~/RetailAnalysis/report_assets/         ← 与 skill4 / skill5 共享
├── annual_report/<bank>_<year>_annual_report.pdf
├── logo/logo.png / logo_base64.txt / logo_source.txt
└── vis/cover-*.png / toc-*.png / finance-*.png / palette.json

skills/skill3-benchmark-analysis/
├── SKILL.md
├── config/
├── scripts/
│   └── paths.py
├── assets/
│   ├── report_template.html            ← 业务模板（继承共享 PDF Runtime 的 base_template）
│   └── style_overrides.css             ← 业务覆盖样式
└── _vendor/
    └── pdf_report_builder_runtime/     ← pack/publish 前由 release.py 自动注入
```

## 10. 与 skill4 PDF 的边界

| 维度 | skill4 同业战略洞察报告 | skill3 同业财报数据分析 |
|---|---|---|
| 内容定位 | 3-5 条战略洞察 + 高频词 + 组织架构变化 | 5 维度矩阵 + 同业排名 + 差距变化追踪 |
| 输入 | `~/RetailAnalysis/data/insight_result.json` | `~/RetailAnalysis/output/<bank>/benchmark_analysis_result.json` + `...benchmark_analysis.md` |
| 输出 | `~/RetailAnalysis/output/<bank>/同业战略洞察报告.pdf` | `~/RetailAnalysis/output/<bank>/同业财报数据分析.pdf` |

> 两份 PDF 互不替代，且各自 Skill 默认生成对应 PDF。
