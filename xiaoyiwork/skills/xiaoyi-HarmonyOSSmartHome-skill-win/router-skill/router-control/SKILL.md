---
name: router-control
description: 路由器控制操作技能
version: 1.0.0
permissions: 发送get请求和post请求的权限、路由器控制操作权限
---

# Router Control Skill（路由器控制操作）

1. Description（技能详细说明）
专注于路由器控制操作和状态查询功能，包括设备状态查询、网络连接状态查询、上网方式查询、信道开关状态等。当用户需要对路由器进行控制管理或查询网络状态时，通过此技能执行具体的控制命令或查询操作，以操作结果或状态信息的形式返回给用户。

2. When to use（触发场景：明确 AI 何时调用此技能）
用户说："网络状态查询"
用户说："查询上网方式"
用户说："查询上行"
用户说："查询信道优化"
用户说："查询5G优选"
用户说："控制5G优选"
用户说："查询ipv6"
用户说："控制ipv6"
用户说："查询路由器状态"
用户说："查询WiFi配置"
用户说："查询访客WiFi状态"
用户说："查询WiFi功率模式"
用户说："查询用户体验计划"
用户说："查询网口速率"
用户说："查询ETH端口"
用户说："控制用户体验计划"
用户说："控制WiFi功率模式"
用户说："控制游戏加速"
用户说："WiFi定时关闭"
用户说："语音接入调优"
用户说："上报故障日志"
用户说："Hota升级检测"
用户说："路由语音重启"
用户说："控制WiFi黑白名单"
用户说："控制设备限速"
用户说："控制备用WiFi"

3. How to use（调用逻辑：教 AI 如何使用技能）
3.1 回复规则
（1）当答复用户时，首先简短一句话告知用户，例如 "好的，已收到"、"请稍等，正在帮您处理"，无需告知底层请求流程；
（2）最终结果以简洁清晰的 checklist 形式统一展示给用户，不要对用户答复详细过程数据和过于专业的内部参数；
（3）【强制】在用户有多个家庭、多个路由场景下，需要明确询问用户具体选择，禁止随机、默认选择；
（4）【强制】禁止在回复中展示命令执行过程/CLI调用/API请求等技术细节；

3.2 前置必要条件（强制：不能跳过该步骤）
（1）获取用户要控制的家庭信息，若有多个家庭，都列举出家庭名称，追问用户，让用户自己选择具体的家庭信息；
（2）在用户选择家庭后，将该家庭下的所有路由名称列出来，追问用户，让用户选择具体要对接的路由，并获取该路由的device id，用于具体对接配置；
（3）通过--router-id 和 --prod-id 参数指定路由器设备，用于后续发送请求

3.3 路由器控制操作和查询逻辑
（1）识别用户的具体需求：
    - 控制操作：时长控制、时段控制、断网控制
    - 状态查询：网络连接状态、上网方式、信道开关、设备信息等
（2）根据需求选择对应的控制命令或查询命令
（3）执行相关命令并返回操作结果或状态信息

> **【重要】儿童上网保护相关操作（时段设置、时长设置、断网控制）请参阅 child-protect 子技能文档**

3.4 命令行调用方式
（1）网络状态查询功能
# 查询路由下挂设备信息
node router-skill/bin/router-claw.js get_host_info
**【重要】设备是否在线通过hostInfo接口返回的active字段判断**

# 查询当前上网方式
node router-skill/bin/router-claw.js get_wan_status

# 查询上行网络连接状态
node router-skill/bin/router-claw.js get_wandetect

# 查询自动优化信道开关状态
node router-skill/bin/router-claw.js get_channel_info

# 查询5G优选开关状态
node router-skill/bin/router-claw.js get_5g_optimize

# 查询ipv6开关状态
node router-skill/bin/router-claw.js get_ipv6

# 查询路由器状态
node router-skill/bin/router-claw.js get_router_status

# 查询WiFi配置（同时查询wlandbho和WlanBasic）
# 注意：WiFi密码脱敏处理
node router-skill/bin/router-claw.js get_wifi_config

# 查询访客WiFi状态
node router-skill/bin/router-claw.js get_guest_wifi

# 查询WiFi功率模式
node router-skill/bin/router-claw.js get_power_mode

# 查询用户体验计划开关状态
node router-skill/bin/router-claw.js get_user_behavior

# 查询网口速率
node router-skill/bin/router-claw.js get_link_rate

