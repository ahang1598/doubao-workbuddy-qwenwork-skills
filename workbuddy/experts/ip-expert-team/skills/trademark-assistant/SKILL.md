---
name: 商标申请助手
name_en: trademark-assistant
description: 当接到商标咨询、需要做类别规划或可注册性初筛、需要输出结构化建议与风险分级，或需要准备商标申请材料（商品清单、商标说明）时使用。基于尼斯分类与中国商标法律法规，面向中国大陆商标申请。不要用于：替代正式法律意见、承诺注册成功率或处理复杂商标争议。
---
# 商标助手

提供“商标类别规划 + 可注册性初筛”的标准化服务流程，可直接交付给客户或内部团队一份结构化结论。

## 适用范围

**主要适用场景：** 中国大陆商标申请

**法律依据：** 本技能所援引的法律法规均为中国国内法规，包括但不限于《中华人民共和国商标法》《商标法实施条例》以及《商标审查审理指南》等。

**国际适用性说明：**
- 尼斯分类（Nice Classification）是国际通用的商标分类标准，故类别规划部分可延伸至国际商标申请
- 但可注册性初筛、审查标准分析等涉及具体法律判断的内容，仅限于中国商标申请
- 若涉及国际商标申请（马德里体系、单一国家注册等），需另行咨询专业律师

**服务主体：** 本技能由中国执业律师提供法律服务支持，仅具备中国大陆法律服务资质。

## 触发条件

在以下情形触发本技能：

- 咨询“应当注册哪些类别”
- 咨询“这个商标名大致能否通过”
- 需要产出可复用的商标初筛报告
- 需要对咨询做风险分级并给出下一步行动
- **客户已敲定设计方案，需要撰写商标说明**
- **需要准备商标申请材料（商品清单、商标说明）**

## 服务边界

- 输出仅为初步研判，不替代律师或代理机构的正式法律意见
- 不承诺注册成功率
- 遇复杂争议（抢注、驰名商标、跨类大规模冲突）直接升级为人工深度审查

## 输入收集

优先依据 `references/service-intake-checklist.md` 收集信息；关键信息缺失时先发问，不直接下结论。

最少输入：

1. 申请主体与主营业务
2. 拟申请商标（文字/图形/组合）
3. 当前已知的目标类别或使用场景

## 执行流程

### 阶段一：咨询与规划

1. 识别请求类型：`类别规划` / `可注册性初筛` / `组合服务`
2. 借助 `references/classification-planning-guide.md` 完成类别规划
3. 借助 `references/registrability-prescreen-guide.md` 完成可注册性初筛
4. 依据 `references/output-contract.md` 输出标准化结果
5. 强制附上免责声明与升级建议（含律师咨询入口）

### 阶段二：申请材料准备

当客户确认设计方案后，进入申请材料准备阶段：

1. **商品清单生成**：依据已确定的目标类别，生成规范的商品清单 Excel 文件
2. **商标说明撰写**：分析商标设计图片，撰写符合官方要求的商标说明文本
3. **材料归档**：把生成的材料归档到 `archive/` 目录

## 输出要求

- 先给结论，再给依据，再给风险，最后给行动
- 明确区分“高风险/中风险/低风险”；信息不足时标注“待补充（信息不足，暂不评级）”
- 引用依据时注明来源文件（如 `references/trademark-examination-and-adjudication-guidelines/chapter-03.md`）
- 缺失信息必须标注“未提及/待补充”
- 统一只输出一个版本：Markdown 结构化结论，不附带 JSON 代码块
- 每次输出必须包含免责声明与升级建议
- 遇高风险、复杂争议或关键信息缺失时，明确建议用户咨询专业律师或商标代理机构

## 输出格式

- 对话内默认输出 Markdown 预览，不声称已生成实际不存在的下载件。
- 正式初筛/规划报告生成为 Word（.docx），命名 `商标助手_{主题}_{YYYYMMDD}.docx`。
- 报告**必须**在标题后放置免责声明（AI 辅助 + 仅供参考 + 不构成正式法律意见）。
- Word 全文**不得含 emoji**；**禁止绝对化法律结论**（使用商标法规范术语，绝对理由 / 相对理由等区分须准确，不得混淆或改写）。
- 风险等级必须**文字 + 颜色**。
  - 对话内 Markdown 预览：直接使用纯文本标签 `高风险` / `中风险` / `低风险` / `待补充（信息不足，暂不评级）`，不加 pandoc 属性语法（聊天界面无法渲染）。
  - 生成 Word（.docx）时：使用 pandoc 属性语法以渲染带色标签——`[高风险]{.tag .risk-high}` / `[中风险]{.tag .risk-mid}` / `[低风险]{.tag .risk-low}` / `[待补充]{.tag .risk-pending}`（须经 pandoc + `assets/richee-reference.docx` + `scripts/richee.lua` 渲染；若运行环境无 pandoc，则退化为上述纯文本标签输出）。
- 依据标签只用本技能声明的封闭集合：风险四档、法规引用「《法规名》第X条」、段落样式 `Disclaimer`。
- 商品清单 Excel 沿用 `templates/导入商品信息.xlsx` 官方导入格式，**不改字段/列序/版式**，只追加数据行；不强套品牌视觉。
- 详细版式、契约、生成与验收见 [`references/输出格式规范.md`](references/输出格式规范.md)。

