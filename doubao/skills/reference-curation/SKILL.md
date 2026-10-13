---
name: reference-curation
description: 整理参考文献，核验 DOI 与元数据，输出带证据、冲突、待核实标记的规范结果与引用草稿；支持 BibTeX/JSON/JSONL 书目整理，不做全文下载、会议纪要、论文代写、绕过受限数据库。
---

# Reference Curation

将来源转换为可追溯的规范化记录，再做验证和补全。所有自动填充必须保留来源证据；
不能用模型记忆、搜索摘要或当前年份填补缺失字段。

本 Skill 的核心交付物是规范化书目数据和核验队列。内置 `render` 只生成常见期刊
条目的引用草稿，不是 GB/T、APA、MLA 的完整实现，也不得作为最终合规书目。最终
样式由成熟 CSL/citeproc 类引擎生成，再由 `paper-formatting` 应用到文档版式、字段和
交叉引用。

## 触发与不触发

**必须触发**：用户要求清理、规范化、核验、补全或去重参考文献记录，或要求从 DOI、BibTeX、JSON/JSONL 生成带来源证据的引用草稿。

**禁止触发**：仅要求论文全文阅读/下载、会议纪要、论文代写、普通翻译、通用网页搜索，或要求绕过登录、验证码、付费墙和访问控制。若请求只涉及最终 DOCX/PDF 版式，交给 `paper-formatting`。

## 快速路由

1. 接收 `.bib`、Zotero 导出 JSON、JSON/JSONL 记录。
2. 先做离线规范化。豆包生产环境同时预检应用已挂载的学术检索、网页读取和中文期刊
   工具；普通用户不配置 MCP/OpenAPI，也不在对话中提供 API key。联网前说明会把题名、
   作者、年份和 DOI 发给哪些 provider，并取得必要许可；未发表、保密或受合同保护的
   材料默认保持离线，或只使用用户认可的机构内部 provider。
3. 用户已授权联网时增加 `--online`。脚本对每条记录自动判断是否需要补全：
   - 有 DOI（包括 `doi:`、`https://doi.org/` 形式）时立即做精确验证；
   - 缺作者、年份、期刊、卷期、页码或 DOI，且有标题和作者/年份时做标题检索；
   - 发现新的 DOI 后再次执行精确验证，不需要用户额外下达“验证 DOI”指令。
4. 中文条目优先使用应用发布者在豆包后台绑定的 `search_cn_bibliography` 逻辑工具，
   或用户提供的 CNKI/Wanfang 结构化导出。逻辑工具可映射到获授权的 Qinyan/Wanfang、
   机构数据库 MCP 或 OpenAPI；未挂载时使用 DOI 精确查询或建立待核实队列，不承诺
   中文数据库覆盖。
5. 仅补充空字段。已有值与权威来源冲突时保留原值，并将冲突写入 `conflicts` 和
   `verification: conflict`，交给用户确认。
6. 只需快速检查常见期刊条目时运行 `render`，选择 `gbt-article-draft`、
   `apa-article-draft` 或 `mla-article-draft`。输出始终带草稿声明；非期刊类型、未验证
   记录和缺失字段进入人工/样式引擎队列。

## 豆包中文期刊获取门

中文期刊元数据覆盖不能只依赖 Crossref，也不能假定目标平台已经提供中文数据库接口。
执行中文条目时按以下顺序处理：

1. 先预检当前豆包应用是否挂载符合约定的 `search_cn_bibliography` 工具。工具端点、
   认证 Header、密钥、请求映射和限流由应用发布者/管理员配置并测试，不能交给普通用户。
2. 已有 DOI 时，优先通过已挂载的学术检索工具精确查询，再读取 DOI 注册机构或出版者
   官方页面复核；这只完成 DOI 级核验，不等于中文数据库覆盖完成。
3. 无 DOI 且中文工具可用时，只发送题名、作者、年份等最小检索字段。工具返回结果必须
   经过标题、作者、年份匹配门，并记录 provider、记录定位符和检索时间。
4. 中文工具未挂载、认证失败、限流或不可用时，不向用户索要 API key。请求用户上传
   CNKI/Wanfang 的 BibTeX、RefWorks、EndNote、CSV 等结构化导出，或补充 DOI；仍需实时
   数据库核验时，提示联系应用管理员启用中文期刊检索工具。
5. Crossref/OpenAlex 和通用网页搜索只能作为补充来源。中文 provider 不可用或结果
   冲突时，交付待核实队列，而不是把近似标题或搜索摘要当成同一篇。

豆包工具契约、Qinyan 本地开发适配、限流和故障处理见
[references/chinese-providers.md](references/chinese-providers.md)。通用 API 和 DOI
合并规则见 [references/provider-policy.md](references/provider-policy.md)。

