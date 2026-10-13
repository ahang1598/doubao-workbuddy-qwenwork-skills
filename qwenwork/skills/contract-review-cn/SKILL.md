---
install_source: official
install_method: download
skill_id: official_004pAqJ7
enabled_at: 1791894021976
version: 1.0.0
name_zh: 中文合同审查技能
---
# 中文合同审查技能 (contract-review-cn)

## 技能描述

`contract-review-cn` 是一个专业的中文合同审查工具，能够自动识别合同中的法律风险、提供修订建议，并生成清晰的三栏对照表。

### 主要功能

1. **自动风险识别** - 识别合同中的潜在法律风险
2. **修订建议** - 提供具体的修改建议
3. **三栏对照表** - 生成原文/建议修改/修改原因对照表
4. **重点审查** - 专注于合同审查的关键领域

### 支持的文件格式

- PDF 文件
- Word 文档 (`.docx`, `.doc`)
- 纯文本文件 (`.txt`)

### 审查重点领域

- 付款条款
- 验收标准
- 违约责任
- 知识产权
- 保密条款
- 争议解决
- 管辖法院

## 安装和配置

### 1. 安装依赖

```bash
cd /Users/mac/.openclaw/workspace/skills/contract-review-cn
pip install -r requirements.txt
```

### 2. 配置API密钥

复制配置文件并编辑：

```bash
cp config.example.json config.json
```

编辑 `config.json`，设置你的API密钥：

```json
{
  "api_provider": "openai",
  "api_key": "your-api-key-here",
  "model": "zai/glm-4.7-flash",
  "temperature": 0.3,
  "max_tokens": 4096,
  "contract_prompt_file": "templates/review_prompt.txt",
  "output_format": "markdown",
  "focus_areas": [
    "payment_terms",
    "acceptance_standards",
    "breach_liability",
    "intellectual_property",
    "confidentiality",
    "dispute_resolution",
    "governing_courts"
  ],
  "risk_threshold": 0.7,
  "max_risks": 10
}
```

### 3. 测试安装

```bash
python scripts/pdf_parser.py examples/sample.pdf
python scripts/word_parser.py examples/sample.docx
```

## 使用方法

### 方法一：直接使用Python脚本

#### 审查合同文件

```bash
# 审查PDF文件
python scripts/contract_analyzer.py contract.pdf

# 审查Word文件
python scripts/contract_analyzer.py contract.docx

# 审查TXT文件
python scripts/contract_analyzer.py contract.txt
```

#### 指定输出文件

```bash
python scripts/contract_analyzer.py contract.pdf --output my_review.md
```

#### 只显示报告，不保存文件

```bash
python scripts/contract_analyzer.py contract.pdf --show-only
```

#### 使用自定义配置

```bash
python scripts/contract_analyzer.py contract.pdf --config custom_config.json
```

### 方法二：通过OpenClaw调用

当你上传合同文件或发送以下指令时，技能会自动触发：

- "让我审合同"
- "让我出修订对照表"
- 上传合同文件

### 方法三：编程方式使用

```python
from pathlib import Path
from scripts.contract_analyzer import ContractAnalyzer
import json

# 加载配置
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 创建分析器
analyzer = ContractAnalyzer(config)

# 审查合同
contract_path = Path('contract.pdf')
report = analyzer.analyze_file(str(contract_path))

print(report)
```

## 输出格式

审查报告采用Markdown格式，包含以下内容：

### 1. 风险摘要

列出识别出的主要风险，每条包含：
- 风险等级（高/中/低）
- 具体风险描述

### 2. 修订建议

针对每个风险点，提供具体的修订建议

### 3. 三栏对照表

| 原文 | 建议修改 | 修改原因 |

清晰展示原文、修改建议和修改理由

## 配置说明

### 核心配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `api_provider` | string | `openai` | API提供商 |
| `api_key` | string | - | API密钥（必需） |
| `model` | string | `zai/glm-4.7-flash` | 使用的AI模型 |
| `temperature` | number | `0.3` | 创造性参数（0-1） |
| `max_tokens` | number | `4096` | 最大生成token数 |
| `focus_areas` | array | 7个领域 | 审查重点领域 |
| `risk_threshold` | number | `0.7` | 风险阈值 |
| `max_risks` | number | `10` | 最大风险数量 |

