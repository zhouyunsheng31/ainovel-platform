#!/bin/bash
# 快速重新构建 APK

echo "=== AI小说拆书系统 - APK 重新构建 ==="
echo ""

# 1. 复制最新的 Web 资源到 assets
echo "[1/4] 复制 Web 资源..."
cp -r ../css android/app/src/main/assets/
cp -r ../js android/app/src/main/assets/
cp ../index.html android/app/src/main/assets/

# 2. 清理旧构建
echo "[2/4] 清理旧构建..."
cd android
./gradlew clean

# 3. 构建 Debug APK
echo "[3/4] 构建 APK..."
./gradlew assembleDebug

# 4. 复制 APK 到下载目录
echo "[4/4] 复制 APK..."
cp app/build/outputs/apk/debug/app-debug.apk /sdcard/Download/ai-novel-platform-fixed.apk

echo ""
echo "✅ 构建完成！"
echo "APK 位置: /sdcard/Download/ai-novel-platform-fixed.apk"
echo ""
echo "请卸载旧版本后安装新 APK"
