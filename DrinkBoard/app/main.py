from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from app.db import Database
from app.errors import BoardError
from app.rate_limit import RateLimiter
from app.service import Service
from app.settings import Settings

logger = logging.getLogger("drinkboard")


class JoinIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nickname: str = ""
    device: dict[str, Any] | None = None


class LogIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    participant_id: str = Field(min_length=4, max_length=80)
    drink_key: str = Field(min_length=1, max_length=32)
    delta_ml: int | None = None
    set_ml: int | None = None
    date: str | None = None


class SettingsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    drinks: list[dict[str, Any]] = Field(min_length=1, max_length=20)


class ResetIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date: str | None = None


class RenameIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nickname: str


class QrIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page_url: str = Field(min_length=8, max_length=500)


def ensure_drinks_file(settings: Settings) -> None:
    if settings.drinks_file.exists():
        return
    settings.drinks_file.parent.mkdir(parents=True, exist_ok=True)
    settings.drinks_file.write_text(
        settings.bundled_drinks_file.read_text(encoding="utf-8"),
        encoding="utf-8",
    )


def client_ip(request: Request, settings: Settings) -> str:
    if settings.trust_proxy:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            first = forwarded.split(",")[0].strip()
            if first:
                return first[:64]
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def guard_rate(request: Request, bucket: str, limit: int, window: float) -> None:
    settings: Settings = request.app.state.settings
    ip = client_ip(request, settings)
    limiter: RateLimiter = request.app.state.limiter
    if not limiter.allow(f"{bucket}:{ip}", limit, window):
        raise HTTPException(status_code=429, detail="点太快了，等几秒再试")


def call(fn):
    try:
        return fn()
    except BoardError as exc:
        if exc.status >= 500:
            logger.error("drinkboard: %s", exc.message)
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc


def service_of(request: Request) -> Service:
    service = request.app.state.service
    if service is None:
        raise HTTPException(status_code=503, detail="还在启动")
    return service


class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path") or ""
        if path.startswith("/api/"):
            for name, value in scope.get("headers") or []:
                if name == b"content-length":
                    try:
                        size = int(value.decode())
                    except ValueError:
                        size = 0
                    if size > 16384:
                        await JSONResponse(status_code=413, content={"detail": "请求太大"})(scope, receive, send)
                        return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                headers.append((b"x-content-type-options", b"nosniff"))
                headers.append((b"referrer-policy", b"no-referrer"))
                headers.append((b"x-robots-tag", b"noindex, nofollow"))
                if path.startswith("/api/"):
                    headers.append((b"cache-control", b"no-store"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        ensure_drinks_file(settings)
        db = Database(settings.db_path)
        service = Service(db, settings)
        app.state.db = db
        app.state.service = service

        def now() -> datetime:
            override = app.state.now_utc
            value = override() if override is not None else datetime.now(timezone.utc)
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)

        service.now_utc = now
        if settings.seed_demo:
            info = settings.db_path.parent / "demo-room.txt"
            service.seed_demo(info)
            logger.info("本地演示局信息在 %s（仅本机，不要提交）", info)
        try:
            yield
        finally:
            db.close()
            app.state.service = None

    app = FastAPI(
        title="酒局记账",
        docs_url="/api/docs" if settings.docs else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.docs else None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.limiter = RateLimiter(settings.rate_limit)
    app.state.service = None
    app.state.now_utc = None
    app.state.db = None

    @app.exception_handler(RequestValidationError)
    async def invalid_body(_request: Request, _exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": "填写不对，看下数字和昵称"})

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["Content-Type", "Accept", "X-Join-Key", "X-Participant-Token", "X-Admin-Token"],
        max_age=600,
    )

    @app.get("/api/health")
    def health():
        return {"ok": True, "timezone": "Asia/Shanghai"}

    @app.post("/api/rooms")
    def create_room(request: Request):
        guard_rate(request, "create", settings.create_per_hour, 3600)
        return call(lambda: service_of(request).create_room())

    @app.get("/api/rooms/{room_id}/state")
    def state(room_id: str, request: Request, board_date: str | None = None):
        guard_rate(request, "read", settings.read_per_minute, 60)
        join_key = request.headers.get("x-join-key", "")
        participant = request.headers.get("x-participant-token", "")
        return call(
            lambda: service_of(request).state(room_id, join_key, participant, board_date)
        )

    @app.post("/api/rooms/{room_id}/join")
    def join(room_id: str, body: JoinIn, request: Request):
        guard_rate(request, "join", settings.join_per_hour, 3600)
        join_key = request.headers.get("x-join-key", "")
        user_agent = request.headers.get("user-agent", "")
        return call(
            lambda: service_of(request).join(room_id, join_key, body.nickname, body.device, user_agent)
        )

    @app.post("/api/rooms/{room_id}/logs")
    def add_log(room_id: str, body: LogIn, request: Request):
        guard_rate(request, "write", settings.write_per_minute, 60)
        return call(
            lambda: service_of(request).add_log(
                room_id,
                request.headers.get("x-join-key", ""),
                request.headers.get("x-participant-token", ""),
                body.participant_id,
                body.drink_key,
                body.delta_ml,
                body.set_ml,
                body.date,
            )
        )

    @app.put("/api/rooms/{room_id}/settings")
    def update_settings(room_id: str, body: SettingsIn, request: Request):
        guard_rate(request, "write", settings.write_per_minute, 60)
        return call(
            lambda: service_of(request).update_settings(
                room_id,
                request.headers.get("x-admin-token", ""),
                body.title,
                body.drinks,
            )
        )

    @app.post("/api/rooms/{room_id}/drinks/reload")
    def reload_drinks(room_id: str, request: Request):
        guard_rate(request, "write", settings.write_per_minute, 60)
        return call(
            lambda: service_of(request).reload_drinks(room_id, request.headers.get("x-admin-token", ""))
        )

    @app.post("/api/rooms/{room_id}/reset-day")
    def reset_day(room_id: str, body: ResetIn, request: Request):
        guard_rate(request, "write", settings.write_per_minute, 60)
        return call(
            lambda: service_of(request).reset_day(
                room_id,
                request.headers.get("x-admin-token", ""),
                body.date,
            )
        )

    @app.post("/api/rooms/{room_id}/participants/{participant_id}/rename")
    def rename(room_id: str, participant_id: str, body: RenameIn, request: Request):
        guard_rate(request, "write", settings.write_per_minute, 60)
        return call(
            lambda: service_of(request).rename_participant(
                room_id,
                request.headers.get("x-admin-token", ""),
                participant_id,
                body.nickname,
            )
        )

    @app.get("/api/rooms/{room_id}/admin/overview")
    def overview(room_id: str, request: Request):
        guard_rate(request, "read", settings.read_per_minute, 60)
        return call(
            lambda: service_of(request).admin_overview(room_id, request.headers.get("x-admin-token", ""))
        )

    @app.post("/api/rooms/{room_id}/qr")
    def qr(room_id: str, body: QrIn, request: Request):
        guard_rate(request, "write", settings.write_per_minute, 60)
        svg = call(
            lambda: service_of(request).qr_svg(
                room_id,
                request.headers.get("x-join-key", ""),
                body.page_url,
            )
        )
        return Response(content=svg, media_type="image/svg+xml")

    @app.post("/api/admin/backup")
    def backup(request: Request):
        guard_rate(request, "write", settings.write_per_minute, 60)
        return call(lambda: service_of(request).backup(request.headers.get("x-admin-token", "")))

    app.mount(
        "/",
        StaticFiles(directory=str(settings.frontend_dir), html=True),
        name="frontend",
    )
    return app


app = create_app()
