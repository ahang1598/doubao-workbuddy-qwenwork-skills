# 降级预置源目录

当 LDH MCP 工具不可用时，按本目录进行离线候选导航和联网定位。
静态目录是快照，只用于候选导航和 LDH 降级；目录 URL 在实时验证前不得作为已核验证据。

## 使用条件

以下任一情况触发降级：
- MCP 工具返回 `not_configured` / `auth_failed` / `quota_exhausted` / `unavailable` / `error`。
- 连续三次调用失败。
- 目标法域不在 `ldh_discover_countries` 返回的实时目录中。

## 降级顺序

```text
本文件预置源目录
→ 联网定位官方 URL
→ verification-engine.md Level A/B/C
→ 无法核验则列入待查清单
```

任何降级都不得退回模型记忆补全条文或判例。

## 主要法域官方源

### 欧盟（EU）

| 来源　　　　　　| 类型　　　 | URL                        |
| -----------------| ------------| ----------------------------|
| EUR-Lex　　　　 | 法规　　　 | https://eur-lex.europa.eu/ |
| CURIA (CJEU)　　| 判例　　　 | https://curia.europa.eu/   |
| EU publications | 官方出版物 | https://op.europa.eu/      |

### 欧洲委员会（CoE）

| 来源　　　　　　　| 类型 | URL                                    |
| -------------------| ------| ----------------------------------------|
| HUDOC (ECtHR)　　 | 判例 | https://hudoc.echr.coe.int/            |
| CoE Treaty Office | 条约 | https://www.coe.int/en/web/conventions |

### 英国（UK）

| 来源 | 类型 | URL |
|---|---|---|
| legislation.gov.uk | 法规 | https://www.legislation.gov.uk/ |
| UK Supreme Court | 判例 | https://www.supremecourt.uk/ |
| BAILII | 判例/法规（第三方） | https://www.bailii.org/ |

### 美国（US）

| 来源 | 类型 | URL |
|---|---|---|
| Congress.gov | 联邦法规 | https://www.congress.gov/ |
| Supreme Court | 判例 | https://www.supremecourt.gov/ |
| CourtListener (RECAP) | 判例（第三方） | https://www.courtlistener.com/ |

### 中国港澳台

| 来源　　　　　　　| 类型 | URL                              |
| -------------------| ------| ----------------------------------|
| HK e-Legislation　| 法规 | https://www.elegislation.gov.hk/ |
| HK Judiciary　　　| 判例 | https://www.judiciary.hk/        |
| MO 印务局　　　　 | 法规 | https://bo.io.gov.mo/            |
| TW 全国法规资料库 | 法规 | https://law.moj.gov.tw/          |

## 第三方/背景源

以下为 L2/L3 来源，仅作解释或线索，不作唯一法律依据：

| 来源 | 类型 | URL |
|---|---|---|
| ICRC IHL Database | 国际人道法 | https://ihl-databases.icrc.org/ |
| WIPO Lex | 知识产权法 | https://www.wipo.int/wipolex/ |
| World Bank GLAW | 全球法律 | https://www.worldbank.org/ |

## 注意事项

- 预置源 URL 仅为导航入口，不替代实时验证。
- 联网访问预置源时仍需按 `verification-engine.md` 完成 Level A/B/C 核验。
- 来源身份无法确认时标 `[待核查]`。
