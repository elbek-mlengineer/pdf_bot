from aiogram.fsm.storage.base import StorageKey

from app.i18n import LANGUAGES, current_language


def language_key(bot_id, user_id):
    return StorageKey(bot_id=bot_id, chat_id=user_id, user_id=user_id, destiny="language")


class LanguageMiddleware:
    def __init__(self, storage):
        self.storage = storage

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)
        saved = await self.storage.get_data(language_key(data["bot"].id, user.id))
        code = saved.get("language") or (user.language_code or "en").lower().split("-")[0]
        token = current_language.set(code if code in LANGUAGES else "en")
        try:
            return await handler(event, data)
        finally:
            current_language.reset(token)
