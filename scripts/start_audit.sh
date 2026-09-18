#!/bin/bash
# 命令审计系统 - 一键启动
# 启动：命令记录 + 自动刷新 + Flask 服务

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/data"

mkdir -p "$LOG_DIR"

# 1. 启用命令记录
source "$PROJECT_ROOT/scripts/audit_setup.sh"

# 2. 启动自动刷新（如果没在跑）
if ! pgrep -f "auto_refresh.sh" > /dev/null; then
    nohup bash "$PROJECT_ROOT/scripts/auto_refresh.sh" \
      > "$LOG_DIR/auto_refresh.log" 2>&1 &
    echo "✓ 自动刷新已启动"
else
    echo "○ 自动刷新已在运行"
fi

# 3. 启动 Flask 服务（如果没在跑）
if ! pgrep -f "src/app.py" > /dev/null; then
    nohup python3 "$PROJECT_ROOT/src/app.py" \
      > "$LOG_DIR/flask.log" 2>&1 &
    echo "✓ Flask 服务已启动"
else
    echo "○ Flask 服务已在运行"
fi

echo ""
echo "报告地址: http://localhost:8000"
echo "日志目录: $LOG_DIR"