#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export DEVELOPER_DIR="${DEVELOPER_DIR:-/Applications/Xcode.app/Contents/Developer}"
if [[ ! -x "$DEVELOPER_DIR/usr/bin/xcodebuild" ]]; then
  echo '需要完整 Xcode 26 或更新版本，请安装后重试。'
  exit 1
fi
xcodebuild -project CodexReset.xcodeproj -scheme CodexReset -configuration Release \
  -derivedDataPath "$PWD/build" CODE_SIGNING_ALLOWED=NO build
APP="$PWD/build/Build/Products/Release/Codex Reset.app"
xattr -cr "$APP"
codesign --force --sign - --entitlements Widget/Widget.entitlements "$APP/Contents/PlugIns/CodexResetWidget.appex"
codesign --force --sign - --entitlements App/App.entitlements "$APP"
codesign --verify --deep --strict "$APP"
echo "已生成系统小组件应用：$APP"
if [[ "${1:-}" != "--no-open" ]]; then open "$APP"; fi
