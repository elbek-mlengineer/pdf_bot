from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.methods import EditMessageCaption, EditMessageText, SendDocument, SendMessage


class BotSignature(BaseRequestMiddleware):
    async def __call__(self, make_request, bot, method):
        if isinstance(method, (SendMessage, EditMessageText)):
            field = "text"
        elif isinstance(method, (SendDocument, EditMessageCaption)):
            field = "caption"
        else:
            return await make_request(bot, method)

        username = (await bot.me()).username
        if username:
            signature = f"@{username}"
            body = (getattr(method, field) or "").rstrip()
            if body.split("\n")[-1] != signature:
                signed = f"{body}\n\n{signature}" if body else signature
                method = method.model_copy(update={field: signed})
        return await make_request(bot, method)
