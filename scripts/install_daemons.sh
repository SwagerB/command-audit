#!/bin/bash
# 命令审计系统 - 用 macOS launchd 托管常驻服务
#
# 托管两个服务（开机自启、崩溃自动拉起、关终端不影响）：
#   1) com.commandaudit.refresh  自动刷新（audit.py + generate_report.py，每 60 秒）
#   2) com.commandaudit.web      Flask 报告服务（http://localhost:8000）
#
# 可重复执行（幂等）。卸载用 scripts/uninstall_daemons.sh

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/data"
LA_DIR="$HOME/Library/LaunchAgents"
UID_NUM="$(id -u)"

mkdir -p "$LOG_DIR" "$LA_DIR"

PYTHON="$PROJECT_ROOT/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
    PYTHON="$(command -v python3)"
fi

REFRESH_LABEL="com.commandaudit.refresh"
WEB_LABEL="com.commandaudit.web"
REFRESH_PLIST="$LA_DIR/$REFRESH_LABEL.plist"
WEB_PLIST="$LA_DIR/$WEB_LABEL.plist"

# ---------- 生成 plist ----------
cat > "$REFRESH_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>$REFRESH_LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$SCRIPT_DIR/auto_refresh.sh</string>
    </array>
    <key>WorkingDirectory</key><string>$PROJECT_ROOT</string>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>ThrottleInterval</key><integer>30</integer>
    <key>StandardOutPath</key><string>$LOG_DIR/auto_refresh.log</string>
    <key>StandardErrorPath</key><string>$LOG_DIR/auto_refresh.log</string>
</dict>
</plist>
EOF

cat > "$WEB_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>$WEB_LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>$PROJECT_ROOT/src/app.py</string>
    </array>
    <key>WorkingDirectory</key><string>$PROJECT_ROOT</string>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>ThrottleInterval</key><integer>30</integer>
    <key>StandardOutPath</key><string>$LOG_DIR/flask.log</string>
    <key>StandardErrorPath</key><string>$LOG_DIR/flask.log</string>
</dict>
</plist>
EOF

echo "✓ 已生成 plist"
echo "  $REFRESH_PLIST"
echo "  $WEB_PLIST"

# ---------- 装进 launchd ----------
load_one() {
    local label="$1" plist="$2"
    launchctl bootout "gui/$UID_NUM/$label" > /dev/null 2>&1
    if launchctl bootstrap "gui/$UID_NUM" "$plist" > /dev/null 2>&1; then
        echo "✓ 已加载 $label"
    elif launchctl load -w "$plist" > /dev/null 2>&1; then
        echo "✓ 已加载 $label (load -w)"
    else
        echo "✗ 加载失败 $label"
        return 1
    fi
}

# 先清掉可能由 nohup 启动的同名进程，避免两个实例抢端口 / 重复写库
pkill -f "$PROJECT_ROOT/scripts/auto_refresh.sh" 2>/dev/null
pkill -f "$PROJECT_ROOT/src/app.py" 2>/dev/null
sleep 1

load_one "$REFRESH_LABEL" "$REFRESH_PLIST"
load_one "$WEB_LABEL" "$WEB_PLIST"

sleep 2
echo ""
echo "状态："
launchctl list | grep -E "$REFRESH_LABEL|$WEB_LABEL" || echo "  (未查到，请检查 $LOG_DIR 下的日志)"
echo ""
echo "报告地址: http://localhost:8000"
echo "查看状态: launchctl list | grep commandaudit"
