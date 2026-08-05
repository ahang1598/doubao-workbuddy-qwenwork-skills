# API与PandoraEx模块详细映射表

> 本文件基于 PandoraEx 项目 `ConstantModel.java` 中定义的全部监控模块与API常量，提供具体系统API到合规模块的完整映射。

---

## 1. 设备信息模块 (DeviceInfoMonitor)

**模块标识**：`ConstantModel.DeviceInfo.NAME` = `"device"`
**Monitor类**：`DeviceInfoMonitor.java`

| 系统API | PandoraEx常量 | 获取信息 | 风险等级 | 所需权限 |
|---------|-------------|---------|---------|---------|
| `TelephonyManager.getDeviceId()` | `GET_DEVICE_ID` | IMEI/MEID | 高 | READ_PHONE_STATE |
| `TelephonyManager.getDeviceId(int)` | `GET_DEVICE_ID_PARAM_INDEX` | IMEI/MEID(指定卡槽) | 高 | READ_PHONE_STATE |
| `TelephonyManager.getImei()` | `GET_IMEI` | IMEI (API 26+) | 高 | READ_PHONE_STATE |
| `TelephonyManager.getImei(int)` | `GET_IMEI_PARAM_INDEX` | IMEI(指定卡槽) | 高 | READ_PHONE_STATE |
| `TelephonyManager.getMeid()` | `GET_MEID` | MEID (API 26+) | 高 | READ_PHONE_STATE |
| `TelephonyManager.getMeid(int)` | `GET_MEID_PARAM_INDEX` | MEID(指定卡槽) | 高 | READ_PHONE_STATE |
| `TelephonyManager.getSubscriberId()` | `GET_SUBSCRIBER_ID` | IMSI | 高 | READ_PHONE_STATE |
| `TelephonyManager.getSubscriberId(int)` | `GET_SUBSCRIBER_ID_I` | IMSI(指定subId) | 高 | READ_PHONE_STATE |
| `TelephonyManager.getLine1Number()` | `GET_LINE1_NUMBER` | 本机号码 | 高 | READ_PHONE_STATE |
| `TelephonyManager.getSimSerialNumber()` | `GET_SIM_SERIAL_NUMBER` | ICCID | 高 | READ_PHONE_STATE |
| `SubscriptionInfo.getIccId()` | `GET_ICCID_FROM_SUBSCRIPTION_INFO` | ICCID | 高 | READ_PHONE_STATE |
| `TelephonyManager.getSimOperator()` | `GET_SIM_OPERATOR` | SIM运营商代码 | 低 | 无 |
| `TelephonyManager.getSimState()` | `GET_SIM_STATE` | SIM卡状态 | 中 | 无 |
| `TelephonyManager.getSimState(int)` | `GET_SIM_STATE_I` | SIM卡状态(指定槽位) | 中 | 无 |
| `TelephonyManager.getNetworkOperator()` | `GET_NETWORK_OPERATOR` | 网络运营商代码 | 低 | 无 |
| `Settings.Secure.getString(ANDROID_ID)` | `GET_ANDROID_ID` | Android ID | 中 | 无 |
| `Build.MODEL` / `Build.getSerial()` | `GET_MODEL` / `GET_SERIAL` | 手机型号/设备序列号 | 中/高 | 无/READ_PHONE_STATE(API 29+) |
| `TelephonyManager.getUiccCardsInfo()` | `GET_UICC_CARDS_INFO` | UICC卡信息(ICCID) | 高 | READ_PHONE_STATE |
| `SubscriptionManager.getActiveSubscriptionInfoList()` | `GET_ACTIVE_SUB_INFO_LIST` | 活跃SIM订阅信息 | 高 | READ_PHONE_STATE |
| `SubscriptionManager.getAccessibleSubscriptionInfoList()` | `GET_ACCESS_SUB_INFO_LIST` | 可访问SIM订阅信息 | 高 | READ_PHONE_STATE |
| `SubscriptionManager.getCompleteActiveSubscriptionInfoList()` | `GET_COMP_ACTIVE_SUB_INFO_LIST` | 完整活跃订阅信息 | 高 | READ_PHONE_STATE |
| `SubscriptionManager.getOpportunisticSubscriptions()` | `GET_OPP_SUBS` | 机会订阅信息 | 高 | READ_PHONE_STATE |
| `SubscriptionManager.getActiveSubscriptionInfo(int)` | `GET_ACTIVE_SUB_INFO_PARAM_I` | 指定活跃订阅信息 | 高 | READ_PHONE_STATE |
| `SubscriptionManager.getActiveSubscriptionInfoForSimSlotIndex(int)` | `GET_ACTIVE_SUB_INFO_SIM_PARAM_I` | 指定槽位活跃订阅 | 高 | READ_PHONE_STATE |
| OAID获取(OPPO/小米/vivo/华为/荣耀) | `OAID_OPPO` / `OAID_XIAOMI` / `OAID_VIVO` / `OAID_HUAWEI` / `OAID_HONOR` | 开放匿名标识 | 中 | 无 |
| `SystemProperties.get(key)` | `OS_PROP_GET` | 系统属性(型号/序列号) | 中 | 无 |
| `UUID.randomUUID()` | `GET_GUID` | 全局唯一ID | 低 | 无 |

