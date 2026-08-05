# API与模块详细映射表

> 本文件包含具体API级别的映射信息。更完整的基于PandoraEx ConstantModel的映射请参阅 violation-mapping/references/api-module-mapping.md。

## 设备信息类模块 (DeviceInfoMonitor)

| API | 获取的信息 | 风险等级 | 是否需要权限 |
|-----|----------|---------|------------|
| `TelephonyManager.getDeviceId()` | IMEI | 高 | READ_PHONE_STATE |
| `TelephonyManager.getImei()` | IMEI (API 26+) | 高 | READ_PHONE_STATE |
| `TelephonyManager.getMeid()` | MEID | 高 | READ_PHONE_STATE |
| `TelephonyManager.getSubscriberId()` | IMSI | 高 | READ_PHONE_STATE |
| `TelephonyManager.getSimSerialNumber()` | SIM序列号(ICCID) | 高 | READ_PHONE_STATE |
| `TelephonyManager.getLine1Number()` | 本机号码 | 高 | READ_PHONE_STATE |
| `TelephonyManager.getSimState()` | SIM状态 | 中 | 无 |
| `TelephonyManager.getNetworkOperator()` | 运营商代码 | 低 | 无 |
| `TelephonyManager.getNetworkOperatorName()` | 运营商名称 | 低 | 无 |
| `WifiInfo.getMacAddress()` | WiFi MAC地址 | 高 | ACCESS_WIFI_STATE |
| `NetworkInterface.getHardwareAddress()` | 网卡MAC地址 | 高 | 无 |
| `BluetoothAdapter.getAddress()` | 蓝牙MAC地址 | 高 | BLUETOOTH |
| `Settings.Secure.getString(ANDROID_ID)` | Android ID | 中 | 无 |
| `Build.SERIAL` | 设备序列号 | 高 | READ_PHONE_STATE (API 29+) |
| `Build.getSerial()` | 设备序列号 | 高 | READ_PHONE_STATE |

## 定位类模块 (LocationMonitor)

| API | 获取的信息 | 风险等级 | 是否需要权限 |
|-----|----------|---------|------------|
| `LocationManager.getLastKnownLocation()` | 最后已知位置 | 高 | ACCESS_FINE/COARSE_LOCATION |
| `LocationManager.requestLocationUpdates()` | 持续定位 | 高 | ACCESS_FINE/COARSE_LOCATION |
| `LocationManager.requestSingleUpdate()` | 单次定位 | 高 | ACCESS_FINE/COARSE_LOCATION |
| `FusedLocationProviderClient.getLastLocation()` | 融合定位 | 高 | ACCESS_FINE/COARSE_LOCATION |
| `WifiManager.getScanResults()` | WiFi列表(间接定位) | 中 | ACCESS_FINE_LOCATION |
| `WifiInfo.getSSID()` | 当前WiFi名称 | 中 | ACCESS_FINE_LOCATION |
| `WifiInfo.getBSSID()` | 当前WiFi BSSID | 中 | ACCESS_FINE_LOCATION |
| `TelephonyManager.getCellLocation()` | 基站位置 | 高 | ACCESS_FINE_LOCATION |
| `TelephonyManager.getAllCellInfo()` | 全部基站信息 | 高 | ACCESS_FINE_LOCATION |

## 通讯录类模块 (ContactsMonitor)

| API | 获取的信息 | 风险等级 | 是否需要权限 |
|-----|----------|---------|------------|
| `ContentResolver.query(ContactsContract.*)` | 联系人信息 | 高 | READ_CONTACTS |
| `ContentResolver.insert(ContactsContract.*)` | 写入联系人 | 高 | WRITE_CONTACTS |
| `Cursor operations on Contacts URI` | 联系人数据操作 | 高 | READ_CONTACTS |

## 剪贴板类模块 (ClipboardMonitor)

| API | 获取的信息 | 风险等级 | 是否需要权限 |
|-----|----------|---------|------------|
| `ClipboardManager.getPrimaryClip()` | 剪贴板内容 | 中 | 无 |
| `ClipboardManager.getText()` | 剪贴板文本 | 中 | 无 |
| `ClipboardManager.hasPrimaryClip()` | 是否有剪贴板内容 | 低 | 无 |

## 传感器类模块 (SensorMonitor / CameraMonitor / AudioMonitor)

| API | 获取的信息 | 风险等级 | 是否需要权限 |
|-----|----------|---------|------------|
| `Camera.open()` | 打开相机 | 高 | CAMERA |
| `CameraManager.openCamera()` | 打开相机(API 21+) | 高 | CAMERA |
| `MediaRecorder.start()` | 开始录音/录像 | 高 | RECORD_AUDIO/CAMERA |
| `AudioRecord(...)` | 音频录制 | 高 | RECORD_AUDIO |
| `SensorManager.registerListener()` | 注册传感器 | 中 | 无(部分需BODY_SENSORS) |

