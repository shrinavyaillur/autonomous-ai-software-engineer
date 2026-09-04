from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class AgentRole(str, Enum):
    ARCHITECT = "Architect & Planner"
    CODER = "Code Builder & Refactor"
    REVIEWER = "Quality Reviewer"
    TESTER = "Automated Tester"

class ToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    output: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None

class AgentStep(BaseModel):
    step_id: int
    role: AgentRole
    thought: str
    action_description: str
    tool_call: Optional[ToolCall] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class TaskRequest(BaseModel):
    goal: str
    workspace_relative_path: Optional[str] = "."

class TaskState(BaseModel):
    task_id: str
    goal: str
    status: TaskStatus = TaskStatus.PENDING
    steps: List[AgentStep] = []
    created_files: List[str] = []
    modified_files: List[str] = []
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    error: Optional[str] = None

class AgentEvent(BaseModel):
    event_type: str  # e.g., "TASK_STARTED", "STEP_UPDATE", "TOOL_CALL", "TASK_COMPLETED", "TASK_FAILED"
    task_id: str
    payload: Dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
