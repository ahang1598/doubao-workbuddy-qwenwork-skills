# TikTok Ads 完整枚举索引 + 搭配矩阵

## 目录

- [TikTok Ads 完整枚举索引 + 搭配矩阵](#tiktok-ads-完整枚举索引-搭配矩阵)
  - [营销目标 (Objective Type)](#营销目标-objective-type)
  - [优化目标 (Optimization Goal)](#优化目标-optimization-goal)
  - [计费方式 (Billing Event)](#计费方式-billing-event)
  - [出价类型 (Bid Type)](#出价类型-bid-type)
  - [广告格式 (Ad Format)](#广告格式-ad-format)
  - [CTA 按钮类型 (Call to Action)](#cta-按钮类型-call-to-action)
  - [投放状态 (Operation Status)](#投放状态-operation-status)
  - [预算模式 (Budget Mode)](#预算模式-budget-mode)
  - [性别定向 (Gender)](#性别定向-gender)
  - [版位类型 (Placement Type)](#版位类型-placement-type)
  - [手动版位选项 (Placements)](#手动版位选项-placements)
  - [📊 目标-优化-计费 搭配矩阵](#-目标-优化-计费-搭配矩阵)
    - [搭配规则说明](#搭配规则说明)
  - [常用国家/地区代码](#常用国家地区代码)

---


## 营销目标 (Objective Type)

| 枚举值 | 中文名称 | 说明 |
|--------|----------|------|
| `APP_PROMOTION` | 应用推广 | 推广移动应用，驱动安装或应用内事件 |
| `CONVERSIONS` | 转化量 | 驱动网站转化（购买、注册等） |
| `TRAFFIC` | 流量 | 驱动网站访问量 |
| `REACH` | 覆盖量 | 最大化品牌曝光覆盖人数 |
| `VIDEO_VIEWS` | 视频观看量 | 驱动视频播放量 |
| `ENGAGEMENT` | 互动量 | 驱动用户互动（点赞、评论、分享） |
| `LEAD_GENERATION` | 线索收集 | 收集潜在客户信息 |
| `PRODUCT_SALES` | 产品销售 | 驱动电商产品销售 |

## 优化目标 (Optimization Goal)

| 枚举值 | 中文名称 | 说明 |
|--------|----------|------|
| `INSTALL` | 安装 | 优化应用安装量 |
| `IN_APP_EVENT` | 应用内事件 | 优化应用内特定事件 |
| `CONVERSIONS` | 转化 | 优化网站转化 |
| `CLICK` | 点击 | 优化点击量 |
| `IMPRESSION` | 曝光 | 优化曝光量 |
| `VIDEO_VIEW` | 视频观看 | 优化视频播放 |
| `LEAD` | 线索 | 优化线索收集 |
| `APP_INSTALL` | 应用安装 | 应用安装优化 |

## 计费方式 (Billing Event)

| 枚举值 | 中文名称 | 说明 |
|--------|----------|------|
| `OCPM` | 优化千次展示成本 | 按展示计费，优化转化 |
| `CPC` | 每次点击成本 | 按点击计费 |
| `CPM` | 千次展示成本 | 按展示计费 |
| `CPV` | 每次观看成本 | 按视频观看计费 |
| `CPA` | 每次行动成本 | 按转化行动计费 |

## 出价类型 (Bid Type)

| 枚举值 | 中文名称 | 说明 |
|--------|----------|------|
| `BID_TYPE_NO_BID` | 自动出价 | 系统自动优化出价，最大化投放量 |
| `BID_TYPE_MANUAL` | 手动出价 | 手动设置出价金额 |
| `BID_TYPE_LOWEST_COST` | 最低成本 | 以最低成本获取转化 |
| `BID_TYPE_COST_CAP` | 成本上限 | 设置成本上限，不超过指定成本 |

## 广告格式 (Ad Format)

| 枚举值 | 中文名称 | 说明 |
|--------|----------|------|
| `SINGLE_VIDEO` | 单视频 | 单个视频素材 |
| `SINGLE_IMAGE` | 单图片 | 单张图片素材 |
| `CAROUSEL` | 轮播 | 多张图片轮播 |
| `PLAYABLE` | 试玩广告 | 可交互试玩素材 |

## CTA 按钮类型 (Call to Action)

| 枚举值 | 中文名称 |
|--------|----------|
| `INSTALL_NOW` | 立即安装 |
| `DOWNLOAD_NOW` | 立即下载 |
| `SHOP_NOW` | 立即购买 |
| `LEARN_MORE` | 了解更多 |
| `SIGN_UP` | 立即注册 |
| `SUBSCRIBE` | 立即订阅 |
| `CONTACT_US` | 联系我们 |
| `WATCH_NOW` | 立即观看 |
| `PLAY_NOW` | 立即体验 |
| `BOOK_NOW` | 立即预订 |
| `GET_QUOTE` | 获取报价 |
| `APPLY_NOW` | 立即申请 |
| `ORDER_NOW` | 立即订购 |
| `BUY_NOW` | 立即购买 |
| `GET_OFFER` | 获取优惠 |
| `NO_BUTTON` | 无按钮 |

## 投放状态 (Operation Status)

| 枚举值 | 中文名称 | 说明 |
|--------|----------|------|
| `ENABLE` | 启用 | 广告正在投放 |
| `DISABLE` | 暂停 | 广告已暂停 |
| `DELETE` | 删除 | 广告已删除 |

## 预算模式 (Budget Mode)

| 枚举值 | 中文名称 | 说明 |
|--------|----------|------|
| `BUDGET_MODE_DAY` | 日预算 | 每日预算上限 |
| `BUDGET_MODE_TOTAL` | 总预算 | 整个投放期总预算 |

## 性别定向 (Gender)

| 枚举值 | 中文名称 |
|--------|----------|
| `GENDER_MALE` | 男性 |
| `GENDER_FEMALE` | 女性 |
| `GENDER_UNLIMITED` | 不限 |

## 版位类型 (Placement Type)

| 枚举值 | 中文名称 | 说明 |
|--------|----------|------|
| `PLACEMENT_TYPE_AUTOMATIC` | 自动版位 | 系统自动选择最优版位 |
| `PLACEMENT_TYPE_MANUAL` | 手动版位 | 手动选择版位 |

## 手动版位选项 (Placements)

| 枚举值 | 平台 | 说明 |
|--------|------|------|
| `TikTok` | TikTok | TikTok 信息流 |
| `Pangle` | Pangle | Pangle 联盟流量 |
| `TopBuzz` | TopBuzz | TopBuzz 平台 |
| `BuzzVideo` | BuzzVideo | BuzzVideo 平台 |

---

## 📊 目标-优化-计费 搭配矩阵

| 营销目标 | 支持的优化目标 | 支持的计费方式 | 推荐出价类型 |
|----------|---------------|---------------|-------------|
| **APP_PROMOTION** | INSTALL, IN_APP_EVENT | OCPM, CPC | BID_TYPE_NO_BID |
| **CONVERSIONS** | CONVERSIONS, CLICK | OCPM, CPC | BID_TYPE_NO_BID |
| **TRAFFIC** | CLICK, IMPRESSION | CPC, CPM | BID_TYPE_MANUAL |
| **REACH** | IMPRESSION | CPM | BID_TYPE_MANUAL |
| **VIDEO_VIEWS** | VIDEO_VIEW | CPV, CPM | BID_TYPE_NO_BID |
| **ENGAGEMENT** | CLICK, IMPRESSION | CPC, CPM | BID_TYPE_MANUAL |
| **LEAD_GENERATION** | LEAD, CONVERSIONS | OCPM, CPC | BID_TYPE_NO_BID |
| **PRODUCT_SALES** | CONVERSIONS, CLICK | OCPM, CPC | BID_TYPE_NO_BID |

### 搭配规则说明

1. **目标决定下游**：objective_type → optimization_goal → billing_event 有严格组合
2. **OCPM 要求**：使用 OCPM 计费必须有对应的转化跟踪（Pixel 或 SDK）
3. **自动出价限制**：BID_TYPE_NO_BID 仅支持 OCPM/CPV 计费方式
4. **最低预算**：日预算最低 $20（OCPM），总预算最低 $50

---

## 常用国家/地区代码

| 代码 | 国家/地区 | 代码 | 国家/地区 |
|------|----------|------|----------|
| US | 美国 | JP | 日本 |
| GB | 英国 | KR | 韩国 |
| DE | 德国 | FR | 法国 |
| CA | 加拿大 | AU | 澳大利亚 |
| SG | 新加坡 | HK | 中国香港 |
| TW | 中国台湾 | MY | 马来西亚 |
| ID | 印度尼西亚 | TH | 泰国 |
| PH | 菲律宾 | VN | 越南 |
| IN | 印度 | BR | 巴西 |
| MX | 墨西哥 | ES | 西班牙 |
| IT | 意大利 | NL | 荷兰 |
| SE | 瑞典 | CH | 瑞士 |