---

## 2. 定位模块 (LocationMonitor)

**模块标识**：`ConstantModel.Location.NAME` = `"location"`
**Monitor类**：`LocationMonitor.java`

| 系统API | PandoraEx常量 | 获取信息 | 风险等级 | 所需权限 |
|---------|-------------|---------|---------|---------|
| `LocationManager.getLastKnownLocation(String)` | `GET_LAST_KNOWN_LOCATION` | 最后已知位置 | 高 | ACCESS_FINE/COARSE_LOCATION |
| `LocationManager.requestLocationUpdates(String,long,float,LocationListener)` | `REQUEST_LOCATION_PARAM_LISTENER` | 持续定位 | 高 | ACCESS_FINE/COARSE_LOCATION |
| `LocationManager.requestLocationUpdates(String,long,float,LocationListener,Looper)` | `REQUEST_LOCATION_PARAM_LOOPER` | 持续定位(指定Looper) | 高 | ACCESS_FINE/COARSE_LOCATION |
| `LocationManager.requestLocationUpdates(long,float,Criteria,LocationListener,Looper)` | `REQUEST_LOCATION_PARAM_CRITERIA` | 按条件定位 | 高 | ACCESS_FINE/COARSE_LOCATION |
| `LocationManager.requestLocationUpdates(String,long,float,PendingIntent)` | `REQUEST_LOCATION_PARAM_INTENT` | PendingIntent定位 | 高 | ACCESS_FINE/COARSE_LOCATION |
| `LocationManager.requestLocationUpdates(long,float,Criteria,PendingIntent)` | `REQUEST_LOCATION_PARAM_C_INTENT` | 按条件PendingIntent定位 | 高 | ACCESS_FINE/COARSE_LOCATION |
| `LocationManager.requestSingleUpdate(...)` (4个重载) | `REQUEST_SINGLE_PARAM_*` | 单次定位 | 高 | ACCESS_FINE/COARSE_LOCATION |
| `LocationManager.removeUpdates(LocationListener)` | `REMOVE_UPDATES_LISTENER` | 停止定位 | — | — |
| `LocationManager.addGpsStatusListener(...)` | `ADD_GPS_STATUS_LISTENER` | GPS状态监听 | 中 | ACCESS_FINE_LOCATION |
| `Location.getLatitude()` / `Location.getLongitude()` | `GET_LATITUDE` / `GET_LONGITUDE` | 经纬度 | 高 | — |
| `Location.getAccuracy()` | `GET_ACCURACY` | 定位精度 | 中 | — |
| `TelephonyManager.getCellLocation()` | `GET_CELL_LOCATION` | 基站位置 | 高 | ACCESS_FINE_LOCATION |
| `TelephonyManager.getAllCellInfo()` | `GET_ALL_CELL_INFO` | 全部基站信息 | 高 | ACCESS_FINE_LOCATION |
| `TelephonyManager.requestCellInfoUpdate(...)` | `REQUEST_CELL_INFO_UPDATE` | 请求基站信息更新 | 高 | ACCESS_FINE_LOCATION |
| `TelephonyManager.requestNetworkScan(...)` | `REQUEST_NETWORK_SCAN` | 网络扫描 | 高 | ACCESS_FINE_LOCATION |
| `TelephonyManager.getServiceState()` | `GET_SERVICE_STATE` | 服务状态 | 中 | — |
| `TelephonyManager.listen(PhoneStateListener,int)` | `LISTEN` | 电话状态监听 | 中 | 视监听内容 |
| `GsmCellLocation.getCid()` / `CellIdentityGsm.getCid()` | `GET_CID` | GSM基站CID | 高 | ACCESS_FINE_LOCATION |
| `CdmaCellLocation.getBaseStationId()` | `GET_BASE_STATION_ID` | CDMA基站ID | 高 | ACCESS_FINE_LOCATION |
| `CellIdentityLte.getCi()` | `GET_CELL_LTE_CI` | LTE基站CI | 高 | ACCESS_FINE_LOCATION |
| `CellIdentityWcdma.getCid()` | `GET_CELL_WCDMA_CID` | WCDMA基站CID | 高 | ACCESS_FINE_LOCATION |
| `CellIdentityTdscdma.getCid()` | `GET_CELL_TDSCDMA_CID` | TD-SCDMA基站CID | 高 | ACCESS_FINE_LOCATION |
| `WifiManager.getConnectionInfo()` | `GET_CONNECT_INFO` | WiFi连接信息 | 中 | ACCESS_WIFI_STATE |
| `BluetoothAdapter.startDiscovery()` | `START_DISCOVERY` | 蓝牙设备扫描 | 中 | BLUETOOTH_SCAN(API 31+) |
| `BluetoothLeScanner.startScan(...)` (3个重载) | `START_SCAN_*` | BLE扫描 | 中 | BLUETOOTH_SCAN(API 31+) |
| `BluetoothAdapter.startLeScan(...)` (2个重载) | `START_LE_SCAN` / `START_LE_SCAN_PARAM_UUID` | BLE扫描(旧API) | 中 | BLUETOOTH_SCAN(API 31+) |

