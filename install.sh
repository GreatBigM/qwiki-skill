#!/usr/bin/env bash
# qwiki skill 一键安装/更新脚本（多 agent 目标）
# 用法:
#   交互选择: curl -fsSL https://gitee.com/GreatBigM/qwiki-skill/raw/main/install.sh -o /tmp/install.sh && bash /tmp/install.sh
#   指定目标: curl -fsSL https://gitee.com/GreatBigM/qwiki-skill/raw/main/install.sh | bash -s -- --target hermes,claude
#   全部目标: curl -fsSL https://gitee.com/GreatBigM/qwiki-skill/raw/main/install.sh | bash -s -- --all
# 等价于手动复制，不经过安全扫描。重复执行 = 更新（自动备份旧版 + 版本对比）
# 镜像: github.com/GreatBigM/qwiki-skill（海外备选）
set -euo pipefail

REPO_URL="https://gitee.com/GreatBigM/qwiki-skill.git"
SKILL_NAME="qwiki"
COPY_DIRS="templates references"   # 除 SKILL.md/CHANGELOG.md 外需拷贝的目录

get_version() { grep -m1 '^version:' "$1" 2>/dev/null | sed 's/^version:[[:space:]]*//' | tr -d '"'\'' ' || true; }
version_gt() { [ "$1" != "$2" ] && [ -n "$2" ] && [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -1)" = "$2" ]; }

# ─── 参数解析 ──────────────────────────────────────────────────────
TARGET_ARG=""
ALL_FLAG=0
for a in "$@"; do
    case "$a" in
        --target=*) TARGET_ARG="${a#*=}" ;;
        --target) TARGET_ARG="" ;;  # 由下一参数接管（简化：仅支持 --target=a,b 形式）
        --all) ALL_FLAG=1 ;;
    esac
done

# ─── 目标探测：检测本机已安装的 agent ───────────────────────────────
detect_targets() {
    TARGETS=()   # 格式: 名称|目录|CLI
    if [ -x "$(command -v hermes 2>/dev/null)" ]; then TARGETS+=("hermes|${HOME}/.hermes/skills|Hermes"); fi
    if [ -x "$(command -v claude 2>/dev/null)" ]; then TARGETS+=("claude|${HOME}/.claude/skills|Claude Code"); fi
    if [ -x "$(command -v codex 2>/dev/null)" ]; then TARGETS+=("codex|${HOME}/.codex/skills|Codex"); fi
    # Cursor 用 skills-cursor 插件结构，暂不支持；其余 agent 未探测到
    if [ "${#TARGETS[@]}" -eq 0 ]; then
        TARGETS+=("hermes|${HOME}/.hermes/skills|Hermes(默认)")
    fi
}

# ─── 单目标安装（版本对比 + 备份 + 拷贝）─────────────────────────────
install_one() {
    local name="$1" dest_dir="$2" label="$3"
    local dest="${dest_dir}/${SKILL_NAME}"

    echo ""
    echo "── 安装到 ${label} (${dest}) ──"
    mkdir -p "${dest_dir}"

    if [ -f "${dest}/SKILL.md" ]; then
        local old_v new_v
        old_v="$(get_version "${dest}/SKILL.md")"
        new_v="$NEW_VERSION"
        if [ -n "$old_v" ] && [ -n "$new_v" ]; then
            if version_gt "$new_v" "$old_v"; then
                echo "    发现新版本: v${old_v} → v${new_v}，正在升级..."
            elif [ "$old_v" = "$new_v" ]; then
                echo "    已是最新版本 v${new_v}（重新安装，旧版备份保留）"
            else
                echo "    本地 v${old_v} 高于远端 v${new_v}（开发版，覆盖安装）"
            fi
        fi
        local bak="${dest}.bak.$(date +%Y%m%d%H%M%S)"
        echo "    备份旧版到 ${bak}"
        mv "${dest}" "${bak}"
    else
        echo "    首次安装 v${NEW_VERSION}"
    fi

    mkdir -p "${dest}"
    cp "${TMP}/repo/SKILL.md" "${dest}/"
    for d in ${COPY_DIRS}; do
        [ -d "${TMP}/repo/${d}" ] && cp -r "${TMP}/repo/${d}" "${dest}/"
    done
    cp "${TMP}/repo/CHANGELOG.md" "${dest}/" 2>/dev/null || true
    echo "    ✅ ${label}: ${SKILL_NAME} 已安装"
}

