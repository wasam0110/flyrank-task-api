# FlyRank Task API

A CRUD Task API built with **FastAPI**, **PostgreSQL**, and **Docker Compose**.

The application demonstrates the progression of storage across assignments while keeping the API layer unchanged.

| Assignment | Storage | Technology |
|------------|---------|------------|
| A1 | In-memory Python list | Python |
| A2 | SQLite database | SQLite |
| **A3** | PostgreSQL | Docker + PostgreSQL |

---

# Features

- FastAPI REST API
- PostgreSQL database
- psycopg3 database driver
- Parameterized SQL queries
- Dockerized application
- Docker Compose orchestration
- Automatic database initialization
- Persistent database storage using Docker volumes
- Interactive Swagger documentation

---

# Project Structure

```
.
├── main.py
├── db.py
├── Dockerfile
├── compose.yaml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

# Running the project

## Using Docker Compose (Recommended)

```bash
docker compose up --build
```

The API becomes available at

```
http://localhost:8000
```

Swagger documentation

```
http://localhost:8000/docs
```

Stop the application

```bash
docker compose down
```

Database data is preserved using a named Docker volume.

---

# Running locally

Create the environment file

```bash
cp .env.example .env
```

Example

```text
DATABASE_URL=postgresql://postgres:dev@localhost:5432/tasks
```

> If port **5432** is already occupied by another PostgreSQL installation, use another host port (for example **5433**) and update the connection string accordingly.

Install dependencies

```bash
pip install -r requirements.txt
```

Initialize the database

```bash
python -c "import db; db.init_db(); print('Database initialized successfully')"
```

Run the API

```bash
uvicorn main:app --reload
```

---

# Environment Variables

| Variable | Description |
|----------|-------------|
| DATABASE_URL | PostgreSQL connection string |

Example

```
DATABASE_URL=postgresql://postgres:dev@localhost:5432/tasks
```

Never commit your `.env` file.

---

# API Endpoints

| Method | Endpoint | Description | Success |
|--------|----------|-------------|---------|
| GET | /tasks | Retrieve all tasks | 200 |
| GET | /tasks/{id} | Retrieve a task | 200 |
| POST | /tasks | Create task | 201 |
| PUT | /tasks/{id} | Update task | 200 |
| DELETE | /tasks/{id} | Delete task | 204 |
| GET | /health | Health check | 200 |

Possible error codes

- 400 Bad Request
- 404 Not Found

---

# Example curl Commands

Retrieve all tasks

```bash
curl -i http://localhost:8000/tasks
```

Create

```bash
curl -i -X POST http://localhost:8000/tasks \
-H "Content-Type: application/json" \
-d '{"title":"Ship A3","done":false}'
```

Update

```bash
curl -i -X PUT http://localhost:8000/tasks/4 \
-H "Content-Type: application/json" \
-d '{"title":"Ship A3","done":true}'
```

Delete

```bash
curl -i -X DELETE http://localhost:8000/tasks/4
```

---

# Database Verification

Run

```sql
\dt
```

Expected

```
List of relations

public | tasks | table | postgres
```

Run

```sql
SELECT * FROM tasks;
```

Replace this section with screenshots from your own PostgreSQL database before submission.

---

# Docker Persistence Test

1. Start the application

```
docker compose up
```

2. Create a new task.

3. Stop the application.

```
docker compose down
```

4. Start again.

```
docker compose up
```

5. Verify that the task still exists.

This demonstrates persistent storage using Docker volumes.

---

# Why the Architecture Works

The API layer never communicates with PostgreSQL directly.

All database operations are isolated inside **db.py**.

Changing the storage engine only requires updating the repository layer, while every API endpoint remains unchanged.

This follows the layered architecture introduced in the course.

---

# Stage 6 – AI vs Me

## Prompt Given to AI

> Write all the files needed to containerize a FastAPI task CRUD API onto PostgreSQL. The app uses FastAPI with uvicorn and psycopg (psycopg3) as the database driver. Keep the existing Pydantic TaskIn model with title (str) and done (bool). Create the tasks table automatically if it doesn't exist and seed exactly three rows on first run only. All SQL must use parameterized queries. Store credentials in a .env file. Use Docker Compose with PostgreSQL and persistent Docker volumes.

## Three Differences

| # | AI Output | My Implementation |
|---|-----------|-------------------|
| 1 | Started the API immediately after the database container | Waited until PostgreSQL became healthy using `depends_on` with `condition: service_healthy` |
| 2 | Did not fully explain Docker volume persistence | Configured and verified persistent Docker volumes across restarts |
| 3 | Generated generic project documentation | Added assignment-specific documentation, curl examples, setup instructions, and verification steps |

## What My Prompt Missed

The original prompt did not explicitly require health checks, detailed documentation, or database verification screenshots.

## Rematch Result

After improving the prompt with health-check and documentation requirements, the AI generated a deployment configuration that required only minor manual adjustments.

---

# Assignment Progression

## Week 3 (A3)

PostgreSQL running inside Docker with persistent storage and Docker Compose.

## Week 2 (A2)

SQLite database stored locally in `tasks.db`.

## Week 1 (A1)

Tasks stored only in memory and lost when the application stopped.

---

# Technologies Used

- Python
- FastAPI
- PostgreSQL
- psycopg3
- Docker
- Docker Compose
- Uvicorn