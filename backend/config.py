from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Azure
    AZURE_SPEECH_KEY: str
    AZURE_SPEECH_REGION: str = "eastus"

    # LLM
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Vector Store
    CHROMA_PERSIST_DIR: str = "./knowledge_base/vector_store"

    # App
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()