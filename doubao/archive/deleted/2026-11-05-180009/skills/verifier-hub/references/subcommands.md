# verifier 子命令完整参考

58 个子命令，分 8 个家族。调用形式统一为 `verifier <family> <subcmd> [args]`，
每次输出一个 JSON 对象。参数的权威来源是 `verifier <family> <subcmd> --help`，
本文件给出用途和一条可直接改用的示例。

---

## file — 通用文件操作（4）

| subcmd          | 说明 | 典型调用 |
| --------------- | ---- | -------- |
| `artifact-list` | 递归列目录下所有文件 + 类型分类 | `verifier file artifact-list workspace/artifacts/` |
| `validate`      | 文件存在 + 用对应库能成功打开 | `verifier file validate report.docx --expected-ext .docx` |
| `extract-text`  | 任意文件抽纯文本（xlsx/docx/pdf/pptx/text） | `verifier file extract-text report.pptx --max-chars 5000` |
| `count`         | 目录下文件数 / 总字节（可 ext 过滤） | `verifier file count workspace/artifacts/ --ext .xlsx,.csv` |

---

## xlsx — Excel 工作簿（read-only，12）

| subcmd          | 说明 | 典型调用 |
| --------------- | ---- | -------- |
| `list-sheets`   | sheet 名 + 维度 | `verifier xlsx list-sheets f.xlsx` |
| `get-value`     | 取某 cell 值（默认 data_only） | `verifier xlsx get-value f.xlsx --sheet Summary --cell C5` |
| `assert-value`  | 比较 cell 值与 expected（带 tol） | `verifier xlsx assert-value f.xlsx --sheet 'P&L' --cell F12 --expected 365.44 --tol-abs 1.0` |
| `get-formula`   | 取 cell 公式文本 | `verifier xlsx get-formula f.xlsx --sheet 'P&L' --cell F12` |
| `eval-formula`  | 用相邻 cell 当输入回算 SUM/AVERAGE/+-*/ 并与 cached 值对比 | `verifier xlsx eval-formula f.xlsx --sheet 'P&L' --cell F12 --tol-abs 0.01` |
| `find-cell`     | 用 regex 找 cell | `verifier xlsx find-cell f.xlsx --sheet 推导计算 --regex '限界利益'` |
| `sheet-shape`   | 行数 × 列数（可去尾空） | `verifier xlsx sheet-shape f.xlsx --sheet Summary --ignore-empty` |
| `header-check`  | 第一行是否包含期望表头（strict / subset） | `verifier xlsx header-check f.xlsx --sheet 参数输入 --expected 项目 数值 单位 --mode subset` |
| `nonempty-rows` | 范围内非空行数 | `verifier xlsx nonempty-rows f.xlsx --sheet 推导计算 --range A2:F100` |
| `style-check`   | 字体粗细 / 填充色 / 数字格式 | `verifier xlsx style-check f.xlsx --sheet 推导 --cell A1 --expect-bold true --expect-fill C0C0C0 --expect-number-format '0.00%'` |
| `sum-range`     | 数值范围求和（报告非数值 cell） | `verifier xlsx sum-range f.xlsx --sheet 推导 --range B2:B30` |
| `column-format` | 范围内**所有**非空 cell 共享同一 number_format（exact 或 regex） | `verifier xlsx column-format f.xlsx --sheet Revenue --range F2:F100 --expected-regex '\$\|USD'` |

---

## docx — Word 文档（read-only，12）

