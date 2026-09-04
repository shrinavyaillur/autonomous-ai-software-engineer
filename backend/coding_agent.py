import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from .config import settings
from .tools import WorkspaceTools
from .llm_service import llm_service

class CodingAgent:
    """
    Autonomous Coding Agent that receives architecture steps from the planner
    and generates, validates, and writes source code files into the dedicated workspace.
    """
    def __init__(self, workspace_dir: Optional[Path] = None):
        self.workspace_dir = workspace_dir or settings.GENERATED_WORKSPACE_DIR
        self.tools = WorkspaceTools(workspace_root=self.workspace_dir)
        self.llm = llm_service

    def implement_step(self, goal: str, step: Dict[str, Any], context: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes a single planned development step by generating and writing the target file.
        """
        file_target = step.get("file_target")
        if not file_target or not isinstance(file_target, str) or not file_target.strip():
            return {
                "success": False,
                "step": step.get("step", 1),
                "role": step.get("role", "Code Builder"),
                "action": step.get("action", ""),
                "file_target": "",
                "bytes_written": 0,
                "explanation": "",
                "error": "No valid 'file_target' specified in step."
            }

        file_target = file_target.strip().replace(chr(92), "/")
        step_action = step.get("action", f"Create {file_target}")
        step_role = step.get("role", "Code Builder")
        step_num = step.get("step", 1)

        # Call LLM service to generate code
        gen_result = self.llm.generate_code(
            goal=goal,
            step_action=step_action,
            file_target=file_target,
            context=context
        )

        if not gen_result["success"]:
            return {
                "success": False,
                "step": step_num,
                "role": step_role,
                "action": step_action,
                "file_target": file_target,
                "bytes_written": 0,
                "explanation": "",
                "error": gen_result.get("error", "Code generation failed")
            }

        content = gen_result.get("content", "")
        if content is None:
            content = ""

        # Write to dedicated workspace directory safely
        try:
            write_msg = self.tools.write_file(file_target, content)
            return {
                "success": True,
                "step": step_num,
                "role": step_role,
                "action": step_action,
                "file_target": file_target,
                "bytes_written": len(content.encode("utf-8")),
                "explanation": gen_result.get("explanation", f"Successfully created {file_target}"),
                "write_message": write_msg,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "step": step_num,
                "role": step_role,
                "action": step_action,
                "file_target": file_target,
                "bytes_written": 0,
                "explanation": "",
                "error": f"Failed writing file '{file_target}': {str(e)}"
            }

    def implement_plan(self, goal: str, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Iterates through the execution steps of a development plan and implements each file target.
        """
        execution_steps = plan.get("execution_steps", [])
        if not execution_steps:
            return {
                "success": True,
                "total_steps": 0,
                "created_files": [],
                "step_results": [],
                "errors": []
            }

        created_files: List[str] = []
        step_results: List[Dict[str, Any]] = []
        errors: List[str] = []

        for step in execution_steps:
            file_target = step.get("file_target")
            if not file_target:
                continue

            # Pass list of already created files as context
            context_str = f"Already created files: {', '.join(created_files)}" if created_files else ""
            res = self.implement_step(goal=goal, step=step, context=context_str)
            step_results.append(res)

            if res["success"]:
                created_files.append(res["file_target"])
            else:
                errors.append(f"Step {res.get('step')}: {res.get('error')}")

        return {
            "success": len(errors) == 0,
            "total_steps": len(execution_steps),
            "created_files": created_files,
            "step_results": step_results,
            "errors": errors
        }

coding_agent = CodingAgent()
