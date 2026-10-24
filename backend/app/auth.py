from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlmodel import Session

from app.database import get_session
from app.models import User


def get_current_user(
    x_user_id: Annotated[int, Header(description="ID of the simulated user (see GET /users)")],
    session: Session = Depends(get_session),
) -> User:
    """Find the simulated user from the x-user-id header. A real app would use a login."""
    user = session.get(User, x_user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown user")
    return user


def require_roles(*allowed_roles: str):
    """Build a check that only lets users with one of the given roles through."""

    def check_role(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            allowed = ", ".join(allowed_roles)
            raise HTTPException(
                status_code=403,
                detail=f"Role '{user.role}' is not allowed to do this. Allowed roles: {allowed}.",
            )
        return user

    return check_role