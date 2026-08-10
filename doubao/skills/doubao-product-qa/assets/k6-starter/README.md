# k6 性能测试 starter

该模板将负载模型、业务流程、阈值和摘要分开。默认不会连接任何环境，也不会执行写请求。

```bash
mkdir -p artifacts
QA_BASE_URL=https://test.example.test \
QA_PROFILE=smoke \
QA_P95_MS=500 \
QA_ERROR_RATE=0.01 \
QA_BUSINESS_SUCCESS_RATE=0.99 \
k6 run run.js
```

PowerShell：

```powershell
New-Item -ItemType Directory -Force artifacts | Out-Null
$env:QA_BASE_URL = "https://test.example.test"
$env:QA_PROFILE = "smoke"
$env:QA_P95_MS = "500"
$env:QA_ERROR_RATE = "0.01"
$env:QA_BUSINESS_SUCCESS_RATE = "0.99"
k6 run run.js
```

可选 profile：`smoke/load/stress/spike/soak`。通过 `QA_VUS`、`QA_RATE`、`QA_DURATION`、`QA_RAMP` 调整，不要未经容量授权直接扩大负载。

没有已确认 SLO 时，设置 `QA_BASELINE_ONLY=1` 只采样而不声称达标。非 GET/HEAD/OPTIONS 请求还必须显式设置 `QA_ALLOW_WRITES=1`。
