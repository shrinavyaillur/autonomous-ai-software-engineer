import { useRef, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";
const WS_URL = "ws://127.0.0.1:8000/ws/agent-stream";

function App() {
  const [task, setTask] = useState("");
  const [taskId, setTaskId] = useState("");
  const [status, setStatus] = useState("IDLE");
  const [steps, setSteps] = useState([]);
  const [result, setResult] = useState("");
  const [events, setEvents] = useState([]);

  const socketRef = useRef(null);

  const workflow = [
    { key: "PLANNING", icon: "🧠", name: "Planner" },
    { key: "EXECUTING", icon: "💻", name: "Coder" },
    { key: "VERIFYING", icon: "🧪", name: "Tester" },
    { key: "DEBUGGING", icon: "🔧", name: "Debugger" },
  ];

  const addEvent = (message) => {
    setEvents((previous) => [
      ...previous,
      `${new Date().toLocaleTimeString()} — ${message}`,
    ]);
  };

  const connectWebSocket = () => {
    return new Promise((resolve, reject) => {
      const socket = new WebSocket(WS_URL);

      socketRef.current = socket;

      socket.onopen = () => {
        addEvent("Connected to agent stream");
        resolve(socket);
      };

      socket.onerror = () => {
        reject(new Error("WebSocket connection failed."));
      };

      socket.onmessage = (message) => {
        try {
          const event = JSON.parse(message.data);

          const type = event.event_type;
          const payload = event.payload || {};

          if (type === "TASK_STATUS_CHANGED") {
            const newStatus = String(payload.status || "").replace(
              "TaskStatus.",
              ""
            );

            setStatus(newStatus);
            addEvent(`Task status changed to ${newStatus}`);
          }

          if (type === "STEP_ADDED") {
            const step = payload.step;

            if (step) {
              setSteps((previous) => [...previous, step]);
              addEvent(
                `Agent step: ${
                  step.action_description || "Step completed"
                }`
              );
            }
          }

          if (type === "DEBUGGING_STARTED") {
            setStatus("DEBUGGING");

            addEvent(
              `Debugger started — attempt ${payload.attempt || 1}`
            );
          }

          if (type === "DEBUGGING_COMPLETED") {
            addEvent(
              `Debugger fixed ${payload.file || "the source file"}`
            );
          }

          if (type === "TEST_RETRY") {
            setStatus("VERIFYING");

            addEvent(
              `Testing again after debugging attempt ${
                payload.attempt || 1
              }`
            );
          }

          if (type === "FINAL_RESULT") {
            const finalStatus = payload.status;

            if (finalStatus === "success") {
              setStatus("COMPLETED");
              setResult(
                JSON.stringify(payload, null, 2)
              );
              addEvent("All tests passed — task completed");
            } else {
              setStatus("FAILED");
              setResult(
                JSON.stringify(payload, null, 2)
              );
              addEvent("Task failed");
            }

            socket.close();
          }

          if (type === "TASK_FAILED") {
            setStatus("FAILED");

            setResult(
              payload.error || "The task failed."
            );

            addEvent(`Task failed: ${payload.error || "Unknown error"}`);

            socket.close();
          }
        } catch (error) {
          console.error("Invalid WebSocket event:", error);
        }
      };

      socket.onclose = () => {
        addEvent("Agent stream disconnected");
      };
    });
  };

  const runAgent = async () => {
    if (!task.trim()) {
      setResult("Please enter a task.");
      return;
    }

    setStatus("STARTING");
    setSteps([]);
    setEvents([]);
    setResult("");
    setTaskId("");

    try {
      // Connect BEFORE creating the task so we don't miss early events.
      try {
        await connectWebSocket();
      } catch (error) {
        addEvent("Live stream unavailable; using task polling.");
      }

      const response = await fetch(`${API_URL}/api/tasks`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          goal: task,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Could not create task."
        );
      }

      setTaskId(data.task_id);

      addEvent(`Task created: ${data.task_id}`);

      // Fallback polling in case WebSocket misses an event.
      watchTask(data.task_id);
    } catch (error) {
      setStatus("FAILED");
      setResult(error.message);
    }
  };

  const watchTask = (id) => {
    const poll = async () => {
      try {
        const response = await fetch(
          `${API_URL}/api/tasks/${id}`
        );

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            data.detail || "Could not get task status."
          );
        }

        // Polling acts as a safety fallback.
        setStatus(data.status);
        setSteps(data.steps || []);

        if (data.status === "COMPLETED") {
          setResult(
            JSON.stringify(
              {
                task_id: data.task_id,
                status: data.status,
                created_files: data.created_files,
                steps: data.steps,
              },
              null,
              2
            )
          );
          return;
        }

        if (data.status === "FAILED") {
          setResult(
            data.error ||
              "The AI agent could not complete the task."
          );
          return;
        }

        setTimeout(() => poll(), 2000);
      } catch (error) {
        console.error(error);
      }
    };

    poll();
  };

  const getStepState = (stepKey) => {
    if (status === "FAILED") {
      return "waiting";
    }

    if (status === "COMPLETED") {
      return "done";
    }

    if (status === stepKey) {
      return "active";
    }

    const order = [
      "PLANNING",
      "EXECUTING",
      "VERIFYING",
      "DEBUGGING",
    ];

    const currentIndex = order.indexOf(status);
    const stepIndex = order.indexOf(stepKey);

    if (
      currentIndex >= 0 &&
      stepIndex >= 0 &&
      stepIndex < currentIndex
    ) {
      return "done";
    }

    return "waiting";
  };

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>🤖 Autonomous AI Software Engineer</h1>
          <p>
            AI that plans, codes, tests and debugs software
          </p>
        </div>

        <div
          className={`status-badge ${status.toLowerCase()}`}
        >
          {status}
        </div>
      </header>

      <main className="main">
        <section className="card">
          <h2>Give the AI a task</h2>

          <textarea
            value={task}
            onChange={(e) => setTask(e.target.value)}
            placeholder="Example: Build a Python calculator with tests"
          />

          <button onClick={runAgent}>
            🚀 Run AI Engineer
          </button>

          {taskId && (
            <div className="task-info">
              Task ID: {taskId}
            </div>
          )}
        </section>

        <section className="card">
          <h2>Agent Workflow</h2>

          <div className="workflow">
            {workflow.map((agent, index) => {
              const state = getStepState(agent.key);

              return (
                <div
                  className="workflow-item"
                  key={agent.key}
                >
                  <div className={`agent-node ${state}`}>
                    <div className="agent-icon">
                      {agent.icon}
                    </div>

                    <strong>{agent.name}</strong>

                    <span>
                      {state === "active"
                        ? "Working..."
                        : state === "done"
                        ? "Done"
                        : "Waiting"}
                    </span>
                  </div>

                  {index < workflow.length - 1 && (
                    <div className="workflow-arrow">
                      →
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        <section className="card">
          <h2>Execution Steps</h2>

          {steps.length === 0 ? (
            <p className="empty">
              No steps yet.
            </p>
          ) : (
            <div className="steps-list">
              {steps.map((step, index) => (
                <div
                  className="step-item"
                  key={index}
                >
                  <strong>
                    {step.role?.replaceAll("_", " ")}
                  </strong>

                  <p>
                    {step.action_description}
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="card">
          <h2>Live Agent Events</h2>

          {events.length === 0 ? (
            <p className="empty">
              Waiting for your task...
            </p>
          ) : (
            <div className="output">
              {events.map((event, index) => (
                <div key={index}>{event}</div>
              ))}
            </div>
          )}
        </section>

        <section className="card">
          <h2>Agent Output</h2>

          <pre className="output">
            {result || "Waiting for your task..."}
          </pre>
        </section>
      </main>
    </div>
  );
}

export default App;