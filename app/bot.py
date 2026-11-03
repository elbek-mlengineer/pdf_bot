from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import SimpleEventIsolation

from app.config import settings
from app.database.fsm import SessionStorage
from app.middlewares.language import LanguageMiddleware
from app.queue.cancellation import CancelActiveConversion

bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

storage = SessionStorage()
dp = Dispatcher(storage=storage, events_isolation=SimpleEventIsolation())
dp.update.outer_middleware.unregister(dp.fsm)
dp.update.outer_middleware(LanguageMiddleware(storage))
dp.update.outer_middleware(CancelActiveConversion(dp.fsm))
dp.update.outer_middleware(dp.fsm)
