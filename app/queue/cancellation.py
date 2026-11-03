import asyncio
from contextlib import contextmanager

from aiogram.filters import Command

from app.i18n import tr


class ConversionCancelled(Exception):
    pass


_active = {}


@contextmanager
def cancellation_scope(key):
    signal = asyncio.Event()
    _active[key] = signal
    try:
        yield signal
    finally:
        _active.pop(key, None)


class CancelActiveConversion:
    """Accept cancellation before FSM isolation locks the user's session."""

    def __init__(self, fsm):
        self.fsm = fsm
        self.command = Command("cancel")

    async def __call__(self, handler, event, data):
        context = self.fsm.resolve_event_context(data["bot"], data)
        signal = _active.get(context.key) if context else None
        if signal is not None:
            callback = event.callback_query
            if callback and callback.data == "action:cancel":
                signal.set()
                await callback.answer(tr("stopping"))
                return
            if event.message and await self.command(event.message, data["bot"]):
                signal.set()
                await event.message.answer(tr("stopping"))
                return
        return await handler(event, data)