# 查询ETH端口协商状态
node router-skill/bin/router-claw.js get_eth_negotiation

# 查询游戏加速记录
node router-skill/bin/router-claw.js get_game_history

# 查询路由运行周报
**【重要】必须回答以下：路由一周运行时间、上网高峰时段（早中晚）、流量报告、上网时间设备排行，统计不要用血条图，使用红绿圆圈**
node router-skill/bin/router-claw.js get_week_report

（2）访客WiFi控制功能
**【重要】set_guest_wifi的设置结果必须再通过get_guest_wifi查询最新配置来判断，严禁通过errcode判断。若查询无响应或配置不符，则提示用户访客WiFi设置功能暂不可用，严禁提示用户设置失败**

**【重要】访客WiFi仅支持开放网络（无密码），不支持设置密码。若用户要求设置访客WiFi密码，需提示用户："很抱歉，当前不支持设置访客WiFi密码，如需设置密码请到智慧生活App的路由器设置界面进行操作"。**

# 开启访客WiFi（同时开启2.4G和5G），默认有效期为1天
node router-skill/bin/router-claw.js set_guest_wifi --data '{"enable":true,"ssid":"MyGuestWiFi"}'

# 开启访客WiFi，设置有效期为4小时
node router-skill/bin/router-claw.js set_guest_wifi --data '{"enable":true,"ssid":"MyGuestWiFi","validTime":1}'

# 开启访客WiFi，设置有效期为不限时
node router-skill/bin/router-claw.js set_guest_wifi --data '{"enable":true,"ssid":"MyGuestWiFi","validTime":3}'

# 关闭访客WiFi
node router-skill/bin/router-claw.js set_guest_wifi --data '{"enable":false,"ssid":"MyGuestWiFi"}'

**【重要】validTime 参数说明：**
| validTime值 | 含义 |
|-------------|------|
| 1 | 4小时 |
| 2 | 一天（默认） |
| 3 | 不限时 |

（3）5G优选控制功能
# 开启5G优选（先GET查询配置，再POST下发开关）
node router-skill/bin/router-claw.js set_5g_optimize --data '{"DbhoEnable":true}'
# 关闭5G优选（先GET查询配置，再POST下发开关）
node router-skill/bin/router-claw.js set_5g_optimize --data '{"DbhoEnable":false}'

（4）ipv6控制功能
# 开启ipv6
node router-skill/bin/router-claw.js set_ipv6 --data '{"Enable":true}'
# 关闭ipv6
node router-skill/bin/router-claw.js set_ipv6 --data '{"Enable":false}'

（5）用户体验计划控制功能
# 开启用户体验计划
node router-skill/bin/router-claw.js set_user_behavior --data '{"Enable":true}'
# 关闭用户体验计划
node router-skill/bin/router-claw.js set_user_behavior --data '{"Enable":false}'

（6）WiFi功率模式控制功能
# 设置睡眠模式
node router-skill/bin/router-claw.js set_power_mode --data '{"PowerMode":0}'
# 设置一般模式
node router-skill/bin/router-claw.js set_power_mode --data '{"PowerMode":1}'
# 设置穿墙模式
node router-skill/bin/router-claw.js set_power_mode --data '{"PowerMode":2}'
**【重要】PowerMode 参数说明：**
| PowerMode | 含义 |
|-----------|------|
| 0 | 睡眠模式 |
| 1 | 一般模式 |
| 2 | 穿墙模式 |

（7）游戏加速控制功能
# 开启游戏加速
node router-skill/bin/router-claw.js set_Game_acceleration --data '{"HiGameControlEnable":"true"}'
# 关闭游戏加速
node router-skill/bin/router-claw.js set_Game_acceleration --data '{"HiGameControlEnable":"false"}'

（8）WiFi定时关闭控制功能
# 设置WiFi定时关闭（例如设置每天21:00到次日7:00这段时间WiFi定时关闭）
node router-skill/bin/router-claw.js set_wifi_timeswitch --action add --data '{"Enable":true,"ID":-1,"RepeatDay":"7,1,2,3,4,5,6","EndTime":"07:00","StartTime":"21:00","deviceMac":"","action":"","isSelected":false}'
# 设置删除某WiFi定时关闭（例如删除周日、周二、周三设置每天11:00到12:00这段时间的WiFi定时关闭，先查询所有WiFi定时关闭时段，如果时间段没有设置定时关闭提醒用户未设置）
node router-skill/bin/router-claw.js set_wifi_timeswitch --action delete --data '{"Enable":true,"ID":-1,"RepeatDay":"7,2,3","EndTime":"12:00","StartTime":"11:00","deviceMac":"","action":"","isSelected":false}'