## 规范化数据契约

脚本的每条输出记录至少包含：

```json
{
  "id": "stable-local-id",
  "type": "article",
  "title": "...",
  "authors": [{"family": "...", "given": "...", "raw": "..."}],
  "year": 2024,
  "venue": "...",
  "volume": null,
  "issue": null,
  "pages": null,
  "doi": null,
  "url": null,
  "language": "zh",
  "source_evidence": [],
  "verification": "unresolved",
  "missing_fields": [],
  "conflicts": [],
  "warnings": []
}
```

作者的 `raw` 始终保留。中文姓名不要自动拼音化；英文作者不能从邮箱、标题或引文
上下文推断。`year` 缺失时保持 `null`，不使用当前年份。

## 本地开发与回归命令

```bash
# 默认离线，只做解析、规范化和待核实标记
python3 scripts/reference_curation.py enrich \
  --input references.bib \
  --output references.normalized.jsonl

# 用户授权后联网核验公开条目
python3 scripts/reference_curation.py enrich \
  --input references.bib \
  --output references.normalized.jsonl \
  --online

# 中文 provider 的直连参数只用于发布者/开发者在隔离环境中做适配回归；密钥必须来自
# 环境变量或平台密钥，不得写入命令历史、文件、日志或对话。
# 豆包生产运行通过后台挂载的 MCP/OpenAPI 工具调用，不让普通用户执行此命令或提供密钥。

# 生成常见期刊条目草稿；不是最终标准书目
python3 scripts/reference_curation.py render \
  --input references.normalized.jsonl \
  --style gbt-article-draft \
  --output references.draft.md
```

## 质量门

- `exact`：DOI 已由 Crossref 或 DataCite 精确解析，且 DOI/标题一致。
- `corroborated`：无 DOI 的记录由检索结果匹配，并有可追溯 provider 证据。
- `partial`：只补到部分字段，仍有缺失或来源不足。
- `conflict`：用户值与权威来源冲突，必须人工确认。
- `unresolved`：没有可接受的证据，不能作为已完成引用交付。

交付前检查重复 DOI、重复标题、缺失必填字段和文内/文后 orphan 引用。输出中区分
`[Script]` 自动检查、`[LLM]` 语义判断和 `[Manual]` 用户确认项。要求最终标准书目时，
把已核验数据交给成熟样式引擎；要求写入 DOCX/LaTeX、处理悬挂缩进、域和交叉引用时，
交给 `paper-formatting`。

## 资源

- [references/chinese-providers.md](references/chinese-providers.md)：豆包中文期刊工具契约、
  发布者配置责任、Qinyan 本地开发适配和无工具时的用户回退文案。
- [references/provider-policy.md](references/provider-policy.md)：Crossref/DataCite/OpenAlex
  级联、字段合并、匹配阈值和 DOI 验证规则。
- [scripts/reference_curation.py](scripts/reference_curation.py)：默认离线的解析、规范化、
  验证、可选 provider 调用和期刊条目草稿预览。
- [assets/reference-record.schema.json](assets/reference-record.schema.json)：规范化记录的
  JSON Schema；`verify` 对 required、enum、ID、数组和字段类型执行等价离线校验。
- [assets/chinese-provider.config.example.json](assets/chinese-provider.config.example.json)：
  豆包中文期刊逻辑工具的无密钥部署模板；真实密钥只存于平台密钥管理或 MCP 服务端。
- [assets/sample-references.jsonl](assets/sample-references.jsonl)：可用于离线演示和回归
  测试的中英文样例，不代表已完成验证。
- [tests/routing-cases.json](tests/routing-cases.json)：should-trigger、should-not-trigger、边界与回归题集。
- [tests/run_regression.py](tests/run_regression.py)：离线路由题量、中文 provider 缺失门和凭据不落盘回归。
- [tests/README.md](tests/README.md)：测试证据保存约定。
- [tests/raw-regression.md](tests/raw-regression.md)：命令、stdout、stderr、return code 与断言摘要。

## 脚本契约

`reference_curation.py` 的三个子命令均要求 `--input` 与 `--output`（`verify` 只要求
`--input`）。`enrich` 默认离线；`--online` 与 `--offline` 互斥，`--require-chinese-provider`
仅在中文 provider 必须可用时开启，超时默认 20 秒、重试默认 2 次。密钥禁止使用命令行参数，
仅允许由 `QINYAN_API_KEY` 环境变量或平台密钥注入。`enrich` 成功返回 0；中文 provider
缺失且启用强制门时返回 2；输入或运行错误返回 1。`render` 对需要人工复核或非期刊类型返回 2，
`verify` 发现 unresolved/conflict/缺失字段返回 2。常用回归命令：

```bash
python3 tests/run_regression.py
```
