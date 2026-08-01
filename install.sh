#!/usr/bin/env bash
# qwiki skill 一键安装/更新脚本
# 用法: curl -fsSL https://raw.githubusercontent.com/GreatBigM/qwiki-skill/main/install.sh | bash
# 等价于手动复制，不经过 hermes skills install 的安全扫描
# 重复执行 = 更新（自动备份旧版 + 版本对比提示）
set -euo pipefail

REPO_URL="https://github.com/GreatBigM/qwiki-skill.git"
SKILL_NAME="qwiki"
SKILLS_DIR="${HOME}/.hermes/skills"
DEST="${SKILLS_DIR}/${SKILL_NAME}"

get_version() { grep -m1 '^version:' "$1" | sed 's/^version:[[:space:]]*//' | tr -d '"'\'' '; }

version_gt() { [ "$1" != "$2" ] && [ -n "$2" ] && [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -1)" = "$2" ]; }

TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

echo "==> 克隆仓库（--depth 1）..."
git clone --depth 1 "${REPO_URL}" "${TMP}/repo" >/dev/null 2>&1 || {
    echo "❌ 克隆失败，请检查网络或仓库地址"; exit 1; }

NEW_VERSION="$(get_version "${TMP}/repo/SKILL.md")"

echo "==> 检查安装目标..."
mkdir -p "${SKILLS_DIR}"
if [ -f "${DEST}/SKILL.md" ]; then
    OLD_VERSION="$(get_version "${DEST}/SKILL.md")"
    if [ -n "$OLD_VERSION" ] && [ -n "$NEW_VERSION" ]; then
        if version_gt "$NEW_VERSION" "$OLD_VERSION"; then
            echo "    发现新版本: v${OLD_VERSION} → v${NEW_VERSION}，正在升级..."
        elif [ "$OLD_VERSION" = "$NEW_VERSION" ]; then
            echo "    已是最新版本 v${NEW_VERSION}（重新安装，旧版备份保留）"
        else
            echo "    本地 v${OLD_VERSION} 高于远端 v${NEW_VERSION}（开发版，覆盖安装）"
        fi
    fi
    BAK="${DEST}.bak.$(date +%Y%m%d%H%M%S)"
    echo "    备份旧版到 ${BAK}"
    mv "${DEST}" "${BAK}"
else
    echo "    首次安装 v${NEW_VERSION}"
fi

echo "==> 安装到 ${DEST}"
mkdir -p "${DEST}"
cp "${TMP}/repo/SKILL.md" "${DEST}/"
cp -r "${TMP}/repo/templates" "${DEST}/"
cp -r "${TMP}/repo/references" "${DEST}/"
cp -r "${TMP}/repo/CHANGELOG.md" "${DEST}/"

echo ""
echo "✅ qwiki skill 安装完成！当前版本 v${NEW_VERSION}"
echo "   新会话自动加载；当前会话执行 /reload-skills 生效"
echo ""
echo "快速开始：对 AI 说 \"qwiki init\" 初始化知识库"
echo "更新：重跑本脚本即升级（自动备份旧版到 .bak.<时间戳>）"
