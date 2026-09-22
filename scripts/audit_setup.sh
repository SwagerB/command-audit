#!/bin/bash
# 命令审计系统 - 环境初始化
#
# 推荐用法（自动写入 rc 文件，幂等）：
#     bash scripts/install_hooks.sh
#
# 手动用法：在 ~/.zshrc 或 ~/.bashrc 里加一行：
#     source /path/to/command-audit/scripts/audit_setup.sh
#
# 本脚本同时兼容 zsh 与 bash，重复 source 不会重复注册钩子。

# ============ 1. 定位项目根目录 ============
if [ -n "${ZSH_VERSION:-}" ]; then
    _AUDIT_SELF="${(%):-%x}"
elif [ -n "${BASH_SOURCE[0]:-}" ]; then
    _AUDIT_SELF="${BASH_SOURCE[0]}"
else
    _AUDIT_SELF="$0"
fi
_AUDIT_SCRIPT_DIR="$(cd "$(dirname "$_AUDIT_SELF")" 2>/dev/null && pwd)"
export AUDIT_PROJECT_ROOT="$(dirname "$_AUDIT_SCRIPT_DIR")"
export AUDIT_LOG_DIR="${AUDIT_LOG_DIR:-$AUDIT_PROJECT_ROOT/data}"
AUDIT_LOG_FILE="$AUDIT_LOG_DIR/commands.log"

[ -d "$AUDIT_LOG_DIR" ] || mkdir -p "$AUDIT_LOG_DIR" 2>/dev/null

# ============ 2. 写日志（带自身过滤，避免自记录） ============
__audit_write() {
    local ec="$1" cmd="$2"
    [ -n "$cmd" ] || return 0
    [ -d "$AUDIT_LOG_DIR" ] || return 0
    case "$cmd" in
        *__audit_write*|*__audit_log_command*|*__audit_precmd*|*__audit_preexec*) return 0 ;;
        source\ *audit_setup.sh*|.\ *audit_setup.sh*) return 0 ;;
    esac
    printf '%s|%d|%s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$ec" "$cmd" >> "$AUDIT_LOG_FILE" 2>/dev/null
}

# ============ 3. 按 shell 注册钩子 ============
# 本脚本可能被 set -u 的 shell source（例如 start_audit.sh），
# 下面会引用若干“可能未定义”的变量，先临时关掉 -u，结束时恢复。
__audit_u_was_set=""
case "$-" in *u*) __audit_u_was_set="1" ;; esac
set +u

if [ -n "${ZSH_VERSION:-}" ]; then
    # ---- zsh：preexec 抓命令原文，precmd 抓退出码 ----
    __audit_preexec() { __AUDIT_PENDING_CMD="${1//$'\n'/ }"; }

    __audit_precmd() {
        local ec=$?                      # 必须是第一条语句，否则 $? 被覆盖
        if [ -n "${__AUDIT_PENDING_CMD:-}" ]; then
            __audit_write "$ec" "$__AUDIT_PENDING_CMD"
            __AUDIT_PENDING_CMD=""
        fi
    }

    # 放在钩子数组最前面：保证 $? 还没被其它 precmd 钩子覆盖
    # ${arr:#fn} 去掉数组里已有的同名项，实现幂等
    precmd_functions=(__audit_precmd ${precmd_functions:#__audit_precmd})
    preexec_functions=(__audit_preexec ${preexec_functions:#__audit_preexec})
else
    # ---- bash：PROMPT_COMMAND 取历史里的上一条 + $? ----
    __audit_log_command() {
        local ec=$?
        local cmd
        cmd="$(HISTTIMEFORMAT='' builtin history 1 2>/dev/null | sed 's/^[[:space:]]*[0-9]*[[:space:]]*//')"
        [ -n "$cmd" ] || cmd="$(fc -ln -1 2>/dev/null | sed 's/^[[:space:]]*//')"
        __audit_write "$ec" "$cmd"
    }

    case "${PROMPT_COMMAND:-}" in
        *__audit_log_command*) ;;   # 已注册，跳过
        "") PROMPT_COMMAND="__audit_log_command" ;;
        *)  PROMPT_COMMAND="__audit_log_command;${PROMPT_COMMAND}" ;;
    esac
fi

# 恢复调用方原来的 -u 设置
[ -n "$__audit_u_was_set" ] && set -u
unset __audit_u_was_set
