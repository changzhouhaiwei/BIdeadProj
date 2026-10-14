# 酒局记账

扫一个码，进同一局。大家各自报个昵称，然后一起记今晚喝了多少。谁都能改谁的量，榜按纯酒精克数排。

页面是中文，手机优先，微信里打开也能用。不用登录。

## 纯酒精怎么算

酒精度按体积分数（ABV）。4° 就是 4%。

```text
纯酒精毫升 = 饮用量毫升 × 酒精度 / 100
纯酒精克   = 纯酒精毫升 × 0.789
```

`0.789` 是乙醇在大约 20℃ 的密度，单位 g/ml。榜单按克从高到低。克数一样时，名次并列，下一名跳号。每一笔都会记下当时的酒精度，之后改酒单不会把旧账重算一遍。

| 酒 | 喝下去 | 纯酒精 | 克 |
| --- | --- | --- | --- |
| 4° 啤酒 | 500 ml | 20.00 ml | 15.78 g |
| 12° 红酒 | 150 ml | 18.00 ml | 14.20 g |
| 42° 白酒 | 50 ml | 21.00 ml | 16.57 g |
| 53° 白酒 | 30 ml | 15.90 ml | 12.55 g |

「今天」按 `Asia/Shanghai` 的日历日切，不是开局之后的 24 小时。过了上海时间零点，今日榜换一天，历史榜照旧累加。

默认酒单：

- 4° 啤酒，每次 100 ml，快捷 330 / 500
- 12° 红酒，每次 50 ml，快捷 50 / 100 / 150
- 42° 白酒，每次 10 ml，快捷 20 / 50 / 100
- 53° 白酒，每次 10 ml，快捷 20 / 50 / 100

## 一局里有什么

局主创建房间后，页面亮出二维码。二维码里是当前网址，带上猜不中的房间 id 和加入口令，例如：

```text
http://8.130.110.101/drink/?room=<房间id>&k=<加入口令>
```

扫进来的人先起昵称（1 到 16 个字，这一局里不能重名）。浏览器会顺手记下这台设备的信息：User-Agent、平台、屏幕大小、语言、粗略类型（手机 / 平板 / 电脑）。牌面上只显示类型。完整信息只有局主口令能看。

进了局就能给任何人加减毫升。每次改动留下谁改的、改了谁、哪种酒、加减多少、上海时间。改动量在 1 到 5000 毫升，单项一天不超过 20000，不能减成负数。也可以补记最近 60 天里的某一天；补记只进历史榜，不动今天的榜。

局主口令只在创建时出现一次，存在这台设备里，服务器只留它的 SHA-256。丢了就改不了酒单，已经在局里的人还能继续记账。可选的环境变量 `DRINKBOARD_ADMIN_TOKEN` 是全局口令，能代管每一局，也能触发备份接口。线上可以留空。

页面大约每 3 秒拉一次最新牌面。接口在内存里按 IP 限流（创建大约每小时 20 次，加入每小时 60 次，写入每分钟 120 次，读取每分钟 90 次）。浏览器跨域只放行配置里的源，不使用 `*`。响应带 `Referrer-Policy: no-referrer`，避免带口令的网址被带到别的网站。

## 本地跑

```bash
cd DrinkBoard
bash scripts/run.sh
```

脚本会建 `.venv`、装依赖，并打开演示局（`DRINKBOARD_SEED_DEMO=1`）。浏览器打开 `http://127.0.0.1:8773/`。演示局的房间 id 和口令写在 `data/demo-room.txt`，权限 600，不要外传，也不要提交。

给旁边的手机扫时，不要用 localhost 打开局主页。用电脑的局域网 IP 打开，例如 `http://192.168.1.20:8773/`，再亮码。手机和电脑要在同一网络。

也可以：

```bash
cd DrinkBoard
docker compose up --build
```

这是本机演示。线上不要用这份 compose 把 8773 暴露到公网。

跑测试：

```bash
cd DrinkBoard
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest
```

测试覆盖开房、扫码链接进同一局、互相改量、克数、上海时区零点、改酒精度不改旧账、清空一天、酒单文件重载、二维码内容、限流和跨域。不需要连真的 ECS。

## 改酒单

不用改代码。两种办法：

1. 改配置文件。本地是 `config/drinks.json`，服务器上是 `/var/lib/drinkboard/drinks.json`（部署不会覆盖已经存在的这一份）。新开的局会抄这份文件。已经开的局，局主在亮码页点「按服务器上的配置重载」。文件里没有的酒会从牌面上拿掉，旧记录还在，克数仍按记账时的酒精度算。
2. 局主在亮码页里直接改名字、度数、每次加减和快捷毫升，点保存。这只写进这一局的数据库。

配置形状：