## 应用列表类模块 (InstalledAppListMonitor)

| API | 获取的信息 | 风险等级 | 是否需要权限 |
|-----|----------|---------|------------|
| `PackageManager.getInstalledPackages()` | 已安装应用列表 | 高 | 无(API 30+受限) |
| `PackageManager.getInstalledApplications()` | 已安装应用信息 | 高 | 无(API 30+受限) |
| `PackageManager.queryIntentActivities()` | 查询可响应的Activity | 中 | 无(API 30+受限) |
| `ActivityManager.getRunningAppProcesses()` | 运行中的进程 | 中 | 无 |
| `ActivityManager.getRunningTasks()` | 运行中的任务 | 中 | 无(已废弃) |
| `ActivityManager.getRunningServices()` | 运行中的服务 | 中 | 无 |

## 网络类模块 (NetworkMonitor)

| API | 获取的信息 | 风险等级 | 是否需要权限 |
|-----|----------|---------|------------|
| `ConnectivityManager.getActiveNetworkInfo()` | 当前网络信息 | 低 | ACCESS_NETWORK_STATE |
| `ConnectivityManager.getAllNetworkInfo()` | 全部网络信息 | 低 | ACCESS_NETWORK_STATE |
| `WifiManager.getConnectionInfo()` | WiFi连接信息 | 中 | ACCESS_WIFI_STATE |
| `WifiManager.getDhcpInfo()` | DHCP信息 | 低 | ACCESS_WIFI_STATE |
| `NetworkInterface.getNetworkInterfaces()` | 网络接口信息 | 中 | 无 |

## 短信/通话记录类模块 (SmsMonitor / TelephonyMonitor)

| API | 获取的信息 | 风险等级 | 是否需要权限 |
|-----|----------|---------|------------|
| `ContentResolver.query(Sms.CONTENT_URI)` | 短信内容 | 高 | READ_SMS |
| `SmsManager.sendTextMessage()` | 发送短信 | 高 | SEND_SMS |
| `ContentResolver.query(CallLog.*)` | 通话记录 | 高 | READ_CALL_LOG |

## 蓝牙类模块 (BluetoothMonitor)

| API | 获取的信息 | 风险等级 | 是否需要权限 |
|-----|----------|---------|------------|
| `BluetoothAdapter.startDiscovery()` | 扫描蓝牙设备 | 中 | BLUETOOTH_SCAN(API 31+) |
| `BluetoothAdapter.getBondedDevices()` | 已配对设备 | 中 | BLUETOOTH |
| `BluetoothAdapter.getName()` | 蓝牙名称 | 低 | BLUETOOTH |
| `BluetoothAdapter.getAddress()` | 蓝牙MAC | 高 | BLUETOOTH |

## 存储访问类模块 (MediaMonitor)

| API | 获取的信息 | 风险等级 | 是否需要权限 |
|-----|----------|---------|------------|
| `File.listFiles()` | 文件列表 | 中 | READ_EXTERNAL_STORAGE |
| `File.exists()` | 文件存在检查 | 低 | 视路径而定 |
| `FileInputStream(...)` | 读取文件 | 中 | READ_EXTERNAL_STORAGE |
| `ContentResolver.query(MediaStore.*)` | 媒体文件查询 | 中 | READ_EXTERNAL_STORAGE/READ_MEDIA_* |

## 反射调用类模块 (ReflectMonitor)

| API | 说明 | 风险等级 |
|-----|------|---------|
| `Class.forName() + Method.invoke()` | 反射调用系统API | 视调用目标 |
| `Runtime.exec()` | 执行系统命令 | 高 |
| `SystemProperties.get()` | 获取系统属性 | 中 |

---

## 权限与API映射速查

| 权限 | 关联的主要API | 建议 |
|------|-------------|------|
| READ_PHONE_STATE | getDeviceId/getImei/getSubscriberId等 | 如无必要建议拔出 |
| ACCESS_FINE_LOCATION | 定位/WiFi扫描/基站查询 | 功能启动时申请，支持模糊定位 |
| ACCESS_COARSE_LOCATION | 粗略定位 | 优先使用替代精确定位 |
| READ_CONTACTS | 通讯录读取 | 仅通讯录功能才需要 |
| READ_EXTERNAL_STORAGE | 文件/媒体访问 | Android 10+考虑替代方案 |
| CAMERA | 相机 | 使用时申请 |
| RECORD_AUDIO | 麦克风 | 使用时申请 |
| READ_SMS | 短信读取 | 仅短信功能才需要 |
| READ_CALL_LOG | 通话记录 | 仅通话功能才需要 |
| BLUETOOTH_SCAN | 蓝牙扫描 | 启动时不扫描 |
