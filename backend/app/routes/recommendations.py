from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, SQLModel, select

from app.activity import log_activity
from app.auth import require_roles
from app.database import get_session
from app.models import (
    Product,
    PurchaseOrder,
    Recommendation,
    StockBatch,
    Supplier,
    User,
)
from app.rules import analyze_inventory
from app.schemas import RecommendationPreview

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

# Only these roles may run the stock check and see the suggestions.
STOCK_ROLES = ("owner", "warehouse")


class ApprovalRequest(SQLModel):
    """Optional input when approving. A quantity can replace the suggested one."""

    quantity: Optional[int] = None


def get_pending_recommendation(session: Session, recommendation_id: int) -> Recommendation:
    """Load a recommendation that is still waiting for a decision, or raise an error."""
    recommendation = session.get(Recommendation, recommendation_id)
    if recommendation is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if recommendation.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"This recommendation was already {recommendation.status}.",
        )
    return recommendation


@router.get(
    "/preview",
    response_model=list[RecommendationPreview],
    dependencies=[Depends(require_roles(*STOCK_ROLES))],
)
def preview_recommendations(session: Session = Depends(get_session)):
    """Show what the stock check would suggest. Nothing is saved."""
    return analyze_inventory(session, date.today())


@router.post("/run", response_model=list[Recommendation])
def run_stock_check(
    user: User = Depends(require_roles(*STOCK_ROLES)),
    session: Session = Depends(get_session),
):
    """Run the stock check and save every new suggestion as 'pending'."""
    suggestions = analyze_inventory(session, date.today())

    pending = session.exec(
        select(Recommendation).where(Recommendation.status == "pending")
    ).all()
    already_pending = {(item.product_id, item.action, item.batch_id) for item in pending}

    open_orders = session.exec(
        select(PurchaseOrder).where(PurchaseOrder.status == "placed")
    ).all()
    ordered_product_ids = {order.product_id for order in open_orders}

    created = []
    for suggestion in suggestions:
        key = (suggestion.product_id, suggestion.action, suggestion.batch_id)
        if key in already_pending:
            continue  # The same suggestion is already waiting for a decision
        if suggestion.batch_id is None and suggestion.product_id in ordered_product_ids:
            continue  # An order for this product is already on its way
        if suggestion.action == "discount":
            batch = session.get(StockBatch, suggestion.batch_id)
            if batch is not None and batch.discount_percent > 0:
                continue  # This batch already has a discount
        recommendation = Recommendation(**suggestion.model_dump())
        session.add(recommendation)
        created.append(recommendation)

    log_activity(
        session,
        user,
        "stock_check_run",
        f"Stock check found {len(suggestions)} suggestion(s), {len(created)} new.",
    )
    session.commit()  # Saves the suggestions and the log line together

    for recommendation in created:
        session.refresh(recommendation)
    return created


@router.get(
    "",
    response_model=list[Recommendation],
    dependencies=[Depends(require_roles(*STOCK_ROLES))],
)
def list_recommendations(
    status: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """List saved suggestions. Add ?status=pending to see only the waiting ones."""
    query = select(Recommendation).order_by(Recommendation.id)
    if status:
        query = query.where(Recommendation.status == status)
    return session.exec(query).all()


@router.post("/{recommendation_id}/approve", response_model=Recommendation)
def approve_recommendation(
    recommendation_id: int,
    body: Optional[ApprovalRequest] = None,
    user: User = Depends(require_roles("owner")),
    session: Session = Depends(get_session),
):
    """Approve a suggestion and carry it out. Only the owner can do this."""
    recommendation = get_pending_recommendation(session, recommendation_id)
    product = session.get(Product, recommendation.product_id)

    if recommendation.action == "discount":
        batch = session.get(StockBatch, recommendation.batch_id)
        batch.discount_percent = recommendation.discount_percent
        session.add(batch)
        outcome = (
            f"{recommendation.discount_percent}% discount applied to a batch of "
            f"{product.name}."
        )
    elif recommendation.action == "needs_review" and recommendation.batch_id is not None:
        raise HTTPException(
            status_code=400,
            detail=(
                "This item needs a manual check, so it cannot be approved. "
                "Reject it to dismiss it after you have handled it."
            ),
        )
    else:
        # A reorder, or a "needs_review" item where the owner chooses the quantity.
        quantity = body.quantity if body and body.quantity else recommendation.suggested_quantity
        if not quantity or quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail="Please give a quantity greater than 0 to place this order.",
            )
        supplier = session.get(Supplier, product.supplier_id)
        order = PurchaseOrder(
            recommendation_id=recommendation.id,
            product_id=product.id,
            product_name=product.name,
            supplier_id=supplier.id,
            supplier_name=supplier.name,
            quantity=quantity,
            total_cost=round(quantity * product.unit_cost, 2),
            approved_by_user_id=user.id,
        )
        session.add(order)
        outcome = (
            f"Order placed with {supplier.name}: {quantity} x {product.name}, "
            f"total RM {order.total_cost:.2f}."
        )

    recommendation.status = "approved"
    recommendation.decided_by_user_id = user.id
    recommendation.decided_at = datetime.now()
    session.add(recommendation)

    log_activity(
        session,
        user,
        "recommendation_approved",
        f"Approved #{recommendation.id} ({recommendation.action}). {outcome}",
    )
    session.commit()
    session.refresh(recommendation)
    return recommendation


@router.post("/{recommendation_id}/reject", response_model=Recommendation)
def reject_recommendation(
    recommendation_id: int,
    user: User = Depends(require_roles("owner")),
    session: Session = Depends(get_session),
):
    """Reject a suggestion. Nothing is ordered or discounted. Only the owner can do this."""
    recommendation = get_pending_recommendation(session, recommendation_id)

    recommendation.status = "rejected"
    recommendation.decided_by_user_id = user.id
    recommendation.decided_at = datetime.now()
    session.add(recommendation)

    log_activity(
        session,
        user,
        "recommendation_rejected",
        f"Rejected #{recommendation.id} ({recommendation.action}) "
        f"for {recommendation.product_name}.",
    )
    session.commit()
    session.refresh(recommendation)
    return recommendation