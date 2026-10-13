# 配置文件字段说明

本配置文件用于**类型1（基础组间设计）**的完整自动分析。其他设计类型通过CLI参数直接调用：

| 设计类型 | 调用方式 |
|---|---|
| 类型1 基础组间 | `python exp_analysis.py config.json`（本文档） |
| 类型2 嵌套设计 | 有限 CLI：`python exp_analysis.py --icc data.sav --group class_id --dv Y`，只做 ICC 诊断，不拟合最终多层模型 |
| 类型4 被试内 | 有限 CLI：`python exp_analysis.py --rm-anova data.csv --subject id --within time --dv Y`，仅单个被试内因素的基础路径 |
| 类型5 混合设计 | 有限 CLI：`python exp_analysis.py --mixed-anova data.csv --subject id --within time --between group --dv Y`，仅一个组间因素加一个被试内因素 |
| 类型3/6/7 | 仅按 [design_decision_matrix.md](design_decision_matrix.md) 提供方法指导或代码模板；主脚本不执行 |

配置文件为 JSON 格式，脚本通过 `python exp_analysis.py config.json` 调用。

## 顶层字段

| 字段 | 类型 | 必需 | 说明 |
|---|---|---|---|
| `data_file` | string | 是 | 数据文件绝对路径，支持 .sav / .csv |
| `output_dir` | string | 是 | 报告输出目录，不存在则自动创建 |
| `factors` | object | 是 | 自变量定义，见下 |
| `scales` | object | 否 | 量表题项分组，见下 |
| `manipulation_checks` | array | 否 | 操纵检验题，见下 |
| `dvs` | object | 是 | 因变量（列名→显示名） |
| `mediation` | object | 否 | 中介模型设定，见下 |

## factors（自变量）

每个自变量一个键值对：

```json
"X1": {
  "label": "思考线索",
  "source_col": "思考（1无；2有）",
  "levels": {"1": 0, "2": 1},
  "level_labels": ["无思考", "有思考"]
}
```

| 子字段 | 必需 | 说明 |
|---|---|---|
| `label` | 否 | 显示名，报告中使用 |
| `source_col` | 否 | 数据中的原始列名；若原始列名含中文/特殊字符，用此字段映射，键名(X1)作为分析用列名 |
| `levels` | 是 | 原始值→0/1的映射，键为原始值（字符串），值为0或1。0=参照/控制组，1=实验组 |
| `level_labels` | 否 | 两个水平的显示标签，顺序对应编码0、1 |

**规则：** 分类自变量必须编码为0/1。3+水平自变量可保留原值（不写levels），但中介分析仅支持0/1编码的调节变量。

## scales（量表）

```json
"scales": {
  "M_拟人化": ["anthropho1", "anthropho2", "anthropho3"],
  "Y_满意度": ["AIsatisfy1", "AIsatisfy2", "AIsatisfy3", "AIsatisfy4"]
}
```

- 键为量表名（将作为新列名加入数据）
- 值为题项列名数组
- 脚本自动计算均值作为量表得分，并计算 Cronbach's α（仅≥2题时）
- 若题项中有反向计分题，需在数据预处理阶段先反向编码，脚本不自动处理

## manipulation_checks（操纵检验）

```json
"manipulation_checks": [
  {
    "iv": "X1",
    "check_var": "thinkingprocess1",
    "label": "机器人呈现了思考过程",
    "type": "continuous",
    "expected_direction": "high"
  },
  {
    "iv": "X1",
    "check_var": "color_recall",
    "label": "背景颜色识别",
    "type": "categorical",
    "correct_values": {"0": "red", "1": "blue"},
    "correct_threshold": 0.80
  }
]
```

### 连续型（type: "continuous"，默认）

| 子字段 | 必需 | 说明 |
|---|---|---|
| `iv` | 是 | 对应的自变量列名（如X1） |
| `check_var` | 是 | 操纵检验题的列名 |
| `label` | 否 | 检验题描述 |
| `type` | 否 | `"continuous"`（默认） |
| `expected_direction` | 是 | `"high"`=编码1组均值应更高；`"low"`=编码0组应更高 |

脚本根据实验设计自动选择方法：
- 单因素2水平：独立样本t检验 + 方向检验
- 单因素3+水平：one-way ANOVA + Tukey HSD
- 多因素设计：全因素ANOVA，检查主效应精准命中+无交叉污染+无交互

### 分类型（type: "categorical"）

| 子字段 | 必需 | 说明 |
|---|---|---|
| `iv` | 是 | 对应的自变量列名 |
| `check_var` | 是 | 分类检验题列名 |
| `label` | 否 | 描述 |
| `type` | 是 | `"categorical"` |
| `correct_values` | 是 | 各组正确答案，键为IV编码（"0"/"1"），值为正确选项 |
| `correct_threshold` | 否 | 正确率阈值，默认0.80（严格标准用0.90） |

## dvs（因变量）

```json
"dvs": {
  "M_拟人化": "拟人化感知",
  "Y_满意度": "AI满意度",
  "Y_使用意愿": "使用意愿"
}
```

- 键为因变量列名（可以是scales中定义的量表名）
- 值为报告中显示的名称
- 每个DV分别跑一次ANOVA决策树

## mediation（中介分析）

```json
"mediation": {
  "X": "X1",
  "W": "X2",
  "Z": "X3",
  "M": "M_拟人化",
  "Y_cols": ["Y_满意度", "Y_使用意愿"],
  "Y_names": ["AI满意度", "使用意愿"],
  "n_boot": 5000,
  "seed": 42
}
```

| 子字段 | 必需 | 说明 |
|---|---|---|
| `X` | 是 | 核心自变量（focal predictor） |
| `W` | 否 | 第一个调节变量，null表示无 |
| `Z` | 否 | 第二个调节变量，null表示无 |
| `M` | 是 | 中介变量列名 |
| `Y_cols` | 是 | 因变量列名数组（可多个） |
| `Y_names` | 否 | 因变量显示名，默认同Y_cols |
| `n_boot` | 否 | Bootstrap次数，默认5000 |
| `seed` | 否 | 随机种子，默认42（保证可重复） |

模型自动选择：
- 无W无Z → Model 4（简单中介）
- 有W无Z → Model 8（前半路径+直接路径被调节）
- 有W有Z → Model 12（双调节变量）

**注意：** 2×2×2设计中，以理论核心自变量为X。若不确定哪个是核心，分别以每个IV为X各跑一遍，比较Index结果。