### 自定义审查重点

可以通过修改 `focus_areas` 数组来自定义审查重点：

```json
{
  "focus_areas": [
    "payment_terms",
    "intellectual_property",
    "confidentiality"
  ]
}
```

### 调整风险识别

修改 `risk_threshold` 来调整风险识别的严格程度：
- `0.5-0.6`: 严格模式，只识别高风险
- `0.7-0.8`: 正常模式（默认）
- `0.9-1.0`: 宽松模式，识别更多潜在风险

## 工作原理

### 1. 文件解析

- **PDF**: 使用 `PyPDF2` 提取文本
- **Word**: 使用 `python-docx` 提取文本和表格
- **TXT**: 直接读取文件内容

### 2. 风险识别

通过调用AI模型，根据预设的审查重点，识别合同中的潜在风险。

### 3. 报告生成

将分析结果整理成结构化的Markdown报告。

## 代码结构

```
contract-review-cn/
├── SKILL.md                    # 技能说明文档
├── README.md                   # 本文档
├── scripts/
│   ├── contract_analyzer.py    # 主分析器
│   ├── pdf_parser.py          # PDF解析器
│   └── word_parser.py         # Word解析器
├── templates/
│   └── review_prompt.txt      # 审查提示词模板
├── requirements.txt           # Python依赖
└── config.example.json        # 配置文件示例
```

## 注意事项

### 1. API密钥安全

- 不要将 `config.json` 提交到版本控制系统
- API密钥应该保存在安全的地方
- 定期更换API密钥以保护安全

### 2. 文件格式

- PDF文件应该包含可提取的文本，扫描版PDF可能无法解析
- Word文档建议使用 `.docx` 格式
- TXT文件应该使用UTF-8编码

### 3. 模型选择

- 推荐使用 `zai/glm-4.7-flash` 或类似的高质量模型
- 较小的模型可能影响审查质量
- 确保选择的模型支持中文合同审查

### 4. 合同长度

- 对于超长合同（超过50页），建议分章节审查
- 可以先使用PDF/Word解析器提取各章节，然后分别分析

### 5. 结果准确性

- AI模型可能产生幻觉，审查结果仅供参考
- 最终审查仍需人工审核确认
- 对于重要的商业合同，建议进行多重审查

## 故障排除

### 问题：无法解析PDF

**解决方案**：
- 确保安装了 `PyPDF2`
- 尝试使用 `pdf_parser.py` 测试
- 如果是扫描版PDF，需要先转换为可搜索的PDF

### 问题：API调用失败

**解决方案**：
- 检查API密钥是否正确
- 确认API服务是否可用
- 检查网络连接
- 查看错误日志获取详细信息

### 问题：审查结果不准确

**解决方案**：
- 调整 `temperature` 参数（降低可提高准确性）
- 优化 `review_prompt.txt` 提示词
- 选择更强大的AI模型
- 分章节审查，提高针对性

### 问题：中文字符乱码

**解决方案**：
- 确保文件使用UTF-8编码
- 在配置文件中设置正确的编码
- 检查终端编码设置

## 扩展和定制

### 修改审查重点

编辑 `templates/review_prompt.txt` 来自定义审查重点和输出格式。

### 添加新的文件格式支持

在 `scripts/` 目录下创建相应的解析器，并修改 `contract_analyzer.py` 中的文件类型判断逻辑。

### 集成到工作流程

可以将审查结果导入到以下工具：
- Markdown编辑器
- Word文档
- 电子邮件
- 项目管理系统

## 技术支持

如遇到问题，请检查：

1. Python版本（建议3.8+）
2. 所有依赖是否正确安装
3. 配置文件是否正确
4. 文件路径是否正确
5. API密钥是否有效

## 版本历史

- **v1.0.0** (2024-03-10)
  - 初始版本
  - 支持PDF、Word、TXT格式
  - 基本的合同审查功能
  - 三栏对照表输出
