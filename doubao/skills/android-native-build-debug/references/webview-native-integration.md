# WebView 壳集成相机/相册清单（Android 原生）

适用：H5 页面（如工单/订单详情 PHP 页）里的 `<input type="file">` 在套壳 APP 里需要调起系统相机/图库。
判定前置：同一 H5 在手机浏览器里能正常弹选择器 → 问题在原生壳，只改 Android 端，不动 H5/PHP。

## 0. 动代码前必须确认

- `MainActivity` 是 `.kt` 还是 `.java`：Java 代码粘进 Kotlin 文件必挂，语法不通用。
- 包名三处同步：源码第 1 行 `package`、`build.gradle(.kts)` 的 `namespace` 与 `applicationId`。
  `applicationId` 决定安装身份（覆盖安装、FileProvider authorities 都以它为准），可与 `namespace` 不同。
- `build.gradle` 是 Groovy 还是 Kotlin DSL（`.kts`），两种语法的依赖/配置写法不同，照抄会 sync 失败。

## 1. `app/src/main/AndroidManifest.xml`

```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-feature android:name="android.hardware.camera" android:required="false" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
<!-- Android 13（API 33）起读相册用这条，READ_EXTERNAL_STORAGE 不再够 -->
<uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
```

`<application>` 内（明文 http 地址必需，内网穿透如 cpolar 常见）：

```xml
android:usesCleartextTraffic="true"
```

FileProvider（Android 7.0 / API 24 起拍照必须，直接 `Uri.fromFile()` 会抛 `FileUriExposedException`）：

```xml
<provider
    android:name="androidx.core.content.FileProvider"
    android:authorities="${applicationId}.fileprovider"
    android:exported="false"
    android:grantUriPermissions="true">
    <meta-data
        android:name="android.support.FILE_PROVIDER_PATHS"
        android:resource="@xml/file_paths" />
</provider>
```

## 2. 新建 `app/src/main/res/xml/file_paths.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<paths>
    <external-files-path name="pictures" path="Pictures/" />
    <external-path name="external" path="." />
    <cache-path name="cache" path="." />
    <files-path name="files" path="." />
</paths>
```

Manifest 引用了 `@xml/file_paths` 但文件不存在会在运行时崩；`res/xml/` 目录不存在就先建。

## 3. `MainActivity` 的 WebView 配置要点

- 关键回调：`webView.setWebChromeClient(new WebChromeClient() { onShowFileChooser(...) })`。
  H5 的 `<input type="file">` 在壳里走的就是这个回调；只设 `WebViewClient` 不弹选择器。
- 成员约定：`ValueCallback<Uri[]> mFilePathCallback`、常量 `FILE_CHOOSER_REQUEST_CODE`、
  `onActivityResult` 里回传结果后必须把 `mFilePathCallback` 置回 `null`，否则第二次点击无响应。
- 拍照 Uri 必须经 `FileProvider.getUriForFile(this, getPackageName() + ".fileprovider", photoFile)`
  生成——authorities 串与 Manifest 里的 `${applicationId}.fileprovider` 逐字一致，否则一拍照就崩。
- 运行时权限：相机走 `ActivityCompat.requestPermissions`，首次使用需用户同意。
- 自定义 JS 桥：`webView.addJavascriptInterface(new JsInterface(), "AndroidBridge")`，
  暴露方法必须带 `@JavascriptInterface` 注解，否则 H5 调不到。

## 4. 打包与覆盖安装规则

- `versionCode` 必须严格大于已装版本（例：1 → 2），`versionName` 顺手递增（"1.0" → "1.1"）；否则覆盖安装失败。
- 签名文件必须与上一版完全一致；换签名 = 覆盖安装失败。华为手机"风险拦截/报毒"用正式签名或应用市场白名单解决。
- 顺序：先 `gradlew assembleDebug` 出 debug 包（不需要签名）验证功能，再打正式签名包。
- 改了 H5 但壳里看不到变化：给入口 script 加版本参数破缓存（如 `main.js?v=5` → `?v=8`）。

## 5. 替换代码交付时的标注

给用户"完整替换代码"时附一张改动对照表，至少列出：包名位置（源码第 1 行 + gradle）、
H5 地址常量（如 `HOME_URL`）、版本号位置（`versionCode`/`versionName`）、APP 名称（Manifest `android:label`）。
