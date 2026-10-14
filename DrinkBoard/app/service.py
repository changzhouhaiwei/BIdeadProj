from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app.alcohol import FORMULA, abv_decimal, as_float, pure_alcohol_g, pure_alcohol_ml
from app.backup import backup_sqlite
from app.db import Database
from app.drinks import load_drinks_file, normalize_settings_payload
from app.errors import BoardError
from app.security import (
    ROOM_RE,
    clean_nickname,
    hash_token,
    new_token,
    plain_matches,
    sanitize_device,
    token_matches,
)
from app.settings import Settings
from app.timeutil import shanghai_today, to_shanghai_iso

MAX_DELTA = 5000
MAX_DAY_ML = 20000
MAX_PARTICIPANTS = 200
MAX_LOGS = 50000
QR_PATHS = {"/", "/index.html", "/drink", "/drink/", "/drink/index.html"}


class Service:
    def __init__(self, db: Database, settings: Settings):
        self.db = db
        self.settings = settings
        self.now_utc = lambda: datetime.now(timezone.utc)

    def now(self) -> datetime:
        value = self.now_utc()
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def stamp(self) -> str:
        return self.now().isoformat(timespec="seconds")

    def today(self) -> str:
        return shanghai_today(self.now()).isoformat()

    def resolve_date(self, raw: str | None) -> str:
        today = shanghai_today(self.now())
        if raw is None or raw == "":
            return today.isoformat()
        if not isinstance(raw, str):
            raise BoardError(400, "日期写成 YYYY-MM-DD")
        try:
            year, month, day = (int(part) for part in raw.split("-"))
            parsed = datetime(year, month, day).date()
        except (TypeError, ValueError):
            raise BoardError(400, "日期写成 YYYY-MM-DD") from None
        if parsed.isoformat() != raw:
            raise BoardError(400, "日期写成 YYYY-MM-DD")
        if parsed > today:
            raise BoardError(400, "不能记未来的量")
        if parsed < today - timedelta(days=60):
            raise BoardError(400, "只能改最近 60 天")
        return parsed.isoformat()

    def create_room(self, title: str | None = None) -> dict:
        config = load_drinks_file(self.settings.drinks_file)
        room_title = title or config["default_title"]
        room_id = new_token(16)
        join_key = new_token(18)
        admin_token = new_token(24)
        now = self.stamp()
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO rooms (id, title, join_key_hash, admin_token_hash, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (room_id, room_title, hash_token(join_key), hash_token(admin_token), now, now),
            )
            self._insert_drinks(conn, room_id, config["drinks"])
        return {
            "room_id": room_id,
            "join_key": join_key,
            "admin_token": admin_token,
            "title": room_title,
            "join_path": f"/?room={room_id}&k={join_key}",
        }

    def seed_demo(self, info_path: Path) -> None:
        with self.db.transaction() as conn:
            count = conn.execute("SELECT COUNT(*) AS n FROM rooms").fetchone()["n"]
        if count:
            return
        created = self.create_room(title="本地演示局")
        info_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"room_id={created['room_id']}",
            f"join_key={created['join_key']}",
            f"admin_token={created['admin_token']}",
            f"join_path={created['join_path']}",
            "",
        ]
        info_path.write_text("\n".join(lines), encoding="utf-8")
        os.chmod(info_path, 0o600)

    def join(self, room_id: str, join_key: str, nickname: object, device: object, user_agent: str) -> dict:
        try:
            clean = clean_nickname(nickname)
        except ValueError as exc:
            raise BoardError(400, str(exc)) from exc
        safe_device = sanitize_device(device, user_agent)
        participant_id = new_token(12)
        token = new_token(18)
        now = self.stamp()
        with self.db.transaction() as conn:
            self._room_by_join(conn, room_id, join_key)
            count = conn.execute(
                "SELECT COUNT(*) AS n FROM participants WHERE room_id = ?",
                (room_id,),
            ).fetchone()["n"]
            if count >= MAX_PARTICIPANTS:
                raise BoardError(400, "这局人满了")
            taken = conn.execute(
                "SELECT id FROM participants WHERE room_id = ? AND nickname = ?",
                (room_id, clean),
            ).fetchone()
            if taken:
                raise BoardError(409, "这个昵称已经有人用了")
            conn.execute(
                """
                INSERT INTO participants
                  (id, room_id, nickname, token_hash, device_json, created_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    participant_id,
                    room_id,
                    clean,
                    hash_token(token),
                    json.dumps(safe_device, ensure_ascii=False),
                    now,
                    now,
                ),
            )
        return {"participant_id": participant_id, "participant_token": token, "nickname": clean}

    def state(self, room_id: str, join_key: str, participant_token: str, board_date: str | None) -> dict:
        day = self.resolve_date(board_date)
        today = self.today()
        with self.db.transaction() as conn:
            room = self._room_by_join(conn, room_id, join_key)
            drinks = self._active_drinks(conn, room_id)
            people = conn.execute(
                """
                SELECT * FROM participants
                WHERE room_id = ?
                ORDER BY created_at, nickname
                """,
                (room_id,),
            ).fetchall()
            grouped = self._grouped_logs(conn, room_id, day)
            all_groups = self._grouped_logs(conn, room_id, None)
            today_groups = grouped if day == today else self._grouped_logs(conn, room_id, today)
            me = None
            if participant_token:
                row = self._participant_by_token(conn, room_id, participant_token)
                if row:
                    me = {"participant_id": row["id"], "nickname": row["nickname"]}
            audit = self._audit(conn, room_id)
        active_keys = {item["key"] for item in drinks}
        return {
            "room_id": room["id"],
            "title": room["title"],
            "server_time": to_shanghai_iso(self.stamp()),
            "shanghai_today": today,
            "board_date": day,
            "formula": FORMULA,
            "drinks": drinks,
            "participants": [
                self._person_payload(person, grouped, active_keys) for person in people
            ],
            "leaderboard_today": self._leaderboard(people, today_groups, "today", today),
            "leaderboard_all": self._leaderboard(people, all_groups, "all", None),
            "audit": audit,
            "me": me,
        }

    def add_log(
        self,
        room_id: str,
        join_key: str,
        participant_token: str,
        subject_id: str,
        drink_key: str,
        delta_ml: int | None,
        set_ml: int | None,
        raw_date: str | None,
    ) -> dict:
        day = self.resolve_date(raw_date)
        if delta_ml is None and set_ml is None:
            raise BoardError(400, "说一下要加多少，或者改成多少")
        if delta_ml is not None and set_ml is not None:
            raise BoardError(400, "加量和改成只能选一个")
        if delta_ml is not None and (delta_ml == 0 or abs(delta_ml) > MAX_DELTA):
            raise BoardError(400, "一次加减在 1 到 5000 毫升")
        if set_ml is not None and (set_ml < 0 or set_ml > MAX_DAY_ML):
            raise BoardError(400, "毫升数要在 0 到 20000")
        now = self.stamp()
        with self.db.transaction() as conn:
            self._room_by_join(conn, room_id, join_key)
            editor = self._participant_by_token(conn, room_id, participant_token)
            if editor is None:
                raise BoardError(401, "先进入这局再改")
            subject = conn.execute(
                "SELECT * FROM participants WHERE room_id = ? AND id = ?",
                (room_id, subject_id),
            ).fetchone()
            if subject is None:
                raise BoardError(404, "找不到这个人")
            drink = conn.execute(
                "SELECT * FROM drinks WHERE room_id = ? AND key = ? AND active = 1",
                (room_id, drink_key),
            ).fetchone()
            if drink is None:
                raise BoardError(400, "酒单里没有这个")
            log_count = conn.execute(
                "SELECT COUNT(*) AS n FROM drink_logs WHERE room_id = ?",
                (room_id,),
            ).fetchone()["n"]
            if log_count >= MAX_LOGS:
                raise BoardError(400, "这局记录太多了")
            current = self._current_ml(conn, room_id, subject["id"], drink["id"], day)
            if set_ml is not None:
                delta = set_ml - current
                if delta == 0:
                    raise BoardError(400, "数量没变")
                if abs(delta) > MAX_DELTA:
                    raise BoardError(400, "一次最多改 5000 毫升，差得多就分几次")
            else:
                delta = int(delta_ml)
            new_total = current + delta
            if new_total < 0:
                raise BoardError(400, "这一项不能减成负数")
            if new_total > MAX_DAY_ML:
                raise BoardError(400, "这一项今天太多了")
            conn.execute(
                """
                INSERT INTO drink_logs (
                  room_id, participant_id, drink_id, delta_ml, abv_snapshot,
                  drink_name_snapshot, drink_key_snapshot, shanghai_date,
                  editor_participant_id, editor_nickname, subject_nickname, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    room_id,
                    subject["id"],
                    drink["id"],
                    delta,
                    drink["abv"],
                    drink["name"],
                    drink["key"],
                    day,
                    editor["id"],
                    editor["nickname"],
                    subject["nickname"],
                    now,
                ),
            )
            conn.execute(
                "UPDATE participants SET last_seen_at = ? WHERE id = ?",
                (now, editor["id"]),
            )
        return {"ok": True, "ml": new_total, "delta_ml": delta, "shanghai_date": day}

    def update_settings(self, room_id: str, admin_token: str, title: str, drinks: list) -> dict:
        payload = normalize_settings_payload(title, drinks)
        now = self.stamp()
        with self.db.transaction() as conn:
            room = self._room_row(conn, room_id)
            self._require_admin(room, admin_token)
            conn.execute(
                "UPDATE rooms SET title = ?, updated_at = ? WHERE id = ?",
                (payload["title"], now, room_id),
            )
            self._apply_drinks(conn, room_id, payload["drinks"])
            self._event(conn, room_id, "settings", {"title": payload["title"]}, "局主", now)
        return {"ok": True, "title": payload["title"]}

    def reload_drinks(self, room_id: str, admin_token: str) -> dict:
        config = load_drinks_file(self.settings.drinks_file)
        now = self.stamp()
        with self.db.transaction() as conn:
            room = self._room_row(conn, room_id)
            self._require_admin(room, admin_token)
            self._apply_drinks(conn, room_id, config["drinks"])
            conn.execute("UPDATE rooms SET updated_at = ? WHERE id = ?", (now, room_id))
            self._event(conn, room_id, "reload_drinks", {"count": len(config["drinks"])}, "局主", now)
        return {"ok": True, "count": len(config["drinks"])}

    def reset_day(self, room_id: str, admin_token: str, raw_date: str | None) -> dict:
        day = self.resolve_date(raw_date)
        now = self.stamp()
        with self.db.transaction() as conn:
            room = self._room_row(conn, room_id)
            self._require_admin(room, admin_token)
            deleted = conn.execute(
                "DELETE FROM drink_logs WHERE room_id = ? AND shanghai_date = ?",
                (room_id, day),
            ).rowcount
            self._event(conn, room_id, "reset_day", {"date": day, "deleted": deleted}, "局主", now)
        return {"ok": True, "date": day, "deleted": deleted}

    def rename_participant(self, room_id: str, admin_token: str, participant_id: str, nickname: object) -> dict:
        try:
            clean = clean_nickname(nickname)
        except ValueError as exc:
            raise BoardError(400, str(exc)) from exc
        now = self.stamp()
        with self.db.transaction() as conn:
            room = self._room_row(conn, room_id)
            self._require_admin(room, admin_token)
            person = conn.execute(
                "SELECT * FROM participants WHERE room_id = ? AND id = ?",
                (room_id, participant_id),
            ).fetchone()
            if person is None:
                raise BoardError(404, "找不到这个人")
            taken = conn.execute(
                """
                SELECT id FROM participants
                WHERE room_id = ? AND nickname = ? AND id != ?
                """,
                (room_id, clean, participant_id),
            ).fetchone()
            if taken:
                raise BoardError(409, "这个昵称已经有人用了")
            conn.execute(
                "UPDATE participants SET nickname = ? WHERE id = ?",
                (clean, participant_id),
            )
            self._event(conn, room_id, "rename", {"from": person["nickname"], "to": clean}, "局主", now)
        return {"ok": True, "nickname": clean}

    def admin_overview(self, room_id: str, admin_token: str) -> dict:
        with self.db.transaction() as conn:
            room = self._room_row(conn, room_id)
            self._require_admin(room, admin_token)
            people = conn.execute(
                """
                SELECT id, nickname, device_json, created_at, last_seen_at
                FROM participants WHERE room_id = ? ORDER BY created_at
                """,
                (room_id,),
            ).fetchall()
            events = conn.execute(
                """
                SELECT kind, detail_json, actor, created_at
                FROM room_events WHERE room_id = ? ORDER BY id DESC LIMIT 20
                """,
                (room_id,),
            ).fetchall()
        participants = []
        for person in people:
            try:
                device = json.loads(person["device_json"])
            except json.JSONDecodeError:
                device = {}
            participants.append(
                {
                    "id": person["id"],
                    "nickname": person["nickname"],
                    "device": device,
                    "created_at": to_shanghai_iso(person["created_at"]),
                    "last_seen_at": to_shanghai_iso(person["last_seen_at"]),
                }
            )
        return {
            "room_id": room_id,
            "title": room["title"],
            "participants": participants,
            "events": [
                {
                    "kind": event["kind"],
                    "detail": json.loads(event["detail_json"]),
                    "actor": event["actor"],
                    "at": to_shanghai_iso(event["created_at"]),
                }
                for event in events
            ],
        }

    def qr_svg(self, room_id: str, join_key: str, page_url: str) -> str:
        from app.qrutil import render_qr_svg

        with self.db.transaction() as conn:
            self._room_by_join(conn, room_id, join_key)
        self._validate_qr_url(room_id, join_key, page_url)
        return render_qr_svg(page_url)

    def backup(self, admin_token: str) -> dict:
        if not self.settings.global_admin_token or not plain_matches(admin_token, self.settings.global_admin_token):
            raise BoardError(404, "没有开全局口令")
        path = backup_sqlite(self.settings.db_path, self.settings.backup_dir)
        return {"ok": True, "file": path.name}

    def _validate_qr_url(self, room_id: str, join_key: str, page_url: str) -> None:
        if not isinstance(page_url, str) or len(page_url) > 500:
            raise BoardError(400, "二维码地址不对")
        parsed = urlparse(page_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise BoardError(400, "二维码地址不对")
        if parsed.username or parsed.password or parsed.fragment:
            raise BoardError(400, "二维码地址不对")
        path = parsed.path or "/"
        if path not in QR_PATHS:
            raise BoardError(400, "二维码地址路径不对")
        query = parse_qs(parsed.query, keep_blank_values=False)
        if query.get("room", [None])[0] != room_id or query.get("k", [None])[0] != join_key:
            raise BoardError(400, "二维码地址和这局对不上")
        if "host" in query:
            raise BoardError(400, "二维码不要带局主页参数")

    def _room_by_join(self, conn, room_id: str, join_key: str):
        if not isinstance(room_id, str) or not ROOM_RE.match(room_id) or not join_key:
            raise BoardError(404, "链接无效")
        row = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if row is None or not token_matches(join_key, row["join_key_hash"]):
            raise BoardError(404, "链接无效")
        return row

    def _room_row(self, conn, room_id: str):
        if not isinstance(room_id, str) or not ROOM_RE.match(room_id):
            raise BoardError(404, "找不到这局")
        row = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if row is None:
            raise BoardError(404, "找不到这局")
        return row

    def _require_admin(self, room, admin_token: str) -> None:
        if self.settings.global_admin_token and plain_matches(admin_token or "", self.settings.global_admin_token):
            return
        if token_matches(admin_token or "", room["admin_token_hash"]):
            return
        raise BoardError(403, "没有局主权限")

    def _participant_by_token(self, conn, room_id: str, token: str):
        if not token:
            return None
        return conn.execute(
            "SELECT * FROM participants WHERE room_id = ? AND token_hash = ?",
            (room_id, hash_token(token)),
        ).fetchone()

    def _insert_drinks(self, conn, room_id: str, drinks: list[dict]) -> None:
        for drink in drinks:
            conn.execute(
                """
                INSERT INTO drinks (room_id, key, name, abv, step_ml, presets_json, sort_order, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    room_id,
                    drink["key"],
                    drink["name"],
                    drink["abv"],
                    drink["step_ml"],
                    json.dumps(drink["presets_ml"]),
                    drink["sort_order"],
                ),
            )

    def _apply_drinks(self, conn, room_id: str, drinks: list[dict]) -> None:
        existing = {
            row["key"]: row
            for row in conn.execute("SELECT * FROM drinks WHERE room_id = ?", (room_id,))
        }
        seen: set[str] = set()
        for drink in drinks:
            seen.add(drink["key"])
            payload = (
                drink["name"],
                drink["abv"],
                drink["step_ml"],
                json.dumps(drink["presets_ml"]),
                drink["sort_order"],
            )
            if drink["key"] in existing:
                conn.execute(
                    """
                    UPDATE drinks
                    SET name = ?, abv = ?, step_ml = ?, presets_json = ?, sort_order = ?, active = 1
                    WHERE room_id = ? AND key = ?
                    """,
                    (*payload, room_id, drink["key"]),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO drinks (room_id, key, name, abv, step_ml, presets_json, sort_order, active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (room_id, drink["key"], *payload),
                )
        for key, row in existing.items():
            if key not in seen:
                conn.execute("UPDATE drinks SET active = 0 WHERE id = ?", (row["id"],))

    def _event(self, conn, room_id: str, kind: str, detail: dict, actor: str, now: str) -> None:
        conn.execute(
            """
            INSERT INTO room_events (room_id, kind, detail_json, actor, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (room_id, kind, json.dumps(detail, ensure_ascii=False), actor, now),
        )

    def _active_drinks(self, conn, room_id: str) -> list[dict]:
        rows = conn.execute(
            """
            SELECT key, name, abv, step_ml, presets_json
            FROM drinks
            WHERE room_id = ? AND active = 1
            ORDER BY sort_order, id
            """,
            (room_id,),
        ).fetchall()
        drinks = []
        for row in rows:
            drinks.append(
                {
                    "key": row["key"],
                    "name": row["name"],
                    "abv": as_float(abv_decimal(row["abv"])),
                    "step_ml": row["step_ml"],
                    "presets_ml": json.loads(row["presets_json"]),
                }
            )
        return drinks

    def _grouped_logs(self, conn, room_id: str, day: str | None) -> list:
        if day is None:
            return conn.execute(
                """
                SELECT participant_id, drink_id, drink_key_snapshot, drink_name_snapshot,
                       abv_snapshot, SUM(delta_ml) AS ml
                FROM drink_logs
                WHERE room_id = ?
                GROUP BY participant_id, drink_id, drink_key_snapshot, drink_name_snapshot, abv_snapshot
                """,
                (room_id,),
            ).fetchall()
        return conn.execute(
            """
            SELECT participant_id, drink_id, drink_key_snapshot, drink_name_snapshot,
                   abv_snapshot, SUM(delta_ml) AS ml
            FROM drink_logs
            WHERE room_id = ? AND shanghai_date = ?
            GROUP BY participant_id, drink_id, drink_key_snapshot, drink_name_snapshot, abv_snapshot
            """,
            (room_id, day),
        ).fetchall()

    def _current_ml(self, conn, room_id: str, participant_id: str, drink_id: int, day: str) -> int:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(delta_ml), 0) AS ml
            FROM drink_logs
            WHERE room_id = ? AND participant_id = ? AND drink_id = ? AND shanghai_date = ?
            """,
            (room_id, participant_id, drink_id, day),
        ).fetchone()
        return int(row["ml"])

    def _person_payload(self, person, grouped, active_keys: set[str]) -> dict:
        ml_by_drink: dict[str, int] = {}
        extras_ml: dict[str, dict] = {}
        total_g = Decimal("0")
        total_ml_pure = Decimal("0")
        try:
            device = json.loads(person["device_json"])
        except json.JSONDecodeError:
            device = {}
        device_type = device.get("device_type") if isinstance(device, dict) else "unknown"
        if device_type not in {"phone", "tablet", "desktop", "unknown"}:
            device_type = "unknown"
        for row in grouped:
            if row["participant_id"] != person["id"]:
                continue
            ml = int(row["ml"])
            if ml == 0:
                continue
            abv = abv_decimal(row["abv_snapshot"])
            total_g += pure_alcohol_g(Decimal(ml), abv)
            total_ml_pure += pure_alcohol_ml(Decimal(ml), abv)
            key = row["drink_key_snapshot"]
            if key in active_keys:
                ml_by_drink[key] = ml_by_drink.get(key, 0) + ml
            else:
                bucket = extras_ml.setdefault(key, {"drink_key": key, "drink_name": row["drink_name_snapshot"], "ml": 0})
                bucket["ml"] += ml
                bucket["drink_name"] = row["drink_name_snapshot"]
        return {
            "id": person["id"],
            "nickname": person["nickname"],
            "device_type": device_type,
            "board": {
                "ml_by_drink": ml_by_drink,
                "extras": list(extras_ml.values()),
                "pure_alcohol_g": as_float(total_g),
                "pure_alcohol_ml": as_float(total_ml_pure),
            },
        }

    def _leaderboard(self, people, grouped, scope: str, day: str | None) -> dict:
        by_id = {person["id"]: person for person in people}
        per_person: dict[str, dict] = {}
        for row in grouped:
            ml = int(row["ml"])
            if ml == 0:
                continue
            person = by_id.get(row["participant_id"])
            if person is None:
                continue
            bucket = per_person.setdefault(
                person["id"],
                {
                    "participant_id": person["id"],
                    "nickname": person["nickname"],
                    "pure_alcohol_g": Decimal("0"),
                    "pure_alcohol_ml": Decimal("0"),
                    "total_ml": 0,
                    "volumes": [],
                },
            )
            abv = abv_decimal(row["abv_snapshot"])
            grams = pure_alcohol_g(Decimal(ml), abv)
            pure_ml = pure_alcohol_ml(Decimal(ml), abv)
            bucket["pure_alcohol_g"] += grams
            bucket["pure_alcohol_ml"] += pure_ml
            bucket["total_ml"] += ml
            bucket["volumes"].append(
                {
                    "drink_key": row["drink_key_snapshot"],
                    "drink_name": row["drink_name_snapshot"],
                    "abv": as_float(abv),
                    "ml": ml,
                    "pure_alcohol_g": as_float(grams),
                }
            )
        rows = [item for item in per_person.values() if item["total_ml"] > 0 or item["pure_alcohol_g"] > 0]
        rows.sort(key=lambda item: (-item["pure_alcohol_g"], -item["total_ml"], item["nickname"]))
        last_grams = None
        rank = 0
        payload = []
        for index, item in enumerate(rows, start=1):
            grams = item["pure_alcohol_g"]
            if last_grams is None or grams != last_grams:
                rank = index
                last_grams = grams
            item["volumes"].sort(key=lambda volume: volume["drink_name"])
            payload.append(
                {
                    "rank": rank,
                    "participant_id": item["participant_id"],
                    "nickname": item["nickname"],
                    "pure_alcohol_g": as_float(item["pure_alcohol_g"]),
                    "pure_alcohol_ml": as_float(item["pure_alcohol_ml"]),
                    "total_ml": item["total_ml"],
                    "volumes": item["volumes"],
                }
            )
        return {
            "scope": scope,
            "shanghai_date": day,
            "metric": "pure_alcohol_g",
            "rows": payload,
        }

    def _audit(self, conn, room_id: str) -> list[dict]:
        logs = conn.execute(
            """
            SELECT id, editor_nickname, subject_nickname, drink_name_snapshot, drink_key_snapshot,
                   delta_ml, shanghai_date, created_at
            FROM drink_logs
            WHERE room_id = ?
            ORDER BY id DESC
            LIMIT 40
            """,
            (room_id,),
        ).fetchall()
        events = conn.execute(
            """
            SELECT id, kind, detail_json, actor, created_at
            FROM room_events
            WHERE room_id = ? AND kind = 'reset_day'
            ORDER BY id DESC
            LIMIT 20
            """,
            (room_id,),
        ).fetchall()
        items = []
        for row in logs:
            items.append(
                {
                    "id": row["id"],
                    "kind": "log",
                    "at": to_shanghai_iso(row["created_at"]),
                    "editor_nickname": row["editor_nickname"],
                    "subject_nickname": row["subject_nickname"],
                    "drink_name": row["drink_name_snapshot"],
                    "drink_key": row["drink_key_snapshot"],
                    "delta_ml": row["delta_ml"],
                    "shanghai_date": row["shanghai_date"],
                    "text": "",
                }
            )
        for event in events:
            detail = json.loads(event["detail_json"])
            day = detail.get("date", "")
            items.append(
                {
                    "id": f"event-{event['id']}",
                    "kind": "reset",
                    "at": to_shanghai_iso(event["created_at"]),
                    "editor_nickname": event["actor"],
                    "subject_nickname": "",
                    "drink_name": "",
                    "drink_key": "",
                    "delta_ml": 0,
                    "shanghai_date": day,
                    "text": f"清空了 {day} 的记录",
                }
            )
        items.sort(key=lambda item: item["at"], reverse=True)
        return items[:40]
