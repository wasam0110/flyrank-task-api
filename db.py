"""
db.py — the only file that talks to Postgres.
main.py never imports psycopg directly — it calls these functions.
Swapping storage again in a future assignment means touching ONLY this file.
"""

import os
import psycopg
from dotenv import load_dotenv

load_dotenv()  # reads .env when running locally; ignored inside compose (env var already set)

DATABASE_URL = os.environ["DATABASE_URL"]


# ── internal helper ──────────────────────────────────────────────────────────

def _conn():
    """Open a fresh connection. Use inside `with` — auto-commits on success,
    rolls back on exception, and closes the connection either way."""
    return psycopg.connect(DATABASE_URL)


# ── bootstrap ────────────────────────────────────────────────────────────────

def init_db():
    """Create the tasks table if missing; seed three rows only on first run."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id    SERIAL  PRIMARY KEY,
                    title TEXT    NOT NULL,
                    done  BOOLEAN NOT NULL DEFAULT FALSE
                )
            """)
            cur.execute("SELECT COUNT(*) FROM tasks")
            if cur.fetchone()[0] == 0:
                cur.executemany(
                    "INSERT INTO tasks (title, done) VALUES (%s, %s)",
                    [
                        ("Buy groceries", False),
                        ("Read a book",   False),
                        ("Go for a walk", False),   # same seeds as your A2
                    ],
                )


# ── reads ────────────────────────────────────────────────────────────────────

def get_all() -> list[dict]:
    """SELECT * FROM tasks — returns a list of dicts."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, done FROM tasks ORDER BY id")
            return [{"id": r[0], "title": r[1], "done": r[2]} for r in cur.fetchall()]


def get_one(task_id: int) -> dict | None:
    """SELECT by id — returns a dict or None if not found."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, done FROM tasks WHERE id = %s",
                (task_id,),   # ← %s placeholder, value passed separately (parameterized)
            )
            row = cur.fetchone()
    return {"id": row[0], "title": row[1], "done": row[2]} if row else None


# ── writes ───────────────────────────────────────────────────────────────────

def create(title: str, done: bool = False) -> dict:
    """INSERT and return the new row (RETURNING hands back the generated id)."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id, title, done",
                (title, done),
            )
            row = cur.fetchone()
    return {"id": row[0], "title": row[1], "done": row[2]}


def update(task_id: int, title: str, done: bool) -> dict | None:
    """UPDATE by id — returns updated dict or None if id not found."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING id, title, done",
                (title, done, task_id),
            )
            row = cur.fetchone()
    return {"id": row[0], "title": row[1], "done": row[2]} if row else None


def delete(task_id: int) -> bool:
    """DELETE by id — returns True if a row was deleted, False if not found."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM tasks WHERE id = %s RETURNING id",
                (task_id,),
            )
            return cur.fetchone() is not None
