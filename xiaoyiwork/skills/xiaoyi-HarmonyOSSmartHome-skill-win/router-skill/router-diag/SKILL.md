---
name: router-diag
description: 路由器诊断和状态查询技能
version: 1.0.0
permissions: 发送get请求和post请求的权限、路由器信息查询权限
---

# Router Diag Skill（路由器诊断和状态查询）

1. Description（技能详细说明）
专注于路由器诊断功能，包括路由器运行状态分析、故障诊断、性能监控等。当用户需要诊断路由器问题、分析网络性能或排查网络故障时，通过此技能查询相关诊断信息，以清晰友好的格式返回结果。

2. When to use（触发场景：明确 AI 何时调用此技能）
用户说："网络卡了"
用户说："无法上网"
用户说："查询路由器运行状态"
用户说："路由器故障诊断"
用户说："路由器性能分析"
用户说："网络问题排查"
用户说："设备连接问题"
用户说："网络延迟分析"
用户说："网络卡顿"

3. How to use（调用逻辑：教 AI 如何使用技能）
3.1 回复规则
（1）当答复用户时，首先简短一句话告知用户，例如 "好的，已收到"、"请稍等，正在帮您处理"，无需告知底层请求流程；
（2）查询结果以简洁清晰的格式统一展示给用户，不要对用户答复详细过程数据和过于专业的内部参数；
（3）【强制】在用户有多个家庭、多个路由场景下，需要明确询问用户具体选择，禁止随机、默认选择；
（4）【强制】禁止在回复中展示命令执行过程/CLI调用/API请求等技术细节；
（5）如果信道拥挤或干扰大，直接触发信道优化；
（6）如果子母路由组网速率低于100Mbps，建议用户改变路由摆放位置和检查路由环境干扰；

3.2 前置必要条件（强制：不能跳过该步骤）
（1）获取用户要查询的家庭信息，若有多个家庭，都列举出家庭名称，追问用户，让用户自己选择具体的家庭信息；
（2）在用户选择家庭后，将该家庭下的所有路由名称列出来，追问用户，让用户选择具体要查询的路由；
（3）通过--router-id 和 --prod-id 参数指定路由器设备，用于后续发送请求

3.3 路由器诊断查询逻辑
（1）识别用户的具体诊断需求：
    - 系统状态：路由器进程状态、系统运行状况、内存情况等
    - 连接检测：网络连接状态、WAN连接质量、主路由网口协商速率情况、子母路由之间组网协商速率情况特别是有plc组网
    - 网络信息：信道状态、网络配置情况
（2）根据需求选择对应的诊断命令
（3）执行诊断命令并整理返回结果

3.4 命令行调用方式
(1)信道优化
# 触发信道优化
node router-skill/bin/router-claw.js set_channel_update
(2)组网速率
# 查询子母路由之间组网协商速率
node router-skill/bin/router-claw.js get_link_rate
(3)主路由网口协商速率
# 查询主路由网口协商速率
node router-skill/bin/router-claw.js get_eth_negotiation

3.5 数据展示格式
开头固定："您家路由器诊断结果如下："

系统状态展示：
- 运行状态（正常运行/异常/维护中）
- CPU使用率、内存使用情况
- 系统运行时间
- 服务进程状态

网络诊断展示：
- 网络连接质量（良好/一般/差）
- 延迟、丢包率（如适用）
- 带宽使用情况
- 并发连接数
- 当前信道情况
- 子母路由之间组网协商速率情况特别是有plc组网
- 主路由网口协商速率情况

性能指标展示：
- CPU负载
- 内存占用
- 磁盘使用率
- 网络吞吐量

异常信息展示：
- 错误日志摘要
- 告警信息
- 问题建议

4. Edge cases（边缘场景）
模糊描述：询问用户具体需要诊断什么问题；
信息不足：告知用户"诊断信息不完整，请稍后重试"；
状态异常：在结果中明确标注异常状态并提供修复建议
网络问题：建议用户检查网络线路、运营商服务等

5. 支持查询 SID 清单
下挂设备：.sys/gateway/system/HostInfo?filterAndroid=true&isSupportHostZip=true
儿童保护：.sys/gateway/ntwk/childHomepage
上网方式：.sys/gateway/ntwk/wan?type=active
上行网络：.sys/gateway/ntwk/wandetect
信道优化：.sys/gateway/ntwk/channelinfo
5G 优选：.sys/gateway/ntwk/wlandbho
IPv6：.sys/gateway/ntwk/ipv6_enable
用户体验计划：.sys/gateway/system/userbehavior
路由状态：.sys/gateway/system/processstatus
WiFi 配置：.sys/gateway/ntwk/wlanradio
路由器进程状态：.sys/gateway/system/processstatus
网络连接检测：.sys/gateway/ntwk/wandetect
WAN状态查询：.sys/gateway/ntwk/wan?type=active
信道信息查询：.sys/gateway/ntwk/channelinfo
子母路由之间组网协商速率查询：.sys/gateway/device/hostmap
主路由网口协商速率查询：.sys/gateway/ntwk/ethnegotiation