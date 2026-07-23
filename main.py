import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI()


# ─── DATABASE SETUP ───────────────────────────────────────────────────────────

def get_db():
    """Open a connection to tasks.db. Creates the file if it doesn't exist."""
    conn = sqlite3.connect("tasks.db")
    conn.row_factory = sqlite3.Row  # lets you do dict(row) to get JSON-friendly output
    return conn


def init_db():
    """Create the tasks table and seed 3 starter tasks — only on first run."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT    NOT NULL,
            done  INTEGER NOT NULL DEFAULT 0
        )
    """)
    # Only seed if table is empty — stops duplicates on every restart
    count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    if count == 0:
        conn.executemany(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            [
                ("Buy groceries", 0),
                ("Read a book", 0),
                ("Go for a walk", 0),
            ]
        )
    conn.commit()
    conn.close()


init_db()  # runs once when the server starts


# ─── REQUEST BODY MODEL ───────────────────────────────────────────────────────

class TaskIn(BaseModel):
    title: str
    done: Optional[bool] = False


# ─── ROUTES ───────────────────────────────────────────────────────────────────

@app.get("/tasks")
def get_tasks():
    """Return all tasks from the database."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    """Return one task by ID, or 404 if not found."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404,
                            detail={"error": "Task not found"})
    return dict(row)


@app.post("/tasks", status_code=201)
def create_task(task: TaskIn):
    """Insert a new task and return it with its new ID."""
    if not task.title or not task.title.strip():
        raise HTTPException(status_code=400,
                            detail={"error": "Title is required"})
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        (task.title.strip(), 1 if task.done else 0)
    )
    conn.commit()
    new_id = cursor.lastrowid  # the ID SQLite just assigned
    row = conn.execute(
        "SELECT * FROM tasks WHERE id = ?", (new_id,)
    ).fetchone()
    conn.close()
    return dict(row)


@app.put("/tasks/{task_id}")
def update_task(task_id: int, task: TaskIn):
    """Update title and done status of an existing task."""
    if not task.title or not task.title.strip():
        raise HTTPException(status_code=400,
                            detail={"error": "Title is required"})
    conn = get_db()
    existing = conn.execute(
        "SELECT * FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    if existing is None:
        conn.close()
        raise HTTPException(status_code=404,
                            detail={"error": "Task not found"})
    conn.execute(
        "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
        (task.title.strip(), 1 if task.done else 0, task_id)
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    conn.close()
    return dict(row)


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    """Delete a task. Returns 204 (no body) on success."""
    conn = get_db()
    existing = conn.execute(
        "SELECT * FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    if existing is None:
        conn.close()
        raise HTTPException(status_code=404,
                            detail={"error": "Task not found"})
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return