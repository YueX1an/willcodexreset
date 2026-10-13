#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if ! xcrun --find swiftc >/dev/null 2>&1; then
  echo '请先安装 Apple 命令行开发工具：xcode-select --install'
  exit 1
fi
APP="$PWD/build/Codex Reset.app"
mkdir -p "$APP/Contents/MacOS"
xcrun swiftc CodexReset.swift -O -module-cache-path "$PWD/build/ModuleCache" -target "$(uname -m)-apple-macosx12.0" -framework AppKit -o "$APP/Contents/MacOS/CodexReset"
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>CodexReset</string>
<key>CFBundleIdentifier</key><string>com.willcodexreset.widget</string>
<key>CFBundleName</key><string>Codex Reset</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>1.0</string>
<key>LSMinimumSystemVersion</key><string>12.0</string>
<key>LSUIElement</key><true/>
<key>NSHighResolutionCapable</key><true/>
</dict></plist>
PLIST
xattr -cr "$APP"
codesign --force --sign - "$APP"
echo "已生成：$APP"
if [[ "${1:-}" != "--no-open" ]]; then open "$APP"; fi
