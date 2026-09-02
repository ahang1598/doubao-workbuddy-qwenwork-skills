# 非 DOCX 输入的入库设计（共享内核 · 本副本已分叉）

> **现状（2026-08-07 起）**：本技能**不再自带本地 PDF/OCR 转换链**。
> `scripts/pdf_intake.py` 已移除，随之移除 8 个仅供其使用的第三方依赖
> （Pillow / easyocr / PyMuPDF / numpy / pdf2docx / pdf2image / pdfplumber /
> pytesseract）。`multilingual-contract-review` 已先行做同样的分叉。
>
> **不要再按旧版描述去调用 `pdf_intake.py`——该脚本不存在。**

## 为什么移除

1. **从未接入主流程**：旧文档自述「集成点（两技能 Step 0，**待接入**）」，
   `pdf_intake.py` 全程无任何脚本 import、未登记进 manifest、SKILL.md 与
   runtime-playbook 均未引用。它是一份从未落地的设计实现。
2. **与平台约束冲突**：`fadada-special-ocr` 明令平台内部 OCR API 是唯一允许的
   OCR 方式、严禁本地替代；`pdf-generation-editing-tool` 明令纯文本提取用系统
   内置读取工具。技能自带本地 OCR 链属重复实现且违反上述约束。
3. **依赖面代价**：8 个重依赖（含 easyocr/PyMuPDF）长期未安装，使技能在
   skill-evaluator S1-025 依赖可用性检查上持续失败，掩盖真实的依赖问题。

## 现在如何处理非 DOCX 输入

入口由 `scripts/review_intake.py` 的**格式门禁**统一把关（按文件头判定，不信后缀）：

| 输入 | 处理 |
|---|---|
| `.docx`（OOXML） | 直通 |
| `.doc` / `.wps` / `.rtf` | 本机装有 LibreOffice 时自动 `soffice --headless --convert-to docx`；否则升级给用户 |
| PDF / 扫描件 / 图片 | 返回 `status: escalate`，指向平台正规链路，**本技能不自行转换** |
| 其他 | 同上，结构化拒绝 |

PDF/扫描件的正规链路（与 multilingual 一致）：

| 能力 | 正规路径 |
|---|---|
| 读数字版 PDF 文本 | 系统内置读取工具（原生支持 PDF） |
| 扫描件 / 图片 OCR | `fadada-special-ocr`（平台内部 OCR API） |
| 文本 / Markdown → DOCX | `word-document-processing` |

取到文本并转成 `.docx` 后，再以该转换稿走正常审查流程；交付时须声明红线建立在
转换稿之上，关键数字/金额/期限需对照原件核对。

## 保留的设计结论（供未来参考）

旧方案中仍然成立的一条判断：**对错误转换的文本做审查 = 输出错误法律结论
（漏条款、错金额）= 比「无法审查」更危险**。故低置信不降级硬跑，而是熔断转人工——
这与技能既有的失败分级（`user_action_required` 预算 0，直接升级给用户）一致。