（9）语音控制接入调优
# 设备接入调优到其他路由（先查询目的路由的MAC地址，CfgBssid填充要目的路由MAC，StaMac填充设备MAC）
node router-skill/bin/router-claw.js smart_dev_connect --data '{"delType":0,"CfgBssid":"","StaMac":""}'
（10）故障日志上报
# 查询主路由MAC地址
node router-skill/bin/router-claw.js get_lan_host
# 故障日志上报(注意：先查询主路由MAC地址，然后把DiagnoseTags填充32个随机和随机字母组成的字符串，DiagnoseMac填充主路由mac地址)
node router-skill/bin/router-claw.js set_upload_log --data '{"CrashAction":"BetaClubFeedBack","DiagnoseTag":"","DiagnoseMac":""}'

（11）Hota升级检测
node router-skill/bin/router-claw.js set_online_upg --action check --data '{"UpdateAction":1,"DevId":"all"}'

（12）路由语音重启
node router-skill/bin/router-claw.js set_reboot --action update --data '{"request":""}'

（13）WiFi黑白名单控制功能
# 设置密码接入（黑名单模式）
node router-skill/bin/router-claw.js set_antisteal_mode --data '{"StealNetModel":0}'
# 黑名单模式下开启WLAN防爆力破解
node router-skill/bin/router-claw.js set_homesec_abfa --data '{"AbfaEnable":true}'
# 黑名单模式下关闭WLAN防爆力破解
node router-skill/bin/router-claw.js set_homesec_abfa --data '{"AbfaEnable":false}'
# 设置设备加入黑名单，如果当前不是黑名单模式也无需切换到黑名单模式
node router-skill/bin/router-claw.js set_auth_Device --data '{"operFlag":2,"mac":""}'
# 设置设备移除黑名单
node router-skill/bin/router-claw.js set_auth_Device --data '{"operFlag"1,"mac":""}'

# 设置授权接入（授权模式）
node router-skill/bin/router-claw.js set_antisteal_mode --data '{"StealNetModel":1}'
# 设置设备加入授权（mac填充设备MAC）
node router-skill/bin/router-claw.js set_auth_Device --data '{"operFlag":1,"mac":""}'
# 设置拒绝设备加入授权（mac填充设备MAC）
node router-skill/bin/router-claw.js set_auth_Device --data '{"operFlag":2,"mac":""}'
# 设置设备移除授权（mac填充设备MAC）
node router-skill/bin/router-claw.js set_auth_Device --data '{"operFlag":5,"mac":""}'

# 设置白名单接入（白名单模式）
node router-skill/bin/router-claw.js set_antisteal_mode --data '{"StealNetModel":2}'
# 设置设备加入白名单
node router-skill/bin/router-claw.js set_auth_De vice --data '{"operFlag":1,"mac":""}'
# 设置设备移除白名单
node router-skill/bin/router-claw.js set_auth_Device --data '{"operFlag":5,"mac":""}'

（14）设备限速控制功能
# 设置设备限速（需要执行下面两个命令，例如设置设备最大上传速度200Mbps，最大下载速度300Mbps，MACAddress填充设备的MAC地址，HostName填充设备名称，注意：不要遗漏参数）
node router-skill/bin/router-claw.js set_Device_ratelimit --action update --data '{"HostName":"","MACAddress":"","DeviceMaxDownLoadRate":300000,"ClassQueue":-1,"ActualName":"","DeviceDownRateEnable":true,"ID":"InternetGatewayDevice.LANDevice.1.Hosts.Host.10.","QosclassID":"","PolicerID":"","DeviceMaxUpLoadRate":200000}'

