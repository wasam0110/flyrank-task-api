FlyRank Task API

A CRUD Task API built with FastAPI, PostgreSQL, and Docker Compose, extended with Supabase authentication in A4.

The application demonstrates the progression of storage and security across assignments while keeping the API layer unchanged.

Assignment
Storage
Technology
A1
In-memory Python list
Python
A2
SQLite database
SQLite
A3
PostgreSQL
Docker + PostgreSQL
A4
PostgreSQL + Supabase Auth
FastAPI + JWT
A9
Local JSON output + HTML cache
Requests + Beautiful Soup + Pydantic







Features

•
FastAPI REST API

•
PostgreSQL database

•
psycopg3 database driver

•
Parameterized SQL queries

•
Dockerized application

•
Docker Compose orchestration

•
Automatic database initialization

•
Persistent database storage using Docker volumes

•
Supabase Auth — signup, login, logout

•
JWT verification via Supabase

•
Protected routes with reusable auth middleware

•
Interactive Swagger documentation with bearer auth




Project Structure

Plain Text


.
├── main.py
├── db.py
├── Dockerfile
├── compose.yaml
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── scraper/
    ├── README.md
    ├── requirements.txt
    ├── src/
    ├── tests/
    ├── cache/
    └── output/






Environment Variables

Variable
Description
DATABASE_URL
PostgreSQL connection string
SUPABASE_URL
Your Supabase project URL
SUPABASE_KEY
Your Supabase anon key




Create your .env from the example:

Bash


cp .env.example .env



.env.example:

Plain Text


DATABASE_URL=postgresql://postgres:dev@localhost:5432/tasks
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key



Never commit your .env file.




Running the project

Install dependencies:

Bash


pip install -r requirements.txt



Run the API:

Bash


uvicorn main:app --reload



The API becomes available at:

Plain Text


http://localhost:8000



Swagger documentation:

Plain Text


http://localhost:8000/docs






API Endpoints

Task endpoints (A1–A3 )

Method
Endpoint
Description
Auth
Success
GET
/tasks
Retrieve all tasks
None
200
GET
/tasks/{id}
Retrieve a task
None
200
POST
/tasks
Create task
None
201
PUT
/tasks/{id}
Update task
None
200
DELETE
/tasks/{id}
Delete task
None
204
GET
/health
Health check
None
200




Auth endpoints (A4)

Method
Endpoint
Description
Auth
Success
POST
/auth/signup
Create a new user account
None
201
POST
/auth/login
Log in and receive a JWT
None
200
POST
/auth/logout
End the user session
Bearer token
200
GET
/public/info
Public route — open to anyone
None
200
GET
/protected/profile
Returns user profile
Bearer token
200
GET
/protected/dashboard
Returns user dashboard
Bearer token
200




Status codes

Code
Meaning
200
OK
201
Created
400
Bad request — missing or invalid input
401
Unauthorized — missing, invalid, or expired token
404
Not found







Auth flow

Plain Text


1. POST /auth/signup        → creates account in Supabase
2. POST /auth/login         → returns access_token (JWT)
3. GET  /protected/profile  → send token as Authorization: Bearer <token>
4. POST /auth/logout        → invalidates the session



Protected routes use a reusable get_current_user dependency that calls supabase.auth.get_user(token) to verify every request. The route handler only runs if the token is valid.




Testing auth with curl

Sign up:

Bash


curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpassword"}'



Log in and copy the access_token:

Bash


curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpassword"}'



Call a protected route:

Bash


curl http://localhost:8000/protected/profile \
  -H "Authorization: Bearer <your_access_token>"



Call with a bad token (should return 401 ):

Bash


curl http://localhost:8000/protected/profile \
  -H "Authorization: Bearer tampered_token"






Swagger UI — bearer auth

Open http://localhost:8000/docs, click Authorize, paste your JWT, then use Try it out on any protected route. The padlock icon appears on all routes that require a token.

![Swagger UI screenshot]













Example curl Commands (Task API)

Retrieve all tasks:

Bash


curl -i http://localhost:8000/tasks



Create:

