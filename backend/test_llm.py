import os

from backend.config import settings
from backend.llm_service import llm_service


def test_llm_service_unconfigured():
    """Verify graceful handling when no API key is available."""

    original_openrouter = os.environ.get("OPENROUTER_API_KEY")
    original_openai = os.environ.get("OPENAI_API_KEY")
    original_gemini = os.environ.get("GEMINI_API_KEY")
    original_llm = os.environ.get("LLM_API_KEY")
    original_settings_key = settings.LLM_API_KEY

    try:
        os.environ.pop("OPENROUTER_API_KEY", None)
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("LLM_API_KEY", None)

        settings.LLM_API_KEY = ""

        result = llm_service.generate_plan(
            "Build a user authentication REST API in Python"
        )

        assert result["success"] is False
        assert "API key" in result["error"]

    finally:
        if original_openrouter is not None:
            os.environ["OPENROUTER_API_KEY"] = original_openrouter

        if original_openai is not None:
            os.environ["OPENAI_API_KEY"] = original_openai

        if original_gemini is not None:
            os.environ["GEMINI_API_KEY"] = original_gemini

        if original_llm is not None:
            os.environ["LLM_API_KEY"] = original_llm

        settings.LLM_API_KEY = original_settings_key


def test_llm_service_mock_key():
    """Verify fallback key handling."""

    original_openrouter = os.environ.get("OPENROUTER_API_KEY")
    original_llm = os.environ.get("LLM_API_KEY")

    try:
        os.environ.pop("OPENROUTER_API_KEY", None)
        os.environ["LLM_API_KEY"] = "mock_test_key_12345"

        assert llm_service.is_configured() is True
        assert llm_service.api_key == "mock_test_key_12345"

    finally:
        if original_openrouter is not None:
            os.environ["OPENROUTER_API_KEY"] = original_openrouter
        else:
            os.environ.pop("OPENROUTER_API_KEY", None)

        if original_llm is not None:
            os.environ["LLM_API_KEY"] = original_llm
        else:
            os.environ.pop("LLM_API_KEY", None)


def test_llm_provider_configuration():
    """Verify the active provider and model."""

    assert llm_service.provider == "openrouter"
    assert llm_service.model == "openrouter/free"
    assert llm_service.api_key.startswith("sk-or-")

    print(
        f"[PASS] Provider: {llm_service.provider}, "
        f"Model: {llm_service.model}"
    )


if __name__ == "__main__":
    test_llm_service_unconfigured()
    test_llm_service_mock_key()
    test_llm_provider_configuration()
    print("[PASS] LLM tests completed successfully.")