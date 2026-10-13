# TikTok Marketing API v1.3 端点参数参考

## 目录

- [TikTok Marketing API v1.3 端点参数参考](#tiktok-marketing-api-v13-端点参数参考)
  - [基础信息](#基础信息)
  - [认证相关](#认证相关)
    - [1. 获取 Access Token](#1-获取-access-token)
  - [Campaign 广告系列](#campaign-广告系列)
    - [2. 创建 Campaign](#2-创建-campaign)
    - [3. 获取 Campaign](#3-获取-campaign)
    - [4. 更新 Campaign 状态](#4-更新-campaign-状态)
    - [4.1 更新 Campaign 属性](#41-更新-campaign-属性)
  - [Ad Group 广告组](#ad-group-广告组)
    - [5. 创建 Ad Group](#5-创建-ad-group)
    - [6. 更新 Ad Group 状态](#6-更新-ad-group-状态)
    - [6.1 更新 Ad Group 属性](#61-更新-ad-group-属性)
  - [Ad 广告](#ad-广告)
    - [7. 创建 Ad](#7-创建-ad)
    - [8. 更新 Ad 状态](#8-更新-ad-状态)
    - [8.1 更新 Ad 属性](#81-更新-ad-属性)
  - [素材管理](#素材管理)
    - [9. 上传视频素材](#9-上传视频素材)
    - [10. 上传图片素材](#10-上传图片素材)
  - [通用响应格式](#通用响应格式)
  - [速率限制](#速率限制)

---


## 基础信息

- **API 基础地址**: `https://business-api.tiktok.com/open_api/v1.3`
- **认证方式**: HTTP Header `Access-Token`
- **请求格式**: JSON (POST) / Query String (GET)
- **响应格式**: JSON

---

## 认证相关

### 1. 获取 Access Token

- **端点**: `POST /oauth2/access_token/`
- **认证**: 不需要 Access-Token
- **用途**: 用 auth_code 换取 access_token

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| app_id | string | 是 | 应用 ID |
| secret | string | 是 | 应用密钥 |
| auth_code | string | 是 | 授权码 |

**响应字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| access_token | string | 访问令牌 |
| advertiser_id | string | 广告主 ID |
| expires_in | int | 有效期（秒） |
| refresh_token | string | 刷新令牌 |
| refresh_token_expires_in | int | 刷新令牌有效期 |

---

## Campaign 广告系列

### 2. 创建 Campaign

- **端点**: `POST /campaign/create/`
- **用途**: 创建新的广告系列

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| advertiser_id | string | 是 | 广告主 ID |
| campaign_name | string | 是 | 广告系列名称（最多 512 字符） |
| objective_type | string | 是 | 营销目标，见枚举表 |
| budget_mode | string | 是 | 预算模式：BUDGET_MODE_DAY / BUDGET_MODE_TOTAL |
| budget | float | 是 | 预算金额（美元） |
| operation_status | string | 否 | 操作状态：ENABLE / DISABLE（默认 DISABLE） |
| campaign_type | string | 否 | 广告系列类型 |
| rf_buy_type | string | 否 | 购买类型 |

**响应字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| campaign_id | string | 广告系列 ID |

### 3. 获取 Campaign

- **端点**: `GET /campaign/get/`
- **用途**: 获取广告系列信息

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| advertiser_id | string | 是 | 广告主 ID |
| campaign_id | string | 否 | 广告系列 ID（不传则返回全部） |
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页数量，默认 20 |
| filtering | array | 否 | 过滤条件 |

### 4. 更新 Campaign 状态

- **端点**: `POST /campaign/status/update/`
- **用途**: 启用/暂停/删除广告系列（支持批量）

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| advertiser_id | string | 是 | 广告主 ID |
| campaign_ids | array | 是 | 广告系列 ID 列表（单次最多 100 个） |
| operation_status | string | 是 | 操作状态：ENABLE / DISABLE / DELETE |

### 4.1 更新 Campaign 属性

- **端点**: `POST /campaign/update/`
- **用途**: 更新广告系列预算、名称、预算模式

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| advertiser_id | string | 是 | 广告主 ID |
| campaign_id | string | 是 | 广告系列 ID |
| budget | float | 否 | 新预算金额 |
| budget_mode | string | 否 | BUDGET_MODE_DAY / BUDGET_MODE_TOTAL |
| campaign_name | string | 否 | 新名称（最多 512 字符） |

---

## Ad Group 广告组

### 5. 创建 Ad Group

- **端点**: `POST /adgroup/create/`
- **用途**: 创建新的广告组

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| advertiser_id | string | 是 | 广告主 ID |
| campaign_id | string | 是 | 所属广告系列 ID |
| adgroup_name | string | 是 | 广告组名称 |
| optimization_goal | string | 是 | 优化目标 |
| billing_event | string | 是 | 计费方式 |
| bid_type | string | 是 | 出价类型 |
| bid_amount | float | 否 | 出价金额（手动出价时必填） |
| targeting | object | 是 | 定向设置 |
| placement | object | 是 | 版位设置 |
| schedule_start_time | string | 否 | 开始时间 |
| schedule_end_time | string | 否 | 结束时间 |
| operation_status | string | 否 | 操作状态 |

**targeting 对象**:

| 字段 | 类型 | 说明 |
|------|------|------|
| location | object | 地理位置定向 |
| age | object | 年龄定向 {min, max} |
| gender | string | 性别定向 |
| language | array | 语言定向 |
| interest_category | array | 兴趣分类 |
| behavior | array | 行为定向 |
| audience | object | 自定义受众 |

**placement 对象**:

| 字段 | 类型 | 说明 |
|------|------|------|
| placement_type | string | 版位类型：PLACEMENT_TYPE_AUTOMATIC / PLACEMENT_TYPE_MANUAL |
| placements | array | 手动版位列表 |

**响应字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| adgroup_id | string | 广告组 ID |

### 6. 更新 Ad Group 状态

- **端点**: `POST /adgroup/status/update/`
- **用途**: 启用/暂停/删除广告组（支持批量）

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| advertiser_id | string | 是 | 广告主 ID |
| adgroup_ids | array | 是 | 广告组 ID 列表（单次最多 100 个） |
| operation_status | string | 是 | 操作状态：ENABLE / DISABLE / DELETE |

### 6.1 更新 Ad Group 属性

- **端点**: `POST /adgroup/update/`
- **用途**: 更新广告组预算、出价、名称、排期、定向、版位、状态

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| advertiser_id | string | 是 | 广告主 ID |
| adgroup_id | string | 是 | 广告组 ID |
| budget | float | 否 | 新预算金额 |
| budget_mode | string | 否 | BUDGET_MODE_DAY / BUDGET_MODE_TOTAL |
| bid_type | string | 否 | BID_TYPE_NO_BID / BID_TYPE_CUSTOM / BID_TYPE_SMART |
| bid_amount | float | 否 | 新出价金额（手动出价时） |
| adgroup_name | string | 否 | 新名称 |
| schedule_start_time | string | 否 | 排期开始时间 |
| schedule_end_time | string | 否 | 排期结束时间 |
| targeting | object | 否 | 定向设置（全量覆盖） |
| placement | object | 否 | 版位设置（全量覆盖） |
| operation_status | string | 否 | ENABLE / DISABLE |

---

## Ad 广告

### 7. 创建 Ad

- **端点**: `POST /ad/create/`
- **用途**: 创建新的广告

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| advertiser_id | string | 是 | 广告主 ID |
| adgroup_id | string | 是 | 所属广告组 ID |
| ad_name | string | 是 | 广告名称 |
| ad_format | string | 是 | 广告格式 |
| video_id | string | 否 | 视频素材 ID（视频广告必填） |
| image_id | string | 否 | 图片素材 ID（图片广告必填） |
| ad_text | string | 否 | 广告文案 |
| call_to_action | string | 否 | CTA 按钮文案 |
| landing_page_url | string | 否 | 落地页 URL |
| app_name | string | 否 | 应用名称 |
| profile_image_id | string | 否 | 头像图片 ID |
| display_name | string | 否 | 显示名称 |
| operation_status | string | 否 | 操作状态 |

**响应字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| ad_id | string | 广告 ID |

### 8. 更新 Ad 状态

- **端点**: `POST /ad/status/update/`
- **用途**: 启用/暂停/删除广告（支持批量）

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| advertiser_id | string | 是 | 广告主 ID |
| ad_ids | array | 是 | 广告 ID 列表（单次最多 100 个） |
| operation_status | string | 是 | 操作状态：ENABLE / DISABLE / DELETE |

### 8.1 更新 Ad 属性

- **端点**: `POST /ad/update/`
- **用途**: 更新广告名称、文案、CTA、落地页、显示名、状态

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| advertiser_id | string | 是 | 广告主 ID |
| ad_id | string | 是 | 广告 ID |
| ad_name | string | 否 | 新名称 |
| ad_text | string | 否 | 新广告文案 |
| call_to_action | string | 否 | 新 CTA 按钮文案 |
| landing_page_url | string | 否 | 新落地页 URL |
| display_name | string | 否 | 新显示名称 |
| operation_status | string | 否 | ENABLE / DISABLE |

---

## 素材管理

### 9. 上传视频素材

- **端点**: `POST /file/video/ad/upload/`
- **Content-Type**: `multipart/form-data`
- **用途**: 上传视频素材到素材库

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| advertiser_id | string | 是 | 广告主 ID |
| video_file | file | 是 | 视频文件 |
| file_name | string | 否 | 文件名 |
| video_signature | string | 否 | 文件 MD5（用于秒传） |
| flaw_detect | bool | 否 | 是否进行素材审核检测 |

**响应字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| video_id | string | 视频 ID |
| video_url | string | 视频 URL |
| width | int | 视频宽度 |
| height | int | 视频高度 |
| duration | float | 视频时长（秒） |
| file_size | int | 文件大小（字节） |

### 10. 上传图片素材

- **端点**: `POST /file/image/ad/upload/`
- **Content-Type**: `multipart/form-data`
- **用途**: 上传图片素材到素材库

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| advertiser_id | string | 是 | 广告主 ID |
| image_file | file | 是 | 图片文件 |
| file_name | string | 否 | 文件名 |

**响应字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| image_id | string | 图片 ID |
| image_url | string | 图片 URL |
| width | int | 图片宽度 |
| height | int | 图片高度 |
| file_size | int | 文件大小（字节） |

---

## 通用响应格式

所有 API 响应统一格式：

```json
{
  "code": 0,
  "message": "OK",
  "data": { ... },
  "request_id": "xxx"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 状态码，0 表示成功 |
| message | string | 状态消息 |
| data | object | 响应数据 |
| request_id | string | 请求 ID（用于排查问题） |

---

## 速率限制

- **普通接口**: 60 次/分钟（按广告主维度）
- **上传接口**: 20 次/分钟
- **查询接口**: 120 次/分钟

超出限制会返回 `429 Too Many Requests` 错误。
