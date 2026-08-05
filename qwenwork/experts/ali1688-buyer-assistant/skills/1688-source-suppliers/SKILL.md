---
name: 找供应商
name_en: 1688-source-suppliers
displayName: 找供应商
version: "2.0.0"
description: |
  1688找供应商 —— 结合用户需求与关键字查询对应的供应商及工厂信息。
  核心工具能力：1688供应商查询能力。用于查询1688平台上的供应商及工厂信息。
  触发词：找供应商、查供应商、1688供应商、供应商信息、工厂信息、产业带查询、找厂家、找工厂、采购供应商、源头工厂、工厂店。
  不触发场景：找商品/选品 → 1688-product-find；下单付款 → 不处理。
  重要限制：失败时直接告知用户原因，不编造、不臆测供应商信息。
description_zh: 1688找供应商，查询平台供应商及工厂信息
user-invocable: true
argument-hint: 描述您要找什么类型的供应商，如"找做保温杯的源头工厂"
---

# 1688 找供应商

## 处理边界

本 Skill 采用 **MCP 调用 + Python 后处理** 两段式流程：

1. **鉴权与 API 调用全部交给 MCP 连接器 `ali1688-buyer`**。Agent 不处理 AK、本地 Token、browser_use 授权、签名或 HTTP 请求。
2. **供应商数据后处理必须交给 Python 脚本**。Agent 不直接解析 MCP 原始结构、不自行筛选 `RETRIEVAL` 阶段、不自行生成供应商表格。

## MCP 连接器

- 连接器名称：`ali1688-buyer`
- 本技能使用的 MCP 工具：`1688_source_suppliers`
- `__userId__` 等用户身份参数由 MCP 网关自动注入，Agent 不手动传递。

## 命令入口

统一入口：

```bash
python3 {baseDir}/cli.py ali_1688_source_suppliers --query "供应商关键字" --mcp-result-file /tmp/source_suppliers.json
```

也支持 stdin：

```bash
cat /tmp/source_suppliers.json | python3 {baseDir}/cli.py ali_1688_source_suppliers -q "供应商关键字"
```

所有命令输出 JSON：

```json
{"success": true, "markdown": "...", "data": {...}}
```

Agent 展示给用户时必须完整输出 `markdown` 字段；后续分析使用 `data.factories`。

## 严格禁止

- 禁止配置、读取、提示用户粘贴或管理 AK。
- 禁止调用旧 `_http.py`、旧鉴权脚本、浏览器或网页搜索引擎请求 1688 供应商数据。
- 禁止在 MCP 调用失败后自行通过外部网站补充供应商信息。
- 禁止让 AI 直接解析 MCP 原始返回并生成最终表格；必须调用 Python 后处理脚本输出 `markdown`。
- 禁止编造供应商信息、伪造工厂数据、臆测供应商资质。
- 禁止擅自改写用户关键字；仅做必要的商品词 + 供应商词提取。

## 意图判断

### 匹配优先级

**P0 - 核心触发词（命中即触发）**：

> 供应商、工厂、厂家、厂商、生产商、制造商、代工厂、源头工厂、工厂店

**P1 - 行为触发词（需搭配商品词）**：

> 找供应商、找工厂、找厂家、采购XX、筛选供应商、对比供应商

**P2 - 服务触发词（需搭配供应商场景）**：

> 贴牌、OEM、ODM、一件代发、定制logo、打样

### 触发规则

```text
命中 P0 词 → 触发本技能
命中 P1 词 + 商品词 → 触发本技能
仅商品词/找商品/选品 → 不触发，交给 1688-product-find
下单/付款/订单/物流 → 不触发
```

## 关键字提取规则

### 提取公式

```text
关键字 = 商品词 + 供应商词
```

| 用户输入 | 提取关键字 |
|---------|-----------|
| 帮我找做不锈钢保温杯的供应商 | `不锈钢保温杯供应商` |
| 我想找儿童书包厂家 | `儿童书包厂家` |
| 我需要采购宠物牵引绳 | `宠物牵引绳供应商` |

筛选条件不加入查询关键字，仅用于脚本输出后的 Agent 分析：

| 条件类型 | 关键词 | 处理方式 |
|---------|--------|---------|
| MOQ | 起订量、500以内 | 结果后分析 |
| 定制能力 | 定制logo、贴牌 | 结果后分析 |
| 工厂属性 | 工厂店、源头工厂 | 结果后分析 |

## 执行流程

