import logging
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from backend.config import settings

logger = logging.getLogger(__name__)


def get_retriever():

    logger.info("[Retriever] Carregando embeddings BAAI/bge-m3...")

    embeddings = HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    vector_store = Chroma(
        persist_directory=settings.CHROMA_PERSIST_DIR,
        embedding_function=embeddings,
    )

    retriever = vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 4,        
            "fetch_k": 20, 
        },
    )

    logger.info("[Retriever] Retriever MMR pronto.")
    return retriever