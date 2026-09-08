import json
import os
import urllib.request

import pytest

from backend.llm_service import llm_service


@pytest.mark.live
def test_gemini_live():
    """
    Live Gemini API verification.

    Run this test only when RUN_LIVE_GEMINI=1 is set.
    This prevents normal pytest runs from consuming API quota.
    """

    if os.getenv("RUN_LIVE_GEMINI") != "1":
        pytest.skip(
            "Live Gemini test skipped. "
            "Set RUN_LIVE_GEMINI=1 to run it."
        )

    print("--- Testing Live Gemini API Connection ---")

    assert llm_service.is_configured(), (
        "Gemini API key is not configured. "
        "Set GEMINI_API_KEY in the local .env file."
    )

    print(f"Detected Provider: {llm_service.provider}")
    print(f"Target Model:     {llm_service.model}")

    api_key = llm_service.api_key

    masked_key = (
        f"{api_key[:4]}...{api_key[-4:]}"
        if len(api_key) > 8
        else "***"
    )

    print(f"API Key Status:   Loaded securely ({masked_key})")

    # Model discovery test
    try:
        discovery_url = (
            "https://generativelanguage.googleapis.com/"
            f"v1beta/models?key={api_key}"
        )

        request = urllib.request.Request(discovery_url)

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )

        model_names = [
            model["name"]
            for model in data.get("models", [])
        ]

        print(
            "Available Gemini Models for this key:",
            model_names[:5],
        )

    except Exception as error:
        pytest.fail(
            f"Gemini model discovery failed: {error}"
        )

    prompt = (
        "Create a simple Python REST API "
        "for a task calculator."
    )

    print(
        f"\nSending requirement to Gemini:\n  '{prompt}'\n"
    )

    result = llm_service.generate_plan(prompt)

    assert result["success"], (
        "Gemini API connection failed: "
        f"{result.get('error', 'Unknown error')}"
    )

    print(
        "[SUCCESS] Gemini API Connection is WORKING! "
        "Live response received."
    )

    print("\n--- Generated Software Development Plan ---")

    plan = result["plan"]

    assert isinstance(plan, dict), (
        "Gemini returned an invalid plan format."
    )

    print(f"Goal: {plan.get('goal')}")

    architecture = plan.get(
        "architecture",
        [],
    )

    print(
        "Architecture:",
        ", ".join(architecture),
    )

    execution_steps = plan.get(
        "execution_steps",
        [],
    )

    print(
        f"Planned Steps ({len(execution_steps)} steps):"
    )

    for step in execution_steps:
        print(
            f"  - Step {step.get('step')}: "
            f"[{step.get('role')}] "
            f"{step.get('action')} -> "
            f"{step.get('file_target')}"
        )

    print("------------------------------------------")


if __name__ == "__main__":
    os.environ["RUN_LIVE_GEMINI"] = "1"
    test_gemini_live()