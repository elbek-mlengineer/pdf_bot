from types import SimpleNamespace
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import repositories
from app.database.models import Base, User, UserActivity
from app.handlers import admin
from app.middlewares.users import RecordUser


async def test_first_message_registers_and_updates_without_resetting_preferences(
    tmp_path, monkeypatch
):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'registry.db').as_posix()}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(repositories, "AsyncSessionLocal", sessions)
    monkeypatch.setattr(admin, "AsyncSessionLocal", sessions)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        middleware = RecordUser()
        user = SimpleNamespace(
            id=42, is_bot=False, username=None, first_name="Test", last_name=None
        )
        await middleware(AsyncMock(), None, {"event_from_user": user})
        async with sessions() as session:
            first = (await session.get(User, 42)).created_at
        await repositories.Repository.update_user_settings(42, page_size="A5")
        user.first_name = "Test <updated>"
        await middleware(AsyncMock(), None, {"event_from_user": user})
        async with sessions() as session:
            updated = await session.get(User, 42)
            assert updated.first_name == user.first_name and updated.created_at == first
            assert (await session.get(UserActivity, 42)).last_seen_at
        assert (await repositories.Repository.get_user_settings(42)).page_size == "A5"
        monkeypatch.setattr(admin.settings, "ADMIN_IDS", [99])
        msg = AsyncMock()
        msg.text = "/users"
        msg.chat.type = "private"
        msg.from_user.id = 99
        await admin.show_users(msg)
        assert "&lt;updated&gt;" in msg.answer.await_args.args[0]
        for chat, uid in [("group", 99), ("private", 42)]:
            msg.chat.type, msg.from_user.id = chat, uid
            await admin.show_users(msg)
            assert msg.answer.await_args.args[0] == admin.tr("unauthorized")
    finally:
        await engine.dispose()
