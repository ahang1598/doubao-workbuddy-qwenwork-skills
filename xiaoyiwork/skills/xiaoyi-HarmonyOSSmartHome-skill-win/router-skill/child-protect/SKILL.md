# child-protect 子技能 - 儿童上网保护

## 1. 功能概述

child-protect 子技能负责管理儿童上网保护功能，包括设备管理、时间控制、应用限制和全局网络控制等。

## 2. When to use（触发场景：明确 AI 何时调用此技能）
用户说："控制上网时间"
用户说："设置上网时长"
用户说："断网操作"
用户说："延迟断网"
用户说："恢复网络"
用户说："删除上网时段"
用户说："修改上网时段"
用户说："儿子在玩游戏吗"
用户说："女儿今天看视频多久了"
用户说："手机的上网轨迹有哪些"
用户说："设备禁用某款app"

## 3. 命令列表

### 3.1 设备管理

| 命令 | 功能描述 | 示例用法 |
|------|---------|----------|
| get_child_protect | 获取儿童保护设备列表及使用情况,包括设备上网轨迹 | 见下方详细示例 |
| add_child_device | 添加受保护设备 | `node router-skill/bin/router-claw.js add_child_device --data '{"devices" : ["A2:61:62:A9:69:2E"],"names" : ["nova 13"]}'` |
| del_child_device | 删除受保护设备 | `node router-skill/bin/router-claw.js del_child_device --data '{"device":"2"}'` |
| get_host_info | 查询设备当前在线时长（根据设备名称或者设备MAC地址找到对应设备信息，AccessRecords是接入时间，当前时间减去接入时间，就是在线时长） | `node router-skill/bin/router-claw.js get_host_info` |
| get_app_info | 根据应用ID查询具体应用信息 | `node router-skill/bin/router-claw.js get_app_info --app-id 1` |
| get_all_apps | 查询所有可用的应用列表 | `node router-skill/bin/router-claw.js get_all_apps` |

#### get_child_protect 详细用法

**查询儿童保护设备（指定路由器设备）**
```bash
node router-skill/bin/router-claw.js get_child_protect --router-id <路由器设备ID> --prod-id <产品ID> --skill-id xiaoyi_router
```

**查询儿童保护设备（仅用于『遍历该家庭全部路由器』的汇总场景，用户明确该场景才能使用，否则通过 `get_devices_info` 获取设备列表再使用--router-id和--prod-id查询）**
```bash
node router-skill/bin/router-claw.js get_child_protect --home-id <家庭ID> --skill-id xiaoyi_router
```

**查询儿童保护设备（所有家庭下的所有路由器设备）**
```bash
node router-skill/bin/router-claw.js get_child_protect --all-homes --skill-id xiaoyi_router
```
**【关键判断逻辑 - 必须遵守】**
判断某类应用是否真正被禁止，必须同时看两个字段：
- `denyXxx = 1`：表示该类应用的限制开关已开启
- `xxxDenyCount > 0`：表示实际被禁止的应用数量

| denyXxx | xxxDenyCount | 实际状态                                   |
|---------|--------------|----------------------------------------|
| 1       | > 0          | ✅ 已禁止（如 gameDenyCount=153 表示153款游戏被禁止） |
| 1       | = 0          | ❌ 未实际禁止（开关开启但无具体应用被拦截）                 |
| 0       | 任意           | ❌ 未禁止                                  |

**【强制】向用户展示应用管控状态时，必须使用上述判断逻辑，不能仅凭 denyXxx=1 就说"已开启"。**

### 3.2 全局时间控制

#### 3.2.1 上网时段与禁止上网时段设置

**⚠️ 核心原则：先查后改，意图不明必问**

