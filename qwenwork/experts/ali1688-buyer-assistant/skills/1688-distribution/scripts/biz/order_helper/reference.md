# 订单助手参考文档

查询 1688 分销订单/退款单信息、识别风险订单、自动催发催揽。

- **多条件查询** — 支持按订单 ID、创建时间、支付时间、订单状态、退款状态筛选
- **风险识别** — 自动识别有发货风险的订单，按商家分组展示
- **批量催发** — 一键向多个卖家发送旺旺催发消息，智能按卖家分组合并

**完整流程：查询订单 → 识别风险 → 催发催揽**

---

## 一、订单查询

### CLI 调用

```bash
# 查询当天订单（默认）
python3 scripts/cli.py order_helper query

# 按订单 ID 查询
python3 scripts/cli.py order_helper query --order_id=4502201509012068443

# 按订单状态查询
python3 scripts/cli.py order_helper query --order_status=waitbuyerreceive

# 按退款状态查询
python3 scripts/cli.py order_helper query --refund_status=waitselleragree

# 按时间范围查询
python3 scripts/cli.py order_helper query --create_start_time="2026-03-20 00:00:00" --create_end_time="2026-03-25 23:59:59"
```

### 接口工具名

`fx_query_order`

### 请求参数

| CLI 参数 | 接口参数 | 类型 | 必填 | 说明 |
|---------|---------|------|------|------|
| `--order_id` | orderId | string | 否 | 订单 ID |
| `--create_start_time` | createStartTime | string | 否 | 创建开始时间，格式：YYYY-MM-DD HH:mm:ss |
| `--create_end_time` | createEndTime | string | 否 | 创建结束时间，格式：YYYY-MM-DD HH:mm:ss |
| `--pay_start_time` | payStartTime | string | 否 | 支付开始时间，格式：YYYY-MM-DD HH:mm:ss |
| `--pay_end_time` | payEndTime | string | 否 | 支付结束时间，格式：YYYY-MM-DD HH:mm:ss |
| `--order_status` | orderStatus | string | 否 | 订单状态（见下方映射表） |
| `--refund_status` | refundStatus | string | 否 | 退款状态（见下方映射表） |
| `--auto_default_today` | - | string | 否 | 默认 `true`，传 `false` 可禁用默认当天查询 |

### 默认查询行为

- **无筛选条件**：自动查询当天订单
- **有筛选条件**：按条件查询，不应用默认当天逻辑
- **禁用默认**：`--auto_default_today=false`

### 返回结构

```json
{
  "success": true,
  "data": {
    "success": true,
    "totalCount": 100,
    "orders": [
      {
        "orderId": "4502201509012068443",
        "createTime": "2026-03-23 15:30:38",
        "payTime": "2026-03-23 15:30:40",
        "orderStatus": "waitbuyerreceive",
        "orderStatusText": "等待买家收货",
        "sellerLoginId": "卖家账号",
        "actualTotalFee": 2.0,
        "productName": "测试商品",
        "riskOrderDesc": "",
        "isRiskOrder": false,
        "refundStatus": "",
        "refundStatusText": "无退款"
      }
    ],
    "warning": "⚠️ 重要提示：符合条件的订单共有 5000 笔，但单次最多返回 3000 笔..."
  }
}
```

> `warning` 字段仅在 `totalCount > 3000` 时出现。

### 返回数量限制

单次查询最多返回 **3000** 笔订单明细。当 `totalCount > 3000` 时，建议：
- 缩小时间范围（如查询 1 天而不是 7 天）
- 指定订单状态
- 指定退款状态

---

## 二、旺旺催发

### CLI 调用

```bash
# 发送旺旺消息（系统自动根据订单 ID 定位卖家）
python3 scripts/cli.py order_helper send --question="请尽快发货" --order_ids=4502201509012068443

# 多个订单（逗号分隔）
python3 scripts/cli.py order_helper send --question="请尽快发货" --order_ids=4502201509012068443,4502201509012068444
```

### 接口工具名

`fx_send_ww`

### 请求参数

| CLI 参数 | 接口参数 | 类型 | 必填 | 说明 |
|---------|---------|------|------|------|
| `--question` | question | string | 是 | 消息内容 |
| `--order_ids` | orderIds | string[] | 是 | 关联订单 ID，CLI 中逗号分隔 |

### 返回结构

```json
{
  "success": true,
  "data": {
    "success": true,
    "task_id": "taskId字符串"
  }
}
```

---

## 三、查询商家回复记录

催发后查询商家是否已回复。

### CLI 调用

```bash
python3 scripts/cli.py order_helper query_reply --task_id=xxx
```

### 接口工具名

`fx_ww_reply`

### 请求参数

