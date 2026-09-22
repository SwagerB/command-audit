#!/bin/bash
# 命令审计系统 - 一键启动
# 启动：环境变量 + 命令记录钩子 + 自动刷新 + Flask 服务
#
# 可重复执行：已在跑的进程不会重复启动

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/data"

mkdir -p "$LOG_DIR"

# ---------- 0. 选 Python：优先项目自带 venv（保证 boto3 / flask 可用）----------
if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    export AUDIT_PYTHON="$PROJECT_ROOT/.venv/bin/python"
else
    export AUDIT_PYTHON="$(command -v python3)"
fi

# ---------- 1. 环境变量（默认适配 LocalStack，外部已设置的不覆盖）----------
export AWS_ENDPOINT_URL="${AWS_ENDPOINT_URL:-http://localhost:4566}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"
export AUDIT_DDB_TABLE="${AUDIT_DDB_TABLE:-AuditLogs}"
export AUDIT_S3_BUCKET="${AUDIT_S3_BUCKET:-audit-reports-2026}"

# ---------- 2. 安装命令记录钩子（写进 ~/.zshrc / ~/.bashrc，幂等）----------
bash "$SCRIPT_DIR/install_hooks.sh"

# 当前进程内也生效一份（用于本脚本后续产物）
source "$SCRIPT_DIR/audit_setup.sh"

# ---------- 3. 自动刷新（按项目路径判断，避免误判其它副本的进程）----------
if ! pgrep -f "$PROJECT_ROOT/scripts/auto_refresh.sh" > /dev/null 2>&1; then
    nohup bash "$PROJECT_ROOT/scripts/auto_refresh.sh" \
      > "$LOG_DIR/auto_refresh.log" 2>&1 &
    echo "✓ 自动刷新已启动 (pid $!)"
else
    echo "○ 自动刷新已在运行"
fi

# ---------- 4. Flask 服务 ----------
if ! pgrep -f "$PROJECT_ROOT/src/app.py" > /dev/null 2>&1; then
    if lsof -nP -iTCP:"${APP_PORT:-8000}" -sTCP:LISTEN > /dev/null 2>&1; then
        echo "⚠ 端口 ${APP_PORT:-8000} 已被占用，Flask 未启动（可能是另一个副本在跑）"
    else
        nohup "$AUDIT_PYTHON" "$PROJECT_ROOT/src/app.py" \
          > "$LOG_DIR/flask.log" 2>&1 &
        echo "✓ Flask 服务已启动 (pid $!)"
    fi
else
    echo "○ Flask 服务已在运行"
fi

echo ""
echo "报告地址: http://localhost:${APP_PORT:-8000}"
echo "日志目录: $LOG_DIR"
echo "命令记录: $LOG_DIR/commands.log"
