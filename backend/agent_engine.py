import asyncio
import uuid
from typing import Dict, List, Callable, Awaitable, Optional
from datetime import datetime

from .models import (
    TaskState,
    TaskStatus,
    AgentStep,
    AgentRole,
    ToolCall,
    AgentEvent,
)
from .tools import WorkspaceTools
from .llm_service import llm_service
from .coding_agent import coding_agent
from .testing_agent import testing_agent
from .debugging_agent import debugging_agent
from .config import settings


class AutonomousAgentEngine:
    def __init__(self):
        self.tasks: Dict[str, TaskState] = {}

        self.tools = WorkspaceTools(
            workspace_root=settings.GENERATED_WORKSPACE_DIR
        )

        self.listeners: List[
            Callable[[AgentEvent], Awaitable[None]]
        ] = []

    def subscribe(self, callback: Callable[[AgentEvent], Awaitable[None]]):
        self.listeners.append(callback)

    def unsubscribe(self, callback: Callable[[AgentEvent], Awaitable[None]]):
        if callback in self.listeners:
            self.listeners.remove(callback)

    async def broadcast_event(
        self,
        event_type: str,
        task_id: str,
        payload: Dict,
    ):
        event = AgentEvent(
            event_type=event_type,
            task_id=task_id,
            payload=payload,
        )

        for listener in self.listeners:
            try:
                await listener(event)
            except Exception as e:
                print(f"Error broadcasting event to listener: {e}")

    def create_task(self, goal: str) -> TaskState:
        task_id = f"task_{uuid.uuid4().hex[:8]}"

        task = TaskState(
            task_id=task_id,
            goal=goal,
            status=TaskStatus.PENDING,
        )

        self.tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[TaskState]:
        return self.tasks.get(task_id)

    def list_tasks(self) -> List[TaskState]:
        return list(self.tasks.values())

    async def execute_task(self, task_id: str):
        task = self.get_task(task_id)

        if not task:
            return

        try:
            # ==========================================================
            # STEP 1: PLANNING
            # ==========================================================

            task.status = TaskStatus.PLANNING

            await self.broadcast_event(
                "TASK_STATUS_CHANGED",
                task_id,
                {"status": task.status},
            )

            llm_plan_res = llm_service.generate_plan(task.goal)

            # ----------------------------------------------------------
            # IMPORTANT:
            # Handle LLM failures such as HTTP 429 quota errors safely.
            # Do not continue with a None plan.
            # ----------------------------------------------------------

            if not llm_plan_res.get("success"):
                error_message = llm_plan_res.get(
                    "error",
                    "Unable to generate a development plan.",
                )

                task.status = TaskStatus.FAILED
                task.error = error_message

                step_1 = AgentStep(
                    step_id=1,
                    role=AgentRole.ARCHITECT,
                    thought=(
                        "The planning agent could not generate "
                        "a development plan."
                    ),
                    action_description=error_message,
                )

                task.steps.append(step_1)

                await self.broadcast_event(
                    "STEP_ADDED",
                    task_id,
                    {"step": step_1.model_dump()},
                )

                await self.broadcast_event(
                    "TASK_FAILED",
                    task_id,
                    {"error": error_message},
                )

                return

            plan_obj = llm_plan_res.get("plan")

            if not isinstance(plan_obj, dict):
                error_message = (
                    "The LLM returned an invalid development plan."
                )

                task.status = TaskStatus.FAILED
                task.error = error_message

                await self.broadcast_event(
                    "TASK_FAILED",
                    task_id,
                    {"error": error_message},
                )

                return

            steps_count = len(
                plan_obj.get("execution_steps", [])
            )

            plan_summary = (
                f"LLM Plan Generated "
                f"({llm_plan_res.get('provider', 'unknown')}/"
                f"{llm_plan_res.get('model', 'unknown')}): "
                f"{steps_count} steps planned."
            )

            thought = (
                f"Received LLM plan for requirement: "
                f"'{task.goal}'."
            )

            step_1 = AgentStep(
                step_id=1,
                role=AgentRole.ARCHITECT,
                thought=thought,
                action_description=plan_summary,
            )

            task.steps.append(step_1)

            await self.broadcast_event(
                "STEP_ADDED",
                task_id,
                {"step": step_1.model_dump()},
            )

            await asyncio.sleep(0.3)

            # ==========================================================
            # STEP 2: CODING
            # ==========================================================

            task.status = TaskStatus.EXECUTING

            await self.broadcast_event(
                "TASK_STATUS_CHANGED",
                task_id,
                {"status": task.status},
            )

            coding_result = coding_agent.implement_plan(
                task.goal,
                plan_obj,
            )

            if not coding_result.get("success"):
                error_message = coding_result.get(
                    "errors",
                    "Coding Agent failed.",
                )

                if isinstance(error_message, list):
                    error_message = "; ".join(
                        str(x) for x in error_message
                    )

                raise RuntimeError(error_message)

            created_files = coding_result.get(
                "created_files",
                [],
            )

            task.created_files.extend(created_files)

            step_2 = AgentStep(
                step_id=2,
                role=AgentRole.CODER,
                thought=(
                    f"Coding Agent generated "
                    f"{len(created_files)} project files."
                ),
                action_description=(
                    f"Created {len(created_files)} files "
                    f"inside the workspace."
                ),
                tool_call=ToolCall(
                    tool_name="coding_agent.implement_plan",
                    arguments={"goal": task.goal},
                    output=", ".join(created_files),
                    success=True,
                ),
            )

            task.steps.append(step_2)

            await self.broadcast_event(
                "STEP_ADDED",
                task_id,
                {"step": step_2.model_dump()},
            )

            await asyncio.sleep(0.3)

            # ==========================================================
            # STEP 3: TESTING
            # ==========================================================

            task.status = TaskStatus.VERIFYING

            await self.broadcast_event(
                "TASK_STATUS_CHANGED",
                task_id,
                {"status": task.status},
            )

            test_result = testing_agent.test_workspace()

            test_output = test_result.get(
                "output",
                "",
            )

            test_errors = test_result.get(
                "errors",
                "",
            )

            step_3 = AgentStep(
                step_id=3,
                role=AgentRole.TESTER,
                thought=(
                    "Testing Agent generated pytest tests "
                    "and executed them."
                ),
                action_description=(
                    "Generated and executed automated tests."
                ),
                tool_call=ToolCall(
                    tool_name="testing_agent.test_workspace",
                    arguments={},
                    output=test_output,
                    success=test_result.get("success", False),
                ),
            )

            task.steps.append(step_3)

            await self.broadcast_event(
                "STEP_ADDED",
                task_id,
                {"step": step_3.model_dump()},
            )

            await asyncio.sleep(0.3)

            # ==========================================================
            # STEP 4: DEBUGGING LOOP
            # ==========================================================

            debugging_attempts = 0
            max_attempts = 3

            while (
                not test_result.get("success", False)
                and debugging_attempts < max_attempts
            ):
                debugging_attempts += 1

                await self.broadcast_event(
                    "DEBUGGING_STARTED",
                    task_id,
                    {
                        "attempt": debugging_attempts,
                        "max_attempts": max_attempts,
                    },
                )

                source_files = test_result.get(
                    "source_files",
                    [],
                )

                if not source_files:
                    break

                fixed_any_file = False

                for source_file in source_files:
                    debug_result = debugging_agent.debug_file(
                        file_path=source_file,
                        test_output=test_output,
                        test_errors=test_errors,
                    )

                    if debug_result.get("success"):
                        fixed_any_file = True

                        await self.broadcast_event(
                            "DEBUGGING_COMPLETED",
                            task_id,
                            {
                                "attempt": debugging_attempts,
                                "file": source_file,
                                "explanation": debug_result.get(
                                    "explanation",
                                    "",
                                ),
                            },
                        )

                        break

                if not fixed_any_file:
                    break

                # Run the Testing Agent again after the fix.
                test_result = testing_agent.test_workspace()

                test_output = test_result.get(
                    "output",
                    "",
                )

                test_errors = test_result.get(
                    "errors",
                    "",
                )

                await self.broadcast_event(
                    "TEST_RETRY",
                    task_id,
                    {
                        "attempt": debugging_attempts,
                        "success": test_result.get(
                            "success",
                            False,
                        ),
                        "output": test_output,
                    },
                )

            # ==========================================================
            # STEP 5: FINAL RESULT
            # ==========================================================

            if test_result.get("success", False):
                task.status = TaskStatus.COMPLETED

                await self.broadcast_event(
                    "FINAL_RESULT",
                    task_id,
                    {
                        "status": "success",
                        "message": "All tests passed.",
                        "created_files": task.created_files,
                        "test_output": test_output,
                        "debugging_attempts": debugging_attempts,
                    },
                )

            else:
                task.status = TaskStatus.FAILED

                task.error = (
                    "Tests did not pass after the maximum "
                    "debugging attempts."
                )

                await self.broadcast_event(
                    "FINAL_RESULT",
                    task_id,
                    {
                        "status": "failed",
                        "message": task.error,
                        "created_files": task.created_files,
                        "test_output": test_output,
                        "test_errors": test_errors,
                        "debugging_attempts": debugging_attempts,
                    },
                )

            task.completed_at = datetime.now().isoformat()

            await self.broadcast_event(
                "TASK_STATUS_CHANGED",
                task_id,
                {
                    "status": task.status,
                    "completed_at": task.completed_at,
                },
            )

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)

            await self.broadcast_event(
                "TASK_FAILED",
                task_id,
                {"error": str(e)},
            )


agent_engine = AutonomousAgentEngine()