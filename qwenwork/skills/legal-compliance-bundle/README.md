# 中国法律合规AI技能包 (Legal Compliance Skill Bundle)

> 50个AI驱动的法律合规自动化技能，覆盖合同、劳动、知产、数据、企业合规五大领域。

## ✨ 核心特性

- **50个即用型技能** — 每个技能独立运行，可自由组合
- **中国法律知识库** — 基于现行法律法规（合同法、劳动法、PIPL等）
- **安全审计报告** — 附带SkillFortify形式化验证（F1=96.95%，零误报）
- **本地数据处理** — 所有数据本地计算，不外传

## 📦 技能分类

| 模块 | 技能数 | 代表技能 |
|------|--------|----------|
| 合同管理 | 10 | 合同审查、条款建议、风险评分、模板生成 |
| 法律问答 | 8 | 法律问答、判例检索、法规解读、诉讼风险评估 |
| 劳动合规 | 8 | 劳动合同审查、社保计算、解雇风险、竞业限制 |
| 知识产权 | 6 | 商标检索、专利辅助、侵权评估、许可协议 |
| 数据合规 | 8 | PIPL合规、隐私政策生成、数据出境评估、泄露应急 |
| 企业合规 | 10 | 反洗钱/KYC、反贿赂、合规培训、审计清单 |

## 🚀 快速开始

```bash
# 安装
clawhub install legal-compliance-bundle

# 配置
cp config/legal-config.yaml.template config/legal-config.yaml

# 测试
python scripts/contract_review.py
python scripts/legal_qa.py --query "劳动合同试用期最长多久？"
```

## 📁 项目结构

```
legal-compliance-bundle/
├── SKILL.md                    # 技能包总览
├── README.md                   # 本文件
├── scripts/                    # 50个技能脚本
│   ├── contract_review.py      # 合同审查
│   ├── legal_qa.py             # 法律问答
│   ├── pipl_compliance_check.py # PIPL合规
│   └── ... (共50个)
├── config/
│   └── legal-config.yaml.template
└── knowledge/
    └── sample_contract.txt     # 测试样本
```

## 💰 定价

| 套餐 | 价格 | 包含 |
|------|------|------|
| 基础版 | ¥999 | 10个核心技能 |
| 标准版 | ¥1,999 | 30个技能 |
| 完整版 | **¥2,999** | 全部50个技能+安全审计报告 |
| 企业定制 | ¥5,000+ | 定制技能+专属知识库+部署支持 |

## 📄 许可

商业使用需购买授权。详见 SKILL.md。
