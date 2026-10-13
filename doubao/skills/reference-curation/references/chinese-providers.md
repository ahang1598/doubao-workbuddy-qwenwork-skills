# 豆包中文期刊 Provider

## 目录

- [责任边界](#责任边界)
- [生产工具契约](#生产工具契约)
- [豆包运行时路由](#豆包运行时路由)
- [证据与匹配](#证据与匹配)
- [故障处理](#故障处理)
- [本地开发适配器](#本地开发适配器)

## 责任边界

豆包生产环境采用“应用配置一次，用户直接使用”的方式：

- 应用发布者/管理员负责在后台注册 MCP Server 或 OpenAPI、配置认证 Header/secret、
  映射请求与响应 schema、设置超时和限流，并完成发布前测试；
- skill 只依赖稳定的逻辑工具契约，不绑定某一家供应商；
- 普通用户只提出核验请求，不配置 MCP/OpenAPI，也不能在对话、附件或日志中粘贴 API
  key；
- 学校或机构采用自带授权时，也应由管理员把凭据放入平台密钥管理或 MCP 服务端。

Qinyan/Wanfang、机构图书馆数据库和其他获授权服务都可以实现同一逻辑工具。更换供应商
时只修改后台映射，不修改用户提示词或规范化数据层。

## 生产工具契约

主逻辑工具名为 `search_cn_bibliography`。豆包中实际挂载的工具名可以不同，但应用配置
必须显式记录别名映射，且工具描述要说明“检索中文学术期刊书目元数据，不下载全文”。

建议输入 schema：

```json
{
  "title": "数字化学习资源研究",
  "authors": ["张三", "李四"],
  "year": 2024,
  "doi": null,
  "sources": ["wanfang"],
  "max_results": 5
}
```

只允许发送完成书目匹配所需的最小字段。不要发送正文、摘要、邮箱、研究数据、私有链接
或完整未公开材料。

建议输出 schema：

```json
{
  "status": "ok",
  "provider": "wanfang",
  "records": [
    {
      "provider_record_id": "opaque-id",
      "title": "数字化学习资源研究",
      "authors": ["张三", "李四"],
      "year": 2024,
      "venue": "现代教育技术",
      "volume": "34",
      "issue": "6",
      "pages": "1-8",
      "doi": null,
      "url": null,
      "match_score": 0.91,
      "retrieved_at": "2026-08-07T00:00:00Z"
    }
  ]
}
```

`status` 只能使用 `ok`、`no_match`、`auth_required`、`rate_limited`、`unavailable` 或
`invalid_response`。`no_match` 只表示本次查询没有可靠候选，不能解释为“文献不存在”。

## 豆包运行时路由

1. 识别中文标题、中文作者或 `language: zh` 后，检查当前应用是否挂载
   `search_cn_bibliography` 或其已登记别名。
2. 有 DOI 时先走已挂载的学术检索/DOI 精确查询，再读取 DOI 注册机构或出版者官方页面；
   中文工具可用于交叉核验，但不是 DOI 成立的必要条件。
3. 无 DOI 且中文工具可用时调用工具，最多取 5 个候选，然后按标题、作者和年份匹配门
   合并。通用网页搜索只能定位官方页面，不可用搜索摘要直接补字段。
4. 工具缺失或返回失败状态时保留原记录，添加对应 warning，并进入用户文件回退。
5. 用户提供 CNKI/Wanfang 结构化导出后，保留原始条目，以 `user_file`、`cnki` 或
   `wanfang` 记录证据，不绕过登录或验证码抓取网页。

普通用户的缺服务提示统一为：

> 当前应用未配置中文期刊数据库核验服务。你可以上传知网/万方导出的 BibTeX、
> RefWorks、EndNote 或 CSV 文件，也可以补充 DOI；如需实时数据库核验，请联系应用
> 管理员启用中文期刊检索工具。

不得把“请提供 API key”“请在豆包中自行配置 MCP”作为普通用户的默认下一步。

## 证据与匹配

每个中文 provider 结果至少写入：

```json
{
  "provider": "wanfang",
  "locator": "record=opaque-id",
  "retrieved_at": "2026-08-07T00:00:00Z",
  "match_score": 0.91
}
```

不要写入 API key、Authorization header 或含个人信息的完整查询参数。标题相似度不足、
年份相差超过 1 年且作者不重合时，不得合并。已有 DOI 可以达到 `exact`，但仍不得据此
声称“已完成中文数据库覆盖”。

## 故障处理

- 工具未挂载：标记 `chinese_provider_missing`，使用上面的用户文件回退提示；
- `auth_required`/`401`/`403`：标记 `chinese_provider_auth_required`，提示管理员修复后台
  凭据，不能向普通用户索取密钥；
- `rate_limited`/`429`：由工具端指数退避；超过重试次数后保留输入并标记限流；
- `unavailable`、`5xx` 或超时：保留输入，允许 DOI 精确查询，最后进入待核实队列；
- `invalid_response`：拒绝合并结果并记录 schema 错误；
- `no_match`：标记 `unresolved`，请求结构化导出或 DOI，不宣称文献不存在。

发布前必须覆盖：成功、无结果、401/403、429、5xx/超时、畸形响应、工具未挂载和敏感
题名禁止外发八类测试。

## 本地开发适配器

仓库脚本保留 Qinyan 直连参数，只用于应用发布者/开发者在隔离环境中验证 provider
wrapper，不代表豆包面向用户的交互：

```bash
QINYAN_API_KEY="$QINYAN_API_KEY" \
python3 scripts/reference_curation.py enrich \
  --input refs.jsonl --output refs.normalized.jsonl \
  --online --qinyan-source wanfang --require-chinese-provider
```

本地测试密钥只放在进程环境或专用密钥管理器中。不得写入 skill、示例 JSON、输出、
日志、截图或版本库。生产环境使用豆包后台挂载的 MCP/OpenAPI 工具，而不是让用户执行
本地命令。
