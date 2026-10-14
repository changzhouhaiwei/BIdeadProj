from __future__ import annotations

import json
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def create_room(client):
    response = client.post("/api/rooms")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["room_id"] in body["join_path"]
    assert body["join_key"] in body["join_path"]
    return body


def join(client, room, key, nickname, device=None):
    payload = {
        "nickname": nickname,
        "device": device
        or {
            "user_agent": "TestPhoneUA",
            "platform": "Linux",
            "screen": "390x844",
            "language": "zh-CN",
            "device_type": "phone",
        },
    }
    response = client.post(
        f"/api/rooms/{room}/join",
        headers={"X-Join-Key": key},
        json=payload,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_health_page_and_cors(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["timezone"] == "Asia/Shanghai"
    assert health.headers["cache-control"] == "no-store"
    assert health.headers["referrer-policy"] == "no-referrer"

    allowed = client.get("/api/health", headers={"Origin": "http://127.0.0.1:8773"})
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:8773"
    blocked = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert blocked.headers.get("access-control-allow-origin") is None

    page = client.get("/")
    assert page.status_code == 200
    assert "酒局记账" in page.text
    script = client.get("/app.js")
    assert script.status_code == 200
    assert "今日排行榜" in script.text
    assert "历史排行榜" in script.text
    assert "纯酒精" in script.text


def test_qr_join_flow_and_ranking(client):
    created = create_room(client)
    room = created["room_id"]
    key = created["join_key"]
    page_url = f"http://127.0.0.1:8773/?room={room}&k={key}"
    from app.qrutil import render_qr_svg

    qr = client.post(
        f"/api/rooms/{room}/qr",
        headers={"X-Join-Key": key},
        json={"page_url": page_url},
    )
    assert qr.status_code == 200
    assert qr.headers["content-type"].startswith("image/svg+xml")
    assert qr.text == render_qr_svg(page_url)

    bad = client.post(
        f"/api/rooms/{room}/qr",
        headers={"X-Join-Key": key},
        json={"page_url": page_url.replace(key, "nope")},
    )
    assert bad.status_code == 400
    sneaky = client.post(
        f"/api/rooms/{room}/qr",
        headers={"X-Join-Key": key},
        json={"page_url": f"http://user:pass@127.0.0.1:8773/?room={room}&k={key}"},
    )
    assert sneaky.status_code == 400

    assert client.post(f"/api/rooms/{room}/join", json={"nickname": "路人"}).status_code == 404

    beer = join(client, room, key, "老王")
    wine = join(client, room, key, "小李")
    assert client.post(
        f"/api/rooms/{room}/join",
        headers={"X-Join-Key": key},
        json={"nickname": "老王"},
    ).status_code == 409
    assert client.post(
        f"/api/rooms/{room}/join",
        headers={"X-Join-Key": key},
        json={"nickname": "  "},
    ).status_code == 400

    # 小李给老王记 500ml 啤酒，老王给小李记 50ml 42° 白酒。
    edited = client.post(
        f"/api/rooms/{room}/logs",
        headers={"X-Join-Key": key, "X-Participant-Token": wine["participant_token"]},
        json={"participant_id": beer["participant_id"], "drink_key": "beer_4", "delta_ml": 500},
    )
    assert edited.status_code == 200, edited.text
    other = client.post(
        f"/api/rooms/{room}/logs",
        headers={"X-Join-Key": key, "X-Participant-Token": beer["participant_token"]},
        json={"participant_id": wine["participant_id"], "drink_key": "baijiu_42", "delta_ml": 50},
    )
    assert other.status_code == 200, other.text

    state = client.get(
        f"/api/rooms/{room}/state",
        headers={"X-Join-Key": key, "X-Participant-Token": beer["participant_token"]},
    ).json()
    names = [item["name"] for item in state["drinks"]]
    assert names == ["4° 啤酒", "12° 红酒", "42° 白酒", "53° 白酒"]
    assert state["me"]["nickname"] == "老王"
    assert "user_agent" not in json.dumps(state["participants"])
    assert "TestPhoneUA" not in json.dumps(state["participants"])
    rows = state["leaderboard_today"]["rows"]
    assert [row["nickname"] for row in rows] == ["小李", "老王"]
    assert rows[0]["pure_alcohol_g"] == pytest.approx(16.57)
    assert rows[0]["volumes"][0]["drink_name"] == "42° 白酒"
    assert rows[0]["volumes"][0]["ml"] == 50
    assert rows[1]["pure_alcohol_g"] == pytest.approx(15.78)
    assert rows[1]["volumes"][0]["ml"] == 500
    assert state["leaderboard_all"]["rows"][0]["nickname"] == "小李"
    audit = next(item for item in state["audit"] if item["drink_key"] == "baijiu_42")
    assert audit["editor_nickname"] == "老王"
    assert audit["subject_nickname"] == "小李"
    assert audit["delta_ml"] == 50

    blocked = client.post(
        f"/api/rooms/{room}/logs",
        headers={"X-Join-Key": key, "X-Participant-Token": beer["participant_token"]},
        json={"participant_id": beer["participant_id"], "drink_key": "beer_4", "delta_ml": -5000},
    )
    assert blocked.status_code == 400
    assert "负数" in blocked.json()["detail"]
    again = client.get(f"/api/rooms/{room}/state", headers={"X-Join-Key": key}).json()
    wang = next(person for person in again["participants"] if person["nickname"] == "老王")
    assert wang["board"]["ml_by_drink"]["beer_4"] == 500
    assert wang["device_type"] == "phone"

    overview = client.get(
        f"/api/rooms/{room}/admin/overview",
        headers={"X-Admin-Token": created["admin_token"]},
    )
    assert overview.status_code == 200
    assert "TestPhoneUA" in overview.text
    assert client.get(f"/api/rooms/{room}/admin/overview").status_code == 403
    global_view = client.get(
        f"/api/rooms/{room}/admin/overview",
        headers={"X-Admin-Token": "global-admin-test-token"},
    )
    assert global_view.status_code == 200


def test_shanghai_day_abv_snapshot_and_reset(client):
    created = create_room(client)
    room = created["room_id"]
    key = created["join_key"]
    person = join(client, room, key, "阿强")
    headers = {"X-Join-Key": key, "X-Participant-Token": person["participant_token"]}
    client.app.state.now_utc = lambda: datetime(2026, 10, 14, 15, 59, tzinfo=timezone.utc)
    logged = client.post(
        f"/api/rooms/{room}/logs",
        headers=headers,
        json={"participant_id": person["participant_id"], "drink_key": "beer_4", "delta_ml": 500},
    )
    assert logged.status_code == 200
    assert logged.json()["shanghai_date"] == "2026-10-14"

    client.app.state.now_utc = lambda: datetime(2026, 10, 14, 16, 30, tzinfo=timezone.utc)
    rolled = client.get(f"/api/rooms/{room}/state", headers={"X-Join-Key": key}).json()
    assert rolled["shanghai_today"] == "2026-10-15"
    assert rolled["leaderboard_today"]["rows"] == []
    assert rolled["leaderboard_all"]["rows"][0]["pure_alcohol_g"] == pytest.approx(15.78)

    # 回到 10 月 14 日白天，改酒精度不应改写已经记下的克数。
    client.app.state.now_utc = lambda: datetime(2026, 10, 14, 8, 0, tzinfo=timezone.utc)
    state = client.get(f"/api/rooms/{room}/state", headers={"X-Join-Key": key}).json()
    drinks = state["drinks"]
    for drink in drinks:
        if drink["key"] == "beer_4":
            drink["abv"] = 8
    saved = client.put(
        f"/api/rooms/{room}/settings",
        headers={"X-Admin-Token": created["admin_token"]},
        json={"title": "改过度数", "drinks": drinks},
    )
    assert saved.status_code == 200, saved.text
    client.post(
        f"/api/rooms/{room}/logs",
        headers=headers,
        json={"participant_id": person["participant_id"], "drink_key": "beer_4", "delta_ml": 500},
    )
    mixed = client.get(f"/api/rooms/{room}/state", headers={"X-Join-Key": key}).json()
    # 15.78（旧 4°）+ 31.56（新 8° 的 500ml）
    assert mixed["leaderboard_today"]["rows"][0]["pure_alcohol_g"] == pytest.approx(47.34)
    assert mixed["title"] == "改过度数"

    yesterday = client.post(
        f"/api/rooms/{room}/logs",
        headers=headers,
        json={
            "participant_id": person["participant_id"],
            "drink_key": "wine_12",
            "delta_ml": 150,
            "date": "2026-10-13",
        },
    )
    assert yesterday.status_code == 200
    reset = client.post(
        f"/api/rooms/{room}/reset-day",
        headers={"X-Admin-Token": created["admin_token"]},
        json={"date": "2026-10-14"},
    )
    assert reset.status_code == 200
    assert reset.json()["deleted"] >= 1
    after = client.get(f"/api/rooms/{room}/state", headers={"X-Join-Key": key}).json()
    assert after["leaderboard_today"]["rows"] == []
    assert after["leaderboard_all"]["rows"][0]["pure_alcohol_g"] == pytest.approx(14.20)
    assert any(item["kind"] == "reset" and "2026-10-14" in item["text"] for item in after["audit"])

    board = client.get(
        f"/api/rooms/{room}/state?board_date=2026-10-13",
        headers={"X-Join-Key": key},
    ).json()
    qiang = board["participants"][0]
    assert qiang["board"]["ml_by_drink"]["wine_12"] == 150
    assert board["leaderboard_today"]["rows"] == []


def test_reload_drinks_file_and_backup(client, settings):
    created = create_room(client)
    path = settings.drinks_file
    data = json.loads(path.read_text(encoding="utf-8"))
    data["drinks"] = [
        item for item in data["drinks"] if item["key"] != "beer_4"
    ]
    data["drinks"].append(
        {"key": "huangjiu_15", "name": "15° 黄酒", "abv": 15, "step_ml": 50, "presets_ml": [100]}
    )
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    reloaded = client.post(
        f"/api/rooms/{created['room_id']}/drinks/reload",
        headers={"X-Admin-Token": created["admin_token"]},
    )
    assert reloaded.status_code == 200, reloaded.text
    state = client.get(
        f"/api/rooms/{created['room_id']}/state",
        headers={"X-Join-Key": created["join_key"]},
    ).json()
    names = [item["name"] for item in state["drinks"]]
    assert "15° 黄酒" in names
    assert "4° 啤酒" not in names

    newer = create_room(client)
    fresh = client.get(
        f"/api/rooms/{newer['room_id']}/state",
        headers={"X-Join-Key": newer["join_key"]},
    ).json()
    assert "15° 黄酒" in [item["name"] for item in fresh["drinks"]]

    backup = client.post("/api/admin/backup", headers={"X-Admin-Token": "global-admin-test-token"})
    assert backup.status_code == 200, backup.text
    assert (settings.backup_dir / backup.json()["file"]).exists()
    assert client.post("/api/admin/backup", headers={"X-Admin-Token": created["admin_token"]}).status_code == 404


def test_seed_demo_and_reset_script(tmp_path, monkeypatch):
    from tests.conftest import apply_env

    settings = apply_env(
        monkeypatch,
        tmp_path,
        DRINKBOARD_SEED_DEMO="1",
        DRINKBOARD_ADMIN_TOKEN="",
    )
    from app.main import create_app

    with TestClient_from(create_app(settings)) as client:
        info_path = tmp_path / "demo-room.txt"
        text = info_path.read_text(encoding="utf-8")
        assert stat.S_IMODE(info_path.stat().st_mode) == 0o600
        room = _field(text, "room_id")
        key = _field(text, "join_key")
        state = client.get(f"/api/rooms/{room}/state", headers={"X-Join-Key": key})
        assert state.status_code == 200
        assert state.json()["title"] == "本地演示局"
        person = join(client, room, key, "演示")
        client.app.state.now_utc = lambda: datetime(2026, 10, 14, 8, 0, tzinfo=timezone.utc)
        logged = client.post(
            f"/api/rooms/{room}/logs",
            headers={"X-Join-Key": key, "X-Participant-Token": person["participant_token"]},
            json={"participant_id": person["participant_id"], "drink_key": "beer_4", "delta_ml": 100},
        )
        assert logged.status_code == 200

    with TestClient_from(create_app(settings)) as _again:
        assert info_path.read_text(encoding="utf-8") == text

    script = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "reset_day.py"),
            "--room",
            room,
            "--date",
            "2026-10-14",
            "--db",
            str(settings.db_path),
            "--yes",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert script.returncode == 0, script.stderr
    assert "已删除" in script.stdout


def TestClient_from(app):
    from fastapi.testclient import TestClient

    return TestClient(app)


def _field(text: str, name: str) -> str:
    for line in text.splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1]
    raise AssertionError(name)


