# 店铺信息查询参考文档

查询用户绑定的三方分销工具和店铺列表，过滤已过期的工具/店铺，为铺货提供目标店铺选择。

---

## 一、CLI 调用

```bash
# 查询店铺和工具信息（自动过滤已过期的工具和店铺）
python3 scripts/cli.py shop_info query
```

### 接口工具名

`shop_and_tool_info`

### 请求参数

无需传入任何参数，API 通过 AK 自动识别用户身份。

### 返回结构

```json
{
  "success": true,
  "data": {
    "toolList": [
      {
        "appKey": "{appKey}",
        "appName": "{工具名称}",
        "toolAuthContent": "已订购",
        "toolExpired": false,
        "channelList": [
          {
            "channel": "douyin",
            "channelDesc": "抖音",
            "shopList": [
              {
                "shopCode": "{shopCode}",
                "shopName": "{店铺名称}",
                "channelAuthExpired": false
              }
            ]
          }
        ]
      }
    ]
  }
}
```

### 关键字段说明

| 字段 | 说明 |
|------|------|
| `appKey` | 三方服务商唯一标识（铺货时需要） |
| `appName` | 工具名称 |
| `toolExpired` | 工具是否已过期（true=过期，自动过滤） |
| `channel` | 渠道标识（如 douyin、pinduoduo、taobao） |
| `channelDesc` | 渠道中文名（如 抖音、拼多多、淘宝） |
| `shopCode` | 店铺编码（铺货时需要） |
| `shopName` | 店铺名称 |
| `channelAuthExpired` | 店铺授权是否过期（true=过期，自动过滤） |

### 过滤规则

CLI 返回的数据已自动过滤：
- `toolExpired: true` 的工具整个移除
- `channelAuthExpired: true` 的店铺移除
- 过滤后无店铺的渠道移除，无渠道的工具移除

---

## 二、确认铺货目标

### toolList 为空（用户未绑定任何分销工具）

输出绑店引导话术，然后**停止当前流程，等待用户完成绑店后重新发起**：

> 您还没有绑定店铺到 1688 分销系统，需要先完成绑店才能铺货。
>
> ### 绑店步骤
> 1. 进入绑店页面，选择你的下游平台（抖音/淘宝/拼多多等）
> 2. 授权 1688 分销工具，勾选"我同意并签署协议"
> 3. 订购并授权下游工具（铺货工具 + 交易工具）
> 4. 确认显示"已授权"后，绑店完成
>
> **绑店快速入口：**
> - [一件代发页面](https://air.1688.com/app/channel-fe/search/index.html?#/result)
> - [AI 工作台绑店](https://air.1688.com/app/channel-fe/distribution-work/ai-assistant.html#/multi-agent-shop-binding)
>
> 遇到问题可加入官方钉钉群（群号：41361847）咨询。
> 绑店完成后，告诉我"绑好了"，我继续帮您铺货。

### 用户已明确指定渠道但该渠道下没有可用店铺

提示用户当前没有该渠道的店铺，列出已有的渠道和店铺供选择，或引导用户去绑定目标渠道的店铺。

### toolList 不为空，正常选择店铺

- **只有 1 个可用店铺** → 直接使用，无需询问
- **有多个可用店铺** → 列出供用户选择
- 用户已明确指定渠道时，优先过滤该渠道

### 展示格式

```
您当前绑定的店铺如下：

**【{工具名称}】**
  - 抖音 · {店铺名称}（店铺编码：{shopCode}）
**【另一个工具】**
  - 拼多多 · {店铺名称2}（店铺编码：{shopCode2}）

请问您要将商品铺货到哪个店铺？
```

---

## 三、注意事项

- 无需传入 userId，API 通过 AK 自动认证
- 所有已过期的工具和店铺已在返回前自动过滤
- 铺货时需要的关键信息：`appKey`（工具标识）、`shopCode`（店铺编码）、`channel`（渠道标识）
