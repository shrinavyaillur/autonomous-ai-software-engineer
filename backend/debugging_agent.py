import subprocess
from pathlib import Path
from typing import Dict, Any

from .config import settings
from .llm_service import llm_service


class DebuggingAgent:
    """
    Autonomous Debugging Agent.

    Reads test failures, asks Gemini to identify and fix the problem,
    then safely writes the corrected file inside the workspace.
    """

    def __init__(self, workspace_root: str | None = None):
        self.workspace_root = Path(
            workspace_root
            or getattr(settings, "GENERATED_WORKSPACE_DIR", "workspace")
        ).resolve()

        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, relative_path: str) -> Path:
        target = (self.workspace_root / relative_path).resolve()

        try:
            target.relative_to(self.workspace_root)
        except ValueError:
            raise PermissionError(
                f"Access denied: {relative_path} is outside the workspace."
            )

        return target

    def run_tests(self) -> Dict[str, Any]:
        """Run pytest and collect the result."""
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
                "output": result.stdout,
                "errors": result.stderr,
            }

        except Exception as exc:
            return {
                "success": False,
                "return_code": -1,
                "output": "",
                "errors": str(exc),
            }

    def debug_file(
        self,
        file_path: str,
        test_output: str,
        test_errors: str = "",
    ) -> Dict[str, Any]:
        """Ask Gemini to fix a failing source file."""
        source_path = self._safe_path(file_path)

        if not source_path.exists():
            return {
                "success": False,
                "error": f"File does not exist: {file_path}",
            }

        source_code = source_path.read_text(encoding="utf-8")

        prompt = f"""
You are an expert Python debugging engineer.

A generated Python program failed its tests.

File:
{file_path}

Current code:
{source_code}

Test output:
{test_output}

Test errors:
{test_errors}

Find the root cause and return ONLY valid JSON with:
{{
  "file_target": "{file_path}",
  "content": "complete corrected source code",
  "explanation": "short explanation of the bug and fix"
}}

Do not include markdown outside the JSON.
"""

        try:
            result = llm_service._call_gemini(
                "You are an expert autonomous software debugging agent.",
                prompt,
            )

            if not result["success"]:
                return {
                    "success": False,
                    "error": result.get("error", "Gemini debugging failed"),
                }

            data = result["plan"]

            if isinstance(data, str):
                import json
                data = json.loads(data)

            corrected_code = data["content"]

            # Only write inside the workspace.
            target = self._safe_path(file_path)
            target.write_text(corrected_code, encoding="utf-8")

            return {
                "success": True,
                "file_target": file_path,
                "explanation": data.get("explanation", ""),
            }

        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
            }

    def debug_until_pass(self, file_path: str, max_attempts: int = 3) -> Dict[str, Any]:
        """
        Run tests, ask Gemini to fix failures, and retry.
        """
        history = []

        for attempt in range(1, max_attempts + 1):
            test_result = self.run_tests()

            history.append({
                "attempt": attempt,
                "test_result": test_result,
            })

            if test_result["success"]:
                return {
                    "success": True,
                    "attempts": attempt,
                    "history": history,
                }

            debug_result = self.debug_file(
                file_path=file_path,
                test_output=test_result["output"],
                test_errors=test_result["errors"],
            )

            history.append({
                "attempt": attempt,
                "debug_result": debug_result,
            })

            if not debug_result["success"]:
                return {
                    "success": False,
                    "attempts": attempt,
                    "history": history,
                }

        final_result = self.run_tests()

        return {
            "success": final_result["success"],
            "attempts": max_attempts,
            "final_test": final_result,
            "history": history,
        }


debugging_agent = DebuggingAgent()