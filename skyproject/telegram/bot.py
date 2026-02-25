"""Telegram bot for SkyProject remote management."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class SkyTelegramBot:
    """Lightweight Telegram bot using raw HTTP (no heavy dependency)."""

    API_BASE = "https://api.telegram.org/bot{token}"

    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
        self.token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
        self.report_every: int = int(os.getenv("SKY_TELEGRAM_REPORT_EVERY", "10"))
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.chat_id)

    async def start(self) -> None:
        if not self.enabled:
            logger.info("Telegram bot disabled (no token/chat_id configured)")
            return
        self._running = True
        self._poll_task = asyncio.create_task(self._poll_updates())
        logger.info("Telegram bot started")

    async def stop(self) -> None:
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        logger.info("Telegram bot stopped")

    async def send_message(self, text: str, chat_id: str = "") -> None:
        if not self.enabled:
            return
        target = chat_id or self.chat_id
        try:
            import httpx
            url = f"{self.API_BASE.format(token=self.token)}/sendMessage"
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(url, json={
                    "chat_id": target,
                    "text": text,
                    "parse_mode": "HTML",
                })
        except Exception as e:
            logger.error("Telegram send failed: %s", e)

    async def send_cycle_report(self, cycle_num: int) -> None:
        """Send periodic cycle report."""
        if not self.enabled or not self.orchestrator:
            return
        s = self.orchestrator.state
        text = (
            f"<b>SkyProject Cycle #{cycle_num}</b>\n\n"
            f"Tasks completed: {s.total_tasks_completed}\n"
            f"Improvements: {s.total_improvements}\n"
            f"Uptime: {int(s.uptime_seconds)}s\n"
        )
        await self.send_message(text)

    async def _poll_updates(self) -> None:
        """Long-poll for Telegram updates and dispatch commands."""
        offset = 0
        while self._running:
            try:
                import httpx
                url = f"{self.API_BASE.format(token=self.token)}/getUpdates"
                async with httpx.AsyncClient(timeout=35) as client:
                    resp = await client.get(url, params={"offset": offset, "timeout": 30})
                    data = resp.json()

                if data.get("ok"):
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        await self._handle_update(update)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Telegram poll error: %s", e)
                await asyncio.sleep(5)

    async def _handle_update(self, update: dict) -> None:
        msg = update.get("message", {})
        text = msg.get("text", "").strip()
        chat_id = str(msg.get("chat", {}).get("id", ""))

        if not text.startswith("/"):
            return

        from skyproject.telegram.handlers import handle_command
        response = await handle_command(text, self.orchestrator)
        if response:
            await self.send_message(response, chat_id=chat_id)