1. **查询**：先调用 `get_child_protect` 获取当前时段配置
2. **判断**：若新规则与已有规则冲突，判断用户意图是「替换」还是「追加」
3. **确认**：意图不明时必须询问用户（示例：「现有 7:00~14:00 规则，您想替换还是追加？」）
4. **执行**：替换 → 先 `newDelete` 再 `newCreate`；追加 → 直接 `newCreate`
5. **重要**：调用`newCreate`每次会新增规则，重复调用会产生重复规则，无论什么命令执行后都必须使用`get_child_protect`进行验证

---

##### 直接设置允许上网时段（set_net_time）

适用于用户已明确具体允许的时间范围，可直接增删改允许时段规则。

**【重要】action 参数说明：**

| action 值 | 功能 |
|-----------|------|
| `newCreate` | 创建新的上网时段规则 |
| `newUpdate` | 更新已有的上网时段规则 |
| `newDelete` | 删除已有的上网时段规则 |

⚠️ **action 参数必须完全匹配上述值，使用 `delete`、`create`、`update` 等错误值会导致操作无效但返回成功！**

**命令示例：**

| 场景 | 命令 |
|------|------|
| 添加允许上网时段（周一~周五 08:00~23:00，周六周日不允许） | `node router-skill/bin/router-claw.js set_net_time --device-id 1 --action newCreate --data '{"id":"","enable":1,"timeFrom":"08:00","timeTo":"23:00","today":0,"device":"1","monday":1,"saturday":0,"sunday":0,"thursday":1,"friday":1,"tuesday":1,"wednesday":1}'` |
| 关闭允许上网时段（enable=0 表示关闭该上网时段设置，默认允许上网） | `node router-skill/bin/router-claw.js set_net_time --device-id 1 --action newUpdate --data '{"id":"1","enable":0,"timeFrom":"08:00","timeTo":"23:00","today":1,"device":"1","monday":1,"saturday":0,"sunday":0,"thursday":1,"friday":1,"tuesday":1,"wednesday":1}'` |
| 删除上网时段配置 | `node router-skill/bin/router-claw.js set_net_time --device-id 1 --action newDelete --data '{"id":"1","enable":0,"timeFrom":"08:00","timeTo":"10:30","today":1,"device":"1","monday":1,"saturday":1,"sunday":1,"thursday":1,"friday":1,"tuesday":1,"wednesday":1}'` |

##### 禁止上网时段设置（set_block_time）

适用于用户说「禁止 XX 点到 XX 点上网」，**自动反向转换为允许规则**（见 3.2.1 set_net_time）。

**参数：** `--forbid-start`（开始时间）、`--forbid-end`（结束时间）、`--weekdays`（weekday=工作日 / weekend=周末 / everyday=每天）

**冲突处理：** 遵循 3.2.1 核心原则——意图不明时询问用户是替换还是追加。

| 场景 | 命令 |
|------|------|
| 周一~周五 08:00~12:00 禁止上网 | `node router-skill/bin/router-claw.js set_block_time --device-id 1 --forbid-start 08:00 --forbid-end 12:00 --weekdays weekday` |
| 每天 20:00~22:00 禁止上网 | `node router-skill/bin/router-claw.js set_block_time --device-id 1 --forbid-start 20:00 --forbid-end 22:00 --weekdays everyday` |
| 周末 18:00~21:00 禁止上网 | `node router-skill/bin/router-claw.js set_block_time --device-id 1 --forbid-start 18:00 --forbid-end 21:00 --weekdays weekend` |

**常见用户意图与 action 映射**

当用户要求对已有规则执行操作时，按以下对应关系选择：

| 用户说 | action | 参数 | 说明 |
|--------|--------|------|------|
| "关闭/禁用/停用" | `newUpdate` | `enable: 0` | 暂时禁用，规则配置保留，可随时重新开启 |
| "删除/移除/去掉" | `newDelete` | 传该规则 id | 彻底移除，需重新创建才能恢复 |

⚠️ **"关闭"≠"删除"**：关闭是禁用（enable=0），删除是直接用newDelete移除规则。

#### 3.2.2 上网时长设置（set_net_duration）

