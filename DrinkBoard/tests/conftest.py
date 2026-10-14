from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


def apply_env(monkeypatch, tmp_path: Path, **extra: str):
    drinks = tmp_path / "drinks.json"
    bundled = ROOT / "config" / "drinks.json"
    drinks.write_text(bundled.read_text(encoding="utf-8"), encoding="utf-8")
    values = {
        "DRINKBOARD_DB": str(tmp_path / "board.sqlite3"),
        "DRINKBOARD_BACKUP_DIR": str(tmp_path / "backups"),
        "DRINKBOARD_DRINKS_FILE": str(drinks),
        "DRINKBOARD_RATE_LIMIT": "0",
        "DRINKBOARD_ALLOWED_ORIGINS": "http://127.0.0.1:8773",
        "DRINKBOARD_DOCS": "0",
        "DRINKBOARD_SEED_DEMO": "0",
        "DRINKBOARD_ADMIN_TOKEN": "global-admin-test-token",
        "DRINKBOARD_TRUST_PROXY": "0",
    }
    values.update(extra)
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    from app.settings import Settings

    return Settings.from_env()


@pytest.fixture()
def settings(tmp_path, monkeypatch):
    return apply_env(monkeypatch, tmp_path)


@pytest.fixture()
def client(settings):
    from app.main import create_app

    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client
