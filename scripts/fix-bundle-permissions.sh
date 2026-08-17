#!/bin/bash
# Tauri build 后处理：确保 backend-runner 在 .app bundle 中有可执行权限
# 这是 PyInstaller 编译产物的可执行位在 Tauri bundle 资源复制时丢失的修复
set -e

APP_PATH="$1"

if [ -z "$APP_PATH" ]; then
    echo "用法: $0 <path-to-.app>" >&2
    exit 1
fi

RUNNER="$APP_PATH/Contents/Resources/backend-runner"
if [ -f "$RUNNER" ]; then
    chmod +x "$RUNNER"
    echo "✅ 已设置可执行权限: $RUNNER"
    ls -la "$RUNNER"
else
    echo "⚠️ 未找到 backend-runner: $RUNNER" >&2
fi