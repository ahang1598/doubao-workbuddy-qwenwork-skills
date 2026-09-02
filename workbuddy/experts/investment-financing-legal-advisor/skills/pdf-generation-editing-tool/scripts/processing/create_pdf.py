import sys
import importlib.util


def ensure_deps():
    missing = [p for p in ("reportlab",) if importlib.util.find_spec(p) is None]
    if missing:
        import subprocess
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install",
             "--break-system-packages", "-q"] + missing
        )

ensure_deps()

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# Register Chinese font - mandatory for Chinese text
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
CHINESE_FONT = 'STSong-Light'


def create_pdf_from_text(output_pdf_path, text_content, title=None):
    """Create a PDF with Chinese text embedded, no tofu boxes, proper formatting"""
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm
    )

    styles = getSampleStyleSheet()

    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontName=CHINESE_FONT,
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        spaceAfter=1.5 * cm
    )

    # Body text style
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontName=CHINESE_FONT,
        fontSize=12,
        leading=18,
        alignment=TA_LEFT,
        firstLineIndent=2 * 12,  # First line indent = 2 chars
        spaceAfter=0.5 * cm
    )

    story = []

    # Add title
    if title:
        story.append(Paragraph(title, title_style))

    # Add body content (convert line breaks to <br/> for Paragraph)
    paragraphs = text_content.split('\n\n')  # Split by empty lines for paragraphs
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # Convert single line breaks to <br/>
        para = para.replace('\n', '<br/>')
        story.append(Paragraph(para, body_style))

    # Build PDF
    doc.build(story)
    print(f"Successfully created PDF: {output_pdf_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_pdf.py <output.pdf> \"<text content>\" [title]")
        print("Or: python create_pdf.py <output.pdf> @input.txt [title]")
        sys.exit(1)

    output_pdf = sys.argv[1]
    text_arg = sys.argv[2]

    if text_arg.startswith('@'):
        with open(text_arg[1:], 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        text = text_arg

    title = sys.argv[3] if len(sys.argv) > 3 else None
    create_pdf_from_text(output_pdf, text, title)
