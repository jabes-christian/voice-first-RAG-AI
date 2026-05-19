# backend/ingest/splitter.py

import logging
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Parâmetros de chunking
#
# chunk_size=512:
#   Tamanho ideal para o bge-m3 (context window de 8192 tokens)
#   e para o prompt do LLM — 4 chunks × 512 ≈ 2048 tokens de contexto
#
# chunk_overlap=50:
#   Evita que uma informação seja cortada no meio
#   entre dois chunks adjacentes
#
# separators:
#   Ordem de preferência para cortar o texto:
#   1. Dupla quebra de linha (fim de parágrafo) — melhor semântica
#   2. Quebra de linha simples
#   3. Ponto final — frase completa
#   4. Espaço — último recurso
# ──────────────────────────────────────────────
_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=50,
    separators=["\n\n", "\n", ". ", " "],
    length_function=len,
)


def split_documents(docs: list[Document]) -> list[Document]:
    if not docs:
        logger.warning("[Splitter] Nenhum documento para dividir.")
        return []

    chunks = _SPLITTER.split_documents(docs)

    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = i

    logger.info(
        f"[Splitter] {len(docs)} doc(s) → {len(chunks)} chunk(s) "
        f"(média: {len(chunks) // max(len(docs), 1)} chunks/doc)"
    )
    return chunks