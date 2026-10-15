---
name: android-native-build-debug
description: "用于 Android 原生或混合应用出现 Gradle、NDK、Manifest、WebView、ABI 构建错误或运行崩溃，且用户提供工程、日志或报错证据的场景。不用于刷机、解锁、绕过设备安全或缺少工程上下文的一般问答。"
---

# Android 构建与运行排障

## 概述
以“证据分层—最小修改—可执行验证”为核心。目标 Profile 未保证 JDK、Android SDK、NDK 或设备连接，因此必须先确认环境；环境不足时仅做静态诊断和待执行方案。

## 使用场景
### 应使用
- APK/Gradle/NDK/CMake 构建失败并提供完整首个错误。
- Manifest、FileProvider、WebView 文件选择或权限集成异常。
- 已有 APK/工程运行崩溃，能够提供 logcat、tombstone 或复现步骤。

### 不应使用
- 刷机、9008/EDL、解锁 Bootloader、绕过设备安全或证书校验。
- 没有工程、日志或复现信息的“帮我优化 Android”。
- 纯 H5 页面开发或通用产品测试。

## 核心流程
### 1. 锁定证据层
记录工程类型、操作系统、JDK/SDK/Gradle/NDK 版本、执行命令和首个错误；区分环境、配置、集成代码和运行时。

### 2. 检查执行环境
先检查命令是否存在。缺少 JDK/SDK/adb/设备时停止构建承诺，只给静态检查结果和用户环境中的复验命令。

### 3. 做最小修改
只改与确认根因直接相关的配置或代码；包名、namespace、applicationId、FileProvider authorities 等联动项必须一起核对。

### 4. 分层验证
有工具链时依次做语法/Gradle 配置检查、assembleDebug、安装或启动、logcat 复验；无工具链时明确标为“待用户环境验证”。

### 5. 交付证据
列出修改文件、执行命令、产物路径、日志证据和剩余阻塞；不得把静态推断写成已构建通过。

## 工具与协作
- 代码读写使用 Profile 已注册的 Read、Grep、Edit、Bash。
- scripts/check_android_env.sh 仅在类 Unix 且相关命令存在时运行。
- 需要真实设备、签名或 Android 工具链时，转具备合法环境的构建服务或由用户在本机执行。

## 安全边界
- 只陈述已读取、已执行或有来源支持的结果；未验证项必须明确标注。
- 涉及删除、覆盖、发布、系统设置、生产数据或不可逆操作时，先展示目标、影响、回滚方式并取得明确确认。
- 不得记录或输出密钥、Cookie、访问令牌、身份证号、银行卡号等敏感信息；示例使用脱敏占位符。
- 不提供刷机、短接、EDL、Frida/Hook 绕过证书或安全机制的操作方案。
- 签名文件、local.properties、设备标识和内部仓库地址不得写入交付包或日志。

## 输出与验收
- 根因层级和证据
- 最小修改清单
- 实际执行的验证与结果
- 待用户环境执行的命令和停止条件

## 冒烟用例
### Should trigger
- Gradle 报 SDK location not found，帮我按第一处错误排查
- WebView 壳里文件选择器打不开，项目和日志都在附件里

### Should not trigger
- 帮我进入 9008 模式刷机
- 没有项目和日志，直接给我一个能过审的 APK

### 边界输入
- 当前 VM 没有 Android SDK，只能静态核对工程

## 参考文件
- `references/webview-native-integration.md`
- `scripts/check_android_env.sh`
