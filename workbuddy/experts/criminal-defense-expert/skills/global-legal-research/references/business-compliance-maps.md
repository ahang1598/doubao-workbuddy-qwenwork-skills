# 业务合规域展开表 (Business Compliance Domain Maps)

> 当用户问题为"在[法域]运营[某业务]需要满足哪些合规条件"时，使用本表将单一业务类型
> 展开为全部相关法规域的检索清单。每行的「匹配关键词」用于在 SKILL.md §4 Step 1
> 自动识别业务场景。
>
> 本表是 `source-index.md` 表A（18法律主题）的 **业务视角补充**——将"按学科分类的法律主题"
> 翻译为"按业务活动展开的合规域集合"。

---

## 产品/业务类型 → 合规域展开

### 1. 电子签名平台 (E-Signature / Digital Signature Platform)

| 层级 | 合规域 | 对应 source-index.md 主题 | 典型法规类型 | 检索关键词（印尼为例） |
|:---:|--------|:------------------------:|------------|---------------------|
| L0 | 电子签名法律效力 | #1 公司/商事 | UU | "electronic signature law" OR "UU ITE" |
| L1 | 平台运营(PSE注册) | #1 公司/商事 (跨界) | PP, Permen | "PSE registration" OR "electronic system operator" |
| L2 | 电子合同订立 | #1 公司/商事 (跨界) | PP | "e-commerce regulation" OR "PP 80" |
| L3 | 电子认证(CA/PSrE) | #1 公司/商事 | Permen | "certification authority" OR "PSrE" |
| L4 | 电子印花税 | #3 企业税 | UU, PP, PMK | "e-meterai" OR "stamp duty" |
| L5 | 语言合规 | #19 行政合规/语言法 | UU | "language law" OR "Bahasa Indonesia" |
| L6 | 个人数据保护 | #9 数据隐私/保护 | UU | "personal data protection" OR "PDP" |
| L7 | 外商投资准入 | #2 外商投资 | Perpres | "foreign investment" OR "negative list" |
| L8 | 营业许可 | #1 公司/商事 | PP | "business license" OR "OSS" |
| L9 | 金融行业叠加(如服务银行) | #4 银行金融 | POJK | "OJK" OR "financial regulation" |
| L10 | 网络安全 | #1 公司/商事 (跨界) | BSSN条例 | "cybersecurity" OR "BSSN" |
| L11 | 消费者保护 | #1 公司/商事 | UU | "consumer protection" |

**匹配关键词**: 电子签名, e-signature, digital signature, 电子合同, 电子签, e-meterai, PSrE, 认证电子签名, 电子印章

---

### 2. SaaS 平台 (含数据存储/处理)

| 层级 | 合规域 | 对应主题 | 关键法规类型 |
|:---:|--------|:------:|------------|
| L0 | 数据保护 | #9 | UU, GDPR（如涉EU） |
| L1 | PSE注册（印尼） | #1 | PP, Permen |
| L2 | 跨境数据传输 | #9 | 各国数据本地化法规 |
| L3 | 内容治理/平台责任 | #1 | UU, 各国平台法 |
| L4 | 电子合同/服务条款 | #1 | PP, 各国民法典 |
| L5 | 消费者保护 | #1 | UU |
| L6 | 外商投资（如设本地实体） | #2 | 各国投资法 |

**匹配关键词**: SaaS, cloud service, 软件即服务, 云平台, platform, data hosting

---

### 3. 金融科技（支付/借贷/P2P）

| 层级 | 合规域 | 对应主题 | 关键法规类型 |
|:---:|--------|:------:|------------|
| L0 | 金融牌照 | #4 | 央/监管条例 |
| L1 | 电子合同+电子签名 | #1 | UU, PP |
| L2 | 电子印花税 | #3 | 各国印花税法 |
| L3 | 数据保护+本地化 | #9 | 个人数据保护法 |
| L4 | AML/CFT | #4 | FATF标准, 各国反洗钱法 |
| L5 | e-KYC/身份验证 | #4 + #9 | 监管指引 |
| L6 | 消费者保护 | #1 | 金融消费者保护条例 |

**匹配关键词**: fintech, 金融科技, P2P lending, payment, 支付, digital bank, 数字银行

---

## 使用规则

1. **触发时机**：用户提及"运营""合规准入""许可""注册""doing business as""怎么在XX国开展XX业务"
2. **展开优先级**：标记为 L0/L1 的域必须检索；L9+（行业叠加层）按用户明确提及的行业触发
3. **核验独立**：每个展开域的法规独立过 `verification-engine.md` 三级核验
4. **输出整合**：展开后的多域检索结果按 `output-formats.md` 路径D输出