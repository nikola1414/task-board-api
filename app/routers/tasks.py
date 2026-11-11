from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import can_edit, can_view
from app.models import ActivityLog, Comment, Priority, ProjectMember, Task, TaskStatus
from app.schemas import CommentCreate, CommentOut, Page, TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["tasks"])

SortKey = Literal[
    "created_at", "-created_at", "due_date", "-due_date", "priority", "-priority", "title", "-title"
]
NULLABLE_FIELDS = {"assignee_id", "due_date"}


def _get_task(db: Session, project_id: int, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None or task.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return task


def _check_assignee(db: Session, project_id: int, assignee_id: int | None) -> None:
    if assignee_id is not None and db.get(ProjectMember, (project_id, assignee_id)) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Assignee must be a project member")


def _log(db: Session, m: ProjectMember, task: Task, message: str) -> None:
    db.add(
        ActivityLog(project_id=m.project_id, task_id=task.id, user_id=m.user_id, message=message)
    )


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    project_id: int,
    body: TaskCreate,
    m: ProjectMember = Depends(can_edit),
    db: Session = Depends(get_db),
) -> Task:
    _check_assignee(db, project_id, body.assignee_id)
    task = Task(project_id=project_id, **body.model_dump())
    db.add(task)
    db.flush()
    _log(db, m, task, f"created task '{task.title}'")
    db.commit()
    return task


@router.get("", response_model=Page[TaskOut])
def list_tasks(
    project_id: int,
    status_: TaskStatus | None = Query(None, alias="status"),
    priority: Priority | None = None,
    assignee_id: int | None = None,
    due_before: date | None = None,
    q: str | None = Query(None, max_length=100, description="Search in title"),
    sort: SortKey = "-created_at",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: ProjectMember = Depends(can_view),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    stmt = select(Task).where(Task.project_id == project_id)
    if status_:
        stmt = stmt.where(Task.status == status_)
    if priority:
        stmt = stmt.where(Task.priority == priority)
    if assignee_id is not None:
        stmt = stmt.where(Task.assignee_id == assignee_id)
    if due_before:
        stmt = stmt.where(Task.due_date < due_before)
    if q:
        stmt = stmt.where(Task.title.icontains(q, autoescape=True))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = getattr(Task, sort.lstrip("-"))
    order = column.desc().nulls_last() if sort.startswith("-") else column.asc().nulls_last()
    items = db.scalars(stmt.order_by(order, Task.id).limit(limit).offset(offset)).all()
    return {
        "items": [TaskOut.model_validate(t) for t in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    project_id: int,
    task_id: int,
    _: ProjectMember = Depends(can_view),
    db: Session = Depends(get_db),
) -> Task:
    return _get_task(db, project_id, task_id)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    project_id: int,
    task_id: int,
    body: TaskUpdate,
    m: ProjectMember = Depends(can_edit),
    db: Session = Depends(get_db),
) -> Task:
    task = _get_task(db, project_id, task_id)
    changes = {
        k: v
        for k, v in body.model_dump(exclude_unset=True).items()
        if v is not None or k in NULLABLE_FIELDS
    }
    if "assignee_id" in changes:
        _check_assignee(db, project_id, changes["assignee_id"])
    for field, new in changes.items():
        old = getattr(task, field)
        if old == new:
            continue
        setattr(task, field, new)
        if field == "description":
            _log(db, m, task, "description updated")
        else:
            _log(db, m, task, f"{field} changed from {old or 'none'} to {new or 'none'}")
    db.commit()
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    project_id: int,
    task_id: int,
    m: ProjectMember = Depends(can_edit),
    db: Session = Depends(get_db),
) -> Response:
    task = _get_task(db, project_id, task_id)
    _log(db, m, task, f"deleted task '{task.title}'")
    db.flush()
    db.delete(task)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- comments ---
@router.get("/{task_id}/comments", response_model=list[CommentOut])
def list_comments(
    project_id: int,
    task_id: int,
    _: ProjectMember = Depends(can_view),
    db: Session = Depends(get_db),
) -> list[Comment]:
    _get_task(db, project_id, task_id)
    return list(db.scalars(select(Comment).where(Comment.task_id == task_id).order_by(Comment.id)))


@router.post("/{task_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(
    project_id: int,
    task_id: int,
    body: CommentCreate,
    m: ProjectMember = Depends(can_edit),
    db: Session = Depends(get_db),
) -> Comment:
    task = _get_task(db, project_id, task_id)
    comment = Comment(task_id=task.id, author_id=m.user_id, body=body.body)
    db.add(comment)
    _log(db, m, task, f"commented on '{task.title}'")
    db.commit()
    return comment
