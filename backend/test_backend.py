import asyncio
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.agent_engine import agent_engine


def test_health_check():
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "online"

    print("[PASS] Health Check Passed:", data)


def test_workspace_endpoints():
    client = TestClient(app)

    response = client.get("/api/workspace/files?path=.")

    assert response.status_code == 200

    data = response.json()

    assert "files" in data

    print(
        "[PASS] Workspace Files Endpoint Passed:",
        f"Found {len(data['files'])} entries",
    )

    response = client.get(
        "/api/workspace/file?path=backend/config.py"
    )

    assert response.status_code == 200

    data = response.json()

    assert "content" in data

    print(
        "[PASS] Workspace Read File Endpoint Passed:",
        f"Read {len(data['content'])} bytes",
    )


async def test_agent_execution():
    task = agent_engine.create_task(
        goal="Create a simple Python calculator."
    )

    print(f"[PASS] Created test task: {task.task_id}")

    mock_plan = {
        "goal": "Create a simple Python calculator.",
        "architecture": [
            "Python calculator module",
            "Pytest tests",
        ],
        "execution_steps": [
            {
                "step": 1,
                "role": "Backend Developer",
                "action": "Create calculator module",
                "file_target": "demo_calculator.py",
            }
        ],
        "risk_analysis": [],
        "verification_plan": [
            "Run pytest"
        ],
    }

    mock_coding_result = {
        "success": True,
        "created_files": ["demo_calculator.py"],
        "step_results": [],
        "errors": [],
    }

    mock_testing_result = {
        "success": True,
        "workspace": "workspace",
        "source_files": ["demo_calculator.py"],
        "test_files": ["tests/test_demo_calculator.py"],
        "generation": {
            "success": True,
            "generated_tests": [],
        },
        "return_code": 0,
        "output": "8 passed in 0.01s",
        "errors": "",
    }

    with patch(
        "backend.agent_engine.llm_service.generate_plan",
        return_value={
            "success": True,
            "provider": "gemini",
            "model": "mock-model",
            "plan": mock_plan,
        },
    ), patch(
        "backend.agent_engine.coding_agent.implement_plan",
        return_value=mock_coding_result,
    ), patch(
        "backend.agent_engine.testing_agent.test_workspace",
        return_value=mock_testing_result,
    ):
        await agent_engine.execute_task(task.task_id)

    updated_task = agent_engine.get_task(task.task_id)

    assert updated_task is not None

    assert updated_task.status.value == "COMPLETED"

    assert len(updated_task.steps) == 3

    assert "demo_calculator.py" in updated_task.created_files

    print("[PASS] Agent Execution Workflow Passed!")

    for step in updated_task.steps:
        print(
            f"  - [{step.role.value}] "
            f"{step.action_description}"
        )


if __name__ == "__main__":
    print("--- Running Autonomous AI Backend Verification ---")

    test_health_check()
    test_workspace_endpoints()

    asyncio.run(test_agent_execution())

    print("--- All Backend Tests Succeeded! ---")