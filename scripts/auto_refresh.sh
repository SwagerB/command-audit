#!/bin/bash
# 命令审计系统 - 自动刷新（每 60 秒跑一次）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/data"

mkdir -p "$LOG_DIR"

# 优先使用项目自带 venv 的 Python
if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
    PYTHON="$(command -v python3)"
fi

while true; do
    echo "=========="
    echo "$(date '+%Y-%m-%d %H:%M:%S') 开始刷新"
    "$PYTHON" "$PROJECT_ROOT/src/audit.py" > /dev/null 2>&1
    "$PYTHON" "$PROJECT_ROOT/src/generate_report.py"
    sleep 60
done