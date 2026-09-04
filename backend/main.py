import asyncio
import json
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from pydantic import BaseModel

from .config import settings
from .models import TaskRequest, TaskState
from .agent_engine import agent_engine, AgentEvent
from .tools import WorkspaceTools
from .llm_service import llm_service

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Autonomous AI Software Engineer Agent Server"
)

# Enable CORS for future frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

workspace_tools = WorkspaceTools()

class RequirementRequest(BaseModel):
    requirement: str

@app.get("/api/health")
async def health_check():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "workspace": str(settings.WORKSPACE_DIR),
        "llm_configured": llm_service.is_configured()
    }

@app.get("/api/llm/status")
async def get_llm_status():
    return {
        "configured": llm_service.is_configured(),
        "provider": llm_service.provider if llm_service.is_configured() else "None",
        "model": llm_service.model if llm_service.is_configured() else "None",
        "message": "LLM API Key present in environment." if llm_service.is_configured() else "No LLM API Key detected in environment variables. Set OPENAI_API_KEY, GEMINI_API_KEY, or LLM_API_KEY."
    }

@app.post("/api/llm/generate-plan")
async def generate_plan(req: RequirementRequest):
    if not req.requirement.strip():
        raise HTTPException(status_code=400, detail="Requirement prompt cannot be empty.")
    
    result = llm_service.generate_plan(req.requirement)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/api/tasks", response_model=TaskState)
async def create_task(request: TaskRequest):
    if not request.goal.strip():
        raise HTTPException(status_code=400, detail="Goal prompt cannot be empty.")
    
    task = agent_engine.create_task(goal=request.goal)
    # Schedule background execution of task
    asyncio.create_task(agent_engine.execute_task(task.task_id))
    return task

@app.get("/api/tasks", response_model=List[TaskState])
async def list_tasks():
    return agent_engine.list_tasks()

@app.get("/api/tasks/{task_id}", response_model=TaskState)
async def get_task(task_id: str):
    task = agent_engine.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    return task

@app.get("/api/workspace/files")
async def list_files(path: str = Query(".", description="Relative path inside workspace")):
    try:
        return {"files": workspace_tools.list_files(path)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/workspace/file")
async def read_file(path: str = Query(..., description="Relative path to file")):
    try:
        content = workspace_tools.read_file(path)
        return {"path": path, "content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File '{path}' not found.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.websocket("/ws/agent-stream")
async def websocket_agent_stream(websocket: WebSocket):
    await websocket.accept()
    
    async def send_event_to_client(event: AgentEvent):
        try:
            await websocket.send_text(event.model_dump_json())
        except Exception:
            pass

    agent_engine.subscribe(send_event_to_client)
    try:
        while True:
            # Keep connection alive & listen for client messages if any
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        agent_engine.unsubscribe(send_event_to_client)
    except Exception:
        agent_engine.unsubscribe(send_event_to_client)
