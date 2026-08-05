## 数据字段与来源契约

## 核心原则

医疗报告生成必须被证据约束。报告中的每个异常、图表、风险标签和管理建议，都必须来自以下来源之一：

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
  "value_verified": true,
  "verification_status": "verified",
  "confidence": "high"
}
```

来源与复核字段：

- `source_page`：页码、图片编号或文件段落。
- `source_location`：表格行列、坐标或原文位置。
- `value_verified`：结果值、单位、参考范围和异常标记是否已核对。
- `verification_status`：`verified`、`needs_review` 或 `conflict`。

置信度：

- `high`：来自清晰表格或明确报告结论。
- `medium`：来自可读段落，但存在轻微歧义。
- `low`：数值不清、单位不清、日期不清或项目映射可能有多种解释。

低置信度证据不能支撑强医学结论，除非用户确认或有其他证据补强。
`low` 或 `needs_review` 的数值不得进入图表、趋势分析、紧急风险判断或高优先级风险结论。若会影响异常解读、图表、趋势、高风险提示或就医优先级，必须先请用户确认；确认后才可使用。

## 数值复核

抽取后按以下顺序复核：

1. 项目名、结果、单位、参考范围和异常标记是否来自同一行或同一段原文。
2. 小数点、指数单位、范围符号和上下箭头是否无歧义。
3. 日期、性别/年龄条件和参考范围是否匹配。
4. 数值不清或字段冲突时，标记 `verification_status: "needs_review"` 或 `"conflict"`。

不要为了生成完整图表而修正、补齐或猜测不清晰的数值。

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
- 带 URL 的来源必须在输出前检查可访问，并在飞书文档中做成可点击链接。

外部来源结构建议使用：

```json
{
  "title": "来源标题",
  "organization": "发布机构/期刊",
  "source_type": "national_authority | guideline | textbook | journal | society | hospital | medical_search",
  "url": "https://...",
  "published_date": "YYYY-MM-DD or unknown",
  "accessed_date": "YYYY-MM-DD",
  "supports": ["支持的结论或章节"],
  "link_checked": true,
  "link_status": 200
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