---

## 3. 网络信息模块 (NetworkMonitor)

**模块标识**：`ConstantModel.Network.NAME` = `"network"`
**Monitor类**：`NetworkMonitor.java`

| 系统API | PandoraEx常量 | 获取信息 | 风险等级 | 所需权限 |
|---------|-------------|---------|---------|---------|
| `WifiInfo.getMacAddress()` | `GET_MAC_ADDRESS` | WiFi MAC地址 | 高 | ACCESS_WIFI_STATE |
| `NetworkInterface.getHardwareAddress()` | `GET_HARDWARE_ADDRESS` | 网卡MAC地址 | 高 | 无 |
| `NetworkInterface.getNetworkInterfaces()` | `GET_NETWORK_INTERFACES` | 网络接口列表 | 中 | 无 |
| `NetworkInterface.getInetAddresses()` | `GET_INET_ADDRESS` | IP地址列表 | 中 | 无 |
| `NetworkInterface.getInterfaceAddresses()` | `GET_INTERFACE_ADDRESS` | 接口地址 | 中 | 无 |
| `InetAddress.getHostAddress()` | `GET_HOST_ADDRESS` | IP地址(字符串) | 中 | 无 |
| `WifiInfo.getSSID()` | `GET_SSID` | WiFi名称(SSID) | 中 | ACCESS_FINE_LOCATION(API 27+) |
| `WifiInfo.getBSSID()` | `GET_BSSID` | WiFi BSSID | 中 | ACCESS_FINE_LOCATION(API 27+) |
| `WifiInfo.getIpAddress()` | `GET_IPADDR` | WiFi IP地址 | 低 | 无 |
| `WifiInfo.toString()` | `WIFI_TO_STRING` | WiFi信息字符串(含SSID/MAC) | 中 | ACCESS_WIFI_STATE |
| `WifiManager.startScan()` | `START_SCAN` | 启动WiFi扫描 | 中 | ACCESS_FINE_LOCATION |
| `WifiManager.getScanResults()` | `GET_SCAN_RESULTS` | WiFi扫描结果 | 中 | ACCESS_FINE_LOCATION |
| `WifiManager.getConfiguredNetworks()` | `GET_CONFIGURE_NETWORKS` | 已配置WiFi列表 | 低 | ACCESS_WIFI_STATE |
| `WifiManager.getDhcpInfo()` | `GET_DHCP_INFO` | DHCP信息 | 低 | ACCESS_WIFI_STATE |
| `TelephonyManager.getNetworkType()` | `GET_NETWORK_TYPE` | 网络类型(2G/3G/4G) | 低 | READ_PHONE_STATE(API 30+) |
| `TelephonyManager.getDataNetworkType()` | `GET_DATA_NETWORK_TYPE` | 数据网络类型 | 低 | READ_PHONE_STATE |
| `NetworkInfo.getType()` / `getSubtype()` / `getTypeName()` | `GET_TYPE` / `GET_SUB_TYPE` / `GET_TYPE_NAME` | 网络类型信息 | 低 | ACCESS_NETWORK_STATE |
| `NetworkInfo.getExtraInfo()` | `NET_GET_EXTRA_INFO` | 网络扩展信息(含SSID) | 中 | ACCESS_NETWORK_STATE |
| `NetworkCapabilities.hasTransport(int)` | `HAS_TRANSPORT` | 传输类型检查 | 低 | 无 |
| `ConnectivityManager.getActiveNetworkInfo()` | `GET_ACTIVE_NET_INFO` | 当前网络信息 | 低 | ACCESS_NETWORK_STATE |
| `BluetoothAdapter.getAddress()` | `GET_ADDRESS` | 蓝牙MAC地址 | 高 | BLUETOOTH |
| `BluetoothAdapter.getName()` | `BLUETOOTH_GET_NAME` | 蓝牙设备名称 | 低 | BLUETOOTH |

