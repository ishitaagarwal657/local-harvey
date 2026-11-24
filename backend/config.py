"""
Application configuration.
All secrets stay outside source code.
"""
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional, Literal

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SAMPLE_DIR = BASE_DIR / "sample_data"
DB_PATH = DATA_DIR / "localharvey.db"


class Settings(BaseSettings):
    app_name: str = "LocalHarvey"
    app_version: str = "1.1.0"
    debug: bool = True

    # Ollama — MUST be local
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_timeout: int = 180

    # Model selection
    # PROFILE=standard → ordinary laptop (7B or smaller)
    # PROFILE=high     → high-RAM / GPU machines (14B+)
    # PROFILE=auto     → detect at runtime from hardware
    profile: Literal["auto", "standard", "high", "minimal"] = "auto"

    # Explicit overrides (leave empty to use profile / hardware recommendation)
    default_model: str = ""
    fallback_model: str = ""

    # Embeddings — Apache-2.0 (sentence-transformers / all-MiniLM-L6-v2)
    embedding_model: str = "all-MiniLM-L6-v2"

    # Safety
    allow_external_llm: bool = False  # Hard lock — never change to True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
DATA_DIR.mkdir(exist_ok=True)
SAMPLE_DIR.mkdir(exist_ok=True)
