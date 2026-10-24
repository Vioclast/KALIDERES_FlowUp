from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.auth import require_roles
from app.database import get_session
from app.models import PurchaseOrder

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get(
    "",
    response_model=list[PurchaseOrder],
    dependencies=[Depends(require_roles("owner", "warehouse"))],
)
def list_orders(session: Session = Depends(get_session)):
    """List the supplier orders, newest first. Each total cost is an expense record."""
    return session.exec(select(PurchaseOrder).order_by(PurchaseOrder.id.desc())).all()