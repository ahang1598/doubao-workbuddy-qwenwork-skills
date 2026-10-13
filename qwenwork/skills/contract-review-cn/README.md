# 中文合同审查工具 (Contract Review Tool)

> 专业的中文合同风险识别与修订建议工具

## 快速开始

### 1. 安装

```bash
cd /Users/mac/.openclaw/workspace/skills/contract-review-cn
pip install -r requirements.txt
```

### 2. 配置

```bash
cp config.example.json config.json
# 编辑 config.json，填入你的 API 密钥
```

### 3. 使用

```bash
# 审查合同
python scripts/contract_analyzer.py contract.pdf
```

## 核心特性

✅ **多格式支持** - PDF、Word、TXT
✅ **自动风险识别** - 智能识别潜在法律风险
✅ **修订建议** - 提供具体的修改建议
✅ **三栏对照表** - 清晰的原文/建议/原因对照
✅ **重点审查** - 专注于关键条款领域

## 审查重点

- 📝 付款条款
- ✅ 验收标准
- ⚠️ 违约责任
- 📚 知识产权
- 🔒 保密条款
- ⚖️ 争议解决
- ⚖️ 管辖法院

## 使用示例

### 命令行使用

```bash
# 审查PDF文件
python scripts/contract_analyzer.py contract.pdf

# 指定输出文件
python scripts/contract_analyzer.py contract.pdf --output report.md

# 只显示不保存
python scripts/contract_analyzer.py contract.pdf --show-only
```

### 通过OpenClaw调用

上传合同文件或发送指令：
- "让我审合同"
- "让我出修订对照表"

## 输出示例

### 风险摘要

识别出3个主要风险：
- **高风险**: 付款条件不明确，可能导致延迟付款
- **中风险**: 违约责任条款过于宽泛
- **中风险**: 争议解决方式未明确

### 三栏对照表

| 原文 | 建议修改 | 修改原因 |
|------|----------|----------|
| 付款方式：现金 | 付款方式：银行转账，汇款后5个工作日内支付 | 明确付款方式，便于实际执行 |
| 逾期付款：按日加收0.1%违约金 | 逾期付款：按日加收0.5%违约金，并赔偿对方损失 | 提高违约成本，保障权益 |

## 配置说明

```json
{
  "api_key": "your-api-key",
  "model": "zai/glm-4.7-flash",
  "temperature": 0.3,
  "focus_areas": ["payment_terms", "intellectual_property"]
}
```

详细配置请参考 [SKILL.md](SKILL.md)

## 依赖项

- PyPDF2 >= 3.0.1
- python-docx >= 1.1.0
- python-pptx >= 0.6.23
- openpyxl >= 3.1.2
- tiktoken >= 0.7.0
- langchain >= 0.1.0

## 文件结构

```
contract-review-cn/
├── SKILL.md              # 详细使用文档
├── README.md             # 本文件
├── scripts/
│   ├── contract_analyzer.py   # 主分析器
│   ├── pdf_parser.py         # PDF解析
│   └── word_parser.py        # Word解析
├── templates/
│   └── review_prompt.txt     # 审查提示词
├── requirements.txt          # 依赖列表
└── config.example.json       # 配置示例
```

## 注意事项

⚠️ **重要提示**：
- AI审查结果仅供参考，重要合同请人工审核
- API密钥请妥善保管，不要泄露
- 超长合同建议分章节审查

## 故障排除

| 问题 | 解决方案 |
|------|----------|
| PDF解析失败 | 检查是否为可搜索PDF |
| API调用失败 | 检查API密钥和网络 |
| 结果不准确 | 调整temperature参数 |
| 中文乱码 | 确保UTF-8编码 |

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 联系方式

如有问题，请通过OpenClaw提问或提交Issue。
