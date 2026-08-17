#!/bin/bash
APP_DIR="/Users/ws/Desktop/Project/Trea-Project/STOCK-Dev/src-tauri/target/debug/衡势价值.app"
BINARY="/Users/ws/Desktop/Project/Trea-Project/STOCK-Dev/src-tauri/target/debug/hengshi-value"

mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Resources"
cp "$BINARY" "$APP_DIR/Contents/MacOS/衡势价值"

if [ ! -f "$APP_DIR/Contents/Resources/衡势价值.icns" ]; then
    cp /Users/ws/Desktop/Project/Trea-Project/STOCK-Dev/src-tauri/icons/icon.icns "$APP_DIR/Contents/Resources/衡势价值.icns"
fi

if [ ! -f "$APP_DIR/Contents/Info.plist" ]; then
    cat > "$APP_DIR/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>衡势价值</string>
    <key>CFBundleIdentifier</key>
    <string>com.hengshi-value.app</string>
    <key>CFBundleName</key>
    <string>衡势价值</string>
    <key>CFBundleIconFile</key>
    <string>衡势价值</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSUIElement</key>
    <true/>
</dict>
</plist>
EOF
fi

open "$APP_DIR"