```json
{
  "default_title": "今晚酒局",
  "drinks": [
    {"key": "beer_4", "name": "4° 啤酒", "abv": 4, "step_ml": 100, "presets_ml": [330, 500]}
  ]
}
```

`key` 用小写字母、数字和下划线，创建后别改，不然新旧记录会在榜上分成两行。度数要大于 0、不超过 100。

## 清空某一天

亮码页的「清空今天」会删掉这一局、这一天（上海日期）的毫升，别的日子还在。牌面的改动列表里会留一句「清空了某天的记录」。

接口（需要局主口令或全局口令）：

```bash
curl -sS -X POST "http://127.0.0.1:8773/api/rooms/$ROOM/reset-day" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: $ADMIN" \
  -d '{"date":"2026-10-14"}'
```

人在服务器上、拿得到数据库文件时，也可以不走网页：

```bash
set -a; source /etc/drinkboard.env; set +a
/opt/drinkboard/.venv/bin/python /opt/drinkboard/scripts/reset_day.py \
  --room "$ROOM" --date 2026-10-14 --yes
```

不加 `--yes` 只打印将要删多少条。

## 备份

数据库是 SQLite，默认：

- 本机：`DrinkBoard/data/drinkboard.sqlite3`
- 服务器：`/var/lib/drinkboard/drinkboard.sqlite3`
- 备份目录：`/var/lib/drinkboard/backups`（本机是 `data/backups`）

热备份用 SQLite 的 backup API，默认留最近 14 份：

```bash
set -a; source /etc/drinkboard.env; set +a
/opt/drinkboard/.venv/bin/python /opt/drinkboard/scripts/backup.py
```

每天跑的例子在 `deploy/backup.cron`，可以放到 `/etc/cron.d/drinkboard`。

设了 `DRINKBOARD_ADMIN_TOKEN` 之后，也可以 `POST /api/admin/backup`。单局的局主口令不能触发这个接口。

## 部署到现有站点

公网页面：`http://8.130.110.101/drink/`

接口：`http://8.130.110.101/drink/api/`，反代到本机 `127.0.0.1:8773`。不要把 8773 对公网开放。现有端口 8765–8772 已经有别的服务，喝酒用 8773。

| 东西 | 位置 |
| --- | --- |
| 静态文件 | `/var/www/fvxpcue/drink/` |
| 程序 | `/opt/drinkboard` |
| 数据 | `/var/lib/drinkboard` |
| 环境变量 | `/etc/drinkboard.env`（权限 600） |
| systemd | `drinkboard.service` |
| Nginx | `/etc/nginx/snippets/drinkboard.conf` |

密钥在另一个仓库：`SkillPoint/IdeaProj/WebSite/highway.pem`。用参数或环境变量指过去，不要拷进本仓库。

```bash
cd DrinkBoard
DRINKBOARD_PEM=/path/to/SkillPoint/IdeaProj/WebSite/highway.pem bash deploy/deploy.sh
```

也可以 `bash deploy/deploy.sh --pem /path/to/highway.pem`。默认 SSH 是 `root@8.130.110.101`。脚本会拒绝放在本仓库目录里的 PEM。

它会同步代码、建 `drinkboard` 用户和虚拟环境、把前端拷到 Nginx 目录、安装 systemd，并尝试在带 `/var/www/fvxpcue` 的站点里插入：

```nginx
include /etc/nginx/snippets/drinkboard.conf;
```

找不到站点时，服务仍会起来，需要手工把上面这一行放进对应的 `server { }`，再 `nginx -t && systemctl reload nginx`。

反代这一段是：

```nginx
location /drink/api/ {
    proxy_pass http://127.0.0.1:8773/api/;
}
```

`/drink/api/health` 会转到 `127.0.0.1:8773/api/health`。`proxy_pass` 末尾的 `/api/` 不要随便删，删了路径会拼错。

第一次部署会从示例生成 `/etc/drinkboard.env`。之后部署不会覆盖它，也不会覆盖已经放在 `/var/lib/drinkboard/drinks.json` 的酒单。全局口令如果要设，自己写进这个 env 文件，用长随机串：

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

改完 env 后 `systemctl restart drinkboard`。

看是否活着：

```bash
curl -sS http://127.0.0.1:8773/api/health
curl -sS http://8.130.110.101/drink/api/health
```

线上保持 `DRINKBOARD_SEED_DEMO=0`。演示局只留给自己电脑。

## 目录

```text
DrinkBoard/
  app/            FastAPI、SQLite、酒精换算
  frontend/       单页（中文）
  config/drinks.json
  deploy/         systemd、nginx、部署脚本
  scripts/        本地启动、备份、清空某一天
  tests/
```

Godot 客户端在仓库的 `Client/`，和这个网页无关。
