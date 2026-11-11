# Task Board API – Project Plan

## Stack

- **FastAPI** with Pydantic: the most in-demand Python framework for junior back-end roles, with automatic API docs
- **PostgreSQL** with SQLAlchemy 2.0 and Alembic migrations
- **Redis** for caching and rate limiting
- **JWT auth** (argon2 password hashing)
- **pytest + httpx**, **ruff + mypy**
- **Docker Compose** and **GitHub Actions**
- **React + TypeScript + Vite** client (small, optional)
- **Jira** for the backlog, with one branch and pull request per ticket

## Phase 0 – Setup

1. Create the GitHub repo and a README skeleton.
2. Create a Jira project with a simple Scrum board and add the tickets below as stories.
3. Write `docker-compose.yml` with the API, Postgres and Redis.
4. Add a FastAPI app with a `/health` endpoint.
5. Add ruff, mypy and one pytest test.
6. Add a GitHub Actions workflow that runs lint, type-check and tests on every pull request.

## Phase 1 – Data and auth

1. Design the tables: users, projects, project_members (with role), tasks, comments, activity_log.
2. Add the SQLAlchemy models and the first Alembic migration.
3. Build register and login with argon2 and JWT.
4. Add a `get_current_user` dependency.
5. Test register, login and a protected route.

## Phase 2 – Core API

1. Projects: CRUD, plus add and remove members.
2. Roles: owner, member and viewer, enforced in one reusable dependency.
3. Tasks: CRUD with status (todo, doing, done), priority, assignee and due date.
4. List endpoint with filters, sorting and pagination, all done in SQL.
5. Comments on tasks.
6. Write an activity_log row on every task change, for example "status changed from todo to doing".
7. Add tests for each router, including permission failures (403 and 404).

## Phase 3 – Redis and reliability

1. Cache the task list per project, and invalidate it on any write.
2. Rate-limit login attempts per IP with Redis.
3. Add consistent error responses and request logging with a request ID.
4. Add a `/health` check that tests both Postgres and Redis.
5. Run the tests against real Postgres and Redis containers in CI.

## Phase 4 – Quality and docs

1. Add pytest coverage reporting and aim for around 80% on the core logic.
2. Add a Dockerfile with a multi-stage build.
3. Write the README: what it does, architecture diagram, `docker compose up` quickstart, an endpoint table and your design decisions.
4. Add seed data and a short Swagger walkthrough.

## Phase 5 – Client (optional, useful for the front-end application)

1. Create the Vite + React + TypeScript project.
2. Build the login screen.
3. Build a project list and a task board with three columns.
4. Add create and move task actions that call the API.
5. Add one Playwright test for login, create task and move task.

## Phase 6 – CV

1. Replace the placeholder with the real project.
2. Add the framework to the Languages line, for example "Python (FastAPI, PyTorch, pytest)".
3. Write 3 bullets covering the stack, the tests and CI, and the documentation, using the real numbers (tests, coverage, endpoints).

## Rules while you build

- Keep each ticket small enough for one pull request, and write the test in the same pull request.
- Don't start the client until Phase 4 is done. A well-tested API with a clear README is worth more than a polished UI.
