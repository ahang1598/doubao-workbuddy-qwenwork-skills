# PDF 合同入库转换方案（共享内核 · SSOT）

两技能此前 PDF 路径只有 `pdf2docx`，仅能转**数字文本 PDF**；对**扫描件**（无文字层）
直接产出空 docx（`Words count: 0 ... scanned pdf not supported`），对**分栏**版式读序错乱。
本方案补齐：先转标准 Word，过**文字准确性闸门**，再进入审查。实现见 `scripts/pdf_intake.py`。

## 流水线

```
PDF → ① 分类 → ② 按类转换 → ③ 文字准确性闸门 → 标准Word + manifest
                                    │
                          high/medium → 进入审查      low → 熔断（不审查）
```

### ① 分类（classify）
- **数字 vs 扫描**：PyMuPDF 读文字层字符数，`>= 40×页数` 判数字；否则有图像判扫描，无图像判空白。
- **语言**：数字版按文字层 CJK 占比判（`chi_sim+eng` / `eng`）；**扫描件无文字层无法预判 → 默认 `chi_sim+eng` 多语言 OCR**（关键修复：避免用英文 OCR 中文导致乱码误熔断）。
- **栏数**：数字版按文字块 x 中心聚类判单/双栏；扫描版交 OCR 自动版面。

### 能力探测注册表（不写死工具）
每个能力维护**优先级提供方列表**，运行时探测环境、择优、缺则回退；某能力全无提供方时清晰报错。
`python3 pdf_intake.py --probe` 查看本环境探测结果；`--prefer cap=provider` / 环境变量
`PDF_INTAKE_DISABLE=` 可强制或禁用某提供方（也用于回退测试）。

| 能力 | 提供方优先级（按序回退） |
|---|---|
| pdf_read | PyMuPDF → pdfplumber → poppler(pdftotext) |
| pdf_render | PyMuPDF → poppler(pdftoppm) → pdf2image |
| ocr | ocrmypdf → tesseract(cli/pytesseract) → easyocr |
| pdf2docx | pdf2docx（无则数字版走 reflow 兜底）|
| docx_build | python-docx → 最小 OOXML 兜底 |

### ② 按类转换（convert，方法由探测决定）
| 类型 | 方法 | 说明 |
|---|---|---|
| 数字·单栏 | 优先 `pdf2docx`，缺则 reflow | 保真最高，保留段落 |
| 数字·多栏 | 按列阅读序(左→右)提取 → 重排标准 docx | 修正分栏读序错乱 |
| 扫描件 | 探测到的 OCR 引擎加文字层/识别 → 提取 → 标准 docx | 中/英/混排；引擎缺失则熔断退4 |

输出标准 Word：中文 SimSun / 英文 Times New Roman / 11pt，每段独立，供 `review_docx.py extract` 索引。

### ③ 文字准确性闸门（verify）——核心
转换后、审查前的强制 GATE，分三档驱动行为：

| 档位 | 判据 | 行为 |
|---|---|---|
| **HIGH** | 数字版覆盖率 ≥0.92、单栏、含合同关键词 | 直接审查；声明基于转换工作副本 |
| **MEDIUM** | 扫描件 OCR 置信均值 ≥75 且低置信词 ≤15%；或多栏重排；或覆盖率 0.6–0.92 | 可审查，但把**待核对项**（金额/期限/跨栏顺序）交用户确认，报告显式声明 |
| **LOW（熔断）** | 空文档；或 OCR 置信均值 <75 或低置信词 >15%；或零合同关键词 | **禁止审查**，报告卡点，请用户提供更清晰副本或人工核对后再继续 |

判据数据：覆盖率（输出字符/数字PDF字符）、OCR 词级置信度（tesseract `image_to_data`）、
合同关键词命中、段落非空。全部写入 `manifest.json` 供留痕。

## 为什么熔断是安全要求（接 D2）
对错误转换的文本做审查 = 输出错误法律结论（漏条款、错金额）= 比"无法审查"更危险。
故低置信不降级硬跑，而是熔断转人工——与技能既有"两策略失败即停"熔断哲学一致。

## 集成点（两技能 Step 0，待接入）
在 `review_docx.py extract` 之前插入：若输入为 `.pdf` → 跑 `pdf_intake.py` → 据档位决定继续/熔断
/带待核对继续；`.doc` 仍用 soffice 转 docx；`.docx` 直接进入。详见各 SKILL.md 集成补丁。

## 依赖（软依赖，按能力探测）
不强绑单一工具：每个能力只要求**至少一个**提供方存在。当前环境探测到的优先项为
PyMuPDF / ocrmypdf / pdf2docx / python-docx / tesseract，缺某一项会自动回退到同能力的次选。
新增 OCR 引擎（如 easyocr/paddleocr）只需在 `REGISTRY["ocr"]` 注册 + 实现适配分支即可被自动发现。