**【重要】时长单位说明：**
- `timeSummary.allowed` 字段单位为**秒**，表示**每天**的允许上网时长，属于**内部请求/换算用数值**，严禁以任何形式回显给用户——包括但不限于出现“= xx秒”、“（xx秒）”等任何带“秒”的表述。展示给用户的时长一律采用“X小时X分钟”格式。
**例外**：当用户要求设置为无限制（或≥24小时）时，allowed 值使用 90000，仅代表 24 小时均可上网，该数值及原始秒数严禁以任何形式出现在面向用户的文字中，用户可见内容只允许为"无限制"。查询/设置后的内部校验结果（含 allowed 字段）仅用于自己核对，不得回显给用户。
- 示例：`allowed: 21600` = 21600秒 = 6小时/天
- 示例：`allowed: 90000` (24小时均可上网)

**【强制】秒级处理规则**：调用`set_net_duration`前解析上网时长并换算总秒数：可被 60 整除则直接处理（换算过程严禁展示给用户）；存在秒余数（含时分秒格式、总秒数无法整除 60）时，提醒用户时长最小单位为分钟，询问是否舍弃秒取整分钟；确认后下发整分钟对应秒数，禁止下发带余数秒值；
**【强制】时长与时段冲突**：如果用户要求上网时长设为无限制(>=24小时)，或允许的上网时长超过了当前上网时段范围时，必须先询问用户是否要关闭/更改上网时段，得到明确确认后才能操作，严禁自行关闭或修改；

| 场景 | 示例用法 |
|------|----------|
| 添加允许上网时长（例如：从周一到周五，每天允许上网6小时） | `node router-skill/bin/router-claw.js set_net_duration --device-id 1 --action update --data '{"daily":{"monday":21600,"tuesday":21600,"wednesday":21600,"thursday":21600,"friday":21600,"saturday":90000,"sunday":90000},"device":"1"}'` |
| 添加允许上网时长（例如：周末每天允许上网3小时） | `node router-skill/bin/router-claw.js set_net_duration --device-id 1 --action update --data '{"daily":{"monday":18000,"tuesday":18000,"wednesday":18000,"thursday":18000,"friday":18000,"saturday":10800,"sunday":10800},"device":"1"}'` |
| 删除上网时长（例如：删除周一到周五（工作日）允许上网时长的设置） | `node router-skill/bin/router-claw.js set_net_duration --device-id 1 --action update --data '{"daily":{"monday":90000,"tuesday":90000,"wednesday":90000,"thursday":90000,"friday":90000,"saturday":10800,"sunday":10800},"device":"1"}'` |
| 删除上网时长（例如：删除周末允许上网时长的设置） | `node router-skill/bin/router-claw.js set_net_duration --device-id 1 --action update --data '{"daily":{"monday":90000,"tuesday":90000,"wednesday":90000,"thursday":90000,"friday":90000,"saturday":90000,"sunday":90000},"device":"1"}'` |

#### 3.2.3 一键断网/延时断网（set_net_off）

| 场景 | 示例用法 |
|------|----------|
| 立即断网（delayEnable=1，allow=0） | `node router-skill/bin/router-claw.js set_net_off --data '{"device":"1","game":0,"video":0,"social":0,"payEnable":0,"appDownload":0,"urlEnable":0,"denyEnable":0,"delayEnable":1,"allow":0,"increaseTime":0}'` |
| 延时10分钟断网（allow单位是秒，可以根据用户指令修改实际延时断网时长） | `node router-skill/bin/router-claw.js set_net_off --data '{"device":"1","game":0,"video":0,"social":0,"payEnable":0,"appDownload":0,"urlEnable":0,"denyEnable":0,"delayEnable":1,"allow":600,"increaseTime":0}'` |
| 恢复上网（delayEnable=0） | `node router-skill/bin/router-claw.js set_net_off --data '{"device":"1","game":0,"video":0,"social":0,"payEnable":0,"appDownload":0,"urlEnable":0,"denyEnable":0,"delayEnable":0,"allow":0,"increaseTime":0}'` |

