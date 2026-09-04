import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class Settings(BaseModel):
    PROJECT_NAME: str = "Autonomous AI Software Engineer"
    VERSION: str = "0.1.0"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # Workspace settings
    WORKSPACE_DIR: Path = Path(os.getenv("WORKSPACE_DIR", Path(__file__).resolve().parent.parent))
    GENERATED_WORKSPACE_DIR: Path = Path(os.getenv("GENERATED_WORKSPACE_DIR", Path(__file__).resolve().parent.parent / "workspace"))
    MAX_ITERATIONS: int = 25
    COMMAND_TIMEOUT: int = 30 # seconds

    # LLM Settings (reads from environment variables)
    LLM_API_KEY: str = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-3.6-flash")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")  # "openai", "gemini"
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")

settings = Settings()
# Ensure generated workspace directory exists
settings.GENERATED_WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
