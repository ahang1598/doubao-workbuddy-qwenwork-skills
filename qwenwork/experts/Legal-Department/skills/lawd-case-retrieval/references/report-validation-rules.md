# 类案检索报告校验规则

服务于 `律师类案检索与报告` **模式C（正式类案检索报告）**，原属 `lawd-case-retrieval-report`（旧名「类案检索报告」）。下文脚本均已迁入本技能 `scripts/` 目录，命令中的 `scripts/xxx.py` 指 `lawd-case-retrieval/scripts/xxx.py`。

## 校验顺序

1. 校验结构化案例 JSON。
2. 生成 DOCX。
3. 校验 DOCX 容器、章节、案例集合和占位符。
4. 所有检查通过后才能交付。

## 生成前数据校验

运行：

```bash
python3 scripts/validate_report_cases.py /absolute/path/report-data.json
```

必须通过：

- JSON 可解析且顶层为对象；
- `schema_version` 为 `1.0`；
- `report`、`explicit_constraints` 为对象；
- `retrieval_targets`、`conclusions`、`cases` 为数组；
- 至少有一个案例；
- 每个案例按 `case_id → case_no → raw_record_locator` 取到非空身份键，且身份键唯一；
- 每个 `title` 非空；
- 非空案号没有重复；
- 不含模板占位符；
- 用户明确时间、地域和数量约束能够被现有字段验证且全部满足。

用户没有明确时间或地域约束时，校验器不执行对应过滤。

## 约束核验

### 时间

- 只读取 `explicit_constraints.date_from` 和 `date_to`。
- 存在时间约束时，每个案例必须有可解析的 `decision_date`。
- 不从案号推断裁判日期。

### 地域

- 只读取 `explicit_constraints.regions`。
- 存在地域约束时，每个案例必须有正式 `court`。
- 地域词须包含于法院名称；校验器不推断法院所在地。

### 数量

- `max_cases` 仅在用户明确指定时填写。
- 案例数量不得超过该值。
- 不自动补足固定数量。

## DOCX 校验

运行：

```bash
python3 scripts/validate_report_docx.py \
  /absolute/path/report-data.json \
  /absolute/path/report.docx
```

必须通过：

- 文件存在且非空；
- 文件是合法 ZIP，并包含 `[Content_Types].xml` 和 `word/document.xml`；
- `python-docx` 可打开文件；
- 文档正文不是空文档；
- 页面为 A4，Title 与三级标题样式固定为黑色；
- “一、检索说明”至“五、附件”五个章节齐全；
- 每个案例标题、非空案号和非空法院均出现在文档中；
- 文档内嵌的案例集合摘要与输入 JSON 完全一致；
- 不含 `TODO`、`TBD`、`{{...}}`、`[待补充]` 等占位符。

## 一致性机制

生成器按案例顺序计算字段摘要，并写入 DOCX 核心属性：

- `case_id`（允许为空）
- `title`
- `case_no`
- `court`
- `decision_date`

验证器使用同一规则重算摘要。摘要不一致说明 DOCX 与输入案例集合不一致，必须重新生成。

## 失败处理

- JSON 失败：修复映射或补充真实数据。
- DOCX 失败：修复生成环境或文件内容后重新生成。
- `python-docx` 不可用：可改用当前环境的 DOCX 能力，但最终仍须通过等价校验。
- 可输出 Markdown 预览用于定位问题，但状态必须写“DOCX 交付失败”，不得写“已完成”。

## 人工复核

脚本不能判断法律分析是否正确。交付前仍需人工确认：

- 结论是否被纳入案例支持；
- 原文摘录是否确为来源原文；
- 摘要是否改变事实或裁判含义；
- 报告是否准确说明样本范围和信息缺失。
