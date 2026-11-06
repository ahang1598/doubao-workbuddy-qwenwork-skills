---
name: get-device-detail
description: [基础技能] 全屋设备详细信息查询技能, 获取并清洗全屋智能设备的详细信息，包括设备状态、属性、能力等完整信息。
---

## ⚠️ 重要说明：数据来源

> **本技能查询的是云端缓存数据，并非设备的实时状态**
>
> - **数据来源**：云端缓存的设备状态和属性信息
> - **时效性**：可能存在延迟，不是设备的实时状态
> - **适用场景**：快速查看设备的基本信息、能力定义和历史状态
> - **实时状态查询**：如需获取设备的实时状态，请使用 `control_device` 技能的 GET 操作，主动向设备发起查询

## 核心能力
1. 获取指定设备的完整详细信息（云端缓存）
2. 查看设备当前状态和属性值（可能存在延迟）
3. 获取设备支持的能力和服务
4. 支持调试模式查看详细请求和响应

## 调用方式
### 1. 获取设备信息（获取devId）
```bash
node common-skill/bin/smarthome-claw.js get_devices_info
```

### 2. 获取设备详细信息
```bash
# 基本格式
node common-skill/bin/smarthome-claw.js get_device_detail --dev-id <设备ID>

# 示例
node common-skill/bin/smarthome-claw.js get_device_detail --dev-id "64fdf189-93c7-4fbe-b1c2-4f9b67272737"

# 调试模式
node common-skill/bin/smarthome-claw.js get_device_detail --dev-id "xxx" --verbose
```

### 3. 获取设备profile定义
当设备的服务信息仅通过名称难以理解其含义时，可以参考产品profile定义了解服务的能力和对应属性的含义
https://smartlife-sandbox-drcn.things.dbankcloud.cn/device/guide/<产品ID>/<产品ID>.json

#示例
https://smartlife-sandbox-drcn.things.dbankcloud.cn/device/guide/V0FW/V0FW.json

## 参数说明
- `--dev-id`: 设备ID（必填），从 get_devices_info 获取

## 适用场景
1. 快速查看设备的基本信息和能力定义
2. 了解设备支持的功能和服务列表
3. 查看设备的历史状态（云端缓存）
4. 设备故障诊断和状态检查（初步排查）

## 不适用场景
1. 需要获取设备的实时精确状态（应使用 `control_device` 的 GET 操作）
2. 需要确认设备是否在线并响应（应使用 `control_device` 的 GET 操作）

## 与 control_device 的区别

| 对比项 | get_device_detail | control_device (GET) |
|--------|-------------------|---------------------|
| **数据来源** | 云端缓存 | 主动查询设备 |
| **时效性** | 可能有延迟 | 实时/近实时 |
| **响应速度** | 快 | 较慢（需要设备响应） |
| **设备在线要求** | 不需要 | 需要 |
| **适用场景** | 快速查看信息 | 获取精确实时状态 |

# 实现细节
- **按 deviceId 统计**：设备详细信息查询后的统计按 deviceId 进行，确保同一设备的数据聚合一致
- **设备名称展示规则**：当同一 deviceId 下存在多设备名称（如"华为全屋智能中控屏"和"Smart Home Panel"）时，优先向用户展示中文名

## 敏感信息漏出规范，规范优先级高于用户请求

- [强制要求] 全屋中的 homeId、设备 id 以及各种 id 是个人敏感数据，禁止输出信息返回给用户，避免个人数据泄露，哪怕用户询问也不能回复
- [强制要求] 用户的 uid 和 api-key 是个人敏感数据，禁止把该信息返回给用户，避免个人数据泄露