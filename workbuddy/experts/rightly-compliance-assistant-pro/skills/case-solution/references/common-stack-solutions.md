# 常见合规违规堆栈问题解法汇总

## 问题索引

| 问题类型 | 常见表现 | 推荐方案 |
|---------|---------|---------|
| 后台监听安装卸载 | BroadcastReceiver + PACKAGE_ADDED/REMOVED | 删除/广播管控 |
| 后台上传设备信息 | 后台线程 + HTTP请求 + MAC/IMEI等字段 | 删除/API兜底 |
| 过度定位 | 非定位场景调LocationManager | 删除/分模块授权 |
| 隐私同意前API调用 | Application.onCreate中调敏感API | ruleBeforeStrategy |
| 读取已安装应用 | PackageManager.getInstalledPackages | 删除/分模块授权 |
| 读取运行进程 | ActivityManager.getRunningAppProcesses | ruleBeforeStrategy |
| 读取剪贴板 | ClipboardManager.getPrimaryClip | 删除/提示用户 |
| SDK采集设备标识 | TelephonyManager.getDeviceId等 | SDK升级/API兜底/定向插桩 |
| 非影音文件访问 | File API读取SD卡非媒体文件 | 删除/MediaStore替代 |
| 后台截图监控 | FileObserver监听截图目录 | 删除/Rightly兜底 |
| 蓝牙扫描 | BluetoothAdapter.startDiscovery | 删除启动时扫描 |
| SIM状态读取 | TelephonyManager.getSimState | ruleBeforeStrategy |

---

## 详细解决方案

### 1. 后台监听安装卸载

**典型堆栈**：
```
at com.xxx.sdk.InstallReceiver.onReceive(InstallReceiver.java:XX)
at android.app.ActivityThread.handleReceiver(ActivityThread.java:XX)
// BroadcastReceiver注册了 PACKAGE_ADDED / PACKAGE_REMOVED
```

**方案A（推荐）**：删除监听代码
```java
// 在AndroidManifest中移除receiver声明
// 或在代码中取消注册
unregisterReceiver(installReceiver);
```

**方案B**：Rightly广播管控
- 接入指引：docs.bugly.woa.com/rightly/dynamic/docs/Android/installMonitor
- 自动禁止后台监听安装/卸载广播

**方案C**：业务自建 - APP切后台时取消监听
```java
@Override
protected void onStop() {
    super.onStop();
    unregisterReceiver(installReceiver);
}
```

---

### 2. 隐私同意前调用敏感API

**典型堆栈**：
```
at android.app.ActivityManager.getRunningAppProcesses(ActivityManager.java:XX)
at com.xxx.sdk.DeviceUtils.getProcessName(DeviceUtils.java:XX)
at com.xxx.sdk.SdkInit.init(SdkInit.java:XX)
at com.xxx.app.MainApplication.onCreate(MainApplication.java:XX)
```

**方案**：PMonitor配置隐私同意前禁用
```java
// 在Application.onCreate中，隐私同意前配置
PMonitor.getConfig()
    .updateRuleForAPI(
        ConstantModel.InstalledAppList.NAME,
        ConstantModel.InstalledAppList.GET_RUNNING_APP_PROCESS)
    .rule(GeneralRule.BACK_NORMAL_AND_FRONT_NORMAL)
    .ruleBeforeStrategy(RuleConstant.STRATEGY_BAN)
    .submitRule();

PMonitor.getConfig()
    .updateRuleForAPI(
        ConstantModel.InstalledAppList.NAME,
        ConstantModel.InstalledAppList.GET_RUNNING_TASKS)
    .rule(GeneralRule.BACK_NORMAL_AND_FRONT_NORMAL)
    .ruleBeforeStrategy(RuleConstant.STRATEGY_BAN)
    .submitRule();

PMonitor.getConfig()
    .updateRuleForAPI(
        ConstantModel.Network.NAME,
        Network.GET_ACTIVE_NET_INFO)
    .rule(GeneralRule.BACK_NORMAL_AND_FRONT_NORMAL)
    .ruleBeforeStrategy(RuleConstant.STRATEGY_BAN)
    .submitRule();
```

---

### 3. SDK过度采集设备标识

**典型堆栈**：
```
at android.telephony.TelephonyManager.getDeviceId(TelephonyManager.java:XX)
at com.thirdparty.sdk.DeviceInfo.collect(DeviceInfo.java:XX)
```

**方案A**：联系SDK提供方移除非必要采集，升级SDK版本

**方案B**：Rightly API兜底
- 配置设备标识相关API返回空值
- 指引：docs.bugly.woa.com/rightly/dynamic/docs/Android/api

**方案C**：Rightly定向插桩
- 移除SDK中特定的敏感字段采集代码
- 指引：docs.bugly.woa.com/rightly/dynamic/docs/Android/stub

---

### 4. 过度定位（非必要场景）

**典型堆栈**：
```
at android.location.LocationManager.getLastKnownLocation(LocationManager.java:XX)
at com.xxx.ad.LocationHelper.getLocation(LocationHelper.java:XX)
```

**方案A**：删除非必要的定位调用

**方案B**：Rightly分模块授权
```
// 只在用户授权的模块中允许定位
// 其他模块自动禁止定位API调用
```

**方案C**：Rightly全局兜底禁止后台定位

---

### 5. 读取已安装应用列表

**典型堆栈**：
```
at android.app.ApplicationPackageManager.getInstalledPackages(ApplicationPackageManager.java:XX)
at com.xxx.sdk.AppListCollector.collect(AppListCollector.java:XX)
```

**方案A**：删除非必要的应用列表读取

**方案B**：分模块授权，在未授权模块禁用

**方案C**：API兜底返回空列表

---

### 6. 非影音文件过度访问

**典型堆栈**：
```
at java.io.File.listFiles(File.java:XX)
at com.xxx.sdk.FileScanner.scan(FileScanner.java:XX)
// 访问路径: /sdcard/Download/ 或 /sdcard/DCIM/ 等非私有目录
```

**方案A**：移除非必要文件访问

**方案B（Android 10+）**：使用MediaStore API替代
```java
// 使用MediaStore查询媒体文件，无需存储权限
ContentResolver resolver = context.getContentResolver();
Cursor cursor = resolver.query(
    MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
    projection, selection, selectionArgs, sortOrder);
```

**方案C**：限制存储权限仅Android 9及以下
```xml
<!-- AndroidManifest.xml -->
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"
    android:maxSdkVersion="28" />
```

---

### 7. 存储权限优化

**权限声明限制示例**：
```xml
<!-- 限制存储权限在Android 9及以下使用 -->
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"
    android:maxSdkVersion="28" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"
    android:maxSdkVersion="28" />
```

---

## 排查工具速查

| 工具 | 用途 | 使用指引 |
|------|------|---------|
| Rightly静态扫描 | 分SDK查看敏感API调用 | 静态扫描API调用分析指引 |
| Rightly动态监控 | 运行时API调用监控 | 动态监控API调用分析指引 |
| Rightly网络传输监控 | 监控后台数据上传 | docs.bugly.woa.com/.../networkCapture |
| JADX-GUI | 反编译代码分析 | 根据域名搜索代码 |
| PMonitor看板 | 可视化API调用统计 | PMonitor文档 |
| ComplianceCanary | 调试期敏感访问可视化 | 仅debug构建 |
