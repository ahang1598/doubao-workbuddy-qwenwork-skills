---
name: uupt-skill
description: >-
  UU跑腿同城配送服务。支持帮我送、帮我取、帮我买、帮我办等多种服务，覆盖订单询价、发单下单、查询订单、取消订单、跑男实时追踪、领取优惠券。当用户要真实发起同城配送、代办交易或领取优惠券时使用：「同城配送」「同城急送」「同城快送」「同城跑腿」「跑腿」「发单」「帮送/帮取/帮买」「代购」「代取号」「代排队」「陪诊」「取寄快递」「送文件」「送钥匙」「送花」「送蛋糕」「取东西」「取快递」「取文件」「去XX取」「帮我买」「买奶茶」「买咖啡」「买药」「买饭」「买烟」「搬东西」「装卸」「小时工」「打扫卫生」「布置场地」「琐事代办」「领优惠券」「领券」「领取优惠券」「有优惠券吗」「有什么优惠」「有什么活动」「参加活动」等。通过 uupt-open-cli 执行。
version: "1.1.0"
author: "UU跑腿开放平台"
---

# UU跑腿 Skill

本 Skill 通过 `uupt-open-cli` 提供同城跑腿配送（帮送 / 帮取 / 帮买）和帮帮服务（陪诊、搬抬、代办等）。WorkBuddy 连接本 Connector 时会自动安装 CLI 并完成手机号授权；之后所有业务操作都用 Bash 调用 CLI。

## 调用方式

优先使用 PATH 中的命令；找不到时使用固定安装路径：

```bash
uupt-open-cli <command> [flags]
# macOS / Linux 回退路径
$HOME/.uupt-open-cli/uupt-open-cli <command> [flags]
# Windows 回退路径
%USERPROFILE%\.uupt-open-cli\uupt-open-cli.exe <command> [flags]
```

不要猜测参数。地址、电话、订单号必须来自用户或上一步命令的返回值。价格字段单位是分，展示给用户时除以 100 转为元。

## 场景判断

先判断用户要的是跑腿配送还是帮帮服务：

| 用户表达 | 类型 | 判断依据 |
|---------|------|---------|
| 从 A 送到 B、寄文件、取快递再送到家、帮买后送达 | 跑腿配送 `send` | 物品在两个地点之间传递 |
| 陪诊、搬抬、代排队、现场保洁、只去驿站代取不另送 | 帮帮服务 `help` | 在同一地点提供现场协助 |

- 配送：必须有不同的起点和终点，默认 `--order-type="send"`
- 帮帮：起点与终点相同，必须 `--order-type="help"`，创建订单时必须 `--note`

## 可用命令

### 1. 授权状态（一般不必手动执行）

连接器安装时 WorkBuddy 会执行 `auth login`。若业务命令输出 `[REGISTRATION_REQUIRED]`，再引导用户完成授权。

```bash
uupt-open-cli auth status
uupt-open-cli auth login
uupt-open-cli auth logout
```

| 命令 | 说明 | 成功特征 |
|------|------|---------|
| auth status | 检查是否已授权 | 退出码 0，输出包含 `Logged in as` |
| auth login | 打开本地授权页，用户用手机号+短信完成登录 | 退出码 0，输出 `Logged in as` |
| auth logout | 清除本地 openId，幂等 | 退出码 0 |

兼容命令（聊天中补授权时也可用）：

```bash
uupt-open-cli register --mobile="13800138000"
uupt-open-cli register --mobile="13800138000" --sms-code="123456"
uupt-open-cli register --mobile="13800138000" --image-code="5678"
```

### 2. 询价 `price`

```bash
# 跑腿配送
uupt-open-cli price --from-address="郑州市金水区花园路1号" --to-address="郑州市二七区大学路100号" --city="郑州市"

# 帮帮服务（to-address 可省略，CLI 会自动使用 from-address）
uupt-open-cli price --from-address="郑州市金水区花园路1号" --order-type="help"
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| --from-address | string | 是 | 起点；帮帮时填写服务地点 |
| --to-address | string | 配送必填 | 终点；帮帮可省略 |
| --city | string | 否 | 城市名，需带「市」，默认 `郑州市` |
| --order-type | string | 否 | `send`（默认）或 `help` |

**返回（JSON）**：`body.priceToken`、`body.needPayMoney` / `body.totalMoney`（分）、`body.distance`（米）。priceToken 有时效，拿到后尽快下单。

回复用户时展示元，并确认是否继续下单所需的电话（帮帮再确认具体事项）。

### 3. 下单 `create`

用户明确要发单时：先询价拿 `priceToken`，再立即创建订单，不要二次确认。

```bash
# 跑腿配送
uupt-open-cli create --price-token="TOKEN_FROM_PRICE" --receiver-phone="13800138000"

