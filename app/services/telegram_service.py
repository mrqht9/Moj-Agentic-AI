import re
import secrets
from datetime import datetime
from typing import Optional, Any, Dict
from urllib.parse import urlparse

import requests
from sqlalchemy.orm import Session

from app.auth.security import encrypt_credentials, decrypt_credentials
from app.db.models import TelegramIntegration, User


class TelegramService:
    BOT_TOKEN_PATTERN = re.compile(r"\b\d+:[A-Za-z0-9_-]{10,}\b")

    def _extract_bot_token(self, raw_value: str) -> str:
        value = (raw_value or "").strip()
        if not value:
            raise ValueError("Bot Token مطلوب")

        match = self.BOT_TOKEN_PATTERN.search(value)
        if not match:
            raise ValueError("Bot Token غير صالح. استخدم التوكن الحقيقي من BotFather بصيغة 123456789:ABC...")

        return match.group(0)

    def _validate_bot_token(self, bot_token: str) -> str:
        clean_token = self._extract_bot_token(bot_token)
        if ":" not in clean_token:
            raise ValueError("Bot Token غير صالح. استخدم التوكن الحقيقي من BotFather بصيغة 123456789:ABC...")

        token_id, token_secret = clean_token.split(":", 1)
        if not token_id.isdigit() or len(token_secret) < 10:
            raise ValueError("Bot Token غير صالح. استخدم التوكن الحقيقي من BotFather بصيغة 123456789:ABC...")

        return clean_token

    def _build_api_url(self, bot_token: str, method: str) -> str:
        return f"https://api.telegram.org/bot{bot_token}/{method}"

    def _normalize_base_url(self, base_url: str) -> str:
        normalized = (base_url or "").strip().rstrip("/")
        if not normalized:
            raise ValueError("Public Base URL مطلوب")

        parsed = urlparse(normalized)
        if parsed.scheme != "https":
            raise ValueError("Public Base URL يجب أن يبدأ بـ https://")

        if not parsed.netloc:
            raise ValueError("Public Base URL غير صالح")

        blocked_hosts = {"localhost", "127.0.0.1", "0.0.0.0"}
        if (parsed.hostname or "").lower() in blocked_hosts:
            raise ValueError("Public Base URL يجب أن يكون رابطًا عامًا وليس localhost")

        return normalized

    def _build_webhook_url(self, base_url: str, webhook_token: str) -> str:
        normalized = self._normalize_base_url(base_url)
        return f"{normalized}/api/telegram/webhook/{webhook_token}"

    def _generate_webhook_token(self) -> str:
        return secrets.token_urlsafe(32)

    def _parse_telegram_response(self, response: requests.Response, fallback_message: str) -> Dict[str, Any]:
        try:
            return response.json()
        except ValueError as exc:
            raise ValueError(fallback_message) from exc

    def _get_me(self, bot_token: str) -> Dict[str, Any]:
        try:
            response = requests.get(self._build_api_url(bot_token, "getMe"), timeout=20)
        except requests.RequestException as exc:
            raise ValueError(f"تعذر الاتصال بـ Telegram للتحقق من Bot Token: {str(exc)}") from exc

        data = self._parse_telegram_response(
            response,
            "تعذر قراءة استجابة Telegram أثناء التحقق من Bot Token",
        )
        if not response.ok or not data.get("ok"):
            raise ValueError(data.get("description", "فشل التحقق من Telegram Bot Token"))
        return data["result"]

    def _set_webhook(self, bot_token: str, webhook_url: str) -> None:
        try:
            response = requests.post(
                self._build_api_url(bot_token, "setWebhook"),
                json={"url": webhook_url},
                timeout=20,
            )
        except requests.RequestException as exc:
            raise ValueError(f"تعذر الاتصال بـ Telegram لإعداد Webhook: {str(exc)}") from exc

        data = self._parse_telegram_response(
            response,
            "تعذر قراءة استجابة Telegram أثناء إعداد Webhook",
        )
        if not response.ok or not data.get("ok"):
            description = data.get("description", "فشل إعداد Telegram webhook")
            raise ValueError(f"{description} | webhook_url={webhook_url}")

    def _delete_webhook(self, bot_token: str) -> None:
        try:
            response = requests.post(self._build_api_url(bot_token, "deleteWebhook"), timeout=20)
        except requests.RequestException as exc:
            raise ValueError(f"تعذر الاتصال بـ Telegram لحذف Webhook: {str(exc)}") from exc

        data = self._parse_telegram_response(
            response,
            "تعذر قراءة استجابة Telegram أثناء حذف Webhook",
        )
        if not response.ok or not data.get("ok"):
            raise ValueError(data.get("description", "فشل حذف Telegram webhook"))

    def _send_message(self, bot_token: str, chat_id: str, text: str) -> None:
        try:
            response = requests.post(
                self._build_api_url(bot_token, "sendMessage"),
                json={"chat_id": chat_id, "text": text},
                timeout=20,
            )
        except requests.RequestException as exc:
            raise ValueError(f"تعذر الاتصال بـ Telegram لإرسال الرسالة: {str(exc)}") from exc

        data = self._parse_telegram_response(
            response,
            "تعذر قراءة استجابة Telegram أثناء إرسال الرسالة",
        )
        if not response.ok or not data.get("ok"):
            raise ValueError(data.get("description", "فشل إرسال الرسالة إلى Telegram"))

    def _build_chat_id_help_message(self, incoming_chat_id: str) -> str:
        return (
            "مرحبًا بك في تكامل موج مع Telegram!\n\n"
            f"هذا هو Chat ID الخاص بك: {incoming_chat_id}\n\n"
            "انسخه وضعه في إعدادات الحساب داخل موج لإكمال الربط، ثم أعد إرسال رسالتك هنا."
        )

    def get_user_integration(self, db: Session, user_id: int) -> Optional[TelegramIntegration]:
        return db.query(TelegramIntegration).filter(TelegramIntegration.user_id == user_id).first()

    def get_integration_by_webhook_token(self, db: Session, webhook_token: str) -> Optional[TelegramIntegration]:
        return db.query(TelegramIntegration).filter(TelegramIntegration.webhook_token == webhook_token).first()

    def upsert_integration(self, db: Session, user: User, bot_token: str, chat_id: str, base_url: str) -> TelegramIntegration:
        clean_bot_token = self._validate_bot_token(bot_token)
        clean_chat_id = str(chat_id or "").strip()
        clean_base_url = self._normalize_base_url(base_url)

        bot_info = self._get_me(clean_bot_token)
        integration = self.get_user_integration(db, user.id)
        webhook_token = integration.webhook_token if integration else self._generate_webhook_token()
        webhook_url = self._build_webhook_url(clean_base_url, webhook_token)

        self._set_webhook(clean_bot_token, webhook_url)

        if integration is None:
            integration = TelegramIntegration(
                user_id=user.id,
                encrypted_bot_token=encrypt_credentials(clean_bot_token),
                chat_id=clean_chat_id,
                webhook_token=webhook_token,
                webhook_url=webhook_url,
                is_enabled=True,
                bot_username=bot_info.get("username"),
                bot_display_name=bot_info.get("first_name"),
                last_connected_at=datetime.utcnow(),
                last_error=None,
            )
            db.add(integration)
        else:
            integration.encrypted_bot_token = encrypt_credentials(clean_bot_token)
            integration.chat_id = clean_chat_id
            integration.webhook_url = webhook_url
            integration.is_enabled = True
            integration.bot_username = bot_info.get("username")
            integration.bot_display_name = bot_info.get("first_name")
            integration.last_connected_at = datetime.utcnow()
            integration.last_error = None

        db.commit()
        db.refresh(integration)
        return integration

    def set_enabled(self, db: Session, integration: TelegramIntegration, is_enabled: bool) -> TelegramIntegration:
        bot_token = decrypt_credentials(integration.encrypted_bot_token)
        if is_enabled:
            if integration.webhook_url:
                self._set_webhook(bot_token, integration.webhook_url)
        else:
            self._delete_webhook(bot_token)
        integration.is_enabled = is_enabled
        integration.last_error = None
        integration.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(integration)
        return integration

    def delete_integration(self, db: Session, integration: TelegramIntegration) -> None:
        try:
            bot_token = decrypt_credentials(integration.encrypted_bot_token)
            self._delete_webhook(bot_token)
        except Exception:
            pass
        db.delete(integration)
        db.commit()

    def process_webhook_update(self, db: Session, integration: TelegramIntegration, update: Dict[str, Any], agent_manager: Any) -> Dict[str, Any]:
        if not integration.is_enabled:
            return {"ok": True, "ignored": "disabled"}

        message = update.get("message") or update.get("edited_message") or {}
        chat = message.get("chat") or {}
        incoming_chat_id = str(chat.get("id", ""))
        text = (message.get("text", "") or "").strip()

        bot_token = decrypt_credentials(integration.encrypted_bot_token)

        if not text:
            return {"ok": True, "ignored": "no_text"}

        if text.lower() in {"/start", "/chatid", "/get_chat_id"}:
            self._send_message(bot_token, incoming_chat_id, self._build_chat_id_help_message(incoming_chat_id))
            integration.last_error = None
            integration.last_connected_at = datetime.utcnow()
            db.commit()
            return {"ok": True, "sent": True, "command": "chat_id_help"}

        if incoming_chat_id != str(integration.chat_id):
            integration.last_error = f"رفض الرسالة من chat_id غير مطابق: {incoming_chat_id}"
            self._send_message(bot_token, incoming_chat_id, self._build_chat_id_help_message(incoming_chat_id))
            db.commit()
            return {"ok": True, "ignored": "chat_id_mismatch"}

        agent_result = agent_manager.process_user_message(
            message=text,
            user_id=integration.user_id,
            session_id=f"telegram:{integration.chat_id}",
            metadata={
                "source": "telegram",
                "telegram_chat_id": integration.chat_id,
                "telegram_update_id": update.get("update_id"),
            },
            db=db,
        )

        response_message = agent_result.get("message") or "عذرًا، لم أتمكن من معالجة رسالتك الآن."
        self._send_message(bot_token, integration.chat_id, response_message)
        integration.last_error = None
        integration.last_connected_at = datetime.utcnow()
        db.commit()
        return {"ok": True, "sent": True}


telegram_service = TelegramService()
