---
name: word-document-processing
description: "用于本地 Word DOC、DOCX 或 WPS 文件需要读取、转换、OCR、版式敏感编辑或交付前结构复核，且通用 lark-doc 流程需要 Office Word 专项规则的场景。在线文档、纯内容写作或简单摘要不使用。"
---

# Word 文档专项处理与复核

## 概述
这是 lark-doc 的本地 Word 专项扩展。文件读取和编辑仍由 lark-doc 执行；本 Skill 补充 DOC/DOCX 分流、扫描页 OCR、OOXML 最小修改和确定性复核。

## 使用场景
### 应使用
- 旧版 .doc 转换、图片型 DOCX OCR。
- 需要保留模板、页眉页脚、编号、表格和合并单元格的编辑。
- 生成 DOCX 后需要包结构和视觉验收。

### 不应使用
- 飞书/豆包在线文档。
- 仅改写一段文字且不要求文件。
- PDF、Excel 或 PPT 任务。

## 核心流程
### 1. 先加载基础 Skill
使用 lark-doc 定位、读取和编辑文件；不得建立平行的通用 Word 入口。

### 2. 识别格式
区分 DOC、DOCX、扫描/图片型文档和真实模板；DOC 不按 ZIP 解包。

### 3. 冻结结构和版式
记录标题层级、表格、合并单元格、编号、页眉页脚、图片、日期和禁改字段。

### 4. 最小修改
优先通过稳定库/转换器和节点级修改；另存新文件，不覆盖源文件。

### 5. 复核交付
用 check_docx_package.py/verifier-hub 检查包结构和内容，用 artifact-preview 检查页面视觉，再使用 present_files。

## 工具与协作
- **REQUIRED BASE SKILL:** lark-doc。
- 确定性检查使用 verifier-hub；视觉检查使用 artifact-preview；交付使用 present_files。

## 安全边界
- 只陈述已读取、已执行或有来源支持的结果；未验证项必须明确标注。
- 涉及删除、覆盖、发布、系统设置、生产数据或不可逆操作时，先展示目标、影响、回滚方式并取得明确确认。
- 不得记录或输出密钥、Cookie、访问令牌、身份证号、银行卡号等敏感信息；示例使用脱敏占位符。
- 不将纯文本伪装成 .docx，不删除源文件，不静默遗漏扫描图片或表格。

## 输出与验收
- 源文件结构清单
- 新 Word 文件
- 结构/内容/视觉复核证据
- 未覆盖的 OCR 或兼容性限制

## 冒烟用例
### Should trigger
- 保持模板和表格结构修改这个 DOCX 并交付 Word
- 旧 .doc 转成 .docx 后检查包结构和版式

### Should not trigger
- 编辑飞书在线文档
- 只帮我润色一段文字，不要文件

### 边界输入
- DOCX 主要由扫描图片组成且 OCR 置信度低

## 参考文件
- `references/ooxml-minimal-edit.md`
- `scripts/check_docx_package.py`
