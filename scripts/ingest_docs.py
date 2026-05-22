import sys
import logging
from pathlib import Path

# Garante que o Python encontre os módulos do backend
sys.path.append(str(Path(__file__).parent.parent))

from backend.ingest.loader import load_documents
from backend.ingest.splitter import split_documents
from backend.ingest.embeddings import ingest_to_vectorstore
from backend.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

RAW_DIR = "knowledge_base/raw"


def main():
    logger.info("=" * 50)
    logger.info("Iniciando pipeline de ingestão")
    logger.info("=" * 50)

    # Etapa 1 — Carregamento
    logger.info(f"Lendo documentos de: {RAW_DIR}")
    docs = load_documents(RAW_DIR)
    if not docs:
        logger.error("Nenhum documento encontrado. Abortando.")
        sys.exit(1)

    # Etapa 2 — Chunking
    chunks = split_documents(docs)

    # Etapa 3 — Embeddings + persistência
    ingest_to_vectorstore(chunks)

    logger.info("=" * 50)
    logger.info("Pipeline concluído com sucesso.")
    logger.info(f"Vector store em: {settings.CHROMA_PERSIST_DIR}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()