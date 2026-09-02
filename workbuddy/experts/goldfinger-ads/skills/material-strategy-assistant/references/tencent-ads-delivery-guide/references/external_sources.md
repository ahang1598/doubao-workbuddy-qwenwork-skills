# 外部信息源清单（L2 官方渠道 / L3 第三方）

> 全部链接于 2026-08-21 实测可达（HTTP 200）。
> **失效黑名单**：`rules.e.qq.com`（DNS 无解析 + 502，规则中心已迁移至 support.e.qq.com）、
> `marketing.qq.com`、`miaowen.e.qq.com`、`open.e.qq.com`、`xiaodian.qq.com`（均无法解析，不要访问）。

---

## L2 官方渠道

### ① support.e.qq.com — 帮助中心（**官方首选**）

覆盖最广、最权威的运营向文档站。文章详情页 URL 格式：`https://support.e.qq.com/detail?cid=<分类id>&pid=<文章id>`

已验证的分类入口：

| 主题 | 入口 |
|---|---|
| 投放总览 | https://support.e.qq.com/detail?cid=3738&pid=10247 |
| 新投放平台基础认知 | https://support.e.qq.com/detail?cid=4514&pid=10247 |
| 新投放模式推广单元创建指引 | https://support.e.qq.com/detail?cid=4559&pid=10170 |
| 了解腾讯营销新工作台 | https://support.e.qq.com/detail?cid=4515&pid=10175 |
| 腾讯营销（小店版） | https://support.e.qq.com/detail?cid=5049&pid=12663 |
| 产品双周速递（新能力追踪） | https://support.e.qq.com/detail?cid=3821&pid=7656 |
| 腾讯营销妙思（AIGC） | https://support.e.qq.com/detail?cid=4575&pid=11046 |
| **内容/素材审核总览** | https://support.e.qq.com/detail?cid=3843&pid=6312 |
| **审核规则当月实时更新专区** | https://support.e.qq.com/detail?cid=4991&pid=12503 |
| 内容/素材审核行业规则 | https://support.e.qq.com/detail?cid=4837&pid=9667 |
| 审核常见问题 | https://support.e.qq.com/detail?cid=4724&pid=6373 |
| 视频号违规案例解析 | https://support.e.qq.com/detail?cid=4853&pid=12067 |
| 营销服务资源总览 | https://support.e.qq.com/detail?cid=3694&pid=7242 |
| 视频号营销 | https://support.e.qq.com/detail?cid=3707&pid=7714 |
| 公众号营销 | https://support.e.qq.com/detail?cid=3710&pid=7653 |
| 搜一搜营销 | https://support.e.qq.com/detail?cid=3720&pid=7360 |
| **财务结算总览** | https://support.e.qq.com/detail?cid=4060&pid=9635 |
| **账户充值** | https://support.e.qq.com/detail?cid=4066&pid=9292 |
| **客户退款** | https://support.e.qq.com/detail?cid=4068&pid=2068 |
| 投放问题咨询通道 | https://support.e.qq.com/detail?cid=4726&pid=9595 |

**用法**：先按上表定位分类入口，读不到再用 WebSearch 限定 `site:support.e.qq.com + 关键词`。

### ② developers.e.qq.com — 开放平台（技术类首选）

Marketing API、转化上报、SDK 接入等技术文档。

| 主题 | 链接 |
|---|---|
| Web JS 转化上报 | https://developers.e.qq.com/docs/guide/conversion/new_version/Web_api |
| APP SDK 接入 | https://developers.e.qq.com/docs/guide/conversion/new_version/APP_sdk |
| APP API 上报 | https://developers.e.qq.com/docs/guide/conversion/new_version/APP_api |
| 小游戏 API 上报 | https://developers.e.qq.com/docs/guide/conversion/new_version/Mini_Game_api |
| 点击监测 | https://developers.e.qq.com/docs/guide/conversion/new_version/dianjijiance |
| 曝光监测 | https://developers.e.qq.com/docs/guide/conversion/new_version/baoguangjiance |
| user_actions 接口 | https://developers.e.qq.com/v3.0/docs/api/user_actions/add |
| 开发者注册 | https://developers.e.qq.com/v3.0/pages/regist_developer |

### ③ datanexus.qq.com — DataNexus 数据接入

| 主题 | 链接 |
|---|---|
| 自归因说明 | https://datanexus.qq.com/doc/develop/intro/inner_app_intro/attribution/attribution_common_self |
| 点击监测接口 | https://datanexus.qq.com/doc/develop/guider/interface/conversion/ad_track_click |
| 曝光监测接口 | https://datanexus.qq.com/doc/develop/guider/interface/conversion/ad_track_impress |
| 数据源配置台 | https://datanexus.qq.com/web/datasource |
| 转化监测配置 | https://datanexus.qq.com/web/monitor/conversion |
| 资产分发 | https://datanexus.qq.com/web/asset/distribute |

### ④ 其他官方站

| 站点 | 用途 |
|---|---|
| https://e.qq.com | 腾讯营销官网首页，产品与资源介绍、成功案例 |
| https://e.qq.com/ads | 广告投放入口、新客礼包 |
| https://ad.qq.com | 投放管理平台（`/account-center/register` 为注册开户入口） |
| https://eschool.qq.com | **营销学堂**：系统课程、FAQ（`/faq/index`），适合体系化知识 |
| https://ad.weixin.qq.com | 微信广告侧（`/docs/45` 为流量主文档） |
| https://ylh.qq.com | 腾讯营销联盟（优量汇）帮助 |
| https://huxuan.qq.com | 互选内容营销（达人合作） |
| https://channels.weixin.qq.com | 视频号官方 |
| https://mp.weixin.qq.com | 公众号平台 |

---

## L3 第三方渠道

**仅在 L1 本地库和 L2 官方渠道都无法解决时使用**，且必须标注"第三方信息，非官方口径，建议向官方核实"。

### 使用规则

1. **优先用 WebSearch 而非直接猜 URL**，检索式建议带上"腾讯广告"或"腾讯营销" + 具体问题。
2. **可信度排序**：官方公众号/官方培训机构 > 头部代理商/服务商官网 > 行业垂媒 > 个人博客/自媒体 > 论坛问答。
3. **交叉验证**：第三方信息至少两个独立来源一致才采信；涉及资质、审核、计费、返点等敏感内容**一律不采信第三方**，直接引导用户查官方或问客服。
4. **时效检查**：注意文章日期，腾讯广告 2024 年起有 3.0 大改版，早于 2024 年的第三方教程可能已完全失效。
5. **禁止**把第三方口径当官方结论陈述。

### 适用场景（第三方通常更有价值的地方）

- 实操踩坑经验、避坑清单
- 行业投放案例与效果数据参考
- 官方文档没写的操作细节补充
- 同行做法对比

### 不适用场景（必须走官方）

- 资质要求、审核规则、禁投清单
- 计费方式、价格、限额、返点政策
- 账户安全、资金操作
- 任何有合规风险的内容
