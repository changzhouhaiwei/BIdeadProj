from __future__ import annotations

import hashlib
import hmac
import re
import secrets

ROOM_RE = re.compile(r"^[A-Za-z0-9_-]{8,80}$")
DRINK_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
DEVICE_TYPES = {"phone", "tablet", "desktop", "unknown"}
DEVICE_FIELDS = ("user_agent", "platform", "screen", "language", "device_type", "timezone")


def new_token(nbytes: int = 18) -> str:
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_matches(token: str, hashed: str) -> bool:
    if not token or not hashed:
        return False
    return hmac.compare_digest(hash_token(token), hashed)


def plain_matches(token: str, expected: str) -> bool:
    if not token or not expected:
        return False
    return hmac.compare_digest(token, expected)


def clean_nickname(raw: object) -> str:
    if not isinstance(raw, str):
        raise ValueError("先起个昵称")
    nickname = re.sub(r"\s+", " ", raw.strip())
    if not nickname:
        raise ValueError("先起个昵称")
    if len(nickname) > 16:
        raise ValueError("昵称最多 16 个字")
    if any(ord(ch) < 32 for ch in nickname):
        raise ValueError("昵称里别带控制符")
    return nickname


def clean_title(raw: object) -> str:
    if not isinstance(raw, str):
        raise ValueError("房间名不能空")
    title = re.sub(r"\s+", " ", raw.strip())
    if not title:
        raise ValueError("房间名不能空")
    if len(title) > 40:
        raise ValueError("房间名最多 40 个字")
    if any(ord(ch) < 32 for ch in title):
        raise ValueError("房间名里别带控制符")
    return title


def sanitize_device(payload: object, request_ua: str = "") -> dict:
    source = payload if isinstance(payload, dict) else {}
    cleaned: dict[str, str] = {}
    for key in DEVICE_FIELDS:
        value = source.get(key, "")
        if not isinstance(value, str):
            value = "" if value is None else str(value)
        cleaned[key] = value.strip()[:300]
    if not cleaned["user_agent"] and request_ua:
        cleaned["user_agent"] = request_ua.strip()[:300]
    if cleaned["device_type"] not in DEVICE_TYPES:
        cleaned["device_type"] = "unknown"
    return cleaned
