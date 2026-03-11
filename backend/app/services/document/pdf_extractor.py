"""
Servicio de extracción de texto de PDFs.
Usa PyMuPDF para texto nativo y Tesseract OCR como fallback.
"""
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
from dataclasses import dataclass
from typing import List


@dataclass
class PageContent:
    page_number: int
    text: str
    is_ocr: bool


def extract_text_from_pdf(pdf_path: str, start_page: int = 0) -> List[PageContent]:
    """
    Extrae texto de un PDF página por página.
    Si una página tiene poco texto (escaneada), aplica OCR con Tesseract.
    """
    pages: List[PageContent] = []

    with fitz.open(pdf_path) as doc:
        total_pages = len(doc)
        for page_num in range(start_page, total_pages):
            page = doc[page_num]
            text = page.get_text().strip()

            if len(text) < 50:
                # Página posiblemente escaneada, aplicar OCR
                pix = page.get_pixmap(dpi=300)
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                text = pytesseract.image_to_string(image, lang="spa")
                pages.append(PageContent(
                    page_number=page_num + 1,
                    text=text,
                    is_ocr=True,
                ))
            else:
                pages.append(PageContent(
                    page_number=page_num + 1,
                    text=text,
                    is_ocr=False,
                ))

    return pages


def get_total_pages(pdf_path: str) -> int:
    with fitz.open(pdf_path) as doc:
        return len(doc)
