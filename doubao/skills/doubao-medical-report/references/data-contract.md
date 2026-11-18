## 数据字段与来源契约

## 核心原则

医疗报告生成必须被证据约束。报告中的每个异常、表格、风险标签和管理建议，都必须来自以下来源之一：

- 用户提供的医院报告证据。
- `MedicalSearch` 或权威网络来源验证过的医学知识。
- 基于已抽取输入的明确计算结果。

不要把模型记忆当成影响医学建议的事实来源。

## 患者背景

只能使用原始报告或用户明确提供的信息：

- 年龄或出生年份。
- 性别。
- 身高、体重、BMI、腰围。
- 妊娠状态，如果相关且已提供。
- 已知疾病。
- 当前用药。
- 家族史。
- 吸烟、饮酒、睡眠、运动、饮食。

缺失时内部记为 `unknown`，不要自行推断。

## 证据项结构

内部证据项建议使用：

```json
{
  "date": "YYYY-MM-DD",
  "source_id": "file-or-page-id",
  "category": "lipids",
  "item_original": "总胆固醇",
  "item_normalized": "TC",
  "value_original": "5.22",
  "value_normalized": 5.22,
  "unit_original": "mmol/L",
  "unit_normalized": "mmol/L",
  "reference_range": "<5.17",
  "abnormal_flag": "high",
  "original_text": "总胆固醇 5.22 mmol/L ↑",
  "source_page": "page-1",
  "source_location": "table-2-row-8",
  "confidence": "high"
}
```

来源位置字段可记录页码、图片编号、表格行列或原文段落。置信度和复核状态可作为内部备注，不作为生成报告的前置确认流程。

资料不清或字段冲突时标注不确定性，不补齐或猜测数值。

## 标准化规则

保留原始值和标准化值。

常见同义词：

- 血压：SBP/DBP、收缩压/舒张压。
- 血脂：TC/总胆固醇、TG/甘油三酯、LDL-C/低密度脂蛋白胆固醇、HDL-C/高密度脂蛋白胆固醇、apoB/载脂蛋白B。
- 血糖：FPG/空腹血糖、HbA1c/糖化血红蛋白。
- 肾功能：Scr/肌酐、eGFR/估算肾小球滤过率、BUN/尿素氮。
- 肝功能：ALT/谷丙转氨酶、AST/谷草转氨酶、GGT/γ-GT。
- 甲状腺：TSH、FT3、FT4、TgAb、TPOAb、TI-RADS。
- 乳腺：BI-RADS。

单位换算必须明确计算，必要时使用 `calculator`。

## 来源要求

对于用户报告：

- 在报告中标注文件、页码或报告日期。
- 需要引用时只引用短片段。
- 影像和病理必须保留原始报告结论，不要重新诊断。

对于外部医学知识：

- 药品、医生、医院、药品说明书和医院/医生建议使用 `MedicalSearch`。
- 当前指南、公共标准和权威科普使用 `general_search`。
- 优先使用国家级网站、权威指南/共识、教材、权威期刊文献；其次使用专业学会、三甲医院或大学附属医院官网。
- 记录来源标题、机构/网站、发布日期或访问日期、URL 或可追溯来源编号，以及该来源支持了哪个结论。

外部来源结构建议使用：

```json
{
  "title": "来源标题",
  "organization": "发布机构/期刊",
  "source_type": "national_authority | guideline | textbook | journal | society | hospital | medical_search",
  "url": "https://...",
  "published_date": "YYYY-MM-DD or unknown",
  "accessed_date": "YYYY-MM-DD",
  "supports": ["支持的结论或章节"]
}
```

## 派生指标

允许计算：

- BMI = 体重 kg / 身高 m²。
- 重复指标的绝对变化和百分比变化。
- 家庭监测数据的均值、最大值、最小值、标准差。
- eGFR：只有在公式、年龄、性别、肌酐和单位完整时计算。
- 风险评分：只有在公式和必要输入完整时计算。

每个派生指标必须记录：

`输入字段 | 公式 | 结果 | 计算工具或方法 | 局限性`

## 缺失数据

表格中统一写 `暂无`。

正文中写：“当前资料不足以判断该项。”

不得为了完整性补造数值或结论。
