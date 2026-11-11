from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import can_view, get_current_user, is_owner
from app.models import ActivityLog, Project, ProjectMember, Role, User
from app.schemas import (
    ActivityOut,
    MemberAdd,
    MemberOut,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
)

router = APIRouter(prefix="/projects", tags=["projects"])


def _out(project: Project, role: Role) -> ProjectOut:
    return ProjectOut.model_validate(project).model_copy(update={"role": role})


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ProjectOut:
    project = Project(name=body.name, description=body.description)
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=user.id, role=Role.owner))
    db.commit()
    return _out(project, Role.owner)


@router.get("", response_model=list[ProjectOut])
def list_projects(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ProjectOut]:
    rows = db.execute(
        select(Project, ProjectMember.role)
        .join(ProjectMember)
        .where(ProjectMember.user_id == user.id)
        .order_by(Project.id)
    ).all()
    return [_out(p, role) for p, role in rows]


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int, m: ProjectMember = Depends(can_view), db: Session = Depends(get_db)
) -> ProjectOut:
    return _out(db.get_one(Project, project_id), m.role)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    body: ProjectUpdate,
    m: ProjectMember = Depends(is_owner),
    db: Session = Depends(get_db),
) -> ProjectOut:
    project = db.get_one(Project, project_id)
    for field, value in body.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(project, field, value)
    db.commit()
    return _out(project, m.role)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int, _: ProjectMember = Depends(is_owner), db: Session = Depends(get_db)
) -> Response:
    db.delete(db.get_one(Project, project_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- members ---
@router.get("/{project_id}/members", response_model=list[MemberOut])
def list_members(
    project_id: int, _: ProjectMember = Depends(can_view), db: Session = Depends(get_db)
) -> list[MemberOut]:
    rows = db.execute(
        select(User.id, User.email, ProjectMember.role)
        .join(ProjectMember)
        .where(ProjectMember.project_id == project_id)
        .order_by(User.id)
    ).all()
    return [MemberOut(user_id=uid, email=email, role=role) for uid, email, role in rows]


@router.post("/{project_id}/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def add_member(
    project_id: int,
    body: MemberAdd,
    _: ProjectMember = Depends(is_owner),
    db: Session = Depends(get_db),
) -> MemberOut:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if db.get(ProjectMember, (project_id, user.id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "User is already a member")
    db.add(ProjectMember(project_id=project_id, user_id=user.id, role=body.role))
    db.commit()
    return MemberOut(user_id=user.id, email=user.email, role=body.role)


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    project_id: int,
    user_id: int,
    _: ProjectMember = Depends(is_owner),
    db: Session = Depends(get_db),
) -> Response:
    member = db.get(ProjectMember, (project_id, user_id))
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    if member.role == Role.owner:
        owners = db.scalar(
            select(func.count())
            .select_from(ProjectMember)
            .where(ProjectMember.project_id == project_id, ProjectMember.role == Role.owner)
        )
        if owners == 1:
            raise HTTPException(status.HTTP_409_CONFLICT, "Cannot remove the last owner")
    db.delete(member)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- activity ---
@router.get("/{project_id}/activity", response_model=list[ActivityOut])
def list_activity(
    project_id: int,
    limit: int = 50,
    _: ProjectMember = Depends(can_view),
    db: Session = Depends(get_db),
) -> list[ActivityLog]:
    return list(
        db.scalars(
            select(ActivityLog)
            .where(ActivityLog.project_id == project_id)
            .order_by(ActivityLog.id.desc())
            .limit(min(max(limit, 1), 200))
        )
    )