Bash


curl -i -X POST http://localhost:8000/tasks \
-H "Content-Type: application/json" \
-d '{"title":"Ship A4","done":false}'



Update:

Bash


curl -i -X PUT http://localhost:8000/tasks/4 \
-H "Content-Type: application/json" \
-d '{"title":"Ship A4","done":true}'



Delete:

Bash


curl -i -X DELETE http://localhost:8000/tasks/4






Why the Architecture Works

The API layer never communicates with PostgreSQL directly.

All database operations are isolated inside db.py.

All auth logic is handled by Supabase — no password hashing, no cryptography, no rolling your own auth. The server only verifies tokens Supabase signs.

Changing the storage engine only requires updating the repository layer, while every API endpoint remains unchanged.




Stage 7 – AI vs Me (A4 )

Prompt Given to AI


Build a secure FastAPI API with Supabase Auth. Use Python and FastAPI. Create five routes: POST /auth/signup (201), POST /auth/login (200, returns access_token and refresh_token), POST /auth/logout (200, requires bearer token), GET /public/info (200, no auth), GET /protected/profile (200, requires bearer token). Use supabase-py to call sign_up(), sign_in_with_password(), sign_out(), and get_user(token). Extract the bearer token from the Authorization header. Verify tokens using get_user() as a reusable FastAPI Depends middleware. Return 400 for missing fields, 401 for missing or invalid tokens. Add CORS middleware. Store SUPABASE_URL and SUPABASE_KEY in a .env file loaded with python-dotenv.

Three Differences

#
AI Output
My Implementation
1
Parsed the Authorization header manually with string splitting, risking crashes if the header was malformed
Used FastAPI's built-in HTTPBearer which handles extraction and validation cleanly
2
Did not wrap get_user() in a try/except — a Supabase error would crash the route with a 500
Wrapped verification in try/except to always return a clean 401 on any token failure
3
Returned 204 No Content for logout which caused fetch errors in the browser client
Returned 200 with a JSON body so all clients handle the response consistently




What My Prompt Missed

The prompt did not specify the exact status code for logout (204 vs 200), which the AI decided silently. It also did not mention error handling inside the auth guard, which the AI omitted entirely.

Rematch Result

After adding explicit error-handling and status code requirements to the prompt, the AI output required no manual fixes.




Assignment Progression

Week 5 (A9)

A separate polite scraper module that processes the first three Books to Scrape catalogue pages, discovers 60 unique books, caches successful HTML, validates normalized records, isolates failures, and writes JSON reports. See scraper/README.md.

Week 4 (A4)

Supabase Auth with JWT verification, protected routes, reusable auth middleware, and Swagger bearer auth.

Week 3 (A3)

PostgreSQL running inside Docker with persistent storage and Docker Compose.

Week 2 (A2)

SQLite database stored locally in tasks.db.

Week 1 (A1)

Tasks stored only in memory and lost when the application stopped.




Week 5 — A9 Polite Scraper

The repository includes a separate scraper/ module for the Week 5 A9 assignment. It does not change the existing FastAPI, PostgreSQL, Docker, or Supabase routes. The scraper uses Requests, Beautiful Soup, and Pydantic to fetch the first three Books to Scrape catalogue pages, discover 60 books, cache HTML, validate normalized records, isolate a deliberately broken page, and write JSON outputs and a run report.

Run it independently from the repository root. On Windows PowerShell:

Plain Text


cd scraper
python -m unittest discover -s tests -v
python src\main.py --check-robots
python src\main.py



On macOS/Linux:

Bash


cd scraper
python3 -m unittest discover -s tests -v
python3 src/main.py --check-robots
python3 src/main.py



See scraper/README.md for the target classification, politeness rules, schema, checkpoints, verified run evidence, and Windows instructions.

Technologies Used

•
Python

•
FastAPI

•
PostgreSQL

•
psycopg3

•
Docker

•
Docker Compose

•
Uvicorn

•
Supabase Auth

•
JSON Web Tokens (JWT)

•
Requests

•
Beautiful Soup

•
Pydantic

