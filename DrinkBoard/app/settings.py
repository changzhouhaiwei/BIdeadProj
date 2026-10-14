from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    db_path: Path
    backup_dir: Path
    drinks_file: Path
    bundled_drinks_file: Path
    frontend_dir: Path
    allowed_origins: tuple[str, ...]
    rate_limit: bool
    docs: bool
    seed_demo: bool
    global_admin_token: str
    trust_proxy: bool
    create_per_hour: int
    join_per_hour: int
    write_per_minute: int
    read_per_minute: int
    host: str
    port: int

    @classmethod
    def from_env(cls) -> "Settings":
        origins = os.environ.get(
            "DRINKBOARD_ALLOWED_ORIGINS",
            "http://127.0.0.1:8773,http://localhost:8773,"
            "http://8.130.110.101,http://fvxpcue.cn,https://fvxpcue.cn",
        )
        bundled = ROOT / "config" / "drinks.json"
        drinks = Path(os.environ.get("DRINKBOARD_DRINKS_FILE", str(bundled)))
        return cls(
            db_path=Path(os.environ.get("DRINKBOARD_DB", str(ROOT / "data" / "drinkboard.sqlite3"))),
            backup_dir=Path(os.environ.get("DRINKBOARD_BACKUP_DIR", str(ROOT / "data" / "backups"))),
            drinks_file=drinks,
            bundled_drinks_file=bundled,
            frontend_dir=ROOT / "frontend",
            allowed_origins=tuple(item.strip() for item in origins.split(",") if item.strip()),
            rate_limit=_flag("DRINKBOARD_RATE_LIMIT", "1"),
            docs=_flag("DRINKBOARD_DOCS", "0"),
            seed_demo=_flag("DRINKBOARD_SEED_DEMO", "0"),
            global_admin_token=os.environ.get("DRINKBOARD_ADMIN_TOKEN", "").strip(),
            trust_proxy=_flag("DRINKBOARD_TRUST_PROXY", "0"),
            create_per_hour=_int("DRINKBOARD_RATE_CREATE_PER_HOUR", 20),
            join_per_hour=_int("DRINKBOARD_RATE_JOIN_PER_HOUR", 60),
            write_per_minute=_int("DRINKBOARD_RATE_WRITE_PER_MINUTE", 120),
            read_per_minute=_int("DRINKBOARD_RATE_READ_PER_MINUTE", 90),
            host=os.environ.get("DRINKBOARD_HOST", "127.0.0.1"),
            port=_int("DRINKBOARD_PORT", 8773),
        )