---

## 4. 已安装应用列表模块 (InstalledAppListMonitor)

**模块标识**：`ConstantModel.InstalledAppList.NAME` = `"appinfo"`
**Monitor类**：`InstalledAppListMonitor.java`

| 系统API | PandoraEx常量 | 获取信息 | 风险等级 | 所需权限 |
|---------|-------------|---------|---------|---------|
| `PackageManager.getInstalledPackages(int)` | `GET_INSTALLED_PACKAGES` | 已安装应用列表 | 高 | 无(API 30+受限) |
| `PackageManager.getInstalledPackages(PackageInfoFlags)` | `GET_INSTALLED_PACKAGES_F` | 已安装应用列表(Flags) | 高 | 无(API 30+受限) |
| `PackageManager.getInstalledApplications(int)` | `GET_INSTALLED_APPLICATIONS` | 已安装应用信息 | 高 | 无(API 30+受限) |
| `PackageManager.getInstalledApplications(ApplicationInfoFlags)` | `GET_INSTALLED_APPLICATIONS_F` | 已安装应用信息(Flags) | 高 | 无(API 30+受限) |
| `PackageManager.getPackageInfo(String,int)` | `GET_PACKAGE_INFO_WITH_NAME` | 指定应用包信息 | 中 | 无(API 30+受限) |
| `PackageManager.getPackageInfo(VersionedPackage,int)` | `GET_PACKAGE_INFO_WITH_VP` | 指定版本包信息 | 中 | 无(API 30+受限) |
| `PackageManager.queryIntentActivities(Intent,int)` | `QUERY_INTENT_ACTIVITIES` | 查询可响应Activity | 中 | 无(API 30+受限) |
| `PackageManager.queryIntentServices(Intent,int)` | `QUERY_INTENT_SERVICES` | 查询可响应Service | 中 | 无(API 30+受限) |
| `PackageManager.getLaunchIntentForPackage(String)` | `GET_LAUNCH_INTENT_FOR_PACKAGE` | 获取应用启动Intent | 中 | 无 |
| `ActivityManager.getRunningAppProcesses()` | `GET_RUNNING_APP_PROCESS` | 运行中的进程列表 | 中 | 无 |
| `ActivityManager.getRunningTasks(int)` | `GET_RUNNING_TASKS` | 运行中的任务 | 中 | 无(已废弃) |
| `Context.registerReceiver(BroadcastReceiver,IntentFilter)` | `CONTEXT_REGISTER_RECEIVER` | 广播注册(含安装/卸载) | 中 | 无 |
| `AccessibilityManager.getEnabledAccessibilityServiceList(int)` | `GET_ENABLED_ACCESSIBILITY_SERVICE_LIST` | 已启用无障碍服务 | 中 | 无 |
| `AccessibilityManager.getInstalledAccessibilityServiceList()` | `GET_INSTALLED_ACCESSIBILITY_SERVICE_LIST` | 已安装无障碍服务 | 中 | 无 |

---

## 5. 剪贴板模块 (ClipboardMonitor)

