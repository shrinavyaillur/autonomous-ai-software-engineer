import json
from backend.llm_service import llm_service

def test_gemini_live():
    print("--- Testing Live Gemini API Connection ---")
    if not llm_service.is_configured():
        print("[FAIL] Gemini API Key is not configured in .env or environment variables.")
        print("       Please add 'GEMINI_API_KEY=AIzaSy...' to your .env file in the project root.")
        return False

    print(f"Detected Provider: {llm_service.provider}")
    print(f"Target Model:     {llm_service.model}")
    masked_key = f"{llm_service.api_key[:4]}...{llm_service.api_key[-4:]}" if len(llm_service.api_key) > 8 else "***"
    print(f"API Key Status:   Loaded securely ({masked_key})")
    
    # Discovery test
    try:
        import urllib.request
        disc_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={llm_service.api_key}"
        req = urllib.request.Request(disc_url)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            model_names = [m["name"] for m in data.get("models", [])]
            print(f"Available Gemini Models for this key: {model_names[:5]}")
    except Exception as err:
        print(f"Model discovery error: {err}")

    prompt = "Create a simple Python REST API for a task calculator."
    print(f"\nSending requirement to Gemini:\n  '{prompt}'\n")
    
    result = llm_service.generate_plan(prompt)
    if result["success"]:
        print("[SUCCESS] Gemini API Connection is WORKING! Live response received.")
        print("\n--- Generated Software Development Plan ---")
        plan = result["plan"]
        print(f"Goal:         {plan.get('goal')}")
        print(f"Architecture: {', '.join(plan.get('architecture', []))}")
        print(f"Planned Steps ({len(plan.get('execution_steps', []))} steps):")
        for step in plan.get("execution_steps", []):
            print(f"  - Step {step.get('step')}: [{step.get('role')}] {step.get('action')} -> {step.get('file_target')}")
        print("------------------------------------------")
        return True
    else:
        print("[FAIL] Connection Error:")
        print(f"       {result.get('error')}")
        return False

if __name__ == "__main__":
    test_gemini_live()
