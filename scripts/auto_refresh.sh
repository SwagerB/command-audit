#!/bin/bash
# 命令审计系统 - 自动刷新
# 策略：盯着 commands.log 的修改时间，有新命令落盘立刻重新生成报告（约 2 秒内响应）；
#      另外每 60 秒兜底刷新一次（防挂钟/环境导致的漏检）。

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/data"
LOG_FILE="$LOG_DIR/commands.log"

mkdir -p "$LOG_DIR"

# 优先使用项目自带 venv 的 Python（保证 boto3 可用）
if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
    PYTHON="$(command -v python3)"
fi

# 与 start_audit.sh 保持一致的环境变量（脚本被单独拉起时也能工作）
export AWS_ENDPOINT_URL="${AWS_ENDPOINT_URL:-http://localhost:4566}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"
export AUDIT_DDB_TABLE="${AUDIT_DDB_TABLE:-AuditLogs}"
export AUDIT_S3_BUCKET="${AUDIT_S3_BUCKET:-audit-reports-2026}"

# 取文件 mtime：Linux 用 stat -c %Y，macOS 用 stat -f %m
get_mtime() {
    if [ -f "$LOG_FILE" ]; then
        stat -c %Y "$LOG_FILE" 2>/dev/null || stat -f %m "$LOG_FILE" 2>/dev/null || echo 0
    else
        echo 0
    fi
}

do_refresh() {
    echo "=========="
    echo "$(date '+%Y-%m-%d %H:%M:%S') 开始刷新"
    "$PYTHON" "$PROJECT_ROOT/src/audit.py" 2>&1 | tail -3
    "$PYTHON" "$PROJECT_ROOT/src/generate_report.py" 2>&1 | tail -3
}

last_mtime="$(get_mtime)"
last_refresh=0

while true; do
    now="$(date +%s)"
    mtime="$(get_mtime)"

    if [ "$mtime" != "$last_mtime" ]; then
        last_mtime="$mtime"
        do_refresh
        last_refresh="$now"
        sleep 3        # 防抖：连续多条命令只多补刷一次
        continue
    fi

    # 兜底：超过 60 秒没刷过就刷一次
    if [ $((now - last_refresh)) -ge 60 ]; then
        do_refresh
        last_refresh="$now"
    fi

    sleep 2
done
