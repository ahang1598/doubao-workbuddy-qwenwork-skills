# 采集任务 API 参考

本页为 `linkfox-plugin-web-data-crawler` 技能调用的底层接口规格。SKILL.md 面向"怎么用"的决策层，本文档面向"接口精确格式"。

## 调用规范

- **请求地址**：`{LINKFOX_TOOL_GATEWAY}/linkFoxApp/api/agent/crawlTask/startCrawlTask`
  - `LINKFOX_TOOL_GATEWAY` 默认 `https://tool-gateway.linkfox.com`，可用环境变量覆盖（如测试环境）。
  - > 网关需将 `/linkFoxApp/api/agent/crawlTask/**` 路由到 linkfoxapp-agent-backend；若网关使用改写后的路径，请同步修改本文件与 `scripts/run_crawl.py` 中的 path。
- **请求方式**：POST，`Content-Type: application/json`
- **认证方式**：Header `Authorization: <api_key>`，`api_key` 从环境变量 `LINKFOX_AGENT_API_KEY` 读取（值为用户 accessToken，后端复用 user-service 校验并解析 memberId）。未配置时提示用户前往 https://skill.linkfox.com/linkfoxskills/guide.htm 申请。
- **目标用户（memberId）由后端从 Authorization 解析**，调用方不要在 body 传 `userId` / `accessToken`（传了也会被忽略）。

### 请求体（StartCrawlTaskParam）

| 参数 | 类型 | 必填 | 说明 |
|------|------|----|------|
| workflowJson | string | 是 | 采集工作流 JSON **字符串**（由 `sites/<site>/base-full.json` 模板填充 tabUrl/tabKey 后序列化得到），DSL 规范见 [`tools/INDEX.md`](../tools/INDEX.md) |

> `workflowJson` 是**字符串**，不是嵌套对象：先得到 workflow 对象，再 `JSON.stringify` 成字符串塞进 body。后端按字符串透传给浏览器插件执行。

```json
{
  "workflowJson": "{\"workflowName\":\"Amazon US 商品详情页数据采集\",\"steps\":[...]}"
}
```

### 响应（CrawlTaskResult）

| 字段 | 类型 | 说明 |
|------|------|------|
| taskId | string | 任务 ID（同步接口也会返回，便于追踪） |
| status | string | `SUCCESS` / `FAILED` / `TIMEOUT`（同步接口不返回 `PENDING`/`RUNNING`） |
| data | string | 采集结果数据；`status=SUCCESS` 时非空，内容为插件回传的采集结果（字段来自工作流 EXTRACT 步骤的 `extractField`） |
| errorMsg | string | `status=FAILED`/`TIMEOUT` 时非空，描述原因（如"目标用户客户端不在线"、采集失败、等待超时） |

### HTTP 状态码

| HTTP | 含义 | 处理 |
|------|------|------|
| 200 | `status=SUCCESS`，采集成功 | 解析 `data` |
| 503 | `status=FAILED`/`TIMEOUT`：客户端不在线、采集失败或等待超时（同步阻塞上限约 300s） | 读 `errorMsg`，按下方"失败处理"决定是否重试 |
| 400 | 参数非法（如缺 Authorization、workflowJson 为空、token 校验失败） | 读 `errorMsg`，修参后重试，**不计入网络层重试** |

### 失败处理

| status / 场景 | 是否重试 |
|---|---|
| `TIMEOUT`（等待回执超时，300s） | 可重试，最多 3 次，退避 1s→2s→4s |
| `FAILED` + "客户端不在线" | 用户浏览器插件未连接 WS，**不要重试**，提示用户打开插件并登录后重试 |
| `FAILED` + 其它采集错误 | 单点确定性错误，**不重试**，检查工作流选择器 |
| HTTP 400 | 参数/鉴权问题，**不重试**，修参 |
| 网络异常 / 5xx / 限流 | 瞬时错误，最多 3 次，退避 1s→2s→4s |

## curl 示例

```bash
# 先把模板填好 tabUrl/tabKey 落成 workflow.json，再序列化为字符串发出去
WORKFLOW=$(python -c "import json;print(json.dumps(open('workflow.json',encoding='utf-8').read(),ensure_ascii=False))")

curl -X POST "$LINKFOX_TOOL_GATEWAY/linkFoxApp/api/agent/crawlTask/startCrawlTask" \
  -H "Authorization: $LINKFOX_AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"workflowJson\":$WORKFLOW}"
```

> 实际调用请用 `python scripts/run_crawl.py`，不要手搓 curl 拼字符串。

---

## Feedback API

> 与采集执行分离，仅用于上报本 skill 的使用反馈。端点与上方采集 API 不同，请勿混用 base URL。

- **POST** `https://skill-api.linkfox.com/api/v1/public/feedback`
- **Content-Type:** `application/json`

```json
{
  "skillName": "linkfox-plugin-web-data-crawler",
  "sentiment": "POSITIVE",
  "category": "OTHER",
  "content": "说明用户说了什么/期望什么、实际发生了什么、为什么是问题/赞赏"
}
```

- `sentiment`：`POSITIVE` / `NEUTRAL` / `NEGATIVE`
- `category`：`BUG` / `COMPLAINT` / `SUGGESTION` / `OTHER`