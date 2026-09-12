---
name: xiaoyuan
description: >-
  出海精灵·小元连接器技能。通过 MCP 工具提供米奥展会外贸数据能力：搜买家/联系人、买家详情、
  一客一档相关查询、搜同行、HS 出口额、关税与 WTO 贸易壁垒、Hunter 找邮箱、
  AroundDeal 海外企业/决策人画像等。
  当用户提到「搜买家、找采购商、买家联系人、一客一档、搜同行、同行展商、HS 出口额、
  关税、WTO、找采购邮箱、海外企业画像、决策人、小元、米奥、展商助手」等意图时触发。
version: "1.0.0"
author: "Meorient"
display_name: "小元"
display_name_en: "Xiaoyuan"
---

# 小元连接器技能

本技能是连接器「出海精灵·小元」的入口技能。能力通过 MCP 服务器 `meo-xiaoyuan`（工具前缀 `mcp__xiaoyuan__*`）提供，**全部为只读查询**，不修改任何业务数据。

## 前置检查：鉴权与连接

MCP 请求头使用 `Authorization: Bearer ${API_KEY}`，其中 `API_KEY` 由用户在 WorkBuddy 连接器配置面板中手动填写（对应 `token-schema.json` 的 API Key 字段）。

**API Key 配置**：访问 https://xyconsole.tradechina.com/key 获取 API Key，配置环境变量 `API_KEY`。未配置时所有工具调用将返回鉴权失败。

**执行任何业务工具前，先确认连接状态：**

1. 首次调用任一 `xiaoyuan_*` 工具前，先用 `xiaoyuan_ping` 探测连通性（回显 pong 即正常）。
2. 调用返回 401 / 403 / token 失效类错误时：
   - 不要重试，不要编造数据；
   - 引导用户：打开 WorkBuddy **连接器管理 → 出海精灵·小元 → 配置**，在「服务对接配置」中粘贴 API Key 后保存；
   - 获取 API Key 的入口见连接器配置页的「如何获取 API Key？」（出海精灵·小元 → Key与平台 → 复制API Key）。
3. 工具整体不可见 / 连接器未启用时，提示用户在连接器管理中信任并启用该连接器。

## 意图路由

| 用户意图 | 工具 |
|----------|------|
| 调试连接、ping 探测 | `xiaoyuan_ping` |
| 多条件搜买家（产品词/国家/展会/预注册） | `xiaoyuan_search_buyers` |
| 按完整公司名查买家 | `xiaoyuan_search_buyers_by_name` |
| 买家公司详情 | `xiaoyuan_get_buyer_detail` |
| 买家联系人（须用户明确要看联系方式再调） | `xiaoyuan_get_buyer_contacts` |
| 搜同行、竞品展商 | `xiaoyuan_get_colleague_categories` → `xiaoyuan_search_colleagues` |
| 本企业资料、订购展信息 | `xiaoyuan_get_company_basic_info` |
| HS 编码出口额 / 双边贸易数据 | `xiaoyuan_comtrade_get` |
| 关税（WITS） | `xiaoyuan_wits_tariff` |
| WTO 贸易壁垒 / SPS / TBT / 补贴通报 | `xiaoyuan_wto_eping` / `xiaoyuan_wto_qrs` / `xiaoyuan_wto_tfad` |
| 按域名 / 公司找邮箱（Hunter） | `xiaoyuan_hunter_domain_search` / `xiaoyuan_hunter_email_finder` |
| 邮箱有效性校验 | `xiaoyuan_hunter_email_verifier` |
| 按人名 / 公司找人（Hunter） | `xiaoyuan_hunter_people_find` / `xiaoyuan_hunter_companies_find` |
| 发现相似公司 | `xiaoyuan_hunter_discover` |
| 海外企业画像（AroundDeal） | `xiaoyuan_arounddeal_list_enums` → `xiaoyuan_arounddeal_enrich_company` / `xiaoyuan_arounddeal_search_companies` / `xiaoyuan_arounddeal_company_intel` |
| 海外决策人画像（AroundDeal） | `xiaoyuan_arounddeal_search_people` / `xiaoyuan_arounddeal_enrich_person` |
| 付费找联系方式（AroundDeal，按条计费） | `xiaoyuan_arounddeal_find_contacts` / `xiaoyuan_arounddeal_search_sourcing_contacts` / `xiaoyuan_arounddeal_search_brand_contacts` |
| 联系人校验 / LinkedIn 关联 | `xiaoyuan_arounddeal_verify_contact` / `xiaoyuan_arounddeal_email_to_linkedin` / `xiaoyuan_arounddeal_check_relationship` |
| 恢复中断的画像增强任务 | `xiaoyuan_arounddeal_resume_enrichment` |

## 推荐链式调用

```
搜买家(search_buyers) → 详情(get_buyer_detail) → 联系人(get_buyer_contacts)
联系人缺邮箱 → AroundDeal find_contacts 或 Hunter email_finder
搜同行(get_colleague_categories → search_colleagues) → 同行买家 → search_buyers
市场研究：comtrade_get → wits_tariff → wto_*（生成报告/选品决策）
```

## 核心规范

### 响应解析

- 优先读 `response.data`；列表多为 `items` + `total`。
- 报错时原文告知用户，**禁止编造数据**；无来源的信息标「待确认」。
- 同行搜索用 `xiaoyuan_search_colleagues` 的 `search_type`（1 无结果再试 2）；勿混用其他工具的 tagId。
- 搜买家翻页透传 `backend_param`；产品词优先 `tag_keyword`（英文），无结果再 `profile_keyword`。
- 本届展会买家须核对 `preExhibitionIds` 含目标展会 ID；预注册买家 `features` 含 21，到展买家含 5。

### 付费与敏感操作

- **AroundDeal `find_contacts` / `search_sourcing_contacts` / `search_brand_contacts` 按条计费**：`limit` ≤ 5，调用前必须向用户确认。
- Hunter `email_finder` 找不到不扣费，可放心先试。
- `xiaoyuan_get_buyer_contacts` 涉及联系方式，须用户明确要看联系方式后再调。
- 展示联系人信息时仅输出职位、邮箱、电话等业务字段。

### 输出约束

- 内部 ID 类字段（`companyCdpId`、各 `*_id`、cursor 等）仅在工具间流转，**禁止出现在最终回复中**；对外一律使用公司名、职位、国家等可读信息，多候选时用序号 + 可读信息构造列表。
- 列表结果默认摘要（公司 + 关键标签 + 国家）；用户下钻时再展开单家公司详情。

## 不触发场景

- 非米奥业务的一般问答、写作、编程等通用请求。
- 发送邮件 / 写入线索 / 导入线索等写操作不在本连接器范围（MCP 工具只读）；用户提出时如实说明并建议在米奥平台完成。
