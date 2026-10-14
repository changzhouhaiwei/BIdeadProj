#!/usr/bin/env bash
# 在 ECS 上执行。deploy.sh 会先把代码同步过去再调用本脚本。
set -euo pipefail

APP=/opt/drinkboard
WWW=/var/www/fvxpcue/drink
DATA=/var/lib/drinkboard

if ! id drinkboard >/dev/null 2>&1; then
  useradd --system --home-dir "$DATA" --shell /usr/sbin/nologin drinkboard
fi

mkdir -p "$DATA/backups" "$WWW"
if [[ ! -f "$DATA/drinks.json" ]]; then
  cp "$APP/config/drinks.json" "$DATA/drinks.json"
fi
if [[ ! -f /etc/drinkboard.env ]]; then
  cp "$APP/deploy/drinkboard.env.example" /etc/drinkboard.env
  chmod 600 /etc/drinkboard.env
fi

if [[ ! -x "$APP/.venv/bin/python" ]]; then
  if ! python3 -m venv "$APP/.venv"; then
    echo "python3-venv 没装。先执行: apt-get update && apt-get install -y python3-venv python3-pip" >&2
    exit 1
  fi
fi
"$APP/.venv/bin/pip" install -r "$APP/requirements.txt"

rm -rf "$WWW"
mkdir -p "$WWW"
cp -a "$APP/frontend/." "$WWW/"
cp "$APP/deploy/drinkboard.service" /etc/systemd/system/drinkboard.service
mkdir -p /etc/nginx/snippets
cp "$APP/deploy/nginx-drink.conf" /etc/nginx/snippets/drinkboard.conf

chown -R drinkboard:drinkboard "$DATA" "$APP"
chmod -R a+rX "$WWW"

set +e
patch_line="$(python3 "$APP/deploy/patch_nginx.py")"
patch_code=$?
set -e
echo "$patch_line"
status="${patch_line%% *}"
if [[ "$patch_code" -eq 0 && "$status" == "patched" ]]; then
  if ! nginx -t; then
    conf="${patch_line#patched }"
    if [[ -f "${conf}.bak-drinkboard" ]]; then
      cp "${conf}.bak-drinkboard" "$conf"
    fi
    echo "nginx -t 没过，已把站点配置退回去。服务仍会启动，请手工加上 include。" >&2
  else
    systemctl reload nginx || nginx -s reload
  fi
elif [[ "$patch_code" -eq 0 && "$status" == "already" ]]; then
  nginx -t
  systemctl reload nginx || nginx -s reload
else
  echo "没找到带 /var/www/fvxpcue 的站点。请在对应 server 里加上：" >&2
  echo "    include /etc/nginx/snippets/drinkboard.conf;" >&2
fi

systemctl daemon-reload
systemctl enable drinkboard
systemctl restart drinkboard
curl -fsS http://127.0.0.1:8773/api/health
echo
echo "静态目录 $WWW"
echo "对外页面 http://8.130.110.101/drink/"
