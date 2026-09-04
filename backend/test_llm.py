import os
import sys
from fastapi.testclient import TestClient
from backend.main import app
from backend.llm_service import llm_service
from backend.config import settings

def test_llm_status_endpoint():
    client = TestClient(app)
    response = client.get("/api/llm/status")
    assert response.status_code == 200
    data = response.json()
    print("[PASS] LLM Status Endpoint Response:")
    print("       Configured:", data["configured"])
    print("       Provider:", data["provider"])
    print("       Model:", data["model"])
    print("       Message:", data["message"])

def test_llm_service_unconfigured():
    # Store original env vars and settings key
    orig_key = os.environ.get("OPENAI_API_KEY")
    orig_gemini = os.environ.get("GEMINI_API_KEY")
    orig_llm = os.environ.get("LLM_API_KEY")
    orig_settings_key = settings.LLM_API_KEY

    try:
        # Temporarily clear keys to test graceful error handling
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("LLM_API_KEY", None)
        settings.LLM_API_KEY = ""

        res = llm_service.generate_plan("Build a user authentication REST API in Python")
        assert res["success"] is False
        assert "API Key is missing" in res["error"]
        print("[PASS] Handled missing API key gracefully without crashing:")
        print("       Error message:", res["error"])
    finally:
        # Restore environment
        if orig_key: os.environ["OPENAI_API_KEY"] = orig_key
        if orig_gemini: os.environ["GEMINI_API_KEY"] = orig_gemini
        if orig_llm: os.environ["LLM_API_KEY"] = orig_llm
        settings.LLM_API_KEY = orig_settings_key

def test_llm_service_mock_key():
    # Test environment variable reading logic with a mock key
    os.environ["LLM_API_KEY"] = "mock_test_key_12345"
    assert llm_service.is_configured() is True
    assert llm_service.api_key == "mock_test_key_12345"
    print("[PASS] Environment variable API key reading verified successfully (Key masked):", f"{llm_service.api_key[:4]}...{llm_service.api_key[-4:]}")
    os.environ.pop("LLM_API_KEY", None)

if __name__ == "__main__":
    print("--- Running LLM Service Connection Tests ---")
    test_llm_status_endpoint()
    test_llm_service_unconfigured()
    test_llm_service_mock_key()
    print("--- All LLM Service Tests Succeeded! ---")
