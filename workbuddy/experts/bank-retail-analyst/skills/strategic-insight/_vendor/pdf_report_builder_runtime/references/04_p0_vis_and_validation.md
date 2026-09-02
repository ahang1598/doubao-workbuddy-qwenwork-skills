# PDF Runtime · 附录 04：P0 VIS 前置流程 + Step A~E 生成流程 + 5 项校验

> **触发阅读条件**：首次构建 VIS 资产、排查 P0 验收失败、排查 PDF 分页/LOGO/承接页异常时。

## 1. P0 强制前置流程（视觉识别资产）

> **未固化 VIS 资产，严禁开始 PDF 生成**。所有视觉资产统一放在 `~/RetailAnalysis/report_assets/`（不放仓库）。

**必须按顺序执行**：

| 步骤 | 动作 | 产物 | 阻断 |
|---|---|---|---|
| P0-1 | 确定基准行（**用户必须指定**），复制/下载其最新年报 PDF 到 `~/RetailAnalysis/report_assets/annual_report/` | `<bank>_<year>_annual_report.pdf`（页数 >100） | ✅ |
| P0-2 | 用 `pdftocairo -png -r 300` 渲染封面 + 目录页 + 财务数据页 | `~/RetailAnalysis/report_assets/vis/cover-*.png` 等 | ✅ |
| P0-3 | 用 `pdfimages -all` / 封面裁剪提取 LOGO；Pillow 做透明背景；升采样至高度 ≥ 200px | `logo/logo.png`、`logo_base64.txt`、`logo_source.txt` | ✅ |
| P0-4 | Pillow 多页像素分析得主红色 + 辅金色；固化 CSS 变量 | `vis/palette.json` | ✅ |
| P0-5 | **P0 验收门禁**：逐项勾选 LOGO 尺寸 / 背景透明 / palette 非空 / 页数充分 | TaskList 6 项全部通过 | ✅ |

**严格禁止**：
- 自行绘制 / AI 生成 LOGO
- 使用搜索引擎下载的模糊素材
- 在 CSS/HTML 中硬编码示例色值（必须引用 `palette.json`）

**降级规则**：若年报 PDF 不可获取，必须先告知用户并获得确认，改用"银行官方名称标准字体排版"替代 LOGO，并在免责区注明。

## 2. 生成流程（Step A~E）

```
Step A  数据准备：业务 Skill 生成 ctx JSON → 调用共享 PDF Runtime

Step B  HTML 渲染：runtime 读 base_template.html + 业务 report_template.html
        + 注入 CSS（base style_guide.css + 可选 overrides.css）
        + 注入 logo_base64 + palette.json
        → 输出 ~/RetailAnalysis/output/<report_name>.html

Step C  PDF 渲染：Playwright headless Chromium 分两次导出 + pypdf 合并
        ─ 第 1 次（封面 PDF）：page_ranges="1"
          · margin: 0mm (四边)
          · display_header_footer: False
          · .cover 高度 = 296mm（skill4）或 297mm（skill3 / skill5）
          · 输出 ~/RetailAnalysis/output/_tmp_<skill>_cover.pdf
        ─ 第 2 次（正文 PDF）：page_ranges="2-"
          · margin: top={{ margin_top | default('22mm') }},
                    bottom={{ margin_bottom | default('15mm') }},
                    left=right=0mm
          · display_header_footer: True
          · headerTemplate / footerTemplate 内联构造
          · 输出 ~/RetailAnalysis/output/_tmp_<skill>_body.pdf
        ─ 合并：pypdf 按 封面 + 正文 顺序拼接
          → 输出 ~/RetailAnalysis/output/<output_name>.pdf
          → 删除 _tmp_ 文件
        · printBackground: true
        · waitForLoadState: networkidle

Step D  5 项校验（任一不通过必须修复并重渲染）
        ① LOGO 校验：封面顶部偏中区非白像素 ≥ 1%；
                     正文首页页眉左上非白像素 ≥ 0.5%
        ② 分页校验：pdfinfo 读取页数，校验在合理区间
        ③ 布局校验：逐页整页采样，非白像素 < 0.5% 视为可疑空页
        ④ 承接页页眉校验：跳过封面，对每一正文页截取顶部 0~130px，
                         确认非全白
        ⑤ 封面干净度校验：封面顶部非白像素 ≤ 5%，
                         验证封面未塞入页眉元素

Step E  落盘 PDF；校验图归档到 ~/RetailAnalysis/output/pdf_check/<skill>-*.png
```

## 3. 参数化差异

| 参数 | skill3 默认值 | skill4 默认值 | skill5 默认值 | 说明 |
|---|---|---|---|---|
| `margin_top` | 25mm | 22mm | 22mm | 正文页顶部 margin |
| `margin_bottom` | 16mm | 15mm | 15mm | 正文页底部 margin |
| `cover_height` | 296mm | 297mm | 297mm | 封面高度 |
| `logo_height` | 88px | 94px | 94px | 封面大 LOGO 高度 |
| `logo_width` | auto | 305px | 305px | 封面大 LOGO 宽度 |
| `page_range` | [8, 30] | [8, 30] | [10, 30] | 分页校验合理区间 |
