"""
Genera un PDF en formato Harvard a partir de un HarvardCV.
Usa ReportLab (pure Python), compatible con Vercel.
"""
import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer


def generate_harvard_pdf(cv) -> bytes:
    """
    Recibe una instancia de HarvardCV y retorna los bytes del PDF generado.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=1.2 * inch,
        rightMargin=1.2 * inch,
        topMargin=1.0 * inch,
        bottomMargin=1.0 * inch,
    )

    name_style = ParagraphStyle(
        "HarvardName",
        fontName="Helvetica-Bold",
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    contact_style = ParagraphStyle(
        "HarvardContact",
        fontName="Helvetica",
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=14,
        textColor=colors.HexColor("#555555"),
    )
    heading_style = ParagraphStyle(
        "HarvardHeading",
        fontName="Helvetica-Bold",
        fontSize=11,
        spaceBefore=12,
        spaceAfter=3,
        textColor=colors.HexColor("#1a1a1a"),
    )
    body_style = ParagraphStyle(
        "HarvardBody",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        spaceAfter=2,
    )
    indent_style = ParagraphStyle(
        "HarvardIndent",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        spaceAfter=2,
        leftIndent=16,
    )

    story = []

    # Nombre centrado
    story.append(Paragraph(_safe(cv.name), name_style))

    # Contacto centrado
    if cv.contact and cv.contact.strip():
        story.append(Paragraph(_safe(cv.contact), contact_style))

    # Línea divisoria principal
    story.append(
        HRFlowable(width="100%", thickness=1.5, color=colors.black, spaceAfter=6)
    )

    # Secciones
    for section in cv.sections:
        story.append(Paragraph(_safe(section.heading.upper()), heading_style))
        story.append(
            HRFlowable(
                width="100%",
                thickness=0.5,
                color=colors.HexColor("#999999"),
                spaceAfter=4,
            )
        )
        for line in section.content.splitlines():
            stripped = line.strip()
            if not stripped:
                story.append(Spacer(1, 3))
                continue
            # Detectar bullet points y aplicar sangría
            is_bullet = stripped.startswith(("•", "-", "*", "·"))
            if is_bullet:
                text = "• " + stripped.lstrip("•-*· ").strip()
                story.append(Paragraph(_safe(text), indent_style))
            else:
                story.append(Paragraph(_safe(stripped), body_style))

    doc.build(story)
    return buffer.getvalue()


def _safe(text: str) -> str:
    """Escapa caracteres especiales HTML para ReportLab."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )