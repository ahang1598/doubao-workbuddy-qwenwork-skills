# Cookbook · 深度场景 pandas/scipy 模板


挑符合用户场景的用,不必全跑。代码里 `<列名>` 是占位符,按实际数据替换。

### 场景 1:差异归因 / 贡献度分析

需要回答"哪些维度组合偏离整体最大 / 哪个维度对总变化贡献最多"时,标准三步:

```python
import pandas as pd
import numpy as np

# ① 拆维度对比:定位低指标的「维度组合」
pivot = df.pivot_table(values='<metric_col>', index='<dim1_col>',
                       columns='<dim2_col>', aggfunc='mean')
overall = df['<metric_col>'].mean()
deviation = (pivot - overall) / overall  # 相对偏离率

# ② 离群定位:z-score
group_mean = df.groupby('<dim1_col>')['<metric_col>'].transform('mean')
group_std = df.groupby('<dim1_col>')['<metric_col>'].transform('std')
z = (df['<metric_col>'] - group_mean) / group_std
df['is_outlier'] = z.abs() > 2

# ③ 贡献度分解:哪个维度拉低了整体
total_drop = df_now['<metric_col>'].sum() - df_prev['<metric_col>'].sum()
by_dim = (df_now.groupby('<dim1_col>')['<metric_col>'].sum()
          - df_prev.groupby('<dim1_col>')['<metric_col>'].sum())
contribution = by_dim / total_drop  # 各维度对总变化的贡献占比
```

### 场景 2:AB 测试显著性

需要 p-value 或置信区间,仅说"差异明显"不算合规。

```python
from scipy import stats

# ① 连续指标:t 检验
control = df[df['<group_col>']=='A']['<metric_col>']
treatment = df[df['<group_col>']=='B']['<metric_col>']
t, p = stats.ttest_ind(control, treatment, equal_var=False)  # Welch's t

# ② 比例指标:卡方
table = [[150, 850], [180, 820]]  # [[A_conv, A_no], [B_conv, B_no]]
chi2, p, _, _ = stats.chi2_contingency(table)

# ③ 95% CI(差值)
diff = treatment.mean() - control.mean()
se = np.sqrt(treatment.var()/len(treatment) + control.var()/len(control))
ci_low, ci_high = diff - 1.96*se, diff + 1.96*se
```

报告必含三种之一:
- (a) p-value 数值(`p=0.032`)
- (b) 95% CI 是否跨 0(`[0.8%, 3.4%], 不跨 0 → 显著`)
- (c) 显式标"未做检验"+ 理由(样本太小/方差未知)

样本量不足(任一组 N<30)时:不强求 p-value,改报「绝对差 + 建议扩样本」。


## JSON 安全写出 (防 int64 不可序列化 — 最高频脚本错)

`json.dump(kpis)` 直接写 pandas/numpy 结果会 `TypeError: Object of type int64 is not JSON serializable`
(数据全算对了却崩在最后一步)。**写任何 JSON 一律带 `default=`**:

```python
import numpy as np, pandas as pd, json
def _js(o):
    if isinstance(o, np.integer):       return int(o)
    if isinstance(o, np.floating):      return float(o)
    if isinstance(o, (np.bool_, bool)): return bool(o)
    if isinstance(o, pd.Timestamp):     return o.isoformat()
    if hasattr(o, 'tolist'):            return o.tolist()   # numpy array
    return str(o)
json.dump(data, f, ensure_ascii=False, default=_js)
```

千分位格式 `f"{v:,}"` 仅对数字用;`v` 可能是字符串时先 `int(v)` 或确认 dtype,否则
`ValueError: Cannot specify ',' with 's'`。