def test_rate_limit(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from tests.conftest import apply_env

    settings = apply_env(
        monkeypatch,
        tmp_path,
        DRINKBOARD_RATE_LIMIT="1",
        DRINKBOARD_RATE_CREATE_PER_HOUR="2",
    )
    from app.main import create_app

    with TestClient(create_app(settings)) as client:
        assert client.post("/api/rooms").status_code == 200
        assert client.post("/api/rooms").status_code == 200
        limited = client.post("/api/rooms")
        assert limited.status_code == 429
        assert "等几秒" in limited.json()["detail"]


def test_readme_mentions_operations():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for needle in ("0.789", "15.78", "Asia/Shanghai", "8773", "/drink/", "drinks.json", "highway.pem"):
        assert needle in text


def test_repo_has_no_private_key():
    header = "-----BEGIN " + "OPENSSH PRIVATE KEY-----"
    rsa = "-----BEGIN " + "RSA PRIVATE KEY-----"
    generic = "-----BEGIN " + "PRIVATE KEY-----"
    for path in ROOT.rglob("*"):
        if not path.is_file() or "tests" in path.parts:
            continue
        if path.suffix == ".pem" or path.name.endswith(".pem"):
            raise AssertionError(path)
        if path.suffix.lower() not in {".md", ".py", ".sh", ".conf", ".service", ".example", ".json", ".yml", ".html", ".js", ".css", ".txt", ".cron"}:
            continue
        if path.stat().st_size > 1_000_000:
            continue
        body = path.read_text(encoding="utf-8", errors="ignore")
        for marker in (header, rsa, generic):
            assert marker not in body
