from __future__ import annotations

import json
from pathlib import Path

from app.alcohol import canonical_abv
from app.errors import BoardError
from app.security import DRINK_KEY_RE, clean_title


def _presets(raw: object) -> list[int]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise BoardError(400, "快捷毫升要写成数组")
    if len(raw) > 6:
        raise BoardError(400, "快捷项最多 6 个")
    values: list[int] = []
    for item in raw:
        if isinstance(item, bool) or not isinstance(item, int):
            raise BoardError(400, "快捷毫升要是整数")
        if item < 1 or item > 5000:
            raise BoardError(400, "快捷毫升要在 1 到 5000")
        values.append(item)
    return values


def normalize_drink(raw: object, index: int) -> dict:
    if not isinstance(raw, dict):
        raise BoardError(400, "酒单项格式不对")
    key = raw.get("key", "")
    if not isinstance(key, str) or not DRINK_KEY_RE.match(key):
        raise BoardError(400, "酒的编号只能用小写字母、数字和下划线")
    name = raw.get("name", "")
    if not isinstance(name, str):
        raise BoardError(400, "酒名不能空")
    name = " ".join(name.split())
    if not name or len(name) > 20:
        raise BoardError(400, "酒名要在 1 到 20 个字")
    if any(ord(ch) < 32 for ch in name):
        raise BoardError(400, "酒名里别带控制符")
    try:
        abv = canonical_abv(raw.get("abv"))
    except ValueError as exc:
        raise BoardError(400, str(exc)) from exc
    step = raw.get("step_ml", 50)
    if isinstance(step, bool) or not isinstance(step, int) or step < 1 or step > 2000:
        raise BoardError(400, "每次加减要在 1 到 2000 毫升")
    return {
        "key": key,
        "name": name,
        "abv": abv,
        "step_ml": step,
        "presets_ml": _presets(raw.get("presets_ml")),
        "sort_order": index,
    }


def normalize_config(data: object) -> dict:
    if not isinstance(data, dict):
        raise BoardError(500, "酒单配置读不了，检查 drinks.json")
    try:
        title = clean_title(data.get("default_title") or "今晚酒局")
    except ValueError as exc:
        raise BoardError(500, "酒单配置里的房间名不对") from exc
    rows = data.get("drinks")
    if not isinstance(rows, list) or not rows or len(rows) > 20:
        raise BoardError(500, "酒单配置里至少要有一种酒，最多 20 种")
    drinks = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        drink = normalize_drink(row, index)
        if drink["key"] in seen:
            raise BoardError(500, "酒单配置里有重复编号")
        seen.add(drink["key"])
        drinks.append(drink)
    return {"default_title": title, "drinks": drinks}


def load_drinks_file(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BoardError(500, "酒单配置读不了，检查 drinks.json") from exc
    return normalize_config(data)


def normalize_settings_payload(title: str, drinks: list) -> dict:
    try:
        clean = clean_title(title)
    except ValueError as exc:
        raise BoardError(400, str(exc)) from exc
    if not isinstance(drinks, list) or not drinks or len(drinks) > 20:
        raise BoardError(400, "至少留一种酒，最多 20 种")
    rows = []
    seen: set[str] = set()
    for index, row in enumerate(drinks):
        item = normalize_drink(row, index)
        if item["key"] in seen:
            raise BoardError(400, "酒的编号重复了")
        seen.add(item["key"])
        rows.append(item)
    return {"title": clean, "drinks": rows}