**模块标识**：`ConstantModel.Clipboard.NAME` = `"clipboard"`
**Monitor类**：`ClipboardMonitor.java`

| 系统API | PandoraEx常量 | 获取信息 | 风险等级 | 所需权限 |
|---------|-------------|---------|---------|---------|
| `ClipboardManager.getPrimaryClip()` | `GET_PRIMARY_CLIP` | 剪贴板内容 | 中 | 无 |
| `ClipboardManager.getText()` | `GET_TEXT` | 剪贴板文本 | 中 | 无 |
| `ClipboardManager.getPrimaryClipDescription()` | `GET_PRIMARY_CLIP_DESCRIPTION` | 剪贴板内容描述 | 低 | 无 |
| `ClipboardManager.hasPrimaryClip()` | `HAS_PRIMARY_CLIP` | 是否有剪贴板内容 | 低 | 无 |
| `ClipboardManager.hasText()` | `HAS_TEXT` | 是否有文本 | 低 | 无 |
| `ClipboardManager.setPrimaryClip(ClipData)` | `SET_PRIMARY_CLIP` | 设置剪贴板 | 低 | 无 |
| `ClipboardManager.clearPrimaryClip()` | `CLEAR_PRIMARY_CLIP` | 清空剪贴板 | 低 | 无 |
| `ClipboardManager.setText(CharSequence)` | `SET_TEXT` | 设置文本 | 低 | 无 |
| `ClipboardManager.addPrimaryClipChangedListener(...)` | `ADD_CLIP_CHANGED_LISTENER` | 监听剪贴板变化 | 中 | 无 |
| `ClipboardManager.removePrimaryClipChangedListener(...)` | `REMOVE_CLIP_CHANGED_LISTENER` | 停止监听剪贴板 | — | 无 |

---

## 6. 相机模块 (CameraMonitor)

**模块标识**：`ConstantModel.Camera.NAME` = `"camera"`
**Monitor类**：`CameraMonitor.java`

| 系统API | PandoraEx常量 | 功能 | 风险等级 | 所需权限 |
|---------|-------------|------|---------|---------|
| `Camera.open()` | `OPEN` | 打开相机(旧API) | 高 | CAMERA |
| `Camera.open(int)` | `OPEN_PARAM_I` | 打开指定相机(旧API) | 高 | CAMERA |
| `CameraManager.openCamera(String,StateCallback,Handler)` | `OPEN_CAMERA_PARAM_SCH` | 打开相机(Camera2) | 高 | CAMERA |
| `CameraManager.openCamera(String,Executor,StateCallback)` | `OPEN_CAMERA_PARAM_SES` | 打开相机(Camera2+Executor) | 高 | CAMERA |
| `Camera.takePicture(...)` (2个重载) | `TAKE_PICTURE_SPP` / `TAKE_PICTURE_SPPP` | 拍照 | 高 | CAMERA |
| `CameraDevice.createCaptureRequest(int)` | `CREATE_CAPTURE_REQ` | 创建拍摄请求 | 高 | CAMERA |
| `CameraDevice.createCaptureRequest(int,Set)` | `CREATE_CAPTURE_REQ_IS` | 创建拍摄请求(含物理相机) | 高 | CAMERA |
| `CameraCaptureSession.setRepeatingRequest(...)` | `SET_REPEATING_REQUEST` | 设置重复捕获请求(预览/录像) | 高 | CAMERA |
| `MediaRecorder.setVideoSource(int)` | `SET_VIDEO_SOURCE` | 设置视频源 | 高 | CAMERA |

---

## 7. 录音/语音模块 (AudioMonitor)

**模块标识**：`ConstantModel.Audio.NAME` = `"recorder"`
**Monitor类**：`AudioMonitor.java`

| 系统API | PandoraEx常量 | 功能 | 风险等级 | 所需权限 |
|---------|-------------|------|---------|---------|
| `MediaRecorder.start()` | `START` | 开始录音/录像 | 高 | RECORD_AUDIO / CAMERA |
| `AudioRecord.startRecording()` | `START_RECORDING` | 开始音频录制 | 高 | RECORD_AUDIO |
| `AudioRecord.startRecording(MediaSyncEvent)` | `START_RECORDING_MEDIA_SYNC_EVENT` | 同步音频录制 | 高 | RECORD_AUDIO |
| `MediaRecorder.setAudioSource(int)` | `SET_AUDIO_SOURCE` | 设置音频源 | 高 | RECORD_AUDIO |

