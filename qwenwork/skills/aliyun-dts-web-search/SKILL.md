---
name: aliyun-dts-web-search
description: 通过阿里云 DTS-AI 搜索公开网页、发现相关来源并提取指定网页的内容。用户需要联网搜索、查询最新资料或新闻、开展产品或行业调研、查找官方网站或 URL、阅读或抓取网页、比较不同来源、核验事实、汇总网页信息并注明来源，或提到 DTS-AI、WebSearch、WebFetch 时使用。
install_source: official
install_method: download
skill_id: official_yxuD10N6
enabled_at: 1791893792944
version: 1.0.1
name_zh: 网页搜索与网页提取
---

# 阿里云 DTS-AI 网页搜索与网页提取

## 功能与结果保存

使用 `scripts/dts_web.py` 调用 WebSearch 按关键词搜索公开网页，或调用 WebFetch 提取指定 URL 的网页内容。两项功能可以独立使用，也可组合为“先搜索、再提取”的工作流。

搜索和抓取命令默认不保存结果。需要保存调研结果且用户未指定路径时，将结果保存至当前用户主目录下的 `.aliyun-dts/web-search/`。临时数据存放在系统临时目录中。

## 安全与使用限制

- 不得打印、记录或暴露 `DTS_AI_API_KEY`。
- 只能通过 `scripts/dts_web.py` 读取凭据。API Key 缺失、尚未配置或认证失败时，阅读 [DTS-AI 认证](references/dts-ai-authentication.md)。
- 每个用户请求最多抓取五个页面。回退页面和对同一 URL 的手动重复抓取均计入限额；搜索请求和自动传输重试不计入。
- 不得将无法支持结论、不完整或提取失败的内容作为信息依据。

## 运行环境与认证配置

支持 Windows、macOS 和 Linux，需要 Python 3。以下命令均相对于本 `SKILL.md` 所在目录执行；命令中的 `python3` 表示 Python 3 解释器，Windows 可使用 `py -3`。

在不显示密钥、不发送网络请求的情况下检查本地配置：

```bash
python3 scripts/dts_web.py check
```

如果尚未配置 API Key，先阅读 [DTS-AI 认证](references/dts-ai-authentication.md)，再提示用户运行：

```bash
python3 scripts/dts_web.py setup --language <en|zh-CN>
```

## 网页搜索与网页提取流程

### 搜索公开网页

```bash
python3 scripts/dts_web.py search "<entity-or-topic>" --max-results 15
```

需要结构化输出时，使用 `--json`。

每个主题最多发起五次搜索调用（与 `--max-results` 的每页结果数无关），分别用于逐步明确主题、来源范围和尚待核实的具体事实。获得足以支持所需事实的候选来源后即停止搜索；抓取对应页面前，只能将搜索结果视为候选来源。

### 提取单个网页

使用与目标信息相关的关键词：

```bash
python3 scripts/dts_web.py fetch "https://example.com/page" \
  --keywords "<term-1>,<term-2>,<term-3>"
```

默认提取为 `text` 格式。页面包含表格或矩阵时，首次抓取建议使用 `--format markdown`。仅在需要保留 HTML 结构时使用 `--format html`。必须保留目标 URL 的所有路径分段和查询参数。

### 批量提取网页

```bash
python3 scripts/dts_web.py fetch-many \
  "https://example.com/official" \
  "https://example.net/independent-report" \
  --keywords "<term-1>,<term-2>,<term-3>"
```

大多数调研任务提取两至三个页面即可。`fetch-many` 接受二至五个 URL；提取单个页面使用 `fetch`。优先将选定页面合并为一个批次；获得足以支持所需事实的信息后即停止。

## 结果核验与异常处理

选择来源、判断提取结果是否可用、处理抓取失败或组织带链接的答复时，必须阅读并遵守[来源选择与结果评估](references/source-selection-and-result-evaluation.md)。命令报告本地配置、API、网络传输或提取结果异常时，不得立即重复执行。信息不足时，必须说明相关事实尚未核实，不得自行推断。

## 官方 API 文档

- [Web 搜索与提取用例](https://help.aliyun.com/zh/dts/use-cases/use-dtsai-api-for-web-search-and-fetch)
- [WebSearch API](https://help.aliyun.com/zh/dts/developer-reference/api-dtsai-2026-04-01-websearch)
- [WebFetch API](https://help.aliyun.com/zh/dts/developer-reference/api-dtsai-2026-04-01-webfetch)
