#!/bin/bash
# 命令审计系统 - 自动刷新（每 60 秒跑一次）
# 常驻循环：audit.py 把 commands.log 灌进 DynamoDB，generate_report.py 重新生成 HTML

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/data"

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

while true; do
    echo "=========="
    echo "$(date '+%Y-%m-%d %H:%M:%S') 开始刷新"
    "$PYTHON" "$PROJECT_ROOT/src/audit.py" 2>&1 | tail -3
    "$PYTHON" "$PROJECT_ROOT/src/generate_report.py" 2>&1 | tail -3
    sleep 60
done
