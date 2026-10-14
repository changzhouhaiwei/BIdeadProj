#!/usr/bin/env python3
"""把正在用的 SQLite 热备份到备份目录，默认留最近 14 份。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.backup import backup_sqlite
from app.settings import Settings


def main() -> None:
    settings = Settings.from_env()
    dest = backup_sqlite(settings.db_path, settings.backup_dir)
    print(dest)


if __name__ == "__main__":
    main()
