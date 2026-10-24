from sqlmodel import Session

from app.models import ActivityLog, User


def log_activity(session: Session, user: User, action: str, details: str) -> None:
    """Add one line to the activity log. The caller must commit the session."""
    session.add(
        ActivityLog(
            user_id=user.id,
            user_name=user.name,
            role=user.role,
            action=action,
            details=details,
        )
    )