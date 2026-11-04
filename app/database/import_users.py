"""Import user profiles from an old SQLite copy without overwriting live profiles."""

import asyncio
import sqlite3
import sys
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert

from app.database.models import User, UserSettings
from app.database.session import AsyncSessionLocal, init_db


async def import_users(source: Path):
    if not source.is_file():
        raise FileNotFoundError(source)
    await init_db()
    with sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True) as old:
        old.row_factory = sqlite3.Row
        users = old.execute(
            "SELECT telegram_id, username, first_name, last_name, created_at FROM users"
        )
        from datetime import datetime, timezone

        count = 0
        async with AsyncSessionLocal.begin() as session:
            if session.get_bind().dialect.name != "postgresql":
                raise RuntimeError("The destination must be PostgreSQL")
            for row in users:
                profile = dict(row)
                stamp = datetime.fromisoformat(profile["created_at"])
                profile["created_at"] = (
                    stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)
                )
                inserted = await session.scalar(
                    insert(User)
                    .values(**profile)
                    .on_conflict_do_nothing(index_elements=[User.telegram_id])
                    .returning(User.telegram_id)
                )
                if inserted is not None:
                    await session.execute(
                        insert(UserSettings)
                        .values(user_id=inserted)
                        .on_conflict_do_nothing(index_elements=[UserSettings.user_id])
                    )
                    count += 1
    print(f"Imported user profiles: {count}")


if __name__ == "__main__":
    asyncio.run(import_users(Path(sys.argv[1])))
