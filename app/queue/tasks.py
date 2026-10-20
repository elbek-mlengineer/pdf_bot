import asyncio
from pathlib import Path
from app.converters.doc_to_pdf import DocumentToPdfConverter
from app.converters.image_to_pdf import ImageToPdfConverter
from app.converters.pdf_tools import PdfTools
from app.converters.text_to_pdf import TextToPdfConverter


def run_image_to_pdf_job(
    image_paths_str: list[str],
    output_path_str: str,
    page_size: str,
    orientation: str,
    margin: int = 18,
) -> str:
    image_paths = [Path(p) for p in image_paths_str]
    out_p = Path(output_path_str)
    res = ImageToPdfConverter.convert_images(
        image_paths=image_paths,
        output_pdf_path=out_p,
        page_size=page_size,
        orientation=orientation,
        margin=margin,
    )
    return str(res)


def run_text_to_pdf_job(text: str, output_path_str: str, title: str) -> str:
    out_p = Path(output_path_str)
    res = TextToPdfConverter.convert_text(text=text, output_pdf_path=out_p, title=title)
    return str(res)


def run_doc_to_pdf_job(input_path_str: str, output_dir_str: str) -> str:
    input_path = Path(input_path_str)
    output_dir = Path(output_dir_str)
    res = asyncio.run(DocumentToPdfConverter.convert(input_path, output_dir))
    return str(res)


def run_merge_pdf_job(pdf_paths_str: list[str], output_path_str: str) -> str:
    pdf_paths = [Path(p) for p in pdf_paths_str]
    out_p = Path(output_path_str)
    res = PdfTools.merge_pdfs(pdf_paths, out_p)
    return str(res)


def run_pdf_tool_job(
    tool_name: str,
    input_path_str: str,
    output_path_str: str,
    param: str = "",
) -> str:
    in_p = Path(input_path_str)
    out_p = Path(output_path_str)

    if tool_name == "compress":
        return str(PdfTools.compress_pdf(in_p, out_p))
    if tool_name == "rotate":
        return str(PdfTools.rotate_pdf(in_p, out_p, angle=int(param or "90")))
    if tool_name == "extract_pages":
        return str(PdfTools.extract_pages(in_p, out_p, page_spec=param))
    if tool_name == "split":
        return str(PdfTools.split_pdf_to_zip(in_p, out_p))
    if tool_name == "page_numbers":
        return str(PdfTools.add_page_numbers(in_p, out_p))
    if tool_name == "extract_images":
        return str(PdfTools.extract_images_to_zip(in_p, out_p))
    if tool_name == "metadata":
        parts = param.split("|", 1)
        title = parts[0].strip()
        author = parts[1].strip() if len(parts) > 1 else ""
        return str(PdfTools.update_metadata(in_p, out_p, title=title, author=author))

    raise ValueError(f"Unknown PDF tool: {tool_name}")
