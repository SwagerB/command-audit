#!/bin/bash
# 命令审计系统 - 环境初始化
# 用法：在 .bashrc 里加一行 source /path/to/command-audit/scripts/audit_setup.sh

# 自动定位项目根目录（脚本在 <project>/scripts/ 下）
_AUDIT_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export AUDIT_PROJECT_ROOT="$(dirname "$_AUDIT_SCRIPT_DIR")"
export AUDIT_LOG_DIR="$AUDIT_PROJECT_ROOT/data"

mkdir -p "$AUDIT_LOG_DIR"

# 记录每条命令的退出码和内容
__audit_log_command() {
    local ec=$?
    local cmd
    cmd=$(fc -ln -1 2>/dev/null | sed 's/^[[:space:]]*//')
    if [ -n "$cmd" ] && [ "$cmd" != "__audit_log_command" ]; then
        printf "%s|%d|%s\n" "$(date "+%Y-%m-%d %H:%M:%S")" "$ec" "$cmd" >> "$AUDIT_LOG_DIR/commands.log"
    fi
}
PROMPT_COMMAND="__audit_log_command"