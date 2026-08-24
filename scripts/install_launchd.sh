#!/bin/zsh
# 安装/卸载/验证 App 榜单扫描的 launchd 定时任务
# 用法: scripts/install_launchd.sh install|uninstall|verify

set -euo pipefail
LABEL="com.appcharts.scan"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "${PROJECT_DIR}/logs"

case "${1:-}" in
install)
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-lc</string>
    <string>cd '${PROJECT_DIR}' && claude -p '/app-scan standard' >> '${PROJECT_DIR}/logs/scan-\$(date +%F).log' 2>&1</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key><integer>1</integer>
    <key>Hour</key><integer>9</integer>
    <key>Minute</key><integer>30</integer>
  </dict>
  <key>StandardOutPath</key><string>${PROJECT_DIR}/logs/launchd.out</string>
  <key>StandardErrorPath</key><string>${PROJECT_DIR}/logs/launchd.err</string>
</dict>
</plist>
EOF
  launchctl unload "$PLIST" 2>/dev/null || true
  launchctl load "$PLIST"
  echo "已安装: $PLIST（每周一 09:30 运行）"
  "$0" verify
  ;;
uninstall)
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "已卸载: $PLIST"
  ;;
verify)
  launchctl list | grep -q "$LABEL" && echo "✓ launchd 任务已加载" || { echo "✗ 未加载"; exit 1; }
  CLAUDE_BIN="$(zsh -lc 'command -v claude' || true)"
  [ -n "$CLAUDE_BIN" ] && echo "✓ claude 可用: $CLAUDE_BIN" || { echo "✗ 登录 shell 找不到 claude"; exit 1; }
  ;;
*)
  echo "用法: $0 install|uninstall|verify"; exit 1
  ;;
esac
