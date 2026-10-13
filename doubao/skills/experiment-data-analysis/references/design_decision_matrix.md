# 实验数据分析决策矩阵（The Master Matrix）

本文档说明 7 种实验设计的统计方法、检查点与模板。先查看“能力等级”，再决定执行还是仅提供指导；模板不是已经运行或验证的统计结果。

## 目录

- [能力等级](#能力等级)
- [类型1：基础组间设计](#类型1基础组间设计between-subject)
- [类型2：嵌套型组间设计](#类型2嵌套型组间设计nested-between--hlm)
- [类型3：刺激物抽样组间](#类型3刺激物抽样组间stimulus-sampling--lmm)
- [类型4：基础被试内设计](#类型4基础被试内设计within-subject--repeated-measures)
- [类型5：基础混合设计](#类型5基础混合设计standard-mixed--mixed-anova)
- [类型6：多情境混合设计](#类型6多情境混合设计multi-topic-mixed--crossed-lmm)
- [类型7：复杂机制检验](#类型7复杂机制检验complex-mechanism--sem)
- [设计类型快速判断流程图](#设计类型快速判断流程图)

## 能力等级

| 类型 | 能力等级 | 边界 |
|---|---|---|
| 1 基础组间 | 脚本主流程 | 配置、操纵检验、ANOVA、简单效应、交互图和受支持中介；执行前仍需人工完成隐私、缺失与假设审计 |
| 2 嵌套 | ICC 有限 CLI；最终多层模型仅指导或模板 | ICC 不是最终模型，也不是单独决定是否建模的阈值 |
| 3 刺激物抽样 | 仅指导或模板 | 主脚本不拟合刺激物随机效应模型 |
| 4 基础被试内 | 有限 CLI | 仅单个被试内因素的基础路径，主要输出终端结果；复杂结构仅指导 |
| 5 标准混合 | 有限 CLI | 仅一个组间因素加一个被试内因素的基础路径；复杂结构仅指导 |
| 6 多情境混合 | 仅指导或模板 | 主脚本不拟合交叉随机效应模型 |
| 7 实验型 CFA 或 SEM | 仅指导或模板 | 主脚本不执行；纯问卷或通用 CFA/SEM 不属于本 Skill |

复杂或不收敛模型必须标注“未由本 Skill 主脚本执行”，不得把模板输出描述成验证结果。

---

## 类型1：基础组间设计（Between-Subject）

### 识别特征
- 每个被试只参与一个实验条件
- 被试完全独立（无嵌套、无配对）
- 每个条件使用单一刺激材料（或刺激材料差异不作为分析因素）

### 统计方法
- 1个IV，2水平：独立样本t检验
- 1个IV，3+水平：单因素ANOVA + Tukey HSD
- 2+个IV：多因素ANOVA（Type III SS）
- 中介机制：PROCESS Model 4/8/12

### 核心命门
1. **Levene's方差齐性检验**：方差不齐时使用Welch校正t检验或Welch ANOVA
2. **交互显著时禁止解释主效应**：必须做简单主效应分析
3. **3+水平主效应显著必须做事后检验**
4. **被调节的中介以Index of Moderated Mediation为准**，不是个别条件间接效应

### 代码模板
脚本自动执行（`exp_analysis.py config.json`），包含Levene检验。

### 报告写法
见 reporting_standards.md。

---

## 类型2：嵌套型组间设计（Nested Between / HLM）

### 识别特征
- 被试嵌套在自然群体中：班级、公司部门、医院、家庭、学校
- 同一群体内的被试不独立（共享环境/教师/管理者）
- 通常是群体随机分配到实验条件（cluster randomization），或个体分配但嵌套存在

### 统计方法
- **空模型（Null Model）**计算ICC
- 聚类来自研究设计时，优先使用能表达聚类结构的多层或稳健方法；ICC 用于量化聚类程度，不是唯一选模阈值
- 若考虑简化为普通 ANOVA，必须同时论证随机化单位、组数、组大小、设计效应与稳健性，而不能只依据 ICC ≤ .05
- 工具：`statsmodels.regression.mixed_linear_model.MixedLM`

### 核心命门
1. **报告 ICC 与聚类设计**：ICC = σ²_between / (σ²_between + σ²_within)
2. 依据设计表达嵌套群体；随机截距只是起点，是否需要随机斜率由理论和数据支持决定
3. 比较候选模型时记录估计方法、收敛、奇异拟合、组数与组大小；似然比检验必须满足可比模型条件
4. 若需要 Satterthwaite 或 Kenward–Roger 自由度，使用明确支持该功能的实现；不要把普通渐近 z/t 值冒充该校正

### 代码模板

> 仅为方法起点，未由本次返修执行或独立验证；需在脱敏数据上检查依赖版本、收敛、自由度与结果复现。

```python
import statsmodels.api as sm
from statsmodels.regression.mixed_linear_model import MixedLM

# 1. 空模型计算ICC
null_model = MixedLM.from_formula('Y ~ 1', groups='class_id', data=df)
null_result = null_model.fit()
icc = null_result.cov_re.iloc[0,0] / (null_result.cov_re.iloc[0,0] + null_result.scale)
print(f"ICC = {icc:.3f}")

# 2. 加入自变量的随机截距模型
model = MixedLM.from_formula('Y ~ X1 + X2 + X1:X2', groups='class_id', data=df)
result = model.fit()
print(result.summary())
```

### 报告写法
- 报告ICC值及理由
- 报告固定效应（B, SE, t, p）和随机效应方差
- 报告边际R²（固定效应解释的方差）和条件R²（固定+随机效应）

---

## 类型3：刺激物抽样组间（Stimulus Sampling / LMM）

### 识别特征
- 组间设计，但每个条件下使用了**多套不同的刺激材料**（如多条广告、多篇文章、多个机器人形象）
- 刺激材料是从更大的材料总体中抽样的
- 目的：证明效应不限于某一特定材料，可推广到材料总体

### 统计方法
- 线性混合模型（LMM）
- 刺激物ID为**随机截距**（必要时随机斜率）
- 实验条件为固定效应
- 被试和刺激物均可作为随机效应（交叉随机效应，见类型6）

### 核心命门
1. **必须将刺激物ID设为随机因子**，否则F1（被试分析）显著但F2（刺激物分析）可能不显著
2. 报告F1和F2（或直接用LMM同时处理）
3. 随机斜率是否需要：理论上效应可能因材料而异时加随机斜率
4. 模型收敛问题：从随机截距开始，逐步加随机斜率

### 代码模板

```python
from statsmodels.regression.mixed_linear_model import MixedLM

# 刺激物为随机截距
model = MixedLM.from_formula(
    'Y ~ condition',
    groups='stimulus_id',
    data=df
)
result = model.fit()
print(result.summary())

# 若同时有被试和刺激物交叉随机效应，见类型6
```

### 报告写法
- 说明刺激物抽样设计
- 报告固定效应F/t/p和随机效应方差
- 明确声明"效应在刺激物间稳健"

---

## 类型4：基础被试内设计（Within-Subject / Repeated Measures）

### 识别特征
- 每个被试参与所有实验条件
- 或同一被试在多个时间点被测量
- 观测值不独立（同一被试的多次测量相关）

### 统计方法
- 重复测量ANOVA（Repeated Measures ANOVA）
- 工具：`pingouin.rm_anova`
- 数据必须为**长格式**（每被试每条件一行）

### 核心命门
1. **Mauchly球形检验**：检验球形假设
2. 球形违背（p<.05）→ **必须报告Greenhouse-Geisser校正**的F和p（或Huynh-Feldt）
3. 也可直接报告多元结果（Pillai's trace），不依赖球形假设
4. 事后检验用配对t检验 + Bonferroni校正

### 代码模板

```python
import pingouin as pg

# 数据需为长格式：subject, condition, Y
aov = pg.rm_anova(data=df_long, dv='Y', within='condition',
                  subject='subject_id', detailed=True)
print(aov)
# 关注：sphericity（球形假设）, p-GG-corr（Greenhouse-Geisser校正p值）

# 事后检验
pt = pg.pairwise_ttests(data=df_long, dv='Y', within='condition',
                        subject='subject_id', padjust='bonf')
print(pt)
```

### 报告写法
- "Mauchly's test indicated that the assumption of sphericity was violated, χ²=..., p=..., therefore Greenhouse-Geisser corrected tests are reported (ε=...)."
- 报告校正后的F(df1, df2)=..., p=..., η²p=...

---

## 类型5：基础混合设计（Standard Mixed / Mixed ANOVA）

### 识别特征
- 同时包含被试间变量（如实验组/控制组）和被试内变量（如前测/后测）
- 最常见场景：干预实验的Pre-post设计

### 统计方法
- 混合ANOVA（Mixed ANOVA / Split-Plot ANOVA）
- 工具：`pingouin.mixed_anova`
- 数据为长格式

### 核心命门
1. **组间×时间交互效应是核心**：这是证明干预有效的唯一指标
2. 交互显著 → 做简单效应：分别在各组内检验时间效应，或在各时间点检验组间差异
3. 交互不显著 → 时间主效应显著不能证明干预有效（可能是成熟/练习效应）
4. 球形检验同样适用于被试内效应

### 代码模板

```python
import pingouin as pg

# df_long: subject_id, group(被试间), time(被试内), Y
aov = pg.mixed_anova(data=df_long, dv='Y', within='time',
                     between='group', subject='subject_id')
print(aov)
# 关注 Interaction 行的F和p

# 简单效应：实验组内前后测
pg.pairwise_ttests(data=df_long[df_long.group=='treatment'],
                   dv='Y', within='time', subject='subject_id')
```

### 报告写法
- 核心报告："A significant group × time interaction was found, F(..., ...)=..., p=..., η²p=..."
- 交互显著后报告简单效应
- 交互不显著时，不做因果性结论

---

## 类型6：多情境混合设计（Multi-Topic Mixed / Crossed LMM）

### 识别特征
- 组间操纵 + 被试对**多个不同Topic/情境/题目**分别作答
- 被试和Topic是**交叉**的（每个被试答所有Topic，每个Topic被所有被试作答）
- 例：被试随机分配到AI有/无思考条件，然后对5个不同健康话题各评价一条AI建议

### 统计方法
- 交叉随机效应混合模型（Crossed Random Effects LMM）
- 被试ID和Topic ID同时设为**交叉随机效应**
- 实验条件为固定效应
- 工具：`statsmodels.MixedLM`（需分别指定两个随机效应，或用R的lme4）

### 核心命门
1. **被试ID和Topic ID必须同时为随机效应**，两者交叉
2. 检验操纵效应在不同Topic下是否稳健（可加Topic随机斜率）
3. 忽略Topic变异 → 相当于把Topic当固定物，结果不可推广
4. 模型可能不收敛，需简化随机效应结构

### 代码模板

```python
from statsmodels.regression.mixed_linear_model import MixedLM
import statsmodels.api as sm

# Crossed random effects: subject_id 和 topic_id
# statsmodels的MixedLM对交叉随机效应支持有限，可用以下方式：
# 方法：用vc_formula指定方差成分
model = MixedLM.from_formula(
    'Y ~ condition',
    groups='subject_id',
    vc_formula={'topic_var': '0 + C(topic_id)'},
    data=df
)
result = model.fit()
print(result.summary())

# 若statsmodels不收敛，建议用R lme4:
# lmer(Y ~ condition + (1|subject_id) + (1|topic_id), data=df)
```

### 报告写法
- 说明交叉随机效应结构
- 报告固定效应B, SE, t, p（t>|2|视为显著，或用Satterthwaite df）
- 报告被试和Topic的随机截距方差
- 说明效应在Topic间的稳健性

---

## 类型7：复杂机制检验（Complex Mechanism / SEM）

### 识别特征
- 核心构念用多题项量表测量（潜变量）
- 需要同时检验多重中介路径、多因变量
- 需要检验测量模型的质量（组合信度、区分效度）

### 统计方法
- 结构方程模型（SEM）
- 测量模型：CFA（验证性因子分析）
- 结构模型：路径分析/全模型
- 工具：Python `semopy`，R `lavaan`

### 核心命门
1. **测量模型先于结构模型**：测量模型不达标，结构系数不可信
2. **组合信度 CR > .70**
3. **平均方差提取 AVE > .50**
4. **区分效度**：每个构念的√AVE > 该构念与其他构念的相关系数
5. **模型拟合**：CFI > .90, TLI > .90, RMSEA < .08（SRMR < .08）
6. 中介效应用Bootstrap CI

### 代码模板（semopy）

```python
from semopy import Model, stats

# 测量模型 + 结构模型
model_desc = """
    # 测量模型
    M =~ item1 + item2 + item3
    Y1 =~ y1_1 + y1_2 + y1_3
    Y2 =~ y2_1 + y2_2 + y2_3

    # 结构模型
    M ~ X1 + X2 + X1:X2
    Y1 ~ M + X1 + X2
    Y2 ~ M + X1 + X2
"""
model = Model(model_desc)
model.fit(df)
print(model.inspect())

# 拟合指标
fit = stats.calc_stats(model)
print(fit.T)
```

### 报告写法
- 先报告测量模型：CFA拟合指标、CR、AVE、区分效度表
- 再报告结构模型：路径系数、Bootstrap CI、模型拟合
- 测量模型不达标时，禁止解释结构路径

---

## 设计类型快速判断流程图

```
被试是否只参与一个条件？
├─ 是（组间）
│   ├─ 被试是否嵌套在自然群体中？ → 类型2（HLM）
│   ├─ 每条件是否有多套不同刺激材料？ → 类型3（LMM）
│   └─ 否 → 类型1（ANOVA）
└─ 否（被试参与多个条件）
    ├─ 是否有组间变量（如实验组/控制组）？
    │   ├─ 被试是否对多个Topic作答？ → 类型6（Crossed LMM）
    │   └─ 否（前后测） → 类型5（Mixed ANOVA）
    └─ 无组间变量
        └─ 类型4（Repeated Measures ANOVA）

是否需要检验潜变量/多重中介的测量模型？
└─ 是 → 类型7（SEM），可与上述设计叠加
```
