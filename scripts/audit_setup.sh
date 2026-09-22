#!/bin/bash
# 命令审计系统 - 环境初始化
# 用法：
#   bash: 在 .bashrc 里加  source /path/to/command-audit/scripts/audit_setup.sh
#   zsh : 在 .zshrc  里加  source /path/to/command-audit/scripts/audit_setup.sh
# 脚本自动识别当前 shell（bash 用 PROMPT_COMMAND，zsh 用 precmd）

# 自动定位项目根目录（脚本在 <project>/scripts/ 下）
_AUDIT_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-${(%):-%x}}")" 2>/dev/null && pwd)" || \
_AUDIT_SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export AUDIT_PROJECT_ROOT="$(dirname "$_AUDIT_SCRIPT_DIR")"
export AUDIT_LOG_DIR="$AUDIT_PROJECT_ROOT/data"

mkdir -p "$AUDIT_LOG_DIR"

# 记录每条命令的退出码和内容（bash / zsh 通用）
__audit_log_command() {
    local ec=$?
    local cmd=""
    if [ -n "$ZSH_VERSION" ]; then
        # zsh: 从历史取上一条命令
        cmd=$(fc -ln -1 2>/dev/null | sed 's/^[[:space:]]*//')
    else
        cmd=$(fc -ln -1 2>/dev/null | sed 's/^[[:space:]]*//')
    fi
    if [ -n "$cmd" ] && [ "$cmd" != "__audit_log_command" ] && [[ "$cmd" != *"audit_log_command"* ]]; then
        printf "%s|%d|%s\n" "$(date "+%Y-%m-%d %H:%M:%S")" "$ec" "$cmd" >> "$AUDIT_LOG_DIR/commands.log"
    fi
}

if [ -n "$ZSH_VERSION" ]; then
    # zsh：注册 precmd 钩子（避免重复注册）
    if ! typeset -f precmd | grep -q "__audit_log_command"; then
        precmd() { __audit_log_command; }
    fi
else
    # bash：PROMPT_COMMAND 追加（避免重复注册）
    case "$PROMPT_COMMAND" in
        *__audit_log_command*) ;;
        "" ) PROMPT_COMMAND="__audit_log_command" ;;
        * ) PROMPT_COMMAND="$PROMPT_COMMAND;__audit_log_command" ;;
    esac
fi
