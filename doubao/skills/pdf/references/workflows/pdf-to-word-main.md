# PDF 转 Word · MainAgent

> 本文档只写给 MainAgent 阅读。你不需要了解 OrganizerAgent 和 SubAgent 的内部细节，也不要把它们的文档拉进上下文。

## 你在工作流中的位置

```
MainAgent（你）
  └── 启动 OrganizerAgent（黑盒，会返回合并好的 DOCX）
        └── 若干 SubAgent（对你不可见）
```

## 命中信号

用户提供 PDF 且交付要求是 `.docx` / "可编辑 Word" 时进入本工作流。以下场景**不**走本工作流：

- 源目都是 PDF
- Word 转 PDF
- 用户只把 PDF 当格式参考、要求重建一份全新的 Word

## 你要做的三件事

### 1. 启动 OrganizerAgent

使用 `create_agent` 启动 OrganizerAgent，把 PDF 路径、用户其他交付要求原样传过去，并要求它读取`pdf-to-word-organizer.md`。OrganizerAgent 会返回 DOCX 产物。

### 2. 告知用户耗时量级

重建操作比较耗时，平均大约每小时 30 页，会在 10~50 页之间波动。需告知用户耗时的大致量级，并强调会随 PDF 复杂度、服务负载等因素波动：

| PDF 页数 | 告知话术 |
|---------|---------|
| < 10 页 | 大约半小时 |
| 10 - 300 页 | 具体的小时数（按每小时 30 页估算） |
| ≥ 300 页 | 12 小时以上 |

### 3. 修复 DOCX 并交付

收到 OrganizerAgent 交付的 DOCX 后，执行修复脚本处理兼容性问题：

```bash
python scripts/repair_docx.py input.docx --output repaired.docx
```

将修复后的 DOCX 文件和交付说明一并交付给用户。