node router-skill/bin/router-claw.js set_Device_ratelimit --action update --data '{"HostName":"","MACAddress":"","DeviceMaxDownLoadRate":300000,"ClassQueue":-1,"ActualName":"","DeviceDownRateEnable":true,"ID":"InternetGatewayDevice.LANDevice.1.Hosts.Host.10.","QosclassID":"InternetGatewayDevice.QueueManagement.Classification.3.","PolicerID":"InternetGatewayDevice.QueueManagement.Policer.2.","DeviceMaxUpLoadRate":200000}'
# 设置设备网速无限制（MACAddress填充设备的MAC地址，HostName填充设备名称，注意：不要遗漏参数）
node router-skill/bin/router-claw.js set_Device_ratelimit --action update --data '{"HostName":"","MACAddress":"","DeviceMaxDownLoadRate":300000,"ClassQueue":-1,"ActualName":"","DeviceDownRateEnable":false,"ID":"InternetGatewayDevice.LANDevice.1.Hosts.Host.10.","QosclassID":"InternetGatewayDevice.QueueManagement.Classification.3.","PolicerID":"InternetGatewayDevice.QueueManagement.Policer.2.","DeviceMaxUpLoadRate":200000}'

（15）路由LED灯控制
# 打开路由LED灯（Mac填充指定路由的MAC地址）
node router-skill/bin/router-claw.js set_led_status --data '{"Action":1,"Mac":""}'
# 关闭路由LED灯（Mac填充指定路由的MAC地址）
node router-skill/bin/router-claw.js set_led_status --data '{"Action":0,"Mac":""}'
3.5 数据展示格式
控制操作数据展示格式：
开头固定：操作已执行成功，结果如下：
展示控制结果状态
展示生效的配置信息
如涉及时长，转换用户友好的时间格式展示

状态查询数据展示格式：
开头固定：您家当前路由器状态如下：

设备信息展示：
- 设备名称、型号
- IP地址、MAC地址
- 在线状态（在线/离线）
- 连接时长（在线设备）

网络状态展示：
- 上网方式（宽带/DHCP/静态等）
- 连接状态（正常/异常）
- 上传/下载速率（如适用）

配置信息展示：
- WiFi名称、频段
- 信道、信号强度
- 优化功能状态
- IPv6支持状态

4. Edge cases（边缘场景）
控制操作：
模糊描述：询问用户具体需要什么控制操作；
配置冲突：告知用户可能存在配置冲突，建议先清理旧配置；
请求失败：告知用户 "操作失败，请稍后重试"。

状态查询：
模糊描述：询问用户具体需要查询哪方面的信息；
信息不足：告知用户"查询到信息不完整，请稍后重试"；
状态异常：在结果中明确标注异常状态并提供建议。

5. 支持查询 SID 清单
下挂设备：.sys/gateway/system/HostInfo?filterAndroid=true&isSupportHostZip=true
WAN状态：.sys/gateway/ntwk/wan?type=active
上行网络：.sys/gateway/ntwk/wandetect
信道优化：.sys/gateway/ntwk/channelinfo
5G优选：.sys/gateway/ntwk/wlandbho
IPv6：.sys/gateway/ntwk/ipv6_enable
路由状态：.sys/gateway/system/processstatus
WiFi配置：.sys/gateway/ntwk/wlanradio
访客WiFi：.sys/gateway/ntwk/guest_network
5G优选开关：.sys/gateway/ntwk/WlanBasic
查询/用户体验计划开关:.sys/gateway/system/userbehavior
查询/设置WiFi功率模式:.sys/gateway/ntwk/wlanradio
查询游戏加速记录:.sys/gateway/hilink/higame_games_v2?allGames=true
查询路由运行周报:.sys/gateway/app/weeklyreport
控制游戏加速:.sys/gateway/hilink/higamecontrol
控制WiFi定时关闭:.sys/gateway/ntwk/wlantimeswitch
语音控制接入调优:.sys/gateway/ntwk/smart_dev_manual_connect
查询主路由mac地址:.sys/gateway/ntwk/lan_host
控制上报故障日志:.sys/gateway/system/diagnose_crash
Hota升级检测:.sys/gateway/system/onlineupg
控制路由语音重启:.sys/gateway/service/reboot.cgi
控制WiFi黑白名单:.sys/gateway/ntwk/access_auth
控制WLAN防爆力破解:.sys/gateway/ntwk/homesec_abfa
控制设备加入黑名单:.sys/gateway/ntwk/wlanfilterenhance
控制设备加入授权:.sys/gateway/ntwk/access_auth
控制设备加入白名单:.sys/gateway/ntwk/access_auth
控制设备限速:.sys/gateway/app/qosclass_host
开关路由LED灯:.sys/gateway/hilink/ledstatus