# 跑腿配送（帮买 / 易碎品建议带 note）
uupt-open-cli create --price-token="TOKEN_FROM_PRICE" --receiver-phone="13800138000" --note="瑞幸生椰拿铁热一杯，少糖"

# 帮帮服务（note 必填）
uupt-open-cli create --price-token="TOKEN_FROM_PRICE" --receiver-phone="13800138000" --note="郑州人民医院东院区陪诊，协助挂号缴费取药"

# 微信渠道需要支付二维码时
uupt-open-cli create --price-token="TOKEN_FROM_PRICE" --receiver-phone="13800138000" --channel="wechat"
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| --price-token | string | 是 | 询价返回的 token |
| --receiver-phone | string | 是 | 收件人 / 联系人手机号 |
| --note | string | 帮帮必填 | 物品说明或帮帮内容 |
| --channel | string | 否 | `wechat` 时生成支付二维码文件 |

**成功**：JSON 中含 `body.orderCode`。

**余额不足**：输出包含 `[PAYMENT_REQUIRED]`，并带：

- `ORDER_CODE=` 订单号
- `PAYMENT_URL=` 支付链接（微信 / 支付宝）
- `QRCODE_FILE=` 本地二维码路径（仅 `--channel="wechat"`）

处理规则：

- 微信渠道：必须带 `--channel="wechat"`，把二维码图片发给用户，不要只发链接
- 其他渠道：直接发送 `PAYMENT_URL`
- 用户确认已支付后，立刻执行 `detail` 查询订单状态

### 4. 查询订单 `detail`

```bash
uupt-open-cli detail --order-code="UU123456789"
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| --order-code | string | 是 | 订单编号 |

返回 JSON：`body.orderCode`、`body.state`、`body.orderPrice`、`body.fromAddress`、`body.toAddress`、`body.driverName`、`body.driverMobile`。

订单状态：`1` 下单成功，`3` 已接单，`4` 已到达，`5` 已取件，`6` 送达中，`10` 已完成，`11` 已取消，`20` 异常。

### 5. 取消订单 `cancel`

```bash
uupt-open-cli cancel --order-code="UU123456789" --reason="地址填错了"
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| --order-code | string | 是 | 订单编号 |
| --reason | string | 否 | 取消原因 |

### 6. 跑男追踪 `track`

```bash
uupt-open-cli track --order-code="UU123456789"
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| --order-code | string | 是 | 订单编号 |

返回 JSON：跑男姓名 / 电话、经纬度、距离。向用户转述当前位置和联系方式，不要原样倾倒坐标。

### 7. 领取优惠券 `coupon`

```bash
uupt-open-cli coupon
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| --source | int | 否 | 领取来源（决定可领哪些券包），默认1，一般无需传入 |

用户要领券或询问优惠（「领券」「领优惠券」「有优惠券吗」「有什么优惠」「有什么活动」「参加活动」）时直接执行，无需额外信息；输出 `[REGISTRATION_REQUIRED]` 时先引导用户完成授权后重试。

**返回字段**（JSON `body`）：

| 字段 | 说明 |
|------|------|
| `newlyClaimed` | 是否本次新领取：true-本次新领取；false-今天已领过（返回当日记录） |
| `couponList` | 领取的优惠券列表，每项含 `packageName`（券包名称，可为空）、`couponDetail`（优惠券信息）、`expireDate`（过期时间 yyyy-MM-dd） |
| `thursdayJoinAble` | 是否可参与淡定星期四活动 |

**回复优先级**：`couponList` 为空或 null → 场景 C；`newlyClaimed=false` → 场景 B；其他 → 场景 A。任意场景下 `thursdayJoinAble=true` 时追加场景 D。回复严格按以下话术模板输出，不得改动任何标点、空行、换行位置，不得输出触发条件或任何 JSON 字段名。

#### 场景 A：领券成功（`newlyClaimed=true` 且 `couponList` 非空）

```
🎉 一键领券完成！本次共领取 N 张优惠券

| 券名称 | 优惠券信息 | 过期时间 |
|--------|---------|--------|
| [packageName] | [couponDetail] | [expireDate] |

可以在UU跑腿App优惠券列表查看所有券详情。
```

> N = couponList 条数；表格按 couponList 逐行输出；packageName 为空时填「优惠券」。

#### 场景 B：当日已领过券（`newlyClaimed=false`）

```
您今天已经领过UU跑腿的优惠券啦，这是今日领取的优惠详情：

| 券名称 | 优惠券信息 | 过期时间 |
|--------|---------|--------|
| [packageName] | [couponDetail] | [expireDate] |

有新的优惠我第一时间通知你 🔔
```

