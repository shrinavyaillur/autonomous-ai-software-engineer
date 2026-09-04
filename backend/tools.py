import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from .config import settings

class WorkspaceTools:
    def __init__(self, workspace_root: Optional[Path] = None):
        if workspace_root is None:
            self.workspace_root = settings.WORKSPACE_DIR.resolve()
        else:
            self.workspace_root = workspace_root.resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, relative_path: str) -> Path:
        # Sanitize path to prevent directory traversal
        clean_path = relative_path.strip().lstrip("/\\")
        target = (self.workspace_root / clean_path).resolve()
        try:
            target.relative_to(self.workspace_root)
        except ValueError:
            raise PermissionError(f"Access denied: Path '{relative_path}' is outside workspace root '{self.workspace_root}'.")
        return target

    def list_files(self, relative_path: str = ".") -> List[Dict[str, Any]]:
        target_dir = self._resolve_path(relative_path)
        if not target_dir.exists() or not target_dir.is_dir():
            return []
        
        results = []
        for entry in os.scandir(target_dir):
            if entry.name.startswith(".") or entry.name == "__pycache__":
                continue
            rel = str(Path(entry.path).relative_to(self.workspace_root)).replace(chr(92), "/")
            results.append({
                "name": entry.name,
                "is_dir": entry.is_dir(),
                "path": rel
            })
        return results

    def file_exists(self, relative_path: str) -> bool:
        try:
            return self._resolve_path(relative_path).is_file()
        except Exception:
            return False

    def read_file(self, relative_path: str) -> str:
        file_path = self._resolve_path(relative_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File '{relative_path}' does not exist.")
        return file_path.read_text(encoding="utf-8", errors="replace")

    def write_file(self, relative_path: str, content: str) -> str:
        file_path = self._resolve_path(relative_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to '{relative_path}'."

    def execute_terminal(self, command: str) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                timeout=settings.COMMAND_TIMEOUT
            )
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Command timed out after {settings.COMMAND_TIMEOUT} seconds.",
                "success": False
            }
        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False
            }
