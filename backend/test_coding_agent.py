import os
import shutil
from pathlib import Path
from backend.config import settings
from backend.tools import WorkspaceTools
from backend.coding_agent import CodingAgent, coding_agent
from backend.llm_service import llm_service

def test_workspace_isolation():
    print("1. Testing Workspace Sandbox Isolation...")
    test_dir = settings.WORKSPACE_DIR / "test_sandbox_workspace"
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)

    tools = WorkspaceTools(workspace_root=test_dir)
    # Write a valid file
    tools.write_file("nested/module/sample.py", "print('hello inside workspace')")
    assert tools.file_exists("nested/module/sample.py")
    assert "hello inside workspace" in tools.read_file("nested/module/sample.py")
    print("   [PASS] Valid file created inside sandbox workspace.")

    # Try directory traversal attack
    try:
        tools.write_file("../forbidden.py", "malicious content")
        assert False, "Should have raised PermissionError for path traversal"
    except PermissionError as pe:
        print(f"   [PASS] Successfully blocked directory traversal attack: {pe}")

    # Clean up test sandbox
    shutil.rmtree(test_dir)

def test_coding_agent_step_and_plan_mock():
    print("\n2. Testing Coding Agent Step and Plan Implementation (Mock/Local)...")
    test_ws = settings.WORKSPACE_DIR / "test_agent_workspace"
    if test_ws.exists():
        shutil.rmtree(test_ws)
    test_ws.mkdir(parents=True, exist_ok=True)

    agent = CodingAgent(workspace_dir=test_ws)
    
    # Mock LLM code generation
    original_generate_code = agent.llm.generate_code
    def mock_generate_code(goal, step_action, file_target, context=None):
        return {
            "success": True,
            "provider": "mock",
            "model": "mock-test",
            "file_target": file_target,
            "content": f"# Code generated for {file_target}\ndef main():\n    return '{step_action}'\n",
            "explanation": f"Implemented {file_target}"
        }
    agent.llm.generate_code = mock_generate_code

    try:
        # Test step implementation
        step = {
            "step": 1,
            "role": "Backend Architect",
            "action": "Create configuration file",
            "file_target": "config/settings.py"
        }
        res = agent.implement_step("Build test project", step)
        assert res["success"] is True
        assert res["file_target"] == "config/settings.py"
        assert res["bytes_written"] > 0
        assert agent.tools.file_exists("config/settings.py")
        content = agent.tools.read_file("config/settings.py")
        assert "Create configuration file" in content
        print("   [PASS] CodingAgent.implement_step created and verified file in workspace.")

        # Test plan implementation
        plan = {
            "goal": "Build calculator microservice",
            "execution_steps": [
                {"step": 1, "role": "Backend Developer", "action": "Define data schemas", "file_target": "app/schemas.py"},
                {"step": 2, "role": "Backend Developer", "action": "Implement calculation logic", "file_target": "app/calculator.py"},
                {"step": 3, "role": "QA Engineer", "action": "Write unit tests", "file_target": "tests/test_calculator.py"}
            ]
        }
        plan_res = agent.implement_plan("Build calculator microservice", plan)
        assert plan_res["success"] is True
        assert len(plan_res["created_files"]) == 3
        assert agent.tools.file_exists("app/schemas.py")
        assert agent.tools.file_exists("app/calculator.py")
        assert agent.tools.file_exists("tests/test_calculator.py")
        print(f"   [PASS] CodingAgent.implement_plan successfully created all {len(plan_res['created_files'])} planned files.")

    finally:
        agent.llm.generate_code = original_generate_code
        if test_ws.exists():
            shutil.rmtree(test_ws)

def test_coding_agent_error_handling():
    print("\n3. Testing Coding Agent Error Handling...")
    agent = CodingAgent()

    # Test invalid/empty file target
    res_empty = agent.implement_step("Some goal", {"step": 1, "action": "Do something", "file_target": ""})
    assert res_empty["success"] is False
    assert "No valid 'file_target'" in res_empty["error"]
    print(f"   [PASS] Gracefully rejected empty file target: {res_empty['error']}")

    # Test LLM generation error propagation
    original_generate = agent.llm.generate_code
    agent.llm.generate_code = lambda **kwargs: {"success": False, "error": "Simulated quota exceeded", "file_target": "fail.py", "content": None}
    try:
        res_fail = agent.implement_step("Goal", {"step": 1, "file_target": "fail.py", "action": "Create"})
        assert res_fail["success"] is False
        assert "Simulated quota exceeded" in res_fail["error"]
        print(f"   [PASS] Gracefully handled code generation failure: {res_fail['error']}")
    finally:
        agent.llm.generate_code = original_generate

def test_coding_agent_live_gemini():
    print("\n4. Testing Live Coding Agent Code Generation with Gemini 3.6 Flash...")
    if not llm_service.is_configured():
        print("   [SKIP] Gemini API Key not configured. Skipping live test.")
        return

    print(f"   Target Model: {llm_service.model}")
    print(f"   Dedicated Workspace: {settings.GENERATED_WORKSPACE_DIR}")

    step = {
        "step": 1,
        "role": "Backend Engineer",
        "action": "Implement a simple math calculator module with add and subtract functions",
        "file_target": "demo_calculator.py"
    }

    result = coding_agent.implement_step(
        goal="Create a simple Python task calculator",
        step=step
    )

    if result["success"]:
        print("   [SUCCESS] Live code generation succeeded!")
        print(f"   File Created:    {result['file_target']}")
        print(f"   Bytes Written:   {result['bytes_written']}")
        print(f"   Explanation:     {result['explanation']}")

        # Read back written file
        file_content = coding_agent.tools.read_file("demo_calculator.py")
        print("   --- Generated Code Preview ---")
        preview_lines = file_content.strip().splitlines()[:10]
        for line in preview_lines:
            print(f"     {line}")
        print("   -----------------------------")
        assert len(file_content) > 20
        print("   [PASS] Live generated file verified inside dedicated workspace.")
    else:
        print(f"   [FAIL] Live code generation failed: {result.get('error')}")
        raise AssertionError(f"Live Gemini code generation failed: {result.get('error')}")

if __name__ == "__main__":
    print("--- Running Coding Agent Test Suite ---")
    test_workspace_isolation()
    test_coding_agent_step_and_plan_mock()
    test_coding_agent_error_handling()
    test_coding_agent_live_gemini()
    print("\n--- All Coding Agent Tests Succeeded! ---")
