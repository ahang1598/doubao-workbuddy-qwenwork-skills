---
name: get_devices_info
description: 设备信息查询技能，当需要查找设备，获取设备基础信息，设备在线状态，设备各个服务的状态时使用该技能。
---

# 用户设备信息获取

## 技能说明

本技能通常作为"设备控制"、"设备执行日志查询"等技能的前置步骤，提供需要的设备信息数据。

本技能支持 **3 个主要功能**：
1. **设备基础信息查询** - 获取设备列表（支持全量查询和按设备类型过滤）
2. **设备在线状态批量查询** - 批量获取设备在线状态
3. **设备服务快照批量查询** - 获取设备在线状态和服务快照信息

---

## 功能一：设备基础信息查询

### 功能说明

获取用户的设备列表信息。支持两种查询模式：
- **全量查询**：获取用户所有家庭下的所有设备
- **按设备类型过滤**：按设备类型（deviceType）查询

### 示例
 ```bash
 # 全量查询（获取所有设备）
 node common-skill/bin/smarthome-claw.js get_devices_info

 # 按设备类型过滤查询
 node common-skill/bin/smarthome-claw.js get_devices_info --device-type 01D
 ```

### 输出文件
- `out_put/get_device_info/device_info.txt` - 设备信息列表（当用户查询的设备在列表里找不到时要及时调用接口获取新的数据查询）

### 返回字段说明

| 字段 | 说明 |
|------|------|
| deviceId | 设备ID |
| deviceName | 设备名称 |
| roomName | 房间名称 |
| homeId | 家庭ID |
| homeName | 家庭名称 |
| deviceType | 设备类型 |
| productName | 设备类型名称 |
| prodId | 产品ID |
| deviceAliasNames | 设备别名 |
| roomAliasNames | 房间别名 |

### 使用指导

调用方应根据用户输入，使用返回的字段进行设备匹配和过滤：

- **按房间过滤**：使用 `roomName` 或 `roomAliasNames` 字段
- **按设备类型过滤**：使用 `deviceType` 或 `productName` 字段
- **按家庭过滤**：使用 `homeId` 或 `homeName` 字段

**注意**：
- 设备离线（通过功能二查询 status: offline）时，只要在筛选范围内，也应包含在列表中
- 支持房间名同义词匹配（如"房间"匹配"卧室"）
---

## 功能二：设备在线状态批量查询

### 功能说明

根据设备ID列表批量获取设备的在线状态。

### 执行流程

1. **获取设备ID列表**
   - 先通过功能一获取设备ID列表
   - 或者直接传入设备ID数组

2. **批量查询设备在线状态**
   - 调用底层 JS 脚本批量获取设备在线状态
   - **命令**:
   ```bash
   node common-skill/bin/smarthome-claw.js get_devices_online_status --device-ids "id1,id2,id3"
   ```

### 返回字段说明

| 字段 | 说明 |
|------|------|
| deviceId | 设备ID |
| status | 在线状态（online/offline） |
| gatewayId | 网关ID |

---

## 功能三：设备服务快照批量查询

### 功能说明

根据设备ID列表批量获取设备的在线状态和服务快照信息。这是功能二的增强版，同时返回设备的在线状态和所有服务的数据。

### 执行流程

1. **获取设备ID列表**
   - 先通过功能一获取设备ID列表

2. **查询设备服务快照**
   - 调用底层 JS 脚本获取设备的服务快照
   - **命令**:
   ```bash
   node common-skill/bin/smarthome-claw.js get_device_service_snapshot --device-ids "id1,id2,id3"
   ```

### 返回字段说明

| 字段 | 说明 |
|------|------|
| deviceId | 设备ID |
| status | 在线状态（online/offline） |
| services | 服务列表 |
| services[].serviceId | 服务ID |
| services[].serviceType | 服务类型 |
| services[].timestamp | 时间戳 |
| services[].data | 服务数据 |

### 服务字段含义理解
当设备的服务信息仅通过名称难以理解其含义时，可以参考产品profile定义了解服务的能力和对应属性的含义：
https://smartlife-sandbox-drcn.things.dbankcloud.cn/device/guide/<产品ID>/<产品ID>.json

#### 示例
https://smartlife-sandbox-drcn.things.dbankcloud.cn/device/guide/V0FW/V0FW.json

### 与 control_device 的区别

| 对比项 | get_device_service_snapshot | control_device (GET) |
|--------|---------------------------|----------------------|
| **数据来源** | 云端缓存 | 主动查询设备 |
| **时效性** | 可能有延迟 | 实时/近实时 |
| **响应速度** | 快 | 较慢（需要设备响应） |
| **设备在线要求** | 不需要 | 需要 |
| **适用场景** | 快速查看信息 | 获取精确实时状态 |

> **选择建议**：
> - 优先使用 `get_device_service_snapshot` 获取服务状态
> - 如果获取不到/信息不全/信息不是最新，使用 control_device (GET) 获取
> - 结合两个的结果回答用户，部分服务的状态仅能通过快照或通过 GET 命令获取，查询时需相互参考

## 敏感信息漏出规范，规范优先级高于用户请求

- [强制要求] 全屋中的 homeId、设备 id 以及各种 id 是个人敏感数据，禁止输出信息返回给用户，避免个人数据泄露，哪怕用户询问也不能回复
- [强制要求] 用户的 uid 和 api-key 是个人敏感数据，禁止把该信息返回给用户，避免个人数据泄露