import os
from pathlib import Path
from dotenv import load_dotenv

# Centralized UTF-8 initialization for Windows compatibility (CO₂, subscripts, Greek letters, etc.)
from backend.app.core.encoding import setup_utf8_environment
setup_utf8_environment()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables
load_dotenv(dotenv_path=BASE_DIR / ".env")

class Settings:
    PROJECT_NAME: str = "ChemSafe AI - Chemical Safety & SDS Assistant"
    API_V1_STR: str = "/api/v1"
    
    # Storage settings
    DATA_DIR: Path = BASE_DIR / "data"
    RAW_DIR: Path = DATA_DIR / "raw"
    PROCESSED_DIR: Path = DATA_DIR / "processed"
    
    # Database setting
    @property
    def DATABASE_URL(self) -> str:
        return f"sqlite:///{self.PROCESSED_DIR}/sds_store.db"
    
    # Vector store settings
    @property
    def FAISS_INDEX_PATH(self) -> Path:
        return self.PROCESSED_DIR / "faiss_index.bin"
        
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    
    # LLM Settings (for future phase, but we declare the env variables/defaults here)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")  # openai, anthropic, mock, etc.
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # Ollama & RAG Settings
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen3:4b")
    TOP_K: int = int(os.getenv("TOP_K", "5"))

    def __init__(self) -> None:
        self.create_directories()

    def create_directories(self) -> None:
        """Create storage directories if they do not exist."""
        self.RAW_DIR.mkdir(parents=True, exist_ok=True)
        self.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()
