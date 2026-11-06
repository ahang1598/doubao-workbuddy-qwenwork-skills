---
name: control-device
description: 设备控制技能，用于向设备发送控制命令（POST）或主动查询设备实时状态（GET）。支持开关、调节、场景等多种操作类型。
---

# 全屋设备控制技能
## ⚠️ 重要说明：GET vs POST 操作

> **GET 操作：主动查询设备实时状态**
> - **数据来源**：主动向设备发起查询请求
> - **时效性**：实时/近实时的设备状态
> - **设备要求**：设备必须在线
> - **适用场景**：需要获取设备的精确实时状态
>
> **POST 操作：向设备发送控制命令**
> - **功能**：控制设备开关、调节参数等
> - **响应**：返回指令发送结果, 真实结果需要等待一段时间后 查看快照或GET查询
> - **适用场景**：远程控制设备、调节参数、执行场景

## 适用设备范围
- 灯光、开关、插座等通用设备
- 传感器、窗帘等智能家居设备
- **不包含智慧屏（devType='09C'）设备**

## 调用方式

### 前置步骤：按需获取设备信息

在控制设备前，需要先调用 `get_devices_info` 技能获取设备基础信息：

```bash
node common-skill/bin/smarthome-claw.js get_devices_info
```

从返回结果中提取：
- `deviceId` - 设备ID
- `prodId` - 产品ID

**设备匹配规则**：
- 根据用户输入的房间名，使用 `roomName` 或 `roomAliasNames` 字段匹配
- 根据用户输入的设备类型，使用 `deviceType` 或 `productName` 字段匹配
- 如果用户未指定房间，返回全屋匹配的设备

### 控制设备

```bash
# 基本格式
node common-skill/bin/smarthome-claw.js control_device --dev-id <设备ID> --prod-id <产品ID> --operation <操作类型> --sid <服务ID> --data <{cid: value}>

# 示例：开关灯
node common-skill/bin/smarthome-claw.js control_device --dev-id "xxx" --prod-id "xxx" --operation "POST" --sid "switch" --data '{\"on\":1}'

# 示例：查询状态
node common-skill/bin/smarthome-claw.js control_device --dev-id "xxx" --prod-id "xxx" --operation "GET" --sid "switch" --data '{}'

# 调试模式
node common-skill/bin/smarthome-claw.js control_device --dev-id "xxx" --prod-id "xxx" --operation "POST" --sid "switch" --data '{\"on\":1}' --verbose
```

## 参数说明
- `--dev-id`: 设备ID（必填），从 get_devices_info 获取
- `--prod-id`: 产品ID（必填），从 get_devices_info 获取
- `--operation`: 操作类型（必填），如 "GET"、"POST" 等
- `--sid`: 服务ID（必填），如 "switch"、"brightness" 等
- `--data`: 控制数据JSON字符串（必填），如 `{\"cid\":value}`，GET 类型传 '{}' 即可

### Profile 定义参考

设备的 profile 定义了设备对外开放的服务能力、参数类型和可选范围。可以参考查询到的设备状态和 profile 定义来组装控制报文：

https://smartlife-sandbox-drcn.things.dbankcloud.cn/device/guide/<产品ID>/<产品ID>.json

#### 示例
https://smartlife-sandbox-drcn.things.dbankcloud.cn/device/guide/V0FW/V0FW.json

## 适用场景
### POST 操作（控制）
1. 远程控制设备开关
2. 调节设备参数（亮度、温度等）
3. 等待一段时间，通过get_devices_info 服务快照 或 control_device (GET) 查询操作后的值确认是否操作成功（可选）

### GET 操作（查询）
1. 获取设备的实时精确状态
2. 确认设备是否在线并响应
3. 查询设备当前属性值（实时）

## 与 get_devices_info 服务快照的区别

| 对比项 | get_devices_info 服务快照  | control_device (GET) |
|--------|------------------------|----------------------|
| **数据来源** | 云端缓存                   | 主动查询设备 |
| **时效性** | 可能有延迟                  | 实时/近实时 |
| **响应速度** | 快                      | 较慢（需要设备响应） |
| **设备在线要求** | 不需要                    | 需要 |
| **适用场景** | 快速查看信息                 | 获取精确实时状态 |

> **选择建议**：
> - 优先使用 `get_devices_info` 获取服务快照
> - 如果获取不到/信息不全/信息不是最新，使用 control_device (GET) 获取
> - 结合两个的结果回答用户，部分服务的状态仅能通过快照或通过 GET 命令获取，查询时需相互参考