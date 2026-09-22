#!/bin/bash
# 命令审计系统 - 把记录钩子幂等写入 shell 配置文件
#
# 重复执行安全：会先删掉旧的托管块，再写入新块（路径变了也能自动更新）。
# 执行后需要新开一个终端（或 source ~/.zshrc）才生效。

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_FILE="$SCRIPT_DIR/audit_setup.sh"

BEGIN_MARK="# >>> command-audit (managed block) >>>"
END_MARK="# <<< command-audit <<<"

install_into() {
    local rc="$1"
    [ -f "$rc" ] || touch "$rc"

    # 备份一次
    cp "$rc" "$rc.command-audit.bak" 2>/dev/null

    # 删除旧的托管块
    if grep -qF "$BEGIN_MARK" "$rc" 2>/dev/null; then
        local tmp
        tmp="$(mktemp "${TMPDIR:-/tmp}/audit_rc.XXXXXX")"
        awk -v b="$BEGIN_MARK" -v e="$END_MARK" '
            $0 == b { skip = 1; next }
            $0 == e { skip = 0; next }
            !skip   { print }
        ' "$rc" > "$tmp" && mv "$tmp" "$rc"
    fi

    # 去掉文件末尾多余空行，再追加新块
    local tmp2
    tmp2="$(mktemp "${TMPDIR:-/tmp}/audit_rc.XXXXXX")"
    awk 'BEGIN{n=0} {lines[n++]=$0} END{
        last=n-1
        while (last>=0 && lines[last]=="") last--
        for (i=0;i<=last;i++) print lines[i]
    }' "$rc" > "$tmp2" && mv "$tmp2" "$rc"

    {
        printf '\n%s\n' "$BEGIN_MARK"
        printf 'source "%s"\n' "$SETUP_FILE"
        printf '%s\n' "$END_MARK"
    } >> "$rc"

    echo "✓ 已写入 $rc"
}

TARGETS=()
if [ -f "$HOME/.zshrc" ] || [ "${SHELL:-}" = "/bin/zsh" ]; then
    TARGETS+=("$HOME/.zshrc")
fi
if [ -f "$HOME/.bashrc" ]; then
    TARGETS+=("$HOME/.bashrc")
fi
# Linux 上 bash 登录 shell 读 .bash_profile 而不是 .bashrc，有就一起装（各自幂等）
if [ -f "$HOME/.bash_profile" ]; then
    TARGETS+=("$HOME/.bash_profile")
fi
if [ ${#TARGETS[@]} -eq 0 ]; then
    TARGETS+=("$HOME/.zshrc")
fi

for rc in "${TARGETS[@]}"; do
    install_into "$rc"
done

echo ""
echo "钩子已安装。新开一个终端即生效；当前终端可执行： source ~/.zshrc"
echo "验证：随便跑一条命令，然后 tail -3 \"$(dirname "$SCRIPT_DIR")/data/commands.log\""
