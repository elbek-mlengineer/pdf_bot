from app.database.repositories import Repository


class RecordUser:
    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user and not user.is_bot:
            await Repository.upsert_user(user.id, user.username, user.first_name, user.last_name)
        return await handler(event, data)
