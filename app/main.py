import asyncio
from pathlib import Path

from app.bot import bot, dp
from app.commands import register_commands
from app.config import settings
from app.database.session import init_db
from app.handlers import admin, common, documents, filename, images, merge, rename, text, tools
from app.handlers import settings as settings_handler
from app.middlewares.rate_limit import DistributedRateLimitMiddleware
from app.middlewares.workspaces import RefreshWorkspace, clean_expired_workspaces
from app.utils.logger import logger


async def main() -> None:
    ready = Path("/tmp/pdfbot-ready") if settings.QUEUE_ALL_CONVERSIONS else None
    if ready:
        ready.unlink(missing_ok=True)
    logger.info("Initializing PostgreSQL database schema...")
    await init_db()

    logger.info("Registering middlewares and routers...")
    dp.update.middleware(
        DistributedRateLimitMiddleware(
            redis_url=settings.REDIS_URL,
            limit_per_minute=settings.RATE_LIMIT_CALLS_PER_MINUTE,
        )
    )

    dp.update.middleware(RefreshWorkspace())

    dp.include_router(admin.router)
    dp.include_router(common.router)
    dp.include_router(settings_handler.router)
    dp.include_router(filename.router)
    dp.include_router(rename.router)
    dp.include_router(images.router)
    dp.include_router(text.router)
    dp.include_router(documents.router)
    dp.include_router(merge.router)
    dp.include_router(tools.router)

    logger.info("Starting Telegram Bot polling...")
    cleanup = asyncio.create_task(clean_expired_workspaces())
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await register_commands(bot)
        if ready:
            ready.touch()
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        cleanup.cancel()
        await asyncio.gather(cleanup, return_exceptions=True)
        if ready:
            ready.unlink(missing_ok=True)
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped gracefully.")
