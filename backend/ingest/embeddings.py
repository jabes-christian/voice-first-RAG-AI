import logging
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from backend.config import settings

logger = logging.getLogger(__name__)


def get_embeddings() -> HuggingFaceEmbeddings:
    
    logger.info(
        f"[Embeddings] Carregando modelo: {settings.EMBEDDING_MODEL}"
    )
    return HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def ingest_to_vectorstore(chunks: list[Document]) -> Chroma:
    
    if not chunks:
        raise ValueError("[Embeddings] Nenhum chunk para indexar.")

    embeddings = get_embeddings()

    logger.info(
        f"[Embeddings] Indexando {len(chunks)} chunks no ChromaDB..."
    )

    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=settings.CHROMA_PERSIST_DIR,
    )

    logger.info(
        f"[Embeddings] Concluído. Vector store em: "
        f"{settings.CHROMA_PERSIST_DIR}"
    )
    return vector_store


def update_vectorstore(chunks: list[Document]) -> None:
    
    if not chunks:
        logger.warning("[Embeddings] Nenhum chunk novo para adicionar.")
        return

    embeddings = get_embeddings()

    vector_store = Chroma(
        persist_directory=settings.CHROMA_PERSIST_DIR,
        embedding_function=embeddings,
    )

    vector_store.add_documents(chunks)
    logger.info(
        f"[Embeddings] {len(chunks)} novos chunks adicionados ao store."
    )