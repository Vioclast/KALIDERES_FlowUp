from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import User

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=list[User])
def list_users(session: Session = Depends(get_session)):
    """List the simulated users. The app uses this to let you switch roles."""
    return session.exec(select(User)).all()