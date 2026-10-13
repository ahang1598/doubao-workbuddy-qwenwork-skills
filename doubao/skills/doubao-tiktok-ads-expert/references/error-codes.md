# TikTok Ads API 错误码排查速查

## 目录

- [TikTok Ads API 错误码排查速查](#tiktok-ads-api-错误码排查速查)
  - [通用错误码](#通用错误码)
  - [认证相关错误](#认证相关错误)
  - [Campaign 相关错误](#campaign-相关错误)
  - [Ad Group 相关错误](#ad-group-相关错误)
  - [Ad 相关错误](#ad-相关错误)
  - [素材相关错误](#素材相关错误)
  - [定向相关错误](#定向相关错误)
  - [常见问题排查](#常见问题排查)
    - [Q1: 40001 Invalid Access Token](#q1-40001-invalid-access-token)
    - [Q2: 41004 Budget Too Low](#q2-41004-budget-too-low)
    - [Q3: 42008 Optimization Goal Mismatch](#q3-42008-optimization-goal-mismatch)
    - [Q4: 43008 Creative Under Review](#q4-43008-creative-under-review)
    - [Q5: 45004 Audience Too Small](#q5-45004-audience-too-small)
  - [获取错误详情](#获取错误详情)

---


## 通用错误码

| 错误码 | 名称 | 说明 | 排查建议 |
|--------|------|------|----------|
| 0 | OK | 请求成功 | - |
| -1 | System Error | 系统内部错误 | 稍后重试，如持续出现请联系支持 |
| 40000 | Param Error | 参数错误 | 检查请求参数格式和必填项 |
| 40001 | Invalid Access Token | Access Token 无效 | 检查 token 是否正确，是否过期 |
| 40002 | Permission Denied | 权限不足 | 确认广告主 ID 正确，token 有对应权限 |
| 40003 | Rate Limit Exceeded | 速率限制超限 | 降低请求频率，参考速率限制文档 |
| 40004 | Not Found | 资源不存在 | 检查 ID 是否正确，资源是否已被删除 |
| 40005 | Conflict | 资源冲突 | 资源状态不允许该操作 |
| 40006 | Invalid Advertiser ID | 广告主 ID 无效 | 检查 advertiser_id 是否正确 |
| 40007 | Invalid App ID | 应用 ID 无效 | 检查 app_id 是否正确 |
| 40008 | Auth Code Expired | 授权码过期 | auth_code 有效期很短，需重新获取 |

---

## 认证相关错误

| 错误码 | 名称 | 说明 | 排查建议 |
|--------|------|------|----------|
| 40100 | Unauthorized | 未授权 | 缺少 Access-Token 请求头 |
| 40101 | Token Expired | Token 过期 | 重新获取 access_token |
| 40102 | Token Revoked | Token 已被撤销 | 用户撤销了授权，需要重新授权 |
| 40103 | Invalid Scope | 权限范围不足 | 申请的权限范围不够，需要重新授权 |
| 40104 | Invalid Auth Code | 授权码无效 | auth_code 错误或已使用 |
| 40105 | Invalid App Secret | 应用密钥错误 | 检查 app_secret 是否正确 |

---

## Campaign 相关错误

| 错误码 | 名称 | 说明 | 排查建议 |
|--------|------|------|----------|
| 41000 | Campaign Not Found | 广告系列不存在 | 检查 campaign_id 是否正确 |
| 41001 | Campaign Name Duplicate | 广告系列名称重复 | 使用不同的名称 |
| 41002 | Invalid Objective Type | 营销目标无效 | 检查 objective_type 枚举值 |
| 41003 | Invalid Budget Mode | 预算模式无效 | 检查 budget_mode 枚举值 |
| 41004 | Budget Too Low | 预算过低 | 日预算最低 $20，总预算最低 $50 |
| 41005 | Campaign Limit Reached | 广告系列数量上限 | 每个广告主最多 999 个广告系列 |
| 41006 | Invalid Status Transition | 状态转换无效 | 已删除的广告系列不能恢复 |

---

## Ad Group 相关错误

| 错误码 | 名称 | 说明 | 排查建议 |
|--------|------|------|----------|
| 42000 | Ad Group Not Found | 广告组不存在 | 检查 adgroup_id 是否正确 |
| 42001 | Invalid Optimization Goal | 优化目标无效 | 检查 optimization_goal 枚举值 |
| 42002 | Invalid Billing Event | 计费方式无效 | 检查 billing_event 枚举值 |
| 42003 | Invalid Bid Type | 出价类型无效 | 检查 bid_type 枚举值 |
| 42004 | Bid Amount Invalid | 出价金额无效 | 检查出价金额范围 |
| 42005 | Targeting Invalid | 定向设置无效 | 检查 targeting 参数格式 |
| 42006 | Placement Invalid | 版位设置无效 | 检查 placement 参数格式 |
| 42007 | Schedule Invalid | 排期设置无效 | 检查开始/结束时间格式 |
| 42008 | Optimization Goal Mismatch | 优化目标与营销目标不匹配 | 参考搭配矩阵，确保目标-优化目标匹配 |
| 42009 | Billing Event Mismatch | 计费方式与优化目标不匹配 | 参考搭配矩阵，确保优化目标-计费方式匹配 |
| 42010 | No Bid For Manual Bid | 手动出价缺少出价金额 | bid_type 为 BID_TYPE_MANUAL 时必须设置 bid_amount |

---

## Ad 相关错误

| 错误码 | 名称 | 说明 | 排查建议 |
|--------|------|------|----------|
| 43000 | Ad Not Found | 广告不存在 | 检查 ad_id 是否正确 |
| 43001 | Invalid Ad Format | 广告格式无效 | 检查 ad_format 枚举值 |
| 43002 | Missing Creative | 缺少创意素材 | 视频广告必须有 video_id，图片广告必须有 image_id |
| 43003 | Invalid Video ID | 视频 ID 无效 | 检查 video_id 是否正确，视频是否上传成功 |
| 43004 | Invalid Image ID | 图片 ID 无效 | 检查 image_id 是否正确 |
| 43005 | Ad Text Too Long | 广告文案过长 | 广告文案最多 100 个英文字符（或 50 个中文字符） |
| 43006 | Invalid CTA | CTA 按钮无效 | 检查 call_to_action 枚举值 |
| 43007 | Landing Page Required | 缺少落地页 | 某些广告类型必须提供落地页 URL |
| 43008 | Creative Under Review | 素材审核中 | 素材正在审核，等待审核完成后再创建广告 |
| 43009 | Creative Rejected | 素材审核未通过 | 查看审核拒绝原因，修改素材后重新上传 |

---

## 素材相关错误

| 错误码 | 名称 | 说明 | 排查建议 |
|--------|------|------|----------|
| 44000 | File Upload Failed | 文件上传失败 | 检查文件大小、格式，网络连接 |
| 44001 | File Too Large | 文件过大 | 视频最大 500MB，图片最大 10MB |
| 44002 | Invalid File Format | 文件格式无效 | 视频支持 MP4/MOV，图片支持 JPG/PNG |
| 44003 | File Corrupted | 文件损坏 | 文件可能损坏，重新上传 |
| 44004 | Upload Timeout | 上传超时 | 网络不稳定，重试或使用更小的文件 |
| 44005 | Video Duration Invalid | 视频时长无效 | 广告视频时长一般为 5-60 秒 |
| 44006 | Video Resolution Invalid | 视频分辨率无效 | 检查视频分辨率是否符合要求 |
| 44007 | Image Resolution Invalid | 图片分辨率无效 | 检查图片分辨率是否符合要求 |

---

## 定向相关错误

| 错误码 | 名称 | 说明 | 排查建议 |
|--------|------|------|----------|
| 45000 | Invalid Location | 地理位置无效 | 检查地区代码是否正确 |
| 45001 | Invalid Age Range | 年龄范围无效 | 年龄范围 13-65，min <= max |
| 45002 | Invalid Gender | 性别无效 | 检查 gender 枚举值 |
| 45003 | Invalid Language | 语言无效 | 检查语言代码是否正确 |
| 45004 | Audience Too Small | 受众规模过小 | 放宽定向条件，确保受众足够大 |
| 45005 | Invalid Interest | 兴趣分类无效 | 检查兴趣分类 ID 是否正确 |
| 45006 | Invalid Behavior | 行为定向无效 | 检查行为定向 ID 是否正确 |

---

## 常见问题排查

### Q1: 40001 Invalid Access Token
**可能原因**:
1. Token 拼写错误
2. Token 已过期（默认有效期 30 天）
3. Token 被用户撤销

**解决方法**:
1. 检查 token 是否正确
2. 使用 refresh_token 刷新 token
3. 重新授权获取新 token

### Q2: 41004 Budget Too Low
**可能原因**:
1. 日预算低于 $20（OCPM 出价）
2. 总预算低于 $50

**解决方法**:
1. 提高预算金额
2. 检查预算模式是否正确

### Q3: 42008 Optimization Goal Mismatch
**可能原因**:
1. 优化目标与营销目标不兼容
2. 例如：REACH 目标不能使用 INSTALL 优化

**解决方法**:
1. 参考 enums-complete.md 中的搭配矩阵
2. 选择兼容的优化目标

### Q4: 43008 Creative Under Review
**可能原因**:
1. 刚上传的素材正在审核中
2. 审核通常需要 10-30 分钟

**解决方法**:
1. 等待审核完成
2. 可以先创建广告，素材审核通过后自动生效

### Q5: 45004 Audience Too Small
**可能原因**:
1. 定向条件过于严格
2. 目标受众规模不足 1000 人

**解决方法**:
1. 放宽定向条件
2. 扩大投放地区
3. 减少兴趣/行为定向

---

## 实战常见错误速查（按错误信息）

> 以下为实际搭建过程中高频遇到的错误，按错误信息原文索引，包含根因和修复方案。

### 1. "The selected advanced creative is not supported. Please select another one."

**根因**：身份-素材不兼容。BC_AUTH_TT 身份在 Smart+ 广告中必须配合 `tiktok_item_id`（TikTok 已发布帖子），不能用素材库的 `video_id`。

**修复方案**：
- 方案 A：改用普通拍卖广告（`ad_create`），BC_AUTH_TT + 素材库 video_id 在普通拍卖中可用
- 方案 B：先用 Spark Ads Push 把视频推送到 TikTok 账号生成帖子，拿到 `tiktok_item_id` 后再用 Smart+
- 方案 C：用该 TikTok 账号下已有的帖子（`identity_video_get` 查询），取 `item_id` 作为 `tiktok_item_id`

### 2. "Unable to find \"Call_to_action_ID\". Try again."

**根因**：Smart+ 广告要求 `ad_configuration.call_to_action_id`（动态 CTA portfolio ID），但传入的 ID 无效。`creative_cta_recommend_get` 返回的 `asset_ids` 不能直接用作 `call_to_action_id`。

**修复方案**：
- 方案 A：改用普通拍卖广告，CTA 直接用文本枚举值如 `INSTALL_NOW`，不需要动态 CTA ID
- 方案 B：在 Ads Manager 中预先创建 CTA portfolio，获取有效的 `call_to_action_id`
- 方案 C：尝试 `call_to_action_list` 代替 `call_to_action_id`（部分场景支持）

### 3. "Invalid operating system targeting. Please try again."

**根因**：普通拍卖 `adgroup_create` 中，`promotion_type=APP_ANDROID` 或 `APP_IOS` 时必须传 `operating_systems` 字段，不传会报此错。

**修复方案**：
- Android 应用：`operating_systems: ["ANDROID"]`
- iOS 应用：`operating_systems: ["IOS"]`

### 4. "creatives.0.call_to_action: one or more value of the param is not acceptable"

**根因**：普通拍卖 `ad_create` 的 `call_to_action` 必须用大写下划线枚举值，传了自然语言如 "Install Now"。

**修复方案**：用枚举值，完整列表：`WATCH_NOW`, `LISTEN_NOW`, `CALL_NOW`, `BOOK_NOW`, `LEARN_MORE`, `PLAY_GAME`, `SEND_MESSAGE`, `INSTALL_NOW`, `SUBSCRIBE`, `DOWNLOAD_NOW`, `SIGN_UP`, `ORDER_NOW`, `SHOP_NOW`, `VISIT_STORE`, `READ_MORE`, `APPLY_NOW`, `CONTACT_US`, `GET_QUOTE`, `CHECK_AVAILABILITY`, `EXPERIENCE_NOW`, `INTERESTED`, `PREORDER_NOW`, `VIEW_NOW`, `VIEW_PROFILE`, `JOIN_THIS_HASHTAG`, `GET_TICKETS_NOW`, `WATCH_LIVE`, `GET_SHOWTIMES`, `VIEW_VIDEO_WITH_THIS_EFFECT`, `SHOOT_WITH_THIS_EFFECT`

### 5. "Your budget setting must not be less than $50."

**根因**：普通拍卖广告的 CBO（`budget_optimize_on=true`）日预算最低 $50，比 Smart+ 的 $20 高。

**修复方案**：
- 方案 A：提高预算到 $50 或以上
- 方案 B：改用非 CBO 模式（`budget_optimize_on=false`，系列 `budget_mode=BUDGET_MODE_INFINITE`），预算放到广告组级别，日预算最低 $20
- 方案 C：改用 Smart+ CBO，日预算最低 $20

### 6. "ad_configuration.identity_id is required for non-spark ad"

**根因**：Smart+ `ad_create` 中，`creative_info` 未指定 `identity_type` 时系统按 non-spark ad 处理，但含 TikTok 版位时 non-spark ad 已弃用且要求身份。

**修复方案**：
- 在 `creative_info` 中指定 `identity_type` / `identity_id` / `identity_authorized_bc_id`（走 Spark Ad）
- 或改用普通拍卖广告，在 `creatives` 元素中指定身份

### 7. "video material should have 1 image_info as the video cover"

**根因**：SINGLE_VIDEO 格式广告必须同时提供视频和封面图，只传 `video_id` 不传封面图会被拒绝。

**修复方案**：
- Smart+：`creative_info.image_info` 数组中传 `{"web_uri": "<image_id>"}`
- 普通拍卖：`creatives[].image_ids` 数组中传封面图 ID
- 封面图可从素材库搜索（`file_image_ad_search`）或上传获取

### 8. "At least 1 location ID is invalid"

**根因**：`location_ids` 传入了错误的地区 ID。地区 ID 不是国家代码或电话区号，需通过 API 查询。

**修复方案**：
- 通过 `tool_targeting_search`（动态工具）查询正确的 `location_id`
- 示例：泰国正确值为 `1605651`（不是 764314），查询时用 `region_code=TH` 或关键词 "Thailand"

### 9. "Insufficient permissions for some videos"

**根因**：传入的创意 ID / video_id 不属于当前广告账户，或没有权限访问。

**修复方案**：
- 确认视频已上传到当前广告账户的素材库（`file_video_ad_upload`）
- 不要使用其他账户或平台的创意 ID
- 用 `file_video_ad_info_get` 验证视频是否可访问

### 10. "Invalid param(s): 'identity_id' is required for Spark ad."

**根因**：用 `tiktok_item_id` 创建 Spark Ad 时，身份信息放在了 `ad_configuration` 中，但 Spark Ad 要求身份放在 `creative_info` 中。

**修复方案**：
- 在 `creative_info` 中指定 `identity_type` / `identity_id` / `identity_authorized_bc_id`
- 不要在 `ad_configuration` 中指定身份（那是 non-spark ad 的用法）

---

## 获取错误详情

如果错误信息不够详细，可以通过以下方式获取更多信息：

1. **查看 request_id**: 每个 API 响应都包含 request_id，可用于联系技术支持排查
2. **检查响应 message**: 部分错误会在 message 中提供详细说明
3. **查看 HTTP 状态码**:
   - 200: 请求成功（但 code 可能非 0）
   - 400: 请求参数错误
   - 401: 认证失败
   - 403: 权限不足
   - 404: 资源不存在
   - 429: 速率限制
   - 500: 服务器内部错误