| CLI 参数 | 接口参数 | 类型 | 必填 | 说明 |
|---------|---------|------|------|------|
| `--task_id` | wwTaskId | string | 是 | 催发任务 ID（由 `fx_send_ww` 返回） |

### 返回结构

```json
{
  "success": true,
  "data": {
    "success": true,
    "hasReply": true,
    "replies": […]
  }
}
```

- `hasReply: true` → 商家已回复，展示回复内容
- `hasReply: false` → 商家暂未回复

---

## 四、催发后查询商家回复

催发成功后，告知用户："催发已发送，商家通常会在 5-10 分钟内回复。您可以稍后让我查询商家回复。"

当用户要求查询回复时：

1. 使用催发返回的 `task_id` 调用：
   ```bash
   python3 scripts/cli.py order_helper query_reply --task_id=xxx
   ```
2. 根据结果向用户反馈：
   - `hasReply: true` → 展示商家回复内容
   - `hasReply: false` → 告知用户"商家暂未回复，建议稍后再查询或再次催发"

---

## 五、批量催发流程

从订单查询结果中自动筛选风险订单，按卖家分组发送催发消息：

1. 从订单列表中筛选风险订单（`isRiskOrder=true`）
2. 按卖家（`sellerLoginId`）分组
3. 对每个卖家生成催发消息并发送
4. 同一卖家的多个订单合并为一条消息（最多展示前 5 个订单号）

### 消息模板

| 模板 | 说明 | 示例 |
|------|------|------|
| `default` | 默认 | 老板您好，我这边有几个订单需要发货：{订单号}，麻烦尽快处理一下哦，谢谢！ |
| `polite` | 礼貌版 | 老板好，我这边有几个订单想催一下：{订单号}，麻烦帮忙尽快安排发货哈，谢谢啦！ |
| `urgent` | 紧急版 | 老板，这几个订单已经超过 48 小时没有揽收了：{订单号}，买家那边催得比较急，麻烦尽快处理一下哥！ |

---

## 六、风险订单判断

- `riskOrderDesc` 为空 → 正常订单
- `riskOrderDesc` 非空 → 检查订单是否已结束：
  - 订单已取消/已完成 **且** 退款已成功/已关闭 → 不是风险订单（交易已结束）
  - 其他情况 → 风险订单（`isRiskOrder=true`）

---

## 七、订单状态映射

| 状态码 | 中文含义 | 说明 |
|--------|----------|------|
| cancel / cancelled | 已取消 | 订单已取消 |
| waitbuyerpay | 等待买家付款 | 买家未付款 |
| waitsellersend | 等待卖家发货 | 卖家尚未发货 |
| waitbuyerreceive | 等待买家收货 | 已发货，等待确认收货 |
| waitingsellerconfirm | 等待卖家确认 | 退款/退货流程中 |
| finish | 完成 | 订单已完成 |
| success | 交易完成 | 交易完成 |

> 状态码不区分大小写

---

## 八、退款状态映射

| 退款状态码 | 中文含义 | 说明 |
|------------|----------|------|
| （空） | 无退款 | 订单没有退款 |
| waitselleragree | 等待卖家同意 | 买家已申请退款 |
| refundsuccess | 退款成功 | 退款已完成 |
| refundclose | 退款关闭 | 退款已关闭 |
| waitbuyermodify | 商家拒绝待修改 | 卖家拒绝，等待买家修改 |
| waitbuyersend | 待寄回退货 | 等待买家寄回商品 |
| waitsellerreceive | 等待卖家确认收货 | 等待卖家确认收到退货 |
| waitbuyerreceive | 等待买家确认收货 | 等待买家确认收到退款 |

> 状态码不区分大小写，同时支持下划线格式（如 `wait_seller_agree`）

---

## 九、输出格式要求

订单查询结果的展示需遵循以下规范：

### 结构层次

1. **重要提示**（如返回结果有 `warning` 字段，**必须在最开始醒目展示**）
2. **标题**：显示查询时间范围
3. **统计**：总订单数、风险订单数、正常订单数、退款订单数
4. **订单列表**：最多展示 10 个，按创建时间倒序
5. **风险订单明细**：按商家分组详细展示（**重要**）
6. **退款订单明细**：简单说明

### 展示规则

- 风险订单用 ⚠️ 标记，按卖家分组展示（**最重要**）
- 商品名称展示前 6-8 个字符
- 使用 Markdown 格式（标题、表格、列表）
- 关键章节加图标（📊 📋 ⚠️ 💰）

---

## 十、注意事项

- 无需传入 userId，API 通过 AK 自动认证
- 卖家分组自动处理，无需手动指定卖家
- 同一卖家的多个订单 ID 自动拼接到消息中