### 3.3 应用限制（禁止特定类型应用）
⚠️ **注意：没说禁游戏、社交等大类不要禁止整个类型，例如：禁止设备的QQ，不要用deny_social接口，用deny_app接口，只禁止设备的QQ用only_deny_app**
| 命令 | 功能描述 | 示例用法 |
|------|---------|----------|
| deny_games | 禁止所有游戏应用访问（包括王者荣耀、和平精英等153款游戏） | `node router-skill/bin/router-claw.js deny_games --device-id 1` |
| deny_videos | 禁止所有视频类应用访问（包括爱奇艺、腾讯视频、抖音等43款视频应用） | `node router-skill/bin/router-claw.js deny_videos --device-id 1` |
| deny_social | 禁止所有社交通讯应用访问（包括微信、QQ、知乎、微博等5款社交应用） | `node router-skill/bin/router-claw.js deny_social --device-id 1` |
| deny_shopping | 禁止所有购物支付应用访问（包括支付宝、微信支付、淘宝、京东等9款购物应用） | `node router-skill/bin/router-claw.js deny_shopping --device-id 1` |
| deny_install | 禁止所有下载安装应用（包括华为应用市场、小米应用商店等8款应用商店） | `node router-skill/bin/router-claw.js deny_install --device-id 1` |
| deny_app | 禁止某一款或多款app（没有说只禁止某款app就要把之前禁用的app加上，device填充设备id，apps填充需要禁用的appid，且每个appid加上双引号，type填充禁用app类型） | `-d '{"action":"update","device":"","apps":[]}'` |
| only_deny_app | 只禁止某一款或多款app（device填充设备id，apps填充需要禁用的appid，且每个appid加上双引号，type填充禁用app类型） | `-d '{"action":"update","device":"","apps":[]}'` |

| 场景 | 示例用法 |
|------|----------|
##### 禁用设备某款app(device填充设备id，apps填充需要禁用的appid，g_saAppInfo中第三个元素是categ，categ填充app的categ)
node router-skill/bin/router-claw.js deny_app  --data '{"device":"","apps":[],"categ":}'
##### 禁用设备多款app(先分类app类型，如果有多种类型则分不同type多次执行,device填充设备id，apps填充需要禁用的appid，且每个appid加上双引号，，g_saAppInfo中第三个元素是categ，categ填充app的categ)
node router-skill/bin/router-claw.js deny_app  --data '{"device":"","apps":[],"categ":}'
##### 只禁用设备某款或多款app(device填充设备id，apps填充需要禁用的appid，且每个appid加上双引号，g_saAppInfo中第三个元素是categ，categ填充app的categ)
node router-skill/bin/router-claw.js only_deny_app  --data '{"device":"","apps":[],"categ":}'
### 3.4 取消应用限制（恢复特定类型应用使用权限）

| 命令 | 功能描述 | 示例用法 |
|------|---------|----------|
| allow_games | 允许游戏应用访问 | `node router-skill/bin/router-claw.js allow_games --device-id 1` |
| allow_videos | 允许视频类应用访问 | `node router-skill/bin/router-claw.js allow_videos --device-id 1` |
| allow_social | 允许社交通讯应用访问 | `node router-skill/bin/router-claw.js allow_social --device-id 1` |
| allow_shopping | 允许购物支付应用访问 | `node router-skill/bin/router-claw.js allow_shopping --device-id 1` |
| allow_install | 允许下载安装应用 | `node router-skill/bin/router-claw.js allow_install --device-id 1` |

### 3.5 使用时长查询说明