### 生成（运行环境已具备 pandoc，在 skill 根目录执行）

```bash
pandoc 报告.md -o "商标助手_{主题}_{YYYYMMDD}.docx" \
  --reference-doc=assets/richee-reference.docx \
  --lua-filter=scripts/richee.lua \
  --from markdown+east_asian_line_breaks
```

商品清单用 openpyxl 加载 `templates/导入商品信息.xlsx` 填充数据行后另存（见 `references/输出格式规范.md` 第 5 节）。组件用法与样例见 `references/输出格式规范.md` 与 `examples/`。

## 关键参考资料

- 服务输入清单：`references/service-intake-checklist.md`
- 类别规划规则：`references/classification-planning-guide.md`
- 初筛判定规则：`references/registrability-prescreen-guide.md`
- 交付模板：`references/output-contract.md`
- 商标说明撰写指南：`references/trademark-description-guide.md`
- 法律与实务依据总索引：`references/legal-basis-index.md`
- 审查指南索引：`references/trademark-examination-and-adjudication-guidelines/trademark-examination-and-adjudication-guidelines-index.md`
- 尼斯分类索引（当前）：`references/nice-classification-v13-2026/nice-classification-v13-2026-index.md`
- 尼斯分类类别摘要：`references/nice-classification-v13-2026/nice-classification-v13-2026-summary.md`
- **商品清单导入模板**：`templates/导入商品信息.xlsx`

## 商品清单输出格式

当需要输出可导入商标系统的商品清单时，使用 `templates/导入商品信息.xlsx` 模板生成 Excel 文件。

### 模板结构

| 列名 | 说明 | 示例 |
|------|------|------|
| 序号 | 商品序号 | 1, 2, 3... |
| 商品类别 | 商标类别编号 | 28 |
| 类似群 | 类似群编号 | 2802 |
| 商品名称 | 规范商品名称 | 玩具 |

### 输出要求

1. **优先选取保护范围更宽的核心商品**，而非细分商品
2. 商品名称必须是尼斯分类中的规范名称（可在 `references/nice-classification-v13-2026/nice-classification-v13-2026-summary.md` 中查找）
3. 同一类似群的商品归并为一组，便于审查
4. 输出文件命名格式：`{商标名}-第{X}类-商品清单.xlsx`

### 生成方式

使用 openpyxl 库生成 Excel 文件：

```python
from openpyxl import load_workbook

# 加载模板
wb = load_workbook('templates/导入商品信息.xlsx')
sheet = wb.active

# 填充数据（从第2行开始）
for idx, item in enumerate(goods_list, start=2):
    sheet[f'A{idx}'] = idx - 1  # 序号
    sheet[f'B{idx}'] = item['类别']  # 商品类别
    sheet[f'C{idx}'] = item['类似群']  # 类似群
    sheet[f'D{idx}'] = item['商品名称']  # 商品名称

wb.save('输出文件.xlsx')
```

## 商标说明撰写

商标说明用于描述商标特征、构成要素及含义；**并非所有商标申请都需要撰写商标说明**，应依据《商标法实施条例》第13条按商标类型按需提供（普通印刷体文字商标通常无需说明，外文、图形、三维、颜色组合、声音、集体 / 证明商标等才需要）。

### 适用时机

- 客户已确认商标设计方案
- 准备提交商标注册申请
- 需要生成申请材料

### 撰写要点

1. **明确商标类型**：声明商标由哪些元素构成
2. **说明文字内容**：描述字体形式（普通印刷体/艺术字）
3. **解释文字含义**：说明含义或声明“无特殊含义”
4. **字数限制**：200字以内

### 图形/组合商标

对于**图形商标**或**组合商标**，必须先调用图像理解工具分析商标图片，再撰写说明。可用工具包括 `mcp__zai-mcp-server__analyze_image`（推荐优先）、`mcp__MiniMax__understand_image`（备选）以及内置 `Read` 工具直接读取图片。

撰写流程：先用图像理解工具分析商标图片 → 提取关键设计特征 → 结合用户补充说明完善细节与寓意 → 按官方要求撰写说明文本。完整的图像分析要点、提示词模板、设计特征描述技巧与填写示例，见 `references/trademark-description-guide.md`。

## Archive 归档

当完成具体商标申请方案后，把生成的材料归档到 `archive/` 目录，便于后续查阅与复用。

### 目录结构

```
archive/
└── {YYYYMMDD}_{商标名}/
    ├── 申请方案.md          # 完整申请方案（含类别规划、风险分析）
    ├── 商品清单.xlsx        # 可导入商标系统的商品清单
    ├── 商标说明.txt         # 商标说明文本
    └── notes.md            # 备注信息（可选）
```

### 归档时机

- 用户确认申请方案后
- 完成商标注册咨询服务后

## 依赖

### 系统依赖

| 依赖 | 安装方式 |
|------|----------|
| 无 | 本技能为文本推理与结构化输出流程，无额外系统依赖 |

### Python 包

| 包名 | 用途 | 安装命令 |
|------|------|----------|
| openpyxl | 生成 Excel 商品清单 | `uv run --with openpyxl python script.py` |
