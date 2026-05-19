import logging
from pathlib import Path
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, TextLoader

logger = logging.getLogger(__name__)

SUPPORTED = {".pdf", ".md", ".txt"}


def load_documents(raw_dir: str) -> list[Document]:
    raw_path = Path(raw_dir)
    if not raw_path.exists():
        raise FileNotFoundError(f"Diretório não encontrado: {raw_dir}")

    all_docs: list[Document] = []
    files = [f for f in raw_path.rglob("*") if f.suffix in SUPPORTED]

    if not files:
        logger.warning(f"[Loader] Nenhum arquivo suportado em: {raw_dir}")
        return []

    for file_path in files:
        try:
            docs = _load_file(file_path)
            all_docs.extend(docs)
            logger.info(
                f"[Loader] {file_path.name} → {len(docs)} página(s)/seção(ões)"
            )
        except Exception as e:
            logger.error(f"[Loader] Falha ao carregar {file_path.name}: {e}")
            continue

    logger.info(f"[Loader] Total carregado: {len(all_docs)} documentos")
    return all_docs


def _load_file(file_path: Path) -> list[Document]:
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        loader = PyPDFLoader(str(file_path))
        return loader.load()

    if suffix in {".md", ".txt"}:
        loader = TextLoader(str(file_path), encoding="utf-8")
        return loader.load()

    raise ValueError(f"Extensão não suportada: {suffix}")