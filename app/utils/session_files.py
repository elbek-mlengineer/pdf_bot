import shutil
from pathlib import Path

from aiogram.fsm.context import FSMContext


async def clear_session(state: FSMContext) -> None:
    data = await state.get_data()
    job_dir = data.get("job_dir")
    if job_dir:
        shutil.rmtree(Path(job_dir), ignore_errors=True)
    await state.clear()
