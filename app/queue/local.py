import asyncio
import json
import sys

from app.queue.cancellation import ConversionCancelled


async def run_local(kind, args, signal):
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "app.queue.local", kind,
        stdin=asyncio.subprocess.PIPE,
    )
    work = asyncio.create_task(process.communicate(json.dumps(args).encode()))
    stop = asyncio.create_task(signal.wait())
    try:
        await asyncio.wait((work, stop), return_when=asyncio.FIRST_COMPLETED)
        if signal.is_set():
            raise ConversionCancelled
        await work
        if process.returncode:
            raise RuntimeError("PDF conversion failed.")
    finally:
        stop.cancel()
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        await asyncio.gather(work, stop, return_exceptions=True)
        await process.wait()


if __name__ == "__main__":
    from app.queue.tasks import run_image_to_pdf_job, run_text_to_pdf_job

    converters = {"images": run_image_to_pdf_job, "text": run_text_to_pdf_job}
    converters[sys.argv[1]](*json.load(sys.stdin.buffer))
