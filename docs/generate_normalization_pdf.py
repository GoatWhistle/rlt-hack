"""Render the normalizer and classifier description as a readable A4 PDF."""

import re
from collections.abc import Iterator
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

SOURCE = Path(__file__).resolve().parent / "normalization-and-classification.md"
OUTPUT = Path(__file__).with_name("normalization-and-classification.pdf")

INK = HexColor("#172238")
MUTED = HexColor("#5d6b80")
ACCENT = HexColor("#2671a8")


def font_path(*candidates: str) -> str:
    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate
    raise FileNotFoundError("Нужен шрифт Arial или DejaVu Sans, поддерживающий кириллицу")


pdfmetrics.registerFont(TTFont("Body", font_path(
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)))
pdfmetrics.registerFont(TTFont("BodyBold", font_path(
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)))
pdfmetrics.registerFont(TTFont("BodyMono", font_path(
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
)))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="BodyBold")

TITLE = ParagraphStyle(
    "Title", fontName="BodyBold", fontSize=22, leading=27, textColor=INK, spaceAfter=4,
)
LEAD = ParagraphStyle(
    "Lead", fontName="Body", fontSize=10, leading=15, textColor=MUTED, spaceAfter=18,
)
HEADING = ParagraphStyle(
    "Heading", fontName="BodyBold", fontSize=14, leading=19, textColor=ACCENT,
    spaceBefore=16, spaceAfter=7,
)
BODY = ParagraphStyle(
    "Body", fontName="Body", fontSize=10.5, leading=16, textColor=INK,
    alignment=TA_JUSTIFY, spaceAfter=9,
)
BULLET = ParagraphStyle("Bullet", parent=BODY, alignment=0, spaceAfter=3)

INLINE_CODE = re.compile(r"`([^`]+)`")
INLINE_BOLD = re.compile(r"\*\*([^*]+)\*\*")


def inline(text: str) -> str:
    """Переводит жирный текст и обратные кавычки в разметку reportlab."""
    parts = []
    for index, chunk in enumerate(INLINE_CODE.split(text)):
        if index % 2:
            parts.append(f'<font name="BodyMono" size="9.5">{escape(chunk)}</font>')
        else:
            parts.append(INLINE_BOLD.sub(r"<b>\1</b>", escape(chunk)))
    return "".join(parts)


def blocks(markdown: str) -> Iterator[tuple[str, str | list[str]]]:
    """Читает документ по абзацам: заголовки, списки и обычный текст."""
    lines = markdown.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].rstrip()
        if not line:
            index += 1
        elif line.startswith("# "):
            yield "title", line[2:]
            index += 1
        elif line.startswith("## "):
            yield "heading", line[3:]
            index += 1
        elif line.startswith("- "):
            items: list[str] = []
            while index < len(lines) and lines[index].startswith(("- ", "  ")):
                if lines[index].startswith("- "):
                    items.append(lines[index][2:].strip())
                else:
                    items[-1] += " " + lines[index].strip()
                index += 1
            yield "list", items
        else:
            paragraph: list[str] = []
            while index < len(lines) and lines[index].strip():
                if lines[index].startswith(("#", "- ")):
                    break
                paragraph.append(lines[index].strip())
                index += 1
            yield "paragraph", " ".join(paragraph)


def decorate(canvas: Canvas, document: SimpleDocTemplate) -> None:
    """Колонтитул: название документа слева, номер страницы справа."""
    canvas.saveState()
    canvas.setFont("Body", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(22 * mm, 12 * mm, "Нормализатор и классификатор")
    canvas.drawRightString(A4[0] - 22 * mm, 12 * mm, str(document.page))
    canvas.restoreState()


def build() -> None:
    document = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4,
        leftMargin=22 * mm, rightMargin=22 * mm, topMargin=20 * mm, bottomMargin=20 * mm,
        title="Нормализатор и классификатор", author="rlt-hack",
    )
    story = []
    first_lead = True
    for kind, value in blocks(SOURCE.read_text(encoding="utf-8")):
        if kind == "title":
            story.append(Paragraph(inline(value), TITLE))
        elif kind == "heading":
            story.append(Paragraph(inline(value), HEADING))
        elif kind == "list":
            story.append(ListFlowable(
                [ListItem(Paragraph(inline(item), BULLET), leftIndent=12) for item in value],
                bulletType="bullet", bulletFontName="Body", bulletFontSize=7,
                start="•", leftIndent=12, spaceAfter=9,
            ))
        elif first_lead:
            story.append(Paragraph(inline(value), LEAD))
            first_lead = False
        else:
            story.append(Paragraph(inline(value), BODY))
    story.append(Spacer(1, 2 * mm))
    document.build(story, onFirstPage=decorate, onLaterPages=decorate)
    print(f"Готово: {OUTPUT}")


if __name__ == "__main__":
    build()
