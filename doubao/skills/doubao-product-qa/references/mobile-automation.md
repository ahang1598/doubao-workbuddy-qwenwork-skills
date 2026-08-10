# iOS 与 Android 自动化

## 目录

- [框架选择](#框架选择)
- [统一执行流程](#统一执行流程)
- [Appium](#appium)
- [iOS XCUITest](#ios-xcuitest)
- [Android Espresso 与 UI Automator](#android-espresso-与-ui-automator)
- [安装启动与状态控制](#安装启动与状态控制)
- [权限测试](#权限测试)
- [日志崩溃与证据](#日志崩溃与证据)
- [稳定性规则](#稳定性规则)

## 框架选择

零基础用户先按 `SKILL.md` 指向的 `beginner-onboarding.md` 判断其拥有 Xcode/Android 工程、`.app/.ipa/.apk`、应用名称还是在线设备。由 Agent 解释并选择 Appium/XCUITest/Espresso/UiAutomator2，不让用户先做框架决策。

| 场景 | 主框架 | 原因 |
|---|---|---|
| iOS/Android 共用黑盒业务旅程 | Appium | 共享测试模型，分别接 XCUITest/UiAutomator2 driver |
| 只有安装包、无源代码 | Appium 或 UI Automator | 可从应用进程外执行 |
| iOS 工程内 UI/性能测试 | XCUITest | Xcode 原生执行、xcresult、attachments、真机集成 |
| Android 工程内页面/组件测试 | Espresso/Compose Test | 与应用同步，速度和稳定性更好 |
| Android 系统 UI、跨 App、权限设置 | UI Automator | 可操作应用外和系统界面 |
| WebView/Hybrid | Appium + 原生/WEBVIEW context | 同时验证原生壳与 Web 内容 |

支持所有框架不等于同一流程写四遍。将高价值跨端旅程放在 Appium，将平台内部逻辑和组件同步留给原生框架，将系统交互留给 UI Automator。

## 统一执行流程

1. 运行 `detect_test_targets.py`，保存工具版本和设备清单。
2. 读取工程已有测试、bundle/package ID、scheme、Gradle variant 和启动入口。
3. 选择目标设备与测试集，生成 `08-device-matrix.json`。
4. 检查安装包：iOS `.app/.ipa`，Android `.apk`；AAB 需先通过 bundletool/CI 生成可安装 APK 集。
5. 安装或升级；记录安装前版本、目标版本和数据保留策略。
6. 设置语言、地区、时区、方向、网络和权限初始状态。
7. 启动 Appium server 或原生 runner，先执行单设备 P0 冒烟。
8. Appium 会话冒烟后必须执行至少一条包含业务结果断言的完整流程；冒烟通过后再按设备矩阵扩展。
9. 采集页面树、测试报告、平台日志和崩溃；截图按执行前向用户确认的策略采集。
10. 聚合并分类结果，恢复设备和测试数据。

## Appium

### 安装与体检

先运行 `detect_test_targets.py` 或 `npm run appium:preflight`。如果 Appium core、目标平台 driver 和 Node 依赖已满足，直接复用；不要机械要求用户重装。如果缺失，先向用户说明以下内容并获得允许：安装位置、Appium/WebdriverIO 与 driver、需要联网、预计影响目录，以及不做全局安装。

遵循项目现有 Node 版本与锁文件。发布的 starter 不包含 `node_modules`；获得允许后，把 starter 复制到测试工作目录并按锁文件安装，不要把安装结果写回 skill 资产：

先运行跨平台的 `npm ci`。然后只安装当前宿主支持的 driver。

macOS Bash/zsh：

```bash
export APPIUM_HOME="$PWD/.appium-home"
npx appium driver install xcuitest
npx appium driver install uiautomator2
npx appium driver doctor xcuitest
npx appium driver doctor uiautomator2
```

Windows PowerShell 仅安装 Android driver：

```powershell
$env:APPIUM_HOME = Join-Path $PWD ".appium-home"
npx appium driver install uiautomator2
npx appium driver doctor uiautomator2
```

Windows 本机不得尝试安装或运行 XCUITest；需要远程 Mac/Appium 或设备云。

将 `APPIUM_HOME` 固定到项目或临时目录，避免不同 Appium core/driver 版本污染用户全局环境。先运行 `npm run appium:preflight`；它会验证 core、driver、目标、安装包和 bundle/package ID。

安装后至少核对：`npm ls --depth=0` 无依赖错误、Appium 版本可读、`driver list --installed --json` 包含目标 driver、doctor 无 required fix、设备在线。`applesimutils` 等 optional fix 只有当前测试确实依赖对应扩展能力时才要求安装，不能把 optional warning 误报成阻塞。

starter 的 WebdriverIO 请求会删除显式 `Content-Length`，交给 undici 按最终 body 自动计算。这用于规避 Node 26 + WebdriverIO 9.29 在创建 session 前可能出现的 `UND_ERR_INVALID_ARG`，不改变 Appium 协议或业务断言。

starter 默认不截图。用户选择允许截图后设置 `QA_SCREENSHOT_POLICY=every-step|key|failure|off`；兼容旧入口时也可设置 `QA_CAPTURE_SCREENSHOTS=1`。无论是否截图，都保存页面树、结构化结果、runner 和平台日志。

`appium-smoke.cjs` 只验证会话、启动和页面树，不代表业务流程通过。`business-flow.cjs` 提供 `TC-MOBILE-CART-001`：商品目录 → 商品详情 → 加入购物车 → 购物车断言。`fallline-analysis-flow.cjs` 是用真实 FallLine iOS App 建立的 `TC-IOS-FALLLINE-001` canary：照片选择 → 视频确认 → 分析 → 报告断言 → 历史重开；它区分 `product_failure` 与 `infra_error`，并允许系统照片选择器使用受记录的坐标兜底，但应用内业务控件不得依赖坐标。

使用 `run-with-appium.cjs` 启动隔离的 Appium server、等待 `/status`、运行用例并回收 server：

macOS Bash/zsh 的 iOS 示例：

```bash
export APPIUM_HOME="$PWD/.appium-home"
export QA_PLATFORM=ios
export QA_TARGET_ID=<simulator-udid>
export QA_APP_PATH=<absolute-app-path>
export QA_APP_ID=<bundle-id>
export QA_SCREENSHOT_POLICY=every-step
npm run appium:preflight
npm run appium:run -- fallline-analysis-flow.cjs
```

Windows PowerShell 的 Android 示例：

```powershell
$env:APPIUM_HOME = Join-Path $PWD ".appium-home"
$env:QA_PLATFORM = "android"
$env:QA_TARGET_ID = "emulator-5554"
$env:QA_APP_PATH = "C:\qa\builds\app-debug.apk"
$env:QA_APP_ID = "com.example.app"
$env:QA_SCREENSHOT_POLICY = "failure"
npm run appium:preflight
npm run appium:run -- business-flow.cjs
```

真实文件必须替换尖括号值。Android 使用 UiAutomator2，iOS 使用 XCUITest driver；同一业务规则共享 case ID，执行结果按平台分开。

原生实例位于 `assets/mobile-examples/`：Android Espresso 与 iOS XCUITest 使用同一 case ID。它们用于展示完整业务层写法；迁移到产品工程时替换定位符和数据，不复制三套相同用例长期维护。

Appium 2/3 的 driver 与 core 分开管理；不要因为 `appium --version` 成功就假定 driver 已安装。iOS XCUITest driver 只能在 macOS host 上工作，真机还需要信任、Developer Mode、UI Automation 和有效 WDA 签名。

### Capabilities 基线

iOS：

```json
{
  "platformName": "iOS",
  "appium:automationName": "XCUITest",
  "appium:udid": "由设备检测结果提供",
  "appium:bundleId": "由被测工程提供",
  "appium:noReset": false,
  "appium:newCommandTimeout": 120
}
```

Android：

```json
{
  "platformName": "Android",
  "appium:automationName": "UiAutomator2",
  "appium:udid": "由 adb devices 提供",
  "appium:appPackage": "由被测应用提供",
  "appium:appActivity": "由被测应用提供",
  "appium:noReset": false,
  "appium:newCommandTimeout": 120
}
```

真实文件中不能保留示例值。优先显式 `udid`，避免多设备时被 Appium 自动选错。

### 用例规则

- 以 accessibility identifier/content-desc/resource-id 为稳定定位；文本定位仅用于稳定用户文案。
- iOS 要求开发设置 `accessibilityIdentifier`；Android 要求稳定 resource ID 或 content description。
- 使用业务条件等待，不使用固定 sleep。
- 每个测试独立创建或恢复数据；跨端共享用例 ID，但使用平台 page/screen object 隔离定位器。
- 需要验证权限流程时关闭 `autoGrantPermissions/autoAcceptAlerts`；只在权限不属于测试目标的套件中使用自动处理。
- Hybrid App 明确切换 NATIVE_APP/WEBVIEW context，并验证返回原生后的状态。
- 一次性 UI 冒烟/快速确认可在用户允许后先使用能读取控件语义或可访问性树的 GUI 能力，随后用安装、启动、日志和崩溃结果交叉验证，并标记 `exploratory`。发布回归仍先使用 Appium/XCUITest/UiAutomator2/Espresso。
- AppleScript、CGEvent、图像定位或坐标点击只用于语义元素不可用时的临时取证，不能替代可重复的发布回归。系统选择器无法稳定暴露元素时允许坐标兜底，但必须写入 actions/result 并列为可测性风险。

## iOS XCUITest

### 工程要求

- macOS、兼容的 Xcode、可构建的 scheme 和 UI Test target；
- Simulator 或已信任并开启 Developer Mode/UI Automation 的真机；
- 真机签名、开发团队和 provisioning profile 可用；
- 测试产物写到唯一 result bundle。

执行示例：

```bash
xcodebuild test \
  -workspace App.xcworkspace \
  -scheme AppUITests \
  -destination 'platform=iOS Simulator,id=<UDID>' \
  -resultBundlePath qa-results/run/ios-<UDID>.xcresult
```

生成命令时从工程读取真实 workspace/project、scheme 和 UDID，不保留尖括号内容。

### 测试结构

```swift
import XCTest

final class LoginUITests: XCTestCase {
    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    func test_TC_LOGIN_001_validUserCanSignIn() throws {
        let app = XCUIApplication()
        app.launchArguments = ["-uiTesting", "-resetState"]
        app.launch()

        app.textFields["login.email"].tap()
        app.textFields["login.email"].typeText("qa@example.test")
        app.secureTextFields["login.password"].tap()
        app.secureTextFields["login.password"].typeText("TestPassword123!")
        app.buttons["login.submit"].tap()

        XCTAssertTrue(app.staticTexts["home.title"].waitForExistence(timeout: 10))
        XCTContext.runActivity(named: "登录成功截图") { activity in
            activity.add(XCTAttachment(screenshot: app.screenshot()))
        }
    }
}
```

敏感凭证通过测试配置注入，不提交真实账号。失败时保留 xcresult；使用 `xcresulttool` 或 Xcode 提取 failure、attachment、duration 和 destination。

## Android Espresso 与 UI Automator

### Espresso/Compose

放在 `src/androidTest/`，通过 `AndroidJUnitRunner` 在目标设备执行。Espresso 适用于了解源码并可注入稳定测试数据的应用内 UI；异步任务必须注册 IdlingResource 或使用应用可观察状态。

```kotlin
@RunWith(AndroidJUnit4::class)
class LoginTest {
    @Test
    fun tcLogin001_validUserCanSignIn() {
        onView(withId(R.id.email)).perform(typeText("qa@example.test"))
        onView(withId(R.id.password)).perform(typeText("TestPassword123!"))
        onView(withId(R.id.submit)).perform(click())
        onView(withId(R.id.home_title)).check(matches(isDisplayed()))
    }
}
```

执行示例：

```bash
./gradlew connectedDebugAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.class=com.example.LoginTest
```

### UI Automator

用于系统权限、通知栏、设置页、跨 App、release 包黑盒和 Appium UiAutomator2 无法稳定覆盖的系统场景。优先使用 resource name、text/content description 组合与内置条件等待；避免坐标点击。

### Espresso Driver

Appium Espresso driver 适合需要 WebDriver 接口但希望利用 Espresso 同步能力的 Android 流程。它需要与被测应用构建/签名兼容，准备成本高于 UiAutomator2；默认跨端黑盒回归仍使用 UiAutomator2，只有同步或 WebView 问题明确时切换。

## 安装启动与状态控制

Android：

```bash
adb -s "$SERIAL" install -r -g app.apk
adb -s "$SERIAL" shell am force-stop com.example.app
adb -s "$SERIAL" shell monkey -p com.example.app 1
adb -s "$SERIAL" shell pm clear com.example.app
adb -s "$SERIAL" uninstall com.example.app
```

iOS Simulator：

```bash
xcrun simctl install "$UDID" App.app
xcrun simctl launch "$UDID" com.example.app
xcrun simctl terminate "$UDID" com.example.app
xcrun simctl uninstall "$UDID" com.example.app
```

iOS 真机优先由 Xcode/XCUITest/Appium 管理安装和启动；可用 `xcrun devicectl` 时先读取本机 help，再生成与本机 Xcode 匹配的命令。安装/清数据/卸载必须符合本轮的升级测试策略，不能无条件重置。

## 权限测试

Android 可使用 `pm grant/revoke` 或 UI Automator 操作系统弹窗。覆盖首次询问、拒绝、拒绝且不再询问、设置页开启、运行中撤权和升级后的保留行为。

iOS Simulator 可使用：

```bash
xcrun simctl privacy "$UDID" grant camera com.example.app
xcrun simctl privacy "$UDID" revoke camera com.example.app
xcrun simctl privacy "$UDID" reset all com.example.app
```

iOS 真机权限通过 XCUITest/Appium 操作 SpringBoard 弹窗或预置设备状态；每种权限的系统行为随 OS 变化，矩阵中保留真实系统版本。

## 日志崩溃与证据

- Appium/WebdriverIO：保存 page source、capabilities、server log 和测试 runner 报告；失败 screenshot 仅在用户选择允许时保存。
- XCUITest：保存 `.xcresult`、XCTAttachment、测试日志和 destination。
- Android：保存 `logcat -b crash`、相关 logcat、设备属性、instrumentation XML/HTML，并按用户策略保存 screenshot。
- iOS Simulator：保存选定进程的 unified log并按用户策略保存 screenshot；真机保存 xcresult/WDA/Appium 日志和可获取的 crash/diagnostic。
- 所有证据记录 case ID、构建、目标、时间、账号角色和数据标识，并脱敏 token、cookie、手机号和邮箱。

`collect_mobile_evidence.py` 可直接采集 Android 与 iOS Simulator。真机 iOS 的日志接口随 Xcode/设备版本变化，优先使用当前 XCUITest/Appium 运行产生的稳定产物，不用未经验证的私有命令。

## 稳定性规则

- 设备先健康检查：在线、已解锁、磁盘充足、无系统更新弹窗、时间同步。
- 禁止测试间共享可变账号/订单/库存；并行目标使用唯一数据命名空间。
- 首次失败原目标重跑一次只用于判定稳定性，不能用重试把 flaky 算通过。
- 记录首跑和重跑结果；flaky 是缺陷/基础设施问题，不是通过。
- Appium server、WDA、adb 和开发者工具端口按 worker 隔离。
- 失败超过环境阈值时暂停矩阵，先修设备实验室，避免产生大量无意义失败。
