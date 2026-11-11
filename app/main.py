from fastapi import FastAPI

from app.routers import auth, projects, tasks

app = FastAPI(title="Task Board API", version="0.1.0")
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(tasks.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
