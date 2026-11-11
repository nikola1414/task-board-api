from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ProjectMember, Role, User
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

ROLE_RANK = {Role.viewer: 0, Role.member: 1, Role.owner: 2}


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    user_id = decode_access_token(token)
    user = db.get(User, user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(min_role: Role) -> Callable[..., ProjectMember]:
    """Dependency factory: caller must be a member of `project_id` with at least `min_role`.

    Non-members get 404 (so project ids don't leak); members with too low a role get 403.
    """

    def dep(
        project_id: int,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> ProjectMember:
        member = db.get(ProjectMember, (project_id, user.id))
        if member is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
        if ROLE_RANK[member.role] < ROLE_RANK[min_role]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires {min_role} role")
        return member

    return dep


can_view = require_role(Role.viewer)
can_edit = require_role(Role.member)
is_owner = require_role(Role.owner)
