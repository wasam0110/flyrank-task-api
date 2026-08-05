from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from supabase import create_client
from dotenv import load_dotenv
import os
import db

load_dotenv()

app = FastAPI(title="FlyRank Task API", version="A4 — Auth")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
security = HTTPBearer()
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

# ── auth models ────────────────────────────────────────────────────────────────

class AuthCredentials(BaseModel):
    email: str
    password: str


# ── auth guard (reusable middleware) ───────────────────────────────────────────

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        result = supabase.auth.get_user(token)
        return result.user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ── auth routes ────────────────────────────────────────────────────────────────

@app.post("/auth/signup", status_code=201)
def signup(creds: AuthCredentials):
    if not creds.email or not creds.password:
        raise HTTPException(status_code=400, detail="Email and password required")
    try:
        result = supabase.auth.sign_up({"email": creds.email, "password": creds.password})
        return {"user": result.user}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login")
def login(creds: AuthCredentials):
    if not creds.email or not creds.password:
        raise HTTPException(status_code=400, detail="Email and password required")
    try:
        result = supabase.auth.sign_in_with_password({"email": creds.email, "password": creds.password})
        return {
            "access_token": result.session.access_token,
            "refresh_token": result.session.refresh_token,
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid login credentials")


@app.post("/auth/logout")
def logout(user=Depends(get_current_user)):
    supabase.auth.sign_out()
    return {"message": "Logged out successfully"}

# ── protected routes ───────────────────────────────────────────────────────────

@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile")
def profile(user=Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "created_at": user.created_at}


@app.get("/protected/dashboard")
def dashboard(user=Depends(get_current_user)):
    return {"message": f"Welcome to your dashboard, {user.email}!"}