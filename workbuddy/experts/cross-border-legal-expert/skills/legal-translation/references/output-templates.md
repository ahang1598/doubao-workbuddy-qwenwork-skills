# 输出模板

## 术语表模板

```markdown
## 翻译术语表

| 中文术语 | 建议英文 | 领域技能/来源 | 适用语境 | 排除译法 | 是否需人工确认 |
|---|---|---|---|---|---|
| 甲方 | Party A | legal_glossary.json | 合同主体 | the First Party | 否 |
| 原告 | plaintiff | foreign-legal-english-term-precision | 民事一审 | claimant/complainant | 否 |
| 不可抗力 | force majeure | civil-law-private-rights-translator | 合同风险条款 | Act of God 直接替代 | 视条款而定 |
```

## 审校报告模板

```markdown
## 法律翻译审校报告

文书类型: [合同/诉状/备忘录/公司文件]
任务范围: [全文/第 X 条/术语表/数字编号]
触发的领域技能: [列出]

| 位置 | 原文/原译 | 问题 | 建议 | 理由 | 风险等级 |
|---|---|---|---|---|---|
| 第 2 条 | defendant | 仲裁语境不宜使用 defendant | respondent | 仲裁被申请人通常用 respondent | 中 |

### 一致性检查

- 术语一致性: 通过/有问题
- 法域一致性: 通过/有问题
- 程序身份一致性: 通过/有问题
- 编号对应性: 通过/有问题
- 数字准确性: 通过/有问题

### 待复核项

- [列出需要用户、律师、法务或客户确认的译法]
```

## 双语 Word 交付模板

```text
【完成】双语对照翻译已生成

路径: [完整路径]
文书类型: [合同/意见书/备忘录等]
任务类型: 中译英 + 中英双语对照
原文: 共 X 段 / X 字
译文: 共 X 段 / X words
触发的领域技能: [列出]

一致性检查:
  - 术语一致性: 通过
  - 编号对应性: 通过
  - 数字准确性: 通过
  - 法域/程序身份一致性: 通过/有风险提示

关键术语表: 共使用 X 个术语
高风险术语: [无/列出]
待复核项: [无/列出]

提醒:
本输出为翻译和术语审校工作底稿, 建议由律师、法务或专业译审复核后使用。
```

## 脚本 JSON 模板

```json
{
  "title_cn": "软件开发服务合同",
  "title_en": "Software Development Service Contract",
  "doc_type": "合同",
  "translation_date": "2026年3月13日",
  "glossary_used": [
    {"cn": "甲方", "en": "Party A"},
    {"cn": "违约金", "en": "liquidated damages"}
  ],
  "sections": [
    {
      "cn": "第一条 项目内容\n甲方委托乙方开发企业管理系统。",
      "en": "Article 1 Project Scope\nParty A engages Party B to develop an enterprise management system."
    }
  ],
  "consistency_check": {
    "terminology_pass": true,
    "numbering_pass": true,
    "figures_pass": true,
    "corrections": []
  }
}
```

脚本 JSON 中不加入 `routing_notes`、`risk_terms`、`excluded_terms` 等内部字段; 这些内容只放入交付报告或审校报告。
