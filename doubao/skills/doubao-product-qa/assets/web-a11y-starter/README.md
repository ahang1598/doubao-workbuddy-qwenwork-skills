# axe + Playwright 可访问性 starter

```bash
npm install
QA_BASE_URL=http://127.0.0.1:3000 QA_A11Y_ROUTES=/,/login npm test
```

PowerShell：

```powershell
npm install
$env:QA_BASE_URL = "http://127.0.0.1:3000"
$env:QA_A11Y_ROUTES = "/,/login"
npm test
```

- 默认门禁 `critical,serious`；用 `QA_A11Y_GATE_IMPACTS` 调整。
- 自动扫描之外，`incomplete` 会进入人工检查清单。
- 豁免必须写入 `a11y-allowlist.json`，包含原因和到期日；过期豁免自动失效。
- 默认不截图。只有用户已选择允许截图时才设置 `QA_CAPTURE_SCREENSHOTS=1`。
