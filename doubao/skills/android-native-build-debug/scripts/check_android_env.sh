#!/usr/bin/env bash
# check_android_env.sh — Android 构建环境体检
# 输出分阻塞项（BLOCKING，不修就无法构建）与非阻塞项（INFO），只修阻塞项。
# 用法: bash scripts/check_android_env.sh [项目根目录]
set -u
ROOT="${1:-.}"

say_block() { echo "[BLOCKING] $*"; }
say_info()  { echo "[INFO]     $*"; }
say_ok()    { echo "[OK]       $*"; }

echo "== Android env check (root: $ROOT) =="

# --- JDK ---
if command -v java >/dev/null 2>&1; then
    say_ok "java: $(java -version 2>&1 | head -n1)"
else
    if [ -n "${JAVA_HOME:-}" ] && [ -x "${JAVA_HOME}/bin/java" ]; then
        say_ok "java via JAVA_HOME=$JAVA_HOME (但 java 不在 PATH，gradlew 可能找不到)"
    else
        say_block "JDK 缺失：java 不在 PATH 且 JAVA_HOME 未设置（报错形如 'JAVA_HOME is not set'）"
    fi
fi
[ -z "${JAVA_HOME:-}" ] && say_info "JAVA_HOME 未设置；若 gradlew 报 JAVA_HOME 错误需先配置"

# --- Android SDK ---
SDK_DIR=""
for c in "${ANDROID_HOME:-}" "${ANDROID_SDK_ROOT:-}"; do
    [ -n "$c" ] && [ -d "$c" ] && SDK_DIR="$c" && break
done
if [ -z "$SDK_DIR" ]; then
    for lp in "$ROOT/local.properties" "$ROOT/android/local.properties"; do
        if [ -f "$lp" ]; then
            v=$(grep -E '^sdk\.dir=' "$lp" | head -n1 | cut -d= -f2- | sed 's/\\:/:/g; s/\\\\/\\/g')
            [ -n "$v" ] && [ -d "$v" ] && SDK_DIR="$v" && break
        fi
    done
fi
if [ -n "$SDK_DIR" ]; then
    say_ok "Android SDK: $SDK_DIR"
    [ -d "$SDK_DIR/platform-tools" ] || say_block "SDK 缺 platform-tools（adb 所在）"
else
    say_block "Android SDK 缺失：ANDROID_HOME/ANDROID_SDK_ROOT 未设置，且 local.properties 无有效 sdk.dir（报错形如 'SDK location not found'）"
fi

# --- adb / 设备 ---
if command -v adb >/dev/null 2>&1; then
    DEVS=$(adb devices 2>/dev/null | awk 'NR>1 && NF>0 {print $2}')
    if echo "$DEVS" | grep -q '^device$'; then
        say_ok "adb 有已授权设备"
    elif echo "$DEVS" | grep -q 'unauthorized'; then
        say_block "设备存在但 unauthorized：需在手机上确认 USB 调试授权弹窗"
    else
        say_info "adb 无连接设备；仅打包不需要设备，运行调试才需要"
    fi
else
    say_info "adb 不在 PATH（一般在 \$SDK_DIR/platform-tools/adb）；模拟器场景可用其自带 adb.exe + adb connect <端口>"
fi

# --- Gradle wrapper ---
if [ -f "$ROOT/gradlew" ] || [ -f "$ROOT/gradlew.bat" ]; then
    say_ok "gradlew 在 $ROOT"
elif [ -f "$ROOT/android/gradlew" ] || [ -f "$ROOT/android/gradlew.bat" ]; then
    say_ok "gradlew 在 $ROOT/android（Capacitor 类工程构建入口在此目录）"
else
    say_block "未找到 gradlew/gradlew.bat（查过 $ROOT 与 $ROOT/android）"
fi

# --- NDK/CMake（仅 native 工程需要） ---
HAS_NATIVE=0
for f in "$ROOT/CMakeLists.txt" "$ROOT/android/CMakeLists.txt" "$ROOT/app/src/main/cpp/CMakeLists.txt" "$ROOT/android/app/src/main/cpp/CMakeLists.txt"; do
    [ -f "$f" ] && HAS_NATIVE=1 && break
done
if [ "$HAS_NATIVE" -eq 1 ]; then
    if command -v cmake >/dev/null 2>&1 || [ -n "${ANDROID_NDK_HOME:-}" ] || { [ -n "$SDK_DIR" ] && [ -d "$SDK_DIR/ndk" ]; }; then
        say_ok "native 工程且 NDK/CMake 可用"
    else
        say_block "工程含 CMakeLists.txt 但 NDK/CMake 未找到（SDK 目录无 ndk/ 且 cmake 不在 PATH）"
    fi
else
    say_info "未发现 CMakeLists.txt，NDK/CMake 非必需"
fi

echo "== 体检完成：只修 BLOCKING 项，INFO 项可先忽略 =="
