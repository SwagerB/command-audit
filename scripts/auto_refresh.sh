#!/bin/bash
# 命令审计系统 - 自动刷新（每 60 秒跑一次）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/data"

mkdir -p "$LOG_DIR"

while true; do
    echo "=========="
    echo "$(date '+%Y-%m-%d %H:%M:%S') 开始刷新"
    python3 "$PROJECT_ROOT/src/audit.py" > /dev/null 2>&1
    python3 "$PROJECT_ROOT/src/generate_report.py"
    sleep 60
done