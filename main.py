from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# App setup  (Stage 0 - hello server)
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Task API",
    version="1.0",
    description="A simple in-memory CRUD API for managing tasks.",
    docs_url="/docs",   # Swagger UI — free in FastAPI, no setup needed
)


# ─────────────────────────────────────────────────────────────────────────────
# Error format: always {"error": "..."} for every 4xx response
# ─────────────────────────────────────────────────────────────────────────────
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Converts Pydantic's 422 into the assignment's 400 format."""
    first = exc.errors()[0]
    field = first["loc"][-1] if first.get("loc") else "body"
    return JSONResponse(
        status_code=400,
        content={"error": f"'{field}' {first['msg']}"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# In-memory store  (Stage 2 — no database, data is lost on restart)
# ─────────────────────────────────────────────────────────────────────────────
tasks: list[dict] = [
    {"id": 1, "title": "Buy groceries", "done": False},
    {"id": 2, "title": "Read a book",   "done": True},
    {"id": 3, "title": "Go for a run",  "done": False},
]
_next_id = 4   # tracks the next id to hand out


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic request models
# ─────────────────────────────────────────────────────────────────────────────
class TaskCreate(BaseModel):
    title: str               # required — missing field auto-returns 400

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done:  Optional[bool] = None


# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — Root & health endpoints
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/", summary="API info", tags=["Info"])
def root():
    """Describes this API: name, version, and available endpoint groups."""
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }

@app.get("/health", summary="Health check", tags=["Info"])
def health():
    """Returns 200 OK when the server is alive. Real companies poll this."""
    return {"status": "ok"}


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — Read: list all tasks and get one by id
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/tasks", summary="List all tasks", tags=["Tasks"])
def list_tasks():
    """Returns every task in the store."""
    return tasks

@app.get("/tasks/{id}", summary="Get one task", tags=["Tasks"])
def get_task(id: int):
    """Returns a single task by ID. 404 if the ID does not exist."""
    task = next((t for t in tasks if t["id"] == id), None)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {id} not found")
    return task


# ─────────────────────────────────────────────────────────────────────────────
# Stage 3 — Create: POST a new task
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/tasks", status_code=201, summary="Create a task", tags=["Tasks"])
def create_task(body: TaskCreate):
    """
    Creates a new task.
    - Requires a non-empty **title** in the JSON body.
    - Returns the created task with status **201 Created**.
    - Missing or empty title returns **400 Bad Request**.
    """
    global _next_id
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="'title' must not be empty")
    task = {"id": _next_id, "title": body.title.strip(), "done": False}
    tasks.append(task)
    _next_id += 1
    return task


# ─────────────────────────────────────────────────────────────────────────────
# Stage 4 — Update & Delete
# ─────────────────────────────────────────────────────────────────────────────
@app.put("/tasks/{id}", summary="Update a task", tags=["Tasks"])
def update_task(id: int, body: TaskUpdate):
    """
    Updates **title** and/or **done** on an existing task.
    - Returns the updated task.
    - Unknown ID returns **404**. Empty body returns **400**.
    """
    task = next((t for t in tasks if t["id"] == id), None)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {id} not found")
    if body.title is None and body.done is None:
        raise HTTPException(
            status_code=400,
            detail="Body must include at least 'title' or 'done'",
        )
    if body.title is not None:
        if not body.title.strip():
            raise HTTPException(status_code=400, detail="'title' must not be empty")
        task["title"] = body.title.strip()
    if body.done is not None:
        task["done"] = body.done
    return task

@app.delete("/tasks/{id}", status_code=204, summary="Delete a task", tags=["Tasks"])
def delete_task(id: int):
    """
    Removes a task by ID.
    - Returns **204 No Content** on success (nothing to say).
    - Unknown ID returns **404**.
    """
    global tasks
    task = next((t for t in tasks if t["id"] == id), None)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {id} not found")
    tasks = [t for t in tasks if t["id"] != id]
    return Response(status_code=204)