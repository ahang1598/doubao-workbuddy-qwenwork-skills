# 中文合同审查技能 - 快速开始

## 5分钟快速上手

### 1. 安装依赖

```bash
cd /Users/mac/.openclaw/workspace/skills/contract-review-cn
pip install -r requirements.txt
```

### 2. 配置API密钥

```bash
cp config.example.json config.json
# 编辑 config.json，将 "your-api-key-here" 替换为你的实际API密钥
```

### 3. 审查你的第一个合同

```bash
# 审查PDF文件
python scripts/contract_analyzer.py 你的合同.pdf

# 审查Word文件
python scripts/contract_analyzer.py 你的合同.docx

# 审查TXT文件
python scripts/contract_analyzer.py 你的合同.txt

# 查看报告
cat 你的合同_review.md
```

## 查看演示

```bash
python demo.py
```

## 配置说明

编辑 `config.json`:

```json
{
  "api_key": "your-actual-api-key",
  "model": "zai/glm-4.7-flash",
  "temperature": 0.3,
  "focus_areas": [
    "payment_terms",
    "acceptance_standards",
    "breach_liability",
    "intellectual_property",
    "confidentiality",
    "dispute_resolution",
    "governing_courts"
  ]
}
```

## 输出示例

### 风险摘要

```
识别出3个主要风险：
- 高风险：付款条件不明确，可能导致延迟付款
- 中风险：违约责任条款过于宽泛
- 中风险：争议解决方式未明确
```

### 三栏对照表

| 原文 | 建议修改 | 修改原因 |
|------|----------|----------|
| 付款方式：现金 | 付款方式：银行转账，汇款后5个工作日内支付 | 明确付款方式，便于实际执行 |
| ... | ... | ... |

## 常见问题

### Q: API调用失败怎么办？
A: 检查API密钥是否正确，网络是否正常，API服务是否可用。

### Q: 中文乱码怎么办？
A: 确保合同文件使用UTF-8编码，配置文件也使用UTF-8编码。

### Q: 审查结果不准确？
A: 可以调整 `temperature` 参数（降低可提高准确性），或使用更强的模型。

### Q: 支持哪些文件格式？
A: PDF、Word (.docx)、TXT格式。

## 更多信息

详细文档请查看：
- [SKILL.md](SKILL.md) - 完整使用文档
- [README.md](README.md) - 项目说明
- [CREATE_SUMMARY.md](CREATE_SUMMARY.md) - 创建总结

## 下一步

1. 配置API密钥
2. 准备合同文件
3. 开始审查
4. 根据审查结果修改合同

祝你使用愉快！
