#!/bin/bash
# 命令审计系统 - 卸载 launchd 托管的常驻服务

set -u

UID_NUM="$(id -u)"
LA_DIR="$HOME/Library/LaunchAgents"

for label in com.commandaudit.refresh com.commandaudit.web; do
    if launchctl bootout "gui/$UID_NUM/$label" > /dev/null 2>&1; then
        echo "✓ 已停止 $label"
    else
        launchctl unload -w "$LA_DIR/$label.plist" > /dev/null 2>&1 \
          && echo "✓ 已停止 $label (unload)" \
          || echo "○ $label 未在运行"
    fi
    rm -f "$LA_DIR/$label.plist"
done

echo "plist 已删除，服务不会再自启。"
