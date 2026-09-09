import json
import subprocess
from pathlib import Path
from typing import Any, Dict

from .config import settings
from .llm_service import llm_service


class DebuggingAgent:
    """
    Autonomous Debugging Agent.

    Reads test failures, asks the configured LLM provider
    to identify and fix the problem, then safely writes the
    corrected source file inside the workspace.
    """

    def __init__(self, workspace_root: str | None = None):
        self.workspace_root = Path(
            workspace_root
            or getattr(
                settings,
                "GENERATED_WORKSPACE_DIR",
                "workspace",
            )
        ).resolve()

        self.workspace_root.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _safe_path(self, relative_path: str) -> Path:
        """
        Allow access only inside the generated workspace.
        """
        target = (
            self.workspace_root / relative_path
        ).resolve()

        try:
            target.relative_to(
                self.workspace_root
            )
        except ValueError:
            raise PermissionError(
                f"Access denied: {relative_path} "
                "is outside the workspace."
            )

        return target

    def run_tests(self) -> Dict[str, Any]:
        """
        Run pytest and collect the result.
        """
        try:
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "pytest",
                    "-q",
                ],
                cwd=str(
                    self.workspace_root
                ),
                capture_output=True,
                text=True,
                timeout=120,
            )

            return {
                "success": (
                    result.returncode == 0
                ),
                "return_code": (
                    result.returncode
                ),
                "output": result.stdout,
                "errors": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "return_code": -1,
                "output": "",
                "errors": (
                    "Testing timed out after "
                    "120 seconds."
                ),
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
        """
        Ask the configured LLM provider to fix a
        failing source file.
        """

        source_path = self._safe_path(
            file_path
        )

        if not source_path.exists():
            return {
                "success": False,
                "error": (
                    f"File does not exist: "
                    f"{file_path}"
                ),
            }

        if not source_path.is_file():
            return {
                "success": False,
                "error": (
                    f"Path is not a file: "
                    f"{file_path}"
                ),
            }

        source_code = source_path.read_text(
            encoding="utf-8"
        )

        system_prompt = (
            "You are an expert autonomous "
            "software debugging engineer. "
            "Analyze the failing Python program "
            "and fix the root cause. "
            "Return ONLY valid JSON with exactly "
            "these keys: "
            "'file_target', "
            "'content', "
            "and 'explanation'. "
            "'content' must contain the complete "
            "corrected source code. "
            "Do not include markdown outside the JSON."
        )

        user_prompt = f"""
A generated Python program failed its tests.

File:
{file_path}

Current code:
{source_code}

Test output:
{test_output}

Test errors:
{test_errors}

Find the root cause and provide the complete
corrected source code.

The file_target must be:
{file_path}
"""

        try:
            # IMPORTANT:
            # Use the active provider (OpenRouter/Gemini/etc.)
            # instead of forcing Gemini.
            result = llm_service._call_llm(
                system_prompt,
                user_prompt,
            )

            if not result["success"]:
                return {
                    "success": False,
                    "error": result.get(
                        "error",
                        "LLM debugging failed.",
                    ),
                }

            data = result.get(
                "plan"
            )

            if isinstance(data, str):
                data = json.loads(data)

            if not isinstance(data, dict):
                return {
                    "success": False,
                    "error": (
                        "LLM returned an invalid "
                        "debugging response."
                    ),
                }

            corrected_code = data.get(
                "content"
            )

            if corrected_code is None:
                return {
                    "success": False,
                    "error": (
                        "LLM did not return "
                        "corrected source code."
                    ),
                }

            corrected_code = str(
                corrected_code
            )

            # Only write inside the workspace.
            target = self._safe_path(
                file_path
            )

            target.write_text(
                corrected_code,
                encoding="utf-8",
            )

            return {
                "success": True,
                "file_target": file_path,
                "provider": llm_service.provider,
                "model": llm_service.model,
                "explanation": data.get(
                    "explanation",
                    "Source file corrected.",
                ),
            }

        except json.JSONDecodeError as exc:
            return {
                "success": False,
                "error": (
                    "LLM returned invalid JSON: "
                    f"{exc}"
                ),
            }

        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
            }

    def debug_until_pass(
        self,
        file_path: str,
        max_attempts: int = 3,
    ) -> Dict[str, Any]:
        """
        Run tests, ask the configured LLM to fix
        failures, and retry until the tests pass
        or the maximum number of attempts is reached.
        """

        history = []

        for attempt in range(
            1,
            max_attempts + 1,
        ):
            test_result = self.run_tests()

            history.append(
                {
                    "attempt": attempt,
                    "test_result": test_result,
                }
            )

            if test_result["success"]:
                return {
                    "success": True,
                    "attempts": attempt,
                    "history": history,
                }

            debug_result = self.debug_file(
                file_path=file_path,
                test_output=test_result[
                    "output"
                ],
                test_errors=test_result[
                    "errors"
                ],
            )

            history.append(
                {
                    "attempt": attempt,
                    "debug_result": debug_result,
                }
            )

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