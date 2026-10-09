"""
OCR service: extrae texto de PDFs escaneados usando la API de visión de OpenAI.
Se invoca como fallback cuando pdfplumber no encuentra texto seleccionable.
"""
import base64
import io


def extract_text_with_ocr(file_bytes: bytes, api_key: str, model: str) -> str:
    """
    Renderiza cada página del PDF como imagen PNG y usa GPT-4o-mini Vision
    para extraer el texto visible. Retorna el texto combinado de todas las páginas.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise RuntimeError("PyMuPDF (pymupdf) no está instalado.") from exc

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("La dependencia 'openai' no está instalada.") from exc

    client = OpenAI(api_key=api_key, timeout=60.0)
    doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
    all_text: list[str] = []

    for page in doc:
        # Zoom 2× para mejor calidad de OCR
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        png_bytes = pix.tobytes("png")
        b64 = base64.b64encode(png_bytes).decode()

        response = client.chat.completions.create(
            model=model,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Extrae todo el texto visible en esta imagen de currículum vitae. "
                                "Devuelve únicamente el texto tal como aparece, sin interpretaciones "
                                "ni comentarios adicionales. Preserva la estructura original "
                                "usando saltos de línea donde corresponda."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
        )
        page_text = response.choices[0].message.content
        if page_text and page_text.strip():
            all_text.append(page_text.strip())

    doc.close()
    return "\n\n".join(all_text).strip()