| subcmd            | 说明 | 典型调用 |
| ----------------- | ---- | -------- |
| `outline`         | 列 H1/H2/H3 标题 | `verifier docx outline contract.docx --max-level 3` |
| `section-text`    | 抽取某 heading 下的章节正文 | `verifier docx section-text contract.docx --heading-regex '区位优势'` |
| `count-chars`     | 总字符数（含 CJK 拆分） | `verifier docx count-chars contract.docx` |
| `table-list`      | 列所有表（index / 行 / 列 / 首行预览） | `verifier docx table-list contract.docx` |
| `table-field`     | 读某表某 cell（行号或行表头 + 列号） | `verifier docx table-field contract.docx --table-index 0 --row-header '甲方' --col 1` |
| `has-revisions`   | 检测修订（insertions/deletions）和评论 | `verifier docx has-revisions contract.docx` |
| `check-clauses`   | 检查所有期望条款标题是否存在（subset 语义） | `verifier docx check-clauses contract.docx --expected '违约责任' '保密条款' '签署' --match contains` |
| `signature-block` | 检测签字 / 盖章 / `_____` 块 | `verifier docx signature-block contract.docx` |
| `layout-compare`  | shape 检查（min/max headings/paragraphs/tables） | `verifier docx layout-compare contract.docx --min-headings 5 --min-tables 1` |
| `page-count`      | 页数，见下方说明 | `verifier docx page-count memo.docx --max-pages 1` |
| `count-images`    | 内联 + 浮动图片总数（含 header/footer）；可选 `--min` | `verifier docx count-images report.docx --min 1` |
| `page-setup`      | 各 section 的页面尺寸 + 方向；可选 `--expect-orientation` | `verifier docx page-setup chart.docx --expect-orientation landscape` |

### `docx page-count` 的三种 method

- `--method auto`（默认）：先试 LibreOffice headless 转 PDF 数页（精确），
  失败或缺 LibreOffice 时**自动退到** XML 启发式，并在结果的
  `soffice_fallback_reason` 字段里写明退化原因。
- `--method soffice`：强制走 LibreOffice，缺失时直接返回 `DEP_MISSING`。
  可以用 `--soffice <path>` 手动指定二进制位置，绕过 PATH 查找。
- `--method heuristic`：只用 XML 启发式，不调外部程序。
  依据 `<w:lastRenderedPageBreak/>`、显式分页符、非连续 section break 三类信号，
  结果里的 `accuracy` 字段会说明这次估算是精确还是近似。

---

## pdf — PDF 文档（read-only，4）

| subcmd         | 说明 | 典型调用 |
| -------------- | ---- | -------- |
| `pages`        | 页数 + 每页 width/height + 方向；可选 `--expect-orientation` / `--min-pages` / `--max-pages` | `verifier pdf pages plot.pdf --expect-orientation landscape` |
| `text-dump`    | 指定页范围抽文本 | `verifier pdf text-dump report.pdf --start 1 --end 3 --max-chars 5000` |
| `cjk-check`    | 是否嵌入 CJK 字体 + 抽样页 CJK 字符比例 | `verifier pdf cjk-check report.pdf --sample-pages 5` |
| `count-images` | 全文图片总数；`--per-page` 给逐页分布；`--min` 断言 | `verifier pdf count-images cost_breakdown.pdf --min 1` |

pdf 家族按 `pymupdf` → `pdfplumber` → `pypdf` 的顺序选用可用的读取库，
结果里的 `backend` 字段写明这次实际用的是哪一个。

---

## pptx — PowerPoint 演示文稿（read-only，4）

| subcmd         | 说明 | 典型调用 |
| -------------- | ---- | -------- |
| `list-slides`  | 每张 slide 的 index/title/n_shapes + has_picture/chart/table | `verifier pptx list-slides deck.pptx` |
| `slide-text`   | 抽取某张 slide 全部文本（`--slide N`）或所有（`--all`） | `verifier pptx slide-text deck.pptx --slide 3 --max-chars 4000` |
| `find-slide`   | 按 regex 找第一张匹配的 slide（可 `--title-only`） | `verifier pptx find-slide deck.pptx --regex '^Executive Summary'` |
| `count-images` | 全 deck 图片 / 图表总数（可 `--per-slide`） | `verifier pptx count-images deck.pptx --per-slide` |

---

## text — 文本 / Markdown 检查（只用标准库，9）

| subcmd              | 说明 | 典型调用 |
| ------------------- | ---- | -------- |
| `must-contain`      | all/any of `--terms` 在文件里 | `verifier text must-contain --file report.md --terms 竞争 毛利率 --mode all` |
| `must-not-contain`  | NONE of `--terms` 在文件里（黑名单守卫） | `verifier text must-not-contain --file report.md --terms 内部代号 PRIVATE` |
| `count-matches`     | 单 regex 出现次数 + 采样位置 | `verifier text count-matches --file report.md --regex 'GMV.*?亿'` |
| `section-length`    | 某 MD heading 下章节字数（min/max 阈值） | `verifier text section-length --file report.md --heading-regex '执行摘要' --min-chars 200` |
| `lang-ratio`        | CJK 字符占非空白字符的比例 | `verifier text lang-ratio --file report.md` |
| `citation-check`    | 找 URL / `[1]` / `(Doe, 2024)` 等引用标记 | `verifier text citation-check --file report.md` |
| `placeholder-audit` | 找残留占位符（TODO / TBD / `<XXX>` / `{{...}}` 等） | `verifier text placeholder-audit --file report.md` |
| `count-list-items`  | 列表项计数，可选 `--heading-regex` 限定段；`--expected/--min/--max` 断言 | `verifier text count-list-items --file report.md --heading-regex 'Cost Drivers' --expected 4` |
| `date-extract`      | 抽取并归一化所有日期（ISO/US/Month-D-Y/D-Month-Y）；可选 `--expected` | `verifier text date-extract --file soap_note.md --expected 2024-03-01` |

CRLF 和 LF 换行的输入产出完全相同的结果，行号统计也一致，不需要预先转换换行符。

---

## archive — ZIP 归档（read-only，只用标准库，2）

| subcmd              | 说明 | 典型调用 |
| ------------------- | ---- | -------- |
| `zip-list`          | 列归档内条目（name/size/kind），可 `--ext .wav,.mp3` 过滤 | `verifier archive zip-list bundle.zip --ext .wav` |
| `zip-check-entries` | 断言所有 `--expected` 条目存在（subset；mode=contains/exact/regex） | `verifier archive zip-check-entries bundle.zip --expected master.wav guitars.wav synths.wav --mode contains` |

---

## rubric — 高层 DSL（推荐路径，11）

`rubric` 把常见的「一条要求一个调用」场景封装好，省去自己 stitch 多个低层家族。
返回值在 `result` 里统一带 `passed` 和 `evidence_quote`。

| subcmd                    | 说明 | 典型调用 |
| ------------------------- | ---- | -------- |
| `check-file-format`       | 文件存在 + 扩展名匹配 + 用对应库能打开 | `verifier rubric check-file-format report.docx --expected-ext .docx` |
| `check-section-exists`    | docx 章节存在 + 正文 ≥ min-chars | `verifier rubric check-section-exists contract.docx --heading-regex '区位优势' --min-chars 80` |
| `check-table-field`       | docx 表 cell 等于 expected（exact/contains/regex/numeric） | `verifier rubric check-table-field contract.docx --table-index 0 --row-header '总价' --col 2 --expected 1200000 --mode numeric --tol-rel 0.01` |
| `check-keywords`          | all/any/none of `--terms` 在文本里 | `verifier rubric check-keywords report.md --terms 竞争 毛利率 --mode all` |
| `check-numeric`           | 数值匹配 expected ± tol，源可以是 xlsx cell 或文本 regex 捕获组 | `verifier rubric check-numeric f.xlsx --source xlsx --sheet 推导 --cell F12 --expected 365.44 --tol-abs 1.0` |
| `check-formula`           | xlsx 公式与引用 cell 计算一致 | `verifier rubric check-formula f.xlsx --sheet 推导 --cell F12 --tol-abs 0.01` |
| `check-excluded`          | NONE of `--banned` 在文本里 | `verifier rubric check-excluded report.md --banned 内部代号 PRIVATE` |
| `check-revisions`         | docx 无修订标记 / 评论 | `verifier rubric check-revisions contract.docx` |
| `check-signature-block`   | docx 含签字 / 盖章块 | `verifier rubric check-signature-block contract.docx` |
| `check-no-placeholder`    | 文本无 TODO / `<XXX>` / `{{...}}` 占位 | `verifier rubric check-no-placeholder report.md` |
| `check-cross-consistency` | 同一指标在多文件中数值一致（±tol）；source 形如 `KIND:k1=v1;k2=v2`，**分号分隔**以免和 regex 里的逗号冲突 | `verifier rubric check-cross-consistency --source 'xlsx:file=data.xlsx;sheet=Sum;cell=B2' --source 'text:file=memo.md;regex=Total: \$([0-9,.]+)' --tol-rel 0.01` |
