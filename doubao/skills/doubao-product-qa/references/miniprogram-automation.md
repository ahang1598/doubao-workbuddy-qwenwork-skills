# 微信小程序自动化

## 目录

- [能力边界](#能力边界)
- [环境准备](#环境准备)
- [执行流程](#执行流程)
- [测试编写](#测试编写)
- [宿主能力与真机](#宿主能力与真机)
- [证据与稳定性](#证据与稳定性)

## 能力边界

零基础用户优先走工程目录模式：只要求其提供包含 `project.config.json` 的文件夹，其余 CLI、依赖和路由由 Agent 检测。不要直接要求初学者理解或配置 `wsEndpoint`；只有团队已提供自动化服务时才使用 endpoint 模式。

`miniprogram-automator` 通过微信开发者工具控制小程序，适合页面导航、元素操作、数据/属性检查、截图和常规回归。支付、订阅消息、扫码、相机、定位、蓝牙、客服、分享链路、系统授权以及微信版本差异必须在真实微信环境补测。

开发者工具通过不等于 iOS/Android 微信真机通过。报告分别统计：`开发者工具自动化`、`iOS 微信真机`、`Android 微信真机`。

正式自动化入口只有两类：

- `launch({ cliPath, projectPath })`：需要本地小程序工程与微信开发者工具 CLI；
- `connect({ wsEndpoint })`：需要环境预先提供并授权的 automator WebSocket endpoint。

只有已上线小程序名称、桌面微信登录态或搜索入口，不足以执行 `miniprogram-automator`。此时应请求工程目录或 endpoint；拿不到时输出自动化 blocker 和人工验收清单。不要默认使用 Computer Use、AppleScript 或坐标点击桌面微信，因为这些能力不是跨 Agent 标准依赖，也不能产生可重复的小程序自动化结论。

二维码、分享卡片和 AppID 仅用于身份确认，不等于 automator endpoint，也不能解除自动化 blocker。初学者不知道工程目录时，先让其联系开发人员提供小程序工程压缩包，并说明压缩包中应包含 `project.config.json`；不要把技术连接参数作为第一个问题。

## 环境准备

需要：

- Node.js 与项目锁文件兼容；
- 微信开发者工具及 CLI；
- 小程序工程目录，包含 `project.config.json` 或 `app.json`；
- 开发者工具“安全设置”允许 CLI/服务端口；
- `miniprogram-automator` 和项目测试 runner（可使用 Jest，也可直接 Node 执行）；
- 需要登录/开放能力时使用专用测试账号与体验版配置。

安装：

```bash
npm install --save-dev miniprogram-automator
```

不要把 AppSecret、登录 code、session key 或生产凭证写进用例、截图或日志。

## 执行流程

1. 先判定输入形态：工程目录、automator endpoint，或只有线上名称。只有线上名称时停止自动化并请求缺失入口。
2. 检测开发者工具 CLI、项目配置和依赖。
3. 读取 `app.json`、页面路由、分包、环境配置和已有测试。
4. 使用 `launch({ cliPath, projectPath })` 启动独立会话；已有自动化端口时可 `connect({ wsEndpoint })`。
5. `reLaunch` 到每个场景的初始页面，准备独立数据。
6. 使用元素 selector 执行 tap/input/trigger，使用 text/attribute/property/data/WXML 做明确断言。
7. 对导航、页面栈、返回、刷新、缓存、分包加载和错误态做检查。
8. 每个失败保存页面路由、WXML/关键 data、console 和 mock/网络信息；截图按执行前向用户确认的策略保存。
9. 关闭会话并恢复 mock、缓存和测试数据。

### 只有线上小程序时的阻塞输出

至少写明：

- 已知信息：小程序名称、目标流程、线上/体验版；
- 缺失入口：`MINIPROGRAM_PROJECT_PATH` 或已授权 `MINIPROGRAM_WS_ENDPOINT`；
- 为什么桌面微信不能替代：无法稳定读取 WXML/data/route/console，不能跨 Agent 复现；
- 可继续的最小输入：工程目录、开发者工具 CLI，或 CI/设备云提供的标准自动化连接；
- 人工清单：仅作为待执行项，不能标记通过。

## 测试编写

可复制 `assets/mobile-starter/miniprogram-smoke.cjs` 作为连接冒烟。业务测试应使用真实路由和稳定 selector：

starter 支持两种互斥入口：设置 `WECHAT_CLI_PATH + MINIPROGRAM_PROJECT_PATH` 使用 `launch`，或设置 `MINIPROGRAM_WS_ENDPOINT` 使用 `connect`；两者都必须设置 `MINIPROGRAM_PAGE`。不要从桌面微信窗口或小程序名称推断 endpoint。

starter 默认不截图。用户选择允许截图后设置 `QA_CAPTURE_SCREENSHOTS=1`。

```js
const assert = require('node:assert/strict')
const automator = require('miniprogram-automator')

describe('优惠券领取', () => {
  let miniProgram

  beforeAll(async () => {
    miniProgram = await automator.launch({
      cliPath: process.env.WECHAT_CLI_PATH,
      projectPath: process.env.MINIPROGRAM_PROJECT_PATH,
    })
  }, 60000)

  afterAll(async () => {
    if (miniProgram) await miniProgram.close()
  })

  test('TC-COUPON-001 符合资格用户可领取', async () => {
    const page = await miniProgram.reLaunch('/pages/coupon/index')
    const claim = await page.$('[data-testid="claim-button"]')
    assert.ok(claim, '领取按钮应存在')
    await claim.tap()
    const result = await page.$('[data-testid="claim-result"]')
    assert.equal(await result.text(), '领取成功')
  })
})
```

小程序项目没有 test id 时，与开发协作增加稳定 `data-*`/class 标识。避免依赖生成 class、元素下标或坐标。

等待应针对 selector、路由或 data 条件。固定 `waitFor(ms)` 只用于开发者工具没有可观察条件的最后手段，并记录原因。

## 宿主能力与真机

以下场景至少在 iOS 和 Android 各一个代表版本的真实微信验证：

- 微信登录、手机号、隐私授权；
- 支付成功/取消/失败/重复回调；
- 订阅消息与系统通知；
- 分享、扫码、场景值和从聊天/二维码冷启动；
- 相机、相册、位置、蓝牙、文件；
- 客服、地图、视频号或其他宿主跳转；
- 网络切换、前后台、锁屏、微信进程被杀；
- 基础库、微信版本和系统版本差异。

若 `miniprogram-automator` 的 remote 能力和实验室环境可稳定控制真机，可自动执行其中可支持部分；仍需保留设备、微信版本和宿主弹窗证据。无法自动控制的场景生成真机清单并标记未执行/人工执行。

## 证据与稳定性

- 每个 case 创建 `evidence/miniprogram/<case-id>/<target>/`。
- 保存 route/page stack、关键 WXML/data、console、开发者工具版本和基础库版本；按用户策略保存 screenshot。
- mock 必须按用例隔离并在结束时恢复；报告区分真实接口和 mock 结果。
- 开发者工具升级后先跑连接冒烟与 P0，发现 SDK/工具不兼容时固定已验证版本并记录。
- 自动化端口和项目目录不能被多个 worker 共享；按 worker 分配端口或串行运行。
- 失败时先区分业务错误、selector 漂移、开发者工具连接、基础库差异和测试数据问题。
