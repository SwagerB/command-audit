export AUDIT_LOG_DIR="/root/audit_logs"
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
