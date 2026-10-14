#!/usr/bin/env bash
# 本机打开酒局记账。手机要扫码时，用电脑的局域网 IP 访问，不要用 localhost。
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"
if [[ ! -d .venv ]]; then
  "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -r requirements.txt
mkdir -p data
export DRINKBOARD_SEED_DEMO="${DRINKBOARD_SEED_DEMO:-1}"
export DRINKBOARD_DOCS="${DRINKBOARD_DOCS:-1}"
export DRINKBOARD_HOST="${DRINKBOARD_HOST:-0.0.0.0}"
export DRINKBOARD_PORT="${DRINKBOARD_PORT:-8773}"
echo "打开 http://127.0.0.1:${DRINKBOARD_PORT}/"
echo "演示局口令在 data/demo-room.txt（只在本机，不要外传）"
exec python -m uvicorn app.main:app --host "$DRINKBOARD_HOST" --port "$DRINKBOARD_PORT" --reload
