#!/usr/bin/env bash
# 从这台电脑把 DrinkBoard 推到现有阿里云 ECS。
# PEM 用 --pem 或 DRINKBOARD_PEM。不要把 highway.pem 放进本仓库。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT/.." && pwd)"
PEM="${DRINKBOARD_PEM:-}"
SSH_HOST="${DRINKBOARD_SSH_HOST:-root@8.130.110.101}"
REMOTE_APP=/opt/drinkboard

usage() {
  echo "用法: deploy/deploy.sh --pem /path/to/highway.pem [--host root@8.130.110.101]"
  echo "或: DRINKBOARD_PEM=/path/to/highway.pem deploy/deploy.sh"
  echo "密钥通常在 SkillPoint 仓库 IdeaProj/WebSite/highway.pem"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pem)
      PEM="${2:-}"
      shift 2
      ;;
    --host)
      SSH_HOST="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$PEM" ]]; then
  candidates=(
    "$HOME/SkillPoint/IdeaProj/WebSite/highway.pem"
    "$HOME/code/SkillPoint/IdeaProj/WebSite/highway.pem"
    "$HOME/src/SkillPoint/IdeaProj/WebSite/highway.pem"
  )
  for candidate in "${candidates[@]}"; do
    if [[ -f "$candidate" ]]; then
      PEM="$candidate"
      break
    fi
  done
fi

if [[ -z "$PEM" || ! -f "$PEM" ]]; then
  echo "找不到 PEM。用 --pem 或 DRINKBOARD_PEM 指向 SkillPoint/IdeaProj/WebSite/highway.pem" >&2
  echo "不要把 pem 拷进本仓库。" >&2
  exit 1
fi

PEM_REAL="$(realpath "$PEM")"
REPO_REAL="$(realpath "$REPO_ROOT")"
if [[ "$PEM_REAL" == "$REPO_REAL"* ]]; then
  echo "PEM 在本仓库里面，拒绝使用。密钥留在 SkillPoint 仓库。" >&2
  exit 1
fi

perm="$(stat -c %a "$PEM_REAL" 2>/dev/null || stat -f %OLp "$PEM_REAL")"
if [[ "$perm" != "600" && "$perm" != "400" ]]; then
  echo "警告: PEM 权限是 $perm，建议 chmod 600" >&2
fi

SSH=(ssh -i "$PEM_REAL" -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes)
RSYNC=(rsync -az --delete
  --exclude .venv
  --exclude data
  --exclude __pycache__
  --exclude .pytest_cache
  --exclude .env
  --exclude demo-room.txt
  --exclude '*.pem'
  -e "ssh -i $PEM_REAL -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes")

"${SSH[@]}" "$SSH_HOST" "mkdir -p $REMOTE_APP"
"${RSYNC[@]}" "$ROOT/" "$SSH_HOST:$REMOTE_APP/"
"${SSH[@]}" "$SSH_HOST" "bash $REMOTE_APP/deploy/remote-install.sh"