通过 get_child_protect 获取各类别使用时长：
- 查询设备上网时长：`timeSummary -> used`的值为当日已使用时长，单位: 秒；`timeSummary -> timeRule`有7个数值，依次为周一到周日的上网时长限制，单位: 分钟，**例外：1500仅表示无限制，不代表时长**; `timeSummary -> allowed`的值为当日允许上网时长，单位: 秒；
- 查询设备当天玩游戏时长：`today -> time -> game` 的值代表游戏时长，单位：秒
- 查询设备看视频娱乐时长：`today -> time -> video`
- 查询设备学习时长：`today -> time -> study`
- 查询设备进行社交资讯时长：`today -> time -> social`

## 4. 操作结果验证（强制规则）

### 4.1 验证要求

操作后**必须**执行以下步骤：

1. **展示当前规则**：调用 `get_child_protect` 获取最新配置，展示时段/时长/应用限制/断网状态
2. **校验一致性**：实际规则与预期一致 → ✅ 成功；不一致 → ❌ 失败并展示实际规则
3. **跨天时段处理**：禁止时段跨天（如 21:00~次日10:00）展示为反向允许时段（10:00~21:00）

### 4.2 校验模板

**成功**：`✅ 设置成功！当前规则：[规则描述]，请确认`
**失败**：`❌ 设置失败，当前操作暂不可用。实际：[实际规则]，请稍后重试`

---

## 5. 数据显示格式

### 5.1 儿童保护信息
```json
{
  "today": {
    "totalUsedTime": 258,
    "stopEpoch": 0,
    "frame": 0,
    "appSorts": [
      {
        "appId": "00000000000000000000000000000881",
        "appName": "王者荣耀",
        "useTime": 160
      },
      {
        "appId": "00000000000000000000000000000503",
        "appName": "抖音",
        "useTime": 98
      }
    ]
  },
  "week": {
    "totalUsedTime": 1680,
    "appSorts": [
      {
        "appId": "00000000000000000000000000000881",
        "appName": "王者荣耀",
        "useTime": 160
      }
    ]
  }
}
```

### 5.2 应用分类
| 分类ID | 分类名称 | 说明 |
|--------|----------|------|
| 1 | 游戏类 | 游戏应用 |
| 2 | 视频类 | 视频播放应用 |
| 3 | 社交类 | 社交通讯应用 |
| 4 | 购物类 | 购物支付应用 |
| 5 | 学习类 | 学习相关应用 |
| 6 | 工具类 | 工具类应用 |
| 7 | 生活类 | 生活类应用 |

## 6. 注意事项

1. 设备ID必须是路由器管理的设备，需要先用路由器技能扫描设备列表
2. 设置时间限制时，注意格式为24小时制，格式为"HH:MM"
3. 应用分类限制会清空该分类下的所有应用，然后重新设置
4. 当appId找不到对应的应用名称时，直接显示appId本身
5. 所有操作都可能需要一定的生效时间，建议操作完毕后查询最新状态
6. 禁用app时如果没说只禁用，都是追加禁用app使用deny_app
7. 用户问设备的主人回家没，不要回答设备连接方式、信号强度、IP地址的信息

## 7. 强制安全规则

**【强制】删除儿童设备前必须先查最新设备映射**

在执行 `del_child_device` 删除设备前，**必须**：
1. 先调用 `get_child_protect` 获取最新的儿童保护设备列表
2. 确认每个设备的 `device` ID 和 `hostName`（设备名）的映射关系
3. **向用户展示当前列表并确认要删除的设备名称**，得到明确确认后再执行

**原因：** 添加/删除设备后，device ID 可能重新排列，凭记忆中的 ID 操作会导致**删错设备**。

示例流程：
```
1. 执行 get_child_protect → 获取最新列表 → 展示给用户
2. 用户确认要删除的设备名
3. 执行 del_child_device 传入正确的 device ID
4. 执行 get_child_protect 验证删除结果
```

⚠️ 任何时候都不能单凭用户说"移除那个设备"就执行，必须让用户说出**设备名称**。

## 8. 错误处理

如遇错误会返回以下格式：
```json
{
  "success": false,
  "data": null,
  "message": "错误描述信息"
}
```