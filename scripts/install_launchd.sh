#!/bin/zsh
# 安装/卸载/验证 App 榜单扫描的 launchd 定时任务(按平台)
# 用法: scripts/install_launchd.sh install|uninstall|verify [ios|play]

set -euo pipefail
ACTION="${1:-}"
PLATFORM="${2:-ios}"
LABEL="com.appcharts.scan.${PLATFORM}"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "${PROJECT_DIR}/logs"

case "$PLATFORM" in
ios)   RUN_AT=("1" "9" "30") ;;   # 周一 09:30
play)  RUN_AT=("1" "9" "50") ;;   # 周一 09:50,与 ios 错开
*) echo "平台须为 ios 或 play"; exit 1 ;;
esac
WEEKDAY="${RUN_AT[1]}" HOUR="${RUN_AT[2]}" MINUTE="${RUN_AT[3]}"
# zsh 数组从 1 开始:RUN_AT[1]=周几,[2]=时,[3]=分

case "$ACTION" in
install)
  # 迁移:卸载旧的单平台任务 com.appcharts.scan(如存在)
  OLD_PLIST="$HOME/Library/LaunchAgents/com.appcharts.scan.plist"
  if [ -f "$OLD_PLIST" ]; then
    launchctl unload "$OLD_PLIST" 2>/dev/null || true
    rm -f "$OLD_PLIST"
    echo "已迁移移除旧任务: com.appcharts.scan"
  fi
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
    <string>cd '${PROJECT_DIR}' &amp;&amp; claude -p '/app-scan ${PLATFORM} standard' &gt;&gt; "${PROJECT_DIR}/logs/scan-${PLATFORM}-\$(date +%F).log" 2&gt;&amp;1</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key><integer>${WEEKDAY}</integer>
    <key>Hour</key><integer>${HOUR}</integer>
    <key>Minute</key><integer>${MINUTE}</integer>
  </dict>
  <key>StandardOutPath</key><string>${PROJECT_DIR}/logs/launchd-${PLATFORM}.out</string>
  <key>StandardErrorPath</key><string>${PROJECT_DIR}/logs/launchd-${PLATFORM}.err</string>
</dict>
</plist>
EOF
  launchctl unload "$PLIST" 2>/dev/null || true
  launchctl load "$PLIST"
  echo "已安装: $PLIST(每周一 ${HOUR}:${MINUTE} 运行 /app-scan ${PLATFORM} standard)"
  "$0" verify "$PLATFORM"
  ;;
uninstall)
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "已卸载: $PLIST"
  ;;
verify)
  launchctl list | grep "$LABEL" > /dev/null && echo "✓ ${LABEL} 已加载" || { echo "✗ ${LABEL} 未加载"; exit 1; }
  CLAUDE_BIN="$(zsh -lc 'command -v claude' || true)"
  [ -n "$CLAUDE_BIN" ] && echo "✓ claude 可用: $CLAUDE_BIN" || { echo "✗ 登录 shell 找不到 claude"; exit 1; }
  if [ "$PLATFORM" = "play" ]; then
    NODE_BIN="$(zsh -lc 'command -v node' || true)"
    [ -n "$NODE_BIN" ] && echo "✓ node 可用: $NODE_BIN" || { echo "✗ 登录 shell 找不到 node(Play 需要)"; exit 1; }
    [ -d "${PROJECT_DIR}/node_modules/google-play-scraper" ] && echo "✓ npm 依赖已装" || { echo "✗ 缺 npm 依赖:请在项目根 npm install"; exit 1; }
  fi
  ;;
*)
  echo "用法: $0 install|uninstall|verify [ios|play]"; exit 1
  ;;
esac
