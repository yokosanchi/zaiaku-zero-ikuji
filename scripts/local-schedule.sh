#!/bin/sh
# 毎朝の自動生成を、この Mac の launchd に登録／解除する。
#   sh scripts/local-schedule.sh install     # 06:15 に毎日実行
#   sh scripts/local-schedule.sh uninstall
#   sh scripts/local-schedule.sh status
#
# ※ GitHub Actions を使う場合はこれは不要。SETUP.md 参照。
set -eu

REPO="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
LABEL="com.zaiaku.daily"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
NODE_BIN="$(dirname "$(command -v node || echo /usr/local/bin/node)")"

case "${1:-}" in
  install)
    # 自動コミット用の git 識別子（このリポジトリだけ）
    git -C "$REPO" config user.name  "zaiaku-bot"
    git -C "$REPO" config user.email "actions@users.noreply.github.com"

    mkdir -p "$HOME/Library/LaunchAgents"
    cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/sh</string>
    <string>$REPO/scripts/run-local.sh</string>
  </array>
  <key>WorkingDirectory</key><string>$REPO</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>$NODE_BIN:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin</string>
  </dict>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>6</integer><key>Minute</key><integer>15</integer></dict>
  <key>StandardOutPath</key><string>$REPO/scripts/local-run.out</string>
  <key>StandardErrorPath</key><string>$REPO/scripts/local-run.err</string>
</dict>
</plist>
EOF
    launchctl unload "$PLIST" 2>/dev/null || true
    launchctl load "$PLIST"
    echo "登録しました： 毎日 06:15 に $REPO/scripts/run-local.sh"
    echo "→ .env に GEMINI_API_KEY を入れておくこと（未設定なら生成はスキップされます）"
    ;;
  uninstall)
    launchctl unload "$PLIST" 2>/dev/null || true
    rm -f "$PLIST"
    echo "解除しました。"
    ;;
  status)
    launchctl list | grep "$LABEL" || echo "未登録"
    ;;
  *)
    echo "usage: sh scripts/local-schedule.sh [install|uninstall|status]"
    exit 1
    ;;
esac