#### 场景 C：无可领券（`couponList` 为空或 null）

```
当前UU跑腿暂无优惠券，有新券上线我第一时间通知你 🔔
```

#### 场景 D：淡定星期四活动（`thursdayJoinAble=true`，附加在上述任意场景回复之后）

命令会输出 `THURSDAY_QRCODE_URL`（远程图片链接）和 `THURSDAY_QRCODE_FILE`（本地图片路径，随 CLI 内嵌，始终可用）。在上述场景话术之后追加以下内容，**图片必须真实展示，不能只输出 URL/路径文本**：

```
另外你还可以参与「淡定星期四」活动，下单1元起！用微信扫描下方二维码即可参与 👇
```

图片展示方式按当前平台能力选择：支持远程 Markdown 图片渲染的平台用 `![淡定星期四活动](THURSDAY_QRCODE_URL)`；不渲染远程链接但有本地图片发送机制的平台直接发送 `THURSDAY_QRCODE_FILE`；两者都不可用时输出活动说明文字 + 可点击的 `THURSDAY_QRCODE_URL` 链接，引导用户微信自行打开。

## 输出标记

| 标记 | 含义 | 处理 |
|------|------|------|
| `[REGISTRATION_REQUIRED]` | 尚未授权 | 引导用户完成 `auth login` 或 `register` |
| `[SMS_SENT]` | 短信已发送 | 请用户回复验证码 |
| `[IMAGE_CAPTCHA_REQUIRED]` | 需要图片验证码 | 从 `IMAGE_DATA=` 展示图片，带 `--image-code` 重试 |
| `[REGISTRATION_SUCCESS]` | 授权成功 | 继续执行用户最初的请求 |
| `[REGISTRATION_FAILED]` | 授权失败 | 从发送验证码步骤重试，最多 3 次 |
| `[PAYMENT_REQUIRED]` | 余额不足 | 按渠道展示支付信息，支付后再 `detail` |
| `[COUPON_RESULT]` | 领券结果 | 提取 `NEWLY_CLAIMED=`、`COUPON_COUNT=`，符合条件时还有 `THURSDAY_JOIN_ABLE=true`、`THURSDAY_QRCODE_URL=`、`THURSDAY_QRCODE_FILE=`，按 coupon 命令的场景话术模板回复 |
| `[OK]` | 操作成功 | 告知用户结果 |
| `[ERROR]` / `[FATAL]` | 失败 | 展示错误信息，不要编造成功 |

退出码：`0` 成功，`1` 一般错误，`2` 需要图片验证码。

## 认证说明

- 用户在 WorkBuddy 中点击连接后，系统执行 `auth login`，打开 `http://127.0.0.1:<port>/login`
- 用户在页面填写手机号、短信验证码（必要时还有图片验证码），CLI 将 `openId` 持久化到 `$HOME/.uupt-open-cli/configs/config.json`
- `auth status` 读取该本地凭证；已授权输出 `Logged in as ...` 且退出码为 0，未授权退出码非 0
- `auth logout` 只删除本地 `openId`，不卸载 CLI；登出后需重新授权
- 凭证跨 WorkBuddy 重启有效；过期或丢失后 `status` 会变为未认证，用户再次连接即可
- 不要把 `appSecret`、完整 `openId` 展示给用户

## 注意事项

- 所有命令通过 CLI 执行，不要直接调用开放平台 HTTP API
- 地址越完整越准确，尽量精确到门牌号；未指定城市时默认郑州市
- 帮买请把商品、规格、缺货如何处理写进 `--note`
- 鲜花、蛋糕等易碎品在 `--note` 注明轻拿轻放 / 保温防震
- 帮帮 `--note` 写清：地点、事项、时长或人数、特殊要求
- 查询结果以 CLI 打印的 JSON 为准，不要编造跑男位置或费用
- 领取优惠券需先完成授权；同一用户同一来源当天只能新领一次，重复领取返回当日记录（`newlyClaimed=false`）；回复严格按场景话术模板输出；`thursdayJoinAble=true` 时必须真实展示活动二维码图片

## English summary

Use `uupt-open-cli` for UU same-city delivery (`send`) and on-site help (`help`). Price first to get `priceToken`, then `create`. Amounts are in cents. If stdout contains `[PAYMENT_REQUIRED]`, send `QRCODE_FILE` for WeChat or `PAYMENT_URL` otherwise. Run `coupon` when the user asks to claim coupons; reply with the fixed scenario templates from `[COUPON_RESULT]`, and show the Thursday activity QR image when `THURSDAY_JOIN_ABLE=true`. Auth is completed by `auth login` during connector connect; `auth status` prints `Logged in as` when signed in.
