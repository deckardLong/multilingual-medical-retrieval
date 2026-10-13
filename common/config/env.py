# Define class env

from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from .paths import ROOT

# Define Paths
_PATHS = ("r2ai_config_dir", "r2ai_corpus_dir", "r2ai_derived_dir", "r2ai_state_dir")

# Class env
class Env(BaseSettings):

    # ====== Model Configuration ====== 
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    # ====== HuggingFace & Qdrant ======
    hf_token: str | None = None
    hf_corpus_repo: str = ""
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None

    # ====== R2AI Dir ======
    r2ai_config_dir: Path = Path("configs")
    r2ai_experiment: str | None = None          
    r2ai_corpus_dir: Path = Path("corpus")
    r2ai_derived_dir: Path = Path("derived")
    r2ai_state_dir: Path = Path("state")

    # ====== LLM Model ======
    llm_api_key: str | None = None
    llm_model: str | None = None

    # Get abs dir
    @field_validator(*_PATHS)
    @classmethod
    def _abs(cls, p: Path) -> Path:
        return p if p.is_absolute() else ROOT / p