# ─── 主流程 ────────────────────────────────────────────────────────
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

echo "==> 克隆仓库（--depth 1）..."
git clone --depth 1 "${REPO_URL}" "${TMP}/repo" >/dev/null 2>&1 || {
    echo "❌ 克隆失败，请检查网络或仓库地址"; exit 1; }
NEW_VERSION="$(get_version "${TMP}/repo/SKILL.md")"
echo "    远端版本 v${NEW_VERSION}"

detect_targets

echo ""
echo "==> 检测到本机 agent:"
for i in "${!TARGETS[@]}"; do
    name="${TARGETS[$i]%%|*}"; dir="${TARGETS[$i]#*|}"; dir="${dir%%|*}"
    state="➕ 未安装"
    [ -f "${dir}/${SKILL_NAME}/SKILL.md" ] && state="✅ 已装 v$(get_version "${dir}/${SKILL_NAME}/SKILL.md")"
    echo "    [$((i+1))] ${TARGETS[$i]##*|}  (${dir})  ${state}"
done

# ─── 目标选择 ──────────────────────────────────────────────────────
SELECTED=()
if [ "$ALL_FLAG" -eq 1 ]; then
    SELECTED=("${TARGETS[@]}")
elif [ -n "$TARGET_ARG" ]; then
    IFS=',' read -ra want <<< "$TARGET_ARG"
    for w in "${want[@]}"; do
        for t in "${TARGETS[@]}"; do
            [ "${t%%|*}" = "$w" ] && SELECTED+=("$t")
        done
    done
    [ "${#SELECTED[@]}" -eq 0 ] && { echo "❌ 未知目标: $TARGET_ARG（可用: hermes/claude/codex）"; exit 1; }
elif [ -t 0 ]; then
    # 交互模式（stdin 是终端）
    echo ""
    read -rp "选择安装目标（逗号分隔如 1,2 / 1-3 / 回车=全部 / q=退出）: " choice
    if [ "${choice,,}" = "q" ]; then echo "已取消"; exit 0; fi
    if [ -z "$choice" ]; then
        SELECTED=("${TARGETS[@]}")
    else
        IFS=', ' read -ra parts <<< "$choice"
        for p in "${parts[@]}"; do
            if [[ "$p" =~ ^[0-9]+-[0-9]+$ ]]; then
                a="${p%-*}"; b="${p#*-}"
                for ((n=a; n<=b; n++)); do
                    [ "$n" -ge 1 ] && [ "$n" -le "${#TARGETS[@]}" ] && SELECTED+=("${TARGETS[$((n-1))]}")
                done
            elif [[ "$p" =~ ^[0-9]+$ ]] && [ "$p" -ge 1 ] && [ "$p" -le "${#TARGETS[@]}" ]; then
                SELECTED+=("${TARGETS[$((p-1))]}")
            fi
        done
        [ "${#SELECTED[@]}" -eq 0 ] && { echo "❌ 无效选择"; exit 1; }
    fi
else
    # 管道模式（stdin 非终端）: 默认全部
    echo ""
    echo "==> 非交互模式（管道执行），默认安装到全部目标"
    SELECTED=("${TARGETS[@]}")
fi

# ─── 执行安装 ──────────────────────────────────────────────────────
for t in "${SELECTED[@]}"; do
    name="${t%%|*}"
    rest="${t#*|}"; dir="${rest%%|*}"
    label="${t##*|}"
    install_one "$name" "$dir" "$label"
done

echo ""
echo "✅ ${SKILL_NAME} v${NEW_VERSION} 安装完成！"
echo "   - Hermes: 新会话自动加载，当前会话 /reload-skills 生效"
echo "   - Claude Code / Codex: 新会话自动加载"
echo ""
echo "快速开始：对 AI 说 \"qwiki init\" 初始化知识库"
echo "更新：重跑本脚本即升级（自动备份旧版到 .bak.<时间戳>）"
echo "指定目标：bash install.sh --target hermes,claude  或  --all"
