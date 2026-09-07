# 🤖 Autonomous AI Software Engineer

An AI-powered software engineering system that can **plan, generate, test, and debug software automatically**.

## 🚀 What It Does

The system takes a software requirement from the user and passes it through multiple AI agents:

User Requirement  
↓  
🧠 Planner  
↓  
💻 Coding Agent  
↓  
🧪 Testing Agent  
↓  
🔧 Debugging Agent  
↓  
✅ Final Result

## ✨ Features

- AI-based software planning using Gemini
- Autonomous code generation
- Automatic pytest test generation
- Automatic test execution
- AI-based debugging and code fixing
- Automatic retry loop for failed tests
- Workspace sandbox for generated code
- FastAPI backend
- React + Vite dashboard
- WebSocket agent event streaming
- Environment-variable API key protection

## 🏗️ Architecture

```text
React + Vite Dashboard
          │
          │ REST / WebSocket
          ↓
      FastAPI Server
          │
          ↓
   Autonomous Agent Engine
      │      │      │
      ↓      ↓      ↓
   Planner  Coder  Tester
                    │
                    ↓
                 Debugger
                    │
                    ↓
                 Workspace