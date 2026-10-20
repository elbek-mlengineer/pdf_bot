import time
from collections.abc import Awaitable, Callable
from typing import Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from app.config import settings
from app.utils.logger import logger


class DistributedRateLimitMiddleware(BaseMiddleware):
    def __init__(self, redis_url: str = "", limit_per_minute: int = 20):
        super().__init__()
        self.limit = limit_per_minute
        self.requests: dict[int, list[float]] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if not user or user.id in settings.ADMIN_IDS:
            return await handler(event, data)

        now = time.time()
        user_timestamps = self.requests.setdefault(user.id, [])
        
        # 60 sekunddan eski so'rovlarni tozalaymiz
        user_timestamps = [t for t in user_timestamps if now - t < 60]
        self.requests[user.id] = user_timestamps

        if len(user_timestamps) >= self.limit:
            logger.warning("User %d exceeded rate limit (%d/min)", user.id, self.limit)
            return

        user_timestamps.append(now)
        return await handler(event, data)