---

## 8. 传感器模块 (SensorMonitor)

**模块标识**：`ConstantModel.Sensor.NAME` = `"sensor"`
**Monitor类**：`SensorMonitor.java`

| 系统API | PandoraEx常量 | 功能 | 风险等级 | 所需权限 |
|---------|-------------|------|---------|---------|
| `SensorManager.getSensors()` | `GET_SENSORS` | 获取传感器列表(已废弃) | 中 | 无 |
| `SensorManager.getSensorList(int)` | `GET_SENSOR_LIST_PARAM_I` | 获取指定类型传感器列表 | 中 | 无 |
| `SensorManager.getDynamicSensorList(int)` | `GET_DYNAMIC_SENSOR_LIST_PARAM_I` | 获取动态传感器列表 | 中 | 无 |
| `SensorManager.getDefaultSensor(int)` | `GET_DEFAULT_SENSOR_PARAM_I` | 获取默认传感器 | 中 | 无 |
| `SensorManager.getDefaultSensor(int,boolean)` | `GET_DEFAULT_SENSOR_PARAM_IB` | 获取默认传感器(含唤醒) | 中 | 无 |
| `SensorManager.registerListener(...)` (6个重载) | `REGISTER_LISTENER_PARAM_*` | 注册传感器监听 | 中 | 无(部分需BODY_SENSORS) |
| `SensorManager.requestTriggerSensor(...)` | `REGISTER_TRIGGER_LISTENER_PARAM_TS` | 请求触发传感器 | 中 | 无 |
| `SensorManager.registerDynamicSensorCallback(...)` (2个重载) | `REGISTER_DYNAMIC_LISTENER_PARAM_*` | 注册动态传感器回调 | 中 | 无 |
| `OrientationEventListener.enable()` | `ORIENTATION_EVENT_LISTENER_ENABLE` | 启用方向监听 | 低 | 无 |

---

## 9. 通讯录模块 (ContactsMonitor)

**模块标识**：`ConstantModel.Contacts.NAME` = `"contact"`
**Monitor类**：`ContactsMonitor.java`

| 系统API | PandoraEx常量 | 获取信息 | 风险等级 | 所需权限 |
|---------|-------------|---------|---------|---------|
| `ContentResolver.query(ContactsContract.*,...)` (3个重载) | `QUERY_PARAM_SORT_ORDER` / `QUERY_PARAM_CANCEL_SIGNAL` / `QUERY_PARAM_BUNDLE` | 联系人信息 | 高 | READ_CONTACTS |

---

## 10. 短信模块 (SmsMonitor)

**模块标识**：`ConstantModel.Sms.NAME` = `"sms"`
**Monitor类**：`SmsMonitor.java`

| 系统API | PandoraEx常量 | 功能 | 风险等级 | 所需权限 |
|---------|-------------|------|---------|---------|
| `SmsManager.sendTextMessage(...)` (2个重载) | `SENT_TEXT_MESSAGE_SSSPP` / `SENT_TEXT_MESSAGE_SSSPPL` | 发送短信 | 高 | SEND_SMS |
| `ContentResolver.query(Sms.CONTENT_URI,...)` (3个重载) | `QUERY_PARAM_*` | 读取短信 | 高 | READ_SMS |

---

## 11. 多媒体文件模块 (MediaMonitor)

**模块标识**：`ConstantModel.MediaFile.NAME` = `"mediaFile"`
**Monitor类**：`MediaMonitor.java`

| 系统API | PandoraEx常量 | 功能 | 风险等级 | 所需权限 |
|---------|-------------|------|---------|---------|
| `ContentResolver.query(MediaStore.*,...)` (3个重载) | `QUERY_PARAM_SORT_ORDER` / `QUERY_PARAM_CANCEL_SIGNAL` / `QUERY_PARAM_BUNDLE` | 查询媒体文件 | 中 | READ_EXTERNAL_STORAGE / READ_MEDIA_* |
| `FileObserver.startWatching()` | `FILE_START_WATCH` | 监听文件变化 | 中 | 无 |
| `ContentResolver.registerContentObserver(...)` | `CR_REG` | 注册内容观察者 | 中 | 无 |
| `ContentResolver.delete(...)` (2个重载) | `DELETE_PARAM_SELECTION` / `DELETE_PARAM_BUNDLE` | 删除媒体文件 | 中 | WRITE_EXTERNAL_STORAGE |
| `ContentResolver.insert(...)` (2个重载) | `INSERT_PARAM_VALUES` / `INSERT_PARAM_BUNDLE` | 插入媒体文件 | 低 | WRITE_EXTERNAL_STORAGE |

