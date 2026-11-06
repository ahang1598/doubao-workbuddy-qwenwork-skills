# SmartLib 学术文献检索 Skill v3.2

> **中文** · [English below](#english)

用自然语言查论文、找文献、下载全文 —— 覆盖 8000 万篇中文期刊 + 12.28 亿条全球文献。**全自动**：首次使用自动注册开通（免费 100 次/月），配额自动消耗，用尽引导微信支付充值。

> Search papers, find literature, download full text — in plain language. 80M Chinese journal articles + 1.228B global records. **Auto-monetization**: auto-register (100 free/month), auto quota consumption, WeChat Pay recharge.

---

## 这是什么 / What is this

一个让 AI 助手具备学术文献检索能力的 Skill。安装后，用日常语言说出需求，AI 自动帮你检索、筛选、展示文献，还能下载中文期刊全文 + 英文 OA 论文。

### 核心亮点 / Highlights

- **中文期刊全文下载**：8000 万篇授权中文期刊，一键获取 PDF
- **英文 OA 多渠道下载**：十一级下载策略，Gold/Hybrid/Green OA 成功率 >85%
- **全球文献覆盖**：12.28 亿条元数据（期刊/专利/会议/学位/标准等）
- **全自动变现**：零配置启动，配额耗尽后扫码支付即恢复
- **自然语言交互**：不需要学检索语法

---

## 🔒 免费体验与受限展示 / Free Trial & Restricted Display

| 状态 | 展示规则 |
|------|---------|
| **配额充足** | 完整展示所有检索结果（含详情、下载、智能排序） |
| **配额耗尽** | Gateway 返回 429，**拒绝服务**，直接提示充值 |

配额耗尽后回复「充值」，展示数字选套餐卡片（①-④），回复数字即可获取带套餐信息的微信支付二维码。

---

## 快速开始 / Quick Start

### 1. 安装

在 WorkBuddy 中搜索 "smartlib" 安装。

### 2. 零配置启动

**无需手动申请 API 密钥。** 首次使用自动检测凭证，未配置则自动通过智能网关注册开通（免费 100 次/月）。

### 3. 开始使用

```
帮我找一些关于大语言模型的最新论文
Find recent papers on CRISPR gene editing
下载第 3 篇
```

---

## 使用示例 / Examples

**查找中文论文并下载：** `帮我找几篇关于知识图谱的中文论文` → AI 自动检索、展示结果、输入编号即可下载 PDF。

**查找英文论文并获取 OA 全文：** `找 transformer architecture 相关的论文` → AI 自动通过 ArXiv / Unpaywall / CORE 等渠道获取 OA 版本。

**配额耗尽 → 对话支付：** 在对话中说「充值」→ 展示 ①-④ 数字套餐卡片 → 回复数字选择 → 直接出带订单信息的支付二维码 → 扫码支付 → 即时恢复。

---

## 常见问题 / FAQ

**Q: 免费吗？** 首次使用自动注册，免费 100 次/月。超出后付费，¥9.90 体验包（1000 次）起。

**Q: 英文文献能下全文吗？** 可以。十一级多渠道下载策略，Gold/Hybrid/Green OA 成功率 >85%。付费墙内（Closed）论文无法获取。

**Q: 配额耗尽后怎么办？** 在对话中说「充值」，展示数字选套餐卡片，回复数字直接获取支付二维码，扫码后即时恢复。

---

## 依赖 / Dependencies

- SmartLib API（自动通过网关注册）
- SmartLib Gateway（腾讯云 SCF 上海）
- WeChat Pay（微信支付 Native 扫码支付）

---

## 相关文档 / Related Docs

- **SKILL.md** — 完整技能规范（API 接口、检索策略、变现流程）
- **PIPELINE.md** — 全链路优化指南

---

## 作者 / Author

**张亚东** — 重庆维普智图 · GitHub: [J-levee](https://github.com/J-levee)

---

<a name="english"></a>

# SmartLib Academic Literature Search Skill v3.2 — English

> Search papers, find literature, download full text in plain language. 80M Chinese journal articles + 1.228B global records. Auto-monetization included.

## What is this

A skill that gives AI assistants academic literature search capabilities. Describe your needs in plain language, and the AI handles search, filtering, result display, and full-text download.

## Free Trial & Restricted Display

| Status | Display Rule |
|--------|-------------|
| **Quota available** | Full results with detail, download, smart ranking |
| **Quota exhausted** | Gateway returns 429, **service denied**, recharge prompt |

Reply "recharge" to see numbered plan cards (①-④), pick a number, get WeChat Pay QR instantly.

## Quick Start

1. Install from WorkBuddy SkillHub
2. Zero-config: auto-registers on first use (100 free/month)
3. Use natural language to search

## FAQ

**Q: Is it free?** 100 free/month. Paid from ¥9.90 (trial, 1000 calls).

**Q: Can I download English papers?** Yes. 11-tier download strategy. Gold/Hybrid/Green OA >85% success.

**Q: What when quota runs out?** Reply "recharge" for WeChat Pay. Instant restoration.

## Dependencies

- SmartLib API (auto-registered via gateway)
- SmartLib Gateway (Tencent Cloud SCF Shanghai)
- WeChat Pay

## Author

**Yadong Zhang** — VIP Smart · GitHub: [J-levee](https://github.com/J-levee)
