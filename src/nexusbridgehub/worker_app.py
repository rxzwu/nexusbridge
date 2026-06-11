"""Standalone thin worker app — runs on user's machine, no secrets embedded."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from typing import Any

import websockets

from nexusbridgehub.client import BridgeClient
from nexusbridgehub.crypto import deobfuscate_seed, decrypt_server_url
from nexusbridgehub.protocol import BridgeMessage, MessageType
from nexusbridgehub.utils import dumps_message, format_error, loads_message, setup_logging

_log = logging.getLogger("nexusbridgehub.worker_app")


class WorkerApp:
    """
    Thin client shell. Pair with bot via code → receive JWT → connect as worker.

    Build-time config (from builder):
        ENCRYPTED_SERVER_URL — AES-GCM blob, no plain WSS in binary
        OBFUSCATED_BUILD_SEED — XOR-masked seed for decryption
    Runtime config (user input, no secrets):
        pair code OR pre-issued JWT token
        user_id (optional if embedded in token)
    """

    def __init__(
        self,
        *,
        server_url: str | None = None,
        encrypted_server_url: str | None = None,
        build_seed: bytes | None = None,
        project_id: str = "default",
        user_id: str = "",
        token: str = "",
        pair_code: str = "",
        register_fn: Any = None,
        reconnect_delay: float = 5.0,
    ) -> None:
        self._server_url = server_url
        self._encrypted = encrypted_server_url
        self._build_seed = build_seed
        self.project_id = project_id
        self.user_id = user_id
        self.token = token
        self.pair_code = pair_code
        self._register_fn = register_fn
        self.reconnect_delay = reconnect_delay
        self._stop = asyncio.Event()

    def resolve_server_url(self) -> str:
        if self._server_url:
            return self._server_url
        if self._encrypted and self._build_seed:
            return decrypt_server_url(self._encrypted, self._build_seed)
        env = os.getenv("NEXUSBRIDGEHUB_SERVER_URL", "")
        if env:
            return env
        raise RuntimeError("server URL not configured")

    async def _pair_for_token(self, server_url: str) -> str:
        if not self.pair_code:
            raise ValueError("pair_code required when token is empty")
        async with websockets.connect(server_url) as conn:
            msg = BridgeMessage(
                type=MessageType.PAIR_REQUEST,
                payload={"code": self.pair_code},
            )
            await conn.send(dumps_message(msg.to_dict()))
            raw = await asyncio.wait_for(conn.recv(), timeout=15)
            reply = BridgeMessage.from_dict(loads_message(raw))
            if reply.type == MessageType.ERROR:
                raise RuntimeError(reply.payload.get("error", "pair failed"))
            if reply.type != MessageType.PAIR_TOKEN:
                raise RuntimeError(f"unexpected pair reply: {reply.type}")
            self.token = str(reply.payload["token"])
            self.project_id = str(reply.payload.get("project_id", self.project_id))
            self.user_id = str(reply.payload.get("user_id", self.user_id))
            _log.info("paired project=%s user=%s", self.project_id, self.user_id)
            return self.token

    async def _run_once(self) -> None:
        server_url = self.resolve_server_url()
        if not self.token:
            await self._pair_for_token(server_url)

        bridge = BridgeClient(
            server_url=server_url,
            token=self.token,
            project_id=self.project_id,
            user_id=self.user_id,
            metadata={"client": "nexusbridgehub-worker"},
            reconnect_delay=self.reconnect_delay,
            stop_event=self._stop,
        )

        if self._register_fn:
            self._register_fn(bridge)
        else:
            # Try to load register_handlers from worker_bundle
            try:
                from nexusbridgehub.worker_bundle import register_handlers  # type: ignore
                register_handlers(bridge)
            except (ImportError, AttributeError):
                # Fallback to default handlers
                bridge.register("ping", lambda: {"status": "ok"})
                bridge.register("status", lambda: {"project": self.project_id, "user": self.user_id})

        _log.info("worker starting project=%s user=%s", self.project_id, self.user_id)
        await bridge.run()

    async def run(self) -> None:
        """Run worker with auto-restart on fatal errors."""
        while not self._stop.is_set():
            try:
                await self._run_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                _log.exception("worker stopped: %s", format_error(exc))
            if self._stop.is_set():
                break
            _log.info("restarting worker in %.1fs...", self.reconnect_delay)
            await asyncio.sleep(self.reconnect_delay)

    def stop(self) -> None:
        self._stop.set()


def _load_embedded_config() -> tuple[str | None, bytes | None]:
    """Populated by builder into worker_bundle.py at compile time."""
    try:
        from nexusbridgehub.worker_bundle import ENCRYPTED_SERVER_URL, OBFUSCATED_BUILD_SEED  # type: ignore

        seed = deobfuscate_seed(OBFUSCATED_BUILD_SEED)
        return ENCRYPTED_SERVER_URL, seed
    except ImportError:
        return None, None


def main_cli() -> None:
    parser = argparse.ArgumentParser(description="NexusBridgeHub worker (thin client)")
    parser.add_argument("--server-url", default=os.getenv("NEXUSBRIDGEHUB_SERVER_URL", ""))
    parser.add_argument("--project-id", default=os.getenv("NEXUSBRIDGEHUB_PROJECT_ID", "taskrelay"))
    parser.add_argument("--user-id", default=os.getenv("NEXUSBRIDGEHUB_USER_ID", ""))
    parser.add_argument("--token", default=os.getenv("NEXUSBRIDGEHUB_TOKEN", ""))
    parser.add_argument("--pair-code", default=os.getenv("NEXUSBRIDGEHUB_PAIR_CODE", ""))
    args = parser.parse_args()

    setup_logging()
    encrypted, seed = _load_embedded_config()

    app = WorkerApp(
        server_url=args.server_url or None,
        encrypted_server_url=encrypted,
        build_seed=seed,
        project_id=args.project_id,
        user_id=args.user_id,
        token=args.token,
        pair_code=args.pair_code,
    )

    if sys.platform == "win32" and sys.version_info < (3, 14):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        app.stop()
        _log.info("worker stopped by user")
