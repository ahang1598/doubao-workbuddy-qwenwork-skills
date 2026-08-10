# 只读分析请求模板

```yaml
platform: oceanengine
advertiser_id: <目标广告账户>
intent: overview | monitor | diagnose | longtail | infrastructure | hit_rate
window: today | last_24h | last_7d | <自定义>
level: account | campaign | adgroup | ad | creative
primary_kpi:
  name: <浅层 CPA / 深层 CPA / 次留成本 / ROI 等>
  target: <可选；未填则中性分析>
  tolerance: <可选>
sample_threshold: <可选>
create_protection: <可选，例如 48h>
output_focus: <例如成本预警、基建、跑出率、长尾>
```

此模板只用于读取与分析，不授予任何写入权限。
