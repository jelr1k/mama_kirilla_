from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("jarvis.telegram_bot")


def chunk_text(text: str, max_len: int = 4000) -> list[str]:
    """Splits long text messages into chunks respecting whitespace and line breaks."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    rest = text
    while len(rest) > max_len:
        split_idx = rest.rfind("\n", 0, max_len)
        if split_idx == -1 or split_idx < max_len // 2:
            split_idx = rest.rfind(" ", 0, max_len)
        if split_idx == -1 or split_idx < max_len // 4:
            split_idx = max_len
        chunks.append(rest[:split_idx].strip())
        rest = rest[split_idx:].strip()
    if rest:
        chunks.append(rest)
    return chunks


class TelegramClientMixin:
    """HTTP transport mixin for interacting with Telegram Bot API."""

    @staticmethod
    def _chunk_text(text: str, max_len: int = 4000) -> list[str]:
        return chunk_text(text, max_len)

    async def _send_chat_action(self, client: httpx.AsyncClient, chat_id: int, action: str = "typing") -> None:
        try:
            url = f"{self.api_base_url}/bot{self.bot_token}/sendChatAction"
            await client.post(url, json={"chat_id": chat_id, "action": action}, timeout=5.0)
        except Exception:
            pass

    async def _answer_callback_query(
        self, client: httpx.AsyncClient, callback_query_id: str, text: str | None = None, alert: bool = False
    ) -> bool:
        url = f"{self.api_base_url}/bot{self.bot_token}/answerCallbackQuery"
        payload: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
            payload["show_alert"] = alert
        try:
            resp = await client.post(url, json=payload, timeout=10.0)
            return resp.is_success
        except Exception as exc:
            logger.debug("telegram_answer_callback_error: %s", exc)
            return False

    async def _send_message(
        self,
        client: httpx.AsyncClient,
        chat_id: int,
        text: str,
        parse_mode: str | None = "HTML",
        reply_markup: dict[str, Any] | None = None,
    ) -> bool:
        chunks = self._chunk_text(text)
        success = True
        for i, chunk in enumerate(chunks):
            # Only attach reply_markup to the final chunk
            markup = reply_markup if i == len(chunks) - 1 else None
            ok = await self._send_single_message(client, chat_id, chunk, parse_mode=parse_mode, reply_markup=markup)
            if not ok:
                success = False
        return success

    async def _send_single_message(
        self,
        client: httpx.AsyncClient,
        chat_id: int,
        text: str,
        parse_mode: str | None = "HTML",
        reply_markup: dict[str, Any] | None = None,
    ) -> bool:
        url = f"{self.api_base_url}/bot{self.bot_token}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            resp = await client.post(url, json=payload, timeout=10.0)
            if resp.is_success:
                return True
            # If 400 Bad Request and parse_mode was specified, retry without parse_mode (entities fallback)
            if resp.status_code == 400 and parse_mode is not None:
                logger.warning(
                    "telegram_send_message_html_failed chat_id=%s resp=%s; retrying as plain text",
                    chat_id,
                    resp.text,
                )
                retry_payload = {k: v for k, v in payload.items() if k != "parse_mode"}
                retry_resp = await client.post(url, json=retry_payload, timeout=10.0)
                return retry_resp.is_success
            logger.error("telegram_send_message_failed status=%d text=%s", resp.status_code, resp.text)
            return False
        except Exception as exc:
            logger.error("telegram_send_message_exception chat_id=%s error=%s", chat_id, exc)
            return False

    async def _send_photo(self, client: httpx.AsyncClient, chat_id: int, photo_path: str, caption: str = "") -> None:
        url = f"{self.api_base_url}/bot{self.bot_token}/sendPhoto"
        file_path = Path(photo_path)
        if not file_path.is_file():
            await self._send_message(client, chat_id, "❌ Файл скриншота не найден на диске.")
            return

        try:
            with open(file_path, "rb") as f:
                files = {"photo": (file_path.name, f, "image/png")}
                data = {"chat_id": str(chat_id), "caption": caption}
                await client.post(url, data=data, files=files, timeout=20.0)
        except Exception as exc:
            logger.error("telegram_send_photo_failed chat_id=%s error=%s", chat_id, exc)
            await self._send_message(client, chat_id, f"❌ Ошибка отправки фото: {exc}")

    async def test_token(self, token: str, base_url: str | None = None) -> dict[str, Any]:
        token = token.strip()
        if not token:
            return {"success": False, "error": "Токен не указан"}
        root = (base_url.strip().rstrip("/") if base_url and base_url.strip() else self.api_base_url)
        url = f"{root}/bot{token}/getMe"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                data = resp.json()
                if data.get("ok"):
                    res = data.get("result", {})
                    return {
                        "success": True,
                        "bot_id": res.get("id"),
                        "username": res.get("username"),
                        "first_name": res.get("first_name"),
                    }
                return {"success": False, "error": data.get("description", "Неверный ответ Telegram")}
        except Exception as exc:
            return {"success": False, "error": f"Ошибка соединения: {exc}"}

    def notify_shutdown(self) -> None:
        """Send notification that the assistant is shutting down and bot is going inactive."""
        if not self.is_enabled or not self.bot_token or not self.allowed_chat_ids:
            return
        bot_name = f"@{self._bot_username}" if getattr(self, "_bot_username", None) else "Kirieshcka"
        url = f"{self.api_base_url}/bot{self.bot_token}/sendMessage"
        text = (
            f"🔴 <b>Kirieshcka v2 отключена на ПК</b>\n"
            f"Ассистент завершил работу. Бот <code>{bot_name}</code> переведён в неактивный режим."
        )
        try:
            logger.info("telegram_notify_shutdown_start allowed_chats=%s url=%s", len(self.allowed_chat_ids), self.api_base_url)
            with httpx.Client(timeout=5.0) as client:
                for cid in self.allowed_chat_ids:
                    try:
                        resp = client.post(url, json={"chat_id": cid, "text": text, "parse_mode": "HTML"})
                        if not resp.is_success and resp.status_code == 400:
                            plain_text = (
                                f"🔴 Kirieshcka v2 отключена на ПК\n"
                                f"Ассистент завершил работу. Бот {bot_name} переведён в неактивный режим."
                            )
                            resp = client.post(url, json={"chat_id": cid, "text": plain_text})
                        if resp.is_success:
                            logger.info("telegram_notify_shutdown_success cid=%s", cid)
                        else:
                            logger.warning("telegram_notify_shutdown_failed cid=%s status=%s resp=%s", cid, resp.status_code, resp.text)
                    except Exception as send_err:
                        logger.warning("telegram_notify_shutdown_send_error cid=%s: %s", cid, send_err)
        except Exception as exc:
            logger.warning("telegram_notify_shutdown_client_failed: %s", exc)
