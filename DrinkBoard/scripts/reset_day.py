#!/usr/bin/env python3
"""在服务器上清空某一天的记账。有数据库文件就能跑，不走网页口令。"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description="清空酒局某一天的毫升记录")
    parser.add_argument("--room", required=True, help="房间 id")
    parser.add_argument("--date", required=True, help="上海日历日，YYYY-MM-DD")
    parser.add_argument("--db", default="", help="数据库路径，默认读环境变量")
    parser.add_argument("--yes", action="store_true", help="真的删")
    args = parser.parse_args()
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print("日期写成 YYYY-MM-DD", file=sys.stderr)
        sys.exit(2)
    settings = Settings.from_env()
    db_path = Path(args.db) if args.db else settings.db_path
    if not db_path.exists():
        print(f"数据库不存在：{db_path}", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(db_path)
    try:
        room = conn.execute("SELECT id FROM rooms WHERE id = ?", (args.room,)).fetchone()
        if room is None:
            print("找不到这局", file=sys.stderr)
            sys.exit(1)
        count = conn.execute(
            "SELECT COUNT(*) FROM drink_logs WHERE room_id = ? AND shanghai_date = ?",
            (args.room, args.date),
        ).fetchone()[0]
        if not args.yes:
            print(f"将删除 {count} 条 {args.date} 的记录。加上 --yes 才会动。")
            return
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with conn:
            deleted = conn.execute(
                "DELETE FROM drink_logs WHERE room_id = ? AND shanghai_date = ?",
                (args.room, args.date),
            ).rowcount
            conn.execute(
                """
                INSERT INTO room_events (room_id, kind, detail_json, actor, created_at)
                VALUES (?, 'reset_day', ?, '服务器脚本', ?)
                """,
                (args.room, json.dumps({"date": args.date, "deleted": deleted}, ensure_ascii=False), now),
            )
        print(f"已删除 {deleted} 条")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
