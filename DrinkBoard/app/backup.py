from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


def backup_sqlite(src: Path, dest_dir: Path, keep: int = 14) -> Path:
    if not src.exists():
        raise FileNotFoundError(f"数据库不存在：{src}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = dest_dir / f"drinkboard-{stamp}.sqlite3"
    suffix = 2
    while dest.exists():
        dest = dest_dir / f"drinkboard-{stamp}-{suffix}.sqlite3"
        suffix += 1
    source = sqlite3.connect(str(src))
    target = sqlite3.connect(str(dest))
    try:
        with target:
            source.backup(target)
    finally:
        source.close()
        target.close()
    files = sorted(dest_dir.glob("drinkboard-*.sqlite3"))
    extra = len(files) - keep
    if extra > 0:
        for old in files[:extra]:
            old.unlink(missing_ok=True)
    return dest
