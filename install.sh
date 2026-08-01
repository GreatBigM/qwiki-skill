#!/usr/bin/env bash
# qwiki skill 一键安装脚本
# 用法: curl -fsSL https://raw.githubusercontent.com/GreatBigM/qwiki-skill/main/install.sh | bash
# 等价于手动复制，不经过 hermes skills install 的安全扫描
set -euo pipefail

REPO_URL="https://github.com/GreatBigM/qwiki-skill.git"
SKILL_NAME="qwiki"
SKILLS_DIR="${HOME}/.hermes/skills"
DEST="${SKILLS_DIR}/${SKILL_NAME}"

TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

echo "==> 克隆仓库（--depth 1）..."
git clone --depth 1 "${REPO_URL}" "${TMP}/repo" >/dev/null 2>&1 || {
    echo "❌ 克隆失败，请检查网络或仓库地址"; exit 1; }

echo "==> 检查安装目标..."
mkdir -p "${SKILLS_DIR}"
if [ -d "${DEST}" ]; then
    BAK="${DEST}.bak.$(date +%Y%m%d%H%M%S)"
    echo "    检测到已有安装，备份到 ${BAK}"
    mv "${DEST}" "${BAK}"
fi

echo "==> 安装到 ${DEST}"
mkdir -p "${DEST}"
cp "${TMP}/repo/SKILL.md" "${DEST}/"
cp -r "${TMP}/repo/templates" "${DEST}/"
cp -r "${TMP}/repo/references" "${DEST}/"

echo ""
echo "✅ qwiki skill 安装完成！"
echo "   新会话自动加载；当前会话执行 /reload-skills 生效"
echo ""
echo "快速开始：对 AI 说 \"qwiki init\" 初始化知识库"
