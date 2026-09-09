import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from .config import settings
from .llm_service import llm_service


class TestingAgent:
    """
    Autonomous Testing Agent.

    Discovers Python source files inside the generated workspace,
    asks the configured LLM provider to generate pytest tests,
    writes those tests into the workspace, and executes pytest.
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

    def discover_python_files(self) -> List[str]:
        """
        Find Python source files inside the workspace.

        Test files and __pycache__ files are excluded.
        """
        files: List[str] = []

        for path in self.workspace_root.rglob(
            "*.py"
        ):
            if "__pycache__" in path.parts:
                continue

            relative = path.relative_to(
                self.workspace_root
            )

            if "tests" in relative.parts:
                continue

            files.append(str(relative))

        return sorted(files)

    def generate_test_for_file(
        self,
        source_file: str,
    ) -> Dict[str, Any]:
        """
        Ask the configured LLM provider to generate
        a pytest test file for one source file.
        """

        source_path = self._safe_path(
            source_file
        )

        if not source_path.exists():
            return {
                "success": False,
                "error": (
                    f"Source file does not exist: "
                    f"{source_file}"
                ),
            }

        if not source_path.is_file():
            return {
                "success": False,
                "error": (
                    f"Source path is not a file: "
                    f"{source_file}"
                ),
            }

        source_code = source_path.read_text(
            encoding="utf-8"
        )

        system_prompt = (
            "You are an expert Python QA engineer. "
            "Generate reliable pytest tests for the "
            "provided Python source file. "
            "Return ONLY valid JSON with exactly these "
            "keys: "
            "'test_file' (string), "
            "'content' (complete pytest source code), "
            "and 'explanation' (short string). "
            "Do not include markdown outside the JSON."
        )

        user_prompt = f"""
Generate a pytest test file for the following Python source file.

Source file:
{source_file}

Source code:
{source_code}

Requirements:
- Use pytest.
- Test normal behavior.
- Test important edge cases where appropriate.
- Do not modify the source file.
- Return ONLY valid JSON.
- The "test_file" should be under tests/
- The filename should start with test_.
"""

        try:
            # IMPORTANT:
            # Use the configured provider instead of
            # forcing Gemini.
            result = llm_service._call_llm(
                system_prompt,
                user_prompt,
            )

            if not result["success"]:
                return {
                    "success": False,
                    "error": result.get(
                        "error",
                        "LLM test generation failed.",
                    ),
                    "source_file": source_file,
                }

            data = result.get("plan")

            if isinstance(data, str):
                data = json.loads(data)

            if not isinstance(data, dict):
                return {
                    "success": False,
                    "error": (
                        "LLM returned an invalid "
                        "test-generation response."
                    ),
                    "source_file": source_file,
                }

            test_file = str(
                data.get("test_file", "")
            ).strip()

            content = data.get("content")

            if not test_file:
                return {
                    "success": False,
                    "error": (
                        "LLM did not provide a "
                        "test_file."
                    ),
                    "source_file": source_file,
                }

            if content is None:
                return {
                    "success": False,
                    "error": (
                        "LLM did not provide test "
                        "content."
                    ),
                    "source_file": source_file,
                }

            content = str(content)

            # Normalize Windows-style paths.
            test_file = test_file.replace(
                "\\",
                "/",
            )

            # Force generated tests under tests/.
            if not test_file.startswith(
                "tests/"
            ):
                test_file = (
                    f"tests/{Path(test_file).name}"
                )

            # Ensure the filename starts with test_.
            filename = Path(test_file).name

            if not filename.startswith(
                "test_"
            ):
                filename = (
                    f"test_{filename}"
                )

            test_file = (
                f"tests/{filename}"
            )

            target = self._safe_path(
                test_file
            )

            target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            target.write_text(
                content,
                encoding="utf-8",
            )

            return {
                "success": True,
                "source_file": source_file,
                "test_file": test_file,
                "provider": llm_service.provider,
                "model": llm_service.model,
                "explanation": data.get(
                    "explanation",
                    "",
                ),
            }

        except json.JSONDecodeError as exc:
            return {
                "success": False,
                "source_file": source_file,
                "error": (
                    "LLM returned invalid JSON: "
                    f"{exc}"
                ),
            }

        except Exception as exc:
            return {
                "success": False,
                "source_file": source_file,
                "error": str(exc),
            }

    def generate_tests(self) -> Dict[str, Any]:
        """
        Generate tests for all discovered Python
        source files.
        """
        source_files = (
            self.discover_python_files()
        )

        results: List[Dict[str, Any]] = []

        for source_file in source_files:
            results.append(
                self.generate_test_for_file(
                    source_file
                )
            )

        success = (
            all(
                item.get("success", False)
                for item in results
            )
            if results
            else False
        )

        return {
            "success": success,
            "source_files": source_files,
            "generated_tests": results,
        }

    def run_tests(self) -> Dict[str, Any]:
        """
        Run pytest inside the isolated workspace.
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
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "return_code": -1,
                "stdout": "",
                "stderr": (
                    "Testing timed out after "
                    "120 seconds."
                ),
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
        Generate tests automatically and then
        execute them.
        """

        generation = self.generate_tests()

        test_result = self.run_tests()

        test_files = []

        for path in self.workspace_root.rglob(
            "test_*.py"
        ):
            if "__pycache__" in path.parts:
                continue

            test_files.append(
                str(
                    path.relative_to(
                        self.workspace_root
                    )
                )
            )

        return {
            "success": (
                generation["success"]
                and test_result["success"]
            ),
            "workspace": str(
                self.workspace_root
            ),
            "source_files": (
                generation["source_files"]
            ),
            "test_files": sorted(
                test_files
            ),
            "generation": generation,
            "return_code": (
                test_result["return_code"]
            ),
            "output": test_result["stdout"],
            "errors": test_result["stderr"],
        }


testing_agent = TestingAgent()