import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


# Load variables from the project-root .env file.
load_dotenv()


class Settings(BaseModel):
    PROJECT_NAME: str = "Autonomous AI Software Engineer"
    VERSION: str = "0.1.0"

    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Workspace settings
    WORKSPACE_DIR: Path = Path(
        os.getenv(
            "WORKSPACE_DIR",
            Path(__file__).resolve().parent.parent,
        )
    )

    GENERATED_WORKSPACE_DIR: Path = Path(
        os.getenv(
            "GENERATED_WORKSPACE_DIR",
            Path(__file__).resolve().parent.parent / "workspace",
        )
    )

    MAX_ITERATIONS: int = 25
    COMMAND_TIMEOUT: int = 30

    # LLM settings
    LLM_PROVIDER: str = os.getenv(
        "LLM_PROVIDER",
        "openrouter",
    )

    LLM_API_KEY: str = (
        os.getenv("OPENROUTER_API_KEY")
        or os.getenv("LLM_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    )

    LLM_MODEL: str = os.getenv(
        "OPENROUTER_MODEL",
        os.getenv(
            "LLM_MODEL",
            "openrouter/free",
        ),
    )

    LLM_BASE_URL: str = os.getenv(
        "LLM_BASE_URL",
        "https://openrouter.ai/api/v1",
    )


settings = Settings()

# Ensure generated workspace directory exists.
settings.GENERATED_WORKSPACE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)