# Provider 与合并规则

## 目录

- [联网授权门](#联网授权门)
- [豆包运行时与配置责任](#豆包运行时与配置责任)
- [级联](#级联)
- [字段优先级](#字段优先级)
- [匹配门槛](#匹配门槛)
- [证据状态](#证据状态)

## 联网授权门

`enrich` 默认离线。增加 `--online` 前，向用户说明将发送的字段和 provider：DOI 精确
查询发送 DOI；题名检索可能发送题名、作者和年份。不得发送正文、摘要、研究数据、
邮箱、私有链接或其他无关字段。

未发表题名、保密项目、受合同保护材料或用户标记为敏感的记录，保持离线或只使用用户
认可的机构内部 provider。用户已经明确要求对公开出版物联网核验时，无需重复询问；
否则先取得许可。

## 豆包运行时与配置责任

豆包应用发布者在后台注册和测试 MCP/OpenAPI 工具，普通用户不负责配置服务，也不得在
对话中提交 API key。skill 在调用前检查当前应用实际挂载的能力，并按以下逻辑名称路由：

- `search_cn_bibliography`：中文期刊书目检索，可由 Qinyan/Wanfang 或机构 MCP 实现；
- 学术检索工具：DOI 和开放学术元数据查询；
- 网页读取工具：读取 DOI 注册机构、出版社或期刊官方页面；
- 通用搜索工具：只用于定位官方来源，搜索结果摘要不能作为字段证据。

工具的真实名称可由后台做别名映射。缺少中文工具时使用结构化导出/DOI 回退并联系应用
管理员，不向普通用户索取 endpoint、MCP 配置或 secret。

## 级联

1. 有 DOI：Crossref `/works/{doi}`；失败后 DataCite `/dois/{doi}`。
2. 无 DOI 且为中文记录：使用豆包已挂载的 `search_cn_bibliography` 逻辑工具；用户已
   提供 CNKI/Wanfang 结构化导出时优先保留并核对该证据。工具缺失则请求结构化导出或
   DOI，Crossref/OpenAlex 只作补充。
3. 无 DOI 且为英文记录：Crossref bibliographic search，随后 OpenAlex。
4. 生物医学记录可额外接 PubMed；数据集、软件和非期刊 DOI 优先保留 DataCite。

Crossref、DataCite 和 OpenAlex 基础查询通常不要求用户 API key，但应设置超时、重试、
限流和可选的 `mailto`/机构身份。中文 provider 的 key 只通过豆包平台密钥管理、MCP
服务端 secret 或开发者隔离测试环境注入，不能由普通用户在会话中提供。

脚本保持 TLS 证书校验开启；如果 Python 默认 CA 路径不可用，会优先使用已安装的
`certifi`，也可通过 `SSL_CERT_FILE` 指定机构 CA。不要用关闭证书校验的方式绕过错误。

## 字段优先级

精确 DOI 元数据 > 用户提供的结构化导出 > 已验证中文 provider 的精确标题匹配 > Crossref/
OpenAlex 标题搜索 > 用户纯文本解析。

合并规则：

- 只填充空字段；
- 用户已有值与 provider 值不一致时不覆盖，写入 `conflicts`；
- DOI 新出现后必须再次精确解析；
- provider 返回当前年份或空作者时不得接受；
- `authors`、`title`、`year`、`venue` 的来源逐字段记录；
- 不以 DOI 字符串格式正确代替 DOI 存在性验证。

## 匹配门槛

- 标题归一化后相似度至少 `0.78`；中文 provider 可放宽到 `0.72`，但必须同时满足
  年份差不超过 1 年或作者至少一人重合；
- DOI 精确命中以规范化 DOI 相等为准；
- 只有期刊名相似、只有第一作者相似或只有年份相同，不足以合并；
- 无法通过门槛时保留候选结果到 `candidates`，原记录标为 `unresolved`。

## 证据状态

```text
exact        DOI 精确解析且标题/作者一致
corroborated 无 DOI，但多来源检索匹配
partial      已获取部分字段，仍有缺失
conflict     用户字段与权威来源冲突
unresolved   没有足够证据
rejected     provider 记录明确不是同一文献
```

`missing_fields` 只表示当前缺失，不表示文献不存在。文章的最小可交付字段为标题、
作者、年份、期刊；卷、期、页码和 DOI 视来源与目标规范补齐。
