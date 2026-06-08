from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Azure Speech
    AZURE_SPEECH_KEY: str
    AZURE_SPEECH_REGION: str = "eastus"

    # OpenRouter (substitui OpenAI diretamente)
    OPENROUTER_API_KEY: str
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_MODEL: str = "google/gemma-3-27b-it:free"

    # Embedding — HuggingFace local, sem API key
    EMBEDDING_MODEL: str = "BAAI/bge-m3"

    # HuggingFace — opcionais
    HF_TOKEN: str = ""
    HF_HUB_DISABLE_SYMLINKS_WARNING: str = "1"

    # Vector Store
    CHROMA_PERSIST_DIR: str = "./knowledge_base/vector_store"

    # App
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore" 


settings = Settings()