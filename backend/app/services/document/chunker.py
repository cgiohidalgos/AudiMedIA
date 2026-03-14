"""
Servicio de chunking de texto extraído de PDFs.
Divide el texto por páginas en fragmentos de ~400 palabras para uso con IA (RAG).
"""
from dataclasses import dataclass
from typing import List
from app.services.document.pdf_extractor import PageContent


@dataclass
class TextChunk:
    page_number: int
    chunk_index: int
    text: str
    word_count: int
    is_ocr: bool


def split_pages_into_chunks(
    pages: List[PageContent], max_words: int = 400
) -> List[TextChunk]:
    """
    Divide el texto de las páginas en chunks de máximo `max_words` palabras.
    Cada chunk mantiene referencia a la página de origen.

    Args:
        pages: Lista de PageContent extraídas del PDF.
        max_words: Máximo de palabras por chunk (default 400).

    Returns:
        Lista ordenada de TextChunk listos para guardar en BD.
    """
    chunks: List[TextChunk] = []
    global_index = 0

    for page in pages:
        words = page.text.split()
        if not words:
            continue  # página vacía, omitir

        for start in range(0, len(words), max_words):
            segment = words[start: start + max_words]
            chunks.append(TextChunk(
                page_number=page.page_number,
                chunk_index=global_index,
                text=" ".join(segment),
                word_count=len(segment),
                is_ocr=page.is_ocr,
            ))
            global_index += 1

    return chunks