---

## 12. 命令行模块 (RuntimeMonitor)

**模块标识**：`ConstantModel.Runtime.NAME` = `"runtime"`
**Monitor类**：`RuntimeMonitor.java`

| 系统API | PandoraEx常量 | 功能 | 风险等级 |
|---------|-------------|------|---------|
| `Runtime.exec("ip ...")` | `EXEC_IP` | 获取IP地址 | 中 |
| `Runtime.exec("pm list package")` | `EXEC_PM` | 获取已安装应用列表 | 高 |
| `Runtime.exec("getprop model")` | `EXEC_GETPROP_MODEL` | 获取手机型号 | 中 |
| `Runtime.exec("getprop serial")` | `EXEC_GETPROP_SERIAL` | 获取设备序列号 | 高 |
| `Runtime.exec("getprop ...")` | `EXEC_GETPROP_ALL` | 获取系统属性 | 中 |

---

## 13. 权限模块 (PermissionMonitor)

**模块标识**：`ConstantModel.Permission.NAME` = `"permission"`
**Monitor类**：`PermissionMonitor.java`

| 系统API | PandoraEx常量 | 功能 | 风险等级 |
|---------|-------------|------|---------|
| `Activity.requestPermissions(String[],int)` | `REQUEST_PERMISSIONS` | 请求权限 | — |

---

## 14. 启动模块 (Boot)

**模块标识**：`ConstantModel.Boot.NAME` = `"boot"`

| 系统API | PandoraEx常量 | 功能 | 风险等级 |
|---------|-------------|------|---------|
| `Context.startActivity(Intent)` | `SA` | 启动Activity | — |

---

## 其他Monitor类（未在ConstantModel中定义独立模块）

| Monitor类 | 职责 |
|-----------|------|
| `ReflectMonitor.java` | 反射调用监控（Class.forName + Method.invoke） |
| `NetHttpMonitor.java` | HTTP网络请求监控 |
| `NetOkHttpMonitor.java` | OkHttp网络请求监控 |
| `NetHttpClientMonitor.java` | HttpClient网络请求监控 |
| `FileMonitor.java` | 文件操作监控 |
| `DexMonitor.java` | 动态加载DEX监控 |
| `DataTraceMonitor.java` | 数据流追踪监控 |
| `AutoStartMonitor.java` | 自启动监控 |
| `RelationBootMonitor.java` | 关联启动监控 |
| `SilentCallMonitor.java` | 静默调用监控 |
| `ReceiverMonitor.java` | 广播接收器监控 |
| `OaidMonitor.java` | OAID专项监控 |
| `MethodMonitor.java` | 通用方法级监控 |

---

## 权限与API映射速查

| 权限 | 关联的主要API | 合规建议 |
|------|-------------|---------|
| READ_PHONE_STATE | getDeviceId/getImei/getMeid/getSubscriberId/getLine1Number/getSimSerialNumber等 | 如无必要建议移除，Android 10+已禁止获取IMEI |
| ACCESS_FINE_LOCATION | 精确定位/WiFi扫描/基站查询/SSID获取 | 功能启动时申请，优先使用粗略定位替代 |
| ACCESS_COARSE_LOCATION | 粗略定位 | 不需要精确位置时优先使用 |
| READ_CONTACTS | 通讯录读取 | 仅通讯录功能才需要 |
| READ_EXTERNAL_STORAGE | 文件/媒体访问 | Android 10+使用分区存储替代 |
| CAMERA | 相机操作 | 使用时动态申请 |
| RECORD_AUDIO | 麦克风/录音 | 使用时动态申请 |
| READ_SMS | 短信读取 | 仅短信相关功能才需要 |
| SEND_SMS | 发送短信 | 仅短信发送功能才需要 |
| BLUETOOTH / BLUETOOTH_SCAN | 蓝牙操作/扫描 | Android 12+使用BLUETOOTH_SCAN替代 |
| BODY_SENSORS | 部分传感器 | 健康类功能才需要 |
