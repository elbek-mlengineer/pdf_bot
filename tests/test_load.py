import concurrent.futures
import time
from pathlib import Path
from PIL import Image
from app.converters.image_to_pdf import ImageToPdfConverter
from app.converters.text_to_pdf import TextToPdfConverter


def _worker_task(idx: int, base_dir: Path) -> float:
    user_dir = base_dir / f"user_{idx}"
    user_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()

    img_path = user_dir / "sample.jpg"
    Image.new("RGB", (1000, 1000), (idx * 10 % 255, 100, 150)).save(img_path, "JPEG")

    out_img_pdf = user_dir / "img.pdf"
    ImageToPdfConverter.convert_images([img_path], out_img_pdf, page_size="A4")

    out_txt_pdf = user_dir / "txt.pdf"
    TextToPdfConverter.convert_text(f"User {idx} concurrent test O‘zbekiston", out_txt_pdf)

    assert out_img_pdf.exists() and out_txt_pdf.exists()
    return (time.perf_counter() - t0) * 1000


def test_concurrent_user_isolation_and_throughput(temp_dir):
    num_users = 16
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        latencies = list(pool.map(lambda i: _worker_task(i, temp_dir), range(num_users)))

    assert len(latencies) == num_users
    median_ms = sorted(latencies)[len(latencies) // 2]
    assert median_ms < 5000
