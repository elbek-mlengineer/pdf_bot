from unittest.mock import AsyncMock, Mock

import pytest

from app.handlers import images
from app.handlers.filename import pdf_filename


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("Yillik hisobot", "Yillik hisobot.pdf"),
        ("Ўқув режаси.PDF", "Ўқув режаси.pdf"),
        ("../test", None),
        (".pdf", None),
        ("  ", None),
    ],
)
def test_pdf_filename(given, expected):
    assert pdf_filename(given) == expected


async def test_images_request_name_and_send_it(tmp_path, monkeypatch):
    state = AsyncMock()
    state.get_data.return_value = dict(
        files=["1.jpg"], job_dir=str(tmp_path), job_id="123", page_size="A4", orientation="portrait"
    )
    callback = AsyncMock()
    callback.data = "img_opt:A4:portrait"
    repo = AsyncMock()
    repo.count_active_user_jobs.return_value = 0
    monkeypatch.setattr(images, "Repository", repo)
    monkeypatch.setattr(images, "run_local", AsyncMock())
    await images.process_image_conversion(callback, state)
    state.set_state.assert_awaited_once_with(images.ImageFlow.waiting_for_name)
    message = AsyncMock()
    message.text = "Mening rasmlarim"
    message.from_user = Mock(id=5)
    await images.create_named_pdf(message, state)
    sent = message.answer_document.await_args.kwargs["document"]
    assert sent.filename == "Mening rasmlarim.pdf"
