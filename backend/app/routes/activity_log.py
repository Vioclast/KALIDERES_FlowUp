from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.auth import require_roles
from app.database import get_session
from app.models import ActivityLog

router = APIRouter(prefix="/activity-log", tags=["Activity log"])


@router.get(
    "",
    response_model=list[ActivityLog],
    dependencies=[Depends(require_roles("owner"))],
)
def list_activity_log(session: Session = Depends(get_session)):
    """Show the audit trail, newest first. Only the owner may view it."""
    return session.exec(select(ActivityLog).order_by(ActivityLog.id.desc())).all()