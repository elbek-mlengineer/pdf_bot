from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from app.config import settings
from app.utils.logger import logger


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count: int):
        self.saveState()
        font_name = "CustomMainFont" if TextToPdfConverter._font_ok else "Helvetica"
        self.setFont(font_name, 9)
        self.setFillColorRGB(0.35, 0.35, 0.35)
        text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 54, 36, text)
        self.restoreState()


class TextToPdfConverter:
    _fonts_checked = False
    _font_ok = False
    _bold_ok = False

    @classmethod
    def register_fonts(cls) -> None:
        if cls._fonts_checked:
            return

        font_paths = [
            settings.FONTS_DIR / "DejaVuSans.ttf",
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
            Path("C:/Windows/Fonts/arial.ttf"),
        ]
        bold_paths = [
            settings.FONTS_DIR / "DejaVuSans-Bold.ttf",
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
            Path("C:/Windows/Fonts/arialbd.ttf"),
        ]

        for fp in font_paths:
            if fp.exists():
                pdfmetrics.registerFont(TTFont("CustomMainFont", str(fp)))
                cls._font_ok = True
                break

        for bp in bold_paths:
            if bp.exists():
                pdfmetrics.registerFont(TTFont("CustomMainFont-Bold", str(bp)))
                cls._bold_ok = True
                break

        cls._fonts_checked = True

    @classmethod
    def convert_text(
        cls,
        text: str,
        output_pdf_path: Path,
        title: str = "Document",
    ) -> Path:
        cls.register_fonts()
        font_name = "CustomMainFont" if cls._font_ok else "Helvetica"
        bold_font_name = "CustomMainFont-Bold" if cls._bold_ok else font_name

        output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(
            str(output_pdf_path),
            pagesize=A4,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName=bold_font_name,
            fontSize=15,
            leading=20,
            spaceAfter=14,
            textColor="#111827",
        )
        heading_style = ParagraphStyle(
            "DocHeading",
            parent=styles["Normal"],
            fontName=bold_font_name,
            fontSize=12.5,
            leading=18,
            spaceBefore=10,
            spaceAfter=6,
            textColor="#111827",
        )
        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=10.5,
            leading=16,
            spaceAfter=8,
            textColor="#1f2937",
        )

        story = []
        if title:
            story.append(Paragraph(escape(title), title_style))
            story.append(Spacer(1, 8))

        blocks = text.split("\n\n")
        for block in blocks:
            clean_b = block.strip()
            if not clean_b:
                continue
            if clean_b.startswith("# "):
                story.append(Paragraph(escape(clean_b[2:].strip()), heading_style))
            else:
                safe_text = escape(clean_b).replace("\n", "<br/>")
                story.append(Paragraph(safe_text, body_style))

        if not story:
            story.append(Paragraph(escape(text or "Empty document"), body_style))

        doc.build(story, canvasmaker=NumberedCanvas)
        logger.info("Rendered text PDF: %s", output_pdf_path)
        return output_pdf_path
