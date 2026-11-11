"""Demo data: `python -m app.seed` (or `docker compose exec api python -m app.seed`).

Creates demo@example.com (owner) and viewer@example.com (viewer), password `password123`,
plus one project with a handful of tasks. Does nothing if the demo user already exists.
"""

from datetime import date, timedelta

from sqlalchemy import select

from app.db import SessionLocal
from app.models import (
    ActivityLog,
    Comment,
    Priority,
    Project,
    ProjectMember,
    Role,
    Task,
    TaskStatus,
    User,
)
from app.security import hash_password

PASSWORD = "password123"


def seed() -> None:
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == "demo@example.com")):
            print("Seed data already present.")
            return
        demo = User(email="demo@example.com", password_hash=hash_password(PASSWORD))
        viewer = User(email="viewer@example.com", password_hash=hash_password(PASSWORD))
        project = Project(name="Website relaunch", description="Q1 marketing site rebuild")
        db.add_all([demo, viewer, project])
        db.flush()
        db.add_all(
            [
                ProjectMember(project_id=project.id, user_id=demo.id, role=Role.owner),
                ProjectMember(project_id=project.id, user_id=viewer.id, role=Role.viewer),
            ]
        )
        today = date.today()
        tasks = [
            Task(
                project_id=project.id,
                title=title,
                status=status,
                priority=prio,
                assignee_id=demo.id,
                due_date=today + timedelta(days=days),
            )
            for title, status, prio, days in [
                ("Draft sitemap", TaskStatus.done, Priority.high, -3),
                ("Design homepage", TaskStatus.doing, Priority.high, 2),
                ("Write copy for About page", TaskStatus.todo, Priority.medium, 5),
                ("Set up analytics", TaskStatus.todo, Priority.low, 10),
                ("Accessibility audit", TaskStatus.todo, Priority.medium, 14),
            ]
        ]
        db.add_all(tasks)
        db.flush()
        db.add(Comment(task_id=tasks[1].id, author_id=demo.id, body="First mockup is in Figma."))
        db.add_all(
            ActivityLog(
                project_id=project.id,
                task_id=t.id,
                user_id=demo.id,
                message=f"created task '{t.title}'",
            )
            for t in tasks
        )
        db.commit()
        print("Seeded demo@example.com / viewer@example.com (password: password123).")


if __name__ == "__main__":
    seed()
