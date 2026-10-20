from PIL import Image
from pypdf import PdfReader
from app.converters.image_to_pdf import ImageToPdfConverter
from app.converters.pdf_tools import PdfTools
from app.converters.text_to_pdf import TextToPdfConverter


def test_single_and_multiple_images_to_pdf(temp_dir):
    img1 = temp_dir / "transparent.png"
    img2 = temp_dir / "photo.jpg"
    img3 = temp_dir / "graphic.webp"

    Image.new("RGBA", (800, 600), (255, 0, 0, 128)).save(img1, "PNG")
    Image.new("RGB", (600, 800), (0, 255, 0)).save(img2, "JPEG")
    Image.new("RGB", (500, 500), (0, 0, 255)).save(img3, "WEBP")

    out_pdf = temp_dir / "combined.pdf"
    ImageToPdfConverter.convert_images(
        image_paths=[img1, img2, img3],
        output_pdf_path=out_pdf,
        page_size="A4",
        orientation="landscape",
    )

    assert out_pdf.exists()
    reader = PdfReader(str(out_pdf))
    assert len(reader.pages) == 3


def test_text_to_pdf_uzbek_and_multipage(temp_dir):
    uzbek_text = (
        "# O'zbekiston va Texnologiya\n\n"
        "O‘zbekiston Respublikasida zamonaviy axborot texnologiyalari va g‘oyalar rivojlanmoqda.\n\n"
        "Ўзбекистон Республикасида замонавий ахборот технологиялари: ў, қ, ғ, ҳ ҳарфлари синови.\n\n"
        + ("Bu ko'p sahifali matn tekshiruvi uchun takrorlanuvchi paragraf. " * 120)
    )
    out_pdf = temp_dir / "uzbek_text.pdf"
    TextToPdfConverter.convert_text(uzbek_text, out_pdf, title="Uzbek Unicode Test")

    assert out_pdf.exists()
    reader = PdfReader(str(out_pdf))
    assert len(reader.pages) >= 2


def test_pdf_tools_merge_rotate_extract_numbers(temp_dir):
    p1 = temp_dir / "p1.pdf"
    p2 = temp_dir / "p2.pdf"
    TextToPdfConverter.convert_text("Page 1 content", p1, title="Doc 1")
    TextToPdfConverter.convert_text("Page 2 content", p2, title="Doc 2")

    merged = temp_dir / "merged.pdf"
    PdfTools.merge_pdfs([p1, p2], merged)
    assert len(PdfReader(str(merged)).pages) == 2

    rotated = temp_dir / "rotated.pdf"
    PdfTools.rotate_pdf(merged, rotated, angle=90)
    assert rotated.exists()

    extracted = temp_dir / "extracted.pdf"
    PdfTools.extract_pages(merged, extracted, "2")
    assert len(PdfReader(str(extracted)).pages) == 1

    numbered = temp_dir / "numbered.pdf"
    PdfTools.add_page_numbers(merged, numbered)
    assert len(PdfReader(str(numbered)).pages) == 2

    split_zip = temp_dir / "split.zip"
    PdfTools.split_pdf_to_zip(merged, split_zip)
    assert split_zip.exists()
