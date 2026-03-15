"""
Servicio RAG (Retrieval Augmented Generation) usando Cohere Command R.

Flujo:
  1. Se reciben todos los chunks del documento desde la BD (texto plano).
  2. Cohere Rerank ordena los chunks por relevancia a la pregunta del usuario.
  3. Los top-N chunks se pasan como `documents` al modelo Command R.
  4. Cohere genera la respuesta con citaciones automáticas a los fragmentos.
"""
import logging
from dataclasses import dataclass
from typing import Optional
import cohere

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RagReference:
    chunk_index: int
    page_number: int
    text_snippet: str
    relevance_score: float


@dataclass
class RagResponse:
    answer: str
    references: list[RagReference]
    model_used: str


def _get_client() -> cohere.Client:
    """Devuelve cliente Cohere síncrono (Cohere SDK v5 usa cliente síncrono)."""
    if not settings.COHERE_API_KEY:
        raise RuntimeError(
            "COHERE_API_KEY no configurada. Agrégala en backend/.env"
        )
    return cohere.Client(api_key=settings.COHERE_API_KEY)


def answer_with_rag(
    question: str,
    chunks: list[dict],  # [{"chunk_index": int, "page_number": int, "text": str}]
    chat_history: Optional[list[dict]] = None,  # [{"role": "USER"|"CHATBOT", "message": str}]
) -> RagResponse:
    """
    Genera una respuesta usando RAG con Cohere Command R.

    Args:
        question: Pregunta del usuario.
        chunks: Lista de chunks del documento (chunk_index, page_number, text).
        chat_history: Historial de la conversación en formato Cohere.

    Returns:
        RagResponse con la respuesta y las referencias usadas.
    """
    if not chunks:
        return RagResponse(
            answer="No hay texto extraído del documento. Por favor extrae el texto primero (Etapa 2).",
            references=[],
            model_used=settings.COHERE_CHAT_MODEL,
        )

    co = _get_client()
    top_n = min(settings.COHERE_TOP_N, len(chunks))

    # ── Paso 1: Rerank — ordenar chunks por relevancia a la pregunta ──────────
    documents_for_rerank = [c["text"] for c in chunks]

    try:
        rerank_result = co.rerank(
            model="rerank-multilingual-v3.0",
            query=question,
            documents=documents_for_rerank,
            top_n=top_n,
            return_documents=True,
        )
        # Mapear resultados del rerank a nuestros chunks
        selected: list[dict] = []
        rerank_scores: list[float] = []
        for r in rerank_result.results:
            idx = r.index
            selected.append(chunks[idx])
            rerank_scores.append(r.relevance_score)

        logger.info(
            f"🔍 [RAG] Rerank completado: {len(selected)}/{len(chunks)} chunks seleccionados "
            f"(scores: {[f'{s:.2f}' for s in rerank_scores]})"
        )
    except Exception as exc:
        # Si rerank falla, usar los primeros top_n chunks como fallback
        logger.warning(f"⚠️ [RAG] Rerank falló, usando fallback: {exc}")
        selected = chunks[:top_n]
        rerank_scores = [0.0] * len(selected)

    # ── Paso 2: Construir documentos para Command R ───────────────────────────
    # Cohere espera lista de dicts con clave "text" (y opcionalmente otras claves como metadata)
    cohere_documents = [
        {
            "text": c["text"],
            "página": str(c.get("page_number", "?")),
            "chunk": str(c.get("chunk_index", i)),
        }
        for i, c in enumerate(selected)
    ]

    # ── Paso 3: Construir historial en formato Cohere ─────────────────────────
    cohere_history: list[dict] = []
    if chat_history:
        for msg in chat_history[-8:]:  # últimos 8 mensajes
            role = msg.get("role", "").lower()
            if role == "user":
                cohere_history.append({"role": "USER", "message": msg["content"]})
            elif role == "assistant":
                cohere_history.append({"role": "CHATBOT", "message": msg["content"]})

    # ── Paso 4: Llamada a Command R con grounding en documentos ──────────────
    preamble = (
        "Eres un asistente de auditoría médica colombiana experto en normativa CIE10, CUPS, "
        "Ley 1438/2011 y glosas hospitalarias. "
        "INSTRUCCIONES CRÍTICAS: "
        "1. Responde ÚNICAMENTE con base en los documentos proporcionados. "
        "2. Si la información no está en los documentos, responde: 'No encontré esa información en el documento.' "
        "3. Cita la página del fragmento cuando sea relevante. "
        "4. Sé técnico, preciso y conciso. "
        "5. Para análisis clínicos, finaliza con: "
        "'⚠️ Respuesta generada por IA como apoyo al auditor. No reemplaza la revisión clínica profesional.'"
    )

    try:
        response = co.chat(
            model=settings.COHERE_CHAT_MODEL,
            message=question,
            documents=cohere_documents,
            chat_history=cohere_history if cohere_history else None,
            preamble=preamble,
            temperature=0.3,
        )
        answer_text = response.text
        logger.info(f"✅ [RAG] Respuesta generada ({len(answer_text)} chars)")
    except Exception as exc:
        logger.error(f"❌ [RAG] Error en Command R: {type(exc).__name__}: {exc}")
        raise

    # ── Paso 5: Extraer referencias desde las citaciones de Cohere ───────────
    references: list[RagReference] = []
    if hasattr(response, "documents") and response.documents:
        # Cohere devuelve qué documentos usó para generar la respuesta
        used_doc_indices = set()
        if hasattr(response, "citations") and response.citations:
            for citation in response.citations:
                for doc_ref in (citation.document_ids or []):
                    # doc_ref es tipo "doc_0", "doc_1", etc.
                    try:
                        doc_idx = int(doc_ref.replace("doc_", ""))
                        used_doc_indices.add(doc_idx)
                    except ValueError:
                        pass
        # Si no hay citaciones explícitas, marcar todos los seleccionados
        if not used_doc_indices:
            used_doc_indices = set(range(len(selected)))

        for doc_idx in sorted(used_doc_indices):
            if doc_idx < len(selected):
                chunk = selected[doc_idx]
                score = rerank_scores[doc_idx] if doc_idx < len(rerank_scores) else 0.0
                references.append(RagReference(
                    chunk_index=chunk.get("chunk_index", doc_idx),
                    page_number=chunk.get("page_number", 0),
                    text_snippet=chunk["text"][:200] + ("..." if len(chunk["text"]) > 200 else ""),
                    relevance_score=round(score, 3),
                ))

    return RagResponse(
        answer=answer_text,
        references=references,
        model_used=settings.COHERE_CHAT_MODEL,
    )
