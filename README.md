# flyrank-task-api

A simple in-memory CRUD API for managing tasks, built with Python and FastAPI.
Built as Week 2 Assignment A1 of the FlyRank Backend Internship Track.

---

## How to run

```bash
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Server starts at `http://localhost:8000`  
Swagger UI is available at `http://localhost:8000/docs`

---

## Endpoints

| Method | Path | Description | Success Code |
|--------|------|-------------|--------------|
| GET | `/` | API info | 200 |
| GET | `/health` | Health check | 200 |
| GET | `/tasks` | List all tasks | 200 |
| GET | `/tasks/{id}` | Get one task by ID | 200 |
| POST | `/tasks` | Create a new task | 201 |
| PUT | `/tasks/{id}` | Update title and/or done | 200 |
| DELETE | `/tasks/{id}` | Delete a task | 204 |

### Error codes

| Code | Meaning |
|------|---------|
| 400 | Missing or empty `title`, or empty request body |
| 404 | Task ID does not exist |

---

## Example curl output

```
curl -i -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy milk"}'

HTTP/1.1 201 Created
content-type: application/json
content-length: 40

{"id":4,"title":"Buy milk","done":false}
```

---

## Swagger UI

![Swagger UI](swagger-screenshot.png)

---

## The mortality experiment

After creating a few tasks and restarting the server, all tasks reset to the original 3 seed tasks — everything added at runtime was gone. This happens because the data lives only in the program's memory (a Python list), which is wiped every time the process stops. This is the entire reason databases exist, and exactly what Week 3 introduces.
