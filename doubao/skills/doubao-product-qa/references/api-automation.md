# API 自动化与 OpenAPI 驱动生成

## 目录

- [目标](#目标)
- [框架选择](#框架选择)
- [OpenAPI 工作流](#openapi-工作流)
- [测试设计](#测试设计)
- [执行安全](#执行安全)
- [框架 starter](#框架-starter)
- [结果与报告](#结果与报告)

## 目标

把 PRD、接口文档和 OpenAPI/Swagger 转成可追踪的接口覆盖，而不是只生成一个能发请求的项目。每个自动化用例必须回指需求或接口 operation，并验证状态码、响应契约和相关业务副作用。

## 框架选择

先检测项目：

```bash
python3 scripts/inspect_api_project.py --project <项目目录> --json
```

选择顺序：

1. 项目已有 API 测试框架；
2. Python 工程使用 pytest + httpx；
3. Node.js/Express/Nest 工程使用 Supertest + Vitest/Jest；
4. Java/Spring 工程使用 REST Assured + JUnit 5/TestNG；
5. 只有远程接口且没有代码栈时，结合团队维护语言选择一套，不同时生成三套长期维护。

Supertest 可对远程 base URL 发请求，但服务工程允许时优先导入 app/server 做无端口集成测试。项目已有 Playwright APIRequestContext、Karate、Postman/Newman 等稳定体系时，不为套用 starter 强制替换。

## OpenAPI 工作流

先从文档生成跨框架 operation 清单和覆盖矩阵：

```bash
python3 scripts/generate_api_manifest.py openapi.yaml \
  --output qa-results/feature/api-operations.json \
  --coverage qa-results/feature/api-coverage.csv
```

生成内容包括：

- method、path、operationId、tags；
- 必填 path/query/header/cookie 参数及样例；
- request body 样例；
- 成功状态和可内联的响应 schema；
- happy、缺少必填项、缺少 body、未鉴权基础场景；
- 安全方法与写方法执行策略。

生成器只解析本地 `$ref`。外部 `$ref`、callback、复杂 discriminator、上传流、多段表单或业务前置链路需要人工/Agent 补全，并在覆盖矩阵中标记。

需要独立 starter 时运行：

```bash
python3 scripts/scaffold_api_tests.py \
  --project <项目目录> \
  --framework auto \
  --openapi <openapi.json-or-yaml> \
  --output <新目录>
```

脚本拒绝覆盖已存在目录。对成熟项目，优先把 `api-operations.json` 和必要测试逻辑局部接入现有 test tree，不创建平行工程。

## 测试设计

生成清单只是起点。按风险补充：

- **鉴权与数据归属**：无 token、过期、撤销、错角色、横向越权、旧会话；
- **输入域**：缺失/null/空串、长度和数值边界、非法枚举、格式、编码、超大 payload；
- **资源状态**：不存在、已删除、已关闭、重复、冲突版本；
- **幂等与重试**：幂等键重复、客户端超时后重试、并发写入、重复 webhook；
- **分页与排序**：首尾页、空页、游标失效、重复/遗漏、并发插入后的稳定性；
- **一致性**：响应、数据库、事件、缓存、库存/额度和下游通知；
- **协议**：content type、缓存头、限流头、错误结构、request ID、版本兼容；
- **契约演进**：字段新增/删除、必填变化、类型变化、枚举收窄和旧客户端兼容。

业务写流程使用唯一数据命名空间并实现清理；涉及支付、通知、删除、库存或真实第三方时必须先确认环境和副作用。

## 执行安全

三个 starter 都遵循：

- 必须显式设置 `QA_BASE_URL`，不因 OpenAPI 中存在 server URL 就自动连接；
- GET/HEAD/OPTIONS 默认可执行；
- POST/PUT/PATCH/DELETE/TRACE 默认跳过，确认测试环境后才设置 `QA_ALLOW_WRITES=1`；
- 鉴权 token 只从 `QA_API_TOKEN` 等环境变量读取，不写入代码、清单或报告；
- TLS 校验默认开启，不通过关闭 TLS 来掩盖环境证书问题；
- 请求/响应日志对 token、cookie、手机号、邮箱和业务敏感字段脱敏。

## 框架 starter

### pytest

复制 `assets/api-starters/pytest/`。支持 httpx、参数化 case、JSON Schema 校验和 JUnit 输出。

```bash
python3 -m pip install -r requirements.txt
QA_BASE_URL=https://test.example.test pytest
```

PowerShell：

```powershell
python -m pip install -r requirements.txt
$env:QA_BASE_URL = "https://test.example.test"
pytest
```

### Supertest

复制 `assets/api-starters/supertest/`。支持 Vitest 动态用例、AJV schema 校验和 JUnit 输出。

```bash
npm install
QA_BASE_URL=https://test.example.test npm test
```

PowerShell：

```powershell
npm install
$env:QA_BASE_URL = "https://test.example.test"
npm test
```

### REST Assured

复制 `assets/api-starters/restassured/`。支持 JUnit 5 dynamic tests、JSON Schema Validator 和 Surefire 报告。

```bash
QA_BASE_URL=https://test.example.test mvn test
```

PowerShell：

```powershell
$env:QA_BASE_URL = "https://test.example.test"
mvn test
```

## 结果与报告

接口报告至少记录：

- 接口文档来源、版本、base URL（脱敏）和构建；
- operation 总数、已生成/已执行/跳过/失败数；
- 每个失败的 case ID、method/path、状态、响应摘要和 request ID；
- schema 失败字段和兼容影响；
- 写入副作用及清理状态；
- 未覆盖 operation 和原因；
- 产品失败、契约问题、环境问题、测试数据问题和脚本问题分类。

不能把 OpenAPI schema 通过等同于业务正确，也不能把未开启写测试的接口算作已覆盖。