```text
步骤1: 提取关键字 → 商品词 + 供应商词

步骤2: 调用 MCP 工具 → 1688_source_suppliers(query="<关键字>")
       ├─ MCP 失败 → 原样输出错误并按错误处理
       └─ MCP 成功 → 将原始 JSON 写入临时文件或传给 stdin

步骤3: 调用 Python 后处理
       python3 {baseDir}/cli.py ali_1688_source_suppliers -q "<关键字>" --mcp-result-file /tmp/source_suppliers.json

步骤4: 处理脚本响应
       ├─ success: true → 完整输出 markdown；Agent 分析可追加在后面
       └─ success: false → 输出 markdown 后终止，不追加分析
```

## Python 后处理职责

原有供应商后处理逻辑已保留在：

```text
scripts/capabilities/ali_1688_source_suppliers/service.py
```

Python 脚本负责：

- 解开 MCP / JSON-RPC 常见包装。
- 兼容原接口的多种数据结构：
  - 顶层 `originResponses`
  - `data.result.originResponses`
  - `data.result.model`
- 查找 `currentPhase == "RETRIEVAL"` 的阶段数据。
- 从 `responseData.data` 中提取工厂列表。
- 解析 `extInfos` 中的 JSON 字符串数组字段，如 `oem_mode`、`manufacture_type`、`factory_type_tag`、`rec_tags`。
- 过滤缺少公司名称、合作方式或服务类型的低质量记录。
- 生成稳定 Markdown 表格。

Agent 不得复刻或替代以上逻辑。

## 输出格式

### 表格样式

返回数据以表格形式展示，**公司名称可点击跳转**：

| 序号 | 公司名称 | 所在地区 | 合作方式 | 服务 | 工厂信息 | 服务指标 |
|:----:|---------|---------|---------|------|---------|---------|
| 1 | [XX公司](url) | 广东中山 | OEM, ODM | 清加工 | 无牌工厂 | 高好评, 月38单 |

### 字段来源

| 展示字段 | 来源字段 |
|----------|----------|
| 公司名称 | `companyName` |
| 公司链接 | `companyUrl` |
| 所在地区 | `extInfos.reg_prov_name` + `extInfos.reg_city_name` |
| 合作方式 | `extInfos.oem_mode` |
| 服务 | `extInfos.manufacture_type` |
| 工厂等级 | `extInfos.factory_level` |
| 工厂类型 | `extInfos.factory_type_tag` |
| 好评/服务指标 | `extInfos.satisfied_rate_std_001` |
| 月订单数 | `extInfos.pay_ord_byr_cnt_1m_004` |
| 是否打样 | `extInfos.is_proofing` |

### 输出完整性

- Agent 必须完整输出 Python 脚本返回的 `markdown` 字段。
- Agent 不得省略、截断、重排表格行。
- Agent 的补充分析只能追加在表格之后。
- 查询失败时只输出失败信息和必要引导，不追加供应商分析。

## 错误处理

### MCP 调用失败

1. 原样展示 MCP 返回的错误信息。
2. 鉴权、401、Forbidden、token 过期等错误：提示用户检查 `ali1688-buyer` 连接器 OAuth 授权，必要时在连接器设置中重新授权。
3. 限流、超时、服务异常：提示稍后重试。
4. 禁止提示用户配置 AK。
5. 禁止浏览器、网页搜索或旧 HTTP 脚本降级。

### Python 后处理失败

脚本会返回：

```json
{
  "success": false,
  "markdown": "❌ 查询失败（已重试3次）：xxx原因\n\n请稍后重试。\n\n> 📌 [在1688上搜索更多供应商](https://s.1688.com/company/company_search.htm)",
  "data": {"data": {}, "error": "具体错误信息", "retries": 3}
}
```

Agent 收到后：

- 直接输出 `markdown`。
- 不要手动重试。
- 不要使用搜索引擎补充。
- 不要编造信息填补空缺。

## 风险识别

| 风险关键词 | 风险类型 | Agent 应对 |
|-----------|---------|-----------|
| 大牌同款、高仿、复刻 | 侵权风险 | 输出结果后追加合规风险提示 |
| 儿童用品 + 低价 | 安全风险 | 提示重点核验安全资质 |
| 医用级、食品级 | 合规风险 | 提示核验证照、检测报告 |
| 帮我找方向 | 意图模糊 | 先追问具体品类 |

## 安全声明

- 本技能不涉及任何 AK / Token 的本地存储和管理。
- 所有鉴权流程通过 MCP 连接器 `ali1688-buyer` 的 OAuth 机制完成。
- Agent 不应接触、存储或传输用户凭证。
- 若怀疑授权异常，用户应在 accio 设置中断开并重新授权 `ali1688-buyer` 连接器。

## 免责声明

- 供应商数据来源于 1688 平台，本技能仅作信息展示，不对供应商资质、产品质量等做任何担保。
- 用户应自行核实供应商信息，进行必要的尽职调查后再做采购决策。
- 查询结果仅供参考，不构成任何形式的商业推荐或背书。
