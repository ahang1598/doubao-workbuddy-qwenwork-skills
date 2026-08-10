# pytest API starter

1. 安装：`python3 -m pip install -r requirements.txt`
2. 设置：`QA_BASE_URL=https://test.example.test`，鉴权接口再设置 `QA_API_TOKEN`
3. 执行：`pytest`
4. 写接口默认跳过；仅在已确认测试环境和副作用后设置 `QA_ALLOW_WRITES=1`

`api-operations.json` 由 `scripts/generate_api_manifest.py` 或 `scripts/scaffold_api_tests.py` 生成。
