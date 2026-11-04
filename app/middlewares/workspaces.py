import asyncio
import os
import re
import shutil
import time
from pathlib import Path

from app.config import settings
from app.i18n import tr
from app.utils.logger import logger

# Only bot-generated UUID workspaces, including TemporaryDirectory suffixes.
_JOB = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}(?:_[a-zA-Z0-9_-]+)?")


def is_workspace(path: Path) -> bool:
    return bool(
        _JOB.fullmatch(path.name)
        and not path.is_symlink()
        and path.resolve().parent == settings.TEMP_DIR.resolve()
    )


async def clean_expired_workspaces():
    while True:
        cutoff = time.time() - 86400
        try:
            for path in settings.TEMP_DIR.iterdir():
                if is_workspace(path) and path.is_dir() and path.stat().st_mtime < cutoff:
                    # Detach before yielding so another update never reuses the directory.
                    retired = path.with_name(".expired-" + path.name)
                    path.rename(retired)
                    await asyncio.to_thread(shutil.rmtree, retired, True)
        except OSError:
            logger.exception("Could not sweep expired temporary files")
        await asyncio.sleep(3600)


class RefreshWorkspace:
    async def __call__(self, handler, event, data):
        state = data.get("state")
        if state:
            folder = (await state.get_data()).get("job_dir")
            if folder:
                path = Path(folder)
                if is_workspace(path) and path.is_dir():
                    os.utime(path)
                else:
                    await state.clear()
                    data["raw_state"] = None
                    message = event.message or (
                        event.callback_query and event.callback_query.message
                    )
                    if message:
                        await message.answer(tr("session_expired"))
        return await handler(event, data)
