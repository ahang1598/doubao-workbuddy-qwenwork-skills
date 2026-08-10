# 真实移动端业务流实例

实例目标为 Sauce Labs 开源 My Demo App：

- Android：https://github.com/saucelabs/my-demo-app-android
- iOS：https://github.com/saucelabs/my-demo-app-ios

两端都执行 `TC-MOBILE-CART-001`：打开商品目录 → 选择 Sauce Labs Backpack → 加入购物车 → 打开购物车 → 断言商品存在。

文件用途：

- `android/DashboardToCartTest.java`：复制到 Android 工程对应 `androidTest` package，运行 `./gradlew connectedAndroidTest`。
- `ios/ProductToCartUITests.swift`：加入 iOS 工程 UI Test target，通过 Xcode 或 `xcodebuild test` 运行。
- 跨端 Appium 版本位于 `assets/mobile-starter/business-flow.cjs`。

这些实例的定位符取自两个官方示例工程；迁移到真实产品时必须替换为产品自身 accessibility ID/resource ID，并保留同一用例 ID。默认不截图。
