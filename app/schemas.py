from datetime import date, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import Priority, Role, TaskStatus

T = TypeVar("T")


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- auth ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(ORM):
    id: int
    email: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- projects ---
class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class ProjectOut(ORM):
    id: int
    name: str
    description: str
    created_at: datetime
    role: Role | None = None  # caller's role, filled in by the router


class MemberAdd(BaseModel):
    email: EmailStr
    role: Role = Role.member


class MemberOut(BaseModel):
    user_id: int
    email: str
    role: Role


# --- tasks ---
class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    status: TaskStatus = TaskStatus.todo
    priority: Priority = Priority.medium
    assignee_id: int | None = None
    due_date: date | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus | None = None
    priority: Priority | None = None
    assignee_id: int | None = None
    due_date: date | None = None


class TaskOut(ORM):
    id: int
    project_id: int
    title: str
    description: str
    status: TaskStatus
    priority: Priority
    assignee_id: int | None
    due_date: date | None
    created_at: datetime
    updated_at: datetime


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


# --- comments / activity ---
class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class CommentOut(ORM):
    id: int
    task_id: int
    author_id: int | None
    body: str
    created_at: datetime


class ActivityOut(ORM):
    id: int
    task_id: int | None
    user_id: int | None
    message: str
    created_at: datetime
