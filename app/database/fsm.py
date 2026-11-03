from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, DefaultKeyBuilder, StorageKey

from app.database.models import BotSession
from app.database.session import AsyncSessionLocal


class SessionStorage(BaseStorage):
    """Keep unfinished conversations in the same database as the user's settings."""

    def __init__(self, sessions=AsyncSessionLocal):
        self.sessions = sessions
        self.keys = DefaultKeyBuilder(
            with_bot_id=True, with_business_connection_id=True, with_destiny=True
        )

    async def get_state(self, key: StorageKey):
        async with self.sessions() as session:
            row = await session.get(BotSession, self.keys.build(key))
            return row.state if row else None

    async def get_data(self, key: StorageKey):
        async with self.sessions() as session:
            row = await session.get(BotSession, self.keys.build(key))
            return row.data if row else {}

    async def set_state(self, key: StorageKey, state=None):
        await self._update(key, state=state.state if isinstance(state, State) else state)

    async def set_data(self, key: StorageKey, data):
        await self._update(key, data=dict(data))

    async def _update(self, key, **changes):
        session_key = self.keys.build(key)
        async with self.sessions.begin() as session:
            row = await session.get(BotSession, session_key)
            if row is None:
                if any(changes.values()):
                    session.add(BotSession(key=session_key, **changes))
                return
            for field, value in changes.items():
                setattr(row, field, value)
            if row.state is None and not row.data:
                await session.delete(row)

    async def close(self):
        pass  # The application's database engine owns the connection pool.
