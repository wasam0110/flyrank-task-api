"""
main.py — FastAPI routes only.
No SQL here. Every storage call goes through db.py.
Compare with your A2 main.py — the routes are almost identical.
Only `import sqlite3` and the inline SQL are gone.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import db

app = FastAPI(title="FlyRank Task API", version="A3 — Containerized Postgres")


# ── startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    """Create the tasks table and seed on first run."""
    db.init_db()


# ── request body model ───────────────────────────────────────────────────────

class TaskIn(BaseModel):
    title: str
    done: Optional[bool] = False


# ── routes ───────────────────────────────────────────────────────────────────

@app.get("/tasks")
def get_tasks():
    """Return all tasks from Postgres."""
    return db.get_all()


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    """Return one task by ID, or 404 if not found."""
    task = db.get_one(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail={"error": "Task not found"})
    return task


@app.post("/tasks", status_code=201)
def create_task(task: TaskIn):
    """Insert a new task and return it with its generated ID."""
    if not task.title or not task.title.strip():
        raise HTTPException(status_code=400, detail={"error": "Title is required"})
    return db.create(task.title.strip(), task.done)


@app.put("/tasks/{task_id}")
def update_task(task_id: int, task: TaskIn):
    """Update title and done status of an existing task."""
    if not task.title or not task.title.strip():
        raise HTTPException(status_code=400, detail={"error": "Title is required"})
    updated = db.update(task_id, task.title.strip(), task.done)
    if updated is None:
        raise HTTPException(status_code=404, detail={"error": "Task not found"})
    return updated


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    """Delete a task. Returns 204 (no body) on success."""
    if not db.delete(task_id):
        raise HTTPException(status_code=404, detail={"error": "Task not found"})


# ── extras ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "FlyRank Task API — A3", "docs": "/docs"}
