import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List

from .config import settings
from .llm_service import llm_service


class TestingAgent:
    """
    Autonomous Testing Agent.

    Finds Python source files inside the generated workspace,
    asks Gemini to generate pytest tests, writes those tests
    into the workspace, and runs pytest.
    """

    def __init__(self, workspace_root: str | None = None):
        self.workspace_root = Path(
            workspace_root
            or getattr(settings, "GENERATED_WORKSPACE_DIR", "workspace")
        ).resolve()

        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, relative_path: str) -> Path:
        """Allow access only inside the generated workspace."""
        target = (self.workspace_root / relative_path).resolve()

        try:
            target.relative_to(self.workspace_root)
        except ValueError:
            raise PermissionError(
                f"Access denied: {relative_path} is outside the workspace."
            )

        return target

    def discover_python_files(self) -> List[str]:
        """Find Python source files inside the workspace."""
        files = []

        for path in self.workspace_root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue

            relative = path.relative_to(self.workspace_root)

            if "tests" not in relative.parts:
                files.append(str(relative))

        return sorted(files)

    def generate_test_for_file(self, source_file: str) -> Dict[str, Any]:
        """
        Ask Gemini to generate pytest tests for one source file.
        """
        source_path = self._safe_path(source_file)

        if not source_path.exists():
            return {
                "success": False,
                "error": f"Source file does not exist: {source_file}",
            }

        source_code = source_path.read_text(encoding="utf-8")

        prompt = f"""
Generate a pytest test file for the following Python source file.

Source file: {source_file}

Source code:
{source_code}

Requirements:
- Use pytest.
- Test normal behavior.
- Test edge cases where appropriate.
- Do not modify the source file.
- Return ONLY valid JSON.
- JSON must contain:
  "test_file": string
  "content": string
  "explanation": string

The test_file should be placed under tests/ and should start with test_.
"""

        try:
            result = llm_service._call_gemini(
                "You are an expert Python QA engineer. Generate reliable pytest tests.",
                prompt,
            )

            if not result["success"]:
                return {
                    "success": False,
                    "error": result.get("error", "Gemini test generation failed"),
                }

            data = result["plan"]

            if isinstance(data, str):
                data = json.loads(data)

            test_file = data["test_file"]
            content = data["content"]

            if not test_file.startswith("tests/"):
                test_file = f"tests/{Path(test_file).name}"

            target = self._safe_path(test_file)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

            return {
                "success": True,
                "source_file": source_file,
                "test_file": test_file,
                "explanation": data.get("explanation", ""),
            }

        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
            }

    def generate_tests(self) -> Dict[str, Any]:
        """Generate tests for all discovered Python source files."""
        source_files = self.discover_python_files()
        results = []

        for source_file in source_files:
            results.append(self.generate_test_for_file(source_file))

        return {
            "success": all(item["success"] for item in results) if results else False,
            "source_files": source_files,
            "generated_tests": results,
        }

    def run_tests(self) -> Dict[str, Any]:
        """Run pytest inside the isolated workspace."""
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "-q"],
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                timeout=120,
            )

            return {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "return_code": -1,
                "stdout": "",
                "stderr": "Testing timed out after 120 seconds.",
            }

        except Exception as exc:
            return {
                "success": False,
                "return_code": -1,
                "stdout": "",
                "stderr": str(exc),
            }

    def test_workspace(self) -> Dict[str, Any]:
        """
        Generate tests automatically and then execute them.
        """
        generation = self.generate_tests()
        test_result = self.run_tests()

        test_files = [
            str(path.relative_to(self.workspace_root))
            for path in self.workspace_root.rglob("test_*.py")
        ]

        return {
            "success": generation["success"] and test_result["success"],
            "workspace": str(self.workspace_root),
            "source_files": generation["source_files"],
            "test_files": sorted(test_files),
            "generation": generation,
            "return_code": test_result["return_code"],
            "output": test_result["stdout"],
            "errors": test_result["stderr"],
        }


testing_agent = TestingAgent()