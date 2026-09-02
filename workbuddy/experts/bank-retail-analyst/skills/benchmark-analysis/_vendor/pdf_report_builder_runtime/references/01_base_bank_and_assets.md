# PDF Runtime · 附录 01：基准行解析 + 按行视觉资产 + 自动下载质量核验

> **触发阅读条件**：首次生成 PDF、配置基准行、排查 `assets_ready()` 为 False、调用 `build_by_bank_vis.py`、LOGO/palette 质量不合格时。

## 1. 基准行（base_bank）解析

见 `scripts/bank_context.py` 与 `scripts/build_by_bank_vis.py`。核心约定：

### 解析优先级（高 → 低）

1. **显式调用参数**：`build_report(base_bank="光大")` / CLI `--base-bank 光大`
2. **环境变量**：`RETAIL_ANALYSIS_BASE_BANK=光大`
3. **用户自然语言 query**：Agent 从用户提问中抽取银行名（支持"光大银行"、"CEB"、"601818"等别名，见 `shared/config-sources/common/banks.yaml::banks[*].aliases`）
4. **无默认值**：三者均未命中时抛出 `ValueError`，调用方必须确保用户已指定基准行

```python
from bank_context import resolve

ctx = resolve(base_bank=None, query="光大银行 2025 年财报数据分析")
# ctx.short_name == "光大"
# ctx.output_dir  == ~/RetailAnalysis/output/光大
# ctx.palette_json == ~/RetailAnalysis/report_assets/by_bank/光大/vis/palette.json
# ctx.primary_color == "#7F2987"
```

### 核心约定

1. 所有 PDF 产物写 `~/RetailAnalysis/output/<bank_short>/`（不再写到 `output/` 根目录）
2. 视觉资产读 `~/RetailAnalysis/report_assets/by_bank/<bank_short>/`（logo / palette / brand.yaml）
3. `build_report(..., base_bank=<short>)` 会自动：
   - 从 `by_bank/<bank>/logo/logo_base64.txt` 加载封面与页眉 LOGO
   - 从 `by_bank/<bank>/vis/palette.json` 加载配色；若与官方色不一致自动用 `banks.yaml::brand_identity.primary_official` 合成 fallback
4. **禁止**自行绘制 / AI 生成 LOGO；资产缺失时降级为"官方名称文字替代"并在 `brand.yaml` 记录

### 按行视觉资产目录

```
~/RetailAnalysis/report_assets/by_bank/光大/
├── logo/logo.png, logo_base64.txt, logo_source.txt
├── vis/palette.json, cover-*.png, toc-*.png, finance-*.png
└── brand.yaml    # 采集来源、交叉校验记录（ΔE、身份校验）
```

## 2. 自动下载 + 多级质量核验

由 `scripts/build_by_bank_vis.py` + `scripts/asset_quality.py` 提供。

### CLI 参数

| CLI 参数 | 用途 |
|---|---|
| `--bank <short>` | 指定基准行（如 `--bank 光大`） |
| `--auto-download` | 本地无年报时尝试从 `banks.yaml::annual_report_url` 下载，带 TLS legacy + curl 兜底 |
| `--manual-logo <path>` | 当自动下载受反爬阻塞时，手动指定官网下载的 PNG/JPG/SVG |
| `--audit-only` | 仅对已存在资产做质量核验，不重建 |
| `--force` | 即使已就绪也强制重建 |

### 多级质量核验

由 `asset_quality.audit()` 实现，输出到 `by_bank/<bank>/quality_report.yaml`：

| 校验项 | 严重度 | 通过阈值 |
|---|---|---|
| logo_exists | critical | logo.png 存在 |
| logo_readable | critical | Pillow 可打开 |
| identity_match | critical | logo_source.txt 含银行识别词（短名/全称/股票代码/英文缩写） |
| logo_height | major | ≥ 200px |
| logo_alpha | major | RGBA |
| logo_opaque_pct | major | 实色像素 8%~92% |
| palette_primary_delta_e | major | 与 primary_official ΔE < 25（<15 优 / <25 可接受） |
| palette_fields | major | primary/primary_dark/primary_light/accent/... 齐全 |
| logo_aspect_ratio | minor | 宽高比 1.3~6.5 |
| logo_transparent_pct | minor | 透明像素 ≥ 15% 优（≥ 5% 可接受） |

### 评级

| 等级 | 条件 |
|---|---|
| **A** | 无 critical 且无 major |
| **B** | 仅 minor 失败 |
| **C** | 仅 major 失败（无 critical） |
| **F** | 有 critical 失败 |

**`F` 级资产严禁直接用于 PDF**（html_to_pdf 会 warning，但不阻断；业务 Skill 应先修复）。

### 构建逻辑（按优先级）

1. **自动提取**：若 `report_assets/annual_report/<bank>_<year>_annual_report.pdf` 存在，从封面提取 LOGO，从多页像素分析提取 palette，并与 `banks.yaml::brand_identity.primary_official` 做 CIE76 **ΔE 交叉校验**
2. **身份校验后的 legacy 克隆**：legacy 全局资产同时满足 ΔE<15 且 `logo_source.txt` 包含该行识别词时，才克隆过来
3. **合成兜底**：上述均不可用时，用 `banks.yaml` 的官方 primary/accent 合成 palette.json，**LOGO 留空**，base_template 自动降级为"官方名称文字替代"

## 3. 典型工作流

PDF 生成前 Agent 必须先运行：

```bash
python3 _vendor/pdf_report_builder_runtime/scripts/build_by_bank_vis.py --bank 光大
```

然后检查 `BankContext.assets_ready()`：
- 返回 True → 进入 build_report
- 返回 False → 先跑 build_by_bank_vis.py，仍失败则走「附录 02 · LOGO 缺失兜底」
